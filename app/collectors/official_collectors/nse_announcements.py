"""NSE corporate announcements collector.

Fetches official exchange filings and corporate announcements directly from the
National Stock Exchange of India (NSE) official corporate announcements API.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

import requests

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.nse")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
}


class NSEAnnouncementCollector(BaseCollector):
    """Collector for National Stock Exchange (NSE) Official Corporate Disclosures."""

    def __init__(
        self,
        source_name: str = "NSE Announcements",
        enabled: bool = True,
        credibility_score: float = 1.0,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds
        self.api_url = "https://www.nseindia.com/api/corporate-announcements?index=equities"

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting official filings from NSE Corporate Announcements API...")
        articles: List[CollectedArticle] = []

        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            # Fetch announcements directly
            resp = session.get(self.api_url, timeout=self.timeout_seconds)

            if resp.status_code != 200:
                logger.warning("NSE Announcements API returned HTTP %d", resp.status_code)
                return []

            data = resp.json()
            if not isinstance(data, list):
                logger.warning("Unexpected response format from NSE API")
                return []

        except Exception as exc:
            logger.error("Failed to fetch NSE Announcements: %s", exc)
            return []

        for item in data:
            symbol = item.get("symbol", "")
            comp_name = item.get("sm_name", symbol)
            desc = item.get("desc", "")
            voice_summary = item.get("voiceSummary", "")
            att_file = item.get("attchmntFile", "")
            att_text = item.get("attchmntText", "")
            sort_date_str = item.get("sort_date", "")

            # Parse date (NSE sort_date is in IST: "YYYY-MM-DD HH:MM:SS")
            pub_dt = None
            if sort_date_str:
                try:
                    import pytz
                    ist_tz = pytz.timezone("Asia/Kolkata")
                    dt_naive = datetime.strptime(sort_date_str, "%Y-%m-%d %H:%M:%S")
                    pub_dt = ist_tz.localize(dt_naive).astimezone(timezone.utc)
                except Exception:
                    pub_dt = datetime.now(timezone.utc)
            else:
                pub_dt = datetime.now(timezone.utc)

            # Build headline
            headline = f"{symbol} ({comp_name}): {desc}"
            if voice_summary:
                first_sentence = voice_summary.split(".")[0].strip()
                if len(first_sentence) > 20:
                    headline = f"{symbol} ({comp_name}): {first_sentence}"

            content = voice_summary or att_text or desc
            url = att_file or f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url=url,
                    source_name=self.source_name,
                    published_at=pub_dt,
                    raw_content=content,
                    extracted_text=content,
                    company_mentions=[comp_name, symbol],
                    credibility_score=self.credibility_score,
                )
            )

        logger.info("NSE Announcements collector retrieved %d official filings", len(articles))
        return articles
