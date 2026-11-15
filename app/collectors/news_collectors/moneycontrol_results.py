"""Moneycontrol latest quarterly results collector.

Scrapes structured earnings results and financial statements from
https://www.moneycontrol.com/markets/earnings/latest-results/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.moneycontrol_results")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class MoneycontrolResultsCollector(BaseCollector):
    """Scrapes structured corporate earnings results from Moneycontrol."""

    def __init__(
        self,
        source_name: str = "Moneycontrol Results",
        enabled: bool = True,
        credibility_score: float = 0.95,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.moneycontrol.com/markets/earnings/latest-results/",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting latest earnings from Moneycontrol Results...")
        try:
            resp = requests.get(
                self.source_url,
                headers=HEADERS,
                timeout=self.timeout_seconds,
            )
            if resp.status_code != 200:
                logger.warning("Moneycontrol Results returned HTTP %d", resp.status_code)
                return []
        except Exception as exc:
            logger.error("Failed to connect to Moneycontrol Results: %s", exc)
            return []

        articles: List[CollectedArticle] = []
        soup = BeautifulSoup(resp.text, "html.parser")
        now_dt = datetime.now(timezone.utc)
        seen_urls = set()

        # Find company results cards / blocks
        tables = soup.find_all("table")
        for t in tables:
            # Find closest company link or heading before or within table container
            parent = t.find_parent("div")
            if not parent:
                continue

            comp_a = parent.find("a", href=lambda h: h and ("/financials/quarterly-results/" in h or "/india/stockpricequote/" in h))
            if not comp_a:
                continue

            comp_name = comp_a.get_text(strip=True)
            if not comp_name or comp_name.lower() in ("results", "financials", "more"):
                continue

            comp_url = comp_a.get("href", "")
            if comp_url in seen_urls:
                continue
            seen_urls.add(comp_url)

            # Parse rows from table
            rev_val, rev_growth = "", ""
            pat_val, pat_growth = "", ""
            gp_val, gp_growth = "", ""

            for tr in t.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if len(cells) < 4:
                    continue
                label = cells[0].lower()
                val = cells[1]
                growth = cells[3]

                if "revenue" in label or "sales" in label:
                    rev_val, rev_growth = val, growth
                elif "net profit" in label or "pat" in label:
                    pat_val, pat_growth = val, growth
                elif "gross profit" in label or "ebitda" in label or "operating" in label:
                    gp_val, gp_growth = val, growth

            parts = [f"{comp_name} Q2 Results:"]
            if pat_growth:
                clean_g = pat_growth.replace("%", "").strip()
                try:
                    p_num = float(clean_g.replace(",", ""))
                    word = "jumps" if p_num > 0 else "drops"
                    parts.append(f"Net profit {word} {abs(p_num):.1f}% YoY")
                except ValueError:
                    parts.append(f"Net profit growth {pat_growth}")
                if pat_val:
                    parts.append(f"to ₹{pat_val} Cr")

            if rev_growth:
                clean_rg = rev_growth.replace("%", "").strip()
                try:
                    r_num = float(clean_rg.replace(",", ""))
                    word = "rises" if r_num > 0 else "falls"
                    parts.append(f", Revenue {word} {abs(r_num):.1f}%")
                except ValueError:
                    parts.append(f", Revenue {rev_growth}")
                if rev_val:
                    parts.append(f"to ₹{rev_val} Cr")

            headline = " ".join(parts).strip()
            summary = f"{comp_name} latest quarterly results reported on Moneycontrol. Revenue: ₹{rev_val} Cr ({rev_growth}), Net Profit: ₹{pat_val} Cr ({pat_growth})."

            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url=comp_url or self.source_url,
                    source_name=self.source_name,
                    published_at=now_dt,
                    raw_content=summary,
                    extracted_text=summary,
                    company_mentions=[comp_name],
                    credibility_score=self.credibility_score,
                )
            )

        logger.info("Moneycontrol Results collector retrieved %d company earnings records", len(articles))
        return articles
