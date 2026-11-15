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


def test_sunday_and_monday_window_picks_friday_330pm():
    from app.trading_calendar import get_effective_collection_window, utc_to_ist
    # Sunday run: 15-Nov-2026
    sunday = date(2026, 11, 15)
    start_utc, end_utc, desc = get_effective_collection_window(report_date=sunday)
    start_ist = utc_to_ist(start_utc)
    # Must start Friday 13-Nov at 15:30 IST
    assert start_ist.date() == date(2026, 11, 13)
    assert start_ist.hour == 15
    assert start_ist.minute == 30

    # Monday run: 16-Nov-2026
    monday = date(2026, 11, 16)
    start_utc_m, end_utc_m, desc_m = get_effective_collection_window(report_date=monday)
    start_ist_m = utc_to_ist(start_utc_m)
    # Must also start Friday 13-Nov at 15:30 IST
    assert start_ist_m.date() == date(2026, 11, 13)
    assert start_ist_m.hour == 15
    assert start_ist_m.minute == 30


def test_quarterly_results_priced_in_if_before_330pm_or_retrospective():
    from app.reporting.telegram_formatter import _is_priced_in
    # 1. Quarterly result announced during market hours (Friday 1:30 PM IST)
    ev_midday = NewsEvent(
        primary_headline="Ashok Leyland Q2 profit jumps 16.4% YoY to ₹2,805 Cr",
        created_at=datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc),  # 1:30 PM IST (before 3:30 PM)
    )
    analysis_midday = StockAnalysis(news_event=ev_midday)
    # Reference date is Friday 13-Nov 6:00 PM IST (post-close)
    ref_dt = datetime(2026, 11, 13, 12, 30, tzinfo=timezone.utc)
    assert _is_priced_in(analysis_midday, as_of_dt=ref_dt) is True

    # 2. Quarterly result announced post market (Friday 5:30 PM IST)
    ev_postmarket = NewsEvent(
        primary_headline="Ashok Leyland Q2 profit jumps 16.4% YoY to ₹2,805 Cr",
        created_at=datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc),  # 5:30 PM IST (after 3:30 PM)
    )
    analysis_postmarket = StockAnalysis(news_event=ev_postmarket)
    assert _is_priced_in(analysis_postmarket, as_of_dt=ref_dt) is False

    # 3. Retrospective quarterly rally (stock already jumped 9%)
    ev_retro = NewsEvent(
        primary_headline="Stock jumps 9% after strong profit growth in Q2",
        created_at=datetime(2026, 11, 13, 12, 30, tzinfo=timezone.utc),
    )
    analysis_retro = StockAnalysis(news_event=ev_retro)
    assert _is_priced_in(analysis_retro, as_of_dt=ref_dt) is True


def test_earnings_quality_gate_penalties(session):
    from app.config import Settings
    from app.intelligence.ai_provider import ClassificationResult
    from app.intelligence.scoring_engine import ScoringEngine

    engine = ScoringEngine(Settings())

    # 1. Bellwether modest growth (<15% profit growth for HDFC Bank)
    c_hdfc = Company(nse_symbol="HDFCBANK", company_name="HDFC Bank Limited", is_active=True, annual_revenue=200000.0)
    session.add(c_hdfc)
    session.flush()

    ev_bw = NewsEvent(
        primary_headline="HDFC Bank Q2 profit rises 5.3% to ₹16,821 crore",
        event_hash="hash_bw",
        primary_company_id=c_hdfc.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(ev_bw)
    session.flush()

    cls_bw = ClassificationResult(
        company_name="HDFC Bank Limited",
        nse_symbol="HDFCBANK",
        news_category="PROFIT_GROWTH",
        sentiment="POSITIVE",
        impact_score=75.0,
        confidence=85.0,
        expected_direction="bullish",
    )
    res_bw = engine.score_event(ev_bw, cls_bw, 75.0, session)
    assert res_bw is not None
    assert "largecap_modest_growth" in res_bw.penalties
    assert res_bw.classification in (CandidateClassification.WATCH_ONLY, CandidateClassification.EXCLUDED)

    # 2. Exceptional / one-off items inflating profit
    c_bajaj = Company(nse_symbol="BAJAJCON", company_name="Bajaj Consumer Care", is_active=True, annual_revenue=1000.0)
    session.add(c_bajaj)
    session.flush()

    ev_exc = NewsEvent(
        primary_headline="Bajaj Consumer Q2 profit jumps 66% aided by exceptional gain of ₹45 crore",
        event_hash="hash_exc",
        primary_company_id=c_bajaj.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(ev_exc)
    session.flush()

    cls_exc = ClassificationResult(
        company_name="Bajaj Consumer Care",
        nse_symbol="BAJAJCON",
        news_category="PROFIT_GROWTH",
        sentiment="VERY_POSITIVE",
        impact_score=80.0,
        confidence=80.0,
        expected_direction="bullish",
    )
    res_exc = engine.score_event(ev_exc, cls_exc, 80.0, session)
    assert res_exc is not None
    assert "exceptional_items_inflation" in res_exc.penalties

    # 3. Management caution tone in commentary
    c_ltm = Company(nse_symbol="LTIM", company_name="LTIMindtree Limited", is_active=True, annual_revenue=35000.0)
    session.add(c_ltm)
    session.flush()

    ev_cautious = NewsEvent(
        primary_headline="LTIMindtree Q2 profit up 8%; management cautious on discretionary tech spending",
        event_hash="hash_ltm",
        primary_company_id=c_ltm.id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(ev_cautious)
    session.flush()

    cls_cautious = ClassificationResult(
        company_name="LTIMindtree Limited",
        nse_symbol="LTIM",
        news_category="PROFIT_GROWTH",
        sentiment="NEUTRAL",
        impact_score=68.0,
        confidence=80.0,
        expected_direction="bullish",
    )
    res_cautious = engine.score_event(ev_cautious, cls_cautious, 68.0, session)
    assert res_cautious is not None
    assert "management_caution_tone" in res_cautious.penalties
    assert res_cautious.classification in (CandidateClassification.WATCH_ONLY, CandidateClassification.EXCLUDED)


def test_telegram_conviction_tier_badges():
    from app.reporting.telegram_formatter import TelegramFormatter
    assert TelegramFormatter._conviction_tier(88.0) == "🎯 "
    assert TelegramFormatter._conviction_tier(75.0) == "⚡ "
    assert TelegramFormatter._conviction_tier(66.0) == "👀 "
    assert TelegramFormatter._conviction_tier(50.0) == ""


def test_sector_momentum_analyzer_mapping():
    from app.intelligence.sector_momentum import get_sector_momentum_analyzer, STOCK_SECTOR_MAP
    analyzer = get_sector_momentum_analyzer()
    assert STOCK_SECTOR_MAP["HDFCBANK"] == "BANKING"
    assert STOCK_SECTOR_MAP["INFY"] == "IT"
    assert STOCK_SECTOR_MAP["SUNPHARMA"] == "PHARMA"
    assert STOCK_SECTOR_MAP["MARUTI"] == "AUTO"
    assert STOCK_SECTOR_MAP["JSWSTEEL"] == "METALS"
    # When cache is empty/mocked, returns 0.0 without errors
    mod = analyzer.get_sector_modifier("HDFCBANK")
    assert isinstance(mod, float)

