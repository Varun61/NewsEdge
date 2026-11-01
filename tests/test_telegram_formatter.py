"""Tests for Telegram report formatting and structure."""

from datetime import date, datetime, timezone
from app.database.models import (
    CandidateClassification,
    DailyWatchlist,
    DailyWatchlistItem,
    NewsEvent,
    StockAnalysis,
)
from app.reporting.telegram_formatter import TelegramFormatter


def test_telegram_formatter_output(session, sample_company):
    now = datetime.now(timezone.utc)
    today = date(2025, 10, 28)

    wl = DailyWatchlist(
        report_date=today,
        generated_at=now,
        scoring_version="1.0",
        total_events=1,
        total_sources_checked=5,
        successful_sources=5,
    )
    session.add(wl)
    session.flush()

    ev = NewsEvent(
        primary_headline="Reliance secures major renewable order",
        event_hash="ev_hash_test",
        primary_company_id=sample_company.id,
        financial_materiality="Order size represents 8% of revenue.",
    )
    session.add(ev)
    session.flush()

    analysis = StockAnalysis(
        news_event_id=ev.id,
        company_id=sample_company.id,
        overall_score=85.0,
        classification=CandidateClassification.STRONG_BULLISH,
        news_impact_score=85.0,
        materiality_score=80.0,
    )
    session.add(analysis)
    session.flush()

    item = DailyWatchlistItem(
        watchlist_id=wl.id,
        stock_analysis_id=analysis.id,
        rank_position=1,
    )
    session.add(item)
    session.commit()

    messages = TelegramFormatter.format_daily_report(wl, session)
    assert len(messages) >= 1
    combined = "\n".join(messages)

    assert "NEWS EDGE" in combined
    assert "INDIAN STOCK MARKET WATCHLIST" in combined
    assert "BULLISH CANDIDATES" in combined
    assert "Reliance Industries Limited" in combined
    assert "RELIANCE" in combined
    assert "85/100" in combined
    assert "DISCLAIMER" in combined or "IMPORTANT" in combined
