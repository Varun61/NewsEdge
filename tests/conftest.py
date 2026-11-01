"""Pytest fixtures for NewsEdge test suite."""

import os
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import (
    Base,
    Company,
    CompanyAlias,
    NewsSource,
    RawArticle,
    SourceType,
    CollectionStatus,
)
from app.collectors.base_collector import CollectedArticle


@pytest.fixture
def test_engine(tmp_path):
    """In-memory or temp SQLite engine for isolated test runs."""
    db_file = tmp_path / "test_newsedge.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session(test_engine):
    """Yields a clean SQLAlchemy session per test."""
    TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    sess = TestingSession()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


@pytest.fixture
def sample_company(session):
    comp = Company(
        nse_symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        sector="Energy & Petrochemicals",
        annual_revenue=900000.0,
    )
    session.add(comp)
    session.flush()

    alias = CompanyAlias(
        company_id=comp.id,
        alias_name="RIL",
        alias_type="abbreviation",
        confidence=0.98,
    )
    session.add(alias)
    session.commit()
    return comp


@pytest.fixture
def sample_source(session):
    src = NewsSource(
        name="Test Feed",
        source_type=SourceType.RSS,
        url="https://example.com/rss",
        credibility_score=0.8,
    )
    session.add(src)
    session.commit()
    return src


@pytest.fixture
def sample_article(session, sample_source):
    now = datetime.now(timezone.utc)
    art = RawArticle(
        source_id=sample_source.id,
        headline="Reliance Industries bags ₹10,000 crore major solar contract",
        article_url="https://example.com/art1",
        published_at=now,
        discovered_at=now,
        raw_content="Reliance bags large order",
        extracted_text="Reliance bags large order",
        source_credibility=0.8,
        content_hash="test_hash_1",
        collection_status=CollectionStatus.COLLECTED,
    )
    session.add(art)
    session.commit()
    return art
