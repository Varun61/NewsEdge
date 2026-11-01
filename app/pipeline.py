"""NewsEdge daily batch pipeline.

This is the daily batch-processing job.
- When run on Monday (or standard scheduled 8:00 AM IST trading days):
  Collects all news from the previous trading day (Friday) 15:30 IST up to Monday 07:59 IST,
  including all news published over the weekend (Saturday and Sunday).
- When run on-demand / ad-hoc (e.g. now, or on a weekend):
  Automatically collects the last 24 hours of news data.
- Every run rebuilds a fresh watchlist (clears previous temporary state).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date

from sqlalchemy import delete

from app.config import get_settings
from app.database.database import get_session, init_db
from app.database.models import (
    DailyWatchlist,
    DailyWatchlistItem,
    NewsEvent,
    NewsEventArticle,
    RawArticle,
    StockAnalysis,
)
from app.logger import setup_logging
from app.trading_calendar import (
    get_effective_collection_window,
    is_trading_day,
    now_ist,
    today_ist,
)
from scripts.initialize_database import seed_database

logger = logging.getLogger("newsedge.pipeline")


def clean_previous_run_data(session) -> None:
    """Clear previous pipeline data so each run rebuilds a 100% fresh watchlist."""
    logger.info("Clearing previous run state for fresh watchlist generation...")
    session.execute(delete(DailyWatchlistItem))
    session.execute(delete(DailyWatchlist))
    session.execute(delete(StockAnalysis))
    session.execute(delete(NewsEventArticle))
    session.execute(delete(NewsEvent))
    session.execute(delete(RawArticle))
    session.commit()
    logger.info("Previous run state cleared successfully.")


def run_pipeline(
    report_date: date | None = None,
    lookback_hours: int | None = None,
    is_adhoc: bool = True,
    fresh_rebuild: bool = True,
) -> bool:
    """Execute the batch processing job. Returns True on success."""
    setup_logging()
    settings = get_settings()
    init_db()

    target_date = report_date or today_ist()

    logger.info("=" * 60)
    logger.info("NewsEdge Batch Pipeline Starting")
    logger.info("Target date: %s", target_date)
    logger.info("Current IST time: %s", now_ist().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # Calculate effective collection window
    window_start, window_end, window_desc = get_effective_collection_window(
        report_date=target_date,
        lookback_hours=lookback_hours,
        is_adhoc=is_adhoc,
        start_hour=settings.collection_start_hour,
        start_minute=settings.collection_start_minute,
        end_hour=settings.collection_end_hour,
        end_minute=settings.collection_end_minute,
    )

    logger.info("Active Collection Window: %s", window_desc)
    logger.info(
        "Window UTC bounds: %s  -->  %s",
        window_start.strftime("%Y-%m-%d %H:%M:%S UTC"),
        window_end.strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    # Ensure master company universe is populated
    try:
        seed_database()
    except Exception as exc:
        logger.debug("Database seeding check: %s", exc)

    with get_session() as session:
        # Fresh rebuild: wipe old analyses/watchlists/events if requested
        if fresh_rebuild:
            clean_previous_run_data(session)

        # ── Step 1: News Collection ──────────────────────────────
        logger.info("[1/5] Collecting news from enabled sources...")
        from app.services.collection_service import CollectionService
        collector_svc = CollectionService(session)
        collection_res = collector_svc.run_collection(window_start, window_end)
        logger.info(
            "Collection finished: %d total found, %d new articles persisted across %d/%d sources.",
            collection_res.total_articles_found,
            collection_res.new_articles,
            collection_res.successful_sources,
            collection_res.total_sources_checked,
        )

        # ── Step 2: News Processing & AI Intelligence ────────────
        logger.info("[2/5] Deduplicating, classifying, and scoring candidates...")
        from app.intelligence.provider_factory import get_ai_provider
        from app.services.analysis_service import AnalysisService

        ai = get_ai_provider()
        analysis_svc = AnalysisService(session, ai)
        analysis_res = analysis_svc.run_analysis(collection_res.new_article_ids)
        logger.info(
            "Analysis finished: %d unique events, %d scored candidate records.",
            analysis_res.total_events,
            len(analysis_res.scored_analyses),
        )

        # ── Step 3: Build Daily Watchlist ────────────────────────
        logger.info("[3/5] Building ranked watchlist...")
        from app.services.report_service import ReportService
        report_svc = ReportService(session, settings)
        watchlist = report_svc.generate_report(target_date, collection_res, analysis_res)

        # ── Step 4: Dispatch Telegram Report ─────────────────────
        logger.info("[4/5] Sending Telegram watchlist report...")
        try:
            delivered = asyncio.run(
                report_svc.send_telegram_report(watchlist, window_description=window_desc)
            )
            if delivered:
                logger.info("Telegram notification delivered successfully.")
            else:
                logger.warning("Telegram notification skipped or failed (check bot token/chat ID).")
        except Exception as exc:
            logger.error("Error during Telegram delivery: %s", exc)

        # ── Step 5: Groww Watchlist Sync & Export ────────────────
        logger.info("[5/6] Synchronizing Groww watchlists and generating symbol exports...")
        try:
            from app.database.models import CandidateClassification
            from app.integrations.groww_sync import GrowwWatchlistSync
            groww_sync = GrowwWatchlistSync(
                auth_token=settings.groww_auth_token,
                email=settings.groww_email,
                password=settings.groww_password,
                totp_secret=settings.groww_totp_secret,
            )

            top_bull_items = []
            top_bear_items = []
            seen_comps = set()
            for it in sorted(watchlist.items, key=lambda x: x.rank_position):
                a = it.stock_analysis
                if not a or not a.company:
                    continue
                cid = a.company.id
                if cid in seen_comps:
                    continue
                item_data = {
                    "symbol": a.company.nse_symbol,
                    "company_name": a.company.company_name,
                    "score": f"{a.overall_score:.0f}",
                    "headline": a.news_event.primary_headline if a.news_event else "",
                }
                if a.classification in (CandidateClassification.STRONG_BULLISH, CandidateClassification.BULLISH):
                    if len(top_bull_items) < 10:
                        seen_comps.add(cid)
                        top_bull_items.append(item_data)
                elif a.classification in (CandidateClassification.STRONG_BEARISH, CandidateClassification.BEARISH):
                    if len(top_bear_items) < 10:
                        seen_comps.add(cid)
                        top_bear_items.append(item_data)

            groww_res = groww_sync.process_sync(top_bull_items, top_bear_items, settings.reports_dir)
            if groww_res.success:
                logger.info("Groww account watchlists updated: %d Bullish, %d Bearish", groww_res.bullish_synced, groww_res.bearish_synced)
            else:
                logger.info("Groww offline watchlists generated in: %s", settings.reports_dir)
        except Exception as exc:
            logger.error("Groww sync error: %s", exc)

        # ── Step 6: Export Local HTML & Excel Reports ────────────
        logger.info("[6/6] Exporting local HTML and Excel reports...")
        try:
            html_file = report_svc.generate_html(watchlist)
            logger.info("HTML report saved: %s", html_file)
        except Exception as exc:
            logger.error("Failed to export HTML report: %s", exc)

        try:
            excel_file = report_svc.generate_excel(watchlist)
            logger.info("Excel report saved: %s", excel_file)
        except Exception as exc:
            logger.error("Failed to export Excel report: %s", exc)

    logger.info("NewsEdge Pipeline Completed Successfully.")
    return True


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="NewsEdge Indian Stock Intelligence Pipeline")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target report date in YYYY-MM-DD format (defaults to current date in IST)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=None,
        help="Explicit lookback window in hours (e.g. --hours 24 to collect last 24 hours of news)",
    )
    parser.add_argument(
        "--cron",
        action="store_true",
        help="Set this flag when executed from automated cron at 08:00 AM IST to enforce trading day skips",
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Preserve existing events from previous runs instead of starting fresh",
    )
    args = parser.parse_args()

    target_date = None
    if args.date:
        from datetime import datetime
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    if args.cron and not args.hours and not args.date:
        if not is_trading_day(today_ist()):
            logger.info("Scheduled cron execution: today is not a trading day. Exiting cleanly.")
            sys.exit(0)

    success = run_pipeline(
        report_date=target_date,
        lookback_hours=args.hours,
        is_adhoc=not args.cron,
        fresh_rebuild=not args.no_rebuild,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
