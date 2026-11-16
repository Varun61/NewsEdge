"""Unit tests for the 5 institutional-grade drastic improvements.

1. Technical Trend Alignment (20/50 EMA Filter)
2. Pre-Market Opening Gap & Microstructure Gate
3. Brokerage Radar & Analyst Consensus Calls
4. Automated Concall & Management Guidance Extractor
5. NSE F&O Derivatives Barriers & Option Wall Intelligence
"""

from __future__ import annotations

import pytest

from app.intelligence.technical_trend import TechnicalTrendAnalyzer, TrendEvaluation
from app.intelligence.gap_analyzer import GapAnalyzer, GapEvaluation
from app.intelligence.concall_analyzer import ConcallAnalyzer, get_concall_analyzer
from app.intelligence.derivatives_context import DerivativesContextAnalyzer, get_derivatives_context_analyzer
from app.collectors.news_collectors.brokerage_radar import BrokerageRadarCollector


def test_technical_trend_ema_calculation():
    analyzer = TechnicalTrendAnalyzer()
    # 25 days of monotonically increasing prices
    prices = [100.0 + i * 2.0 for i in range(30)]
    ema20 = analyzer._calculate_ema(prices, 20)
    assert ema20 > 100.0
    assert ema20 < prices[-1]


def test_technical_trend_directional_modifiers():
    analyzer = TechnicalTrendAnalyzer()

    # 1. Strong uptrend + bullish direction = bonus
    base_up = TrendEvaluation(
        symbol="RELIANCE",
        current_price=2800.0,
        ema_20=2750.0,
        ema_50=2700.0,
        trend_state="STRONG_UPTREND",
        score_modifier=0.0,
        trend_label="Structural Uptrend",
    )
    up_eval = analyzer._apply_direction(base_up, "bullish")
    assert up_eval.score_modifier == +8.0
    assert up_eval.warning is None

    # 2. Strong downtrend + bullish direction = penalty & warning
    base_down = TrendEvaluation(
        symbol="ASIANPAINT",
        current_price=2400.0,
        ema_20=2500.0,
        ema_50=2600.0,
        trend_state="STRONG_DOWNTREND",
        score_modifier=0.0,
        trend_label="Structural Downtrend",
    )
    down_eval = analyzer._apply_direction(base_down, "bullish")
    assert down_eval.score_modifier == -14.0
    assert "Counter-Trend Bounce Risk" in down_eval.warning

    # 3. Strong downtrend + bearish direction = breakdown velocity bonus
    bear_eval = analyzer._apply_direction(base_down, "bearish")
    assert bear_eval.score_modifier == +8.0


def test_gap_analyzer_classification():
    # 1. Sweet spot gap (+1.5%)
    eval_sweet = GapAnalyzer.evaluate_gap("LT", open_price=3552.5, prev_close=3500.0, predicted_direction="bullish")
    assert eval_sweet.gap_category == "SWEET_SPOT"
    assert eval_sweet.is_favorable is True
    assert "Favorable Gap" in eval_sweet.execution_tip

    # 2. Exhaustion gap (+5.2%)
    eval_exhaust = GapAnalyzer.evaluate_gap("TCS", open_price=4208.0, prev_close=4000.0, predicted_direction="bullish")
    assert eval_exhaust.gap_category == "EXHAUSTION_RISK"
    assert eval_exhaust.is_favorable is False
    assert "DO NOT chase" in eval_exhaust.execution_tip

    # 3. Disconnect trap (stock opened down -2.5% despite bullish catalyst)
    eval_trap = GapAnalyzer.evaluate_gap("INFY", open_price=1755.0, prev_close=1800.0, predicted_direction="bullish")
    assert eval_trap.gap_category == "DISCONNECT_TRAP"
    assert eval_trap.is_favorable is False
    assert "Bearish Disconnect" in eval_trap.execution_tip


def test_concall_analyzer_signals():
    analyzer = get_concall_analyzer()

    # 1. Guidance raised + margin expansion
    text_bullish = (
        "In the Q2 earnings call, management raised full-year revenue guidance to 18% "
        "and noted operating leverage with margins expanding 150 bps on robust demand."
    )
    eval_bullish = analyzer.analyze_text(text_bullish)
    assert eval_bullish.guidance_sentiment == "POSITIVE"
    assert eval_bullish.score_modifier > 0
    assert any("Guidance raised" in s for s in eval_bullish.detected_signals)
    assert any("Margin expansion" in s for s in eval_bullish.detected_signals)

    # 2. Guidance cut + pricing pressure
    text_bearish = (
        "Management slashed FY27 guidance citing severe demand slowdown in export markets "
        "and margin pressure due to high input costs."
    )
    eval_bearish = analyzer.analyze_text(text_bearish)
    assert eval_bearish.guidance_sentiment == "NEGATIVE"
    assert eval_bearish.is_guidance_cut is True
    assert eval_bearish.is_margin_warning is True
    assert eval_bearish.score_modifier <= -18.0


