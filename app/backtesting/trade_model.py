"""Realistic trade simulation + aggregate statistics for backtesting.

This is the honest core the old backtester lacked. Key corrections:

1. **Realistic fill.** A next-morning pick is entered at the NEXT session's
   OPEN, not the previous close. The overnight gap is already gone by the time
   you can trade, so returns are measured open->close.
2. **Costs.** Every trade pays round-trip costs (brokerage + exchange charges +
   STT + slippage) expressed in basis points of turnover.
3. **Benchmark-relative.** A long is credited only with its return *in excess of*
   the index that day (and a short with the index's decline), so a rising tide
   isn't mistaken for skill.
4. **Honest aggregates.** Win rate is reported with a Wilson confidence interval
   so small samples aren't over-interpreted.

Pure module: no network, no DB, no pandas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

BULLISH = "bullish"
BEARISH = "bearish"


@dataclass(frozen=True)
class CostModel:
    """Round-trip trading friction, in basis points of turnover (1 bp = 0.01%)."""

    brokerage_bps: float = 3.0     # discount-broker intraday, both sides combined
    exchange_bps: float = 1.0      # exchange txn + SEBI + stamp
    stt_bps: float = 2.5           # STT on intraday sell side (~0.025%)
    gst_bps: float = 0.5
    slippage_bps: float = 10.0     # entry+exit slippage; widen for illiquid names

    @property
    def round_trip_pct(self) -> float:
        """Total round-trip cost as a percentage of entry price."""
        total_bps = (
            self.brokerage_bps
            + self.exchange_bps
            + self.stt_bps
            + self.gst_bps
            + self.slippage_bps
        )
        return total_bps / 100.0  # bps -> percent


@dataclass(frozen=True)
class Bar:
    """A single daily OHLC bar for the trade day (prices in ₹)."""

    prev_close: float
    open: float
    high: float
    low: float
    close: float

    @property
    def gap_pct(self) -> float:
        if self.prev_close <= 0:
            return 0.0
        return (self.open - self.prev_close) / self.prev_close * 100.0


@dataclass
class TradeResult:
    direction: str
    gross_pct: float          # open->close, direction-adjusted, before costs
    net_pct: float            # after round-trip costs
    excess_pct: float         # net minus the benchmark's contribution
    max_favorable_pct: float  # best unrealised move from open (direction-adjusted)
    max_adverse_pct: float    # worst unrealised move from open (direction-adjusted)
    gap_pct: float
    is_win: bool              # net_pct > 0
    verdict: str              # STRONG_WIN, WIN, FLAT, LOSS, STRONG_LOSS

    @property
    def is_flat(self) -> bool:
        return self.verdict == "FLAT"


def simulate_trade(
    direction: str,
    bar: Bar,
    cost: CostModel = CostModel(),
    benchmark_day_pct: float = 0.0,
    flat_threshold_pct: float = 0.3,
    strong_threshold_pct: float = 3.0,
) -> TradeResult:
    """Simulate a single intraday trade: enter at open, exit at close.

    ``benchmark_day_pct`` is the index's open->close return that day.
    """
    direction = direction.lower()
    if bar.open <= 0:
        return TradeResult(direction, 0, 0, 0, 0, 0, bar.gap_pct, False, "FLAT")

    raw = (bar.close - bar.open) / bar.open * 100.0
    up_move = (bar.high - bar.open) / bar.open * 100.0
    down_move = (bar.low - bar.open) / bar.open * 100.0

    if direction == BEARISH:
        gross = -raw
        max_fav = -down_move          # price falling helps a short
        max_adv = -up_move
        bench_contrib = -benchmark_day_pct
    else:
        gross = raw
        max_fav = up_move
        max_adv = down_move
        bench_contrib = benchmark_day_pct

    net = gross - cost.round_trip_pct
    excess = net - bench_contrib

    if abs(net) < flat_threshold_pct:
        verdict = "FLAT"
        is_win = False
    elif net >= strong_threshold_pct:
        verdict = "STRONG_WIN"
        is_win = True
    elif net > 0:
        verdict = "WIN"
        is_win = True
    elif net <= -strong_threshold_pct:
        verdict = "STRONG_LOSS"
        is_win = False
    else:
        verdict = "LOSS"
        is_win = False

    return TradeResult(
        direction=direction,
        gross_pct=round(gross, 3),
        net_pct=round(net, 3),
        excess_pct=round(excess, 3),
        max_favorable_pct=round(max_fav, 3),
        max_adverse_pct=round(max_adv, 3),
        gap_pct=round(bar.gap_pct, 3),
        is_win=is_win,
        verdict=verdict,
    )


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a proportion (default 95%).

    Returns (low, high) as fractions in [0, 1]. For n == 0 returns (0, 0).
    """
    if n <= 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


@dataclass
class AggregateStats:
    n: int = 0
    actionable: int = 0           # non-flat trades
    wins: int = 0
    losses: int = 0
    flats: int = 0
    win_rate_pct: float = 0.0
    win_rate_ci_low_pct: float = 0.0
    win_rate_ci_high_pct: float = 0.0
    avg_net_pct: float = 0.0          # mean net return over actionable trades
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0        # sum(win net) / abs(sum(loss net))
    avg_excess_pct: float = 0.0       # benchmark-relative mean
    expectancy_pct: float = 0.0       # per-trade expected net return
    details: dict = field(default_factory=dict)


def aggregate(results: list[TradeResult]) -> AggregateStats:
    """Compute honest aggregate statistics over a list of simulated trades."""
    stats = AggregateStats(n=len(results))
    actionable = [r for r in results if not r.is_flat]
    stats.flats = len(results) - len(actionable)
    stats.actionable = len(actionable)
    if not actionable:
        return stats

    wins = [r for r in actionable if r.is_win]
    losses = [r for r in actionable if not r.is_win]
    stats.wins = len(wins)
    stats.losses = len(losses)

    stats.win_rate_pct = round(len(wins) / len(actionable) * 100.0, 2)
    lo, hi = wilson_interval(len(wins), len(actionable))
    stats.win_rate_ci_low_pct = round(lo * 100.0, 2)
    stats.win_rate_ci_high_pct = round(hi * 100.0, 2)

    net_vals = [r.net_pct for r in actionable]
    stats.avg_net_pct = round(sum(net_vals) / len(net_vals), 3)
    stats.expectancy_pct = stats.avg_net_pct
    stats.avg_excess_pct = round(sum(r.excess_pct for r in actionable) / len(actionable), 3)

    if wins:
        stats.avg_win_pct = round(sum(r.net_pct for r in wins) / len(wins), 3)
    if losses:
        stats.avg_loss_pct = round(sum(r.net_pct for r in losses) / len(losses), 3)

    win_sum = sum(r.net_pct for r in wins)
    loss_sum = abs(sum(r.net_pct for r in losses))
    stats.profit_factor = round(win_sum / loss_sum, 3) if loss_sum > 0 else float("inf")

    return stats
