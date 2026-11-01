"""Standalone HTML report generator for NewsEdge watchlists."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from jinja2 import Template
from sqlalchemy.orm import Session

from app.database.models import CandidateClassification, DailyWatchlist, StockAnalysis

logger = logging.getLogger("newsedge.reporting.html")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NewsEdge - Indian Stock Watchlist ({{ report_date }})</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; line-height: 1.5; }
  .container { max-width: 900px; margin: 0 auto; }
  header { border-bottom: 2px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }
  h1 { margin: 0 0 8px 0; color: #38bdf8; font-size: 28px; }
  .meta { color: #94a3b8; font-size: 14px; }
  .section-title { font-size: 20px; font-weight: 700; margin: 24px 0 16px 0; padding-bottom: 8px; border-bottom: 1px solid #334155; }
  .bullish-title { color: #4ade80; }
  .bearish-title { color: #f87171; }
  .watch-title { color: #fbbf24; }
  .card { background: #1e293b; border-radius: 8px; padding: 16px; margin-bottom: 16px; border-left: 4px solid #64748b; }
  .card-bullish { border-left-color: #22c55e; }
  .card-bearish { border-left-color: #ef4444; }
  .card-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
  .stock-name { font-size: 18px; font-weight: 600; color: #ffffff; }
  .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; text-transform: uppercase; }
  .badge-bullish { background: #14532d; color: #86efac; }
  .badge-bearish { background: #7f1d1d; color: #fca5a5; }
  .score { font-weight: 700; color: #38bdf8; }
  .headline { font-size: 15px; margin: 8px 0; color: #e2e8f0; font-weight: 500; }
  .materiality { background: #0f172a; border-radius: 6px; padding: 10px; margin: 8px 0; font-size: 13px; color: #cbd5e1; }
  .details-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; font-size: 12px; margin-top: 10px; color: #94a3b8; }
  .sources a { color: #38bdf8; text-decoration: none; margin-right: 12px; }
  .sources a:hover { text-decoration: underline; }
  footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #334155; color: #64748b; font-size: 12px; text-align: center; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>NewsEdge Intelligence Watchlist</h1>
    <div class="meta">
      <strong>Report Date:</strong> {{ report_date }} | 
      <strong>Collection Window:</strong> Previous Trading Day 15:30 &rarr; Today 07:59 IST |
      <strong>Scoring Version:</strong> {{ scoring_version }}
    </div>
  </header>

  <div class="section-title bullish-title">&bull; BULLISH CANDIDATES ({{ bullish|length }})</div>
  {% for item in bullish %}
  <div class="card card-bullish">
    <div class="card-header">
      <div class="stock-name">{{ item.company.company_name }} (NSE: {{ item.company.nse_symbol }})</div>
      <div>
        <span class="badge badge-bullish">{{ item.classification.value }}</span>
        <span class="score">{{ item.overall_score|round|int }}/100</span>
      </div>
    </div>
    <div class="headline">&bull; {{ item.news_event.primary_headline }}</div>
    <div class="materiality"><strong>Why it matters:</strong> {{ item.news_event.financial_materiality }}</div>
    <div class="details-grid">
      <div>Catalyst: <strong>{{ item.news_event.news_category.value if item.news_event.news_category else 'N/A' }}</strong></div>
      <div>Sentiment: <strong>{{ item.news_event.sentiment.value if item.news_event.sentiment else 'N/A' }}</strong></div>
      <div>Confidence: <strong>{{ item.company_confidence_score|round|int }}%</strong></div>
      <div>Impact Score: <strong>{{ item.news_impact_score|round|int }}</strong></div>
    </div>
    {% if item.news_event.article_links %}
    <div class="sources" style="margin-top: 10px; font-size: 12px;">
      <strong>Sources:</strong>
      {% for link in item.news_event.article_links %}
        {% if link.article %}
          <a href="{{ link.article.article_url }}" target="_blank">{{ link.article.source.name if link.article.source else 'Article' }}</a>
        {% endif %}
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% else %}
  <p style="color: #64748b;">No high-priority bullish candidates identified.</p>
  {% endfor %}

  <div class="section-title bearish-title">&bull; BEARISH CANDIDATES ({{ bearish|length }})</div>
  {% for item in bearish %}
  <div class="card card-bearish">
    <div class="card-header">
      <div class="stock-name">{{ item.company.company_name }} (NSE: {{ item.company.nse_symbol }})</div>
      <div>
        <span class="badge badge-bearish">{{ item.classification.value }}</span>
        <span class="score">{{ item.overall_score|round|int }}/100</span>
      </div>
    </div>
    <div class="headline">&bull; {{ item.news_event.primary_headline }}</div>
    <div class="materiality"><strong>Why it matters:</strong> {{ item.news_event.financial_materiality }}</div>
    <div class="details-grid">
      <div>Catalyst: <strong>{{ item.news_event.news_category.value if item.news_event.news_category else 'N/A' }}</strong></div>
      <div>Sentiment: <strong>{{ item.news_event.sentiment.value if item.news_event.sentiment else 'N/A' }}</strong></div>
      <div>Confidence: <strong>{{ item.company_confidence_score|round|int }}%</strong></div>
      <div>Impact Score: <strong>{{ item.news_impact_score|round|int }}</strong></div>
    </div>
    {% if item.news_event.article_links %}
    <div class="sources" style="margin-top: 10px; font-size: 12px;">
      <strong>Sources:</strong>
      {% for link in item.news_event.article_links %}
        {% if link.article %}
          <a href="{{ link.article.article_url }}" target="_blank">{{ link.article.source.name if link.article.source else 'Article' }}</a>
        {% endif %}
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% else %}
  <p style="color: #64748b;">No high-priority bearish candidates identified.</p>
  {% endfor %}

  <footer>
    DISCLAIMER: NewsEdge candidates are research and intelligence ideas based on aggregated news disclosures, not investment or trading signals. Confirm opening market liquidity, VWAP, and price action before taking any trading decisions.
  </footer>
</div>
</body>
</html>
"""


class HTMLReportGenerator:
    """Generates standalone styled HTML reports."""

    @staticmethod
    def generate(watchlist: DailyWatchlist, session: Session) -> str:
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

        template = Template(HTML_TEMPLATE)
        return template.render(
            report_date=watchlist.report_date.strftime("%Y-%m-%d"),
            scoring_version=watchlist.scoring_version,
            bullish=bullish,
            bearish=bearish,
        )

    @classmethod
    def save(cls, watchlist: DailyWatchlist, session: Session, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        html_content = cls.generate(watchlist, session)
        path = output_dir / f"newsedge_{watchlist.report_date.strftime('%Y-%m-%d')}.html"
        path.write_text(html_content, encoding="utf-8")
        logger.info("Saved HTML report to %s", path)
        return path
