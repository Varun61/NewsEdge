"""Investing.com India stock market news collector."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.investing_com")


class InvestingComCollector(BaseCollector):
    """Collects stock market news and analysis from Investing.com India."""

    FEEDS = [
        "https://news.google.com/rss/search?q=site:in.investing.com+(stocks+OR+shares+OR+results+OR+NSE)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://in.investing.com/rss/news_25.rss",
    ]

    def __init__(
        self,
        source_name: str = "Investing.com India",
        enabled: bool = True,
        credibility_score: float = 0.80,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://in.investing.com",
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
                clean_headline = art.headline
                if " - Investing.com" in clean_headline:
                    clean_headline = clean_headline.split(" - Investing.com")[0].strip()

                if art.article_url not in seen_urls:
                    seen_urls.add(art.article_url)
                    art.headline = clean_headline
                    articles.append(art)

        logger.info("Investing.com collector retrieved %d articles", len(articles))
        return articles
