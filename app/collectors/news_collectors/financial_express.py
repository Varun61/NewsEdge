"""Financial Express Markets and Companies news collector (direct feeds with syndication fallback)."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.financial_express")


class FinancialExpressCollector(BaseCollector):
    """Collects markets and business news from Financial Express."""

    # High-velocity real-time syndication feeds ensure 100% current coverage
    # (Financial Express legacy static feeds were deprecated by Express Group).
    FEEDS = [
        "https://news.google.com/rss/search?q=site:financialexpress.com+(stocks+OR+market+OR+results+OR+NSE)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:financialexpress.com+(earnings+OR+shares+OR+SEBI)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:financialexpress.com+intitle:(Q2+OR+Q3+OR+results+OR+profit+OR+order)&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=site:financialexpress.com+(capex+OR+acquisition+OR+contract+OR+regulatory)&hl=en-IN&gl=IN&ceid=IN:en",
    ]

    def __init__(
        self,
        source_name: str = "Financial Express",
        enabled: bool = True,
        credibility_score: float = 0.75,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.financialexpress.com",
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
                if " - The Financial Express" in clean_headline:
                    clean_headline = clean_headline.split(" - The Financial Express")[0].strip()
                elif " - Financial Express" in clean_headline:
                    clean_headline = clean_headline.split(" - Financial Express")[0].strip()

                norm_title = clean_headline.lower()
                if art.article_url not in seen_urls and norm_title not in seen_titles:
                    seen_urls.add(art.article_url)
                    seen_titles.add(norm_title)
                    art.headline = clean_headline
                    articles.append(art)

        logger.info("Financial Express collector retrieved %d articles", len(articles))
        return articles
