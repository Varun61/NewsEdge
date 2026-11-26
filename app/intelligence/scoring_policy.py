"""Centralised scoring policy — the single source of truth for the thresholds
and tier cutoffs the scoring engine uses.

Previously these numbers were scattered as literals throughout
``scoring_engine.score_event`` (and duplicated in the old backtest), which made
the policy impossible to see in one place or tune safely. They now live here as
named, documented fields. Values are unchanged from the original inline literals
(this is a behaviour-preserving extraction).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringPolicy:
    # ── Actionable tier cutoffs (final 0-100 score) ─────────────────────
    strong_cutoff: float = 78.0      # STRONG_BULLISH / STRONG_BEARISH
    bullish_cutoff: float = 64.0     # BULLISH
    bearish_cutoff: float = 60.0     # BEARISH
    watch_cutoff: float = 46.0       # WATCH_ONLY (below this -> EXCLUDED)

    # ── Minimum-confidence gate ─────────────────────────────────────────
    min_confidence: float = 52.0         # below this + low score -> EXCLUDED
    min_confidence_score: float = 72.0   # score needed to survive low confidence

    # ── "High conviction required to override a penalty" thresholds ─────
    override_body_only: float = 86.0         # body-only mention needs this to stay actionable
    override_unquantified_order: float = 78.0
    override_buyback: float = 78.0
    override_growth_quality: float = 78.0    # subpar growth / divergence / exceptional items
    override_counter_trend: float = 80.0     # bullish call against a structural downtrend
    override_high_pledge: float = 82.0

    def tier_for(self, direction_is_negative: bool, score: float) -> str:
        """Map a final score to an actionable tier name (no penalty gating).

        Returns one of: strong_bullish, bullish, strong_bearish, bearish,
        watch_only, excluded. The scoring engine still layers its penalty gates
        on top of this.
        """
        if direction_is_negative:
            if score >= self.strong_cutoff:
                return "strong_bearish"
            if score >= self.bearish_cutoff:
                return "bearish"
            return "watch_only" if score >= self.watch_cutoff else "excluded"
        if score >= self.strong_cutoff:
            return "strong_bullish"
        if score >= self.bullish_cutoff:
            return "bullish"
        return "watch_only" if score >= self.watch_cutoff else "excluded"


DEFAULT_POLICY = ScoringPolicy()
