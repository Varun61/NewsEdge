"""Repository — data-access helpers for every major entity."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.models import (
    CollectionRun,
    Company,
    CompanyAlias,
    DailyWatchlist,
    DailyWatchlistItem,
    HistoricalPerformance,
    MarketSnapshot,
    NewsEvent,
    NewsEventArticle,
    NewsSource,
    RawArticle,
    StockAnalysis,
    SystemLog,
    CandidateClassification,
)


class Repository:
    """Static data-access methods.  Every public method takes an
    explicit ``session`` so the caller controls the transaction."""

    # ── NewsSource ──────────────────────────────────────────────────

    @staticmethod
    def create_source(session: Session, **kwargs) -> NewsSource:
        source = NewsSource(**kwargs)
        session.add(source)
        session.flush()
        return source

    @staticmethod
    def get_source_by_id(session: Session, source_id: int) -> Optional[NewsSource]:
        return session.get(NewsSource, source_id)

    @staticmethod
    def get_source_by_name(session: Session, name: str) -> Optional[NewsSource]:
        return session.scalar(select(NewsSource).where(NewsSource.name == name))

    @staticmethod
    def get_enabled_sources(session: Session) -> list[NewsSource]:
        return list(session.scalars(select(NewsSource).where(NewsSource.enabled.is_(True))))

    @staticmethod
    def update_source_status(
        session: Session,
        source_id: int,
        *,
        last_collected_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ) -> None:
        source = session.get(NewsSource, source_id)
        if source is None:
            return
        if last_collected_at is not None:
            source.last_collected_at = last_collected_at
        source.last_error = last_error

    # ── RawArticle ──────────────────────────────────────────────────

    @staticmethod
    def create_article(session: Session, **kwargs) -> RawArticle:
        article = RawArticle(**kwargs)
        session.add(article)
        session.flush()
        return article

    @staticmethod
    def get_article_by_url(session: Session, url: str) -> Optional[RawArticle]:
        return session.scalar(select(RawArticle).where(RawArticle.article_url == url))

    @staticmethod
    def get_article_by_hash(session: Session, content_hash: str) -> Optional[RawArticle]:
        return session.scalar(
            select(RawArticle).where(RawArticle.content_hash == content_hash)
        )

    @staticmethod
    def get_articles_in_window(
        session: Session, start_utc: datetime, end_utc: datetime
    ) -> list[RawArticle]:
        return list(
            session.scalars(
                select(RawArticle)
                .where(RawArticle.discovered_at >= start_utc)
                .where(RawArticle.discovered_at <= end_utc)
                .order_by(RawArticle.discovered_at.desc())
            )
        )

    @staticmethod
    def get_unprocessed_articles(session: Session) -> list[RawArticle]:
        """Articles not yet linked to any NewsEvent."""
        linked_ids = select(NewsEventArticle.raw_article_id).scalar_subquery()
        return list(
            session.scalars(
                select(RawArticle).where(RawArticle.id.notin_(linked_ids))
            )
        )

    # ── Company ─────────────────────────────────────────────────────

    @staticmethod
    def create_company(session: Session, **kwargs) -> Company:
        company = Company(**kwargs)
        session.add(company)
        session.flush()
        return company

    @staticmethod
    def get_company_by_symbol(session: Session, symbol: str) -> Optional[Company]:
        return session.scalar(
            select(Company).where(func.upper(Company.nse_symbol) == symbol.upper())
        )

    @staticmethod
    def get_company_by_isin(session: Session, isin: str) -> Optional[Company]:
        return session.scalar(select(Company).where(Company.isin == isin))

    @staticmethod
    def search_companies(session: Session, query: str) -> list[Company]:
        pattern = f"%{query}%"
        return list(
            session.scalars(
                select(Company).where(
                    Company.company_name.ilike(pattern)
                    | Company.nse_symbol.ilike(pattern)
                )
            )
        )

    @staticmethod
    def get_all_active_companies(session: Session) -> list[Company]:
        return list(
            session.scalars(select(Company).where(Company.is_active.is_(True)))
        )

    @staticmethod
    def bulk_upsert_companies(session: Session, companies_data: list[dict]) -> int:
        """Insert companies that don't already exist.  Returns count of new rows."""
        added = 0
        for data in companies_data:
            existing = session.scalar(
                select(Company).where(
                    func.upper(Company.nse_symbol) == data["nse_symbol"].upper()
                )
            )
            if existing is None:
                session.add(Company(**data))
                added += 1
        session.flush()
        return added

    # ── CompanyAlias ────────────────────────────────────────────────

    @staticmethod
    def create_alias(
        session: Session,
        company_id: int,
        alias_name: str,
        alias_type: str = "common_name",
        confidence: float = 1.0,
    ) -> CompanyAlias:
        alias = CompanyAlias(
            company_id=company_id,
            alias_name=alias_name,
            alias_type=alias_type,
            confidence=confidence,
        )
        session.add(alias)
        session.flush()
        return alias

    @staticmethod
    def find_company_by_alias(session: Session, alias_name: str) -> Optional[Company]:
        alias = session.scalar(
            select(CompanyAlias).where(
                func.lower(CompanyAlias.alias_name) == alias_name.lower()
            )
        )
        if alias is None:
            return None
        return session.get(Company, alias.company_id)

    # ── NewsEvent ───────────────────────────────────────────────────

    @staticmethod
    def create_event(session: Session, **kwargs) -> NewsEvent:
        event = NewsEvent(**kwargs)
        session.add(event)
        session.flush()
        return event

    @staticmethod
    def get_event_by_hash(session: Session, event_hash: str) -> Optional[NewsEvent]:
        return session.scalar(
            select(NewsEvent).where(NewsEvent.event_hash == event_hash)
        )

    @staticmethod
    def get_unprocessed_events(session: Session) -> list[NewsEvent]:
        return list(
            session.scalars(
                select(NewsEvent).where(NewsEvent.is_processed.is_(False))
            )
        )

    @staticmethod
    def get_events_in_window(
        session: Session, start_utc: datetime, end_utc: datetime
    ) -> list[NewsEvent]:
        return list(
            session.scalars(
                select(NewsEvent)
                .where(NewsEvent.created_at >= start_utc)
                .where(NewsEvent.created_at <= end_utc)
            )
        )

    @staticmethod
    def link_article_to_event(
        session: Session,
        event_id: int,
        article_id: int,
        is_primary: bool = False,
    ) -> NewsEventArticle:
        link = NewsEventArticle(
            news_event_id=event_id,
            raw_article_id=article_id,
            is_primary=is_primary,
        )
        session.add(link)
        session.flush()
        return link

    # ── StockAnalysis ───────────────────────────────────────────────

    @staticmethod
    def create_analysis(session: Session, **kwargs) -> StockAnalysis:
        analysis = StockAnalysis(**kwargs)
        session.add(analysis)
        session.flush()
        return analysis

    @staticmethod
    def get_analyses_for_date(session: Session, target_date: date) -> list[StockAnalysis]:
        from datetime import timedelta
        end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
        start = end - timedelta(hours=36)
        return list(
            session.scalars(
                select(StockAnalysis)
                .where(StockAnalysis.created_at >= start)
                .where(StockAnalysis.created_at <= end)
                .order_by(StockAnalysis.overall_score.desc())
            )
        )

    @staticmethod
    def get_bullish_candidates(
        session: Session, target_date: date, min_score: float = 60.0
    ) -> list[StockAnalysis]:
        from datetime import timedelta
        end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
        start = end - timedelta(hours=36)
        return list(
            session.scalars(
                select(StockAnalysis)
                .where(StockAnalysis.created_at >= start)
                .where(StockAnalysis.created_at <= end)
                .where(StockAnalysis.overall_score >= min_score)
                .where(
                    StockAnalysis.classification.in_([
                        CandidateClassification.STRONG_BULLISH,
                        CandidateClassification.BULLISH,
                    ])
                )
                .order_by(StockAnalysis.overall_score.desc())
            )
        )

    @staticmethod
    def get_bearish_candidates(
        session: Session, target_date: date, min_score: float = 60.0
    ) -> list[StockAnalysis]:
        from datetime import timedelta
        end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
        start = end - timedelta(hours=36)
        return list(
            session.scalars(
                select(StockAnalysis)
                .where(StockAnalysis.created_at >= start)
                .where(StockAnalysis.created_at <= end)
                .where(StockAnalysis.overall_score >= min_score)
                .where(
                    StockAnalysis.classification.in_([
                        CandidateClassification.STRONG_BEARISH,
                        CandidateClassification.BEARISH,
                    ])
                )
                .order_by(StockAnalysis.overall_score.desc())
            )
        )

    # ── DailyWatchlist ──────────────────────────────────────────────

    @staticmethod
    def create_watchlist(session: Session, **kwargs) -> DailyWatchlist:
        wl = DailyWatchlist(**kwargs)
        session.add(wl)
        session.flush()
        return wl

    @staticmethod
    def get_watchlist_by_date(session: Session, report_date: date) -> Optional[DailyWatchlist]:
        return session.scalar(
            select(DailyWatchlist).where(DailyWatchlist.report_date == report_date)
        )

    @staticmethod
    def mark_delivered(session: Session, watchlist_id: int, delivered_at: datetime) -> None:
        wl = session.get(DailyWatchlist, watchlist_id)
        if wl:
            wl.is_delivered = True
            wl.delivered_at = delivered_at

    @staticmethod
    def add_watchlist_item(
        session: Session, watchlist_id: int, analysis_id: int, rank: int
    ) -> DailyWatchlistItem:
        item = DailyWatchlistItem(
            watchlist_id=watchlist_id,
            stock_analysis_id=analysis_id,
            rank_position=rank,
        )
        session.add(item)
        session.flush()
        return item

    # ── CollectionRun ───────────────────────────────────────────────

    @staticmethod
    def create_run(session: Session, **kwargs) -> CollectionRun:
        run = CollectionRun(**kwargs)
        session.add(run)
        session.flush()
        return run

    @staticmethod
    def complete_run(
        session: Session,
        run_id: int,
        *,
        articles_found: int = 0,
        articles_new: int = 0,
        articles_duplicate: int = 0,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> None:
        run = session.get(CollectionRun, run_id)
        if run:
            run.completed_at = datetime.now(timezone.utc)
            run.articles_found = articles_found
            run.articles_new = articles_new
            run.articles_duplicate = articles_duplicate
            run.status = status
            run.error_message = error

    # ── HistoricalPerformance ───────────────────────────────────────

    @staticmethod
    def create_performance(session: Session, **kwargs) -> HistoricalPerformance:
        perf = HistoricalPerformance(**kwargs)
        session.add(perf)
        session.flush()
        return perf

    # ── MarketSnapshot ──────────────────────────────────────────────

    @staticmethod
    def create_snapshot(session: Session, **kwargs) -> MarketSnapshot:
        snap = MarketSnapshot(**kwargs)
        session.add(snap)
        session.flush()
        return snap

    @staticmethod
    def get_snapshot(
        session: Session, company_id: int, snapshot_date: date
    ) -> Optional[MarketSnapshot]:
        return session.scalar(
            select(MarketSnapshot)
            .where(MarketSnapshot.company_id == company_id)
            .where(MarketSnapshot.snapshot_date == snapshot_date)
        )

    # ── SystemLog ───────────────────────────────────────────────────

    @staticmethod
    def log(
        session: Session,
        level: str,
        module: str,
        message: str,
        details: Optional[dict] = None,
    ) -> SystemLog:
        entry = SystemLog(level=level, module=module, message=message, details=details)
        session.add(entry)
        session.flush()
        return entry
