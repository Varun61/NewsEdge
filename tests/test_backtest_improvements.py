"""Tests for intelligence and accuracy enhancements derived from empirical backtesting."""

import pytest
from app.processors.nse_master import get_nse_resolver
from app.intelligence.thematic_engine import get_thematic_engine
from app.intelligence.ollama_provider import OllamaProvider
from app.config import Settings


def test_anil_ambani_adag_not_mapped_to_ril():
    """Verify that Anil Ambani / ADAG enforcement news does NOT resolve to Mukesh Ambani's RIL."""
    resolver = get_nse_resolver()

    # Anil Ambani ADAG probe should NOT map to RELIANCE
    res = resolver.resolve_from_text("ED attaches 2 aircraft in probe against Reliance Anil Ambani Group")
    assert res is None or res.get("symbol") != "RELIANCE"

    # Genuine Reliance Industries news should map to RELIANCE
    res_ril = resolver.resolve_from_text("Reliance Industries Q2 net profit jumps 15% to ₹18,000 crore")
    assert res_ril is not None
    assert res_ril.get("symbol") == "RELIANCE"


def test_irdai_fee_cut_not_marked_as_bearish_casualty():
    """Verify that administrative processing fee cuts do not trigger bearish insurance casualty rules."""
    engine = get_thematic_engine()

    # Administrative fee cut should NOT trigger INSURANCE_COMMISSION_CUT
    headline = "IRDAI cuts processing fee for insurer share transfer approval from Rs 50 lakh to Rs 10 lakh"
    impacts = engine.detect_sector_catalysts(headline)
    bearish_symbols = [imp.symbol for imp in impacts if imp.direction == "bearish"]

    assert "STARHEALTH" not in bearish_symbols
    assert "HDFCLIFE" not in bearish_symbols
    assert "SBILIFE" not in bearish_symbols


def test_low_profit_growth_margin_compression():
    """Verify that modest/single-digit profit growth (<15%) does not get inflated to high impact."""
    provider = OllamaProvider(Settings())

    # V2 Retail scenario: profit up only 6% despite revenue jumping 28%
    headline = "V2 Retail Q2 results: Profit rises 6%, revenue jumps 28% as margins improve"
    res = provider._heuristic_fallback(headline, company_name="V2 Retail Limited", nse_symbol="V2RETAIL", source_urls=[])

    assert res.news_category == "PROFIT_GROWTH"
    # Impact should be moderate (≤ 60), not inflated to strong bullish (80+)
    assert res.impact_score <= 60.0
    assert res.sentiment != "VERY_POSITIVE"


def test_deregulatory_relief_heuristic():
    """Verify that deregulatory fee reductions are classified as positive regulatory approval."""
    provider = OllamaProvider(Settings())

    headline = "IRDAI cuts processing fee for insurer share transfer approval from Rs 50 lakh to Rs 10 lakh"
    res = provider._heuristic_fallback(headline, company_name="HDFC Life Insurance", nse_symbol="HDFCLIFE", source_urls=[])

    assert res.expected_direction == "bullish"
    assert res.news_category == "REGULATORY_APPROVAL"
