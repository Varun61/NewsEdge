"""CNBC-TV18 Markets and Corporate news collector."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.cnbc_tv18")


class CNBCTV18Collector(BaseCollector):
    """Collects markets and business news from CNBC-TV18."""

    FEEDS = [
        "https://news.google.com/rss/search?q=site:cnbctv18.com+(stocks+OR+market+OR+results+OR+NSE)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:cnbctv18.com+(earnings+OR+shares+OR+deal+OR+SEBI)&hl=en-IN&gl=IN&ceid=IN:en",
    ]

    def __init__(
        self,
        source_name: str = "CNBC-TV18",
        enabled: bool = True,
        credibility_score: float = 0.80,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.cnbctv18.com",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        if not self.enabled:
            return []

        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
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
                if " - CNBCTV18" in clean_headline:
                    clean_headline = clean_headline.split(" - CNBCTV18")[0].strip()
                elif " - CNBC TV18" in clean_headline:
                    clean_headline = clean_headline.split(" - CNBC TV18")[0].strip()

                norm_title = clean_headline.lower()
                if art.article_url not in seen_urls and norm_title not in seen_titles:
                    seen_urls.add(art.article_url)
                    seen_titles.add(norm_title)
                    art.headline = clean_headline
                    articles.append(art)

        logger.info("CNBC-TV18 collector retrieved %d articles", len(articles))
        return articles
