"""Press Information Bureau (PIB) policy & sector-catalyst collector.

PIB is the Government of India's official press-release feed — the authoritative
source for the defence / railways / capex / duty / PLI-type policy catalysts the
thematic engine maps onto sector-beneficiary stocks. A keyword pre-filter keeps
only market-relevant releases (PIB also publishes a lot of non-market content).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.rss_collector import RSSCollector

logger = logging.getLogger("newsedge.collectors.pib")

# Official PIB RSS (all releases). Verified format: RssMain.aspx with ModId/Lang/Regid.
_FEEDS = (
    "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=3",
)

# Only keep releases that plausibly move a sector/stock.
_RELEVANCE = (
    "crore", "capex", "capital expenditure", "procurement", "order", "contract",
    "tender", "duty", "tariff", "anti-dumping", "safeguard", "pli", "production linked",
    "scheme", "subsidy", "spectrum", "auction", "defence", "defense", "railway",
    "highway", "road", "port", "power", "solar", "renewable", "ethanol", "sugar",
    "semiconductor", "electronics", "pharma", "fertiliser", "fertilizer", "steel",
    "cement", "telecom", "shipping", "aviation", "policy", "approves", "cabinet",
    "mou", "investment", "infrastructure", "gst", "import", "export", "msp",
)


class PIBCollector(BaseCollector):
    """Collects market-relevant Government of India policy releases from PIB."""

    def __init__(
        self,
        source_name: str = "PIB (Govt of India)",
        enabled: bool = True,
        credibility_score: float = 0.95,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.pib.gov.in/",
            enabled=enabled,
            credibility_score=credibility_score,
        )

    @staticmethod
    def _is_relevant(text: str) -> bool:
        t = (text or "").lower()
        return any(k in t for k in _RELEVANCE)

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []
        logger.info("Collecting Government policy releases from PIB...")
        seen: set[str] = set()
        out: List[CollectedArticle] = []
        for feed_url in _FEEDS:
            sub = RSSCollector(
                source_name=self.source_name,
                feed_url=feed_url,
                enabled=True,
                credibility_score=self.credibility_score,
            )
            try:
                for art in sub.collect(since, until):
                    if art.article_url in seen:
                        continue
                    if not self._is_relevant(f"{art.headline} {art.extracted_text or ''}"):
                        continue
                    seen.add(art.article_url)
                    out.append(art)
            except Exception as exc:
                logger.debug("PIB feed error: %s", exc)
        logger.info("PIB collector retrieved %d market-relevant policy releases.", len(out))
        return out
