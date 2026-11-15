"""Registry and factory for news and announcement collectors."""

from __future__ import annotations

import logging
from typing import Dict, List

from app.collectors.base_collector import BaseCollector
from app.collectors.news_collectors.business_standard import BusinessStandardCollector
from app.collectors.news_collectors.cnbc_tv18 import CNBCTV18Collector
from app.collectors.news_collectors.economic_times import ETMarketsCollector
from app.collectors.news_collectors.financial_express import FinancialExpressCollector
from app.collectors.news_collectors.google_news import GoogleNewsCollector
from app.collectors.news_collectors.hindu_businessline import HinduBusinessLineCollector
from app.collectors.news_collectors.investing_com import InvestingComCollector
from app.collectors.news_collectors.marketbyte import MarketByteCollector
from app.collectors.news_collectors.mint_news import MintCollector
from app.collectors.news_collectors.moneycontrol import MoneycontrolCollector
from app.collectors.news_collectors.moneycontrol_results import MoneycontrolResultsCollector
from app.collectors.news_collectors.screener_collector import ScreenerCollector
from app.collectors.news_collectors.thecore_earnings import TheCoreEarningsCollector
from app.collectors.news_collectors.tijori_finance import TijoriFinanceCollector
from app.collectors.news_collectors.zerodha_pulse import ZerodhaPulseCollector
from app.collectors.official_collectors.bse_announcements import BSEAnnouncementCollector
from app.collectors.official_collectors.nse_announcements import NSEAnnouncementCollector

logger = logging.getLogger("newsedge.collectors.registry")


class CollectorRegistry:
    """Manages active and available collectors without modifying core pipeline."""

    def __init__(self):
        self._collectors: Dict[str, BaseCollector] = {}

    def register(self, collector: BaseCollector) -> None:
        self._collectors[collector.source_name] = collector
        logger.debug("Registered collector '%s'", collector.source_name)

    def get_collector(self, name: str) -> BaseCollector | None:
        return self._collectors.get(name)

    def get_all_collectors(self) -> List[BaseCollector]:
        return list(self._collectors.values())

    def get_enabled_collectors(self) -> List[BaseCollector]:
        return [c for c in self._collectors.values() if c.enabled]


def build_default_registry() -> CollectorRegistry:
    """Instantiate and register default news and official collectors."""
    registry = CollectorRegistry()

    # Enabled public RSS and real-time financial publishers
    registry.register(GoogleNewsCollector(enabled=True))
    registry.register(ETMarketsCollector(enabled=True))
    registry.register(BusinessStandardCollector(enabled=True))
    registry.register(MintCollector(enabled=True))
    registry.register(HinduBusinessLineCollector(enabled=True))
    registry.register(MoneycontrolCollector(enabled=True))
    registry.register(FinancialExpressCollector(enabled=True))
    registry.register(CNBCTV18Collector(enabled=True))
    registry.register(ZerodhaPulseCollector(enabled=True))
    registry.register(InvestingComCollector(enabled=True))

    # High-precision earnings, concall, and financial results sources
    registry.register(TijoriFinanceCollector(enabled=True))
    registry.register(MarketByteCollector(enabled=True))
    registry.register(MoneycontrolResultsCollector(enabled=True))
    registry.register(TheCoreEarningsCollector(enabled=True))
    registry.register(ScreenerCollector(enabled=True))

    # Official exchange announcements
    registry.register(NSEAnnouncementCollector(enabled=True))
    registry.register(BSEAnnouncementCollector(enabled=False))

    return registry