def test_derivatives_fno_barriers():
    analyzer = get_derivatives_context_analyzer()

    # 1. Non-F&O stock
    res_non_fno = analyzer.evaluate_derivatives_barriers("UNKNOWN_SME", 150.0)
    assert res_non_fno.is_fno is False
    assert res_non_fno.nearest_call_resistance is None

    # 2. F&O stock: RELIANCE at ₹2,840 (step = 100)
    # Next call strike = 2900 (+2.11% away), Put support = 2800
    res_ril = analyzer.evaluate_derivatives_barriers("RELIANCE", 2840.0, "bullish")
    assert res_ril.is_fno is True
    assert res_ril.nearest_call_resistance == 2900.0
    assert res_ril.nearest_put_support == 2800.0
    assert res_ril.advisory is not None
    assert "F&O" in res_ril.advisory or "resistance" in res_ril.advisory.lower()


def test_brokerage_radar_collector_init():
    collector = BrokerageRadarCollector()
    assert collector.source_name == "Brokerage Radar"
    assert collector.enabled is True
    assert collector.credibility_score >= 0.85


def test_trade_playbook_levels():
    from app.intelligence.trade_playbook import TradePlaybookCalculator
    # Bullish playbook for stock at ₹3,500 (ATR = 77)
    pb_bull = TradePlaybookCalculator.calculate_playbook("LT", 3500.0, "BULLISH")
    assert pb_bull.direction == "BULLISH"
    assert pb_bull.stop_loss < 3500.0
    assert pb_bull.target_1 > 3500.0
    assert pb_bull.target_2 > pb_bull.target_1
    assert "Entry:" in pb_bull.summary_text
    assert "SL:" in pb_bull.summary_text

    # Bearish playbook for stock at ₹1,000
    pb_bear = TradePlaybookCalculator.calculate_playbook("INFY", 1000.0, "BEARISH")
    assert pb_bear.direction == "BEARISH"
    assert pb_bear.stop_loss > 1000.0
    assert pb_bear.target_1 < 1000.0
    assert pb_bear.target_2 < pb_bear.target_1
    assert "Short:" in pb_bear.summary_text


def test_bulk_deals_marquee_buyer_and_promoter_selling():
    from app.intelligence.bulk_deals_analyzer import get_bulk_deals_analyzer
    analyzer = get_bulk_deals_analyzer()

    # 1. Marquee institutional buyer (GQG Partners buys)
    headline_buy = "GQG Partners buys 1.2 crore shares of GMR Airports in block deal"
    eval_buy = analyzer.evaluate_deal(headline_buy)
    assert eval_buy.is_institutional_buying is True
    assert eval_buy.score_modifier == +12.0
    assert "Marquee Institutional Accumulation" in eval_buy.advisory

    # 2. Promoter stake sale (Supply Overhang)
    headline_sell = "Promoter sells 3.5% stake in Amber Enterprises via block deal at discount"
    eval_sell = analyzer.evaluate_deal(headline_sell)
    assert eval_sell.is_promoter_selling is True
    assert eval_sell.score_modifier == -20.0
    assert "Supply Overhang" in eval_sell.advisory


def test_shareholding_pledge_risk_and_fii_inflows():
    from app.intelligence.shareholding_analyzer import get_shareholding_analyzer
    analyzer = get_shareholding_analyzer()

    # 1. High pledge stock from benchmark list (ZEEL 45% pledge)
    eval_zeel = analyzer.evaluate_health("ZEEL")
    assert eval_zeel.is_high_pledge is True
    assert eval_zeel.score_modifier <= -18.0
    assert "Pledge" in eval_zeel.advisory

    # 2. Promoter pledge disclosure in text
    eval_pledge_txt = analyzer.evaluate_health("XYZ", "Corporate governance update: promoter pledge rises to 35% of holding")
    assert eval_pledge_txt.is_high_pledge is True
    assert eval_pledge_txt.score_modifier <= -18.0

    # 3. Institutional inflows (FII raises stake)
    eval_fii = analyzer.evaluate_health("RELIANCE", "Q2 shareholding pattern: FII raises stake by 2.4%")
    assert eval_fii.is_institutional_inflow is True
    assert eval_fii.score_modifier == +8.0
    assert "Institutional Inflows" in eval_fii.advisory


