"""Tests for sector-wide thematic intelligence, company knowledge, and historical reactions."""

from app.processors.company_knowledge import get_company_profile
from app.intelligence.thematic_engine import get_thematic_engine
from app.intelligence.historical_reactions import match_historical_reaction


def test_company_knowledge_profile():
    # 1. PB Fintech profile
    prof_pb = get_company_profile("POLICYBZR")
    assert prof_pb is not None
    assert "Policybazaar" in prof_pb.business_summary or "insurance broker" in prof_pb.business_summary.lower()
    assert any("commission" in cat.lower() for cat in prof_pb.negative_catalysts)

    # 2. RVNL profile
    prof_rvnl = get_company_profile("RVNL")
    assert prof_rvnl is not None
    assert "railway" in prof_rvnl.business_summary.lower()
    assert any("railway" in cat.lower() for cat in prof_rvnl.positive_catalysts)

    # 3. Small and Micro Cap Profiles
    from app.processors.company_knowledge import get_profiles_by_market_cap
    small_caps = get_profiles_by_market_cap("small_cap")
    micro_caps = get_profiles_by_market_cap("micro_cap")
    mid_caps = get_profiles_by_market_cap("mid_cap")

    assert len(small_caps) >= 10
    assert len(micro_caps) >= 3
    assert len(mid_caps) >= 10

    # Kernex (micro cap Kavach), Paras (micro cap defence), Zen Technologies (small cap anti-drone)
    assert any(p.symbol == "KERNEX" for p in micro_caps)
    assert any(p.symbol == "PARAS" for p in micro_caps)
    assert any(p.symbol == "ZENTEC" for p in small_caps)
    assert any(p.symbol == "BORORENEW" for p in small_caps)


def test_thematic_railway_capex_detection():
    engine = get_thematic_engine()

    # Case: Government allocates massive capex to railway sector
    headline = "Govt decides to invest 100,000 crores in railway modernization and track expansion"
    impacts = engine.detect_sector_catalysts(headline)

    assert len(impacts) > 0
    symbols = [imp.symbol for imp in impacts]
    directions = {imp.symbol: imp.direction for imp in impacts}

    # Should identify top railway players as bullish
    assert "RVNL" in symbols
    assert "IRFC" in symbols
    assert "TITAGARH" in symbols
    assert directions["RVNL"] == "bullish"
    assert directions["IRFC"] == "bullish"
    assert impacts[0].impact_score >= 80.0


def test_thematic_insurance_commission_cut_detection():
    engine = get_thematic_engine()

    # Case: IRDAI decides to cut commission on insurance policies
    headline = "IRDAI proposes cutting commission on life insurance policies and raising surrender values"
    impacts = engine.detect_sector_catalysts(headline)

    assert len(impacts) > 0
    symbols = [imp.symbol for imp in impacts]
    directions = {imp.symbol: imp.direction for imp in impacts}

    # Should identify Policybazaar (PB Fintech) and life insurers as bearish casualties
    assert "POLICYBZR" in symbols
    assert "HDFCLIFE" in symbols
    assert directions["POLICYBZR"] == "bearish"
    assert directions["HDFCLIFE"] == "bearish"
    assert impacts[0].impact_score >= 80.0


def test_thematic_city_gas_apm_cut():
    engine = get_thematic_engine()

    headline = "Govt slashes APM domestic gas allocation to city gas distributors by 20%"
    impacts = engine.detect_sector_catalysts(headline)

    assert len(impacts) > 0
    symbols = [imp.symbol for imp in impacts]
    assert "IGL" in symbols
    assert "MGL" in symbols
    assert any(imp.direction == "bearish" for imp in impacts if imp.symbol == "IGL")


def test_thematic_crude_oil_asymmetry():
    engine = get_thematic_engine()

    # When crude surges: ONGC benefits, IOC / Indigo suffer
    headline = "Brent crude oil prices surge above $90 as Middle East tensions escalate"
    impacts = engine.detect_sector_catalysts(headline)

    assert len(impacts) > 0
    bullish_syms = [imp.symbol for imp in impacts if imp.direction == "bullish"]
    bearish_syms = [imp.symbol for imp in impacts if imp.direction == "bearish"]

    assert "ONGC" in bullish_syms
    assert "IOC" in bearish_syms or "INDIGO" in bearish_syms


def test_historical_reaction_profiles():
    # 1. SEBI regulatory action
    profile_sebi = match_historical_reaction("SEBI imposes ₹1 crore penalty for regulatory lapse")
    assert profile_sebi is not None
    assert profile_sebi.expected_direction == "bearish"
    assert profile_sebi.directional_conviction_pct >= 80.0

    # 2. Major railway capex
    profile_rail = match_historical_reaction("Cabinet clears 100000 crore railway capex package")
    assert profile_rail is not None
    assert profile_rail.expected_direction == "bullish"
    assert profile_rail.historical_score >= 80.0


def test_thematic_custom_rule_learning(tmp_path):
    engine = get_thematic_engine()
    success = engine.learn_rule(
        theme_title="Drone Surveillance Procurement",
        trigger_patterns=[r"\b(?:drone|uav|anti-drone)\b.*\b(?:procurement|tender|army|defence)\b"],
        bullish_beneficiaries=[
            ("IDEA_FORGE", "Pure play drone manufacturer gaining from armed forces contracts.", 88.0),
            ("ZENTEC", "Anti-drone countermeasure tech leader with expanding order book.", 87.0),
        ],
        bearish_casualties=[],
        theme_id="DEFENCE_DRONES_TEST",
    )
    assert success is True

    # Test detection on a headline without any company name mentioned
    impacts = engine.detect_sector_catalysts("Indian Army issues mega tender for high-altitude surveillance drone procurement")
    symbols = [imp.symbol for imp in impacts]
    assert "IDEA_FORGE" in symbols or "ZENTEC" in symbols
