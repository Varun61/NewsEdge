"""Backtest NewsEdge predictions against actual next-day stock performance.

Fetches BULLISH/BEARISH predictions from the database, downloads actual
next-trading-day price data from Yahoo Finance (NSE tickers), and evaluates
whether the stock moved in the predicted direction.

Usage:
    python scripts/backtest_predictions.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import yfinance as yf
from sqlalchemy import func

from app.database.database import get_session
from app.database.models import (
    StockAnalysis,
    NewsEvent,
    Company,
    CandidateClassification,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# Data Structures
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Prediction:
    """A single directional prediction from NewsEdge."""
    symbol: str
    company_name: str
    classification: str          # strong_bullish / bullish / bearish / strong_bearish
    predicted_direction: str     # bullish / bearish
    overall_score: float
    impact_score: float
    confidence: float
    news_category: str
    headline: str
    article_url: str             # first linked article URL
    created_at: str              # ISO timestamp
    report_date: str             # YYYY-MM-DD


@dataclass
class PriceData:
    """Actual next-day price data."""
    prev_close: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    volume: Optional[int] = None
    # Derived
    gap_pct: Optional[float] = None        # (open - prev_close) / prev_close
    intraday_pct: Optional[float] = None   # (close - open) / open
    full_day_pct: Optional[float] = None   # (close - prev_close) / prev_close
    max_up_pct: Optional[float] = None     # (high - prev_close) / prev_close
    max_down_pct: Optional[float] = None   # (low - prev_close) / prev_close


@dataclass
class BacktestResult:
    """Prediction vs actual outcome for a single symbol."""
    prediction: Prediction
    price: Optional[PriceData]
    direction_correct: Optional[bool] = None
    actual_move_pct: Optional[float] = None
    verdict: str = "NO_DATA"
    notes: str = ""


# ══════════════════════════════════════════════════════════════════════════
# Step 1: Extract predictions from DB
# ══════════════════════════════════════════════════════════════════════════

def extract_predictions() -> dict[str, list[Prediction]]:
    """Pull all BULLISH/BEARISH predictions, grouped by report_date."""
    predictions_by_date: dict[str, list[Prediction]] = defaultdict(list)

    with get_session() as session:
        analyses = (
            session.query(StockAnalysis)
            .filter(
                StockAnalysis.classification.in_([
                    CandidateClassification.STRONG_BULLISH,
                    CandidateClassification.BULLISH,
                    CandidateClassification.STRONG_BEARISH,
                    CandidateClassification.BEARISH,
                ])
            )
            .all()
        )

        for sa in analyses:
            evt = sa.news_event
            comp = sa.company
            if not evt or not comp:
                continue

            # Determine predicted direction
            if sa.classification in (
                CandidateClassification.STRONG_BULLISH,
                CandidateClassification.BULLISH,
            ):
                direction = "bullish"
            else:
                direction = "bearish"

            # Get first article URL
            article_url = ""
            if evt.article_links:
                for link in evt.article_links:
                    if link.article and link.article.article_url:
                        article_url = link.article.article_url
                        break

            # Determine report_date from the DailyWatchlist or created_at
            report_dt = str(sa.created_at.date()) if sa.created_at else "unknown"

            pred = Prediction(
                symbol=comp.nse_symbol,
                company_name=comp.company_name,
                classification=sa.classification.value,
                predicted_direction=direction,
                overall_score=sa.overall_score,
                impact_score=evt.impact_score or 0,
                confidence=evt.confidence or 0,
                news_category=evt.news_category.value if evt.news_category else "OTHER",
                headline=evt.primary_headline,
                article_url=article_url,
                created_at=str(sa.created_at),
                report_date=report_dt,
            )
            predictions_by_date[report_dt].append(pred)

    return dict(predictions_by_date)


# ══════════════════════════════════════════════════════════════════════════
# Step 2: Deduplicate predictions per symbol per day
# ══════════════════════════════════════════════════════════════════════════

def deduplicate_predictions(preds: list[Prediction]) -> list[Prediction]:
    """Keep the highest-scoring prediction per symbol."""
    best: dict[str, Prediction] = {}
    for p in preds:
        if p.symbol not in best or p.overall_score > best[p.symbol].overall_score:
            best[p.symbol] = p
    return list(best.values())


# ══════════════════════════════════════════════════════════════════════════
# Step 3: Fetch actual stock prices from Yahoo Finance
# ══════════════════════════════════════════════════════════════════════════

def get_next_trading_day(prediction_date: date) -> date:
    """Get the next trading day after the prediction date.
    
    Skip weekends. Doesn't account for holidays — yfinance will simply
    return no data for non-trading days.
    """
    next_day = prediction_date + timedelta(days=1)
    # Skip weekends
    while next_day.weekday() >= 5:  # 5=Sat, 6=Sun
        next_day += timedelta(days=1)
    return next_day


def fetch_prices_batch(
    symbols: list[str],
    prediction_date: date,
) -> dict[str, PriceData]:
    """Fetch price data for all symbols.
    
    Downloads data for prediction_date and the next trading day so we can
    get prev_close from prediction_date and OHLCV from the next day.
    """
    next_day = get_next_trading_day(prediction_date)
    
    # Download 5-day window to handle holidays/gaps
    start = prediction_date - timedelta(days=3)
    end = next_day + timedelta(days=3)
    
    # Build yfinance ticker symbols (append .NS for NSE)
    yf_symbols = [f"{s}.NS" for s in symbols]
    
    results: dict[str, PriceData] = {}
    
    # Batch download in chunks to avoid rate limits
    chunk_size = 50
    for i in range(0, len(yf_symbols), chunk_size):
        chunk = yf_symbols[i:i + chunk_size]
        chunk_str = " ".join(chunk)
        log.info(f"Fetching prices for {len(chunk)} symbols (batch {i//chunk_size + 1})...")
        
        try:
            data = yf.download(
                chunk_str,
                start=start.isoformat(),
                end=end.isoformat(),
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            log.error(f"yfinance download error: {e}")
            continue
        
        for yf_sym in chunk:
            nse_sym = yf_sym.replace(".NS", "")
            try:
                if len(chunk) == 1:
                    ticker_data = data
                else:
                    ticker_data = data[yf_sym]
                
                if ticker_data.empty:
                    continue
                
                # Find the closest trading day data
                # prev_close = last available close on or before prediction_date
                # next_day data = first available data after prediction_date
                pred_data = ticker_data[ticker_data.index.date <= prediction_date]
                next_data = ticker_data[ticker_data.index.date > prediction_date]
                
                if pred_data.empty or next_data.empty:
                    continue
                
                prev_close = float(pred_data["Close"].iloc[-1])
                next_row = next_data.iloc[0]
                
                pd_ = PriceData(
                    prev_close=prev_close,
                    open_price=float(next_row["Open"]),
                    high_price=float(next_row["High"]),
                    low_price=float(next_row["Low"]),
                    close_price=float(next_row["Close"]),
                    volume=int(next_row["Volume"]) if "Volume" in next_row else None,
                )
                
                # Calculate derived metrics
                if prev_close and prev_close > 0:
                    pd_.gap_pct = round((pd_.open_price - prev_close) / prev_close * 100, 2)
                    pd_.full_day_pct = round((pd_.close_price - prev_close) / prev_close * 100, 2)
                    pd_.max_up_pct = round((pd_.high_price - prev_close) / prev_close * 100, 2)
                    pd_.max_down_pct = round((pd_.low_price - prev_close) / prev_close * 100, 2)
                if pd_.open_price and pd_.open_price > 0:
                    pd_.intraday_pct = round((pd_.close_price - pd_.open_price) / pd_.open_price * 100, 2)
                
                results[nse_sym] = pd_
                
            except Exception as e:
                log.debug(f"Error processing {nse_sym}: {e}")
                continue
        
        if i + chunk_size < len(yf_symbols):
            time.sleep(1)  # Rate limit pause between batches
    
    return results


# ══════════════════════════════════════════════════════════════════════════
# Step 4: Evaluate each prediction
# ══════════════════════════════════════════════════════════════════════════

def evaluate_predictions(
    predictions: list[Prediction],
    prices: dict[str, PriceData],
) -> list[BacktestResult]:
    """Compare predictions against actual price moves."""
    results = []
    
    for pred in predictions:
        price = prices.get(pred.symbol)
        
        if not price or price.full_day_pct is None:
            results.append(BacktestResult(
                prediction=pred,
                price=None,
                verdict="NO_DATA",
                notes=f"No price data available for {pred.symbol}",
            ))
            continue
        
        actual_move = price.full_day_pct
        
        # Determine if direction was correct
        if pred.predicted_direction == "bullish":
            direction_correct = actual_move > 0
        else:  # bearish
            direction_correct = actual_move < 0
        
        # Classify the verdict
        if abs(actual_move) < 0.3:
            verdict = "FLAT"  # Less than 0.3% move, essentially flat
            notes = f"Stock barely moved ({actual_move:+.2f}%), inconclusive"
        elif direction_correct:
            if abs(actual_move) >= 3.0:
                verdict = "STRONG_HIT"
                notes = f"Strong move in predicted direction ({actual_move:+.2f}%)"
            elif abs(actual_move) >= 1.0:
                verdict = "HIT"
                notes = f"Stock moved in predicted direction ({actual_move:+.2f}%)"
            else:
                verdict = "WEAK_HIT"
                notes = f"Slight move in predicted direction ({actual_move:+.2f}%)"
        else:
            if abs(actual_move) >= 3.0:
                verdict = "STRONG_MISS"
                notes = f"Strong move AGAINST prediction ({actual_move:+.2f}% vs predicted {pred.predicted_direction})"
            elif abs(actual_move) >= 1.0:
                verdict = "MISS"
                notes = f"Moved against prediction ({actual_move:+.2f}% vs predicted {pred.predicted_direction})"
            else:
                verdict = "WEAK_MISS"
                notes = f"Slight move against prediction ({actual_move:+.2f}%)"
        
        results.append(BacktestResult(
            prediction=pred,
            price=price,
            direction_correct=direction_correct,
            actual_move_pct=actual_move,
            verdict=verdict,
            notes=notes,
        ))
    
    return results


# ══════════════════════════════════════════════════════════════════════════
# Step 5: Generate report
# ══════════════════════════════════════════════════════════════════════════

def generate_report(
    results: list[BacktestResult],
    prediction_date: str,
) -> str:
    """Generate a detailed markdown report of backtest results."""
    
    next_day = get_next_trading_day(date.fromisoformat(prediction_date))
    
    # Separate by direction
    bullish_results = [r for r in results if r.prediction.predicted_direction == "bullish"]
    bearish_results = [r for r in results if r.prediction.predicted_direction == "bearish"]
    
    # Calculate stats
    total = len(results)
    with_data = [r for r in results if r.verdict != "NO_DATA"]
    hits = [r for r in with_data if r.direction_correct is True]
    misses = [r for r in with_data if r.direction_correct is False]
    flat = [r for r in with_data if r.verdict == "FLAT"]
    strong_hits = [r for r in with_data if r.verdict == "STRONG_HIT"]
    strong_misses = [r for r in with_data if r.verdict == "STRONG_MISS"]
    no_data = [r for r in results if r.verdict == "NO_DATA"]
    
    # Calculate hit rate (excluding flat)
    actionable = [r for r in with_data if r.verdict != "FLAT"]
    hit_rate = len([r for r in actionable if r.direction_correct]) / len(actionable) * 100 if actionable else 0
    
    # Bullish hit rate
    bull_actionable = [r for r in bullish_results if r.verdict not in ("NO_DATA", "FLAT")]
    bull_hit_rate = len([r for r in bull_actionable if r.direction_correct]) / len(bull_actionable) * 100 if bull_actionable else 0
    
    # Bearish hit rate
    bear_actionable = [r for r in bearish_results if r.verdict not in ("NO_DATA", "FLAT")]
    bear_hit_rate = len([r for r in bear_actionable if r.direction_correct]) / len(bear_actionable) * 100 if bear_actionable else 0
    
    # Average move for hits vs misses
    hit_moves = [abs(r.actual_move_pct) for r in hits if r.actual_move_pct is not None]
    miss_moves = [abs(r.actual_move_pct) for r in misses if r.actual_move_pct is not None]
    avg_hit_magnitude = sum(hit_moves) / len(hit_moves) if hit_moves else 0
    avg_miss_magnitude = sum(miss_moves) / len(miss_moves) if miss_moves else 0
    
    # Category breakdown
    category_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "hits": 0, "misses": 0, "no_data": 0})
    for r in results:
        cat = r.prediction.news_category
        category_stats[cat]["total"] += 1
        if r.verdict == "NO_DATA":
            category_stats[cat]["no_data"] += 1
        elif r.direction_correct:
            category_stats[cat]["hits"] += 1
        elif r.direction_correct is False:
            category_stats[cat]["misses"] += 1
    
    # Classification tier breakdown
    tier_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "hits": 0, "misses": 0})
    for r in results:
        tier = r.prediction.classification
        tier_stats[tier]["total"] += 1
        if r.direction_correct is True:
            tier_stats[tier]["hits"] += 1
        elif r.direction_correct is False:
            tier_stats[tier]["misses"] += 1
    
    # Build report
    lines = []
    lines.append(f"# NewsEdge Backtest Report")
    lines.append(f"")
    lines.append(f"**Predictions from:** {prediction_date} (pipeline run)")
    lines.append(f"**Evaluated against:** {next_day} (next trading day)")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    
    # Summary stats
    lines.append(f"## Summary Statistics")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Predictions (unique symbols) | {total} |")
    lines.append(f"| With Price Data | {len(with_data)} |")
    lines.append(f"| No Price Data | {len(no_data)} |")
    lines.append(f"| **Overall Hit Rate** | **{hit_rate:.1f}%** ({len([r for r in actionable if r.direction_correct])}/{len(actionable)}) |")
    lines.append(f"| Bullish Hit Rate | {bull_hit_rate:.1f}% ({len([r for r in bull_actionable if r.direction_correct])}/{len(bull_actionable)}) |")
    lines.append(f"| Bearish Hit Rate | {bear_hit_rate:.1f}% ({len([r for r in bear_actionable if r.direction_correct])}/{len(bear_actionable)}) |")
    lines.append(f"| Strong Hits (≥3%) | {len(strong_hits)} |")
    lines.append(f"| Strong Misses (≥3%) | {len(strong_misses)} |")
    lines.append(f"| Flat (<0.3%) | {len(flat)} |")
    lines.append(f"| Avg Hit Magnitude | {avg_hit_magnitude:.2f}% |")
    lines.append(f"| Avg Miss Magnitude | {avg_miss_magnitude:.2f}% |")
    lines.append(f"")
    
    # Tier breakdown
    lines.append(f"## Hit Rate by Classification Tier")
    lines.append(f"")
    lines.append(f"| Tier | Total | Hits | Misses | Hit Rate |")
    lines.append(f"|------|-------|------|--------|----------|")
    for tier in ["strong_bullish", "bullish", "bearish", "strong_bearish"]:
        s = tier_stats.get(tier, {"total": 0, "hits": 0, "misses": 0})
        actionable_count = s["hits"] + s["misses"]
        rate = s["hits"] / actionable_count * 100 if actionable_count else 0
        lines.append(f"| {tier} | {s['total']} | {s['hits']} | {s['misses']} | {rate:.0f}% |")
    lines.append(f"")
    
    # Category breakdown
    lines.append(f"## Hit Rate by News Category")
    lines.append(f"")
    lines.append(f"| Category | Total | Hits | Misses | Hit Rate |")
    lines.append(f"|----------|-------|------|--------|----------|")
    for cat, s in sorted(category_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        actionable_count = s["hits"] + s["misses"]
        rate = s["hits"] / actionable_count * 100 if actionable_count else 0
        lines.append(f"| {cat} | {s['total']} | {s['hits']} | {s['misses']} | {rate:.0f}% |")
    lines.append(f"")
    
    # ── Detailed STRONG_BULLISH & STRONG_BEARISH Results ──
    lines.append(f"## High-Conviction Predictions (STRONG)")
    lines.append(f"")
    strong_preds = [r for r in results if "strong" in r.prediction.classification]
    if strong_preds:
        lines.append(f"| Symbol | Classification | Score | Headline | Actual Move | Verdict |")
        lines.append(f"|--------|---------------|-------|----------|-------------|---------|")
        for r in sorted(strong_preds, key=lambda x: x.prediction.overall_score, reverse=True):
            move = f"{r.actual_move_pct:+.2f}%" if r.actual_move_pct is not None else "N/A"
            icon = "✅" if r.direction_correct else ("❌" if r.direction_correct is False else "⚪")
            lines.append(
                f"| {r.prediction.symbol} | {r.prediction.classification} | "
                f"{r.prediction.overall_score:.1f} | "
                f"{r.prediction.headline[:60]}... | {move} | {icon} {r.verdict} |"
            )
    else:
        lines.append("_No strong predictions found._")
    lines.append(f"")
    
    # ── All Bullish Predictions ──
    lines.append(f"## All Bullish Predictions")
    lines.append(f"")
    lines.append(f"| # | Symbol | Score | Category | Headline | Gap% | Close% | Verdict |")
    lines.append(f"|---|--------|-------|----------|----------|------|--------|---------|")
    for i, r in enumerate(
        sorted(bullish_results, key=lambda x: x.prediction.overall_score, reverse=True), 1
    ):
        gap = f"{r.price.gap_pct:+.2f}" if r.price and r.price.gap_pct is not None else "N/A"
        move = f"{r.actual_move_pct:+.2f}" if r.actual_move_pct is not None else "N/A"
        icon = "✅" if r.direction_correct else ("❌" if r.direction_correct is False else "⚪")
        lines.append(
            f"| {i} | {r.prediction.symbol} | {r.prediction.overall_score:.1f} | "
            f"{r.prediction.news_category} | "
            f"{r.prediction.headline[:55]}... | {gap} | {move} | {icon} {r.verdict} |"
        )
    lines.append(f"")
    
    # ── All Bearish Predictions ──
    lines.append(f"## All Bearish Predictions")
    lines.append(f"")
    lines.append(f"| # | Symbol | Score | Category | Headline | Gap% | Close% | Verdict |")
    lines.append(f"|---|--------|-------|----------|----------|------|--------|---------|")
    for i, r in enumerate(
        sorted(bearish_results, key=lambda x: x.prediction.overall_score, reverse=True), 1
    ):
        gap = f"{r.price.gap_pct:+.2f}" if r.price and r.price.gap_pct is not None else "N/A"
        move = f"{r.actual_move_pct:+.2f}" if r.actual_move_pct is not None else "N/A"
        icon = "✅" if r.direction_correct else ("❌" if r.direction_correct is False else "⚪")
        lines.append(
            f"| {i} | {r.prediction.symbol} | {r.prediction.overall_score:.1f} | "
            f"{r.prediction.news_category} | "
            f"{r.prediction.headline[:55]}... | {gap} | {move} | {icon} {r.verdict} |"
        )
    lines.append(f"")
    
    # ── Strong Misses Analysis ──
    lines.append(f"## Analysis: Strong Misses (≥1% against prediction)")
    lines.append(f"")
    strong_miss_results = [
        r for r in results
        if r.direction_correct is False and r.actual_move_pct is not None and abs(r.actual_move_pct) >= 1.0
    ]
    if strong_miss_results:
        for r in sorted(strong_miss_results, key=lambda x: abs(x.actual_move_pct or 0), reverse=True):
            lines.append(f"### {r.prediction.symbol} — Predicted {r.prediction.predicted_direction.upper()}, moved {r.actual_move_pct:+.2f}%")
            lines.append(f"")
            lines.append(f"- **Headline:** {r.prediction.headline}")
            lines.append(f"- **Category:** {r.prediction.news_category}")
            lines.append(f"- **Score:** {r.prediction.overall_score:.1f} (impact={r.prediction.impact_score:.0f}, conf={r.prediction.confidence:.0f})")
            lines.append(f"- **Classification:** {r.prediction.classification}")
            if r.price:
                lines.append(f"- **Price Action:** Prev Close={r.price.prev_close:.2f}, Open={r.price.open_price:.2f} (gap={r.price.gap_pct:+.2f}%), Close={r.price.close_price:.2f}")
                lines.append(f"- **Day Range:** Low={r.price.low_price:.2f} ({r.price.max_down_pct:+.2f}%), High={r.price.high_price:.2f} ({r.price.max_up_pct:+.2f}%)")
            lines.append(f"- **Why missed:** Likely reasons below")
            
            # Auto-generate possible miss reasons
            reasons = []
            if "buy" in r.prediction.headline.lower() or "rating" in r.prediction.headline.lower() or "upside" in r.prediction.headline.lower():
                reasons.append("Analyst rating/target — often already priced in, weak catalyst")
            if "data centre" in r.prediction.headline.lower() or "data center" in r.prediction.headline.lower():
                reasons.append("Sectoral thematic — indirect beneficiary, weak company-specific linkage")
            if r.prediction.news_category == "ORDER_WIN" and r.prediction.impact_score < 80:
                reasons.append("Order win may be routine or already market-known")
            if "Q2" in r.prediction.headline or "results" in r.prediction.headline.lower():
                reasons.append("Q2 results news — stock may have already reacted on result day itself")
            if r.prediction.news_category == "REGULATORY_ACTION":
                reasons.append("Regulatory action — market may see it differently or impact is limited")
            if not reasons:
                reasons.append("Needs manual review of market context and broader sentiment")
            
            for reason in reasons:
                lines.append(f"  - {reason}")
            lines.append(f"")
    else:
        lines.append("_No strong misses found. Excellent performance!_")
    lines.append(f"")
    
    # ── Recommendations ──
    lines.append(f"## Recommendations for Tuning")
    lines.append(f"")
    
    # Analyze which categories perform worst
    worst_categories = []
    for cat, s in category_stats.items():
        act = s["hits"] + s["misses"]
        if act >= 3:  # Minimum sample size
            rate = s["hits"] / act * 100
            if rate < 50:
                worst_categories.append((cat, rate, act))
    
    if worst_categories:
        lines.append("### Low-Accuracy Categories")
        for cat, rate, act in sorted(worst_categories, key=lambda x: x[1]):
            lines.append(f"- **{cat}**: {rate:.0f}% hit rate over {act} predictions — consider raising score thresholds or adding exclusion rules")
    
    lines.append(f"")
    lines.append("---")
    lines.append(f"_Report generated by NewsEdge Backtester v1.0_")
    
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 60)
    log.info("NEWSEDGE PREDICTION BACKTEST")
    log.info("=" * 60)
    
    # Step 1: Extract predictions
    log.info("[1/5] Extracting predictions from database...")
    all_predictions = extract_predictions()
    
    if not all_predictions:
        log.error("No BULLISH/BEARISH predictions found in database!")
        return
    
    for pred_date, preds in all_predictions.items():
        log.info(f"  Date {pred_date}: {len(preds)} raw predictions")
    
    # Process each prediction date
    for pred_date, raw_preds in sorted(all_predictions.items()):
        log.info(f"\n{'='*60}")
        log.info(f"Processing predictions for: {pred_date}")
        log.info(f"{'='*60}")
        
        # Step 2: Deduplicate
        log.info(f"[2/5] Deduplicating {len(raw_preds)} predictions...")
        deduped = deduplicate_predictions(raw_preds)
        log.info(f"  {len(deduped)} unique symbols after dedup")
        
        bullish_count = sum(1 for p in deduped if p.predicted_direction == "bullish")
        bearish_count = sum(1 for p in deduped if p.predicted_direction == "bearish")
        log.info(f"  Bullish: {bullish_count}, Bearish: {bearish_count}")
        
        # Step 3: Fetch prices
        symbols = [p.symbol for p in deduped]
        log.info(f"[3/5] Fetching next-day prices for {len(symbols)} symbols...")
        prices = fetch_prices_batch(symbols, date.fromisoformat(pred_date))
        log.info(f"  Got price data for {len(prices)} of {len(symbols)} symbols")
        
        # Step 4: Evaluate
        log.info("[4/5] Evaluating predictions against actual moves...")
        results = evaluate_predictions(deduped, prices)
        
        # Print quick summary to console
        hits = sum(1 for r in results if r.direction_correct is True)
        misses = sum(1 for r in results if r.direction_correct is False)
        no_data = sum(1 for r in results if r.verdict == "NO_DATA")
        flat = sum(1 for r in results if r.verdict == "FLAT")
        actionable = hits + misses
        hit_rate = hits / actionable * 100 if actionable else 0
        
        log.info(f"  RESULTS: Hits={hits} | Misses={misses} | Flat={flat} | No Data={no_data}")
        log.info(f"  HIT RATE: {hit_rate:.1f}% ({hits}/{actionable} actionable)")
        
        # Print top hits
        log.info("\n  Top Correct Predictions:")
        for r in sorted(
            [r for r in results if r.direction_correct],
            key=lambda x: abs(x.actual_move_pct or 0),
            reverse=True,
        )[:10]:
            log.info(f"    ✅ {r.prediction.symbol:15s} | {r.actual_move_pct:+6.2f}% | {r.prediction.headline[:60]}")
        
        # Print misses
        log.info("\n  Biggest Misses:")
        for r in sorted(
            [r for r in results if r.direction_correct is False],
            key=lambda x: abs(x.actual_move_pct or 0),
            reverse=True,
        )[:10]:
            log.info(f"    ❌ {r.prediction.symbol:15s} | {r.actual_move_pct:+6.2f}% (predicted {r.prediction.predicted_direction}) | {r.prediction.headline[:50]}")
        
        # Step 5: Generate report
        log.info(f"\n[5/5] Generating detailed report...")
        report = generate_report(results, pred_date)
        
        # Save report
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        report_path = reports_dir / f"backtest_{pred_date}.md"
        report_path.write_text(report, encoding="utf-8")
        log.info(f"  Report saved to: {report_path}")
        
        # Also save raw JSON data for further analysis
        json_data = []
        for r in results:
            entry = {
                "symbol": r.prediction.symbol,
                "company": r.prediction.company_name,
                "classification": r.prediction.classification,
                "predicted_direction": r.prediction.predicted_direction,
                "score": r.prediction.overall_score,
                "impact": r.prediction.impact_score,
                "confidence": r.prediction.confidence,
                "category": r.prediction.news_category,
                "headline": r.prediction.headline,
                "verdict": r.verdict,
                "direction_correct": r.direction_correct,
                "actual_move_pct": r.actual_move_pct,
                "gap_pct": r.price.gap_pct if r.price else None,
                "max_up_pct": r.price.max_up_pct if r.price else None,
                "max_down_pct": r.price.max_down_pct if r.price else None,
            }
            json_data.append(entry)
        
        json_path = reports_dir / f"backtest_{pred_date}.json"
        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info(f"  JSON data saved to: {json_path}")
    
    log.info("\n" + "=" * 60)
    log.info("BACKTEST COMPLETE")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
