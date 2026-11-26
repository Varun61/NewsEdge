"""Configurable stock ranking and candidate scoring engine.

Implements institutional-grade intraday intelligence logic:
- Negativity Asymmetry: Negative regulatory/governance catalysts carry higher velocity
  penalties and downside impact multipliers.
- Materiality-Weighted Scoring: Order wins and profit expansion evaluated against revenue scale.
- Multi-Source Confirmation: Independent verification across top publishers increases conviction.
- Overnight Freshness Decay: Maximizes priority for announcements occurring between
  yesterday's 15:30 close and today's 08:00 open.
- Earnings Quality Gate: Detects revenue-profit divergence, one-off items, large-cap
  modest growth, and management caution tone to filter false-positive bullish signals.
- Sector Momentum Context: Adjusts conviction based on broad market / sectoral index direction.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.database.models import (
    CandidateClassification,
    NewsEvent,
    StockAnalysis,
)
from app.database.repository import Repository
from app.intelligence.ai_provider import ClassificationResult, is_stale_recap
from app.processors.nse_master import ALIAS_STOPWORDS
from app.processors.reference_data import load_set

logger = logging.getLogger("newsedge.intelligence.scoring")


    # Institutional bellwether / large-cap stocks where <15% profit growth is a SELL signal
    # (institutional consensus expects high-teens to 20%+ growth; single-digit growth = disappointment)
INSTITUTIONAL_BELLWETHERS = {
    # Banking & Finance
    "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "BAJAJFINSV",
    "INDUSINDBK", "BANKBARODA", "PNB", "CANBK",
    # IT Services
    "INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "LTIM", "MPHASIS", "COFORGE", "PERSISTENT",
    # FMCG
    "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "COLPAL", "DABUR", "MARICO",
    "GODREJCP", "TATACONSUM", "EMAMILTD",
    # Pharma
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "BIOCON", "LUPIN",
    # Auto
    "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "ASHOKLEY",
    # Metals & Mining
    "JSWSTEEL", "TATASTEEL", "HINDALCO", "VEDL", "COALINDIA", "NMDC",
    # Energy & Oil
    "RELIANCE", "ONGC", "BPCL", "IOC", "GAIL", "NTPC", "POWERGRID", "ADANIGREEN",
    # Infrastructure & Engineering
    "LT", "ADANIENT", "ADANIPORTS", "ULTRACEMCO", "GRASIM", "SHREECEM",
    # Others
    "BHARTIARTL", "ASIANPAINT", "TITAN", "PIDILITIND", "BERGEPAINT",
    "HAVELLS", "VOLTAS", "SIEMENS", "ABB", "TRENT",
}
# Externalised: data/reference/institutional_bellwethers.json overrides the
# in-code default above when present.
INSTITUTIONAL_BELLWETHERS = load_set("institutional_bellwethers", INSTITUTIONAL_BELLWETHERS)


class ScoringEngine:
    """Calculates overall 0-100 score and assigns candidate priority."""

    def __init__(self, settings: Settings, policy: Optional["ScoringPolicy"] = None):
        self.settings = settings
        self.version = "1.3"
        from app.intelligence.scoring_policy import DEFAULT_POLICY
        self.policy = policy or DEFAULT_POLICY

    def _calculate_freshness_score(self, event_time: Optional[datetime]) -> float:
        """Exponential decay based on age in hours."""
        if not event_time:
            return 60.0

        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_hours = (now - event_time).total_seconds() / 3600.0

        if age_hours <= 4.0:
            return 100.0
        elif age_hours <= 10.0:
            return 90.0
        elif age_hours <= 16.0:
            return 75.0
        elif age_hours <= 24.0:
            return 55.0
        else:
            return 25.0

    def _calculate_confirmation_score(self, num_articles: int) -> float:
        """Score based on independent publishers reporting the event."""
        if num_articles >= 3:
            return 100.0
        elif num_articles == 2:
            return 80.0
        else:
            return 50.0

    def _contextual_signals(
        self, event, event_symbol, direction, is_positive, is_negative, company
    ) -> Dict[str, float]:
        """Collect optional, independent contextual signals into a modifier map.

        Each evaluator (sector momentum, technical trend, concall tone, bulk/
        block deals, promoter pledge, delivery/volume, tradeable liquidity) is
        best-effort: a failure in one never blocks the others or the score.
        """
        signals: Dict[str, float] = {}

        # ── SECTOR MOMENTUM CONTEXT ───────────────────────────────────────
        try:
            from app.intelligence.sector_momentum import get_sector_momentum_analyzer
            momentum_analyzer = get_sector_momentum_analyzer()
            if event_symbol:
                sector_mod = momentum_analyzer.get_sector_modifier(event_symbol)
                if sector_mod < 0:
                    signals["sector_headwind"] = sector_mod
                elif sector_mod > 0 and is_positive:
                    signals["sector_tailwind"] = sector_mod
        except Exception:
            pass  # Sector momentum is optional; continue without it

        # ── TECHNICAL TREND CONTEXT ───────────────────────────────────────
        try:
            from app.intelligence.technical_trend import get_technical_trend_analyzer
            trend_analyzer = get_technical_trend_analyzer()
            if event_symbol:
                trend_eval = trend_analyzer.get_trend_evaluation(event_symbol, direction)
                if trend_eval:
                    if trend_eval.score_modifier < 0:
                        signals["technical_counter_trend"] = trend_eval.score_modifier
                    elif trend_eval.score_modifier > 0 and is_positive:
                        signals["technical_uptrend_tailwind"] = trend_eval.score_modifier
        except Exception:
            pass

        # ── CONCALL COMMENTARY ALIGNMENT ──────────────────────────────────
        try:
            from app.intelligence.concall_analyzer import get_concall_analyzer
            concall_analyzer = get_concall_analyzer()
            full_c_text = f"{event.primary_headline} {event.news_summary or ''}"
            concall_eval = concall_analyzer.analyze_text(full_c_text)
            if concall_eval.score_modifier < 0:
                signals["concall_headwind"] = concall_eval.score_modifier
            elif concall_eval.score_modifier > 0 and is_positive:
                signals["concall_tailwind"] = concall_eval.score_modifier
        except Exception:
            pass

        # ── BULK & BLOCK DEALS CORRELATION ────────────────────────────────
        try:
            from app.intelligence.bulk_deals_analyzer import get_bulk_deals_analyzer
            bulk_analyzer = get_bulk_deals_analyzer()
            full_b_text = f"{event.primary_headline} {event.news_summary or ''}"
            deal_eval = bulk_analyzer.evaluate_deal(event.primary_headline, full_b_text)
            if deal_eval.is_promoter_selling:
                signals["bulk_deals_promoter_dump"] = deal_eval.score_modifier
            elif deal_eval.is_institutional_buying and is_positive:
                signals["bulk_deals_marquee_buyer"] = deal_eval.score_modifier
        except Exception:
            pass

        # ── PROMOTER PLEDGE & SHAREHOLDING HEALTH ─────────────────────────
        try:
            from app.intelligence.shareholding_analyzer import get_shareholding_analyzer
            share_analyzer = get_shareholding_analyzer()
            full_s_text = f"{event.primary_headline} {event.news_summary or ''}"
            if event_symbol:
                share_eval = share_analyzer.evaluate_health(event_symbol, full_s_text)
                if share_eval.is_high_pledge:
                    signals["high_promoter_pledge"] = share_eval.score_modifier
                elif share_eval.is_promoter_selling:
                    signals["promoter_stake_dilution"] = share_eval.score_modifier
                elif share_eval.is_institutional_inflow and is_positive:
                    signals["institutional_stake_inflow"] = share_eval.score_modifier
        except Exception:
            pass

        # ── DELIVERY & VOLUME CONVICTION (NSE bhavcopy) ───────────────────
        try:
            from app.market_data.bhavcopy import get_bhavcopy_provider
            if event_symbol:
                mkt = get_bhavcopy_provider().metrics(event_symbol)
                if mkt:
                    if (is_positive or is_negative) and mkt.delivery_pct >= 65.0 and mkt.relative_volume >= 1.5:
                        signals["delivery_volume_conviction"] = +6.0
                    elif mkt.relative_volume and mkt.relative_volume < 0.5:
                        signals["thin_volume_participation"] = -4.0
        except Exception:
            pass

        # ── TRADEABLE LIQUIDITY GATE ──────────────────────────────────────
        try:
            from app.intelligence.liquidity_gate import evaluate_liquidity
            if event_symbol:
                mcap_cat = None
                mcap_cr = None
                if company is not None:
                    if getattr(company, "market_cap_category", None) is not None:
                        mcap_cat = company.market_cap_category.value
                    mcap_cr = getattr(company, "market_cap", None)
                liq = evaluate_liquidity(event_symbol, mcap_cat, mcap_cr)
                if not liq.is_tradeable:
                    signals["illiquid_untradeable"] = liq.score_modifier
                elif liq.score_modifier < 0:
                    signals[f"liquidity_{liq.tier.lower()}"] = liq.score_modifier
        except Exception:
            pass

        return signals

    def score_event(
        self,
        event: NewsEvent,
        classification: ClassificationResult,
        materiality_score: float,
        session: Session,
    ) -> Optional[StockAnalysis]:
        """Compute multi-factor score and persist StockAnalysis record."""
        if not event.primary_company_id:
            logger.debug("Event %d has no mapped company; skipping analysis.", event.id)
            return None

        # 1. Base component scores
        news_impact = float(classification.impact_score)
        mat_score = float(materiality_score)

        # Source credibility: average of linked articles
        linked_articles = [link.article for link in event.article_links if link.article]
        if linked_articles:
            avg_cred = sum(a.source_credibility for a in linked_articles) / len(linked_articles)
            credibility_score = avg_cred * 100.0
        else:
            credibility_score = 65.0

        event_time = linked_articles[0].published_at if linked_articles else event.created_at
        freshness_score = self._calculate_freshness_score(event_time)
        confirmation_score = self._calculate_confirmation_score(len(linked_articles))

        # Dynamic empirical historical reaction score
        from app.intelligence.historical_reactions import match_historical_reaction
        hist_profile = match_historical_reaction(event.primary_headline)
        if hist_profile:
            historical_score = float(hist_profile.historical_score)
        else:
            historical_score = 55.0

        company_conf_score = float(classification.confidence)

        # 2. Cross-validate direction with semantic news category
        direction = classification.expected_direction.lower()
        cat_str = str(classification.news_category)
        if hasattr(classification.news_category, "value"):
            cat_str = classification.news_category.value
        cat_str = cat_str.upper()

        bearish_cats = {"PROFIT_WARNING", "FRAUD_OR_GOVERNANCE", "REGULATORY_ACTION", "CONTRACT_CANCELLATION", "LEGAL_ISSUE"}
        bullish_cats = {"ORDER_WIN", "PROFIT_GROWTH", "REVENUE_GROWTH", "CAPACITY_EXPANSION", "REGULATORY_APPROVAL", "BUYBACK"}

        # Regulatory relief check (e.g. IRDAI cutting processing fees, SEBI reducing charges)
        regulatory_relief_keywords = ["cuts fee", "cut fee", "slashes fee", "reduces fee", "fee cut", "processing fee cut", "relaxes norm", "eases norm"]
        is_reg_relief = any(kw in event.primary_headline.lower() for kw in regulatory_relief_keywords)

        if cat_str == "REGULATORY_ACTION" and is_reg_relief:
            direction = "bullish"
        elif cat_str in bearish_cats and "bullish" in direction:
            logger.warning("Direction mismatch for event #%d: Category %s cannot be bullish. Overriding to bearish.", event.id, cat_str)
            direction = "bearish"
        elif cat_str in bullish_cats and "bearish" in direction:
            logger.warning("Direction mismatch for event #%d: Category %s cannot be bearish. Overriding to bullish.", event.id, cat_str)
            direction = "bullish"

        # Asymmetric Negativity Boost (institutional market reality: bad news repricing is faster)
        is_negative = "bearish" in direction or classification.sentiment in ("VERY_NEGATIVE", "NEGATIVE")
        is_positive = "bullish" in direction or classification.sentiment in ("VERY_POSITIVE", "POSITIVE")

        if is_negative and news_impact >= 70.0:
            news_impact = min(100.0, news_impact * 1.15)

        # 3. Weighted sum
        weights = (
            (self.settings.weight_news_impact, news_impact),
            (self.settings.weight_financial_materiality, mat_score),
            (self.settings.weight_source_credibility, credibility_score),
            (self.settings.weight_freshness, freshness_score),
            (self.settings.weight_confirmations, confirmation_score),
            (self.settings.weight_historical_reaction, historical_score),
            (self.settings.weight_company_confidence, company_conf_score),
        )

        total_weight = sum(w[0] for w in weights)
        raw_score = sum(w * s for w, s in weights) / (total_weight or 100.0)

        # 4. Apply penalties
        penalties: Dict[str, float] = {}
        import re
        headline_lower = (event.primary_headline or "").lower()

        if freshness_score <= 30.0:
            penalties["stale_news_gap_exhaustion"] = -10.0
        if confirmation_score <= 50.0 and credibility_score < 70.0:
            penalties["unconfirmed_single_source"] = -5.0
        if classification.confidence < 50.0:
            penalties["low_confidence_identification"] = -10.0
        # Routine / low-signal news: cap impact
        if classification.news_category in ("BUSINESS_UPDATE", "OTHER", "SHAREHOLDING_CHANGE") and \
                classification.impact_score < 65.0:
            penalties["routine_low_signal"] = -8.0
        # Capacity expansion & buyback sell-on-news dampener (lacks immediate intraday earnings velocity)
        if cat_str == "CAPACITY_EXPANSION" and not any(kw in headline_lower for kw in ["bags order", "wins contract", "commissions"]):
            penalties["long_gestation_capex"] = -10.0
        if cat_str == "BUYBACK":
            penalties["buyback_sell_on_news"] = -8.0
        # Backward-looking past price action report (exhausted momentum)
        past_surge_patterns = [
            r"\b(?:shares|stock)\b.*\b(?:surge\w*|skyrocket\w*|rally\w*|rallied|jump\w*|jumped|gain\w*|gained|soar\w*)\b.*\b(?:\d+%\b|\d+\s*percent)",
            r"\b(?:rallies|surges|jumps|zooms|skyrockets)\b\s+(?:whopping\s+)?(?:\d+%\b|\d+\s*percent)",
            r"\b(?:hits|hit|touches|scaled)\b.*\b(?:52-week high|record high|all-time high|new high)\b",
            r"\bup\s+(?:\d+%\b|\d+\s*percent)\s+(?:since|in\s+\d+|from\s+ipo)",
        ]
        is_past_price_report = any(bool(re.search(pat, headline_lower)) for pat in past_surge_patterns)
        if is_past_price_report and not any(kw in headline_lower for kw in ["bags order", "wins contract", "secures order", "awarded"]):
            penalties["past_price_action_exhaustion"] = -12.0

        # Tiny absolute profit filter: if headline mentions profit in single-digit crores, it's immaterial for mid/large caps
        tiny_profit_match = re.search(r"profit.*?(?:rs\.?|inr|₹)\s*(\d+(?:\.\d+)?)\s*(?:crore|cr)\b", headline_lower)
        if tiny_profit_match:
            abs_profit_cr = float(tiny_profit_match.group(1))
            if abs_profit_cr < 5.0:
                penalties["tiny_absolute_profit"] = -15.0

        # Speculative / interview / forecast headlines — not confirmed events
        speculative_patterns = [
            r"\binterview\b", r"\bcould\s+rally\b", r"\bmay\s+(?:rally|surge|jump)\b",
            r"\bsees?\s+\d+%\s+upside\b", r"\bexpects?\b.*\bgrowth\b"
        ]
        if any(re.search(pat, headline_lower) for pat in speculative_patterns):
            penalties["speculative_forecast"] = -10.0

        # Sub-par growth (<8%) or flat profit is an institutional growth deceleration / miss
        low_growth_match = re.search(r"\b(?:profit|pat|net)\b.*?\b(?:rises|up|grows)\b\s+(\d+(?:\.\d+)?)%", headline_lower)
        if low_growth_match:
            pct = float(low_growth_match.group(1))
            if pct < 8.0:
                penalties["subpar_growth_deceleration"] = -14.0
        elif any(w in headline_lower for w in ["pat remains flat", "profit remains flat", "flat pat", "profit flat"]):
            penalties["flat_growth_deceleration"] = -14.0

        # Operating margin compression / margin erosion (causes post-earnings dump)
        margin_compression_patterns = [
            r"\bmargins?\s+(?:shrink\w*|contract\w*|narrow\w*|drop\w*|fall\w*|decline\w*|sinks?)",
            r"\bmargin\s+pressure\b",
            r"\bebitda\s+margin\s+(?:down|drops|falls|contracts)",
            r"\boperating\s+margin\s+(?:down|drops|falls|contracts)",
        ]
        if any(re.search(pat, headline_lower) for pat in margin_compression_patterns):
            penalties["margin_compression"] = -18.0

        # Unquantified order win without monetary value (cannot be modeled by institutions)
        if cat_str == "ORDER_WIN":
            has_rupee_amount = bool(re.search(r"(?:rs\.?|inr|₹|usd|\$)\s*[\d,]+(?:\.\d+)?\s*(?:crore|cr|million|billion|mn|bn)\b", headline_lower))
            if not has_rupee_amount:
                penalties["unquantified_order_win"] = -12.0

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

        # Routine calendar, dividend date schedules, or generic listicles
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

        # Evergreen recap / preview / "should you buy" / "in focus" articles are a
        # fresh article about an OLD or not-yet-occurred event — not a fresh
        # catalyst (e.g. a TCS Q2 "results review" published weeks after results).
        if is_stale_recap(event.primary_headline or ""):
            penalties["stale_or_recap_reference"] = -14.0

        # Entity headline verification: ensure headline actually names the company/symbol
        company = event.primary_company
        event_symbol = company.nse_symbol if company else ""
        comp_name = company.company_name if company else ""
        is_exchange_announcement = any(x in headline_lower for x in ["corporate/", "announces", "intimates", "submits", "outcome of board", "appointment", "appointed"])
        headline_mentions_company = (
            (event_symbol and bool(re.search(rf"\b{re.escape(event_symbol)}\b", event.primary_headline, re.IGNORECASE)))
            or (comp_name and any(p.lower() in headline_lower for p in comp_name.lower().split() if len(p) >= 4 and p.lower() not in ALIAS_STOPWORDS))
            or is_exchange_announcement
        )
        if not headline_mentions_company:
            penalties["body_only_mention"] = -12.0

        # ── EARNINGS QUALITY GATE ─────────────────────────────────────────
        # Revenue-Profit divergence: profit inflated by one-offs / exceptional items
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
            # If profit grows 50%+ but revenue only grows <15%, profit is likely inflated by one-offs
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
        company = event.primary_company
        event_symbol = company.nse_symbol if company else ""
        if event_symbol in INSTITUTIONAL_BELLWETHERS:
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

        # ── Contextual signals (sector, trend, concall, bulk/block deals,
        #    promoter pledge, delivery/volume, liquidity). Each is an optional,
        #    independent evaluator; see _contextual_signals. ────────────────
        penalties.update(
            self._contextual_signals(event, event_symbol, direction, is_positive, is_negative, company)
        )

        final_score = max(0.0, min(100.0, raw_score + sum(penalties.values())))

        # 5. Hard minimum-confidence gate — if we can't verify the company, exclude from watchlist
        if classification.confidence < self.policy.min_confidence and final_score < self.policy.min_confidence_score:
            candidate_class = CandidateClassification.EXCLUDED
            analysis = Repository.create_analysis(
                session=session,
                news_event_id=event.id,
                company_id=event.primary_company_id,
                overall_score=round(final_score, 1),
                classification=candidate_class,
                news_impact_score=round(news_impact, 1),
                materiality_score=round(mat_score, 1),
                source_credibility_score=round(credibility_score, 1),
                freshness_score=round(freshness_score, 1),
                confirmation_score=round(confirmation_score, 1),
                historical_reaction_score=round(historical_score, 1),
                company_confidence_score=round(company_conf_score, 1),
                penalties=penalties if penalties else None,
                scoring_version=self.version,
            )
            logger.debug(
                "Event #%d excluded by min-confidence gate (conf=%.1f, score=%.1f)",
                event.id, classification.confidence, final_score,
            )
            return analysis

        # 6. Determine Classification Priority (thresholds centralised in ScoringPolicy)
        p = self.policy
        CC = CandidateClassification

        def _watch(score: float) -> CandidateClassification:
            return CC.WATCH_ONLY if score >= p.watch_cutoff else CC.EXCLUDED

        mat_str = (event.financial_materiality or "").strip()
        is_thematic_secondary = mat_str.startswith("[") and "]" in mat_str

        if is_thematic_secondary:
            # Secondary basket picks from sector themes are sympathy tracking items, not primary trade recommendations
            candidate_class = _watch(final_score)
        elif "illiquid_untradeable" in penalties:
            # Micro-cap: too thin for a reliable intraday fill — tracking only, never actionable
            candidate_class = _watch(final_score)
        elif "routine_calendar_event" in penalties:
            # Ex-dividend lists and general calendar updates belong in Watch Only
            candidate_class = _watch(final_score)
        elif "stale_or_recap_reference" in penalties:
            # Recap/preview/analysis of an old or future event — track, don't trade
            candidate_class = _watch(final_score)
        elif "body_only_mention" in penalties and final_score < p.override_body_only:
            # Company was not in the headline; avoid recommending body passing mentions as high conviction trades
            candidate_class = _watch(final_score)
        elif cat_str in ("BUSINESS_UPDATE", "OTHER"):
            # Routine commentary and generic updates never qualify for Bullish/Bearish trade watchlists
            candidate_class = _watch(final_score)
        elif cat_str == "CAPACITY_EXPANSION" and not any(kw in headline_lower for kw in ["bags order", "wins contract", "commissions", "inaugurates"]):
            # Uncommissioned long-gestation capex lacks next-day velocity — keep as WATCH_ONLY
            candidate_class = _watch(final_score)
        elif cat_str == "BUYBACK" and final_score < p.override_buyback:
            # Routine buybacks without high conviction tend to be sell-on-news
            candidate_class = _watch(final_score)
        elif "margin_compression" in penalties or "negative_forward_guidance" in penalties or "management_caution_tone" in penalties:
            # Margin erosion, guidance cut, or cautious management tone invalidates bullish trade thesis
            if is_negative or "negative_forward_guidance" in penalties:
                candidate_class = CC.BEARISH if final_score >= p.bearish_cutoff else CC.WATCH_ONLY
            else:
                candidate_class = _watch(final_score)
        elif "unquantified_order_win" in penalties and final_score < p.override_unquantified_order:
            # Orders without numeric value cannot be modeled by institutions — keep in WATCH_ONLY
            candidate_class = _watch(final_score)
        elif ("subpar_growth_deceleration" in penalties or "largecap_modest_growth" in penalties or "revenue_profit_divergence" in penalties or "exceptional_items_inflation" in penalties) and final_score < p.override_growth_quality:
            # Growth deceleration, bellwether modest growth, or accounting quality issues → WATCH_ONLY
            candidate_class = _watch(final_score)
        elif "technical_counter_trend" in penalties and is_positive and final_score < p.override_counter_trend:
            # Stock is in structural downtrend (Price < 20 EMA and 50 EMA) - avoid counter-trend trap
            candidate_class = _watch(final_score)
        elif "bulk_deals_promoter_dump" in penalties:
            # Promoter or PE stake offload creates massive supply overhang
            candidate_class = CC.BEARISH if final_score >= p.bearish_cutoff else CC.WATCH_ONLY
        elif "high_promoter_pledge" in penalties and is_positive and final_score < p.override_high_pledge:
            # Toxic pledge risk gates stock out of bullish actionable recommendations
            candidate_class = _watch(final_score)
        elif is_negative:
            if final_score >= p.strong_cutoff:
                candidate_class = CC.STRONG_BEARISH
            elif final_score >= p.bearish_cutoff:
                candidate_class = CC.BEARISH
            else:
                candidate_class = _watch(final_score)
        elif "bullish" in direction or classification.sentiment in ("VERY_POSITIVE", "POSITIVE"):
            if final_score >= p.strong_cutoff:
                candidate_class = CC.STRONG_BULLISH
            elif final_score >= p.bullish_cutoff:
                candidate_class = CC.BULLISH
            else:
                candidate_class = _watch(final_score)
        else:
            candidate_class = _watch(final_score)

        analysis = Repository.create_analysis(
            session=session,
            news_event_id=event.id,
            company_id=event.primary_company_id,
            overall_score=round(final_score, 1),
            classification=candidate_class,
            news_impact_score=round(news_impact, 1),
            materiality_score=round(mat_score, 1),
            source_credibility_score=round(credibility_score, 1),
            freshness_score=round(freshness_score, 1),
            confirmation_score=round(confirmation_score, 1),
            historical_reaction_score=round(historical_score, 1),
            company_confidence_score=round(company_conf_score, 1),
            penalties=penalties if penalties else None,
            scoring_version=self.version,
        )

        return analysis
