"""Tests for objective confidence calibration (pure/offline)."""

from app.intelligence.ai_provider import calibrate_confidence, is_stale_recap


def test_stale_recap_detects_preview_and_review():
    assert is_stale_recap("TCS Q2 results review: should you buy the stock?")
    assert is_stale_recap("Infosys earnings preview: what to expect")
    assert is_stale_recap("Top 5 stocks to watch today")
    assert is_stale_recap("IT stocks in focus ahead of Q2 results")
    assert is_stale_recap("Reliance share price: key takeaways from AGM")


def test_stale_recap_allows_fresh_catalyst():
    assert not is_stale_recap("L&T bags Rs 4,000 crore order from NHAI")
    assert not is_stale_recap("SEBI imposes Rs 25 crore penalty on XYZ")
    assert not is_stale_recap("Infosys Q2 net profit rises 12% YoY to Rs 6,500 crore")


def test_stale_recap_question_and_analysis_headlines():
    assert is_stale_recap("Why is SanDisk stock falling despite surging profits?")
    assert is_stale_recap("Can Siemens data centre push power its next leg of growth?")
    assert is_stale_recap("Explained: What the new F&O rules mean for traders")
    # A plain factual catalyst (no '?', no analysis markers) stays actionable
    assert not is_stale_recap("Siemens bags Rs 5,000 crore metro order")


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
