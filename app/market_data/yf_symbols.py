"""Central NSE symbol -> yfinance ticker mapping.

NSE symbols occasionally change (rebrands, demergers). yfinance keys off the
*current* ticker, so a stale symbol returns "No data found" and silently drops
the price-dependent signals (e.g. the 20/50 EMA trend check). This one place
maps known renames so every price lookup stays correct.

IMPORTANT: only add a mapping when the new ticker is unambiguous. A wrong map
points at the wrong company, which is worse than a graceful skip.
"""

from __future__ import annotations

# Legacy NSE symbol -> current NSE symbol (yfinance uses the current one).
# Keep this list conservative and verifiable.
_SYMBOL_OVERRIDES: dict[str, str] = {
    # Zomato Ltd rebranded to Eternal Ltd; ticker changed ZOMATO -> ETERNAL on
    # 9 Apr 2025 (NSE & BSE). (Confirmed via multiple exchange/press filings.)
    "ZOMATO": "ETERNAL",
    # NOTE: Tata Motors demerged (Oct-Nov 2025) into Tata Motors Passenger
    # Vehicles and a separately-listed CV "Tata Motors Ltd". The surviving
    # ticker is ambiguous, so no override is added here on purpose — a missing
    # map skips gracefully, a wrong map would point at the wrong entity.
}


def current_symbol(nse_symbol: str) -> str:
    """Return the current NSE symbol, applying known renames."""
    s = (nse_symbol or "").upper().strip()
    return _SYMBOL_OVERRIDES.get(s, s)


def to_yf_ticker(nse_symbol: str) -> str:
    """Return the yfinance ticker (``SYMBOL.NS``) for an NSE symbol, remapped."""
    return f"{current_symbol(nse_symbol)}.NS"
