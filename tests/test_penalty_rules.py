"""Tests for the extracted pure penalty rules (offline)."""

from app.intelligence.penalty_rules import PenaltyContext, compute_headline_penalties

_STOP = {"limited", "ltd", "the", "and", "industries"}


def ctx(headline, *, cat_str="OTHER", news_category="OTHER", confidence=80.0, impact=70.0,
        fresh=100.0, conf_score=80.0, cred=80.0, symbol="", name="", bellwethers=None):
    return PenaltyContext(
        headline=headline, headline_lower=headline.lower(), cat_str=cat_str,
        news_category=news_category, confidence=confidence, impact_score=impact,
        freshness_score=fresh, confirmation_score=conf_score, credibility_score=cred,
        event_symbol=symbol, company_name=name, bellwethers=bellwethers or set(),
        alias_stopwords=_STOP,
    )


def test_unquantified_vs_quantified_order():
    assert "unquantified_order_win" in compute_headline_penalties(
        ctx("ABC secures large order", cat_str="ORDER_WIN", symbol="ABC"))
    assert "unquantified_order_win" not in compute_headline_penalties(
        ctx("ABC bags order worth Rs 2,000 crore", cat_str="ORDER_WIN", symbol="ABC"))


def test_order_book_is_not_a_fresh_order():
    p = compute_headline_penalties(
        ctx("Can Siemens's Rs 47,000 crore order book power its growth", cat_str="ORDER_WIN", symbol="SIEMENS"))
    assert "order_book_not_new_order" in p
    # A genuine fresh order (with an action verb) is not flagged
    assert "order_book_not_new_order" not in compute_headline_penalties(
        ctx("Siemens bags Rs 5,000 crore metro order", cat_str="ORDER_WIN", symbol="SIEMENS"))


def test_margin_compression():
    assert "margin_compression" in compute_headline_penalties(
        ctx("XYZ Q2 margins contract on input costs", symbol="XYZ"))


def test_past_price_action_exhaustion():
    assert "past_price_action_exhaustion" in compute_headline_penalties(
        ctx("PQR shares rally 18 percent in trade", symbol="PQR"))
    assert "past_price_action_exhaustion" in compute_headline_penalties(
        ctx("PQR stock hits 52-week high", symbol="PQR"))
    # Regression: "surge 18%" (percent sign + space) is now caught too.
    assert "past_price_action_exhaustion" in compute_headline_penalties(
        ctx("PQR shares surge 18% in trade", symbol="PQR"))


def test_stale_recap_penalty():
    assert "stale_or_recap_reference" in compute_headline_penalties(
        ctx("TCS Q2 results review: should you buy?", symbol="TCS"))


def test_bellwether_modest_growth():
    p = compute_headline_penalties(
        ctx("HDFCBANK net profit rises 6% YoY", symbol="HDFCBANK", bellwethers={"HDFCBANK"}))
    assert "largecap_modest_growth" in p
    # Non-bellwether same headline should not trigger it
    assert "largecap_modest_growth" not in compute_headline_penalties(
        ctx("SMALLCO net profit rises 6% YoY", symbol="SMALLCO", bellwethers={"HDFCBANK"}))


def test_revenue_profit_divergence():
    assert "revenue_profit_divergence" in compute_headline_penalties(
        ctx("ABC net profit jumps 60% while revenue rises 8%", symbol="ABC"))


def test_body_only_mention_present_and_absent():
    # Company not named -> body-only penalty
    assert "body_only_mention" in compute_headline_penalties(
        ctx("Market rally lifts benchmark indices", symbol="RELIANCE", name="Reliance Industries Limited"))
    # Company named -> no penalty
    assert "body_only_mention" not in compute_headline_penalties(
        ctx("Reliance Industries bags mega order", symbol="RELIANCE", name="Reliance Industries Limited"))


def test_routine_low_signal():
    assert "routine_low_signal" in compute_headline_penalties(
        ctx("ABC general business update", news_category="BUSINESS_UPDATE", impact=40.0, symbol="ABC", name="ABC Ltd"))


def test_speculative_and_tiny_profit():
    assert "speculative_forecast" in compute_headline_penalties(
        ctx("ABC may surge on new deal", symbol="ABC"))
    assert "tiny_absolute_profit" in compute_headline_penalties(
        ctx("ABC reports profit of Rs 3 crore", symbol="ABC"))


def test_subpar_growth():
    assert "subpar_growth_deceleration" in compute_headline_penalties(
        ctx("ABC profit rises 5% in Q2", symbol="ABC"))


def test_clean_quantified_bullish_has_minimal_penalties():
    p = compute_headline_penalties(
        ctx("Reliance Industries bags order worth Rs 4,000 crore",
            cat_str="ORDER_WIN", news_category="ORDER_WIN", symbol="RELIANCE",
            name="Reliance Industries Limited"))
    # A clean, named, quantified order win should not carry the big red-flag penalties
    for bad in ("unquantified_order_win", "body_only_mention", "margin_compression",
                "stale_or_recap_reference", "past_price_action_exhaustion"):
        assert bad not in p


def test_unquantified_order_penalty_softens_at_high_confidence():
    # High-confidence unquantified order win is penalised less harshly, so a
    # genuinely strong catalyst can still reach actionable.
    high = compute_headline_penalties(
        ctx("ABC secures large order", cat_str="ORDER_WIN", confidence=90.0, symbol="ABC"))
    low = compute_headline_penalties(
        ctx("ABC secures large order", cat_str="ORDER_WIN", confidence=70.0, symbol="ABC"))
    assert high["unquantified_order_win"] == -6.0
    assert low["unquantified_order_win"] == -12.0
    assert high["unquantified_order_win"] > low["unquantified_order_win"]
