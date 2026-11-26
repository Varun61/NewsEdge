"""Tests for the central NSE->yfinance symbol remap (pure/offline)."""

from app.market_data.yf_symbols import current_symbol, to_yf_ticker


def test_zomato_remapped_to_eternal():
    assert current_symbol("ZOMATO") == "ETERNAL"
    assert to_yf_ticker("ZOMATO") == "ETERNAL.NS"


def test_unchanged_symbol_passthrough():
    assert current_symbol("RELIANCE") == "RELIANCE"
    assert to_yf_ticker("RELIANCE") == "RELIANCE.NS"


def test_case_and_whitespace_normalised():
    assert to_yf_ticker("  zomato ") == "ETERNAL.NS"
    assert current_symbol(" reliance ") == "RELIANCE"


def test_empty_symbol_safe():
    assert to_yf_ticker("") == ".NS"
