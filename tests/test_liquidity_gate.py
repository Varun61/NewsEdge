"""Tests for the tradeable-liquidity gate (pure/offline)."""

from app.intelligence.liquidity_gate import evaluate_liquidity


def test_fno_stock_is_liquid_no_penalty():
    a = evaluate_liquidity("RELIANCE")
    assert a.tier == "FNO"
    assert a.score_modifier == 0.0
    assert a.is_tradeable


def test_large_cap_category_no_penalty():
    a = evaluate_liquidity("SOMELARGE", market_cap_category="large_cap")
    assert a.tier == "LARGE"
    assert a.score_modifier == 0.0
    assert a.is_tradeable


def test_small_cap_penalised_but_tradeable():
    a = evaluate_liquidity("SMALLX", market_cap_category="small_cap")
    assert a.tier == "SMALL"
    assert a.score_modifier < 0
    assert a.is_tradeable


def test_micro_cap_is_gated_untradeable():
    a = evaluate_liquidity("MICROX", market_cap_category="micro_cap")
    assert a.tier == "MICRO"
    assert a.is_tradeable is False
    assert a.score_modifier <= -10.0


def test_tier_inferred_from_market_cap_when_no_category():
    assert evaluate_liquidity("X", market_cap_cr=50_000).tier == "LARGE"
    assert evaluate_liquidity("X", market_cap_cr=8_000).tier == "MID"
    assert evaluate_liquidity("X", market_cap_cr=2_000).tier == "SMALL"
    micro = evaluate_liquidity("X", market_cap_cr=400)
    assert micro.tier == "MICRO"
    assert micro.is_tradeable is False


def test_unknown_is_mild_caution():
    a = evaluate_liquidity("TOTALLYUNKNOWN")
    assert a.tier == "UNKNOWN"
    assert a.is_tradeable
    assert a.score_modifier < 0


def test_fno_membership_overrides_category():
    # Even if mislabelled micro, an F&O name is liquid.
    a = evaluate_liquidity("TATASTEEL", market_cap_category="micro_cap")
    assert a.tier == "FNO"
    assert a.is_tradeable
