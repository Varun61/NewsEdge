"""Tests for duplicate article detection and event grouping."""

from datetime import datetime, timezone
from app.database.models import RawArticle
from app.processors.deduplicator import Deduplicator


def test_deduplication_similar_headlines(session, sample_company, sample_source):
    now = datetime.now(timezone.utc)

    # Two articles reporting the same event from different publishers
    art1 = RawArticle(
        source_id=sample_source.id,
        headline="Reliance bags ₹1,000 crore contract for solar power plant",
        article_url="https://moneycontrol.com/article1",
        published_at=now,
        content_hash="h1",
    )
    art2 = RawArticle(
        source_id=sample_source.id,
        headline="Reliance Industries wins ₹1,000 crore solar project deal",
        article_url="https://economictimes.com/article2",
        published_at=now,
        content_hash="h2",
    )
    session.add_all([art1, art2])
    session.commit()

    dedup = Deduplicator(headline_similarity_threshold=0.60)
    events = dedup.deduplicate_articles([art1, art2], session)

    # Should group into 1 event with 2 linked articles
    assert len(events) == 1
    assert len(events[0].article_links) == 2
