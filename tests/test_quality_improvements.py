"""Tests for NewsEdge quality improvements:
- Retrospective rally detection
- Bearish profit decline detection (e.g. Alkem Lab profit falls)
- Disambiguation guards (TAKE, TRIDENT, ICICIBANK, KOTAKBANK)
- Roundup headline blocking
- 4-category Telegram message generation
"""

from datetime import date, datetime, time, timezone
import pytest

from app.database.models import (
    CandidateClassification,
    DailyWatchlist,
    DailyWatchlistItem,
    NewsEvent,
    StockAnalysis,
    Company,
)
from app.intelligence.ai_provider import BaseAIProvider
from app.processors.nse_master import get_nse_resolver
from app.reporting.telegram_formatter import TelegramFormatter, _is_priced_in


class DummyAI(BaseAIProvider):
    def classify_news(self, headline, content, company_name, nse_symbol, source_urls, additional_context=None):
        return self._heuristic_fallback(headline, company_name, nse_symbol, source_urls)

    def is_available(self):
        return False


def test_retrospective_rallies_classified_as_neutral():
    ai = DummyAI()
    
    retrospective_headlines = [
        ("Nava Q2 Results: Shares jump 8% after profit more than doubles", "NAVA"),
        ("Cupid shares extend 2026 gains to 265%; Stock at record high after Q2 results", "CUPID"),
        ("Hindustan Copper shares jump 6% after strong operating Q2, record high margins", "HINDCOPPER"),
        ("Up 118% from 52-week low, Rolex Rings hits year-high! Is small-cap good buy?", "ROLEXRINGS"),
        ("Nuvama Wealth share price: Brokerage stock up over 6% today, near peak", "NUVAMA"),
    ]

    for hl, sym in retrospective_headlines:
        res = ai._heuristic_fallback(hl, sym, sym, ["https://example.com"])
        assert res.expected_direction == "neutral", f"Failed for '{hl}': got {res.expected_direction}"
        assert res.impact_score <= 50.0


def test_profit_decline_classified_as_bearish():
    ai = DummyAI()
    
    bearish_earnings_headlines = [
        "Alkem Lab Q2 profit falls 14.4% to ₹667 cr; revenue rises to ₹4,552 cr",
        "Reliance Power Q2 profit drops 65% to ₹30 crore",
        "Caplin Point Q2 results: Revenue rises 18%, margin edges up; stock falls over 6%",
        "Urban Company shares fall 10% as Q2 net loss widens despite revenue growth",
    ]

    for hl in bearish_earnings_headlines:
        res = ai._heuristic_fallback(hl, "Company", "TEST", ["https://example.com"])
        assert res.expected_direction == "bearish", f"Failed for '{hl}': got {res.expected_direction}"
        assert res.news_category == "PROFIT_WARNING"


def test_disambiguation_guards():
    resolver = get_nse_resolver()

    # 1. 'take over' phrase should NOT map to TAKE Solutions
    take_res = resolver.resolve_from_text("Nvidia CEO Jensen Huang resigns; CFO Kress to take over as interim chief")
    assert take_res is None or take_res["symbol"] != "TAKE"

    # 2. Trident Hotel news should NOT map to TRIDENT textiles
    trident_res = resolver.resolve_from_text("EIH approves ₹777 crore Trident Hotel near Hyderabad Airport")
    assert trident_res is None or trident_res["symbol"] != "TRIDENT"

    # 3. ICICI Sec downgrade note should NOT map to ICICIBANK
    icici_res = resolver.resolve_from_text("Matrimony downgraded by ICICI Sec despite 167% rise in Q2 PAT")
    assert icici_res is None or icici_res["symbol"] != "ICICIBANK"

    # 4. Kotak Alts PE pump should NOT map to KOTAKBANK
    kotak_res = resolver.resolve_from_text("Kotak Alts pumps ₹325 crore into Gainwell Group")
    assert kotak_res is None or kotak_res["symbol"] != "KOTAKBANK"

    # 5. Generic roundup / Buzzing stocks headline blocked
    buzz_res = resolver.resolve_from_text("Buzzing stocks: Bajaj Finance, Tata Power, Adani Enterprises, Sandur Manganese")
    assert buzz_res is None


