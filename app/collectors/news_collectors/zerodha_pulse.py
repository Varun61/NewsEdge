"""Zerodha Pulse aggregated financial news collector."""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.zerodha_pulse")


class ZerodhaPulseCollector(BaseCollector):
    """Collects financial news aggregated by Zerodha Pulse across major Indian publications."""

    FEED_URL = "https://pulse.zerodha.com/feed.xml"

    def __init__(
        self,
        source_name: str = "Zerodha Pulse",
        enabled: bool = True,
        credibility_score: float = 0.85,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://pulse.zerodha.com",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        if not self.enabled:
            return []

        sub = RSSCollector(
            source_name=self.source_name,
            feed_url=self.FEED_URL,
            enabled=True,
            credibility_score=self.credibility_score,
        )
        articles = sub.collect(since, until)
        logger.info("Zerodha Pulse collector retrieved %d articles", len(articles))
        return articles
