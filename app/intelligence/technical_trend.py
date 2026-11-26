"""Technical trend and moving average alignment engine.

Applies institutional trend alignment principles:
- 'The trend is your friend': Bullish catalysts occurring on stocks in confirmed
  uptrends (Price > 20 EMA > 50 EMA) have significantly higher follow-through.
- 'Sell on Rise trap': Stocks in severe structural downtrends (Price < 20 EMA and < 50 EMA)
  frequently dump into positive headline liquidity as trapped bagholders exit.
- 'Breakdown velocity': Bearish catalysts on stocks already below 20/50 EMA produce
  rapid downward repricing.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger("newsedge.intelligence.technical_trend")


@dataclass
class TrendEvaluation:
    symbol: str
    current_price: float
    ema_20: float
    ema_50: float
    trend_state: str           # STRONG_UPTREND, UPTREND, STRONG_DOWNTREND, DOWNTREND, NEUTRAL
    score_modifier: float      # Score adjustment (-14.0 to +8.0)
    trend_label: str           # Human-readable summary
    warning: Optional[str] = None


class TechnicalTrendAnalyzer:
    """Computes 20 EMA and 50 EMA trend status for NSE equities."""

    def __init__(self, cache_ttl_seconds: int = 14400):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._trend_cache: Dict[str, Tuple[float, TrendEvaluation]] = {}

    def _calculate_ema(self, prices: list[float], period: int) -> float:
        """Calculate Exponential Moving Average for a series of closing prices."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0

        multiplier = 2.0 / (period + 1)
        # Start with Simple Moving Average of first 'period' bars
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return round(ema, 2)

    def get_trend_evaluation(self, nse_symbol: str, target_direction: str = "bullish") -> Optional[TrendEvaluation]:
        """Fetch historical bars, compute 20/50 EMA, and return directional trend modifier."""
        clean_sym = nse_symbol.upper().strip()
        now = time.time()

        # Check in-memory cache
        if clean_sym in self._trend_cache:
            ts, cached_eval = self._trend_cache[clean_sym]
            if now - ts < self.cache_ttl_seconds:
                return self._apply_direction(cached_eval, target_direction)

        import yfinance as yf
        from app.market_data.yf_symbols import to_yf_ticker

        yf_ticker = to_yf_ticker(clean_sym)
        try:
            # Fetch 75 days of daily data to cleanly compute 50 EMA
            ticker_obj = yf.Ticker(yf_ticker)
            df = ticker_obj.history(period="75d", interval="1d", auto_adjust=True)
            if df.empty or len(df) < 25:
                return None

            closes = df["Close"].dropna().tolist()
            if not closes:
                return None

            curr_price = round(closes[-1], 2)
            ema_20 = self._calculate_ema(closes, 20)
            ema_50 = self._calculate_ema(closes, min(50, len(closes)))

            # Determine Trend State
            if curr_price > ema_20 and ema_20 > ema_50:
                trend_state = "STRONG_UPTREND"
                trend_label = f"Structural Uptrend (Price ₹{curr_price} > 20 EMA ₹{ema_20} > 50 EMA ₹{ema_50})"
            elif curr_price > ema_20:
                trend_state = "UPTREND"
                trend_label = f"Short-term Uptrend (Price ₹{curr_price} > 20 EMA ₹{ema_20})"
            elif curr_price < ema_20 and ema_20 < ema_50:
                trend_state = "STRONG_DOWNTREND"
                trend_label = f"Structural Downtrend (Price ₹{curr_price} < 20 EMA ₹{ema_20} < 50 EMA ₹{ema_50})"
            elif curr_price < ema_20:
                trend_state = "DOWNTREND"
                trend_label = f"Short-term Downtrend (Price ₹{curr_price} < 20 EMA ₹{ema_20})"
            else:
                trend_state = "NEUTRAL"
                trend_label = f"Consolidating/Neutral (Price ₹{curr_price} ~ 20 EMA ₹{ema_20})"

            base_eval = TrendEvaluation(
                symbol=clean_sym,
                current_price=curr_price,
                ema_20=ema_20,
                ema_50=ema_50,
                trend_state=trend_state,
                score_modifier=0.0,
                trend_label=trend_label,
            )

            # Store in cache
            self._trend_cache[clean_sym] = (now, base_eval)
            return self._apply_direction(base_eval, target_direction)

        except Exception as exc:
            logger.debug("Technical trend evaluation skipped for %s: %s", clean_sym, exc)
            return None

    def _apply_direction(self, base: TrendEvaluation, target_direction: str) -> TrendEvaluation:
        """Apply directional alignment bonuses or penalties."""
        direction = target_direction.lower()
        state = base.trend_state
        mod = 0.0
        warning = None

        if "bullish" in direction:
            if state == "STRONG_UPTREND":
                mod = +8.0
            elif state == "UPTREND":
                mod = +4.0
            elif state == "STRONG_DOWNTREND":
                mod = -14.0
                warning = f"⚠️ Counter-Trend Bounce Risk: Stock is in a structural downtrend (Below 20 & 50 EMA). Risk of sell-on-rise."
            elif state == "DOWNTREND":
                mod = -8.0
                warning = f"⚠️ Short-term Downtrend: Trading below 20-day EMA."
        elif "bearish" in direction:
            if state == "STRONG_DOWNTREND":
                mod = +8.0  # High breakdown velocity
            elif state == "DOWNTREND":
                mod = +4.0
            elif state == "STRONG_UPTREND":
                mod = -12.0
                warning = f"⚠️ Counter-Trend Short Risk: Stock is in a powerful uptrend (Above 20 & 50 EMA). Shorting against institutional momentum."
            elif state == "UPTREND":
                mod = -6.0

        return TrendEvaluation(
            symbol=base.symbol,
            current_price=base.current_price,
            ema_20=base.ema_20,
            ema_50=base.ema_50,
            trend_state=base.trend_state,
            score_modifier=mod,
            trend_label=base.trend_label,
            warning=warning,
        )


_trend_instance: Optional[TechnicalTrendAnalyzer] = None


def get_technical_trend_analyzer() -> TechnicalTrendAnalyzer:
    global _trend_instance
    if _trend_instance is None:
        _trend_instance = TechnicalTrendAnalyzer()
    return _trend_instance
