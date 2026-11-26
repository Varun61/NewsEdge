"""STOCKSCOPE 360 — Intraday Layer 3 Runner & 5-Minute Live Scanner.

Usage:
    python -m app.intraday_runner --once
    python -m app.intraday_runner --once --symbols RELIANCE TCS SBIN
    python -m app.intraday_runner --loop --interval 300 --telegram
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from typing import List, Optional, Set, Tuple

from sqlalchemy import desc, select

from app.config import get_settings
from app.database.database import get_session, init_db
from app.database.models import CandidateClassification, DailyWatchlist
from app.logger import setup_logging
from app.market_data.intraday_scanner import IntradayScanner, StockScopeCandidate
from app.reporting.intraday_alerts import IntradayAlertFormatter
from app.reporting.telegram_bot import TelegramBot
from app.trading_calendar import is_trading_day, now_ist

logger = logging.getLogger("newsedge.intraday_runner")


def load_watchlist_candidates(limit: int = 25) -> list[dict]:
    """Load top bullish & bearish candidates from the latest DailyWatchlist in DB."""
    init_db()
    candidates: list[dict] = []
    seen_symbols: set[str] = set()

    with get_session() as session:
        latest_wl = session.execute(
            select(DailyWatchlist).order_by(desc(DailyWatchlist.report_date)).limit(1)
        ).scalar_one_or_none()

        if not latest_wl or not latest_wl.items:
            logger.warning("No DailyWatchlist found in database. Run NewsEdge pre-market pipeline first or pass --symbols.")
            return []

        for item in sorted(latest_wl.items, key=lambda x: x.rank_position):
            sa = item.stock_analysis
            if not sa or not sa.news_event:
                continue
            # Load company via event or analysis
            comp = sa.company if hasattr(sa, "company") and sa.company else None
            if not comp:
                continue

            sym = comp.nse_symbol.upper()
            if sym in seen_symbols:
                continue
            seen_symbols.add(sym)

            is_bull = sa.classification in (
                CandidateClassification.STRONG_BULLISH,
                CandidateClassification.BULLISH,
            )
            is_bear = sa.classification in (
                CandidateClassification.STRONG_BEARISH,
                CandidateClassification.BEARISH,
            )
            if not (is_bull or is_bear):
                continue

            ev = sa.news_event
            urls = []
            if ev.articles:
                for link in ev.articles:
                    if link.raw_article and link.raw_article.source_url:
                        urls.append(link.raw_article.source_url)

            candidates.append({
                "symbol": sym,
                "company_name": comp.company_name,
                "direction": "BULLISH" if is_bull else "BEARISH",
                "raw_score": sa.overall_score,
                "catalyst_type": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                "headline": ev.title or "",
                "news_urls": urls[:3],
            })

            if len(candidates) >= limit:
                break

    return candidates


def print_scan_table(results: List[StockScopeCandidate], session_date_str: str) -> None:
    """Print formatted STOCKSCOPE 360 console report."""
    print("\n" + "=" * 95)
    print(f"STOCKSCOPE 360 — INTRADAY SCANNER REPORT (Session: {session_date_str})")
    print("=" * 95)

    if not results:
        print("No candidates scanned (check Angel One scrip master or watchlist).")
        print("=" * 95 + "\n")
        return

    header = f"{'SYMBOL':<12} {'DIR':<8} {'STATUS':<16} {'SCORE':>6} {'CAT/35':>6} {'TEC/45':>6} {'LIQ/20':>6} {'LTP':>9} {'VWAP':>9} {'RVOL':>6}"
    print(header)
    print("-" * 95)
    for c in results:
        s = c.snapshot
        print(
            f"{c.symbol:<12} {c.direction:<8} {c.trade_status:<16} "
            f"{c.total_score:>6.1f} {c.catalyst_score:>6.1f} {c.intraday_score:>6.1f} {c.liquidity_score:>6.1f} "
            f"{s.ltp:>9.2f} {s.vwap:>9.2f} {s.relative_volume:>5.2f}x"
        )
        if c.playbook and c.trade_status in ("CONFIRMED_LONG", "CONFIRMED_SHORT"):
            print(f"   ▶ {c.playbook.summary_text} ({c.playbook.risk_reward})")
        elif c.rejection_reason:
            print(f"   · {c.rejection_reason}")
    print("=" * 95 + "\n")


def run_scan_once(
    scanner: IntradayScanner,
    symbols: Optional[list[str]] = None,
    send_telegram: bool = False,
    alerted_keys: Optional[Set[Tuple[str, str]]] = None,
) -> list[StockScopeCandidate]:
    """Execute one full intraday scan cycle."""
    if symbols:
        watchlist = [
            {
                "symbol": sym.upper(),
                "company_name": sym.upper(),
                "direction": "BULLISH",
                "raw_score": 70.0,
                "catalyst_type": "MANUAL_SCAN",
                "headline": f"Manual intraday scan for {sym.upper()}",
                "news_urls": [],
            }
            for sym in symbols
        ]
    else:
        watchlist = load_watchlist_candidates(limit=25)

    if not watchlist:
        return []

    session_date = scanner.resolve_session_date()
    results = scanner.scan_candidates(watchlist, session_date=session_date)
    print_scan_table(results, str(session_date))

    if send_telegram:
        bot = TelegramBot(get_settings())
        confirmed = [c for c in results if c.trade_status in ("CONFIRMED_LONG", "CONFIRMED_SHORT")]
        sent_count = 0

        for c in confirmed:
            key = (c.symbol, c.trade_status)
            if alerted_keys is not None and key in alerted_keys:
                continue
            msg = IntradayAlertFormatter.format_confirmed_signal(c)
            if asyncio.run(bot.send_daily_report([msg])):
                sent_count += 1
                if alerted_keys is not None:
                    alerted_keys.add(key)

        if sent_count == 0 and alerted_keys is None:
            # Single --once run: send scan summary even if NO TRADE
            summary_msg = IntradayAlertFormatter.format_scan_summary(results, str(session_date))
            asyncio.run(bot.send_daily_report([summary_msg]))

    return results


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="STOCKSCOPE 360 Intraday Scanner")
    parser.add_argument("--once", action="store_true", help="Run a single intraday scan and exit")
    parser.add_argument("--loop", action="store_true", help="Continuously scan every --interval seconds during market hours")
    parser.add_argument("--interval", type=int, default=300, help="Scan interval in seconds for --loop (default: 300s / 5m)")
    parser.add_argument("--symbols", nargs="+", default=None, help="Optional list of NSE symbols to scan directly")
    parser.add_argument("--telegram", action="store_true", help="Send confirmed signals to Telegram")
    args = parser.parse_args()

    scanner = IntradayScanner()

    if args.loop:
        logger.info("Starting STOCKSCOPE 360 live 5-min loop (interval=%ds)...", args.interval)
        alerted: Set[Tuple[str, str]] = set()
        while True:
            cur = now_ist()
            # Market hours: Mon-Fri 09:15 to 15:25 IST
            in_market = (
                is_trading_day(cur.date())
                and ((cur.hour == 9 and cur.minute >= 15) or (10 <= cur.hour <= 14) or (cur.hour == 15 and cur.minute <= 25))
            )
            if in_market:
                run_scan_once(scanner, symbols=args.symbols, send_telegram=args.telegram, alerted_keys=alerted)
            else:
                logger.info("Outside live market hours (%s). Waiting...", cur.strftime("%H:%M IST"))
            time.sleep(args.interval)
    else:
        run_scan_once(scanner, symbols=args.symbols, send_telegram=args.telegram)


if __name__ == "__main__":
    main()
