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
