"""Business Standard RSS collector."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.business_standard")


class BusinessStandardCollector(BaseCollector):
    """Collects markets and company news from Business Standard RSS."""

    FEEDS = [
        "https://www.business-standard.com/rss/markets-106.rss",
        "https://www.business-standard.com/rss/companies-101.rss",
    ]

    def __init__(
        self,
        source_name: str = "Business Standard",
        enabled: bool = True,
        credibility_score: float = 0.70,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.business-standard.com",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        if not self.enabled:
            return []

        seen_urls: set[str] = set()
        articles: list[CollectedArticle] = []

        for feed_url in self.FEEDS:
            sub = RSSCollector(
                source_name=self.source_name,
                feed_url=feed_url,
                enabled=True,
                credibility_score=self.credibility_score,
            )
            for art in sub.collect(since, until):
                if art.article_url not in seen_urls:
                    seen_urls.add(art.article_url)
                    articles.append(art)

        logger.info("Business Standard collector retrieved %d articles", len(articles))
        return articles
