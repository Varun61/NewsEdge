"""Brokerage Radar and Morning Analyst Calls collector.

Scrapes target price upgrades, downgrades, and consensus revisions from
global and domestic institutional brokerages (Morgan Stanley, CLSA, Jefferies,
Goldman Sachs, Motilal Oswal, Kotak Institutional Equities, Nomura, Macquarie).
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import List, Set

import dateparser
import feedparser

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.processors.nse_master import clean_headline_publisher

logger = logging.getLogger("newsedge.collectors.brokerage_radar")

BROKERAGE_QUERIES = [
    'brokerage radar OR "maintains buy" OR "raises target" OR "cuts target" site:moneycontrol.com',
    '"target price" OR "upgrade to buy" OR "downgrade to sell" site:economictimes.indiatimes.com',
    'brokerage calls "Jefferies" OR "CLSA" OR "Morgan Stanley" OR "Goldman Sachs" OR "Nomura" NSE',
]


class BrokerageRadarCollector(BaseCollector):
    """Scrapes sell-side analyst calls and institutional target price updates."""

    def __init__(
        self,
        source_name: str = "Brokerage Radar",
        enabled: bool = True,
        credibility_score: float = 0.90,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.moneycontrol.com/news/brokerage-radar/",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        articles: List[CollectedArticle] = []
        seen_urls: Set[str] = set()

        for q in BROKERAGE_QUERIES:
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    link = entry.get("link", "")
                    if not link or link in seen_urls:
                        continue

                    title = clean_headline_publisher(entry.get("title", ""))
                    if not title:
                        continue

                    # Filter for brokerage-relevant keywords
                    title_lower = title.lower()
                    brokerage_keywords = [
                        "target", "brokerage", "upgrade", "downgrade", "buy rating",
                        "sell rating", "outperform", "underperform", "clsa", "jefferies",
                        "morgan stanley", "goldman sachs", "nomura", "motilal", "macquarie",
                        "kotak", "nifty", "initiates", "cuts target", "hikes target"
                    ]
                    if not any(k in title_lower for k in brokerage_keywords):
                        continue

                    pub_raw = entry.get("published", "")
                    pub_dt = dateparser.parse(pub_raw) if pub_raw else None
                    if pub_dt:
                        if pub_dt.tzinfo is None:
                            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                        if pub_dt < since or pub_dt > until:
                            continue
                    else:
                        pub_dt = datetime.now(timezone.utc)

                    seen_urls.add(link)
                    summary = entry.get("summary", title)

                    articles.append(
                        CollectedArticle(
                            headline=title,
                            article_url=link,
                            source_name=self.source_name,
                            published_at=pub_dt,
                            raw_content=summary,
                            extracted_text=summary,
                            source_credibility=self.credibility_score,
                        )
                    )
            except Exception as exc:
                logger.debug("Brokerage radar query error: %s", exc)

        logger.info("BrokerageRadarCollector retrieved %d analyst notes", len(articles))
        return articles
