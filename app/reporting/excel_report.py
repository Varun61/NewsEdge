"""Excel workbook report generator for NewsEdge watchlists."""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.database.models import CandidateClassification, DailyWatchlist, StockAnalysis

logger = logging.getLogger("newsedge.reporting.excel")


class ExcelReportGenerator:
    """Generates an Excel workbook with Summary, Bullish, Bearish, and Watch Only sheets."""

    @classmethod
    def generate(cls, watchlist: DailyWatchlist, session: Session, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()

        items = sorted(watchlist.items, key=lambda it: it.rank_position)
        analyses: list[StockAnalysis] = [it.stock_analysis for it in items if it.stock_analysis]

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

        # ── 1. Summary Sheet ─────────────────────────────────────────
        ws_sum = wb.active
        ws_sum.title = "Summary"
        ws_sum.append(["NewsEdge Intraday Stock Intelligence Report"])
        ws_sum.append(["Report Date", watchlist.report_date.strftime("%Y-%m-%d")])
        ws_sum.append(["Scoring Version", watchlist.scoring_version])
        ws_sum.append(["Total Unique Events", watchlist.total_events])
        ws_sum.append(["Sources Checked", f"{watchlist.successful_sources}/{watchlist.total_sources_checked}"])
        ws_sum.append([])

        bullish = [a for a in analyses if a.classification in (CandidateClassification.STRONG_BULLISH, CandidateClassification.BULLISH)]
        bearish = [a for a in analyses if a.classification in (CandidateClassification.STRONG_BEARISH, CandidateClassification.BEARISH)]
        watch = [a for a in analyses if a.classification == CandidateClassification.WATCH_ONLY]

        ws_sum.append(["Category", "Count"])
        ws_sum.append(["Bullish Candidates", len(bullish)])
        ws_sum.append(["Bearish Candidates", len(bearish)])
        ws_sum.append(["Watch Only", len(watch)])

        # ── 2. Candidates Sheets ─────────────────────────────────────
        headers = [
            "Rank", "Symbol", "Company", "Score", "Classification", "Catalyst",
            "Sentiment", "Impact", "Materiality", "Headline", "Why It Matters", "Sources"
        ]

        def _populate_sheet(ws, candidates, is_bullish=True):
            ws.append(headers)
            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center" if col_num in (1, 4) else "left")

            for rank, a in enumerate(candidates, 1):
                sym = a.company.nse_symbol if a.company else ""
                name = a.company.company_name if a.company else ""
                ev = a.news_event
                cat = ev.news_category.value if (ev and ev.news_category) else ""
                sent = ev.sentiment.value if (ev and ev.sentiment) else ""
                head = ev.primary_headline if ev else ""
                mat = ev.financial_materiality if ev else ""

                sources_str = ", ".join(
                    link.article.source.name for link in ev.article_links if (link.article and link.article.source)
                ) if ev else ""

                ws.append([
                    rank, sym, name, round(a.overall_score, 1), a.classification.value,
                    cat, sent, round(a.news_impact_score, 1), round(a.materiality_score, 1),
                    head, mat, sources_str
                ])

            # Auto fit widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 50)

        ws_bull = wb.create_sheet("Bullish Candidates")
        _populate_sheet(ws_bull, bullish, is_bullish=True)

        ws_bear = wb.create_sheet("Bearish Candidates")
        _populate_sheet(ws_bear, bearish, is_bullish=False)

        ws_watch = wb.create_sheet("Watch Only")
        _populate_sheet(ws_watch, watch, is_bullish=True)

        filepath = output_dir / f"newsedge_{watchlist.report_date.strftime('%Y-%m-%d')}.xlsx"
        wb.save(filepath)
        logger.info("Saved Excel report to %s", filepath)
        return filepath
