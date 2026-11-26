"""Tests for the NSE sec_bhavdata parser (pure/offline)."""

from app.market_data.bhavcopy import parse_sec_bhavdata

# Mirrors the real file: header/value cells carry leading spaces; DELIV_PER can be '-'.
_CSV = (
    "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, "
    "CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
    "20MICRONS, EQ, 26-Nov-2026, 179.13, 181.85, 182.00, 175.80, 176.31, 176.43, 177.59, 36715, 65.20, 1853, 18862, 51.37\n"
    "RELIANCE, EQ, 26-Nov-2026, 2900.00, 2910.00, 2950.00, 2905.00, 2945.00, 2948.00, 2930.00, 5000000, 14650.00, 120000, 3500000, 70.00\n"
    "SOMEFUT, FUTSTK, 26-Nov-2026, 1, 1, 1, 1, 1, 1, 1, 10, 1, 1, 0, -\n"
    "ILLIQ, BE, 26-Nov-2026, 50.00, 50.5, 51, 49, 50, 50, 50, 1000, 0.5, 20, 500, -\n"
)


def test_parses_equity_rows_only():
    bars = parse_sec_bhavdata(_CSV)
    assert "20MICRONS" in bars and "RELIANCE" in bars
    assert "SOMEFUT" not in bars  # non-equity series skipped
    assert "ILLIQ" in bars        # BE is an equity series


def test_fields_mapped_and_stripped():
    b = parse_sec_bhavdata(_CSV)["20MICRONS"]
    assert b.close == 176.43
    assert b.qty == 36715
    assert b.deliv_per == 51.37
    assert b.prev_close == 179.13
    assert b.high == 182.00


def test_missing_delivery_is_negative_sentinel():
    b = parse_sec_bhavdata(_CSV)["ILLIQ"]
    assert b.deliv_per == -1.0


def test_empty_input_safe():
    assert parse_sec_bhavdata("") == {}
    assert parse_sec_bhavdata("SYMBOL, SERIES\n") == {}
