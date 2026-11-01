"""Google News RSS collector for Indian stock market topics."""

from __future__ import annotations

import logging
import urllib.parse
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.google_news")


class GoogleNewsCollector(BaseCollector):
    """Aggregates Indian stock market news from Google News RSS search queries."""

    DEFAULT_QUERIES = [
        "indian stock market NSE",
        "NSE corporate announcements",
        "NSE stocks order win OR contract",
        "NSE quarterly results profit OR revenue",
        "NSE SEBI penalty OR probe OR raid",
        "NSE dividend OR buyback OR bonus",
    ]

    def __init__(
        self,
        source_name: str = "Google News RSS",
        enabled: bool = True,
        credibility_score: float = 0.65,
        queries: list[str] | None = None,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://news.google.com/rss",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.queries = queries or self.DEFAULT_QUERIES

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        if not self.enabled:
            return []

        seen_urls: set[str] = set()
        all_articles: list[CollectedArticle] = []

        for q in self.queries:
            encoded_query = urllib.parse.quote(q)
            feed_url = (
                f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            )
            sub_collector = RSSCollector(
                source_name=self.source_name,
                feed_url=feed_url,
                enabled=True,
                credibility_score=self.credibility_score,
            )
            batch = sub_collector.collect(since, until)
            for art in batch:
                if art.article_url not in seen_urls:
                    seen_urls.add(art.article_url)
                    all_articles.append(art)

        logger.info("Google News aggregate returned %d unique articles", len(all_articles))
        return all_articles
