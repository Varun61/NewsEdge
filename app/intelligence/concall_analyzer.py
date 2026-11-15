"""Automated Earnings Conference Call and Management Guidance Analyzer.

Extracts forward-looking institutional metrics from earnings concalls:
- Forward Guidance: Raised, Maintained, or Lowered
- Margin Trajectory: Expansion vs Compression
- Demand & Volume Commentary: Robust/Buoyant vs Sluggish/Challenging
- Capex & Execution Timeline: On-track vs Delayed
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("newsedge.intelligence.concall")


@dataclass
class ConcallEvaluation:
    guidance_sentiment: str     # POSITIVE, NEUTRAL, CAUTIOUS, NEGATIVE
    score_modifier: float       # -18.0 to +10.0
    detected_signals: List[str] = field(default_factory=list)
    key_quotes: List[str] = field(default_factory=list)
    is_guidance_cut: bool = False
    is_margin_warning: bool = False


class ConcallAnalyzer:
    """Evaluates earnings conference calls and management commentary."""

    GUIDANCE_RAISE_PATTERNS = [
        r"\b(?:raise\w*|hike\w*|upgrade\w*)\s+(?:[\w-]+\s+){0,3}guidance\b",
        r"\bguidance\s+(?:raised|hiked|upgraded|revised\s+upward)",
        r"\bupward\s+revision\s+in\s+guidance\b",
        r"\bsees?\s+higher\s+(?:revenue|growth|margins?|profit)\b",
    ]

    GUIDANCE_CUT_PATTERNS = [
        r"\b(?:cut\w*|lower\w*|slash\w*|reduce\w*)\s+(?:[\w-]+\s+){0,3}guidance\b",
        r"\bguidance\s+(?:cut|lowered|slashed|reduced|downgraded)",
        r"\bdownward\s+revision\s+in\s+guidance\b",
        r"\bcuts?\s+(?:growth|revenue|margin|ebitda)\s+forecast\b",
    ]

    MARGIN_EXPANSION_PATTERNS = [
        r"\bmargins?\s+(?:expand\w*|widen\w*|improve\w*|edge\w*\s+up)",
        r"\bebitda\s+margin\s+(?:up|expands?|widens?|improves?)",
        r"\boperating\s+leverage\b",
        r"\bpricing\s+power\b",
        r"\bbetter\s+realisations?\b",
    ]

    MARGIN_COMPRESSION_PATTERNS = [
        r"\bmargins?\s+(?:contract\w*|shrink\w*|narrow\w*|drop\w*|fall\w*|decline\w*|sinks?)",
        r"\bmargin\s+pressure\b",
        r"\bebitda\s+margin\s+(?:down|contracts?|drops?|falls?)",
        r"\bpricing\s+pressure\b",
        r"\brising\s+input\s+costs?\b",
        r"\bhigh\s+feedstock\s+cost\b",
    ]

    DEMAND_BULLISH_PATTERNS = [
        r"\brobust\s+(?:demand|order\s*book|visibility|pipeline|inflows?)",
        r"\bstrong\s+(?:demand|order\s*book|visibility|inflows?|traction)",
        r"\brecord\s+(?:order\s*book|inflows?|dispatches|sales|volume)",
        r"\bhealthy\s+(?:pipeline|visibility|order\s*inflow)",
        r"\bdouble[- ]digit\s+volume\s+growth\b",
    ]

    DEMAND_BEARISH_PATTERNS = [
        r"\bweak\s+(?:demand|order\s*book|inflow|traction|macro)",
        r"\bdemand\s+slowdown\b",
        r"\bsluggish\s+(?:demand|sales|volume|offtake|recovery)",
        r"\bdelayed\s+(?:capex|orders?|decisions?|tenders?)",
        r"\bdeferrals?\s+by\s+clients?\b",
        r"\bmacro\s+headwinds?\b",
        r"\bfurloughs?\b",
        r"\binventory\s+(?:overhang|pileup|destocking)\b",
    ]

    def analyze_text(self, text: str) -> ConcallEvaluation:
        """Scan concall text or management commentary and return structural evaluation."""
        if not text:
            return ConcallEvaluation(guidance_sentiment="NEUTRAL", score_modifier=0.0)

        t_lower = text.lower()
        signals = []
        score_mod = 0.0
        is_cut = False
        is_margin_warn = False

        # 1. Guidance changes
        if any(re.search(pat, t_lower) for pat in self.GUIDANCE_RAISE_PATTERNS):
            signals.append("Guidance raised/upgraded by management")
            score_mod += 10.0
        elif any(re.search(pat, t_lower) for pat in self.GUIDANCE_CUT_PATTERNS):
            signals.append("Guidance cut/lowered by management")
            score_mod -= 18.0
            is_cut = True

        # 2. Margin trajectory
        if any(re.search(pat, t_lower) for pat in self.MARGIN_COMPRESSION_PATTERNS):
            signals.append("Margin compression/pricing pressure flagged")
            score_mod -= 14.0
            is_margin_warn = True
        elif any(re.search(pat, t_lower) for pat in self.MARGIN_EXPANSION_PATTERNS):
            signals.append("Margin expansion/operating leverage noted")
            score_mod += 6.0

        # 3. Demand and volume commentary
        if any(re.search(pat, t_lower) for pat in self.DEMAND_BEARISH_PATTERNS):
            signals.append("Demand slowdown or macro headwinds mentioned")
            score_mod -= 12.0
        elif any(re.search(pat, t_lower) for pat in self.DEMAND_BULLISH_PATTERNS):
            signals.append("Robust demand and strong order book visibility")
            score_mod += 6.0

        # Overall sentiment
        if is_cut or score_mod <= -14.0:
            sentiment = "NEGATIVE"
        elif score_mod < 0.0:
            sentiment = "CAUTIOUS"
        elif score_mod >= 8.0:
            sentiment = "POSITIVE"
        else:
            sentiment = "NEUTRAL"

        return ConcallEvaluation(
            guidance_sentiment=sentiment,
            score_modifier=max(-25.0, min(15.0, score_mod)),
            detected_signals=signals,
            is_guidance_cut=is_cut,
            is_margin_warning=is_margin_warn,
        )


_concall_instance: Optional[ConcallAnalyzer] = None


def get_concall_analyzer() -> ConcallAnalyzer:
    global _concall_instance
    if _concall_instance is None:
        _concall_instance = ConcallAnalyzer()
    return _concall_instance
