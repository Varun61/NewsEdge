"""STOCKSCOPE 360 — Intraday Telegram Signal Formatter."""

from __future__ import annotations

import html
from typing import List

from app.market_data.intraday_scanner import StockScopeCandidate
from app.trading_calendar import now_ist


class IntradayAlertFormatter:
    """Formats confirmed intraday trade signals and scan summaries for Telegram."""

    @staticmethod
    def format_confirmed_signal(c: StockScopeCandidate) -> str:
        """Format a single confirmed LONG or SHORT setup into an actionable Telegram alert."""
        is_long = c.trade_status == "CONFIRMED_LONG"
        icon = "🟢" if is_long else "🔴"
        action = "CONFIRMED LONG" if is_long else "CONFIRMED SHORT"
        snap = c.snapshot

        lines = [
            f"{icon} <b>STOCKSCOPE 360 — {action}</b>",
            f"<b>{html.escape(c.company_name)}</b> (NSE: <code>{c.symbol}</code>)",
            f"⏱ {now_ist().strftime('%d-%b %H:%M IST')} | Score: <b>{c.total_score}/100</b>",
            "",
            f"📊 <b>Score Breakdown:</b>",
            f"  • Catalyst: <b>{c.catalyst_score}/35</b> ({html.escape(c.catalyst_type)})",
            f"  • Technical: <b>{c.intraday_score}/45</b> ({html.escape(snap.signal_summary)})",
            f"  • Liquidity: <b>{c.liquidity_score}/20</b> (Turnover ₹{c.avg_traded_value_cr} Cr | ATR ₹{c.atr_14})",
            "",
            f"📈 <b>Intraday Levels:</b>",
            f"  • LTP: <b>₹{snap.ltp:,.2f}</b> ({snap.gap_pct:+.2f}%) | VWAP: ₹{snap.vwap:,.2f}",
            f"  • ORB (9:15–9:30): ₹{snap.opening_range_low or 0:,.2f} – ₹{snap.opening_range_high or 0:,.2f} [{snap.orb_signal.upper()}]",
            f"  • RelVol: <b>{snap.relative_volume}x</b> | RSI(14): {snap.rsi_14 or 'N/A'} | EMA(9): ₹{snap.ema9 or 0:,.2f}",
        ]

        if c.playbook:
            lines.extend([
                "",
                f"🎯 <b>Trade Playbook ({c.playbook.risk_reward}):</b>",
                f"  • {html.escape(c.playbook.summary_text)}",
            ])

        if c.headline:
            lines.extend([
                "",
                f"📰 <i>{html.escape(c.headline[:160])}</i>",
            ])

        if c.news_urls:
            links = [f'<a href="{html.escape(u)}">Source {i}</a>' for i, u in enumerate(c.news_urls[:2], 1)]
            lines.append("🔗 " + " | ".join(links))

        lines.append("\n<i>⚠️ Paper-trade / research alert. Verify order book & VWAP before entry.</i>")
        return "\n".join(lines)

    @staticmethod
    def format_scan_summary(candidates: List[StockScopeCandidate], session_str: str) -> str:
        """Format a compact summary of the intraday scan (including NO TRADE if none confirmed)."""
        confirmed = [c for c in candidates if c.trade_status in ("CONFIRMED_LONG", "CONFIRMED_SHORT")]
        watching = [c for c in candidates if c.trade_status == "WATCH"]

        lines = [
            f"📡 <b>STOCKSCOPE 360 Scan Summary</b> ({session_str})",
            f"Scanned: {len(candidates)} catalyst stocks | Confirmed: <b>{len(confirmed)}</b> | Watching: <b>{len(watching)}</b>",
            "",
        ]

        if not confirmed:
            lines.append("🛑 <b>NO TRADE CONFIRMED YET</b> — Waiting for VWAP + Opening Range confirmation.")
        else:
            lines.append("✅ <b>Confirmed Setups:</b>")
            for c in confirmed[:6]:
                icon = "🟢" if c.trade_status == "CONFIRMED_LONG" else "🔴"
                lines.append(
                    f"  {icon} <b>{c.symbol}</b> — {c.total_score}/100 | "
                    f"LTP ₹{c.snapshot.ltp:,.1f} ({c.snapshot.gap_pct:+.1f}%) | "
                    f"RelVol {c.snapshot.relative_volume}x"
                )

        if watching:
            lines.append("\n👀 <b>On Watch (Pre-Breakout):</b>")
            for c in watching[:5]:
                lines.append(
                    f"  • <b>{c.symbol}</b> ({c.total_score}/100): {html.escape(c.rejection_reason or 'Monitoring')}"
                )

        return "\n".join(lines)
