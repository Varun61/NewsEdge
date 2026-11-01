"""NSE corporate announcements collector.

NOTE: NSE web pages and internal APIs actively enforce bot protection, rate limits,
and session validation. Direct scraping without licensed access is strictly prohibited
by the PRD and exchange terms.

This adapter provides the standardized interface. When official API access or licensed
feeds are configured, implement the API authentication and retrieval here.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.nse")


class NSEAnnouncementCollector(BaseCollector):
    """Adapter for National Stock Exchange (NSE) Corporate Disclosures."""

    def __init__(
        self,
        source_name: str = "NSE Announcements",
        enabled: bool = False,  # Disabled by default until licensed feed/API key configured
        credibility_score: float = 1.0,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        if not self.enabled:
            logger.info("NSE Announcement Collector is disabled (requires official API key or feed license).")
            return []

        logger.warning(
            "NSE Official Collector activated. Verify that licensed access credentials are supplied."
        )
        # Placeholder for licensed feed or authorized data integration
        return []
