"""Indian trading calendar – holidays, weekend checks, collection windows.

NSE holidays are updated annually.  The 2024-2026 list covers the near-term.
Store all timestamps in UTC internally and display them in IST.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

import pytz

IST = pytz.timezone("Asia/Kolkata")

# ── NSE holidays (date only, not including weekends) ─────────────────
NSE_HOLIDAYS: set[date] = {
    # 2024
    date(2024, 1, 26), date(2024, 3, 8), date(2024, 3, 25),
    date(2024, 3, 29), date(2024, 4, 11), date(2024, 4, 14),
    date(2024, 4, 17), date(2024, 4, 21), date(2024, 5, 1),
    date(2024, 5, 20), date(2024, 5, 23), date(2024, 6, 17),
    date(2024, 7, 17), date(2024, 8, 15), date(2024, 9, 16),
    date(2024, 10, 2), date(2024, 10, 12), date(2024, 10, 31),
    date(2024, 11, 1), date(2024, 11, 15), date(2024, 12, 25),
    # 2025
    date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31),
    date(2025, 4, 10), date(2025, 4, 14), date(2025, 4, 18),
    date(2025, 5, 1), date(2025, 5, 12), date(2025, 6, 27),
    date(2025, 7, 10), date(2025, 8, 15), date(2025, 8, 16),
    date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 20),
    date(2025, 10, 21), date(2025, 10, 22), date(2025, 11, 5),
    date(2025, 11, 26), date(2025, 12, 25),
    # 2026
    date(2026, 1, 26), date(2026, 3, 5), date(2026, 3, 19),
    date(2026, 3, 20), date(2026, 4, 3), date(2026, 4, 14),
    date(2026, 5, 1), date(2026, 5, 25), date(2026, 6, 16),
    date(2026, 7, 1), date(2026, 8, 15), date(2026, 9, 4),
    date(2026, 10, 2), date(2026, 10, 9), date(2026, 10, 20),
    date(2026, 11, 14), date(2026, 11, 24), date(2026, 12, 25),
}


def is_trading_day(d: date) -> bool:
    """Return True if *d* is an NSE trading day (Mon–Fri, not a holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in NSE_HOLIDAYS


def previous_trading_day(d: date) -> date:
    """Return the most recent trading day strictly before *d*."""
    candidate = d - timedelta(days=1)
    while not is_trading_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def next_trading_day(d: date) -> date:
    """Return the next trading day on or after *d*."""
    candidate = d
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def today_ist() -> date:
    """Return today's date in IST."""
    return datetime.now(IST).date()


def now_utc() -> datetime:
    """Return current UTC-aware datetime."""
    return datetime.now(timezone.utc)


def now_ist() -> datetime:
    """Return current IST-aware datetime."""
    return datetime.now(IST)


def utc_to_ist(dt: datetime) -> datetime:
    """Convert a UTC datetime to IST."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def ist_to_utc(dt: datetime) -> datetime:
    """Convert an IST datetime to UTC."""
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    return dt.astimezone(timezone.utc)


def get_collection_window(
    report_date: date,
    start_hour: int = 15,
    start_minute: int = 30,
    end_hour: int = 7,
    end_minute: int = 59,
) -> Tuple[datetime, datetime]:
    """Return the standard (start_utc, end_utc) collection window for a given report date.

    * **start** = previous trading day at ``start_hour:start_minute`` IST
    * **end**   = ``report_date`` at ``end_hour:end_minute`` IST
    """
    prev_day = previous_trading_day(report_date)
    start_ist = IST.localize(datetime.combine(prev_day, time(start_hour, start_minute)))
    end_ist = IST.localize(datetime.combine(report_date, time(end_hour, end_minute)))

    return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)


def get_last_market_close(dt: Optional[datetime] = None) -> datetime:
    """Return the datetime (in IST) of the most recent NSE market close (15:30 IST).

    - If dt is on a trading day (Mon-Fri) and time >= 15:30 IST:
        returns today at 15:30 IST.
    - If dt is on a trading day (Mon-Fri) and time < 15:30 IST:
        returns previous trading day at 15:30 IST.
    - If dt is on a weekend or trading holiday:
        returns previous trading day at 15:30 IST.
    """
    if dt is not None:
        current = dt.astimezone(IST) if dt.tzinfo else IST.localize(dt)
    else:
        current = now_ist()

    target_d = current.date()

    if is_trading_day(target_d) and current.time() >= time(15, 30):
        return IST.localize(datetime.combine(target_d, time(15, 30)))

    prev_d = previous_trading_day(target_d)
    return IST.localize(datetime.combine(prev_d, time(15, 30)))


def get_effective_collection_window(
    report_date: Optional[date] = None,
    lookback_hours: Optional[int] = None,
    is_adhoc: bool = False,
    start_hour: int = 15,
    start_minute: int = 30,
    end_hour: int = 7,
    end_minute: int = 59,
) -> Tuple[datetime, datetime, str]:
    """Calculate the collection window dynamically.

    Rules:
    - If run on Sunday or Monday (or weekend):
        Collects from previous trading day's (Friday) 15:30 IST up to current time,
        capturing all Friday post-market and weekend news.
    - If run on a regular weekday (Tuesday - Friday):
        Collects the last 24 hours of news up to current time (or previous trading day 15:30),
        allowing both market-hours news (for priced-in lists) and post-market news (for fresh lists).
    - If scheduled cron run:
        Uses previous trading day 15:30 IST to today's end_hour:end_minute IST.

    Returns:
        (start_utc, end_utc, window_description)
    """
    current_ist = now_ist()
    target_date = report_date or current_ist.date()

    # Case 1: Scheduled cron run on a trading day (e.g. 07:59 AM morning run)
    if not is_adhoc and report_date is not None:
        prev_day = previous_trading_day(target_date)
        start_ist = IST.localize(datetime.combine(prev_day, time(start_hour, start_minute)))
        scheduled_end = IST.localize(datetime.combine(target_date, time(end_hour, end_minute)))

        start_utc = start_ist.astimezone(timezone.utc)
        end_utc = scheduled_end.astimezone(timezone.utc)

        days_span = (target_date - prev_day).days
        if days_span > 1:
            desc = (
                f"Weekend window: {prev_day.strftime('%A')} 15:30 to "
                f"{target_date.strftime('%A')} {scheduled_end.strftime('%H:%M')} IST (includes Sat & Sun)"
            )
        else:
            desc = (
                f"Overnight window: {prev_day.strftime('%d-%b')} 15:30 to "
                f"{target_date.strftime('%d-%b')} {scheduled_end.strftime('%H:%M')} IST"
            )
        return start_utc, end_utc, desc

    # Case 2: Run on Sunday or Monday pre-market (before Monday 3:30 PM IST)
    # Picks from Friday 3:30 PM up to current time (capturing weekend and Friday evening)
    is_sunday = target_date.weekday() == 6
    is_monday_before_close = target_date.weekday() == 0 and current_ist.time() < time(start_hour, start_minute)
    if is_sunday or is_monday_before_close or (target_date.weekday() == 5 and not is_adhoc):
        prev_trading = previous_trading_day(target_date)
        start_ist = IST.localize(datetime.combine(prev_trading, time(start_hour, start_minute)))
        end_utc = now_utc()
        end_ist = current_ist
        start_utc = start_ist.astimezone(timezone.utc)
        desc = (
            f"Weekend/Pre-market window: {prev_trading.strftime('%A')} 15:30 to "
            f"{end_ist.strftime('%a %H:%M')} IST (from Friday 3:30 PM)"
        )
        return start_utc, end_utc, desc

    # Case 3: Ad-hoc run on a Saturday with explicit 24h request or standard ad-hoc
    if target_date.weekday() == 5 and is_adhoc and report_date is not None:
        end_utc = now_utc()
        start_utc = end_utc - timedelta(hours=24)
        desc = (
            f"Ad-hoc 24h window: "
            f"{utc_to_ist(start_utc).strftime('%d-%b %H:%M')} to "
            f"{utc_to_ist(end_utc).strftime('%d-%b %H:%M')} IST"
        )
        return start_utc, end_utc, desc

    # Case 4: Explicit lookback hours requested (e.g. --hours 24) on normal weekday
    if lookback_hours is not None and lookback_hours > 0:
        end_utc = now_utc()
        start_utc = end_utc - timedelta(hours=lookback_hours)
        desc = (
            f"Last {lookback_hours} hours: "
            f"{utc_to_ist(start_utc).strftime('%d-%b %H:%M')} to "
            f"{utc_to_ist(end_utc).strftime('%d-%b %H:%M')} IST"
        )
        return start_utc, end_utc, desc

    # Case 5: Default weekday ad-hoc run (collects from last market close or 24h)
    end_utc = now_utc()
    start_utc = end_utc - timedelta(hours=24)
    desc = (
        f"Last 24 hours: "
        f"{utc_to_ist(start_utc).strftime('%d-%b %H:%M')} to "
        f"{utc_to_ist(end_utc).strftime('%d-%b %H:%M')} IST"
    )
    return start_utc, end_utc, desc