def test_tnpl_state_name_not_matched_from_air_purifier_article():
    """Verify that state names in article bodies do NOT match equities like TNPL."""
    from app.processors.nse_master import get_nse_resolver
    resolver = get_nse_resolver()
    headline = "Air purifier sales surge as Delhi-NCR AQI deteriorates; demand spreads beyond traditional markets"
    body = "Demand spreads beyond traditional markets, including Maharashtra, Karnataka, Tamil Nadu and Telangana."
    match = resolver.resolve_from_text(headline, body)
    # Must NOT match TNPL or any company based on state names
    if match:
        assert match["symbol"] != "TNPL"


def test_comparative_benchmark_not_resolved_as_subject():
    """Verify that benchmark comparative companies mentioned after 'than/rivals' are not picked."""
    from app.processors.nse_master import get_nse_resolver
    resolver = get_nse_resolver()
    headline = "Meet the smallcap lender with faster profit growth and a lower valuation than Tata Capital"
    match = resolver.resolve_from_text(headline, "")
    if match:
        assert match["symbol"] != "TATACAP"


def test_telegram_formatter_guaranteed_clickable_links():
    """Verify that telegram candidate cards always contain a valid clickable link."""
    from app.database.models import StockAnalysis, CandidateClassification, NewsEvent, Company
    from app.reporting.telegram_formatter import TelegramFormatter

    comp = Company(id=1, nse_symbol="ZENTEC", company_name="Zen Technologies Limited")
    event = NewsEvent(
        id=1,
        primary_headline="Rs 20,000 cr military drone opportunity: 2 defence stocks",
        event_hash="hash_zentec_test_123",
        financial_materiality="[Defence Theme] Drone opportunity",
        impact_score=78.0,
        article_links=[],  # Empty article links!
    )
    analysis = StockAnalysis(
        id=1,
        news_event_id=1,
        company_id=1,
        overall_score=77.0,
        classification=CandidateClassification.BULLISH,
    )
    analysis.company = comp
    analysis.news_event = event

    card_lines = TelegramFormatter._format_candidate_card(analysis, 1, is_bullish=True)
    card_text = "\n".join(card_lines)
    assert ' • <a href="https://' in card_text
    assert "LINK</a>" in card_text


def test_thematic_secondary_basket_gated_to_watch_only(session):
    """Verify secondary basket thematic events are classified as WATCH_ONLY rather than BULLISH."""
    from app.intelligence.scoring_engine import ScoringEngine
    from app.intelligence.ai_provider import ClassificationResult
    from app.database.models import NewsEvent, Company, CandidateClassification
    from app.database.repository import Repository

    comp = Repository.create_company(
        session,
        nse_symbol="ZENTEC",
        company_name="Zen Technologies Limited",
        sector="Capital Goods",
        industry="Anti-Drone",
        annual_revenue=500.0,
        is_active=True,
    )
    session.flush()

    event = NewsEvent(
        primary_headline="Rs 20,000 cr military drone opportunity: 2 defence stocks",
        event_hash="hash_thematic_drone_999",
        primary_company_id=comp.id,
        financial_materiality="[Defence Theme] Secondary basket thematic catalyst",
        impact_score=80.0,
        confidence=85.0,
        expected_direction="bullish",
    )
    session.add(event)
    session.flush()

    classification = ClassificationResult(
        company_name=comp.company_name,
        nse_symbol=comp.nse_symbol,
        news_category="ORDER_WIN",
        sentiment="VERY_POSITIVE",
        impact_score=80.0,
        confidence=85.0,
        financial_materiality="[Defence Theme] Secondary basket thematic catalyst",
        expected_direction="bullish",
    )

    from app.config import get_settings
    scoring = ScoringEngine(get_settings())
    analysis = scoring.score_event(event, classification, 80.0, session)
    assert analysis is not None
    # Must be gated to WATCH_ONLY, never actionable BULLISH or STRONG_BULLISH
    assert analysis.classification == CandidateClassification.WATCH_ONLY


