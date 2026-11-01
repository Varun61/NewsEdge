"""Tests for financial materiality calculations and Indian currency parsing."""

from app.database.models import Company
from app.intelligence.materiality_analyzer import MaterialityAnalyzer


def test_extract_monetary_value():
    analyzer = MaterialityAnalyzer()

    # Crores
    assert analyzer.extract_monetary_value("Company wins ₹1,000 crore order") == 1000.0
    assert analyzer.extract_monetary_value("Awarded contract worth Rs 500 crore") == 500.0
    assert analyzer.extract_monetary_value("Bags INR 2500 cr highway project") == 2500.0

    # Lakhs (normalized to Crores)
    assert analyzer.extract_monetary_value("Gets ₹50 lakh grant") == 0.50
    assert analyzer.extract_monetary_value("Received Rs 100 lakh deal") == 1.0

    # None
    assert analyzer.extract_monetary_value("No figures here") is None


def test_analyze_order_win_ratio():
    analyzer = MaterialityAnalyzer()

    # Company with ₹10,000 Cr revenue
    comp_a = Company(
        nse_symbol="COMPA",
        company_name="Company A",
        annual_revenue=10000.0,
    )

    # Order of ₹1,000 Cr = 10% ratio -> High materiality
    score_a, text_a = analyzer.analyze_order_win("Wins ₹1,000 crore order", comp_a)
    assert score_a >= 80.0
    assert "10.0%" in text_a

    # Company with ₹100,000 Cr revenue
    comp_b = Company(
        nse_symbol="COMPB",
        company_name="Company B",
        annual_revenue=100000.0,
    )

    # Same order of ₹1,000 Cr = 1% ratio -> Low materiality
    score_b, text_b = analyzer.analyze_order_win("Wins ₹1,000 crore order", comp_b)
    assert score_b <= 65.0
    assert "1.0%" in text_b


def test_materiality_direction_awareness(session):
    from app.database.models import NewsCategory, NewsEvent
    from app.intelligence.ai_provider import ClassificationResult

    analyzer = MaterialityAnalyzer()
    comp = Company(nse_symbol="ZEEL", company_name="Zee Entertainment", annual_revenue=8000.0)
    session.add(comp)
    session.flush()

    # Bearish event with percentage drop
    ev_bearish = NewsEvent(
        primary_headline="ZEEL net profit slumps 40% amid rising operational expenses",
        event_hash="h_bearish_test",
        primary_company_id=comp.id,
    )
    class_bearish = ClassificationResult(
        company_name="Zee Entertainment",
        nse_symbol="ZEEL",
        news_category=NewsCategory.QUARTERLY_RESULTS.value,
        sentiment="NEGATIVE",
        impact_score=80.0,
        expected_direction="bearish",
    )

    score_bearish, text_bearish = analyzer.analyze(ev_bearish, class_bearish, session)
    assert score_bearish >= 85.0
    assert "growth" not in text_bearish.lower()
    assert "drop" in text_bearish.lower() or "slump" in text_bearish.lower() or "contraction" in text_bearish.lower()

    # Bullish event with percentage surge
    ev_bullish = NewsEvent(
        primary_headline="ZEEL net profit surges 60% with record ad revenues",
        event_hash="h_bullish_test",
        primary_company_id=comp.id,
    )
    class_bullish = ClassificationResult(
        company_name="Zee Entertainment",
        nse_symbol="ZEEL",
        news_category=NewsCategory.PROFIT_GROWTH.value,
        sentiment="POSITIVE",
        impact_score=85.0,
        expected_direction="bullish",
    )

    score_bullish, text_bullish = analyzer.analyze(ev_bullish, class_bullish, session)
    assert score_bullish >= 85.0
    assert "surge" in text_bullish.lower() or "growth" in text_bullish.lower()
