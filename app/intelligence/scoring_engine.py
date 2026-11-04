"""Configurable stock ranking and candidate scoring engine.

Implements institutional-grade intraday intelligence logic:
- Negativity Asymmetry: Negative regulatory/governance catalysts carry higher velocity
  penalties and downside impact multipliers.
- Materiality-Weighted Scoring: Order wins and profit expansion evaluated against revenue scale.
- Multi-Source Confirmation: Independent verification across top publishers increases conviction.
- Overnight Freshness Decay: Maximizes priority for announcements occurring between
  yesterday's 15:30 close and today's 08:00 open.
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
from app.intelligence.ai_provider import ClassificationResult

logger = logging.getLogger("newsedge.intelligence.scoring")


class ScoringEngine:
    """Calculates overall 0-100 score and assigns candidate priority."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.version = "1.1"

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
        # Backward-looking past price action report (exhausted momentum)
        import re
        headline_lower = event.primary_headline.lower()
        past_surge_patterns = [
            r"\b(?:shares|stock)\b.*\b(?:surge\w*|skyrocket\w*|rally\w*|rallied|jump\w*|jumped|gain\w*|gained|soar\w*)\b.*\b(?:\d+%\b|\d+\s*percent)",
            r"\b(?:rallies|surges|jumps|zooms|skyrockets)\b\s+(?:whopping\s+)?(?:\d+%\b|\d+\s*percent)",
            r"\b(?:hits|hit|touches|scaled)\b.*\b(?:52-week high|record high|all-time high|new high)\b",
            r"\bup\s+(?:\d+%\b|\d+\s*percent)\s+(?:since|in\s+\d+|from\s+ipo)",
        ]
        is_past_price_report = any(bool(re.search(pat, headline_lower)) for pat in past_surge_patterns)
        if is_past_price_report and not any(kw in headline_lower for kw in ["bags order", "wins contract", "secures order", "awarded"]):
            penalties["past_price_action_exhaustion"] = -12.0

        final_score = max(0.0, min(100.0, raw_score + sum(penalties.values())))

        # 5. Hard minimum-confidence gate — if we can't verify the company, exclude from watchlist
        if classification.confidence < 52.0 and final_score < 72.0:
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

        # 6. Determine Classification Priority (tighter thresholds for STRONG tiers)
        if is_negative:
            if final_score >= 78.0:
                candidate_class = CandidateClassification.STRONG_BEARISH
            elif final_score >= 60.0:
                candidate_class = CandidateClassification.BEARISH
            elif final_score >= 46.0:
                candidate_class = CandidateClassification.WATCH_ONLY
            else:
                candidate_class = CandidateClassification.EXCLUDED
        elif "bullish" in direction or classification.sentiment in ("VERY_POSITIVE", "POSITIVE"):
            if final_score >= 78.0:
                candidate_class = CandidateClassification.STRONG_BULLISH
            elif final_score >= 60.0:
                candidate_class = CandidateClassification.BULLISH
            elif final_score >= 46.0:
                candidate_class = CandidateClassification.WATCH_ONLY
            else:
                candidate_class = CandidateClassification.EXCLUDED
        else:
            candidate_class = CandidateClassification.WATCH_ONLY if final_score >= 46.0 else CandidateClassification.EXCLUDED

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
