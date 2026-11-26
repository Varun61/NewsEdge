"""Exchange-filing catalyst parser.

Unlike news headlines, exchange filings (NSE/BSE) arrive pre-categorised by the
exchange itself (e.g. "Financial Results", "Awarding of Order/Receipt of Order",
"Resignation", "Acquisition", "Disclosure under SEBI Regulation 30"). That
category is authoritative and far higher-signal than guessing a catalyst from a
free-text news headline.

This module maps a filing's exchange category + subject + attachment text into a
structured :class:`FilingCatalyst`: a normalised NewsCategory, an expected
intraday direction, a base impact hint, and any hard numbers we can extract
(order value in ₹ crore, profit/revenue YoY %, penalty amount, dividend, etc.).

It is intentionally pure (no network, no DB) so it can be unit-tested offline and
reused by both the NSE and BSE collectors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Direction constants ────────────────────────────────────────────────────
BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


@dataclass
class FilingCatalyst:
    """Structured interpretation of a single exchange filing."""

    news_category: str = "OTHER"
    direction: str = NEUTRAL
    # Base intraday-impact hint (0-100) derived purely from the filing type.
    # Numeric evidence (order size, profit %, penalty) escalates it.
    impact_hint: float = 40.0
    # Exchange filings are authoritative on *identity and occurrence*, so
    # classification confidence starts high.
    confidence: float = 85.0
    # Whether this filing type is worth surfacing at all (vs. pure noise such as
    # trading-window closures, newspaper ads, duplicate-share notices).
    is_material: bool = True
    summary: str = ""
    # Extracted hard numbers (None when not present in the text).
    order_value_cr: Optional[float] = None
    profit_growth_pct: Optional[float] = None
    revenue_growth_pct: Optional[float] = None
    penalty_amount_cr: Optional[float] = None
    matched_rule: str = ""
    tags: list[str] = field(default_factory=list)


# ── Subjects that are pure noise — never worth a watchlist slot ─────────────
_NOISE_SUBJECTS = (
    "trading window",
    "newspaper publication",
    "newspaper advertisement",
    "loss of share certificate",
    "duplicate share",
    "sub-division of shares not",  # rare, keep broad matches below
    "compliance certificate",
    "reg. 74(5)",
    "regulation 74",
    "certificate under",
    "investor complaint",
    "reconciliation of share capital",
    "closure of trading window",
    "record date for",  # dividend record-date admin follow-ups (the declaration is caught separately)
)


def _num(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _extract_order_value_cr(text: str) -> Optional[float]:
    """Pull an order/contract value and normalise to ₹ crore."""
    t = text.lower()

    # ₹ 1,234.5 crore  /  rs 1234 cr  /  inr 500 crore
    m = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(crore|cr)\b", t)
    if m:
        return _num(m.group(1))

    # ₹ 1,234 lakh  ->  crore
    m = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*lakh", t)
    if m:
        v = _num(m.group(1))
        return round(v / 100.0, 2) if v is not None else None

    # USD / $ 120 million|billion  ->  approx crore (1 USD ~ 83 INR)
    m = re.search(r"(?:usd|us\$|\$)\s*([\d,]+(?:\.\d+)?)\s*(million|mn|billion|bn)\b", t)
    if m:
        v = _num(m.group(1))
        if v is None:
            return None
        usd = v * (1_000 if m.group(2) in ("billion", "bn") else 1)  # in millions
        return round(usd * 83 / 10.0, 2)  # million USD -> ₹ crore

    # bare "value of 1,234 crore"
    m = re.search(r"\b([\d,]+(?:\.\d+)?)\s*(crore|cr)\b", t)
    if m:
        return _num(m.group(1))
    return None


def _extract_yoy(text: str, metric_words: tuple[str, ...]) -> Optional[float]:
    """Signed YoY percentage for a given metric (profit/revenue)."""
    t = text.lower()
    metric = "|".join(metric_words)
    up = re.search(rf"\b(?:{metric})\b.*?\b(?:rises?|jumps?|surges?|grew|grows?|up|climbs?|doubles?)\b\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", t)
    if up:
        return _num(up.group(1))
    down = re.search(rf"\b(?:{metric})\b.*?\b(?:falls?|drops?|declines?|slips?|down|dips?|plunges?|tumbles?)\b\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", t)
    if down:
        v = _num(down.group(1))
        return -v if v is not None else None
    return None


def _extract_penalty_cr(text: str) -> Optional[float]:
    t = text.lower()
    m = re.search(r"(?:penalty|fine)\s+of\s+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh)?", t)
    if m:
        v = _num(m.group(1))
        if v is None:
            return None
        if m.group(2) == "lakh":
            return round(v / 100.0, 2)
        return v
    return None


def classify_filing(
    subject: str,
    description: str = "",
    attachment_text: str = "",
) -> FilingCatalyst:
    """Interpret an exchange filing into a structured catalyst.

    ``subject`` is the exchange's own category (most authoritative). ``description``
    and ``attachment_text`` carry the free-text detail used for number extraction.
    """
    subj = (subject or "").strip().lower()
    full = f"{subject} {description} {attachment_text}".strip()
    full_l = full.lower()

    cat = FilingCatalyst(summary=(description or subject or "").strip()[:200])

    # 0. Noise gate ----------------------------------------------------------
    if any(n in subj for n in _NOISE_SUBJECTS) or any(n in full_l for n in _NOISE_SUBJECTS):
        cat.news_category = "OTHER"
        cat.direction = NEUTRAL
        cat.impact_hint = 10.0
        cat.is_material = False
        cat.matched_rule = "noise_subject"
        cat.tags.append("noise")
        return cat

    order_cr = _extract_order_value_cr(full)
    profit_yoy = _extract_yoy(full, ("net profit", "profit", "pat", "net"))
    revenue_yoy = _extract_yoy(full, ("revenue", "sales", "total income", "turnover"))
    penalty_cr = _extract_penalty_cr(full)

    cat.order_value_cr = order_cr
    cat.profit_growth_pct = profit_yoy
    cat.revenue_growth_pct = revenue_yoy
    cat.penalty_amount_cr = penalty_cr

    # 1. Regulatory / governance shocks (bearish, high conviction) -----------
    if any(k in full_l for k in ("sebi order", "adjudication", "show cause", "penalty", "debarred", "ban order")) or penalty_cr:
        cat.news_category = "REGULATORY_ACTION"
        cat.direction = BEARISH
        cat.impact_hint = 82.0 + (6.0 if (penalty_cr or 0) >= 10 else 0.0)
        cat.confidence = 90.0
        cat.matched_rule = "regulatory_action"
        cat.tags.append("regulatory")
        return cat

    if any(k in full_l for k in ("fraud", "forensic audit", "ed summons", "enforcement directorate", "cbi", "insolvency", "nclt", "default on", "resolution plan")):
        cat.news_category = "FRAUD_OR_GOVERNANCE"
        cat.direction = BEARISH
        cat.impact_hint = 88.0
        cat.confidence = 90.0
        cat.matched_rule = "governance_shock"
        cat.tags.append("governance")
        return cat

    if any(k in full_l for k in ("auditor resign", "resignation of auditor", "resignation of statutory auditor")):
        cat.news_category = "FRAUD_OR_GOVERNANCE"
        cat.direction = BEARISH
        cat.impact_hint = 85.0
        cat.matched_rule = "auditor_resignation"
        cat.tags.append("governance")
        return cat

    # 2. Financial results ---------------------------------------------------
    if "financial result" in subj or "financial results" in full_l or "quarterly result" in full_l or re.search(r"\b(q[1-4])\s*fy", full_l):
        cat.news_category = "QUARTERLY_RESULTS"
        cat.confidence = 88.0
        cat.matched_rule = "financial_results"
        cat.tags.append("results")
        # Direction from the strongest available signal: profit YoY, else revenue YoY.
        signal = profit_yoy if profit_yoy is not None else revenue_yoy
        if signal is None:
            # Results filed but numbers not in the text yet — neutral placeholder,
            # the numbers collector / LLM fills this in later.
            cat.direction = NEUTRAL
            cat.impact_hint = 55.0
            return cat
        if signal <= -10:
            cat.news_category = "PROFIT_WARNING"
            cat.direction = BEARISH
            cat.impact_hint = 78.0 if signal <= -25 else 68.0
        elif signal < 8:
            # Flat / low growth is a deceleration disappointment, not a buy.
            cat.direction = NEUTRAL
            cat.impact_hint = 52.0
        elif signal < 25:
            cat.direction = BULLISH
            cat.impact_hint = 66.0
        else:
            cat.direction = BULLISH
            cat.impact_hint = 80.0
        return cat

    # 3. Order wins / contracts ----------------------------------------------
    if any(k in full_l for k in ("award of order", "receipt of order", "bags order", "wins order", "awarded contract", "letter of award", "work order", "order worth", "secures order", "bags contract")):
        cat.news_category = "ORDER_WIN"
        cat.direction = BULLISH
        cat.confidence = 86.0
        cat.matched_rule = "order_win"
        cat.tags.append("order")
        if order_cr is None:
            cat.impact_hint = 58.0  # unquantified order — cannot be modelled by institutions
            cat.tags.append("unquantified")
        elif order_cr >= 5000:
            cat.impact_hint = 90.0
        elif order_cr >= 1000:
            cat.impact_hint = 84.0
        elif order_cr >= 100:
            cat.impact_hint = 74.0
        else:
            cat.impact_hint = 64.0
        return cat

    # 4. Corporate actions ----------------------------------------------------
    if "buy" in subj and "back" in subj or "buyback" in full_l or "buy-back" in full_l:
        cat.news_category = "BUYBACK"
        cat.direction = BULLISH
        cat.impact_hint = 64.0
        cat.matched_rule = "buyback"
        cat.tags.append("capital_return")
        return cat

    if any(k in full_l for k in ("bonus issue", "stock split", "sub-division of equity", "special dividend")):
        cat.news_category = "DIVIDEND"
        cat.direction = BULLISH
        cat.impact_hint = 58.0
        cat.matched_rule = "bonus_split"
        cat.tags.append("capital_return")
        return cat

    if any(k in full_l for k in ("acquisition", "acquires", "to acquire", "stake in", "scheme of arrangement", "amalgamation", "merger", "demerger")):
        cat.news_category = "MERGER" if any(k in full_l for k in ("merger", "amalgamation", "demerger", "scheme of arrangement")) else "ACQUISITION"
        cat.direction = BULLISH
        cat.impact_hint = 70.0
        cat.matched_rule = "m_and_a"
        cat.tags.append("m&a")
        return cat

    if any(k in full_l for k in ("fund rais", "fund-rais", "qip", "preferential issue", "preferential allotment", "rights issue", "ncd", "debenture")):
        cat.news_category = "FUND_RAISE"
        cat.direction = NEUTRAL
        cat.impact_hint = 55.0
        cat.matched_rule = "fund_raise"
        cat.tags.append("capital")
        return cat

    if any(k in full_l for k in ("credit rating", "rating upgrade", "rating downgrade", "reaffirm")):
        if any(k in full_l for k in ("downgrade", "revised downward", "negative outlook")):
            cat.news_category = "REGULATORY_ACTION"
            cat.direction = BEARISH
            cat.impact_hint = 68.0
            cat.matched_rule = "rating_downgrade"
        else:
            cat.news_category = "BUSINESS_UPDATE"
            cat.direction = BULLISH if "upgrade" in full_l else NEUTRAL
            cat.impact_hint = 60.0 if "upgrade" in full_l else 45.0
            cat.matched_rule = "rating_change"
        cat.tags.append("rating")
        return cat

    # 5. Management / board ---------------------------------------------------
    if any(k in full_l for k in ("resignation", "resigns", "cessation", "steps down")):
        cat.news_category = "MANAGEMENT_CHANGE"
        # Resignation of a key person (MD/CEO/CFO/Chairman) is the market-moving case.
        key_person = any(k in full_l for k in ("managing director", "chief executive", "ceo", "cfo", "chief financial", "chairman", "whole-time director", "whole time director"))
        cat.direction = BEARISH if key_person else NEUTRAL
        cat.impact_hint = 66.0 if key_person else 42.0
        cat.matched_rule = "management_change"
        cat.tags.append("management")
        if not key_person:
            cat.is_material = False
        return cat

    if any(k in full_l for k in ("appointment", "appointed", "re-appointment")):
        cat.news_category = "MANAGEMENT_CHANGE"
        cat.direction = NEUTRAL
        cat.impact_hint = 40.0
        cat.is_material = False
        cat.matched_rule = "appointment"
        cat.tags.append("management")
        return cat

    # 6. Capacity / dividends -------------------------------------------------
    if any(k in full_l for k in ("capacity expansion", "commissioning", "commissions", "new plant", "capex")):
        cat.news_category = "CAPACITY_EXPANSION"
        cat.direction = BULLISH
        cat.impact_hint = 58.0
        cat.matched_rule = "capacity"
        cat.tags.append("capex")
        return cat

    if "dividend" in full_l:
        cat.news_category = "DIVIDEND"
        cat.direction = NEUTRAL
        cat.impact_hint = 45.0
        cat.is_material = False
        cat.matched_rule = "dividend"
        cat.tags.append("dividend")
        return cat

    # 7. Board-meeting intimation (agenda unknown until outcome filed) --------
    if "board meeting" in full_l or "intimation of" in subj:
        cat.news_category = "BUSINESS_UPDATE"
        cat.direction = NEUTRAL
        cat.impact_hint = 40.0
        cat.is_material = False
        cat.matched_rule = "board_meeting_intimation"
        cat.tags.append("intimation")
        return cat

    # 8. Fallback -------------------------------------------------------------
    cat.news_category = "BUSINESS_UPDATE"
    cat.direction = NEUTRAL
    cat.impact_hint = 40.0
    cat.confidence = 70.0
    cat.is_material = False
    cat.matched_rule = "unclassified"
    return cat
