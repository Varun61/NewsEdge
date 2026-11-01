"""BSE corporate announcements collector.

NOTE: BSE corporate disclosures require authorized access or permitted data subscription.
Do not bypass bot protections or terms of service.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.bse")


class BSEAnnouncementCollector(BaseCollector):
    """Adapter for Bombay Stock Exchange (BSE) Corporate Filings."""

    def __init__(
        self,
        source_name: str = "BSE Announcements",
        enabled: bool = False,  # Disabled by default until licensed credentials provided
        credibility_score: float = 1.0,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.bseindia.com/corporates/ann.html",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        if not self.enabled:
            logger.info("BSE Announcement Collector is disabled (requires official API key or feed license).")
            return []

        logger.warning(
            "BSE Official Collector activated. Verify that licensed access credentials are supplied."
        )
        return []
