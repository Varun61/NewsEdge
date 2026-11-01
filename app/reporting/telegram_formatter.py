"""Telegram message formatter matching the NewsEdge PRD format.

Produces clean, highly readable messages for intraday stock traders:
- Prominently displays Company Name and NSE Ticker symbol.
- Delivers Top 10 Strongest Bullish stocks in one clean message.
- Delivers Top 10 Strongest Bearish stocks in a second clean message.
- Eliminates repetitive clutter and verbosity for fast scanning.
"""

from __future__ import annotations

import html
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database.models import (
    CandidateClassification,
    DailyWatchlist,
    StockAnalysis,
)

logger = logging.getLogger("newsedge.reporting.formatter")


def _esc(text: str) -> str:
    """Escape HTML entities to prevent Telegram parse errors."""
    return html.escape(text or "")


class TelegramFormatter:
    """Formats DailyWatchlists into clean, highly scannable Telegram messages (HTML)."""

    MAX_MESSAGE_LENGTH = 3900

    @classmethod
    def format_daily_report(
        cls,
        watchlist: DailyWatchlist,
        session: Session,
        window_description: Optional[str] = None,
    ) -> List[str]:
        """Convert a DailyWatchlist into focused Bullish and Bearish messages."""
        ist_date = watchlist.report_date.strftime("%A, %d-%m-%Y")
        collection_meta = window_description or "Previous trading session close to cutoff"

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
            "📊 <b>NEWS EDGE — INDIAN STOCK MARKET WATCHLIST</b>",
            f"📅 <b>Date:</b> {_esc(ist_date)} | ⏰ {_esc(collection_meta)}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🟢 <b>TOP {len(top_bullish)} STRONGEST BULLISH CANDIDATES</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        if not top_bullish:
            lines_bullish.append("<i>No high-probability bullish catalyst identified for this session.</i>")
            lines_bullish.append("")
        else:
            for idx, item in enumerate(top_bullish, 1):
                lines_bullish.extend(cls._format_candidate_card(item, idx, is_bullish=True))

        lines_bullish.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        bullish_text = "\n".join(lines_bullish)
        for chunk in cls._chunk_text(bullish_text):
            messages.append(chunk)

        # ── Message 2: Top Bearish Candidates ──────────────────────────
        lines_bearish = [
            "📊 <b>NEWS EDGE — INDIAN STOCK MARKET WATCHLIST</b>",
            f"📅 <b>Date:</b> {_esc(ist_date)} | ⏰ {_esc(collection_meta)}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔴 <b>TOP {len(top_bearish)} STRONGEST BEARISH CANDIDATES</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        if not top_bearish:
            lines_bearish.append("<i>No high-probability bearish catalyst identified for this session.</i>")
            lines_bearish.append("")
        else:
            for idx, item in enumerate(top_bearish, 1):
                lines_bearish.extend(cls._format_candidate_card(item, idx, is_bullish=False))

        lines_bearish.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
        bearish_text = "\n".join(lines_bearish)
        for chunk in cls._chunk_text(bearish_text):
            messages.append(chunk)

        # ── Message 3: Market Summary & Sources ────────────────────────
        strong_b_count = len([a for a in bullish if a.classification == CandidateClassification.STRONG_BULLISH])
        b_count = len([a for a in bullish if a.classification == CandidateClassification.BULLISH])
        strong_bear_count = len([a for a in bearish if a.classification == CandidateClassification.STRONG_BEARISH])
        bear_count = len([a for a in bearish if a.classification == CandidateClassification.BEARISH])

        summary_lines = [
            "📋 <b>MARKET PREPARATION SUMMARY</b>",
            f"• Bullish Candidates: <b>{len(bullish)}</b> ({strong_b_count} Strong, {b_count} Moderate)",
            f"• Bearish Candidates: <b>{len(bearish)}</b> ({strong_bear_count} Strong, {bear_count} Moderate)",
            f"• Total News Events Analyzed: <b>{watchlist.total_events}</b>",
            f"• Active Sources Checked: <b>{watchlist.successful_sources}/{watchlist.total_sources_checked}</b>",
            "📡 <i>Sources: Google News, ET, Business Standard, Mint, Hindu BusinessLine, Moneycontrol, Financial Express, CNBC-TV18</i>",
            "",
            "⚠️ <b>IMPORTANT:</b>",
            "<i>These research candidates are generated via automated news intelligence.</i>",
            "<i>Actual trades must depend on 9:15 AM opening price action, market breadth, and risk management.</i>",
        ]
        messages.append("\n".join(summary_lines))

        return messages

    @classmethod
    def _format_candidate_card(
        cls, analysis: StockAnalysis, rank: int, is_bullish: bool = True
    ) -> List[str]:
        company = analysis.company
        event = analysis.news_event
        comp_name = company.company_name if company else "Company"
        symbol = company.nse_symbol if company else "UNKNOWN"
        score = int(analysis.overall_score)
        conviction = "STRONG" if "strong" in analysis.classification.value else "MODERATE"
        headline = event.primary_headline if event else "Announcement"
        raw_materiality = (event.financial_materiality or "").strip() if event else ""
        icon = "📈" if is_bullish else "📉"

        # Ensure rationale explanation is rich and not a one-word placeholder (e.g. "High", "Price")
        reason = raw_materiality
        if not reason or len(reason) < 10 or reason.lower() in ("high", "low", "medium", "price", "yes", "no", "n/a"):
            if event and event.reasoning and len(event.reasoning) >= 15:
                reason = event.reasoning
            elif event and event.news_summary and len(event.news_summary) >= 15:
                reason = event.news_summary
            else:
                cat_name = event.news_category.value.replace("_", " ").title() if (event and event.news_category) else "Market Catalyst"
                reason = f"{cat_name} driving institutional intraday repricing"

        # Strip publisher suffix from headline if still present
        from app.processors.nse_master import clean_headline_publisher
        clean_hl = clean_headline_publisher(headline)

        card = [
            f"<b>{rank}. {_esc(comp_name)}</b>",
            f"   NSE: <code>{_esc(symbol)}</code> | ⚡ Score: <b>{score}/100</b> ({conviction})",
            f"   📰 {_esc(clean_hl[:110])}",
            f"   {icon} <i>{_esc(reason[:120])}</i>",
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
