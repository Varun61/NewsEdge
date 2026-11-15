"""Institutional intraday trade playbook calculator.

Computes mathematically sound, volatility-adjusted execution levels:
- Entry Zone: Optimum accumulation price window
- Stop-Loss (SL): 1.2 × 14-day ATR (Average True Range)
- Target 1: 1.2 × ATR (Conservative 1:1 Risk-Reward for scaling out)
- Target 2: 2.4 × ATR (Expansion 1:2 Risk-Reward for full move)
- Risk-Reward Ratio (RRR)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("newsedge.intelligence.playbook")


@dataclass
class TradePlaybook:
    symbol: str
    direction: str              # "BULLISH" or "BEARISH"
    reference_price: float
    atr_14: float
    entry_low: float
    entry_high: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: str            # e.g. "1:2.0"
    summary_text: str           # One-line Telegram/report summary


class TradePlaybookCalculator:
    """Calculates volatility-adjusted ATR trade parameters for candidates."""

    @staticmethod
    def _default_atr_pct(price: float) -> float:
        """Estimate typical NSE equity daily ATR % based on share price bracket."""
        if price <= 100:
            return 0.035   # 3.5% daily volatility
        elif price <= 500:
            return 0.028   # 2.8% daily volatility
        elif price <= 2000:
            return 0.022   # 2.2% daily volatility
        else:
            return 0.018   # 1.8% daily volatility for high-priced/large-cap stocks

    @classmethod
    def calculate_playbook(
        cls,
        symbol: str,
        reference_price: float,
        direction: str = "BULLISH",
        atr: Optional[float] = None,
    ) -> TradePlaybook:
        """Generate precise trade levels using 14-day ATR."""
        ref = max(1.0, float(reference_price))
        is_bullish = "bull" in direction.lower()

        # Compute or fallback ATR
        if atr is None or atr <= 0:
            calculated_atr = round(ref * cls._default_atr_pct(ref), 2)
        else:
            calculated_atr = round(float(atr), 2)

        sl_distance = round(calculated_atr * 1.2, 2)
        t1_distance = round(calculated_atr * 1.2, 2)
        t2_distance = round(calculated_atr * 2.4, 2)

        if is_bullish:
            entry_low = round(ref * 0.996, 2)
            entry_high = round(ref * 1.008, 2)
            sl = round(max(0.1, ref - sl_distance), 2)
            t1 = round(ref + t1_distance, 2)
            t2 = round(ref + t2_distance, 2)
            dir_label = "BULLISH"
            summary = (
                f"Entry: ₹{entry_low:,.1f}–₹{entry_high:,.1f} | "
                f"SL: ₹{sl:,.1f} (-{round(sl_distance/ref*100, 1)}%) | "
                f"T1: ₹{t1:,.1f} (+{round(t1_distance/ref*100, 1)}%) | "
                f"T2: ₹{t2:,.1f} (+{round(t2_distance/ref*100, 1)}%)"
            )
        else:
            entry_low = round(ref * 0.992, 2)
            entry_high = round(ref * 1.004, 2)
            sl = round(ref + sl_distance, 2)
            t1 = round(max(0.1, ref - t1_distance), 2)
            t2 = round(max(0.1, ref - t2_distance), 2)
            dir_label = "BEARISH"
            summary = (
                f"Short: ₹{entry_low:,.1f}–₹{entry_high:,.1f} | "
                f"SL: ₹{sl:,.1f} (+{round(sl_distance/ref*100, 1)}%) | "
                f"T1: ₹{t1:,.1f} (-{round(t1_distance/ref*100, 1)}%) | "
                f"T2: ₹{t2:,.1f} (-{round(t2_distance/ref*100, 1)}%)"
            )

        return TradePlaybook(
            symbol=symbol.upper(),
            direction=dir_label,
            reference_price=ref,
            atr_14=calculated_atr,
            entry_low=entry_low,
            entry_high=entry_high,
            stop_loss=sl,
            target_1=t1,
            target_2=t2,
            risk_reward="1:2.0",
            summary_text=summary,
        )
