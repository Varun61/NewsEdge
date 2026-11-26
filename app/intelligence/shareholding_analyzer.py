"""Promoter Shareholding and Pledge Risk Intelligence.

Evaluates corporate governance and balance sheet health via equity ownership structure:
- Promoter Pledge Risk: When promoters pledge >20% of their holdings, market volatility
  triggers forced lender liquidations (margin call cascades).
- Promoter Stake Dilution: Continuous stake reduction signals insider skepticism.
- Institutional Inflows: FII and DII stake accumulation confirms institutional backing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("newsedge.intelligence.shareholding")

# Well-known high pledge risk NSE equities tracked for institutional defense
HIGH_PLEDGE_WATCHLIST = {
    "ZEEL": 45.0,
    "GMRINFRA": 38.0,
    "IBULHSGFIN": 42.0,
    "RPOWER": 55.0,
    "JINDALSTEL": 28.0,
    "VEDL": 35.0,
    "SUZLON": 25.0,
    "SPARC": 32.0,
}
# Externalised: data/reference/high_pledge_watchlist.json overrides the default.
from app.processors.reference_data import load_dict as _load_dict
HIGH_PLEDGE_WATCHLIST = _load_dict("high_pledge_watchlist", HIGH_PLEDGE_WATCHLIST)


@dataclass
class ShareholdingEvaluation:
    symbol: str
    pledge_pct: float
    is_high_pledge: bool
    is_promoter_selling: bool
    is_institutional_inflow: bool
    score_modifier: float
    advisory: Optional[str] = None


class ShareholdingAnalyzer:
    """Evaluates promoter pledge and ownership stability for candidates."""

    @classmethod
    def evaluate_health(cls, symbol: str, text: str = "") -> ShareholdingEvaluation:
        """Scan announcement text or reference watchlist for pledge and ownership health."""
        clean_sym = symbol.upper().strip()
        t_lower = text.lower()

        # Check known high-pledge benchmark list
        known_pledge = HIGH_PLEDGE_WATCHLIST.get(clean_sym, 0.0)

        # Check text patterns for pledge disclosures
        pledge_match = re.search(r"promoter\s+pledge\s+(?:at|of|rises\s+to|jumps\s+to|surges\s+to)\s+(\d+(?:\.\d+)?)%", t_lower)
        if pledge_match:
            pledge_val = float(pledge_match.group(1))
        else:
            pledge_val = known_pledge

        is_high_pledge = pledge_val >= 20.0
        is_severe_pledge = pledge_val >= 40.0

        # Check promoter selling/dilution in text
        promoter_dilution_patterns = [
            r"\bpromoters?\s+(?:trim\w*|cut\w*|slash\w*|reduc\w*|dilut\w*)\s+stake\b",
            r"\bpromoter\s+holding\s+(?:drops?|falls?|declines?|slips?)\b",
            r"\bpromoter\s+pledge\s+(?:invoked|called)\b",
        ]
        is_promoter_dilution = any(re.search(pat, t_lower) for pat in promoter_dilution_patterns)

        # Check institutional inflows
        fii_inflow_patterns = [
            r"\bfii\s+(?:raises?|hikes?|increases?|ups?)\s+stake\b",
            r"\bdii\s+(?:raises?|hikes?|increases?|ups?)\s+stake\b",
            r"\bmutual\s+funds?\s+(?:increase|hike|raise)\s+stake\b",
            r"\binstitutional\s+holding\s+rises?\b",
        ]
        is_inst_inflow = any(re.search(pat, t_lower) for pat in fii_inflow_patterns)

        # Calculate modifier
        score_mod = 0.0
        advisories = []

        if is_severe_pledge:
            score_mod -= 25.0
            advisories.append(f"⚠️ Toxic Pledge Alert: Promoter pledged {pledge_val:.1f}% of holding. High risk of lender margin-call liquidation.")
        elif is_high_pledge:
            score_mod -= 18.0
            advisories.append(f"⚠️ High Promoter Pledge ({pledge_val:.1f}%): Lenders hold significant claim on equity.")

        if is_promoter_dilution:
            score_mod -= 14.0
            advisories.append("⚠️ Promoter Stake Dilution: Insiders reducing ownership stake.")

        if is_inst_inflow:
            score_mod += 8.0
            advisories.append("🏛️ Institutional Inflows: FII/DII stake expansion confirmed.")

        return ShareholdingEvaluation(
            symbol=clean_sym,
            pledge_pct=pledge_val,
            is_high_pledge=is_high_pledge,
            is_promoter_selling=is_promoter_dilution,
            is_institutional_inflow=is_inst_inflow,
            score_modifier=score_mod,
            advisory=" | ".join(advisories) if advisories else None,
        )


_shareholding_instance: Optional[ShareholdingAnalyzer] = None


def get_shareholding_analyzer() -> ShareholdingAnalyzer:
    global _shareholding_instance
    if _shareholding_instance is None:
        _shareholding_instance = ShareholdingAnalyzer()
    return _shareholding_instance
