"""The Core Earnings collector.

Scrapes executive earnings tracking, management highlights, and results updates
from https://earnings.thecore.in/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.thecore")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class TheCoreEarningsCollector(BaseCollector):
    """Scrapes corporate earnings disclosures from The Core Earnings."""

    def __init__(
        self,
        source_name: str = "The Core Earnings",
        enabled: bool = True,
        credibility_score: float = 0.90,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://earnings.thecore.in/",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting earnings updates from The Core Earnings...")
        try:
            resp = requests.get(
                self.source_url,
                headers=HEADERS,
                timeout=self.timeout_seconds,
            )
            if resp.status_code != 200:
                logger.warning("The Core Earnings returned HTTP %d", resp.status_code)
                return []
        except Exception as exc:
            logger.error("Failed to connect to The Core Earnings: %s", exc)
            return []

        articles: List[CollectedArticle] = []
        soup = BeautifulSoup(resp.text, "html.parser")
        now_dt = datetime.now(timezone.utc)
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("/company/"):
                continue

            full_url = f"https://earnings.thecore.in{href}"
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            text = a.get_text(" ", strip=True)
            if not text or len(text) < 2:
                continue

            # e.g. "Tata Consultancy Services (TCS)" or "Reliance Industries"
            comp_name = text
            ticker_match = re.search(r"/company/([A-Z0-9\-]+)\.NS", href)
            symbol = ticker_match.group(1) if ticker_match else ""

            headline = f"{comp_name} ({symbol}) Quarterly Earnings & Disclosures Update" if symbol else f"{comp_name} Quarterly Earnings Update"
            summary = f"{comp_name} filed quarterly results and earnings disclosures tracked on The Core Earnings."

            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url=full_url,
                    source_name=self.source_name,
                    published_at=now_dt,
                    raw_content=summary,
                    extracted_text=summary,
                    company_mentions=[comp_name],
                    credibility_score=self.credibility_score,
                )
            )

        logger.info("The Core Earnings collector retrieved %d companies", len(articles))
        return articles
