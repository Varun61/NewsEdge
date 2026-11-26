"""BSE corporate announcements collector (authoritative filings fallback).

BSE's public announcements API is generally more accessible than NSE's and
covers the same dual-listed companies, so it is a useful redundant source for
the filings-first catalyst engine. BSE returns a company name + numeric BSE
scrip code (no NSE symbol/ISIN), so we resolve the NSE symbol via the shared
resolver and only tag the article as an authoritative filing when that resolves
to a valid, confidently-matched NSE equity.

Only public, unauthenticated endpoints are used; no bot-protection bypass.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

import pytz
import requests

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.processors.filing_catalyst import classify_filing
from app.processors.nse_master import get_nse_resolver

logger = logging.getLogger("newsedge.collectors.bse")

_IST = pytz.timezone("Asia/Kolkata")
_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
_ATTACH_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bseindia.com/corporates/ann.html",
    "Origin": "https://www.bseindia.com",
}
_MAX_PAGES = 10


class BSEAnnouncementCollector(BaseCollector):
    """Collector for Bombay Stock Exchange (BSE) corporate filings."""

    def __init__(
        self,
        source_name: str = "BSE Announcements",
        enabled: bool = True,
        credibility_score: float = 1.0,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.bseindia.com/corporates/ann.html",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds
        self._resolver = get_nse_resolver()

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update(_HEADERS)
        try:
            s.get("https://www.bseindia.com/", timeout=self.timeout_seconds)
            time.sleep(0.3)
        except requests.RequestException:
            pass
        return s

    @staticmethod
    def _parse_dt(item: dict) -> Optional[datetime]:
        raw = (item.get("NEWS_DT") or item.get("DT_TM") or item.get("News_submission_dt") or "").strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return _IST.localize(datetime.strptime(raw[:26], fmt)).astimezone(timezone.utc)
            except (ValueError, AttributeError):
                continue
        return None

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []

        logger.info("Collecting official filings from BSE Corporate Announcements API...")
        session = self._session()

        frm = since.astimezone(_IST).strftime("%Y%m%d")
        to = until.astimezone(_IST).strftime("%Y%m%d")

        rows: list[dict] = []
        for pageno in range(1, _MAX_PAGES + 1):
            params = {
                "pageno": pageno,
                "strCat": "-1",
                "strPrevDate": frm,
                "strToDate": to,
                "strScrip": "",
                "strSearch": "P",
                "strType": "C",
            }
            try:
                resp = session.get(_API, params=params, timeout=self.timeout_seconds)
                if resp.status_code != 200:
                    logger.debug("BSE page %d -> HTTP %d", pageno, resp.status_code)
                    break
                data = resp.json()
            except (requests.RequestException, ValueError) as exc:
                logger.warning("BSE announcements fetch failed on page %d: %s", pageno, exc)
                break

            table = data.get("Table") or []
            if not table:
                break
            rows.extend(table)

            try:
                total = int((data.get("Table1") or [{}])[0].get("ROWCNT", 0))
            except (ValueError, TypeError, IndexError):
                total = len(rows)
            if len(rows) >= total:
                break
            time.sleep(0.3)

        if not rows:
            logger.warning("BSE Announcements returned no usable data (empty or fetch failed).")
            return []

        articles: List[CollectedArticle] = []
        for item in rows:
            name = (item.get("SLONGNAME") or "").strip()
            if not name:
                continue
            subject = (item.get("NEWSSUB") or item.get("CATEGORYNAME") or "").strip()
            category = (item.get("CATEGORYNAME") or "").strip()
            detail = (item.get("HEADLINE") or item.get("NEWSSUB") or "").strip()

            pub_dt = self._parse_dt(item) or datetime.now(timezone.utc)
            if pub_dt < since or pub_dt > until:
                continue

            # Resolve the NSE symbol by company name (BSE gives no NSE symbol/ISIN).
            resolved = self._resolver.resolve_from_text(name)
            sym = None
            if resolved and self._resolver.is_valid_nse_symbol(resolved.get("symbol", "")):
                sym = resolved["symbol"]

            catalyst = classify_filing(subject=category or subject, description=subject, attachment_text=detail)

            attach = (item.get("ATTACHMENTNAME") or "").strip()
            url = f"{_ATTACH_BASE}{attach}" if attach else self.source_url
            label = sym or name
            headline_core = detail.split(".")[0].strip() if detail and len(detail.split(".")[0]) > 20 else subject
            headline = f"{label} ({name}): {headline_core}".strip()

            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url=url,
                    source_name=self.source_name,
                    published_at=pub_dt,
                    raw_content=detail or subject,
                    extracted_text=detail or subject,
                    company_mentions=[x for x in (sym, name) if x],
                    credibility_score=self.credibility_score,
                    # Only authoritative when the NSE symbol resolved confidently.
                    authoritative_symbol=sym,
                    filing_catalyst=asdict(catalyst) if sym else None,
                )
            )

        materials = sum(1 for a in articles if (a.filing_catalyst or {}).get("is_material"))
        logger.info(
            "BSE Announcements: %d filings in window (%d NSE-mapped material catalysts).",
            len(articles),
            materials,
        )
        return articles
