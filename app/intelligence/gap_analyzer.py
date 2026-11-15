"""Pre-market opening gap analysis and execution risk evaluation.

Evaluates how a stock opens relative to its previous close to detect:
1. 'Sweet Spot' gaps (+0.5% to +2.5%): Ideal runway for sustained intraday follow-through.
2. 'Exhaustion Gaps' (> +4.0%): Excessive opening surge where smart money dumps into
   retail liquidity; high probability of intraday pullback.
3. 'Disconnect Traps': Stock gapping down on ostensibly bullish news, signaling
   stealth institutional distribution or negative concall guidance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("newsedge.intelligence.gap_analyzer")


@dataclass
class GapEvaluation:
    symbol: str
    prev_close: float
    open_price: float
    gap_pct: float
    gap_category: str       # SWEET_SPOT, EXHAUSTION_RISK, DISCONNECT_TRAP, MODEST, FLAT
    execution_tip: str      # Clear operational advice for the trader
    is_favorable: bool      # True if good risk-reward entry


class GapAnalyzer:
    """Classifies opening price action to protect traders against gap-up exhaustion."""

    @staticmethod
    def evaluate_gap(
        symbol: str,
        open_price: float,
        prev_close: float,
        predicted_direction: str = "bullish",
    ) -> GapEvaluation:
        """Calculate gap percentage and assign actionable execution guidelines."""
        if prev_close <= 0:
            return GapEvaluation(
                symbol=symbol,
                prev_close=0.0,
                open_price=open_price,
                gap_pct=0.0,
                gap_category="FLAT",
                execution_tip="Awaiting opening price action.",
                is_favorable=True,
            )

        gap_pct = round(((open_price - prev_close) / prev_close) * 100.0, 2)
        direction = predicted_direction.lower()

        if "bullish" in direction:
            if gap_pct >= 4.0:
                cat = "EXHAUSTION_RISK"
                tip = f"⚡ Gap-Up Caution (+{gap_pct}%): High exhaustion risk. DO NOT chase market orders. Wait for a 15-min consolidation."
                fav = False
            elif 0.5 <= gap_pct < 4.0:
                cat = "SWEET_SPOT"
                tip = f"🎯 Favorable Gap (+{gap_pct}%): Controlled gap-up allows intraday trend continuation with defined stop-loss below open."
                fav = True
            elif -0.5 < gap_pct < 0.5:
                cat = "FLAT"
                tip = f"Flat Open ({gap_pct:+.1f}%): Catalyst not yet aggressively priced in; monitor volume on first 5-min candle."
                fav = True
            elif gap_pct <= -1.0:
                cat = "DISCONNECT_TRAP"
                tip = f"🔴 Bearish Disconnect ({gap_pct}%): Stock opened DOWN despite positive catalyst. Institutional selling pressure detected — AVOID."
                fav = False
            else:
                cat = "MODEST"
                tip = f"Modest gap ({gap_pct:+0.1f}%)."
                fav = True
        else:  # bearish
            if gap_pct <= -4.0:
                cat = "EXHAUSTION_RISK"
                tip = f"⚡ Gap-Down Caution ({gap_pct}%): Oversold at open. Avoid shorting at day's low; wait for dead-cat bounce."
                fav = False
            elif -4.0 < gap_pct <= -0.5:
                cat = "SWEET_SPOT"
                tip = f"🎯 Favorable Short Gap ({gap_pct}%): Controlled gap-down confirms institutional selling."
                fav = True
            elif gap_pct >= 1.0:
                cat = "DISCONNECT_TRAP"
                tip = f"🟢 Bullish Disconnect (+{gap_pct}%): Stock opened UP despite negative headline. Resilience/absorption detected."
                fav = False
            else:
                cat = "MODEST"
                tip = f"Flat/Modest gap ({gap_pct:+0.1f}%)."
                fav = True

        return GapEvaluation(
            symbol=symbol,
            prev_close=prev_close,
            open_price=open_price,
            gap_pct=gap_pct,
            gap_category=cat,
            execution_tip=tip,
            is_favorable=fav,
        )
