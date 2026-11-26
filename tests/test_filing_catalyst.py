"""Tests for the exchange-filing catalyst parser.

Pure/offline: no network, no DB. Validates that NSE/BSE filing categories map to
the right NewsCategory, direction, materiality, and extracted numbers.
"""

from app.processors.filing_catalyst import (
    BEARISH,
    BULLISH,
    NEUTRAL,
    classify_filing,
)


# ── Order wins ──────────────────────────────────────────────────────────────

def test_large_order_win_is_bullish_high_impact():
    c = classify_filing(
        subject="Awarding of Order/Receipt of Order",
        attachment_text="Company bags order worth Rs 6,500 crore from NHAI for highway construction.",
    )
    assert c.news_category == "ORDER_WIN"
    assert c.direction == BULLISH
    assert c.order_value_cr == 6500.0
    assert c.impact_hint >= 88.0
    assert c.is_material


def test_unquantified_order_win_is_capped():
    c = classify_filing(
        subject="Awarding of Order/Receipt of Order",
        attachment_text="Company secures order for supply of equipment. Value undisclosed.",
    )
    assert c.news_category == "ORDER_WIN"
    assert c.direction == BULLISH
    assert c.order_value_cr is None
    assert c.impact_hint <= 60.0
    assert "unquantified" in c.tags


def test_small_order_win_modest_impact():
    c = classify_filing(
        subject="Receipt of Order",
        attachment_text="Received a work order worth Rs 45 crore.",
    )
    assert c.news_category == "ORDER_WIN"
    assert c.order_value_cr == 45.0
    assert c.impact_hint <= 70.0


# ── Financial results ─────────────────────────────────────────────────────────

def test_strong_profit_growth_results_bullish():
    c = classify_filing(
        subject="Financial Results",
        attachment_text="Net profit rises 42% YoY to Rs 800 crore; revenue up 28%.",
    )
    assert c.news_category == "QUARTERLY_RESULTS"
    assert c.direction == BULLISH
    assert c.profit_growth_pct == 42.0
    assert c.impact_hint >= 78.0


def test_profit_decline_results_is_warning_bearish():
    c = classify_filing(
        subject="Financial Results",
        attachment_text="Net profit falls 30% YoY on margin pressure.",
    )
    assert c.news_category == "PROFIT_WARNING"
    assert c.direction == BEARISH
    assert c.profit_growth_pct == -30.0


def test_flat_growth_results_is_neutral_deceleration():
    c = classify_filing(
        subject="Financial Results",
        attachment_text="Net profit rises 5% YoY; broadly flat quarter.",
    )
    assert c.news_category == "QUARTERLY_RESULTS"
    assert c.direction == NEUTRAL
    assert c.impact_hint <= 55.0


def test_results_filed_without_numbers_is_neutral_placeholder():
    c = classify_filing(
        subject="Financial Results",
        attachment_text="Outcome of board meeting: audited financial results approved.",
    )
    assert c.news_category == "QUARTERLY_RESULTS"
    assert c.direction == NEUTRAL


# ── Regulatory / governance ──────────────────────────────────────────────────

def test_sebi_penalty_is_bearish_high_conviction():
    c = classify_filing(
        subject="Disclosure under SEBI Regulation 30",
        attachment_text="SEBI order imposing penalty of Rs 25 crore for disclosure lapses.",
    )
    assert c.news_category == "REGULATORY_ACTION"
    assert c.direction == BEARISH
    assert c.penalty_amount_cr == 25.0
    assert c.confidence >= 90.0


def test_fraud_governance_shock_is_bearish():
    c = classify_filing(
        subject="Disclosure under Regulation 30",
        attachment_text="Company discloses forensic audit initiated by lenders.",
    )
    assert c.news_category == "FRAUD_OR_GOVERNANCE"
    assert c.direction == BEARISH
    assert c.impact_hint >= 85.0


def test_key_person_resignation_is_bearish():
    c = classify_filing(
        subject="Resignation",
        attachment_text="Resignation of Chief Financial Officer with immediate effect.",
    )
    assert c.news_category == "MANAGEMENT_CHANGE"
    assert c.direction == BEARISH
    assert c.is_material


def test_routine_appointment_is_immaterial():
    c = classify_filing(
        subject="Appointment",
        attachment_text="Appointment of Company Secretary and Compliance Officer.",
    )
    assert c.is_material is False


# ── Capital actions ──────────────────────────────────────────────────────────

def test_buyback_is_bullish():
    c = classify_filing(subject="Buy back of Securities", attachment_text="Board approves buyback of equity shares.")
    assert c.news_category == "BUYBACK"
    assert c.direction == BULLISH


def test_acquisition_is_bullish():
    c = classify_filing(
        subject="Acquisition",
        attachment_text="Company to acquire 100% stake in a renewable energy firm.",
    )
    assert c.news_category == "ACQUISITION"
    assert c.direction == BULLISH


# ── Noise gating ─────────────────────────────────────────────────────────────

def test_trading_window_closure_is_noise():
    c = classify_filing(
        subject="Trading Window",
        attachment_text="Closure of trading window for designated persons.",
    )
    assert c.is_material is False
    assert c.impact_hint <= 15.0


def test_newspaper_publication_is_noise():
    c = classify_filing(
        subject="Newspaper Publication",
        attachment_text="Newspaper advertisement of financial results published.",
    )
    assert c.is_material is False


def test_board_meeting_intimation_is_immaterial():
    c = classify_filing(
        subject="Board Meeting Intimation",
        attachment_text="Intimation of board meeting to be held on 10th.",
    )
    assert c.is_material is False


# ── Number extraction helpers ────────────────────────────────────────────────

def test_usd_order_value_converted_to_crore():
    c = classify_filing(
        subject="Receipt of Order",
        attachment_text="Company wins order worth USD 120 million.",
    )
    assert c.order_value_cr is not None
    # 120 million USD * 83 / 10  ~= 996 cr
    assert 900 <= c.order_value_cr <= 1100
