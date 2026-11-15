"""Tijori Finance quarterly results collector.

Scrapes real-time segment-level results, sales, operating profit, and YoY/QoQ metrics
from https://www.tijorifinance.com/results/quarterly-results/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.tijori")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class TijoriFinanceCollector(BaseCollector):
    """Scrapes structured quarterly results from Tijori Finance."""

    def __init__(
        self,
        source_name: str = "Tijori Finance",
        enabled: bool = True,
        credibility_score: float = 0.95,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.tijorifinance.com/results/quarterly-results/",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting quarterly results from Tijori Finance...")
        try:
            resp = requests.get(
                self.source_url,
                headers=HEADERS,
                timeout=self.timeout_seconds,
            )
            if resp.status_code != 200:
                logger.warning("Tijori Finance returned HTTP %d", resp.status_code)
                return []
        except Exception as exc:
            logger.error("Failed to connect to Tijori Finance: %s", exc)
            return []

        articles: List[CollectedArticle] = []
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="result_item")
        now_dt = datetime.now(timezone.utc)

        for item in items:
            header = item.find("div", class_="result_item__header")
            comp_a = header.find("a") if header else None
            if not comp_a:
                continue

            comp_name = comp_a.get_text(strip=True)
            rel_link = comp_a.get("href", "")
            full_url = f"https://www.tijorifinance.com{rel_link}" if rel_link.startswith("/") else rel_link

            table = item.find("table")
            if not table:
                continue

            sales_yoy, sales_val = "", ""
            op_yoy, op_val = "", ""

            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if not cells:
                    continue
                row_label = cells[0].lower()
                if "sales" in row_label or "revenue" in row_label:
                    sales_yoy = cells[1] if len(cells) > 1 else ""
                    sales_val = cells[3] if len(cells) > 3 else ""
                elif "operating profit" in row_label or "ebitda" in row_label or "net profit" in row_label:
                    op_yoy = cells[1] if len(cells) > 1 else ""
                    op_val = cells[3] if len(cells) > 3 else ""

            # Build high-information financial headline
            parts = [f"{comp_name} Q2 Results:"]
            if op_yoy:
                clean_op_yoy = op_yoy.replace("%", "").strip()
                try:
                    op_num = float(clean_op_yoy.replace(",", ""))
                    word = "jumps" if op_num > 0 else "drops"
                    parts.append(f"Operating profit {word} {abs(op_num):.1f}% YoY")
                except ValueError:
                    parts.append(f"Operating profit growth {op_yoy}")
                if op_val:
                    parts.append(f"to ₹{op_val} Cr")

            if sales_yoy:
                clean_sales_yoy = sales_yoy.replace("%", "").strip()
                try:
                    s_num = float(clean_sales_yoy.replace(",", ""))
                    word = "rises" if s_num > 0 else "falls"
                    parts.append(f", sales {word} {abs(s_num):.1f}%")
                except ValueError:
                    parts.append(f", sales {sales_yoy}")
                if sales_val:
                    parts.append(f"to ₹{sales_val} Cr")

            headline = " ".join(parts).strip()
            summary = (
                f"{comp_name} reported quarterly results. Sales YoY: {sales_yoy} (₹{sales_val} Cr), "
                f"Operating profit YoY: {op_yoy} (₹{op_val} Cr)."
            )

            # Extract date if available in Tijori HTML
            pub_dt = now_dt
            date_span = item.find("span", class_=lambda c: c and "event_date" in c)
            if date_span:
                d_text = date_span.get_text(strip=True)
                if d_text.lower() != "today":
                    try:
                        import dateparser
                        import pytz
                        ist_tz = pytz.timezone("Asia/Kolkata")
                        parsed_d = dateparser.parse(d_text)
                        if parsed_d:
                            # Default to 16:00 IST on that announcement date
                            parsed_dt_ist = ist_tz.localize(datetime.combine(parsed_d.date(), datetime.min.time().replace(hour=16)))
                            pub_dt = parsed_dt_ist.astimezone(timezone.utc)
                    except Exception:
                        pass

            article = CollectedArticle(
                headline=headline,
                article_url=full_url or self.source_url,
                source_name=self.source_name,
                published_at=pub_dt,
                raw_content=summary,
                extracted_text=summary,
                company_mentions=[comp_name],
                credibility_score=self.credibility_score,
            )
            articles.append(article)

        logger.info("Tijori Finance collector retrieved %d structured results", len(articles))
        return articles
