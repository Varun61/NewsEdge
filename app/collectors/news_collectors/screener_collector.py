"""Screener.in collector for management concalls, corporate presentations, and quarterly disclosures.

Scrapes official investor concall links, presentation transcripts, and regulatory filings
from https://www.screener.in/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.screener")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Key high-activity large & mid cap stocks to check on Screener for concall/filing updates
WATCH_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "SBIN",
    "BHARTIARTL", "ITC", "BAJFINANCE", "TATAMOTORS", "TATASTEEL", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "HCLTECH", "ADANIENT", "COALINDIA",
    "NTPC", "ONGC", "POWERGRID", "JSWSTEEL", "HAL", "BEL", "RVNL",
]


class ScreenerCollector(BaseCollector):
    """Scrapes investor concall transcripts, presentations, and announcements from Screener.in."""

    def __init__(
        self,
        source_name: str = "Screener",
        enabled: bool = True,
        credibility_score: float = 0.95,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.screener.in/",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting concalls and management presentations from Screener.in...")
        articles: List[CollectedArticle] = []
        now_dt = datetime.now(timezone.utc)
        seen_urls = set()

        session = requests.Session()
        session.headers.update(HEADERS)

        # Poll recent corporate disclosures across key tracked equities
        for sym in WATCH_SYMBOLS[:12]:  # Check top active stocks
            url = f"https://www.screener.in/company/{sym}/consolidated/"
            try:
                resp = session.get(url, timeout=self.timeout_seconds)
                if resp.status_code != 200:
                    continue
            except Exception as exc:
                logger.debug("Screener fetch error for %s: %s", sym, exc)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            comp_h1 = soup.find("h1")
            comp_name = comp_h1.get_text(strip=True) if comp_h1 else sym

            # Find recent announcements section
            ann_section = soup.find("section", id=lambda i: i and "document" in str(i).lower())
            if not ann_section:
                continue

            # Look for recent transcripts and presentations
            for a in ann_section.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)

                if any(k in href.lower() or k in text.lower() for k in ["concall", "transcript", "presentation", "fact sheet", "investor meet"]):
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # Determine document type
                    is_concall = "transcript" in href.lower() or "concall" in href.lower() or "transcript" in text.lower()
                    doc_type = "Earnings Concall Transcript" if is_concall else "Investor Presentation / Factsheet"

                    headline = f"{sym} ({comp_name}): Latest {doc_type} and Management Commentary"
                    summary = f"{comp_name} ({sym}) published official {doc_type} on Screener.in. Direct document link available."

                    articles.append(
                        CollectedArticle(
                            headline=headline,
                            article_url=href if href.startswith("http") else f"https://www.screener.in{href}",
                            source_name=self.source_name,
                            published_at=now_dt,
                            raw_content=summary,
                            extracted_text=summary,
                            company_mentions=[comp_name, sym],
                            credibility_score=self.credibility_score,
                        )
                    )

        logger.info("Screener collector retrieved %d management concall/filing items", len(articles))
        return articles
