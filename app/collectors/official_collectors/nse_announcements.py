"""NSE corporate announcements collector (filings-first, authoritative).

Fetches official exchange filings directly from the National Stock Exchange of
India (NSE) corporate-announcements API. This is the authoritative, fastest
catalyst source for a post-market / pre-open watchlist: results, order wins,
SEBI orders, resignations and board outcomes are filed here before the news
wires rewrite them.

Improvements over the naive version:
- Cookie-primed session (NSE rejects un-primed API calls with 401/403).
- Explicit from/to date window so only filings inside the run window are kept.
- Captures the authoritative symbol + ISIN (no downstream re-guessing).
- Parses the exchange's own filing category into a structured catalyst with
  extracted numbers via :mod:`app.processors.filing_catalyst`.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

import pytz

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.official_collectors.nse_session import fetch_nse_json
from app.processors.filing_catalyst import classify_filing

logger = logging.getLogger("newsedge.collectors.nse")

_IST = pytz.timezone("Asia/Kolkata")
_WARMUP = ("/companies-listing/corporate-filings-announcements",)


class NSEAnnouncementCollector(BaseCollector):
    """Collector for NSE official corporate disclosures (filings-first)."""

    def __init__(
        self,
        source_name: str = "NSE Announcements",
        enabled: bool = True,
        credibility_score: float = 1.0,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.nseindia.com/companies-listing/corporate-filings-announcements",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def _api_url(self, since: datetime, until: datetime) -> str:
        """Build the equities announcements API URL for the given UTC window.

        NSE expects dates as DD-MM-YYYY in IST.
        """
        start_ist = since.astimezone(_IST)
        end_ist = until.astimezone(_IST)
        frm = start_ist.strftime("%d-%m-%Y")
        to = end_ist.strftime("%d-%m-%Y")
        return (
            "https://www.nseindia.com/api/corporate-announcements"
            f"?index=equities&from_date={frm}&to_date={to}"
        )

    @staticmethod
    def _parse_pub_dt(item: dict) -> datetime:
        """Parse the filing timestamp (IST) into UTC, tolerant of field names."""
        raw = item.get("sort_date") or item.get("an_dt") or item.get("exchdisstime") or ""
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M"):
            try:
                dt_naive = datetime.strptime(raw.strip(), fmt)
                return _IST.localize(dt_naive).astimezone(timezone.utc)
            except (ValueError, AttributeError):
                continue
        return datetime.now(timezone.utc)

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting official filings from NSE Corporate Announcements API...")
        data = fetch_nse_json(
            self._api_url(since, until),
            warmup_paths=_WARMUP,
            timeout=self.timeout_seconds,
        )
        if not isinstance(data, list):
            logger.warning("NSE Announcements returned no usable data (primed fetch failed or empty).")
            return []

        articles: List[CollectedArticle] = []
        for item in data:
            symbol = (item.get("symbol") or "").strip().upper()
            if not symbol:
                continue

            comp_name = (item.get("sm_name") or item.get("companyName") or symbol).strip()
            # NSE announcement payload uses `sm_isin` (verified live).
            isin = (item.get("sm_isin") or item.get("isin") or "").strip() or None
            # NSE field names vary: `desc` is the category/subject, `attchmntText`
            # (and sometimes `smIndustry`/`bdp_descriptor`) carry detail.
            subject = (item.get("desc") or item.get("bdp_descriptor") or "").strip()
            detail = (item.get("attchmntText") or item.get("voiceSummary") or "").strip()
            att_file = (item.get("attchmntFile") or "").strip()

            pub_dt = self._parse_pub_dt(item)

            # Window guard (the API range param is day-granular; enforce exact bounds).
            if pub_dt < since or pub_dt > until:
                continue

            catalyst = classify_filing(subject=subject, description=subject, attachment_text=detail)

            # Build a clean, information-dense headline.
            headline_core = detail.split(".")[0].strip() if detail and len(detail.split(".")[0]) > 20 else subject
            headline = f"{symbol} ({comp_name}): {headline_core}".strip()

            content = detail or subject
            url = att_file or f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url=url,
                    source_name=self.source_name,
                    published_at=pub_dt,
                    raw_content=content,
                    extracted_text=content,
                    company_mentions=[symbol, comp_name],
                    credibility_score=self.credibility_score,
                    authoritative_symbol=symbol,
                    authoritative_isin=isin,
                    filing_catalyst=asdict(catalyst),
                )
            )

        materials = sum(1 for a in articles if (a.filing_catalyst or {}).get("is_material"))
        logger.info(
            "NSE Announcements: %d filings in window (%d material catalysts).",
            len(articles),
            materials,
        )
        return articles