def test_telegram_formatter_four_categories(session):
    now = datetime.now(timezone.utc)
    today = date(2026, 11, 13)

    wl = DailyWatchlist(
        report_date=today,
        generated_at=now,
        scoring_version="1.1",
        total_events=4,
        total_sources_checked=5,
        successful_sources=5,
    )
    session.add(wl)
    session.flush()

    # Company 1: Fresh Bullish (L&T order win announced at 6:00 PM IST)
    c1 = Company(nse_symbol="LT", company_name="Larsen & Toubro Limited", is_active=True)
    session.add(c1)
    session.flush()

    ev1 = NewsEvent(
        primary_headline="L&T bags mega ₹4,000 crore hydrocarbon order in Middle East",
        event_hash="h1",
        primary_company_id=c1.id,
        financial_materiality="Major order win",
        created_at=datetime(2026, 11, 13, 13, 0, tzinfo=timezone.utc),  # 6:30 PM IST (post market)
    )
    session.add(ev1)
    session.flush()

    a1 = StockAnalysis(
        news_event_id=ev1.id,
        company_id=c1.id,
        overall_score=88.0,
        classification=CandidateClassification.STRONG_BULLISH,
    )
    session.add(a1)
    session.flush()
    session.add(DailyWatchlistItem(watchlist_id=wl.id, stock_analysis_id=a1.id, rank_position=1))

    # Company 2: Fresh Bearish (SEBI penalty at 7:00 PM IST)
    c2 = Company(nse_symbol="INVENTURE", company_name="Inventure Growth & Securities", is_active=True)
    session.add(c2)
    session.flush()

    ev2 = NewsEvent(
        primary_headline="Inventure Growth gets SEBI penalty for disclosure violations",
        event_hash="h2",
        primary_company_id=c2.id,
        created_at=datetime(2026, 11, 13, 14, 0, tzinfo=timezone.utc),  # 7:30 PM IST (post market)
    )
    session.add(ev2)
    session.flush()

    a2 = StockAnalysis(
        news_event_id=ev2.id,
        company_id=c2.id,
        overall_score=80.0,
        classification=CandidateClassification.STRONG_BEARISH,
    )
    session.add(a2)
    session.flush()
    session.add(DailyWatchlistItem(watchlist_id=wl.id, stock_analysis_id=a2.id, rank_position=2))

    # Company 3: Priced-In Bullish (Rallied during market hours at 11:00 AM IST)
    c3 = Company(nse_symbol="CUPID", company_name="Cupid Limited", is_active=True)
    session.add(c3)
    session.flush()

    ev3 = NewsEvent(
        primary_headline="Cupid shares surge 15% after Q2 profit doubles",
        event_hash="h3",
        primary_company_id=c3.id,
        created_at=datetime(2026, 11, 13, 5, 30, tzinfo=timezone.utc),  # 11:00 AM IST (market hours)
    )
    session.add(ev3)
    session.flush()

    a3 = StockAnalysis(
        news_event_id=ev3.id,
        company_id=c3.id,
        overall_score=78.0,
        classification=CandidateClassification.BULLISH,
    )
    session.add(a3)
    session.flush()
    session.add(DailyWatchlistItem(watchlist_id=wl.id, stock_analysis_id=a3.id, rank_position=3))

    session.commit()

    messages = TelegramFormatter.format_daily_report(wl, session)
    combined = "\n".join(messages)

    # Verifications
    assert "BULLISH WATCHLIST" in combined
    assert "BEARISH WATCHLIST" in combined
    assert "PRICED-IN BULLISH" in combined
    assert "LT" in combined
    assert "INVENTURE" in combined
    assert "CUPID" in combined
    assert "LINK" in combined or "<code>" in combined
