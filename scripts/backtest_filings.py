"""Honest filings-first backtester.

Unlike ``backtest_one_month.py`` (which runs a *duplicated* pipeline over
Google-News headlines), this evaluates the **real** candidate analyses that the
production pipeline already produced and stored in the database. It therefore
measures exactly what you would have been shown — no shadow scoring, no
headline re-mining, no selection bias from catalyst-only search queries.

How it works:
1. Read actionable ``StockAnalysis`` rows from the DB within a date range
   (optionally only those backed by an authoritative exchange filing).
2. Determine the realistic trade session: the next market open strictly after
   the filing/analysis timestamp (you cannot trade before the open).
3. Fetch that session's OHLC bar for the stock and for the Nifty 50 benchmark
   via yfinance.
4. Evaluate each trade with the tested core in ``app.backtesting.trade_model``
   (enter at open, round-trip costs, benchmark-relative, Wilson CI).
5. Write an honest markdown report with results bucketed by liquidity tier.

Because it reads the accumulated DB, its sample grows every day you run the
pipeline. On a fresh DB it will correctly report that there is nothing to test.

Usage:
    python -m scripts.backtest_filings --days 30
    python -m scripts.backtest_filings --days 60 --all-sources
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.backtesting.trade_model import Bar, CostModel, aggregate, simulate_trade
from app.database.database import get_session
from app.database.models import CandidateClassification, StockAnalysis
from app.intelligence.liquidity_gate import evaluate_liquidity
from app.trading_calendar import IST, is_trading_day, next_trading_day

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("backtest_filings")

BENCHMARK_TICKER = "^NSEI"  # Nifty 50

_BULLISH = {CandidateClassification.STRONG_BULLISH, CandidateClassification.BULLISH}
_BEARISH = {CandidateClassification.STRONG_BEARISH, CandidateClassification.BEARISH}


def _trade_session_for(filing_dt_utc: datetime) -> date:
    """The next session whose open you could realistically trade at.

    A filing before 09:00 IST on a trading day is actionable at that day's open;
    otherwise it is actionable at the next trading day's open.
    """
    ist = filing_dt_utc.astimezone(IST) if filing_dt_utc.tzinfo else IST.localize(filing_dt_utc)
    d = ist.date()
    if is_trading_day(d) and ist.time() < time(9, 0):
        return d
    return next_trading_day(d + timedelta(days=1))


def _analysis_filing_time(a: StockAnalysis) -> datetime:
    """Best available timestamp for when the catalyst was knowable."""
    ev = a.news_event
    if ev is not None:
        for link in ev.article_links:
            art = link.article
            if art and link.is_primary and art.published_at:
                return art.published_at
        for link in ev.article_links:
            art = link.article
            if art and art.published_at:
                return art.published_at
    return a.created_at or datetime.now(timezone.utc)


def _is_filing_backed(a: StockAnalysis) -> bool:
    ev = a.news_event
    if ev is None:
        return False
    for link in ev.article_links:
        art = link.article
        if art and isinstance(art.company_mentions, dict) and art.company_mentions.get("authoritative_symbol"):
            return True
    return False


def _collect_setups(start: date, end: date, filings_only: bool):
    """Return (symbol, direction, analysis, filing_dt) tuples for actionable picks."""
    setups = []
    with get_session() as session:
        rows = list(session.query(StockAnalysis).all())
        for a in rows:
            if a.classification in _BULLISH:
                direction = "bullish"
            elif a.classification in _BEARISH:
                direction = "bearish"
            else:
                continue
            if filings_only and not _is_filing_backed(a):
                continue
            filing_dt = _analysis_filing_time(a)
            trade_day = _trade_session_for(filing_dt)
            if not (start <= trade_day <= end):
                continue
            comp = a.company
            if not comp:
                continue
            setups.append({
                "symbol": comp.nse_symbol,
                "name": comp.company_name,
                "direction": direction,
                "score": a.overall_score,
                "trade_day": trade_day,
                "mcap_cat": comp.market_cap_category.value if comp.market_cap_category else None,
                "mcap": comp.market_cap,
            })
    return setups


def _fetch_bars(symbols: set[str], start: date, end: date):
    """Download daily OHLC for symbols + benchmark. Returns {yf_symbol: {date: row}}."""
    import yfinance as yf

    tickers = sorted({f"{s}.NS" for s in symbols} | {BENCHMARK_TICKER})
    data: dict[str, dict] = {}
    df = yf.download(
        " ".join(tickers),
        start=(start - timedelta(days=7)).isoformat(),
        end=(end + timedelta(days=4)).isoformat(),
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    for tk in tickers:
        try:
            sub = df[tk] if hasattr(df.columns, "levels") else df
        except Exception:
            continue
        sub = sub.dropna(subset=["Close"])
        per_day = {}
        prev_close = None
        for idx in range(len(sub)):
            row = sub.iloc[idx]
            d = sub.index[idx].date()
            try:
                o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
            except Exception:
                continue
            if prev_close is not None and o > 0:
                per_day[d] = {"prev_close": prev_close, "open": o, "high": h, "low": l, "close": c}
            prev_close = c
        data[tk] = per_day
    return data


def _benchmark_day_pct(bars, trade_day) -> float:
    row = bars.get(BENCHMARK_TICKER, {}).get(trade_day)
    if not row or row["open"] <= 0:
        return 0.0
    return (row["close"] - row["open"]) / row["open"] * 100.0


def _fmt(stats, title: str) -> list[str]:
    if stats.actionable == 0:
        return [f"### {title}", "", "_No actionable trades with price data._", ""]
    return [
        f"### {title}",
        "",
        f"- Trades (actionable / total): **{stats.actionable}** / {stats.n}  (flat: {stats.flats})",
        f"- Win rate: **{stats.win_rate_pct:.1f}%**  (95% CI {stats.win_rate_ci_low_pct:.1f}–{stats.win_rate_ci_high_pct:.1f}%)",
        f"- Avg net/trade: **{stats.avg_net_pct:+.2f}%**  |  Expectancy: {stats.expectancy_pct:+.2f}%",
        f"- Avg win: {stats.avg_win_pct:+.2f}%  |  Avg loss: {stats.avg_loss_pct:+.2f}%  |  Profit factor: {stats.profit_factor}",
        f"- Benchmark-relative (excess vs Nifty): **{stats.avg_excess_pct:+.2f}%/trade**",
        "",
    ]


def run(days: int, filings_only: bool, cost: CostModel):
    end = date.today()
    start = end - timedelta(days=days)
    logger.info("Backtest window (trade days): %s to %s | filings_only=%s", start, end, filings_only)

    setups = _collect_setups(start, end, filings_only)
    if not setups:
        logger.warning(
            "No actionable %s setups found in the DB for this window. "
            "Run the pipeline daily to accumulate filings, then re-run the backtest.",
            "filing-backed" if filings_only else "",
        )
        return

    logger.info("Collected %d actionable setups. Fetching prices...", len(setups))
    symbols = {s["symbol"] for s in setups}
    bars = _fetch_bars(symbols, start, end)

    all_results = []
    by_dir = {"bullish": [], "bearish": []}
    by_tier: dict[str, list] = {}
    skipped = 0

    for s in setups:
        day_bars = bars.get(f"{s['symbol']}.NS", {})
        row = day_bars.get(s["trade_day"])
        if not row:
            skipped += 1
            continue
        bar = Bar(**row)
        bench = _benchmark_day_pct(bars, s["trade_day"])
        r = simulate_trade(s["direction"], bar, cost, benchmark_day_pct=bench)
        all_results.append(r)
        by_dir[s["direction"]].append(r)
        tier = evaluate_liquidity(s["symbol"], s["mcap_cat"], s["mcap"]).tier
        by_tier.setdefault(tier, []).append(r)

    overall = aggregate(all_results)

    lines = [
        "# NewsEdge — Honest Filings-First Backtest",
        "",
        f"**Window (trade sessions):** {start} to {end}",
        f"**Source filter:** {'authoritative exchange filings only' if filings_only else 'all actionable picks'}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "> Entries are modelled at the **next session open** (overnight gap not captured), "
        f"with round-trip costs of **{cost.round_trip_pct:.2f}%** "
        "(brokerage + exchange + STT + GST + slippage), and returns are reported "
        "**relative to the Nifty 50** that session. Win rate carries a 95% Wilson "
        "confidence interval. No parameters are fit to this data.",
        "",
        f"_Setups evaluated: {len(all_results)} (skipped {skipped} with no price data)._",
        "",
        "---",
        "",
    ]
    lines += _fmt(overall, "Overall")
    lines += _fmt(aggregate(by_dir["bullish"]), "Bullish")
    lines += _fmt(aggregate(by_dir["bearish"]), "Bearish")
    lines += ["---", "", "## By liquidity tier", ""]
    for tier in ("FNO", "LARGE", "MID", "SMALL", "MICRO", "UNKNOWN"):
        if tier in by_tier:
            lines += _fmt(aggregate(by_tier[tier]), tier)

    report = "\n".join(lines)
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out = reports_dir / f"backtest_filings_{start}_to_{end}.md"
    out.write_text(report, encoding="utf-8")

    logger.info("=" * 60)
    logger.info("Overall: %d actionable | win %.1f%% (CI %.1f-%.1f) | net %+.2f%%/trade | excess %+.2f%%",
                overall.actionable, overall.win_rate_pct, overall.win_rate_ci_low_pct,
                overall.win_rate_ci_high_pct, overall.avg_net_pct, overall.avg_excess_pct)
    logger.info("Report saved: %s", out)
    logger.info("=" * 60)


def main():
    p = argparse.ArgumentParser(description="NewsEdge honest filings-first backtester")
    p.add_argument("--days", type=int, default=30, help="Look back this many days of trade sessions (default 30)")
    p.add_argument("--all-sources", action="store_true", help="Include news-backed picks, not just exchange filings")
    p.add_argument("--slippage-bps", type=float, default=10.0, help="Per round-trip slippage in bps (raise for illiquid names)")
    args = p.parse_args()

    cost = CostModel(slippage_bps=args.slippage_bps)
    run(days=args.days, filings_only=not args.all_sources, cost=cost)


if __name__ == "__main__":
    main()
