"""STOCKSCOPE 360 — Layer 3 Intraday Technical Scanner & Unified Scorer.

Bridges NewsEdge pre-market catalyst intelligence (Layers 1 & 2) with
live Angel One 5-minute & daily market data (Layer 3):
  - Daily catalyst strength:      35% (0–35 pts)
  - Intraday technical strength:  45% (0–45 pts via VWAP, RSI-14, EMA-9, ORB, RelVol)
  - Liquidity & volatility:       20% (0–20 pts via Avg Traded Value Cr & ATR%)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from app.intelligence.trade_playbook import TradePlaybook, TradePlaybookCalculator
from app.market_data.angel_client import AngelOneClient, get_angel_client
from app.market_data.indicators import IntradaySnapshot, compute_intraday_snapshot
from app.market_data.symbol_resolver import get_token
from app.trading_calendar import is_trading_day, now_ist, previous_trading_day

logger = logging.getLogger("newsedge.market_data.intraday_scanner")


@dataclass
class StockScopeCandidate:
    """Unified Layer 1 + 2 + 3 scored intraday opportunity."""
    symbol: str
    company_name: str
    direction: str                  # "BULLISH" | "BEARISH"
    catalyst_type: str
    headline: str
    news_urls: list[str]

    # STOCKSCOPE 360 Score Breakdown (total 0–100)
    catalyst_score: float           # 0–35
    intraday_score: float           # 0–45
    liquidity_score: float          # 0–20
    total_score: float              # 0–100

    # Market & Intraday Metrics
    snapshot: IntradaySnapshot
    prev_close: float
    atr_14: float
    avg_traded_value_cr: float

    # Trade Validation
    trade_status: str               # "CONFIRMED_LONG" | "CONFIRMED_SHORT" | "WATCH" | "NO_TRADE"
    rejection_reason: Optional[str]
    playbook: Optional[TradePlaybook]


class IntradayScanner:
    """Scans shortlisted catalyst stocks using live Angel One 5-min & daily OHLCV."""

    def __init__(self, client: Optional[AngelOneClient] = None) -> None:
        self.client = client or get_angel_client()
        # Cache 20-day daily metrics per (symbol, session_date) so repeated 5-min scans are fast
        self._daily_cache: Dict[tuple[str, date], dict] = {}

    def resolve_session_date(self) -> date:
        """Return today if market has opened on a trading day, else latest trading day."""
        current = now_ist()
        today = current.date()
        if is_trading_day(today) and (current.hour > 9 or (current.hour == 9 and current.minute >= 16)):
            return today
        return previous_trading_day(today)

    def scan_candidates(
        self,
        watchlist_items: list[dict],
        session_date: Optional[date] = None,
        min_confirmed_score: float = 65.0,
    ) -> list[StockScopeCandidate]:
        """Scan a list of catalyst candidates and return scored StockScopeCandidates.

        Each dict in watchlist_items should have:
          symbol, company_name, direction ('BULLISH'/'BEARISH'),
          raw_score (0-100 NewsEdge score), catalyst_type, headline, news_urls
        """
        target_date = session_date or self.resolve_session_date()
        logger.info(
            "Starting STOCKSCOPE 360 intraday scan for %d candidates (session: %s)...",
            len(watchlist_items),
            target_date,
        )

        results: list[StockScopeCandidate] = []
        for idx, item in enumerate(watchlist_items, 1):
            sym = item["symbol"].upper()
            token = get_token(sym)
            if not token:
                logger.debug("Skipping %s: not found in Angel One scrip master.", sym)
                continue

            # 1. Get 20-day daily baseline (prev_close, avg_vol, ATR-14)
            daily_stats = self._get_daily_baseline(sym, token, target_date)
            if not daily_stats:
                continue

            # 2. Get 5-min intraday candles for target_date
            from_dt = f"{target_date.strftime('%Y-%m-%d')} 09:15"
            now_dt = now_ist()
            if target_date == now_dt.date():
                to_dt = now_dt.strftime("%Y-%m-%d %H:%M")
            else:
                to_dt = f"{target_date.strftime('%Y-%m-%d')} 15:30"

            candles_5m = self.client.get_candles(
                symbol_token=token,
                exchange="NSE",
                interval="FIVE_MINUTE",
                from_date=from_dt,
                to_date=to_dt,
            )
            time.sleep(0.35)  # Respect Angel One SmartAPI rate limit

            if not candles_5m:
                logger.debug("No 5-min candles returned for %s on %s", sym, target_date)
                continue

            ltp = candles_5m[-1]["close"]
            prev_close = daily_stats["prev_close"]
            avg_vol = daily_stats["avg_volume"]
            atr_14 = daily_stats["atr_14"]
            avg_val_cr = round((avg_vol * prev_close) / 1e7, 2) if prev_close > 0 else 0.0

            direction = item.get("direction", "BULLISH").upper()
            snapshot = compute_intraday_snapshot(
                symbol=sym,
                ltp=ltp,
                prev_close=prev_close,
                today_candles=candles_5m,
                avg_daily_volume=avg_vol,
                direction=direction,
            )

            # 3. Compute STOCKSCOPE 360 3-pillar score
            raw_news_score = float(item.get("raw_score", 60.0))
            catalyst_score = round(min(35.0, max(0.0, raw_news_score * 0.35)), 1)
            liquidity_score = self._score_liquidity_and_volatility(
                avg_val_cr=avg_val_cr,
                atr_pct=(atr_14 / prev_close * 100) if prev_close > 0 else 0.0,
            )
            total_score = round(catalyst_score + snapshot.intraday_score + liquidity_score, 1)

            # 4. Validate setup (Opening Range rule + VWAP + Volume + Score threshold)
            trade_status, reason = self._validate_setup(
                direction=direction,
                snapshot=snapshot,
                candles_count=len(candles_5m),
                total_score=total_score,
                avg_val_cr=avg_val_cr,
                min_confirmed_score=min_confirmed_score,
            )

            playbook = None
            if trade_status in ("CONFIRMED_LONG", "CONFIRMED_SHORT", "WATCH"):
                playbook = TradePlaybookCalculator.calculate_playbook(
                    symbol=sym,
                    reference_price=ltp,
                    direction=direction,
                    atr=atr_14 if atr_14 > 0 else None,
                )

            results.append(
                StockScopeCandidate(
                    symbol=sym,
                    company_name=item.get("company_name", sym),
                    direction=direction,
                    catalyst_type=item.get("catalyst_type", "NEWS"),
                    headline=item.get("headline", ""),
                    news_urls=item.get("news_urls", []),
                    catalyst_score=catalyst_score,
                    intraday_score=snapshot.intraday_score,
                    liquidity_score=liquidity_score,
                    total_score=total_score,
                    snapshot=snapshot,
                    prev_close=prev_close,
                    atr_14=atr_14,
                    avg_traded_value_cr=avg_val_cr,
                    trade_status=trade_status,
                    rejection_reason=reason,
                    playbook=playbook,
                )
            )

        results.sort(key=lambda c: c.total_score, reverse=True)
        return results

    def _get_daily_baseline(self, symbol: str, token: str, target_date: date) -> Optional[dict]:
        """Fetch 20-day daily candles to compute prev_close, avg_volume, and ATR-14."""
        cache_key = (symbol, target_date)
        if cache_key in self._daily_cache:
            return self._daily_cache[cache_key]

        from_dt = (target_date - timedelta(days=40)).strftime("%Y-%m-%d 09:15")
        to_dt = (target_date - timedelta(days=1)).strftime("%Y-%m-%d 15:30")

        daily_candles = self.client.get_candles(
            symbol_token=token,
            exchange="NSE",
            interval="ONE_DAY",
            from_date=from_dt,
            to_date=to_dt,
        )
        time.sleep(0.35)

        if not daily_candles or len(daily_candles) < 2:
            logger.debug("Insufficient daily candles for %s", symbol)
            return None

        recent = daily_candles[-20:]
        prev_close = recent[-1]["close"]
        avg_vol = sum(c["volume"] for c in recent) / len(recent)

        # Compute 14-day ATR
        trs = []
        for i in range(1, len(recent)):
            h = recent[i]["high"]
            l = recent[i]["low"]
            pc = recent[i - 1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        atr_14 = round(sum(trs[-14:]) / min(len(trs), 14), 2) if trs else 0.0

        stats = {
            "prev_close": prev_close,
            "avg_volume": avg_vol,
            "atr_14": atr_14,
        }
        self._daily_cache[cache_key] = stats
        return stats

    @staticmethod
    def _score_liquidity_and_volatility(avg_val_cr: float, atr_pct: float) -> float:
        """Compute 0–20 Liquidity & Volatility score."""
        liq = 0.0
        # Average Traded Value (0–10 pts)
        if avg_val_cr >= 100.0:
            liq += 10.0
        elif avg_val_cr >= 25.0:
            liq += 8.0
        elif avg_val_cr >= 5.0:
            liq += 5.0
        elif avg_val_cr >= 1.0:
            liq += 2.0

        # ATR% sweet spot for intraday movement (0–10 pts)
        if 1.5 <= atr_pct <= 5.5:
            liq += 10.0
        elif 1.0 <= atr_pct < 1.5 or 5.5 < atr_pct <= 8.0:
            liq += 6.0
        elif atr_pct > 0:
            liq += 3.0

        return round(min(20.0, liq), 1)

    @staticmethod
    def _validate_setup(
        direction: str,
        snapshot: IntradaySnapshot,
        candles_count: int,
        total_score: float,
        avg_val_cr: float,
        min_confirmed_score: float,
    ) -> tuple[str, Optional[str]]:
        """Validate whether an actual intraday trade setup exists."""
        # Rule 1: Do not enter solely on the first 9:15 candle (wait for 15-min opening range)
        if candles_count < 3:
            return "WATCH", "Waiting for 9:15–9:30 AM Opening Range to complete"

        # Rule 2: Minimum liquidity check (avoid illiquid traps < 1 Cr daily turnover)
        if avg_val_cr < 1.0:
            return "NO_TRADE", f"Illiquid stock (Avg turnover ₹{avg_val_cr} Cr < ₹1 Cr)"

        is_bullish = "bull" in direction.lower()

        if is_bullish:
            if snapshot.vwap_position == "below":
                return "WATCH", "Price below VWAP — waiting for VWAP reclaim"
            if total_score >= min_confirmed_score and (
                snapshot.orb_signal == "breakout_up"
                or (snapshot.vwap_position == "above" and snapshot.relative_volume >= 1.5)
            ):
                return "CONFIRMED_LONG", None
            return "WATCH", f"Score {total_score}/100 or volume ({snapshot.relative_volume}x) awaiting breakout"
        else:
            if snapshot.vwap_position == "above":
                return "WATCH", "Price above VWAP — waiting for VWAP breakdown"
            if total_score >= min_confirmed_score and (
                snapshot.orb_signal == "breakout_down"
                or (snapshot.vwap_position == "below" and snapshot.relative_volume >= 1.5)
            ):
                return "CONFIRMED_SHORT", None
            return "WATCH", f"Score {total_score}/100 or volume ({snapshot.relative_volume}x) awaiting breakdown"
