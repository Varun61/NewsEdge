"""NSE insider-trading (PIT) & promoter-pledge collector.

NSE publishes SEBI Prohibition-of-Insider-Trading (PIT) disclosures after close:
promoter/designated-person acquisitions, disposals, and pledge/encumbrance
events. These are authoritative, stock-specific next-day catalysts — promoter
buying is a confidence signal, promoter selling and fresh pledges are risks.
Each row carries its NSE symbol and a synthesized headline the downstream
ShareholdingAnalyzer recognises.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

import pytz

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.official_collectors.nse_session import fetch_nse_json
from app.processors.filing_catalyst import BEARISH, BULLISH, NEUTRAL

logger = logging.getLogger("newsedge.collectors.nse_insider")

_IST = pytz.timezone("Asia/Kolkata")
_WARMUP = ("/companies-listing/corporate-filings-insider-trading",)
_PIT_URL = "https://www.nseindia.com/api/corporates-pit?index=equities&from_date={frm}&to_date={to}"

_NOTABLE_VALUE_CR = 10.0


def classify_insider(person_category: str, txn_type: str, value_cr: float):
    """Classify a PIT disclosure. Returns (direction, category, impact, is_material, label)."""
    pc = (person_category or "").lower()
    tt = (txn_type or "").lower()
    is_promoter = "promoter" in pc

    if any(k in tt for k in ("pledge", "encumber", "invoke")):
        return BEARISH, "PROMOTER_ACTIVITY", 70.0, is_promoter, "pledge_created"
    if any(k in tt for k in ("revoke", "release")):
        return BULLISH, "PROMOTER_ACTIVITY", 56.0, False, "pledge_released"
    if any(k in tt for k in ("sale", "sell", "disposal", "dispose")):
        material = is_promoter or value_cr >= _NOTABLE_VALUE_CR
        return BEARISH, "PROMOTER_ACTIVITY", 64.0, material, "insider_sale"
    if any(k in tt for k in ("purchase", "buy", "acqui")):
        material = is_promoter or value_cr >= _NOTABLE_VALUE_CR
        return BULLISH, "PROMOTER_ACTIVITY", 62.0, material, "insider_buy"
    return NEUTRAL, "SHAREHOLDING_CHANGE", 45.0, False, "other"


class NSEInsiderCollector(BaseCollector):
    """Collector for NSE insider-trading (PIT) and promoter-pledge disclosures."""

    def __init__(
        self,
        source_name: str = "NSE Insider Trading",
        enabled: bool = True,
        credibility_score: float = 1.0,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.nseindia.com/companies-listing/corporate-filings-insider-trading",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _field(item: dict, *keys: str) -> str:
        for k in keys:
            v = item.get(k)
            if v not in (None, ""):
                return str(v).strip()
        return ""

    @staticmethod
    def _num(item: dict, *keys: str) -> float:
        for k in keys:
            v = item.get(k)
            if v not in (None, ""):
                try:
                    return float(str(v).replace(",", ""))
                except ValueError:
                    continue
        return 0.0

    def _row_to_article(self, item: dict) -> Optional[CollectedArticle]:
        symbol = self._field(item, "symbol", "Symbol").upper()
        if not symbol:
            return None
        name = self._field(item, "company", "companyName") or symbol
        acq = self._field(item, "acqName", "name", "personName") or "Insider"
        pcat = self._field(item, "personCategory", "category")
        txn = self._field(item, "tdpTransactionType", "transactionType", "acqMode", "secType")
        qty = self._num(item, "secAcq", "securitiesVal", "noOfSecurities", "secVal")
        value_cr = round(self._num(item, "secVal", "totalValue") / 1e7, 2)

        direction, category, impact, is_material, label = classify_insider(pcat, txn, value_cr)

        pcat_str = pcat or "Insider"
        val_str = f", ₹{value_cr:,.1f} Cr" if value_cr else ""
        if label == "pledge_created":
            action = "promoter pledge created" if "promoter" in pcat.lower() else "pledge created"
        elif label == "pledge_released":
            action = "pledge released"
        else:
            action = txn or "transaction"
        headline = f"{symbol} ({name}): {pcat_str} {acq} — {action}{val_str} [insider disclosure]"

        catalyst = {
            "news_category": category,
            "direction": direction,
            "impact_hint": impact,
            "confidence": 88.0,
            "is_material": is_material,
            "summary": headline,
            "matched_rule": f"insider_{label}",
            "order_value_cr": None, "profit_growth_pct": None,
            "revenue_growth_pct": None, "penalty_amount_cr": None, "tags": ["insider", label],
        }

        return CollectedArticle(
            headline=headline,
            article_url=f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
            source_name=self.source_name,
            published_at=datetime.now(timezone.utc),
            raw_content=headline,
            extracted_text=headline,
            company_mentions=[symbol, name],
            credibility_score=self.credibility_score,
            authoritative_symbol=symbol,
            filing_catalyst=catalyst,
        )

    def collect(self, since: datetime, until: datetime) -> List[CollectedArticle]:
        if not self.enabled:
            return []
        logger.info("Collecting NSE insider-trading / pledge disclosures...")
        frm = since.astimezone(_IST).strftime("%d-%m-%Y")
        to = until.astimezone(_IST).strftime("%d-%m-%Y")
        data = fetch_nse_json(_PIT_URL.format(frm=frm, to=to), warmup_paths=_WARMUP, timeout=self.timeout_seconds)
        rows = data.get("data") if isinstance(data, dict) else (data if isinstance(data, list) else None)
        if not rows:
            logger.warning("NSE Insider Trading returned no usable data (empty or fetch failed).")
            return []

        articles: List[CollectedArticle] = []
        for item in rows:
            try:
                art = self._row_to_article(item)
                if art and (art.filing_catalyst or {}).get("is_material"):
                    articles.append(art)
            except Exception as exc:
                logger.debug("Skipping malformed insider row: %s", exc)

        logger.info("NSE Insider Trading: %d material promoter/pledge disclosures.", len(articles))
        return articles
