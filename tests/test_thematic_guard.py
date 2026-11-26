"""Tests for the thematic foreign-entity guard (pure/offline)."""

from app.intelligence.thematic_engine import _is_foreign_centric, get_thematic_engine


def test_foreign_headline_no_india_anchor_is_blocked():
    assert _is_foreign_centric(
        "SpaceX gets FCC nod for 1 million orbital compute modules",
        "spacex gets fcc nod for 1 million orbital compute modules data center ai",
    )
    assert _is_foreign_centric(
        "Why is SanDisk stock falling despite surging profits?",
        "why is sandisk stock falling despite surging profits data center",
    )


def test_foreign_headline_with_india_anchor_is_allowed():
    assert not _is_foreign_centric(
        "SpaceX partners Reliance for India data centre buildout",
        "spacex partners reliance for india data centre buildout crore",
    )


def test_pure_indian_headline_not_flagged():
    assert not _is_foreign_centric(
        "Railways allocates Rs 25,000 crore for Kavach rollout",
        "railways allocates rs 25,000 crore for kavach rollout",
    )


def test_engine_returns_no_impacts_for_foreign_news():
    eng = get_thematic_engine()
    impacts = eng.detect_sector_catalysts(
        "SpaceX gets FCC nod for 1 million orbital compute modules",
        "data center server farm hyperscaler ai supercomputing boom buildout",
    )
    assert impacts == []


def test_engine_still_maps_genuine_india_theme():
    eng = get_thematic_engine()
    impacts = eng.detect_sector_catalysts(
        "Defence Ministry clears Rs 3.7 lakh crore indigenous procurement",
        "defence ministry clears procurement drone radar missile order india crore",
    )
    assert any(i.symbol for i in impacts)  # Indian defence beneficiaries mapped
