"""Tests for objective confidence calibration (pure/offline)."""

from app.intelligence.ai_provider import calibrate_confidence


def test_grounded_quantified_official_boosts():
    # Stock named in headline, hard number, authoritative source.
    c = calibrate_confidence(70, source_credibility=1.0, headline="LT bags ₹4,000 crore order", symbol="LT")
    base = calibrate_confidence(70, source_credibility=0.5, headline="generic market note", symbol="LT")
    assert c > base
    assert c >= 70


def test_ungrounded_symbol_penalised():
    grounded = calibrate_confidence(70, 0.8, "RELIANCE Q2 profit up 20%", "RELIANCE")
    ungrounded = calibrate_confidence(70, 0.8, "Markets rally on global cues", "RELIANCE")
    assert ungrounded < grounded


def test_speculative_language_reduces_confidence():
    firm = calibrate_confidence(75, 0.8, "ABC wins ₹500 crore order", "ABC")
    spec = calibrate_confidence(75, 0.8, "ABC may win order, in talks reportedly", "ABC")
    assert spec < firm


def test_authoritative_source_anchors_timid_model():
    # A timid model number gets lifted by a high-credibility source.
    c = calibrate_confidence(40, source_credibility=1.0, headline="XYZ board approves results", symbol="XYZ")
    assert c > 40


def test_blog_not_inflated_by_overconfident_model():
    c = calibrate_confidence(95, source_credibility=0.3, headline="some vague tip", symbol="")
    assert c < 95


def test_output_always_clamped():
    assert 10.0 <= calibrate_confidence(999, 1.0, "x", "x") <= 95.0
    assert 10.0 <= calibrate_confidence(-50, 0.0, "", "") <= 95.0


def test_handles_bad_input_gracefully():
    assert 10.0 <= calibrate_confidence(None, None, None, None) <= 95.0
