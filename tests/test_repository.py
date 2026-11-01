"""Tests for Repository CRUD helper methods."""

from datetime import date, datetime, timezone
from app.database.models import SourceType
from app.database.repository import Repository


def test_repository_operations(session):
    # 1. Sources
    src = Repository.create_source(session, name="Repo Source", source_type=SourceType.RSS)
    found_src = Repository.get_source_by_name(session, "Repo Source")
    assert found_src is not None
    assert found_src.id == src.id

    # 2. Companies & Aliases
    comp = Repository.create_company(session, nse_symbol="INFY", company_name="Infosys Ltd")
    found_comp = Repository.get_company_by_symbol(session, "infy")  # case-insensitive
    assert found_comp is not None
    assert found_comp.nse_symbol == "INFY"

    alias = Repository.create_alias(session, comp.id, "Infy", "abbreviation", 0.95)
    matched = Repository.find_company_by_alias(session, "infy")
    assert matched is not None
    assert matched.id == comp.id

    # 3. Articles
    now = datetime.now(timezone.utc)
    art = Repository.create_article(
        session,
        source_id=src.id,
        headline="Infosys signs mega deal",
        article_url="https://example.com/infy",
        published_at=now,
        content_hash="infy_hash",
    )
    assert Repository.get_article_by_url(session, "https://example.com/infy") is not None
    assert Repository.get_article_by_url(session, "https://example.com/nonexistent") is None

    # 4. Watchlist
    today = date(2025, 10, 28)
    wl = Repository.create_watchlist(
        session,
        report_date=today,
        generated_at=now,
        total_events=1,
    )
    found_wl = Repository.get_watchlist_by_date(session, today)
    assert found_wl is not None
    assert found_wl.total_events == 1
