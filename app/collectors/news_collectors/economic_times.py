"""Economic Times Markets RSS collector."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.economic_times")


class ETMarketsCollector(BaseCollector):
    """Collects Indian stock market updates from Economic Times Markets RSS."""

    FEEDS = [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
        "https://economictimes.indiatimes.com/news/company/corporate-trends/rssfeeds/2143429.cms",
    ]

    def __init__(
        self,
        source_name: str = "Economic Times Markets",
        enabled: bool = True,
        credibility_score: float = 0.75,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://economictimes.indiatimes.com",
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

        logger.info("ET Markets collector retrieved %d articles", len(articles))
        return articles
