"""Tests for ORM models, enumerations, and relationships."""

from datetime import datetime, timezone
from app.database.models import (
    CandidateClassification,
    Company,
    CompanyAlias,
    NewsCategory,
    NewsEvent,
    NewsEventArticle,
    NewsSource,
    RawArticle,
    Sentiment,
    SourceType,
    CollectionStatus,
)


def test_models_and_enums(session):
    # Enums accessibility
    assert NewsCategory.ORDER_WIN.value == "ORDER_WIN"
    assert Sentiment.VERY_POSITIVE.value == "VERY_POSITIVE"
    assert CandidateClassification.STRONG_BULLISH.value == "strong_bullish"

    # Create Company with alias
    comp = Company(
        nse_symbol="TCS",
        company_name="Tata Consultancy Services",
        sector="IT",
    )
    session.add(comp)
    session.flush()

    alias = CompanyAlias(
        company_id=comp.id,
        alias_name="Tata Consultancy",
        alias_type="common_name",
        confidence=1.0,
    )
    session.add(alias)
    session.flush()

    assert len(comp.aliases) == 1
    assert comp.aliases[0].alias_name == "Tata Consultancy"

    # Source and Article
    src = NewsSource(name="Test Source", source_type=SourceType.RSS)
    session.add(src)
    session.flush()

    art = RawArticle(
        source_id=src.id,
        headline="TCS wins $1B deal",
        article_url="https://example.com/tcs1",
        published_at=datetime.now(timezone.utc),
        source_credibility=0.8,
        collection_status=CollectionStatus.COLLECTED,
    )
    session.add(art)
    session.flush()

    # Event and link
    ev = NewsEvent(
        primary_headline="TCS wins $1B deal",
        event_hash="test_event_hash",
        primary_company_id=comp.id,
    )
    session.add(ev)
    session.flush()

    link = NewsEventArticle(news_event_id=ev.id, raw_article_id=art.id, is_primary=True)
    session.add(link)
    session.commit()

    assert len(ev.article_links) == 1
    assert ev.article_links[0].article.headline == "TCS wins $1B deal"
