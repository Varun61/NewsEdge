"""Pure, headline-derived scoring penalties.

Extracted verbatim from ``ScoringEngine.score_event`` so the densest, most
logic-heavy part of scoring is isolated and unit-testable with no DB, network,
or LLM. Given a :class:`PenaltyContext` it returns a ``{name: modifier}`` map;
the scoring engine merges it with the contextual (market/analyzer) signals.

Behaviour-preserving: the rules and magnitudes are identical to the original
inline block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict

from app.intelligence.ai_provider import is_stale_recap


@dataclass(frozen=True)
class PenaltyContext:
    headline: str
    headline_lower: str
    cat_str: str
    news_category: str
    confidence: float
    impact_score: float
    freshness_score: float
    confirmation_score: float
    credibility_score: float
    event_symbol: str
    company_name: str
    bellwethers: frozenset | set
    alias_stopwords: frozenset | set


def compute_headline_penalties(ctx: PenaltyContext) -> Dict[str, float]:
    """Compute the headline-derived penalty/modifier map for one event."""
    penalties: Dict[str, float] = {}
    headline_lower = ctx.headline_lower
    cat_str = ctx.cat_str

    if ctx.freshness_score <= 30.0:
        penalties["stale_news_gap_exhaustion"] = -10.0
    if ctx.confirmation_score <= 50.0 and ctx.credibility_score < 70.0:
        penalties["unconfirmed_single_source"] = -5.0
    if ctx.confidence < 50.0:
        penalties["low_confidence_identification"] = -10.0
    # Routine / low-signal news: cap impact
    if ctx.news_category in ("BUSINESS_UPDATE", "OTHER", "SHAREHOLDING_CHANGE") and ctx.impact_score < 65.0:
        penalties["routine_low_signal"] = -8.0
    # Capacity expansion & buyback sell-on-news dampener
    if cat_str == "CAPACITY_EXPANSION" and not any(kw in headline_lower for kw in ["bags order", "wins contract", "commissions"]):
        penalties["long_gestation_capex"] = -10.0
    if cat_str == "BUYBACK":
        penalties["buyback_sell_on_news"] = -8.0

    # Backward-looking past price action report (exhausted momentum)
    # Note: use ``\d+\s*%`` (not ``\d+%\b``) — a percent sign followed by a space
    # has no word boundary, so the old ``\d+%\b`` silently missed "surge 18%".
    past_surge_patterns = [
        r"\b(?:shares|stock)\b.*\b(?:surge\w*|skyrocket\w*|rally\w*|rallied|jump\w*|jumped|gain\w*|gained|soar\w*)\b.*(?:\d+\s*%|\d+\s*percent)",
        r"\b(?:rallies|surges|jumps|zooms|skyrockets)\b\s+(?:whopping\s+)?(?:\d+\s*%|\d+\s*percent)",
        r"\b(?:hits|hit|touches|scaled)\b.*\b(?:52-week high|record high|all-time high|new high)\b",
        r"\bup\s+(?:\d+\s*%|\d+\s*percent)\s+(?:since|in\s+\d+|from\s+ipo)",
    ]
    is_past_price_report = any(bool(re.search(pat, headline_lower)) for pat in past_surge_patterns)
    if is_past_price_report and not any(kw in headline_lower for kw in ["bags order", "wins contract", "secures order", "awarded"]):
        penalties["past_price_action_exhaustion"] = -12.0

    # Tiny absolute profit filter
    tiny_profit_match = re.search(r"profit.*?(?:rs\.?|inr|₹)\s*(\d+(?:\.\d+)?)\s*(?:crore|cr)\b", headline_lower)
    if tiny_profit_match:
        abs_profit_cr = float(tiny_profit_match.group(1))
        if abs_profit_cr < 5.0:
            penalties["tiny_absolute_profit"] = -15.0

    # Speculative / interview / forecast headlines
    speculative_patterns = [
        r"\binterview\b", r"\bcould\s+rally\b", r"\bmay\s+(?:rally|surge|jump)\b",
        r"\bsees?\s+\d+%\s+upside\b", r"\bexpects?\b.*\bgrowth\b",
    ]
    if any(re.search(pat, headline_lower) for pat in speculative_patterns):
        penalties["speculative_forecast"] = -10.0

    # Sub-par growth (<8%) or flat profit = growth deceleration / miss
    low_growth_match = re.search(r"\b(?:profit|pat|net)\b.*?\b(?:rises|up|grows)\b\s+(\d+(?:\.\d+)?)%", headline_lower)
    if low_growth_match:
        pct = float(low_growth_match.group(1))
        if pct < 8.0:
            penalties["subpar_growth_deceleration"] = -14.0
    elif any(w in headline_lower for w in ["pat remains flat", "profit remains flat", "flat pat", "profit flat"]):
        penalties["flat_growth_deceleration"] = -14.0

    # Operating margin compression / erosion
    margin_compression_patterns = [
        r"\bmargins?\s+(?:shrink\w*|contract\w*|narrow\w*|drop\w*|fall\w*|decline\w*|sinks?)",
        r"\bmargin\s+pressure\b",
        r"\bebitda\s+margin\s+(?:down|drops|falls|contracts)",
        r"\boperating\s+margin\s+(?:down|drops|falls|contracts)",
    ]
    if any(re.search(pat, headline_lower) for pat in margin_compression_patterns):
        penalties["margin_compression"] = -18.0

    # Unquantified order win (no monetary value). A highly-confident source
    # reporting an order is likely real even if the headline omits the figure,
    # so penalise it less (the value is usually in the body).
    if cat_str == "ORDER_WIN":
        has_rupee_amount = bool(re.search(r"(?:rs\.?|inr|₹|usd|\$)\s*[\d,]+(?:\.\d+)?\s*(?:crore|cr|million|billion|mn|bn)\b", headline_lower))
        if not has_rupee_amount:
            penalties["unquantified_order_win"] = -6.0 if ctx.confidence >= 85.0 else -12.0

    # "Order book"/backlog/pipeline is a CUMULATIVE figure (analysis), not a fresh
    # order win catalyst (e.g. "Can X's ₹47,000cr order book power growth?").
    if any(k in headline_lower for k in ("order book", "orderbook", "order backlog", "order pipeline")) and not any(
        v in headline_lower for v in ("bags", "wins", "secures", "receives", "awarded", "bagged", "new order")
    ):
        penalties["order_book_not_new_order"] = -12.0

    # Negative forward guidance / concall headwinds
    negative_guidance_patterns = [
        r"\bguidance\s+(?:cut|lowered|slashed|reduced|downgraded)",
        r"\bcuts?\s+guidance\b",
        r"\bdemand\s+slowdown\b",
        r"\bpricing\s+pressure\b",
        r"\bfurloughs?\b",
        r"\bdelayed\s+(?:decision|capex|order)",
        r"\bcautious\s+outlook\b",
    ]
    if any(re.search(pat, headline_lower) for pat in negative_guidance_patterns):
        penalties["negative_forward_guidance"] = -18.0

    # Routine calendar / dividend schedules / generic listicles
    routine_calendar_patterns = [
        r"\bdividend\s+this\s+week\b",
        r"\bdividend\s+calendar\b",
        r"\brecord\s+dates?\b",
        r"\bstocks?\s+to\s+watch\s+this\s+week\b",
        r"\bshares?\s+to\s+remain\s+in\s+focus\b",
        r"\breworks?\s+20\d\d\s+target\b",
        r"\bmeet\s+the\s+smallcap\b",
    ]
    if any(re.search(pat, headline_lower) for pat in routine_calendar_patterns):
        penalties["routine_calendar_event"] = -15.0

    # Evergreen recap / preview / "should you buy" / "in focus" — not a fresh catalyst
    if is_stale_recap(ctx.headline or ""):
        penalties["stale_or_recap_reference"] = -14.0

    # Entity headline verification: headline must actually name the company/symbol
    event_symbol = ctx.event_symbol
    comp_name = ctx.company_name
    is_exchange_announcement = any(x in headline_lower for x in ["corporate/", "announces", "intimates", "submits", "outcome of board", "appointment", "appointed"])
    headline_mentions_company = (
        (event_symbol and bool(re.search(rf"\b{re.escape(event_symbol)}\b", ctx.headline, re.IGNORECASE)))
        or (comp_name and any(p.lower() in headline_lower for p in comp_name.lower().split() if len(p) >= 4 and p.lower() not in ctx.alias_stopwords))
        or is_exchange_announcement
    )
    if not headline_mentions_company:
        penalties["body_only_mention"] = -12.0

    # ── EARNINGS QUALITY GATE ─────────────────────────────────────────────
    profit_g_match = re.search(
        r"\b(?:profit|pat|net)\b.*?\b(?:rises?|jumps?|surges?|up|grows?)\b\s+(?:by\s+)?(\d+(?:\.\d+)?)%",
        headline_lower,
    )
    revenue_g_match = re.search(
        r"\b(?:revenue|sales|turnover)\b.*?\b(?:rises?|jumps?|surges?|up|grows?)\b\s+(?:by\s+)?(\d+(?:\.\d+)?)%",
        headline_lower,
    )
    if profit_g_match and revenue_g_match:
        profit_g = float(profit_g_match.group(1))
        revenue_g = float(revenue_g_match.group(1))
        if profit_g > revenue_g + 25 and revenue_g < 15:
            penalties["revenue_profit_divergence"] = -12.0

    # Exceptional / one-time / non-recurring income inflating results
    exceptional_patterns = [
        r"\bexceptional\s+(?:item|gain|income)",
        r"\bone[- ]time\s+(?:gain|income|benefit)",
        r"\bnon[- ]recurring\s+(?:income|gain)",
        r"\bother\s+income\s+(?:jumps?|surges?|rises?|up|boost)",
        r"\bextraordinary\s+(?:item|gain|income)",
        r"\btax\s+(?:write[- ]?back|reversal|refund)\s+(?:boost|lifts?|aids?)",
    ]
    if any(re.search(pat, headline_lower) for pat in exceptional_patterns):
        penalties["exceptional_items_inflation"] = -15.0

    # Large-cap modest growth: institutional sell-the-news for blue chips
    if event_symbol in ctx.bellwethers:
        bellwether_growth = re.search(
            r"\b(?:profit|pat|net)\b.*?\b(?:rises?|up|grows?|jumps?)\b\s+(?:by\s+)?(\d+(?:\.\d+)?)%",
            headline_lower,
        )
        if bellwether_growth:
            bw_pct = float(bellwether_growth.group(1))
            if bw_pct < 15.0:
                penalties["largecap_modest_growth"] = -14.0

    # Management caution / concall headwind signals
    cautious_tone_patterns = [
        r"\bcautious\s+(?:on|about|outlook|management)",
        r"\bmanagement\s+(?:cautious|warns?|sees?\s+challenges?)",
        r"\bchallenging\s+(?:quarter|environment|outlook|macro)",
        r"\bweak\s+(?:demand|pipeline|order\s*book|commentary)",
        r"\bslower\s+(?:growth|recovery|momentum|deal\s+wins?)",
        r"\bheadwinds?\b",
        r"\bmuted\s+(?:outlook|guidance|growth|commentary)",
        r"\bpressure\s+on\s+(?:margins?|growth|revenue)",
        r"\bmanagement\s+(?:commentary|tone)\s+(?:negative|weak|cautious|disappointing)",
        r"\bdisappointing\s+(?:guidance|commentary|outlook|concall)",
    ]
    if any(re.search(pat, headline_lower) for pat in cautious_tone_patterns):
        penalties["management_caution_tone"] = -14.0

    return penalties
