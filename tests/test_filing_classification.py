"""Tests for the filings-first fast-path in NewsClassifier.

Exercises the pure helpers (_get_filing_context, _classification_from_catalyst)
with lightweight stand-in objects — no DB or network required.
"""

from types import SimpleNamespace

from app.intelligence.news_classifier import NewsClassifier
from app.processors.filing_catalyst import classify_filing


def _article(company_mentions):
    return SimpleNamespace(company_mentions=company_mentions, article_url="u", extracted_text="", raw_content="")


def _link(article, is_primary):
    return SimpleNamespace(article=article, is_primary=is_primary)


def _event(links):
    return SimpleNamespace(article_links=links)


def test_get_filing_context_prefers_primary_filing():
    cat = {"news_category": "ORDER_WIN", "is_material": True}
    primary = _article({
        "mentions": ["KEC", "KEC International Limited"],
        "authoritative_symbol": "KEC",
        "authoritative_isin": "INE389H01022",
        "filing_catalyst": cat,
    })
    secondary = _article({"mentions": ["XYZ", "Other"], "authoritative_symbol": "XYZ", "filing_catalyst": {"is_material": True}})
    event = _event([_link(secondary, False), _link(primary, True)])

    ctx = NewsClassifier._get_filing_context(None, event)
    assert ctx is not None
    assert ctx["symbol"] == "KEC"
    assert ctx["isin"] == "INE389H01022"
    assert ctx["name"] == "KEC International Limited"


def test_get_filing_context_none_for_plain_news():
    news = _article({"mentions": ["Reliance"]})  # no authoritative_symbol
    event = _event([_link(news, True)])
    assert NewsClassifier._get_filing_context(None, event) is None


def test_classification_from_order_win_catalyst():
    cat = classify_filing(
        subject="Awarding of Order/Receipt of Order",
        attachment_text="Bags order worth Rs 2,000 crore.",
    )
    res = NewsClassifier._classification_from_catalyst(
        cat.__dict__ if hasattr(cat, "__dict__") else cat, "KEC", "KEC International Limited", ["u"]
    )
    assert res.nse_symbol == "KEC"
    assert res.news_category == "ORDER_WIN"
    assert res.expected_direction == "bullish"
    assert res.sentiment in ("POSITIVE", "VERY_POSITIVE")
    assert "2,000 Cr" in res.financial_materiality
    assert res.confidence >= 85.0


def test_classification_from_sebi_penalty_catalyst():
    cat = classify_filing(
        subject="Disclosure under SEBI Regulation 30",
        attachment_text="SEBI order imposing penalty of Rs 15 crore.",
    )
    res = NewsClassifier._classification_from_catalyst(cat.__dict__, "ABC", "ABC Limited", ["u"])
    assert res.news_category == "REGULATORY_ACTION"
    assert res.expected_direction == "bearish"
    assert res.sentiment in ("NEGATIVE", "VERY_NEGATIVE")
    assert "penalty" in res.financial_materiality.lower()
