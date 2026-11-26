"""Tests for the pure classifier cores of the new catalyst sources (offline)."""

from app.collectors.official_collectors.nse_deals import classify_deal
from app.collectors.official_collectors.nse_insider import classify_insider
from app.collectors.official_collectors.fda_collector import map_fda_firm_to_symbol
from app.processors.filing_catalyst import BEARISH, BULLISH, NEUTRAL


# ── Bulk/block deals ─────────────────────────────────────────────────────────

def test_marquee_buy_is_bullish_material():
    d, impact, material, label = classify_deal("GQG Partners Emerging Markets", "BUY", 120.0)
    assert d == BULLISH and material and label == "marquee_accumulation"


def test_promoter_pe_sell_is_bearish_material():
    d, impact, material, label = classify_deal("Blackstone Capital Partners", "SELL", 300.0)
    assert d == BEARISH and material and label == "promoter_pe_offload"


def test_large_unknown_deal_is_context_only():
    d, impact, material, label = classify_deal("XYZ Securities Prop Desk", "BUY", 60.0)
    assert d == NEUTRAL and not material and label == "large_deal"


def test_small_routine_deal_skipped():
    d, impact, material, label = classify_deal("Some Broker", "SELL", 3.0)
    assert label == "routine" and not material


# ── Insider / pledge ─────────────────────────────────────────────────────────

def test_promoter_pledge_is_bearish_material():
    d, cat, impact, material, label = classify_insider("Promoter", "Pledge", 0.0)
    assert d == BEARISH and material and label == "pledge_created"
    assert cat == "PROMOTER_ACTIVITY"


def test_promoter_purchase_is_bullish_material():
    d, cat, impact, material, label = classify_insider("Promoter Group", "Market Purchase", 5.0)
    assert d == BULLISH and material and label == "insider_buy"


def test_promoter_sale_is_bearish():
    d, cat, impact, material, label = classify_insider("Promoter", "Market Sale", 2.0)
    assert d == BEARISH and material and label == "insider_sale"


def test_nonpromoter_small_sale_not_material():
    d, cat, impact, material, label = classify_insider("Designated Person", "Market Sale", 1.0)
    assert not material


def test_nonpromoter_large_buy_is_material():
    d, cat, impact, material, label = classify_insider("Designated Person", "Market Purchase", 50.0)
    assert d == BULLISH and material


# ── USFDA firm mapping ───────────────────────────────────────────────────────

def test_fda_firm_mapping_known():
    assert map_fda_firm_to_symbol("Aurobindo Pharma USA Inc.") == "AUROPHARMA"
    assert map_fda_firm_to_symbol("Dr. Reddy's Laboratories Inc") == "DRREDDY"
    assert map_fda_firm_to_symbol("Zydus Pharmaceuticals (USA) Inc.") == "ZYDUSLIFE"


def test_fda_firm_mapping_unknown_is_none():
    assert map_fda_firm_to_symbol("Pfizer Inc.") is None
    assert map_fda_firm_to_symbol("") is None
