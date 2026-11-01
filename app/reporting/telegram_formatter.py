"""Telegram message formatter matching modern, minimalist fintech standards.

Produces clean, aesthetic, and scannable messages for stock traders:
- Monospace tap-to-copy NSE ticker (`<code>SYMBOL</code>`)
- Bold clear company name
- One concise line of news catalyst
- Minimal visual noise and no verbose clutter
"""

from __future__ import annotations

import html
import logging
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import (
    CandidateClassification,
    DailyWatchlist,
    StockAnalysis,
)
from app.processors.nse_master import clean_headline_publisher

logger = logging.getLogger("newsedge.reporting.formatter")


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
        "Q4 results:", "Q1 results:", "Exclusive:",
    ):
        if clean.lower().startswith(prefix.lower()):
            clean = clean[len(prefix):].strip()

    clean = " ".join(clean.split())  # normalize extra spaces
    if len(clean) > max_chars:
        clean = clean[:max_chars].rsplit(" ", 1)[0] + "…"
    return clean


class TelegramFormatter:
    """Formats DailyWatchlists into modern, clean, scannable Telegram messages (HTML)."""

    MAX_MESSAGE_LENGTH = 3900

    @classmethod
    def format_daily_report(
        cls,
        watchlist: DailyWatchlist,
        session: Session,
        window_description: Optional[str] = None,
    ) -> List[str]:
        """Convert a DailyWatchlist into focused Bullish and Bearish messages."""
        date_str = watchlist.report_date.strftime("%d %b")

        items = sorted(watchlist.items, key=lambda it: it.rank_position)
        analyses: list[StockAnalysis] = [it.stock_analysis for it in items if it.stock_analysis]

        bullish = [
            a for a in analyses
            if a.classification in (CandidateClassification.STRONG_BULLISH, CandidateClassification.BULLISH)
        ]
        bearish = [
            a for a in analyses
            if a.classification in (CandidateClassification.STRONG_BEARISH, CandidateClassification.BEARISH)
        ]

        # Select Top 10 unique companies for Bullish and Top 10 unique companies for Bearish
        seen_comps = set()
        top_bullish = []
        for a in bullish:
            if a.company_id and a.company_id not in seen_comps:
                seen_comps.add(a.company_id)
                top_bullish.append(a)
                if len(top_bullish) == 10:
                    break

        top_bearish = []
        for a in bearish:
            if a.company_id and a.company_id not in seen_comps:
                seen_comps.add(a.company_id)
                top_bearish.append(a)
                if len(top_bearish) == 10:
                    break

        messages: List[str] = []

        # ── Message 1: Top Bullish Candidates ──────────────────────────
        lines_bullish = [
            f"🟢 <b>BULLISH WATCHLIST</b> • {date_str}",
            "",
        ]

        if not top_bullish:
            lines_bullish.append("<i>No high-conviction bullish catalysts found today.</i>")
        else:
            for idx, item in enumerate(top_bullish, 1):
                lines_bullish.extend(cls._format_candidate_card(item, idx, is_bullish=True))

        bullish_text = "\n".join(lines_bullish).strip()
        for chunk in cls._chunk_text(bullish_text):
            messages.append(chunk)

        # ── Message 2: Top Bearish Candidates ──────────────────────────
        lines_bearish = [
            f"🔴 <b>BEARISH WATCHLIST</b> • {date_str}",
            "",
        ]

        if not top_bearish:
            lines_bearish.append("<i>No high-conviction bearish catalysts found today.</i>")
        else:
            for idx, item in enumerate(top_bearish, 1):
                lines_bearish.extend(cls._format_candidate_card(item, idx, is_bullish=False))

        # ── Optional: Major Sector Catalysts & News Highlights ─────────
        major_section = cls._format_major_catalysts(analyses)
        if major_section:
            lines_bearish.extend(major_section)

        bearish_text = "\n".join(lines_bearish).strip()
        for chunk in cls._chunk_text(bearish_text):
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

            # Deduplicate by event
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
            if len(seen_events) >= 3:  # Limit to Top 3 major developments
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

        card = [
            f"{rank}. <code>{_esc(symbol)}</code> • <b>{_esc(comp_name)}</b>",
            f"   {_esc(concise_news)}",
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
