"""Tests for candidate ranking and score weighting algorithm."""

from datetime import datetime, timezone
from app.config import get_settings
from app.database.models import CandidateClassification, NewsEvent
from app.intelligence.ai_provider import ClassificationResult
from app.intelligence.scoring_engine import ScoringEngine


def test_scoring_classification_thresholds(session, sample_company):
    settings = get_settings()
    engine = ScoringEngine(settings)

    event = NewsEvent(
        primary_headline="Reliance bags massive ₹50,000 crore energy contract",
        event_hash="test_rel_hash",
        primary_company_id=sample_company.id,
    )
    session.add(event)
    session.commit()

    # Link credible articles
    from app.database.models import RawArticle, NewsEventArticle, NewsSource, SourceType
    src = NewsSource(name="Official Source", source_type=SourceType.OFFICIAL, credibility_score=0.95)
    session.add(src)
    session.flush()

    art1 = RawArticle(
        source_id=src.id,
        headline="Reliance bags massive ₹50,000 crore energy contract",
        article_url="https://example.com/art1",
        published_at=datetime.now(timezone.utc),
        source_credibility=0.95,
        content_hash="h1",
    )
    art2 = RawArticle(
        source_id=src.id,
        headline="Reliance bags solar contract",
        article_url="https://example.com/art2",
        published_at=datetime.now(timezone.utc),
        source_credibility=0.95,
        content_hash="h2",
    )
    session.add_all([art1, art2])
    session.flush()

    session.add_all([
        NewsEventArticle(news_event_id=event.id, raw_article_id=art1.id, is_primary=True),
        NewsEventArticle(news_event_id=event.id, raw_article_id=art2.id, is_primary=False),
    ])
    session.commit()

    # High impact bullish classification
    high_class = ClassificationResult(
        company_name=sample_company.company_name,
        nse_symbol=sample_company.nse_symbol,
        news_category="ORDER_WIN",
        sentiment="VERY_POSITIVE",
        impact_score=90.0,
        confidence=95.0,
        expected_direction="bullish",
    )

    analysis = engine.score_event(
        event=event,
        classification=high_class,
        materiality_score=90.0,
        session=session,
    )

    assert analysis is not None
    assert analysis.overall_score >= 80.0
    assert analysis.classification == CandidateClassification.STRONG_BULLISH

    # High impact bearish classification
    bearish_class = ClassificationResult(
        company_name=sample_company.company_name,
        nse_symbol=sample_company.nse_symbol,
        news_category="PROFIT_WARNING",
        sentiment="VERY_NEGATIVE",
        impact_score=85.0,
        confidence=90.0,
        expected_direction="bearish",
    )

    analysis_bear = engine.score_event(
        event=event,
        classification=bearish_class,
        materiality_score=85.0,
        session=session,
    )

    assert analysis_bear is not None
    assert analysis_bear.overall_score >= 75.0
    assert analysis_bear.classification in (CandidateClassification.STRONG_BEARISH, CandidateClassification.BEARISH)
