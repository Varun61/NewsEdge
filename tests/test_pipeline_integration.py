"""End-to-end integration tests over a real (temp SQLite) DB, no network.

Covers the two halves of the pipeline deterministically:
1. collect -> normalize -> deduplicate: an exchange filing and a news item flow
   into RawArticles (authoritative identity preserved) and group into NewsEvents
   mapped to the right company.
2. classify -> score (filing fast-path): an authoritative bullish order-win
   filing becomes a bullish, actionable StockAnalysis. Network-touching
   analyzers (yfinance trend, bhavcopy, Screener fundamentals, sector momentum,
   concall) are monkeypatched to neutral so the test is offline and fast.

Requires the project dependencies (SQLAlchemy etc.); runs in the project venv.
"""

from datetime import datetime, timezone

import pytest

from app.collectors.base_collector import CollectedArticle
from app.database.models import CandidateClassification, NewsEvent, StockAnalysis
from app.database.repository import Repository
from app.processors.article_normalizer import ArticleNormalizer
from app.processors.deduplicator import Deduplicator


def _filing_article() -> CollectedArticle:
    catalyst = {
        "news_category": "ORDER_WIN", "direction": "bullish", "impact_hint": 84.0,
        "confidence": 88.0, "is_material": True, "summary": "bags ₹4,000 crore order",
        "matched_rule": "order_win", "order_value_cr": 4000.0, "profit_growth_pct": None,
        "revenue_growth_pct": None, "penalty_amount_cr": None, "tags": ["order"],
    }
    return CollectedArticle(
        headline="RELIANCE (Reliance Industries Limited): bags order worth Rs 4,000 crore",
        article_url="https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE",
        source_name="NSE Announcements",
        published_at=datetime.now(timezone.utc),
        raw_content="Reliance bags order worth Rs 4,000 crore",
        extracted_text="Reliance bags order worth Rs 4,000 crore",
        company_mentions=["RELIANCE", "Reliance Industries Limited"],
        credibility_score=1.0,
        authoritative_symbol="RELIANCE",
        authoritative_isin="INE002A01018",
        filing_catalyst=catalyst,
    )


# ── Half 1: collect -> normalize -> dedup ────────────────────────────────────

def test_filing_normalizes_with_authoritative_identity(session, sample_company):
    norm = ArticleNormalizer()
    rec, is_new = norm.process_article(_filing_article(), session)
    session.commit()

    assert is_new
    cm = rec.company_mentions
    assert isinstance(cm, dict)
    assert cm.get("authoritative_symbol") == "RELIANCE"
    assert cm.get("authoritative_isin") == "INE002A01018"
    assert cm.get("filing_catalyst", {}).get("news_category") == "ORDER_WIN"


def test_dedup_groups_and_maps_company(session, sample_company):
    norm = ArticleNormalizer()
    arts = []
    rec1, _ = norm.process_article(_filing_article(), session)
    news = CollectedArticle(
        headline="Reliance Industries wins ₹4,000 crore contract, shares in focus",
        article_url="https://example.com/ril-order",
        source_name="Economic Times Markets",
        published_at=datetime.now(timezone.utc),
        raw_content="Reliance wins big order", extracted_text="Reliance wins big order",
        company_mentions=["Reliance Industries"], credibility_score=0.8,
    )
    rec2, _ = norm.process_article(news, session)
    session.commit()

    events = Deduplicator().deduplicate_articles([rec1, rec2], session)
    session.commit()

    assert events, "expected at least one NewsEvent"
    comp_ids = {e.primary_company_id for e in events}
    assert sample_company.id in comp_ids


# ── Half 2: classify + score via the filing fast-path ────────────────────────

class _StubAI:
    def classify_news(self, *a, **k):  # pragma: no cover - should not be called on fast-path
        raise AssertionError("LLM should not be called for an authoritative filing")

    def is_available(self):
        return False

    def _heuristic_fallback(self, headline, company_name, nse_symbol, source_urls):  # pragma: no cover
        from app.intelligence.ai_provider import ClassificationResult
        return ClassificationResult(company_name=company_name, nse_symbol=nse_symbol)


@pytest.fixture
def _neutralise_network(monkeypatch):
    class _Dummy:
        def get_trend_evaluation(self, *a, **k): return None
        def get_sector_modifier(self, *a, **k): return 0.0
        def analyze_text(self, *a, **k):
            return type("C", (), {"score_modifier": 0.0, "is_guidance_cut": False})()
        def metrics(self, *a, **k): return None
        def get(self, *a, **k): return None
    d = _Dummy()
    for target in (
        "app.intelligence.technical_trend.get_technical_trend_analyzer",
        "app.intelligence.sector_momentum.get_sector_momentum_analyzer",
        "app.intelligence.concall_analyzer.get_concall_analyzer",
        "app.market_data.bhavcopy.get_bhavcopy_provider",
        "app.market_data.fundamentals.get_fundamentals_provider",
    ):
        monkeypatch.setattr(target, lambda d=d: d, raising=True)
    return d


def test_filing_fastpath_produces_bullish_analysis(session, sample_company, _neutralise_network):
    from app.config import get_settings
    from app.intelligence.news_classifier import NewsClassifier
    from app.intelligence.scoring_engine import ScoringEngine

    # Build a filing-backed event linked to one article.
    norm = ArticleNormalizer()
    rec, _ = norm.process_article(_filing_article(), session)
    event = Repository.create_event(
        session=session,
        primary_headline=rec.headline,
        event_hash="evt_filing_test",
        primary_company_id=sample_company.id,
        is_processed=False,
    )
    Repository.link_article_to_event(session, event_id=event.id, article_id=rec.id, is_primary=True)
    session.commit()

    clf = NewsClassifier(_StubAI(), ScoringEngine(get_settings()))
    analysis = clf.process_event(event, session)
    session.commit()

    assert analysis is not None
    assert analysis.company_id == sample_company.id
    assert analysis.overall_score > 60.0
    assert analysis.classification in (
        CandidateClassification.STRONG_BULLISH,
        CandidateClassification.BULLISH,
    )
    assert event.expected_direction == "bullish"
