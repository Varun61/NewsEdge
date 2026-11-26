"""NSE cash-market bhavcopy provider (authoritative price / volume / delivery).

One daily download (`sec_bhavdata_full_DDMMYYYY.csv`) covers the entire NSE cash
universe with OHLC, traded quantity, number of trades, and — crucially —
**delivery quantity and delivery percentage**. Delivery % is a classic
smart-money conviction signal: a catalyst that moves on high delivery + high
relative volume has real institutional participation, versus a thin, low-
delivery pop that fades.

This is the authoritative, free, post-market source that replaces per-symbol
yfinance for price/volume/delivery (yfinance is still used for multi-month EMA
history, which a single-day bhavcopy can't provide).

The CSV parser is pure/offline-testable; downloads are disk-cached (each day's
file is immutable once published) and loaded lazily behind a lock.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("newsedge.market_data.bhavcopy")

_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d}.csv"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
}
_EQUITY_SERIES = {"EQ", "BE", "BZ", "SM", "ST"}


@dataclass
class DayBar:
    symbol: str
    series: str
    prev_close: float
    open: float
    high: float
    low: float
    close: float
    avg_price: float
    qty: float            # total traded quantity
    turnover_lacs: float
    trades: int
    deliv_qty: float
    deliv_per: float      # delivery percentage (0-100), -1 if unavailable


def _f(s: str, default: float = 0.0) -> float:
    s = (s or "").strip()
    if not s or s in ("-", "NA"):
        return default
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return default


def parse_sec_bhavdata(csv_text: str) -> Dict[str, DayBar]:
    """Parse a sec_bhavdata_full CSV into {symbol: DayBar} (equity series only)."""
    out: Dict[str, DayBar] = {}
    lines = [ln for ln in (csv_text or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return out

    header = [h.strip().upper() for h in lines[0].split(",")]
    idx = {name: i for i, name in enumerate(header)}

    def col(cells, name, default=""):
        i = idx.get(name)
        return cells[i].strip() if i is not None and i < len(cells) else default

    for ln in lines[1:]:
        cells = ln.split(",")
        series = col(cells, "SERIES").upper()
        if series and series not in _EQUITY_SERIES:
            continue
        symbol = col(cells, "SYMBOL").upper()
        if not symbol:
            continue
        out[symbol] = DayBar(
            symbol=symbol,
            series=series,
            prev_close=_f(col(cells, "PREV_CLOSE")),
            open=_f(col(cells, "OPEN_PRICE")),
            high=_f(col(cells, "HIGH_PRICE")),
            low=_f(col(cells, "LOW_PRICE")),
            close=_f(col(cells, "CLOSE_PRICE")),
            avg_price=_f(col(cells, "AVG_PRICE")),
            qty=_f(col(cells, "TTL_TRD_QNTY")),
            turnover_lacs=_f(col(cells, "TURNOVER_LACS")),
            trades=int(_f(col(cells, "NO_OF_TRADES"))),
            deliv_qty=_f(col(cells, "DELIV_QTY")),
            deliv_per=_f(col(cells, "DELIV_PER"), default=-1.0),
        )
    return out


@dataclass
class SymbolMetrics:
    symbol: str
    close: float
    delivery_pct: float       # latest day's delivery %
    relative_volume: float    # latest qty / trailing average qty
    avg_delivery_pct: float   # trailing average delivery %


class BhavcopyProvider:
    """Lazily loads recent bhavcopy days and exposes per-symbol metrics."""

    def __init__(self, cache_dir: Optional[Path] = None, lookback_days: int = 10, timeout: int = 30):
        self.cache_dir = cache_dir
        self.lookback_days = lookback_days
        self.timeout = timeout
        self._lock = threading.Lock()
        self._loaded = False
        self._days: List[Tuple[date, Dict[str, DayBar]]] = []  # newest first

    # ── fetching ────────────────────────────────────────────────────────
    def _cache_path(self, d: date) -> Optional[Path]:
        if not self.cache_dir:
            return None
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir / f"sec_bhavdata_{d.strftime('%d%m%Y')}.csv"

    def _download_day(self, d: date) -> Optional[str]:
        cp = self._cache_path(d)
        if cp and cp.exists():
            try:
                return cp.read_text(encoding="utf-8")
            except Exception:
                pass
        import requests
        url = _URL.format(d=d.strftime("%d%m%Y"))
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200 or "SYMBOL" not in resp.text[:200].upper():
                return None
            if cp:
                try:
                    cp.write_text(resp.text, encoding="utf-8")
                except Exception:
                    pass
            return resp.text
        except requests.RequestException as exc:
            logger.debug("Bhavcopy download failed for %s: %s", d, exc)
            return None

    def _ensure_loaded(self, as_of: Optional[date] = None) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            from app.trading_calendar import is_trading_day, previous_trading_day, today_ist
            cur = as_of or today_ist()
            # Walk back, collecting available trading-day files until we have lookback_days.
            probe = cur
            attempts = 0
            while len(self._days) < self.lookback_days and attempts < self.lookback_days + 8:
                attempts += 1
                if is_trading_day(probe):
                    text = self._download_day(probe)
                    if text:
                        parsed = parse_sec_bhavdata(text)
                        if parsed:
                            self._days.append((probe, parsed))
                probe = previous_trading_day(probe)
            self._loaded = True
            logger.info("Bhavcopy loaded %d trading days (newest %s).",
                        len(self._days), self._days[0][0] if self._days else "none")

    # ── metrics ─────────────────────────────────────────────────────────
    def metrics(self, symbol: str) -> Optional[SymbolMetrics]:
        self._ensure_loaded()
        if not self._days:
            return None
        sym = (symbol or "").upper().strip()
        latest = self._days[0][1].get(sym)
        if not latest:
            return None

        prior = [d[sym].qty for _, d in self._days[1:] if sym in d and d[sym].qty > 0]
        avg_qty = sum(prior) / len(prior) if prior else 0.0
        rel_vol = round(latest.qty / avg_qty, 2) if avg_qty > 0 else 1.0

        deliv_vals = [d[sym].deliv_per for _, d in self._days if sym in d and d[sym].deliv_per >= 0]
        avg_deliv = round(sum(deliv_vals) / len(deliv_vals), 1) if deliv_vals else -1.0

        return SymbolMetrics(
            symbol=sym,
            close=latest.close,
            delivery_pct=latest.deliv_per,
            relative_volume=rel_vol,
            avg_delivery_pct=avg_deliv,
        )


_provider: Optional[BhavcopyProvider] = None


def get_bhavcopy_provider() -> BhavcopyProvider:
    global _provider
    if _provider is None:
        try:
            from app.config import get_settings
            cache = get_settings().data_dir / "cache" / "bhavcopy"
        except Exception:
            cache = None
        _provider = BhavcopyProvider(cache_dir=cache)
    return _provider
