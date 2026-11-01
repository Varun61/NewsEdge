"""SQLAlchemy 2.0 ORM models for NewsEdge.

All timestamps are stored as UTC.  Display in IST is handled at the
application / reporting layer.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    BigInteger,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ═══════════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════════

class SourceType(str, enum.Enum):
    RSS = "rss"
    API = "api"
    WEB = "web"
    OFFICIAL = "official"


class CollectionStatus(str, enum.Enum):
    PENDING = "pending"
    COLLECTED = "collected"
    FAILED = "failed"
    SKIPPED = "skipped"


class NewsCategory(str, enum.Enum):
    ORDER_WIN = "ORDER_WIN"
    QUARTERLY_RESULTS = "QUARTERLY_RESULTS"
    REVENUE_GROWTH = "REVENUE_GROWTH"
    PROFIT_GROWTH = "PROFIT_GROWTH"
    PROFIT_WARNING = "PROFIT_WARNING"
    ACQUISITION = "ACQUISITION"
    MERGER = "MERGER"
    FUND_RAISE = "FUND_RAISE"
    DEBT_REDUCTION = "DEBT_REDUCTION"
    CAPACITY_EXPANSION = "CAPACITY_EXPANSION"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    REGULATORY_APPROVAL = "REGULATORY_APPROVAL"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    LEGAL_ISSUE = "LEGAL_ISSUE"
    FRAUD_OR_GOVERNANCE = "FRAUD_OR_GOVERNANCE"
    PROMOTER_ACTIVITY = "PROMOTER_ACTIVITY"
    DIVIDEND = "DIVIDEND"
    BUYBACK = "BUYBACK"
    SHAREHOLDING_CHANGE = "SHAREHOLDING_CHANGE"
    CONTRACT_CANCELLATION = "CONTRACT_CANCELLATION"
    BUSINESS_UPDATE = "BUSINESS_UPDATE"
    OTHER = "OTHER"


class Sentiment(str, enum.Enum):
    VERY_POSITIVE = "VERY_POSITIVE"
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    VERY_NEGATIVE = "VERY_NEGATIVE"
    MIXED = "MIXED"


class MarketCapCategory(str, enum.Enum):
    LARGE_CAP = "large_cap"
    MID_CAP = "mid_cap"
    SMALL_CAP = "small_cap"
    MICRO_CAP = "micro_cap"


class CandidateClassification(str, enum.Enum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    STRONG_BEARISH = "strong_bearish"
    BEARISH = "bearish"
    WATCH_ONLY = "watch_only"
    EXCLUDED = "excluded"


# ═══════════════════════════════════════════════════════════════════════
# Base
# ═══════════════════════════════════════════════════════════════════════

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════════════
# 1. NewsSource
# ═══════════════════════════════════════════════════════════════════════

class NewsSource(Base):
    __tablename__ = "news_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(SAEnum(SourceType), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    collection_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collection_frequency_minutes: Mapped[int] = mapped_column(Integer, default=15)
    last_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60)
    credibility_score: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    articles: Mapped[list["RawArticle"]] = relationship(back_populates="source", lazy="selectin")

    def __repr__(self) -> str:
        return f"<NewsSource(id={self.id}, name='{self.name}', type={self.source_type.value})>"


# ═══════════════════════════════════════════════════════════════════════
# 2. RawArticle
# ═══════════════════════════════════════════════════════════════════════

class RawArticle(Base):
    __tablename__ = "raw_articles"
    __table_args__ = (
        Index("ix_raw_articles_content_hash", "content_hash"),
        Index("ix_raw_articles_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_sources.id"), nullable=False)
    headline: Mapped[str] = mapped_column(String(1000), nullable=False)
    article_url: Mapped[str] = mapped_column(String(2000), unique=True, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_mentions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_credibility: Mapped[float] = mapped_column(Float, default=0.5)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    collection_status: Mapped[CollectionStatus] = mapped_column(
        SAEnum(CollectionStatus), default=CollectionStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    source: Mapped["NewsSource"] = relationship(back_populates="articles", lazy="selectin")
    event_links: Mapped[list["NewsEventArticle"]] = relationship(back_populates="article", lazy="selectin")

    def __repr__(self) -> str:
        return f"<RawArticle(id={self.id}, headline='{self.headline[:60]}...')>"


# ═══════════════════════════════════════════════════════════════════════
# 3. Company
# ═══════════════════════════════════════════════════════════════════════

class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_nse_symbol", "nse_symbol", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nse_symbol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False)
    isin: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    market_cap_category: Mapped[Optional[MarketCapCategory]] = mapped_column(
        SAEnum(MarketCapCategory), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    annual_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    aliases: Mapped[list["CompanyAlias"]] = relationship(back_populates="company", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, symbol='{self.nse_symbol}', name='{self.company_name}')>"


# ═══════════════════════════════════════════════════════════════════════
# 4. CompanyAlias
# ═══════════════════════════════════════════════════════════════════════

class CompanyAlias(Base):
    __tablename__ = "company_aliases"
    __table_args__ = (
        Index("ix_company_aliases_alias_name", "alias_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    alias_name: Mapped[str] = mapped_column(String(300), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(50), nullable=False)  # abbreviation, brand, subsidiary, common_name
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="aliases", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CompanyAlias(id={self.id}, alias='{self.alias_name}', company_id={self.company_id})>"


# ═══════════════════════════════════════════════════════════════════════
# 5. NewsEvent  (a deduplicated, unique news happening)
# ═══════════════════════════════════════════════════════════════════════

class NewsEvent(Base):
    __tablename__ = "news_events"
    __table_args__ = (
        Index("ix_news_events_event_hash", "event_hash", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    primary_headline: Mapped[str] = mapped_column(String(1000), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    news_category: Mapped[Optional[NewsCategory]] = mapped_column(SAEnum(NewsCategory), nullable=True)
    sentiment: Mapped[Optional[Sentiment]] = mapped_column(SAEnum(Sentiment), nullable=True)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    financial_materiality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    time_horizon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    news_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risks: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    primary_company_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=True
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    primary_company: Mapped[Optional["Company"]] = relationship(lazy="selectin")
    article_links: Mapped[list["NewsEventArticle"]] = relationship(back_populates="event", lazy="selectin")
    analyses: Mapped[list["StockAnalysis"]] = relationship(back_populates="news_event", lazy="selectin")

    def __repr__(self) -> str:
        return f"<NewsEvent(id={self.id}, headline='{self.primary_headline[:60]}...')>"


# ═══════════════════════════════════════════════════════════════════════
# 6. NewsEventArticle  (M2M link between events and raw articles)
# ═══════════════════════════════════════════════════════════════════════

class NewsEventArticle(Base):
    __tablename__ = "news_event_articles"
    __table_args__ = (
        UniqueConstraint("news_event_id", "raw_article_id", name="uq_event_article"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_event_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_events.id"), nullable=False)
    raw_article_id: Mapped[int] = mapped_column(Integer, ForeignKey("raw_articles.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    event: Mapped["NewsEvent"] = relationship(back_populates="article_links", lazy="selectin")
    article: Mapped["RawArticle"] = relationship(back_populates="event_links", lazy="selectin")

    def __repr__(self) -> str:
        return f"<NewsEventArticle(event={self.news_event_id}, article={self.raw_article_id})>"


# ═══════════════════════════════════════════════════════════════════════
# 7. StockAnalysis
# ═══════════════════════════════════════════════════════════════════════

class StockAnalysis(Base):
    __tablename__ = "stock_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_event_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_events.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[CandidateClassification] = mapped_column(
        SAEnum(CandidateClassification), nullable=False
    )
    news_impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    materiality_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_credibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0)
    confirmation_score: Mapped[float] = mapped_column(Float, default=0.0)
    historical_reaction_score: Mapped[float] = mapped_column(Float, default=0.0)
    company_confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    penalties: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    scoring_version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    news_event: Mapped["NewsEvent"] = relationship(back_populates="analyses", lazy="selectin")
    company: Mapped["Company"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<StockAnalysis(id={self.id}, company_id={self.company_id}, "
            f"score={self.overall_score}, class={self.classification.value})>"
        )


# ═══════════════════════════════════════════════════════════════════════
# 8. MarketSnapshot
# ═══════════════════════════════════════════════════════════════════════

class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    avg_volume_20d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vwap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gap_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relative_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    company: Mapped["Company"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<MarketSnapshot(company_id={self.company_id}, date={self.snapshot_date})>"


# ═══════════════════════════════════════════════════════════════════════
# 9. DailyWatchlist
# ═══════════════════════════════════════════════════════════════════════

class DailyWatchlist(Base):
    __tablename__ = "daily_watchlists"
    __table_args__ = (
        Index("ix_daily_watchlists_report_date", "report_date", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(20), default="1.0")
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    total_sources_checked: Mapped[int] = mapped_column(Integer, default=0)
    successful_sources: Mapped[int] = mapped_column(Integer, default=0)
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    items: Mapped[list["DailyWatchlistItem"]] = relationship(back_populates="watchlist", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DailyWatchlist(date={self.report_date}, delivered={self.is_delivered})>"


# ═══════════════════════════════════════════════════════════════════════
# 10. DailyWatchlistItem
# ═══════════════════════════════════════════════════════════════════════

class DailyWatchlistItem(Base):
    __tablename__ = "daily_watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(Integer, ForeignKey("daily_watchlists.id"), nullable=False)
    stock_analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("stock_analyses.id"), nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    watchlist: Mapped["DailyWatchlist"] = relationship(back_populates="items", lazy="selectin")
    stock_analysis: Mapped["StockAnalysis"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<DailyWatchlistItem(watchlist={self.watchlist_id}, rank={self.rank_position})>"


# ═══════════════════════════════════════════════════════════════════════
# 11. HistoricalPerformance
# ═══════════════════════════════════════════════════════════════════════

class HistoricalPerformance(Base):
    __tablename__ = "historical_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("stock_analyses.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    news_event_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_events.id"), nullable=False)
    predicted_direction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    previous_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    next_open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    next_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    next_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    next_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_favorable_move: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_adverse_move: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    move_30min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    move_60min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    move_full_session: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    stock_analysis: Mapped["StockAnalysis"] = relationship(lazy="selectin")
    company: Mapped["Company"] = relationship(lazy="selectin")
    news_event: Mapped["NewsEvent"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<HistoricalPerformance(analysis={self.stock_analysis_id}, direction={self.predicted_direction})>"


# ═══════════════════════════════════════════════════════════════════════
# 12. CollectionRun
# ═══════════════════════════════════════════════════════════════════════

class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("news_sources.id"), nullable=True)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "batch", "manual"
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    articles_found: Mapped[int] = mapped_column(Integer, default=0)
    articles_new: Mapped[int] = mapped_column(Integer, default=0)
    articles_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="running")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    source: Mapped[Optional["NewsSource"]] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<CollectionRun(id={self.id}, type={self.run_type}, status={self.status})>"


# ═══════════════════════════════════════════════════════════════════════
# 13. SystemLog
# ═══════════════════════════════════════════════════════════════════════

class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    module: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<SystemLog(level={self.level}, module={self.module})>"
