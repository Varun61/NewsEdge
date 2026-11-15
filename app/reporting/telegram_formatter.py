"""Telegram message formatter with 4-category system for actionable trading intelligence.

Categories:
1. 🟢 BULLISH — Fresh post-market news, actionable for next trading day
2. 🔴 BEARISH — Fresh post-market news, actionable for next trading day
3. 📊 PRICED-IN BULLISH — News from during market hours (already reflected in price); momentum play
4. 📊 PRICED-IN BEARISH — News from during market hours (already reflected in price); momentum play

Produces clean, aesthetic, scannable messages for stock traders:
- Monospace tap-to-copy NSE ticker (`<code>SYMBOL</code>`)
- Bold clear company name
- One concise line of news catalyst
- Direct clickable link to news source
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime, time, timezone
from typing import List, Optional

import pytz

from sqlalchemy.orm import Session

from app.database.models import (
    CandidateClassification,
    DailyWatchlist,
    StockAnalysis,
)
from app.processors.nse_master import clean_headline_publisher

logger = logging.getLogger("newsedge.reporting.formatter")

IST = pytz.timezone("Asia/Kolkata")
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM IST


def _esc(text: str) -> str:
    """Escape HTML entities to prevent Telegram parse errors."""
    return html.escape(text or "")


def _format_concise_headline(headline: str, max_chars: int = 75) -> str:
    """Strip news prefixes, publishers, and cleanly truncate to a single crisp line."""
    clean = clean_headline_publisher(headline or "")

    # Strip common wire prefixes
    for prefix in (
        "Earnings call transcript:", "Transcript:", "Live:", "Alert:",
        "Watch:", "Stock in focus:", "Stocks in focus:", "Stocks to watch:",
        "Buzzing stock:", "Buzzing stocks:", "Q2 results:", "Q3 results:",
        "Q4 results:", "Q1 results:", "Exclusive:", "Q2 results impact:",
        "Q3 results impact:", "Q1 results impact:", "Q4 results impact:",
    ):
        if clean.lower().startswith(prefix.lower()):
            clean = clean[len(prefix):].strip()

    clean = " ".join(clean.split())  # normalize extra spaces
    if len(clean) > max_chars:
        clean = clean[:max_chars].rsplit(" ", 1)[0] + "…"
    return clean


def _is_priced_in(analysis: StockAnalysis) -> bool:
    """Determine if the news was published during market hours (already priced in).
    
    News published between 9:15 AM IST and 3:30 PM IST on a weekday
    is considered 'priced in' — the market has already reacted.
    """
    event = analysis.news_event
    if not event:
        return False
    
    # Check article publication times
    pub_times = []
    if event.article_links:
        for link in event.article_links:
            art = getattr(link, "article", None)
            if art and getattr(art, "published_at", None):
                pub_times.append(art.published_at)
    
    if not pub_times:
        if event.created_at:
            pub_times.append(event.created_at)
        else:
            return False
    
    # Use the earliest publication time
    earliest = min(pub_times)
    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=timezone.utc)
    
    earliest_ist = earliest.astimezone(IST)
    pub_time = earliest_ist.time()
    pub_weekday = earliest_ist.weekday()
    
    # During market hours: 9:15 AM to 3:30 PM IST on weekdays
    market_open = time(9, 15)
    market_close = time(15, 30)
    
    if pub_weekday < 5 and market_open <= pub_time <= market_close:
        return True
    
    # Also check: headline mentions retrospective price action
    h_lower = (event.primary_headline or "").lower()
    retro_patterns = [
        r"\b(?:shares?|stocks?)\s+(?:surge|rall|jump|gain|climb|soar|rise|zoom)\w*\s+(?:over\s+|nearly\s+|by\s+)?\d+",
        r"\b(?:shares?|stocks?)\s+(?:gain|rise|hit|extend)\w*\s+(?:after|as|on)\b",
        r"\bextend\w*\s+(?:\d{4}\s+)?gain",
        r"\b(?:hits?|at)\s+(?:52-week|record|all-time|year|new|lifetime)\s*-?\s*high",
        r"\bup\s+\d+.*(?:from\s+(?:52-week\s+)?low|from\s+ipo)",
        r"\b(?:stock|shares?)\s+(?:up|down)\s+(?:over\s+)?\d+%?\s+today",
    ]
    if any(re.search(pat, h_lower) for pat in retro_patterns):
        return True
    
    return False


class TelegramFormatter:
    """Formats DailyWatchlists into 4-category Telegram messages (HTML)."""

    MAX_MESSAGE_LENGTH = 3900

    @classmethod
    def format_daily_report(
        cls,
        watchlist: DailyWatchlist,
        session: Session,
        window_description: Optional[str] = None,
    ) -> List[str]:
        """Convert a DailyWatchlist into 4-category messages:
        1. Fresh Bullish, 2. Fresh Bearish, 3. Priced-In Bullish, 4. Priced-In Bearish.
        """
        date_str = watchlist.report_date.strftime("%d %b")

        items = sorted(watchlist.items, key=lambda it: it.rank_position)
        analyses: list[StockAnalysis] = [it.stock_analysis for it in items if it.stock_analysis]

        # Separate into bullish and bearish
        all_bullish = [
            a for a in analyses
            if a.classification in (CandidateClassification.STRONG_BULLISH, CandidateClassification.BULLISH)
        ]
        all_bearish = [
            a for a in analyses
            if a.classification in (CandidateClassification.STRONG_BEARISH, CandidateClassification.BEARISH)
        ]

        # Further split into fresh vs priced-in
        fresh_bullish_raw = [a for a in all_bullish if not _is_priced_in(a)]
        priced_bullish_raw = [a for a in all_bullish if _is_priced_in(a)]
        fresh_bearish_raw = [a for a in all_bearish if not _is_priced_in(a)]
        priced_bearish_raw = [a for a in all_bearish if _is_priced_in(a)]

        # Deduplicate per company — and prevent same stock in both bullish AND bearish
        global_seen = set()

        def _dedupe_top(items_list: list[StockAnalysis], max_items: int = 10) -> list[StockAnalysis]:
            result = []
            for a in items_list:
                if a.company_id and a.company_id not in global_seen:
                    global_seen.add(a.company_id)
                    result.append(a)
                    if len(result) == max_items:
                        break
            return result

        # Fresh lists first (higher priority), then priced-in
        top_fresh_bullish = _dedupe_top(fresh_bullish_raw, 10)
        top_fresh_bearish = _dedupe_top(fresh_bearish_raw, 10)
        top_priced_bullish = _dedupe_top(priced_bullish_raw, 5)
        top_priced_bearish = _dedupe_top(priced_bearish_raw, 5)

        messages: List[str] = []

        # ── Message 1: Fresh Bullish ──────────────────────────────
        lines = [
            f"🟢 <b>BULLISH WATCHLIST</b> • {date_str}",
            f"<i>Fresh post-market catalysts for next trading day</i>",
            "",
        ]
        if not top_fresh_bullish:
            lines.append("<i>No high-conviction bullish catalysts found.</i>")
        else:
            for idx, item in enumerate(top_fresh_bullish, 1):
                lines.extend(cls._format_candidate_card(item, idx, is_bullish=True))
        for chunk in cls._chunk_text("\n".join(lines).strip()):
            messages.append(chunk)

        # ── Message 2: Fresh Bearish ──────────────────────────────
        lines = [
            f"🔴 <b>BEARISH WATCHLIST</b> • {date_str}",
            f"<i>Fresh post-market catalysts for next trading day</i>",
            "",
        ]
        if not top_fresh_bearish:
            lines.append("<i>No high-conviction bearish catalysts found.</i>")
        else:
            for idx, item in enumerate(top_fresh_bearish, 1):
                lines.extend(cls._format_candidate_card(item, idx, is_bullish=False))
        for chunk in cls._chunk_text("\n".join(lines).strip()):
            messages.append(chunk)

        # ── Message 3: Priced-In Bullish ──────────────────────────
        if top_priced_bullish:
            lines = [
                f"📊 <b>PRICED-IN BULLISH</b> • {date_str}",
                f"<i>Market already reacted — consider momentum only</i>",
                "",
            ]
            for idx, item in enumerate(top_priced_bullish, 1):
                lines.extend(cls._format_candidate_card(item, idx, is_bullish=True))
            for chunk in cls._chunk_text("\n".join(lines).strip()):
                messages.append(chunk)

        # ── Message 4: Priced-In Bearish ──────────────────────────
        if top_priced_bearish:
            lines = [
                f"📊 <b>PRICED-IN BEARISH</b> • {date_str}",
                f"<i>Market already reacted — consider momentum only</i>",
                "",
            ]
            for idx, item in enumerate(top_priced_bearish, 1):
                lines.extend(cls._format_candidate_card(item, idx, is_bullish=False))
            for chunk in cls._chunk_text("\n".join(lines).strip()):
                messages.append(chunk)

        # ── Optional: Major Sector Catalysts ──────────────────────
        major_section = cls._format_major_catalysts(analyses)
        if major_section:
            major_text = "\n".join(major_section).strip()
            for chunk in cls._chunk_text(major_text):
                messages.append(chunk)

        return messages

    @classmethod
    def _format_major_catalysts(cls, analyses: List[StockAnalysis]) -> List[str]:
        """Extract and format distinct major sector/policy news events with direct news links."""
        seen_events = set()
        cards = []

        for a in analyses:
            ev = a.news_event
            if not ev or ev.id in seen_events:
                continue

            mat = (ev.financial_materiality or "").strip()
            is_thematic = mat.startswith("[") and "]" in mat
            is_major = (
                a.overall_score >= 82.0
                or (ev.impact_score and ev.impact_score >= 82.0)
                or is_thematic
            )

            if not is_major:
                continue

            # Find direct article URL and publisher name
            url = None
            source_label = "News Source"
            if ev.article_links:
                for link in ev.article_links:
                    art = getattr(link, "article", None)
                    if art and getattr(art, "article_url", None):
                        url = art.article_url
                        src = getattr(art, "source", None)
                        if src and getattr(src, "name", None):
                            source_label = src.name
                        elif getattr(art, "source_name", None):
                            source_label = art.source_name
                        break

            seen_events.add(ev.id)

            if is_thematic:
                theme_title = mat.split("]")[0].replace("[", "").strip()
            else:
                comp = a.company
                theme_title = comp.company_name if comp else "Corporate Catalyst"

            highlight = _format_concise_headline(ev.primary_headline, max_chars=85)

            card_lines = [
                f"• <b>{_esc(theme_title)}</b>",
                f"  {_esc(highlight)}",
            ]
            if url:
                card_lines.append(f'  🔗 <a href="{_esc(url)}">Read on {_esc(source_label)}</a>')
            card_lines.append("")

            cards.extend(card_lines)
            if len(seen_events) >= 3:
                break

        if not cards:
            return []

        return [
            "",
            "🌐 <b>KEY SECTOR DEVELOPMENTS</b>",
            "",
            *cards,
        ]

    @classmethod
    def _format_candidate_card(
        cls, analysis: StockAnalysis, rank: int, is_bullish: bool = True
    ) -> List[str]:
        company = analysis.company
        event = analysis.news_event
        comp_name = company.company_name if company else "Company"
        symbol = company.nse_symbol if company else "UNKNOWN"
        headline = event.primary_headline if event else "Announcement"

        concise_news = _format_concise_headline(headline, max_chars=75)

        # Extract direct article link to original news source
        url = None
        if event and event.article_links:
            for link in event.article_links:
                art = getattr(link, "article", None)
                if art and getattr(art, "article_url", None):
                    url = art.article_url
                    break

        link_html = f' • <a href="{_esc(url)}">LINK</a>' if url else ""

        card = [
            f"{rank}. <code>{_esc(symbol)}</code> • <b>{_esc(comp_name)}</b>",
            f"   {_esc(concise_news)}{link_html}",
            "",
        ]
        return card

    @classmethod
    def _chunk_text(cls, text: str) -> List[str]:
        """Split text into chunks smaller than MAX_MESSAGE_LENGTH without breaking HTML tags."""
        if len(text) <= cls.MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        lines = text.split("\n")
        current_chunk: list[str] = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1
            if current_len + line_len > cls.MAX_MESSAGE_LENGTH:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    @classmethod
    def format_startup_notification(cls, *args, **kwargs) -> str:
        """Minimal, modern startup alert."""
        return "⚡ <b>News Feed started</b>"
