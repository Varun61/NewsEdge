"""USFDA drug-enforcement (recall) collector for Indian pharma.

A USFDA action against an Indian pharma's US operations is a major overnight
catalyst. openFDA exposes drug enforcement reports (recalls) via a public REST
API; we map the recalling firm to its NSE symbol and surface Class I/II recalls
(the material ones) as bearish catalysts. Warning letters / import alerts are
not in openFDA's structured API, so this covers recalls only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.fda")

_API = "https://api.fda.gov/drug/enforcement.json"

# Recalling-firm substring -> NSE symbol (US arms are named after the parent).
_FIRM_TO_SYMBOL = {
    "aurobindo": "AUROPHARMA",
    "sun pharma": "SUNPHARMA",
    "dr. reddy": "DRREDDY",
    "dr reddy": "DRREDDY",
    "cipla": "CIPLA",
    "lupin": "LUPIN",
    "zydus": "ZYDUSLIFE",
    "cadila": "ZYDUSLIFE",
    "glenmark": "GLENMARK",
    "torrent pharma": "TORNTPHARM",
    "alkem": "ALKEM",
    "biocon": "BIOCON",
    "divi": "DIVISLAB",
    "ipca": "IPCALAB",
    "laurus": "LAURUSLABS",
    "mankind": "MANKIND",
    "wockhardt": "WOCKPHARMA",
    "granules": "GRANULES",
    "natco": "NATCOPHARM",
    "ajanta": "AJANTPHARM",
    "gland pharma": "GLAND",
    "jubilant": "JUBLPHARMA",
    "strides": "STAR",
    "aarti": "AARTIDRUGS",
    "hetero": None,  # unlisted; recognised but skipped
}


def map_fda_firm_to_symbol(firm: str) -> Optional[str]:
    """Map an FDA recalling-firm name to an NSE symbol, or None if not Indian-listed."""
    f = (firm or "").lower()
    for key, sym in _FIRM_TO_SYMBOL.items():
        if key in f:
            return sym
    return None


class FDACollector(BaseCollector):
    """Collects USFDA drug recalls affecting NSE-listed Indian pharma."""

    def __init__(
        self,
        source_name: str = "USFDA Enforcement",
        enabled: bool = True,
        credibility_score: float = 1.0,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://api.fda.gov/drug/enforcement.json",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []
        logger.info("Collecting USFDA drug enforcement actions for Indian pharma...")

        # openFDA report_date is day-granular; widen a little to catch recent actions.
        start = (since.astimezone(timezone.utc) - timedelta(days=3)).strftime("%Y%m%d")
        end = until.astimezone(timezone.utc).strftime("%Y%m%d")
        params = {
            "search": f"report_date:[{start}+TO+{end}]",
            "limit": 100,
        }
        try:
            resp = requests.get(_API, params=params, timeout=self.timeout_seconds)
            if resp.status_code != 200:
                logger.warning("openFDA returned HTTP %d", resp.status_code)
                return []
            results = resp.json().get("results", [])
        except (requests.RequestException, ValueError) as exc:
            logger.warning("openFDA fetch failed: %s", exc)
            return []

        articles: List[CollectedArticle] = []
        for r in results:
            firm = (r.get("recalling_firm") or "").strip()
            symbol = map_fda_firm_to_symbol(firm)
            if not symbol:
                continue
            classification = (r.get("classification") or "").strip()  # Class I/II/III
            # Only Class I/II are materially market-moving.
            if classification not in ("Class I", "Class II"):
                continue

            reason = (r.get("reason_for_recall") or "").strip()
            product = (r.get("product_description") or "").strip()[:120]
            impact = 82.0 if classification == "Class I" else 70.0
            headline = f"{symbol} ({firm}): USFDA {classification} recall — {product}"

            catalyst = {
                "news_category": "REGULATORY_ACTION",
                "direction": "bearish",
                "impact_hint": impact,
                "confidence": 90.0,
                "is_material": True,
                "summary": f"{classification} recall: {reason}"[:200],
                "matched_rule": "usfda_recall",
                "order_value_cr": None, "profit_growth_pct": None,
                "revenue_growth_pct": None, "penalty_amount_cr": None,
                "tags": ["usfda", "recall"],
            }
            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url="https://www.accessdata.fda.gov/scripts/ires/index.cfm",
                    source_name=self.source_name,
                    published_at=datetime.now(timezone.utc),
                    raw_content=f"{headline}. Reason: {reason}",
                    extracted_text=f"{headline}. Reason: {reason}",
                    company_mentions=[symbol, firm],
                    credibility_score=self.credibility_score,
                    authoritative_symbol=symbol,
                    filing_catalyst=catalyst,
                )
            )

        if articles:
            logger.info("USFDA Enforcement: %d Class I/II recalls mapped to NSE pharma.", len(articles))
        else:
            logger.info("USFDA Enforcement: no material recalls for tracked Indian pharma in window.")
        return articles
