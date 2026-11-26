"""Screener.in fundamentals enrichment (market cap, key ratios).

Screener's real value is not a news feed (its concall/presentation scraper was
retired) but its structured fundamentals. This provider fetches a company's
headline ratios on demand — only for stocks that are already candidates — and
caches them. The most important field is **market cap**, which the tradeable-
liquidity gate needs to place a stock in the right tier (without it, every name
falls into the 'unknown' bucket).

The HTML parser is pure and unit-tested; the network fetch is a thin, graceful
wrapper (returns None on any failure, so callers degrade to prior behaviour).
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("newsedge.market_data.fundamentals")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class Fundamentals:
    symbol: str
    market_cap_cr: Optional[float] = None
    current_price: Optional[float] = None
    revenue_cr: Optional[float] = None   # latest annual / TTM sales, ₹ crore
    ratios: Dict[str, float] = field(default_factory=dict)


def _to_number(text: str) -> Optional[float]:
    """Parse an Indian-formatted numeric string (e.g. '16,45,678' or '2,950.5')."""
    if not text:
        return None
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_screener_ratios(html: str) -> Dict[str, float]:
    """Extract the #top-ratios list from a Screener company page into a dict.

    Keys are lowercased ratio names (e.g. 'market cap', 'current price').
    Values are the first numeric token of each ratio.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    ratios: Dict[str, float] = {}
    container = soup.select_one("#top-ratios")
    if not container:
        return ratios

    for li in container.select("li"):
        name_el = li.select_one(".name")
        if not name_el:
            continue
        name = " ".join(name_el.get_text(strip=True).split()).lower()
        # Prefer an explicit .number span; fall back to the value text.
        num_el = li.select_one(".number")
        if num_el is not None:
            val = _to_number(num_el.get_text())
        else:
            val_el = li.select_one(".value")
            val = _to_number(val_el.get_text()) if val_el else None
        if name and val is not None:
            ratios[name] = val
    return ratios


def market_cap_cr_from_html(html: str) -> Optional[float]:
    """Return market cap in ₹ crore from a Screener page, if present."""
    ratios = parse_screener_ratios(html)
    for key in ("market cap", "mcap", "market capitalization"):
        if key in ratios:
            return ratios[key]
    return None


def annual_sales_cr_from_html(html: str) -> Optional[float]:
    """Return the latest annual / TTM sales (revenue) in ₹ crore from the P&L table.

    Screener figures are already in ₹ crore. We take the last numeric column of
    the 'Sales' (or 'Revenue') row, which is the most recent period / TTM.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    section = soup.select_one("#profit-loss")
    if not section:
        return None
    table = section.find("table")
    if not table:
        return None
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        label = cells[0].get_text(strip=True).lower()
        if label.startswith("sales") or label.startswith("revenue"):
            nums = [_to_number(td.get_text()) for td in cells[1:]]
            nums = [n for n in nums if n is not None]
            if nums:
                return nums[-1]
    return None


class FundamentalsProvider:
    """On-demand, cached Screener fundamentals lookup."""

    def __init__(self, timeout_seconds: int = 12):
        self.timeout_seconds = timeout_seconds
        self._cache: Dict[str, Optional[Fundamentals]] = {}
        self._lock = threading.Lock()

    def get(self, nse_symbol: str) -> Optional[Fundamentals]:
        sym = (nse_symbol or "").upper().strip()
        if not sym:
            return None
        with self._lock:
            if sym in self._cache:
                return self._cache[sym]

        result = self._fetch(sym)
        with self._lock:
            self._cache[sym] = result
        return result

    def _fetch(self, sym: str) -> Optional[Fundamentals]:
        import requests

        for path in (f"/company/{sym}/consolidated/", f"/company/{sym}/"):
            url = f"https://www.screener.in{path}"
            try:
                resp = requests.get(url, headers=_HEADERS, timeout=self.timeout_seconds)
                if resp.status_code != 200 or not resp.text:
                    continue
                ratios = parse_screener_ratios(resp.text)
                if not ratios:
                    continue
                mcap = None
                for key in ("market cap", "mcap", "market capitalization"):
                    if key in ratios:
                        mcap = ratios[key]
                        break
                return Fundamentals(
                    symbol=sym,
                    market_cap_cr=mcap,
                    current_price=ratios.get("current price"),
                    revenue_cr=annual_sales_cr_from_html(resp.text),
                    ratios=ratios,
                )
            except requests.RequestException as exc:
                logger.debug("Screener fundamentals fetch failed for %s: %s", sym, exc)
            time.sleep(0.2)
        logger.debug("No Screener fundamentals for %s", sym)
        return None


_provider: Optional[FundamentalsProvider] = None


def get_fundamentals_provider() -> FundamentalsProvider:
    global _provider
    if _provider is None:
        _provider = FundamentalsProvider()
    return _provider
