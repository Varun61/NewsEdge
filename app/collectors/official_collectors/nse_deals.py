"""NSE bulk & block deals collector (authoritative, post-market catalyst).

Bulk and block deals are disclosed by NSE after market close and are a direct
next-day catalyst: marquee-fund accumulation is bullish, promoter/PE offloads
create supply overhang. We emit only *notable* deals (known smart-money buyer,
promoter/PE seller, or large value) so routine prop-desk churn doesn't flood the
watchlist. Each deal carries its authoritative NSE symbol, and a synthesized
headline that the existing BulkDealsAnalyzer recognises.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

import pytz

from app.collectors.base_collector import BaseCollector, CollectedArticle
from app.collectors.official_collectors.nse_session import fetch_nse_json
from app.intelligence.bulk_deals_analyzer import MARQUEE_BUYERS
from app.processors.filing_catalyst import BEARISH, BULLISH, NEUTRAL

logger = logging.getLogger("newsedge.collectors.nse_deals")

_IST = pytz.timezone("Asia/Kolkata")
_WARMUP = ("/report-detail/display-bulk-and-block-deals",)

# Candidate endpoints (first JSON wins). The `historicalOR/bulk-block-short-deals`
# path is the one verified live (returns BD_* rows); the older `historical/*`
# paths now 503, kept only as a fallback. NSE redirects .com->.in; requests
# follows that automatically.
_BULK_URLS = (
    "https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?optionType=bulk_deals&from={frm}&to={to}",
    "https://www.nseindia.com/api/historical/bulk-deals?from={frm}&to={to}",
)
_BLOCK_URLS = (
    "https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?optionType=block_deals&from={frm}&to={to}",
    "https://www.nseindia.com/api/historical/block-deals?from={frm}&to={to}",
)

# PE / promoter-style sellers that signal supply overhang on the SELL side.
_PE_PROMOTER_SELLERS = (
    "promoter", "blackstone", "warburg", "softbank", "tiger global", "temasek",
    "tpg", "bain capital", "general atlantic", "carlyle", "kkr", "westbridge",
    "peak xv", "sequoia", "elevation", "accel",
)

_NOTABLE_VALUE_CR = 25.0


def classify_deal(client: str, side: str, value_cr: float):
    """Classify a single deal. Returns (direction, impact, is_material, label)."""
    c = (client or "").lower()
    s = (side or "").upper()
    is_buy = s.startswith("B")
    is_sell = s.startswith("S")

    is_marquee = any(b in c for b in MARQUEE_BUYERS)
    is_pe_promoter = any(p in c for p in _PE_PROMOTER_SELLERS)

    if is_buy and is_marquee:
        return BULLISH, 66.0, True, "marquee_accumulation"
    if is_sell and is_pe_promoter:
        return BEARISH, 68.0, True, "promoter_pe_offload"
    if value_cr >= _NOTABLE_VALUE_CR:
        # Large deal, unknown counterparty — context only, not an actionable call.
        return NEUTRAL, 50.0, False, "large_deal"
    return NEUTRAL, 40.0, False, "routine"


class NSEDealsCollector(BaseCollector):
    """Collector for NSE bulk and block deals."""

    def __init__(
        self,
        source_name: str = "NSE Bulk/Block Deals",
        enabled: bool = True,
        credibility_score: float = 1.0,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url="https://www.nseindia.com/report-detail/display-bulk-and-block-deals",
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.timeout_seconds = timeout_seconds

    def _fetch_deals(self, url_templates, frm, to):
        for tmpl in url_templates:
            data = fetch_nse_json(tmpl.format(frm=frm, to=to), warmup_paths=_WARMUP, timeout=self.timeout_seconds)
            rows = data.get("data") if isinstance(data, dict) else (data if isinstance(data, list) else None)
            if rows:
                return rows
        return []

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

    def _row_to_article(self, item: dict, deal_kind: str) -> Optional[CollectedArticle]:
        symbol = self._field(item, "BD_SYMBOL", "symbol", "Symbol").upper()
        if not symbol:
            return None
        name = self._field(item, "BD_SCRIP_NAME", "scripName", "companyName") or symbol
        client = self._field(item, "BD_CLIENT_NAME", "clientName", "client")
        side = self._field(item, "BD_BUY_SELL", "buySell", "BuySell")
        qty = self._num(item, "BD_QTY_TRD", "quantityTraded", "qty")
        price = self._num(item, "BD_TP_WATP", "tradePrice", "wap", "price")
        value_cr = round(qty * price / 1e7, 2) if qty and price else 0.0

        direction, impact, is_material, label = classify_deal(client, side, value_cr)
        if label == "routine":
            return None  # skip prop-desk churn entirely

        side_word = "buys" if side.upper().startswith("B") else "sells"
        val_str = f", ₹{value_cr:,.0f} Cr" if value_cr else ""
        headline = f"{symbol} ({name}): {client} {side_word} {qty:,.0f} shares ({deal_kind} deal{val_str})"

        catalyst = {
            "news_category": "SHAREHOLDING_CHANGE",
            "direction": direction,
            "impact_hint": impact,
            "confidence": 88.0,
            "is_material": is_material,
            "summary": headline,
            "matched_rule": f"{deal_kind}_deal_{label}",
            "order_value_cr": None, "profit_growth_pct": None,
            "revenue_growth_pct": None, "penalty_amount_cr": None, "tags": ["deal", label],
        }

        pub_dt = datetime.now(timezone.utc)
        return CollectedArticle(
            headline=headline,
            article_url=f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
            source_name=self.source_name,
            published_at=pub_dt,
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
        logger.info("Collecting NSE bulk & block deals...")
        frm = since.astimezone(_IST).strftime("%d-%m-%Y")
        to = until.astimezone(_IST).strftime("%d-%m-%Y")

        articles: List[CollectedArticle] = []
        for kind, urls in (("block", _BLOCK_URLS), ("bulk", _BULK_URLS)):
            for item in self._fetch_deals(urls, frm, to):
                try:
                    art = self._row_to_article(item, kind)
                    if art:
                        articles.append(art)
                except Exception as exc:
                    logger.debug("Skipping malformed %s deal row: %s", kind, exc)

        if not articles:
            logger.warning("NSE Bulk/Block Deals returned no notable deals (empty or fetch failed).")
        else:
            logger.info("NSE Bulk/Block Deals: %d notable deals surfaced.", len(articles))
        return articles
