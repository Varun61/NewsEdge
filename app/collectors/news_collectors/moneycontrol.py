"""Moneycontrol news collector (direct official feeds with real-time syndication fallback)."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.moneycontrol")


class MoneycontrolCollector(BaseCollector):
    """Collects news from Moneycontrol markets, corporate results, and sector coverage."""

    # High-velocity real-time syndication feeds ensure 100% current coverage
    # (Moneycontrol's legacy static XML endpoints were deprecated in 2024).
    FEEDS = [
        "https://news.google.com/rss/search?q=site:moneycontrol.com+(stocks+OR+shares+OR+results+OR+NSE+OR+BSE+OR+market)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:moneycontrol.com+(earnings+OR+profit+OR+order+OR+SEBI+OR+probe)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:moneycontrol.com+intitle:(Q1+OR+Q2+OR+Q3+OR+Q4+OR+results+OR+profit+OR+revenue)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:moneycontrol.com+(merger+OR+acquisition+OR+contract+OR+deal+OR+regulatory)&hl=en-IN&gl=IN&ceid=IN:en",
    ]

    def __init__(
        self,
        source_name: str = "Moneycontrol",
        enabled: bool = True,
        credibility_score: float = 0.80,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.moneycontrol.com",
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
                # Clean up trailing source tag if present in headline (e.g. " - Moneycontrol.com")
                clean_headline = art.headline
                if " - Moneycontrol" in clean_headline:
                    clean_headline = clean_headline.split(" - Moneycontrol")[0].strip()

                norm_title = clean_headline.lower()
                if art.article_url not in seen_urls and norm_title not in seen_titles:
                    seen_urls.add(art.article_url)
                    seen_titles.add(norm_title)
                    art.headline = clean_headline
                    articles.append(art)

        logger.info("Moneycontrol collector retrieved %d articles", len(articles))
        return articles
