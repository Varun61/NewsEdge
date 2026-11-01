"""Report generation and multi-channel delivery service."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.models import DailyWatchlist, DailyWatchlistItem, StockAnalysis
from app.database.repository import Repository
from app.reporting.excel_report import ExcelReportGenerator
from app.reporting.html_report import HTMLReportGenerator
from app.reporting.telegram_bot import TelegramBot
from app.reporting.telegram_formatter import TelegramFormatter
from app.services.analysis_service import AnalysisResult
from app.services.collection_service import CollectionResult

logger = logging.getLogger("newsedge.services.reporting")


class ReportService:
    """Creates watchlists, formats messages, triggers Telegram delivery, and saves reports."""

    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.bot = TelegramBot(settings)

    def generate_report(
        self,
        report_date: date,
        collection_result: CollectionResult,
        analysis_result: AnalysisResult,
    ) -> DailyWatchlist:
        """Construct DailyWatchlist entity from scored candidates and persist ranked items."""
        now = datetime.now(timezone.utc)

        # Check existing watchlist for today or create new
        watchlist = Repository.get_watchlist_by_date(self.session, report_date)
        if not watchlist:
            watchlist = Repository.create_watchlist(
                session=self.session,
                report_date=report_date,
                generated_at=now,
                scoring_version="1.0",
                total_events=analysis_result.total_events,
                total_sources_checked=collection_result.total_sources_checked,
                successful_sources=collection_result.successful_sources,
                is_delivered=False,
            )
        else:
            watchlist.generated_at = now
            watchlist.total_events = analysis_result.total_events
            watchlist.total_sources_checked = collection_result.total_sources_checked
            watchlist.successful_sources = collection_result.successful_sources
            # Clear previous items so re-running refreshes cleanly
            self.session.execute(
                delete(DailyWatchlistItem).where(DailyWatchlistItem.watchlist_id == watchlist.id)
            )

        # Fetch candidate analyses for this report date
        analyses: List[StockAnalysis] = Repository.get_analyses_for_date(self.session, report_date)
        if analysis_result.scored_analyses:
            existing_ids = {a.id for a in analyses}
            additional = list(
                self.session.scalars(
                    select(StockAnalysis).where(StockAnalysis.id.in_(analysis_result.scored_analyses))
                )
            )
            for a in additional:
                if a.id not in existing_ids:
                    analyses.append(a)

        # Rank candidates by overall score descending
        analyses.sort(key=lambda a: a.overall_score, reverse=True)

        for rank, a in enumerate(analyses, 1):
            Repository.add_watchlist_item(
                session=self.session,
                watchlist_id=watchlist.id,
                analysis_id=a.id,
                rank=rank,
            )

        self.session.commit()
        logger.info(
            "Watchlist #%d populated with %d ranked items for %s",
            watchlist.id,
            len(analyses),
            report_date,
        )
        return watchlist

    async def send_telegram_report(
        self, watchlist: DailyWatchlist, window_description: Optional[str] = None
    ) -> bool:
        """Format and dispatch daily report via Telegram Bot."""
        if not self.settings.telegram_bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured. Skipping Telegram delivery.")
            return False

        message_chunks = TelegramFormatter.format_daily_report(
            watchlist, self.session, window_description=window_description
        )
        success = await self.bot.send_daily_report(message_chunks)

        if success:
            Repository.mark_delivered(self.session, watchlist.id, datetime.now(timezone.utc))
            self.session.commit()

        return success

    def generate_html(self, watchlist: DailyWatchlist) -> Path:
        """Export watchlist to HTML in the reports directory."""
        return HTMLReportGenerator.save(watchlist, self.session, self.settings.reports_dir)

    def generate_excel(self, watchlist: DailyWatchlist) -> Path:
        """Export watchlist to Excel in the reports directory."""
        return ExcelReportGenerator.generate(watchlist, self.session, self.settings.reports_dir)
