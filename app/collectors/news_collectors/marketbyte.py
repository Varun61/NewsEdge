"""MarketByte collector for daily earnings beats/misses and market briefs.

Scrapes breaking earnings summaries and market intelligence from https://marketbyte.in/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.marketbyte")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class MarketByteCollector(BaseCollector):
    """Scrapes breaking earnings summaries and market intelligence from MarketByte."""

    def __init__(
        self,
        source_name: str = "MarketByte",
        enabled: bool = True,
        credibility_score: float = 0.90,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://marketbyte.in/",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting earnings and market briefs from MarketByte...")
        try:
            resp = requests.get(
                self.source_url,
                headers=HEADERS,
                timeout=self.timeout_seconds,
            )
            if resp.status_code != 200:
                logger.warning("MarketByte returned HTTP %d", resp.status_code)
                return []
        except Exception as exc:
            logger.error("Failed to connect to MarketByte: %s", exc)
            return []

        articles: List[CollectedArticle] = []
        soup = BeautifulSoup(resp.text, "html.parser")
        now_dt = datetime.now(timezone.utc)
        seen_urls = set()

        # 1. Company earnings beats / misses from company links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)

            if href.startswith("/company/") and ("Revenue" in text or "Net profit" in text or "Beat" in text or "Miss" in text):
                full_url = f"https://marketbyte.in{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                comp_name = ""
                # Try finding exact company name element inside anchor
                sub_elems = [e.get_text(strip=True) for e in a.find_all(["span", "p", "div", "h3", "h4", "h5"]) if e.get_text(strip=True)]
                if len(sub_elems) >= 3 and len(sub_elems[2]) > 2:
                    comp_name = sub_elems[2]
                else:
                    # Fallback to slug
                    slug = href.replace("/company/", "").replace("-", " ").title()
                    comp_name = slug

                # Extract Revenue and Net Profit Beat / Miss
                rev_match = re.search(r"Revenue\s*(?:₹|Rs\.?)?\s*([\d,]+)\s*Cr", text)
                np_match = re.search(r"Net\s+profit\s*(Beat|Miss)\s*([-+]?[\d.]+)%", text)

                rev_str = f"Revenue ₹{rev_match.group(1)} Cr" if rev_match else ""
                if np_match:
                    verdict, pct = np_match.group(1), np_match.group(2)
                    np_str = f"Net profit {verdict} ({pct}%)"
                else:
                    np_str = ""

                parts = [f"{comp_name} Q2 Results:"]
                if np_str:
                    parts.append(np_str)
                if rev_str:
                    parts.append(f"with {rev_str}")

                headline = " ".join(parts).strip()
                if len(parts) == 1:
                    headline = f"{comp_name} Financial Update"

                articles.append(
                    CollectedArticle(
                        headline=headline,
                        article_url=full_url,
                        source_name=self.source_name,
                        published_at=now_dt,
                        raw_content=text,
                        extracted_text=text,
                        company_mentions=[],
                        credibility_score=self.credibility_score,
                    )
                )

            # 2. Market updates / Pre-market briefs
            elif href.startswith("/updates/") and len(text) > 25:
                full_url = f"https://marketbyte.in{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                headline = text
                # Strip reading time or author
                headline = re.sub(r"^\w+\s+\d+\s+\w+\s+\d{4}\s*·\s*\d+\s*min\s*read\s*", "", headline).strip()

                articles.append(
                    CollectedArticle(
                        headline=headline,
                        article_url=full_url,
                        source_name=self.source_name,
                        published_at=now_dt,
                        raw_content=text,
                        extracted_text=text,
                        company_mentions=[],
                        credibility_score=self.credibility_score,
                    )
                )

        logger.info("MarketByte collector retrieved %d items", len(articles))
        return articles
