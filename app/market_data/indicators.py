"""Intraday price indicators — VWAP, relative volume, RSI, opening range.

All functions take a list of candle dicts (from angel_client.get_candles)
and return computed indicator values. Pure functions, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IntradaySnapshot:
    """All key intraday metrics for a single stock at a point in time."""
    symbol: str
    ltp: float
    vwap: float
    vwap_position: str          # "above" | "below" | "at"
    relative_volume: float      # current vol / avg vol at same time
    gap_pct: float              # gap from prev close %
    rsi_14: Optional[float]
    ema9: Optional[float]
    opening_range_high: Optional[float]  # 9:15–9:30 AM range high
    opening_range_low: Optional[float]   # 9:15–9:30 AM range low
    orb_signal: str             # "breakout_up" | "breakout_down" | "inside" | "none"
    intraday_score: float       # 0–45 (45% weight in final score)
    signal_summary: str         # Human-readable signal description


def calculate_vwap(candles: list[dict]) -> float:
    """Compute VWAP from open of day candles. Returns 0.0 if no data."""
    total_pv = 0.0
    total_vol = 0
    for c in candles:
        typical_price = (c["high"] + c["low"] + c["close"]) / 3
        total_pv += typical_price * c["volume"]
        total_vol += c["volume"]
    return round(total_pv / total_vol, 2) if total_vol > 0 else 0.0


def calculate_rsi(candles: list[dict], period: int = 14) -> Optional[float]:
    """Compute RSI-14 from list of candles. Returns None if insufficient data."""
    closes = [c["close"] for c in candles]
    if len(closes) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_ema(candles: list[dict], period: int = 9) -> Optional[float]:
    """Compute EMA for given period. Returns None if insufficient data."""
    closes = [c["close"] for c in candles]
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)


def calculate_relative_volume(
    today_candles: list[dict],
    avg_daily_volume: float,
    total_minutes_in_session: int = 375,
) -> float:
    """Compare today's volume so far vs expected average at this point.

    avg_daily_volume: 20-day average daily volume
    Returns relative volume ratio (1.0 = average, 2.0 = double average).
    """
    if avg_daily_volume <= 0 or not today_candles:
        return 0.0
    today_vol = sum(c["volume"] for c in today_candles)
    minutes_elapsed = len(today_candles) * 5  # assumes 5-min candles
    # Expected volume at this point in day
    fraction_of_day = max(minutes_elapsed / total_minutes_in_session, 0.01)
    expected_vol = avg_daily_volume * fraction_of_day
    return round(today_vol / expected_vol, 2) if expected_vol > 0 else 0.0


def get_opening_range(candles: list[dict]) -> tuple[Optional[float], Optional[float]]:
    """Extract opening range (9:15–9:30 AM) high and low from 5-min candles.
    Returns (high, low) or (None, None) if fewer than 3 candles available.
    """
    if len(candles) < 3:
        return None, None
    # First 3 candles of a 5-min chart = 9:15, 9:20, 9:25 (opening range up to 9:30)
    or_candles = candles[:3]
    return (
        max(c["high"] for c in or_candles),
        min(c["low"] for c in or_candles),
    )


def compute_intraday_snapshot(
    symbol: str,
    ltp: float,
    prev_close: float,
    today_candles: list[dict],
    avg_daily_volume: float = 0,
    direction: str = "BULLISH",
) -> IntradaySnapshot:
    """Compute all intraday indicators and produce a direction-aware scored snapshot."""
    is_bullish = "bull" in direction.lower()
    vwap = calculate_vwap(today_candles)
    rsi = calculate_rsi(today_candles)
    ema9 = calculate_ema(today_candles, period=9)
    rel_vol = calculate_relative_volume(today_candles, avg_daily_volume)
    or_high, or_low = get_opening_range(today_candles)

    # Gap from prev close
    gap_pct = round(((ltp - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

    # VWAP position
    if vwap == 0:
        vwap_pos = "none"
    elif ltp > vwap * 1.001:
        vwap_pos = "above"
    elif ltp < vwap * 0.999:
        vwap_pos = "below"
    else:
        vwap_pos = "at"

    # ORB signal
    orb_signal = "none"
    if or_high and or_low and ltp > 0:
        if ltp > or_high:
            orb_signal = "breakout_up"
        elif ltp < or_low:
            orb_signal = "breakout_down"
        else:
            orb_signal = "inside"

    # ── Intraday score (0–45) ──────────────────────────────────────────
    score = 0.0
    reasons = []

    # VWAP alignment (0–12 pts)
    if is_bullish:
        if vwap_pos == "above":
            score += 12
            reasons.append("Above VWAP ✓")
        elif vwap_pos == "at":
            score += 7
            reasons.append("At VWAP")
        elif vwap_pos == "below":
            score += 2
            reasons.append("Below VWAP ✗")
    else:
        if vwap_pos == "below":
            score += 12
            reasons.append("Below VWAP ✓")
        elif vwap_pos == "at":
            score += 7
            reasons.append("At VWAP")
        elif vwap_pos == "above":
            score += 2
            reasons.append("Above VWAP ✗")

    # RSI zone (0–10 pts)
    if rsi is not None:
        if is_bullish:
            if 55 <= rsi <= 75:
                score += 10
                reasons.append(f"RSI {rsi} (bullish momentum ✓)")
            elif 45 <= rsi < 55:
                score += 6
                reasons.append(f"RSI {rsi} (neutral)")
            elif rsi > 75:
                score += 4
                reasons.append(f"RSI {rsi} (overbought, caution)")
            else:
                score += 2
                reasons.append(f"RSI {rsi} (weak ✗)")
        else:
            if 25 <= rsi <= 45:
                score += 10
                reasons.append(f"RSI {rsi} (bearish momentum ✓)")
            elif 45 < rsi <= 55:
                score += 6
                reasons.append(f"RSI {rsi} (neutral)")
            elif rsi < 25:
                score += 4
                reasons.append(f"RSI {rsi} (oversold, caution)")
            else:
                score += 2
                reasons.append(f"RSI {rsi} (strong ✗)")

    # Relative volume (0–10 pts)
    if rel_vol >= 3.0:
        score += 10
        reasons.append(f"RelVol {rel_vol}x (very high ✓✓)")
    elif rel_vol >= 2.0:
        score += 8
        reasons.append(f"RelVol {rel_vol}x (high ✓)")
    elif rel_vol >= 1.3:
        score += 5
        reasons.append(f"RelVol {rel_vol}x (above avg)")
    elif rel_vol > 0:
        score += 2
        reasons.append(f"RelVol {rel_vol}x (low)")

    # ORB breakout (0–8 pts)
    if is_bullish:
        if orb_signal == "breakout_up":
            score += 8
            reasons.append("ORB breakout UP ✓")
        elif orb_signal == "inside":
            score += 3
            reasons.append("Inside opening range")
        elif orb_signal == "breakout_down":
            reasons.append("ORB breakdown DOWN ✗")
    else:
        if orb_signal == "breakout_down":
            score += 8
            reasons.append("ORB breakdown DOWN ✓")
        elif orb_signal == "inside":
            score += 3
            reasons.append("Inside opening range")
        elif orb_signal == "breakout_up":
            reasons.append("ORB breakout UP ✗")

    # EMA9 alignment (0–5 pts)
    if ema9 and ltp > 0:
        if is_bullish:
            if ltp > ema9:
                score += 5
                reasons.append(f"Above EMA9 ({ema9}) ✓")
            else:
                score += 1
                reasons.append(f"Below EMA9 ({ema9})")
        else:
            if ltp < ema9:
                score += 5
                reasons.append(f"Below EMA9 ({ema9}) ✓")
            else:
                score += 1
                reasons.append(f"Above EMA9 ({ema9})")

    return IntradaySnapshot(
        symbol=symbol,
        ltp=ltp,
        vwap=vwap,
        vwap_position=vwap_pos,
        relative_volume=rel_vol,
        gap_pct=gap_pct,
        rsi_14=rsi,
        ema9=ema9,
        opening_range_high=or_high,
        opening_range_low=or_low,
        orb_signal=orb_signal,
        intraday_score=round(min(score, 45.0), 1),
        signal_summary=" | ".join(reasons) if reasons else "No signal",
    )
