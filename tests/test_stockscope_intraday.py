"""Tests for STOCKSCOPE 360 Layer 3 intraday technical indicators, scoring, and alerts."""

from __future__ import annotations

from app.market_data.indicators import (
    calculate_ema,
    calculate_relative_volume,
    calculate_rsi,
    calculate_vwap,
    compute_intraday_snapshot,
    get_opening_range,
)
from app.market_data.intraday_scanner import IntradayScanner
from app.reporting.intraday_alerts import IntradayAlertFormatter


def _make_candles(prices: list[float], vol: int = 10000) -> list[dict]:
    return [
        {
            "timestamp": f"2026-11-26T09:{15 + i * 5:02d}:00+05:30",
            "open": p - 1.0,
            "high": p + 2.0,
            "low": p - 2.0,
            "close": p,
            "volume": vol,
        }
        for i, p in enumerate(prices)
    ]


def test_vwap_and_ema_and_rsi():
    candles = _make_candles([100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128, 130])
    vwap = calculate_vwap(candles)
    ema9 = calculate_ema(candles, period=9)
    rsi = calculate_rsi(candles, period=14)

    assert 114.0 <= vwap <= 116.0
    assert ema9 is not None and ema9 > vwap
    assert rsi == 100.0  # Strictly monotonic rising closes


def test_opening_range_and_relative_volume():
    candles = _make_candles([100, 105, 102, 108, 110], vol=50000)
    or_high, or_low = get_opening_range(candles)
    assert or_high == 107.0  # 105 + 2.0
    assert or_low == 98.0    # 100 - 2.0

    # 5 candles = 25 mins out of 375 (1/15th of day). Total vol = 250,000.
    # If avg daily vol = 1,500,000, expected vol at 25 mins = 100,000 -> RelVol = 2.5x
    rel_vol = calculate_relative_volume(candles, avg_daily_volume=1_500_000)
    assert rel_vol == 2.5


def test_snapshot_bullish_and_bearish_directional_scoring():
    # Rising prices breaking above ORB and VWAP
    bull_candles = _make_candles([100, 101, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126], vol=40000)
    snap_bull = compute_intraday_snapshot(
        symbol="RELIANCE",
        ltp=126.0,
        prev_close=100.0,
        today_candles=bull_candles,
        avg_daily_volume=1_000_000,
        direction="BULLISH",
    )
    assert snap_bull.vwap_position == "above"
    assert snap_bull.orb_signal == "breakout_up"
    assert snap_bull.intraday_score >= 30.0

    # Falling prices breaking below ORB and VWAP
    bear_candles = _make_candles([126, 124, 122, 120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100, 98], vol=40000)
    snap_bear = compute_intraday_snapshot(
        symbol="GLAND",
        ltp=98.0,
        prev_close=126.0,
        today_candles=bear_candles,
        avg_daily_volume=1_000_000,
        direction="BEARISH",
    )
    assert snap_bear.vwap_position == "below"
    assert snap_bear.orb_signal == "breakout_down"
    assert snap_bear.intraday_score >= 30.0


def test_setup_validation_gates():
    candles = _make_candles([100, 101, 102, 104, 106, 108], vol=50000)
    snap = compute_intraday_snapshot("TCS", 108.0, 100.0, candles, avg_daily_volume=1_000_000, direction="BULLISH")

    # 1. Opening range rule (< 3 candles = before 9:30 AM)
    status, reason = IntradayScanner._validate_setup("BULLISH", snap, candles_count=2, total_score=80.0, avg_val_cr=50.0, min_confirmed_score=65.0)
    assert status == "WATCH"
    assert "Opening Range" in reason

    # 2. Illiquidity gate (< 1 Cr turnover)
    status, reason = IntradayScanner._validate_setup("BULLISH", snap, candles_count=6, total_score=80.0, avg_val_cr=0.5, min_confirmed_score=65.0)
    assert status == "NO_TRADE"

    # 3. Confirmed Long
    status, reason = IntradayScanner._validate_setup("BULLISH", snap, candles_count=6, total_score=78.0, avg_val_cr=120.0, min_confirmed_score=65.0)
    assert status == "CONFIRMED_LONG"
    assert reason is None


def test_intraday_alert_formatter_no_trade_summary():
    msg = IntradayAlertFormatter.format_scan_summary([], "2026-11-26")
    assert "NO TRADE CONFIRMED YET" in msg
