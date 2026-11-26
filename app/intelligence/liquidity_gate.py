"""Tradeable-liquidity gate.

A next-morning intraday pick is only useful if you can actually get in and out at
the open without the stock being the move. This gate classifies a symbol into a
liquidity tier and returns a score modifier plus a hard ``is_tradeable`` flag.

Signals used (all static / offline — no market-data feed required):
- NSE F&O membership (the ~185 derivative names are the most liquid cash stocks).
- The company's market-cap category / market cap when known.

Philosophy: liquidity is not alpha, so it never *boosts* a score. It only
penalises thin names and hard-gates micro-caps out of actionable tiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.intelligence.derivatives_context import NSE_FNO_UNIVERSE

# Rough market-cap thresholds in ₹ crore.
_LARGE_CR = 20_000.0
_MID_CR = 5_000.0
_SMALL_CR = 1_000.0

# Map the DB's MarketCapCategory enum values to tiers.
_CAT_TO_TIER = {
    "large_cap": "LARGE",
    "mid_cap": "MID",
    "small_cap": "SMALL",
    "micro_cap": "MICRO",
}


@dataclass
class LiquidityAssessment:
    symbol: str
    tier: str              # FNO, LARGE, MID, SMALL, MICRO, UNKNOWN
    score_modifier: float  # <= 0
    is_tradeable: bool
    note: str = ""


def _tier_from_mcap(market_cap_cr: Optional[float]) -> Optional[str]:
    if market_cap_cr is None or market_cap_cr <= 0:
        return None
    if market_cap_cr >= _LARGE_CR:
        return "LARGE"
    if market_cap_cr >= _MID_CR:
        return "MID"
    if market_cap_cr >= _SMALL_CR:
        return "SMALL"
    return "MICRO"


def evaluate_liquidity(
    symbol: str,
    market_cap_category: Optional[str] = None,
    market_cap_cr: Optional[float] = None,
) -> LiquidityAssessment:
    """Return a liquidity assessment for an NSE symbol."""
    sym = (symbol or "").upper().strip()

    # 1. F&O membership is the strongest liquidity signal.
    if sym in NSE_FNO_UNIVERSE:
        return LiquidityAssessment(sym, "FNO", 0.0, True, "F&O stock — ample intraday liquidity.")

    # 2. Explicit category, else infer from market cap.
    tier: Optional[str] = None
    if market_cap_category:
        tier = _CAT_TO_TIER.get(market_cap_category.strip().lower())
    if tier is None:
        tier = _tier_from_mcap(market_cap_cr)

    if tier == "LARGE":
        return LiquidityAssessment(sym, "LARGE", 0.0, True, "Large-cap — liquid.")
    if tier == "MID":
        return LiquidityAssessment(sym, "MID", 0.0, True, "Mid-cap — generally liquid.")
    if tier == "SMALL":
        return LiquidityAssessment(sym, "SMALL", -4.0, True, "Small-cap — expect wider spreads / slippage at open.")
    if tier == "MICRO":
        return LiquidityAssessment(
            sym, "MICRO", -12.0, False,
            "Micro-cap — too thin for a reliable intraday fill; tracking only.",
        )

    # 3. Unknown — mild caution, still tradeable (don't over-penalise missing data).
    return LiquidityAssessment(sym, "UNKNOWN", -2.0, True, "Liquidity unknown — size positions conservatively.")
