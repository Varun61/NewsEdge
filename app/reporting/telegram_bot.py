"""Telegram Bot service for NewsEdge report delivery and interactive queries."""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from app.config import Settings, get_settings
from app.database.database import get_session
from app.database.models import CandidateClassification, DailyWatchlist
from app.database.repository import Repository
from app.reporting.telegram_formatter import TelegramFormatter

logger = logging.getLogger("newsedge.reporting.telegram")


class TelegramBot:
    """Manages Telegram communications: one-shot daily dispatch and interactive commands."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.token = self.settings.telegram_bot_token
        self.chat_id = self.settings.telegram_chat_id
        self.authorized_ids = self.settings.authorized_user_ids

    def _is_authorized(self, user_id: int) -> bool:
        if not self.authorized_ids:
            return True  # If not configured, allow
        return user_id in self.authorized_ids

    async def send_daily_report(self, messages: List[str]) -> bool:
        """Send formatted daily report messages to the configured TELEGRAM_CHAT_ID."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram bot credentials not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing).")
            return False

        try:
            bot = Bot(token=self.token)
            for msg in messages:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(0.5)  # Respect rate limits
            logger.info("Successfully delivered %d Telegram message chunk(s) to %s", len(messages), self.chat_id)
            return True
        except Exception as exc:
            logger.error("Failed to send Telegram report: %s", exc)
            return False

    async def send_error_notification(self, error_message: str) -> None:
        """Alert admin chat when a critical failure occurs."""
        if not self.token or not self.chat_id:
            return
        try:
            bot = Bot(token=self.token)
            alert = f"🚨 <b>NewsEdge System Alert</b>\n\n{error_message}"
            await bot.send_message(chat_id=self.chat_id, text=alert, parse_mode=ParseMode.HTML)
        except Exception as exc:
            logger.error("Failed to send Telegram error alert: %s", exc)

    def build_application(self) -> Application:
        """Construct interactive Application for long-polling command mode."""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set to run interactive bot.")

        app = Application.builder().token(self.token).build()

        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("help", self._cmd_help))
        app.add_handler(CommandHandler("today", self._cmd_today))
        app.add_handler(CommandHandler("bullish", self._cmd_bullish))
        app.add_handler(CommandHandler("bearish", self._cmd_bearish))
        app.add_handler(CommandHandler("stock", self._cmd_stock))
        app.add_handler(CommandHandler("status", self._cmd_status))

        return app

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Unauthorized access.")
            return

        text = (
            "👋 <b>Welcome to NewsEdge</b>\n"
            "Indian Intraday Stock Intelligence System.\n\n"
            "Available commands:\n"
            "/today - Get today's full watchlist\n"
            "/bullish - Top bullish candidates\n"
            "/bearish - Top bearish candidates\n"
            "/stock SYMBOL - Analysis for a specific stock (e.g. /stock RELIANCE)\n"
            "/status - System health and sources\n"
            "/help - Display this help message"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._cmd_start(update, context)

    async def _cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self._is_authorized(user_id):
            return

        from app.trading_calendar import today_ist
        with get_session() as session:
            wl = Repository.get_watchlist_by_date(session, today_ist())
            if not wl:
                await update.message.reply_text("No watchlist generated yet for today.")
                return

            chunks = TelegramFormatter.format_daily_report(wl, session)
            for ch in chunks:
                await update.message.reply_text(ch, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    async def _cmd_bullish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self._is_authorized(user_id):
            return

        from app.trading_calendar import today_ist
        with get_session() as session:
            candidates = Repository.get_bullish_candidates(session, today_ist())
            if not candidates:
                await update.message.reply_text("No bullish candidates found for today.")
                return

            lines = ["🟢 <b>TODAY'S BULLISH CANDIDATES</b>", ""]
            for idx, c in enumerate(candidates, 1):
                lines.append(f"<b>{idx}. {c.company.company_name}</b> ({c.company.nse_symbol})")
                lines.append(f"⚡ Score: {int(c.overall_score)}/100 | {c.classification.value.upper()}")
                lines.append(f"📰 {c.news_event.primary_headline}")
                lines.append("")

            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    async def _cmd_bearish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self._is_authorized(user_id):
            return

        from app.trading_calendar import today_ist
        with get_session() as session:
            candidates = Repository.get_bearish_candidates(session, today_ist())
            if not candidates:
                await update.message.reply_text("No bearish candidates found for today.")
                return

            lines = ["🔴 <b>TODAY'S BEARISH CANDIDATES</b>", ""]
            for idx, c in enumerate(candidates, 1):
                lines.append(f"<b>{idx}. {c.company.company_name}</b> ({c.company.nse_symbol})")
                lines.append(f"⚡ Score: {int(c.overall_score)}/100 | {c.classification.value.upper()}")
                lines.append(f"📰 {c.news_event.primary_headline}")
                lines.append("")

            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    async def _cmd_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self._is_authorized(user_id):
            return

        if not context.args:
            await update.message.reply_text("Usage: /stock SYMBOL (e.g. /stock RELIANCE)")
            return

        symbol = context.args[0].upper()
        with get_session() as session:
            comp = Repository.get_company_by_symbol(session, symbol)
            if not comp:
                await update.message.reply_text(f"Stock '{symbol}' not found in database.")
                return

            text = (
                f"🏢 <b>{comp.company_name}</b> (NSE: {comp.nse_symbol})\n"
                f"Sector: {comp.sector or 'N/A'}\n"
                f"Industry: {comp.industry or 'N/A'}\n"
                f"Market Cap Cat: {comp.market_cap_category.value if comp.market_cap_category else 'N/A'}\n"
                f"Baseline Revenue: ₹{comp.annual_revenue:,.1f} Cr\n"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id if update.effective_user else 0
        if not self._is_authorized(user_id):
            return

        with get_session() as session:
            sources = Repository.get_enabled_sources(session)
            lines = ["⚙️ <b>SYSTEM STATUS & HEALTH</b>", ""]
            lines.append(f"Enabled Sources: {len(sources)}")
            for s in sources:
                lines.append(f"• <b>{s.name}</b> ({s.source_type.value}) - Last: {s.last_collected_at or 'Never'}")

            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
