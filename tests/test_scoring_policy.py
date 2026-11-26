"""Tests for the centralised scoring policy (pure/offline)."""

from app.intelligence.scoring_policy import DEFAULT_POLICY, ScoringPolicy


def test_default_cutoffs_match_historical_values():
    p = DEFAULT_POLICY
    assert p.strong_cutoff == 78.0
    assert p.bullish_cutoff == 64.0
    assert p.bearish_cutoff == 60.0
    assert p.watch_cutoff == 46.0
    assert p.min_confidence == 52.0
    assert p.min_confidence_score == 72.0


def test_tier_for_bullish():
    p = ScoringPolicy()
    assert p.tier_for(False, 85) == "strong_bullish"
    assert p.tier_for(False, 70) == "bullish"
    assert p.tier_for(False, 50) == "watch_only"
    assert p.tier_for(False, 40) == "excluded"


def test_tier_for_bearish():
    p = ScoringPolicy()
    assert p.tier_for(True, 85) == "strong_bearish"
    assert p.tier_for(True, 62) == "bearish"
    assert p.tier_for(True, 50) == "watch_only"
    assert p.tier_for(True, 30) == "excluded"


def test_policy_is_overridable():
    strict = ScoringPolicy(strong_cutoff=90.0)
    assert strict.tier_for(False, 85) == "bullish"  # no longer strong under stricter policy
