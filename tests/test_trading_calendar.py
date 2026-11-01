"""Tests for Indian trading calendar, holiday logic, and collection window computation."""

from datetime import date, datetime, timezone
import pytz

from app.trading_calendar import (
    get_collection_window,
    is_trading_day,
    previous_trading_day,
    utc_to_ist,
    IST,
)


def test_is_trading_day():
    # Regular trading days (Monday to Friday, non-holiday)
    assert is_trading_day(date(2025, 10, 27)) is True  # Monday
    assert is_trading_day(date(2025, 10, 28)) is True  # Tuesday

    # Weekends
    assert is_trading_day(date(2025, 10, 25)) is False  # Saturday
    assert is_trading_day(date(2025, 10, 26)) is False  # Sunday

    # Known NSE holidays
    assert is_trading_day(date(2025, 10, 2)) is False   # Gandhi Jayanti
    assert is_trading_day(date(2025, 12, 25)) is False  # Christmas


def test_previous_trading_day_weekend():
    # If Monday, previous trading day should be Friday
    monday = date(2025, 10, 27)
    friday = date(2025, 10, 24)
    assert previous_trading_day(monday) == friday


def test_previous_trading_day_holiday():
    # 2025-10-02 is a Thursday holiday. For Friday 2025-10-03, previous day should be Wednesday 2025-10-01
    friday = date(2025, 10, 3)
    wednesday = date(2025, 10, 1)
    assert previous_trading_day(friday) == wednesday


def test_get_collection_window():
    # Tuesday 28-Oct-2025
    tuesday = date(2025, 10, 28)
    start_utc, end_utc = get_collection_window(tuesday)

    start_ist = utc_to_ist(start_utc)
    end_ist = utc_to_ist(end_utc)

    # Previous trading day Monday 27-Oct at 15:30 IST
    assert start_ist.date() == date(2025, 10, 27)
    assert start_ist.hour == 15
    assert start_ist.minute == 30

    # Current trading day Tuesday 28-Oct at 07:59 IST
    assert end_ist.date() == date(2025, 10, 28)
    assert end_ist.hour == 7
    assert end_ist.minute == 59


def test_monday_collection_window_includes_weekend():
    # Monday 02-Nov-2026: Window starts Friday 30-Oct-2026 15:30 IST
    from app.trading_calendar import get_effective_collection_window
    monday = date(2026, 11, 2)

    start_utc, end_utc, desc = get_effective_collection_window(report_date=monday)
    start_ist = utc_to_ist(start_utc)
    end_ist = utc_to_ist(end_utc)

    # Starts Friday 15:30
    assert start_ist.date() == date(2026, 10, 30)
    assert start_ist.hour == 15
    assert start_ist.minute == 30

    # Ends Monday morning
    assert end_ist.date() == date(2026, 11, 2)
    assert "Sat & Sun" in desc or "weekend" in desc.lower()


def test_adhoc_run_now_gives_24_hours():
    from app.trading_calendar import get_effective_collection_window
    # When run on a weekend adhoc, should span 24 hours
    saturday = date(2026, 10, 31)
    start_utc, end_utc, desc = get_effective_collection_window(
        report_date=saturday,
        is_adhoc=True,
    )
    diff_hours = (end_utc - start_utc).total_seconds() / 3600.0
    assert abs(diff_hours - 24.0) < 0.1
    assert "24h" in desc.lower()

