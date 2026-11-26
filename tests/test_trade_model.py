"""Tests for the backtesting trade/cost/statistics core (pure/offline)."""

import math

from app.backtesting.trade_model import (
    Bar,
    CostModel,
    aggregate,
    simulate_trade,
    wilson_interval,
)


# ── Fill realism ─────────────────────────────────────────────────────────────

def test_long_entered_at_open_not_prev_close():
    # Stock gapped up +5% overnight, then open->close only +1%.
    bar = Bar(prev_close=100.0, open=105.0, high=107.0, low=104.0, close=106.05)
    r = simulate_trade("bullish", bar, CostModel(slippage_bps=0, brokerage_bps=0, exchange_bps=0, stt_bps=0, gst_bps=0))
    # gross is measured from the OPEN (105 -> 106.05 = +1.0%), NOT from prev_close.
    assert abs(r.gross_pct - 1.0) < 0.05
    assert abs(r.gap_pct - 5.0) < 0.01


def test_costs_reduce_net_below_gross():
    bar = Bar(prev_close=100, open=100, high=102, low=99, close=101)  # +1% gross
    r = simulate_trade("bullish", bar, CostModel())
    assert r.net_pct < r.gross_pct
    # default round-trip ~0.17%
    assert abs((r.gross_pct - r.net_pct) - CostModel().round_trip_pct) < 1e-6


def test_short_profits_when_price_falls():
    bar = Bar(prev_close=100, open=100, high=100.5, low=96, close=97)
    r = simulate_trade("bearish", bar, CostModel(slippage_bps=0, brokerage_bps=0, exchange_bps=0, stt_bps=0, gst_bps=0))
    assert r.gross_pct > 0           # short gained
    assert abs(r.gross_pct - 3.0) < 0.05


def test_benchmark_relative_excess_for_long():
    bar = Bar(prev_close=100, open=100, high=103, low=100, close=102)  # +2% gross
    r = simulate_trade(
        "bullish", bar,
        CostModel(slippage_bps=0, brokerage_bps=0, exchange_bps=0, stt_bps=0, gst_bps=0),
        benchmark_day_pct=1.5,
    )
    # net +2% minus 1.5% index contribution = +0.5% excess
    assert abs(r.excess_pct - 0.5) < 0.05


def test_max_favorable_and_adverse_for_long():
    bar = Bar(prev_close=100, open=100, high=104, low=98, close=101)
    r = simulate_trade("bullish", bar, CostModel())
    assert abs(r.max_favorable_pct - 4.0) < 0.01
    assert abs(r.max_adverse_pct - (-2.0)) < 0.01


def test_flat_trade_classified_flat():
    bar = Bar(prev_close=100, open=100, high=100.2, low=99.9, close=100.05)
    r = simulate_trade("bullish", bar, CostModel())
    assert r.verdict == "FLAT"
    assert r.is_flat


def test_strong_win_threshold():
    bar = Bar(prev_close=100, open=100, high=105, low=100, close=104)  # +4% gross
    r = simulate_trade("bullish", bar, CostModel())
    assert r.verdict == "STRONG_WIN"
    assert r.is_win


# ── Wilson interval ──────────────────────────────────────────────────────────

def test_wilson_interval_zero_n():
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_wilson_interval_brackets_point_estimate():
    lo, hi = wilson_interval(60, 100)
    assert lo < 0.60 < hi
    assert 0.0 <= lo <= hi <= 1.0


def test_wilson_interval_wider_for_small_n():
    lo_small, hi_small = wilson_interval(6, 10)
    lo_big, hi_big = wilson_interval(600, 1000)
    assert (hi_small - lo_small) > (hi_big - lo_big)


# ── Aggregation ──────────────────────────────────────────────────────────────

def _bar_pct(p):
    """Build a bar with open->close = p% (open=100), wide enough to avoid flat."""
    return Bar(prev_close=100, open=100, high=100 + max(p, 0) + 1, low=100 + min(p, 0) - 1, close=100 + p)


def test_aggregate_counts_and_winrate():
    zero_cost = CostModel(slippage_bps=0, brokerage_bps=0, exchange_bps=0, stt_bps=0, gst_bps=0)
    results = [
        simulate_trade("bullish", _bar_pct(2), zero_cost),   # win
        simulate_trade("bullish", _bar_pct(4), zero_cost),   # strong win
        simulate_trade("bullish", _bar_pct(-2), zero_cost),  # loss
        simulate_trade("bullish", _bar_pct(0.1), zero_cost), # flat
    ]
    agg = aggregate(results)
    assert agg.n == 4
    assert agg.flats == 1
    assert agg.actionable == 3
    assert agg.wins == 2
    assert agg.losses == 1
    assert abs(agg.win_rate_pct - (2 / 3 * 100)) < 0.1
    assert agg.win_rate_ci_low_pct < agg.win_rate_pct < agg.win_rate_ci_high_pct
    assert agg.profit_factor > 1.0


def test_aggregate_empty_safe():
    agg = aggregate([])
    assert agg.n == 0
    assert agg.win_rate_pct == 0.0
