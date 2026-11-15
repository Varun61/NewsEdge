"""NSE Bulk and Block Deals Correlator.

Tracks smart money institutional accumulation vs promoter/PE stake liquidations:
- Marquee Institutional Buyers: GQG, Vanguard, Capital Group, BlackRock, GIC,
  SBI MF, HDFC MF, ICICI Pru MF, Ashish Kacholia, Mukul Agrawal, Vijay Kedia.
- Supply Overhang Liquidations: Promoters, PE funds (Blackstone, Warburg, SoftBank,
  Tiger Global) offloading shares via discounted block deals / OFS.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("newsedge.intelligence.bulk_deals")

MARQUEE_BUYERS = [
    "gqg partners", "gqg", "capital group", "vanguard", "blackrock", "fidelity",
    "norges bank", "gic", "government of singapore", "adia", "abu dhabi investment",
    "sbi mutual fund", "sbi mf", "hdfc mutual fund", "hdfc mf", "icici prudential mf",
    "nippon india mf", "kotak mutual fund", "mirae asset", "uti mutual fund",
    "ashish kacholia", "mukul agrawal", "rekha jhunjhunwala", "vijay kedia",
    "dolly khanna", "nemish shah", "madhusudan kela", "porinju veliyath",
    "morgan stanley asia", "societe generale", "goldman sachs india"
]

PROMOTER_PE_SELLERS = [
    "promoter sells", "promoter offloads", "promoters sell", "promoter stake sale",
    "promoter cuts stake", "promoters trim stake", "promoter group sells",
    "pe fund sells", "private equity exits", "blackstone sells", "warburg pincus",
    "softbank offloads", "softbank sells", "tiger global exits", "temasek trims",
    "tpg sells", "bain capital", "general atlantic", "stake sale at discount",
    "block deal at discount", "ofs at discount", "dilutes stake", "offloads stake"
]


@dataclass
class BlockDealEvaluation:
    is_institutional_buying: bool = False
    is_promoter_selling: bool = False
    score_modifier: float = 0.0
    detected_entities: List[str] = field(default_factory=list)
    advisory: Optional[str] = None


class BulkDealsAnalyzer:
    """Evaluates bulk and block deal disclosures for market conviction."""

    @classmethod
    def evaluate_deal(cls, headline: str, text: str = "") -> BlockDealEvaluation:
        """Scan announcement text for marquee institutional buying or promoter dumps."""
        combined = f"{headline} {text[:350]}".lower()

        detected_buyers = [b for b in MARQUEE_BUYERS if b in combined]
        has_promoter_selling = any(s in combined for s in PROMOTER_PE_SELLERS)

        # 1. Promoter or Private Equity stake dump (Severe Supply Overhang)
        if has_promoter_selling:
            return BlockDealEvaluation(
                is_institutional_buying=False,
                is_promoter_selling=True,
                score_modifier=-20.0,
                detected_entities=["Promoter/PE Seller"],
                advisory="🐋 Institutional Supply Overhang: Large block deal stake sale / promoter offload detected. High selling pressure.",
            )

        # 2. Marquee Institutional / Super-investor accumulation
        if detected_buyers and any(w in combined for w in ["buys", "bought", "picks up", "acquires", "accumulates", "invests", "stake buy"]):
            top_buyer = detected_buyers[0].title()
            return BlockDealEvaluation(
                is_institutional_buying=True,
                is_promoter_selling=False,
                score_modifier=+12.0,
                detected_entities=detected_buyers,
                advisory=f"🐋 Marquee Institutional Accumulation: {top_buyer} acquired stake via bulk/block deal.",
            )

        return BlockDealEvaluation()


_bulk_instance: Optional[BulkDealsAnalyzer] = None


def get_bulk_deals_analyzer() -> BulkDealsAnalyzer:
    global _bulk_instance
    if _bulk_instance is None:
        _bulk_instance = BulkDealsAnalyzer()
    return _bulk_instance
