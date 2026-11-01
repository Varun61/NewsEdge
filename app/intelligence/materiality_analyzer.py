"""Financial materiality analysis engine for Indian market news."""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.database.models import Company, NewsCategory, NewsEvent
from app.intelligence.ai_provider import ClassificationResult

logger = logging.getLogger("newsedge.intelligence.materiality")


class MaterialityAnalyzer:
    """Evaluates the financial significance of announcements relative to company size."""

    @staticmethod
    def extract_monetary_value(text: str) -> Optional[float]:
        """Parse monetary figures in Indian numbering (Crores / Lakhs) and normalize to Crores (₹ Cr).

        Examples:
        - "₹1,000 crore" -> 1000.0
        - "Rs 500 crore" -> 500.0
        - "INR 2000 cr"  -> 2000.0
        - "₹50 lakh"     -> 0.50
        """
        # Look for numbers followed by crore/cr or lakh
        pattern = r"(?:(?:rs\.?|inr|₹)\s*)?([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh|lac)s?"
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None

        val_str = match.group(1).replace(",", "")
        unit = match.group(2).lower()

        try:
            val = float(val_str)
            if unit in ("crore", "cr"):
                return val
            elif unit in ("lakh", "lac"):
                return val / 100.0  # 100 Lakh = 1 Crore
        except ValueError:
            return None

        return None

    def analyze_order_win(
        self,
        event_text: str,
        company: Optional[Company],
    ) -> Tuple[float, str]:
        """Analyze ORDER_WIN materiality.

        Returns (score 0-100, explanation).
        """
        order_val = self.extract_monetary_value(event_text)

        if not order_val:
            return 50.0, "Order win announced; specific monetary order value not stated in text."

        if not company or not company.annual_revenue or company.annual_revenue <= 0:
            return 65.0, f"Order value ₹{order_val:,.1f} Cr reported (company annual revenue baseline unavailable)."

        ratio = (order_val / company.annual_revenue) * 100.0

        if ratio >= 20.0:
            score = 95.0
            impact_desc = "Extremely high materiality (>20% of annual revenue)"
        elif ratio >= 10.0:
            score = 85.0
            impact_desc = "High materiality (10-20% of annual revenue)"
        elif ratio >= 5.0:
            score = 75.0
            impact_desc = "Moderate materiality (5-10% of annual revenue)"
        elif ratio >= 1.0:
            score = 60.0
            impact_desc = "Low-to-moderate materiality (1-5% of annual revenue)"
        else:
            score = 40.0
            impact_desc = "Low materiality (<1% of annual revenue)"

        explanation = (
            f"Order size: ₹{order_val:,.1f} Cr vs Annual Revenue: ₹{company.annual_revenue:,.1f} Cr "
            f"({ratio:.1f}%). {impact_desc}."
        )
        return score, explanation

    @staticmethod
    def _is_negative_context(text: str, match_pos: int, window: int = 50) -> bool:
        """Check if context around a number indicates a decline/drop rather than growth."""
        start = max(0, match_pos - window)
        end = min(len(text), match_pos + window)
        snippet = text[start:end].lower()
        neg_words = [
            "fall", "falls", "fell", "drop", "drops", "dropped", "sink", "sinks", "sank",
            "decline", "declines", "declined", "slump", "slumps", "slumped", "plunge", "plunges",
            "plunged", "crash", "crashes", "crashed", "down", "loss", "losses", "shrink",
            "shrinks", "tumble", "tumbles", "slip", "slips", "dip", "dips", "cut", "cuts",
            "drag", "drags", "hit", "hits", "lower", "deficit"
        ]
        return any(re.search(rf"\b{re.escape(w)}\b", snippet) for w in neg_words)

    def analyze(
        self,
        event: NewsEvent,
        classification: ClassificationResult,
        session: Session,
    ) -> Tuple[float, str]:
        """Compute materiality score (0-100) and rationale for a news event."""
        company = event.primary_company
        raw_cat = classification.news_category
        cat = raw_cat.value if isinstance(raw_cat, NewsCategory) else str(raw_cat)

        full_text = f"{event.primary_headline} {event.news_summary or ''}"

        if cat == NewsCategory.ORDER_WIN.value:
            return self.analyze_order_win(full_text, company)

        elif cat in (
            NewsCategory.QUARTERLY_RESULTS.value,
            NewsCategory.PROFIT_GROWTH.value,
            NewsCategory.REVENUE_GROWTH.value,
            NewsCategory.PROFIT_WARNING.value,
        ):
            # Check for percentages with direction awareness
            pct_matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*%", full_text))
            if pct_matches:
                # Find the most prominent percentage
                best_match = max(pct_matches, key=lambda m: float(m.group(1)))
                pct_val = float(best_match.group(1))
                is_decline = self._is_negative_context(full_text, best_match.start()) or (
                    classification.expected_direction == "bearish"
                    or classification.sentiment in ("NEGATIVE", "VERY_NEGATIVE")
                )

                if is_decline:
                    if pct_val >= 40.0:
                        return 92.0, f"Severe reported contraction ({pct_val:.1f}% drop/slump reported)."
                    elif pct_val >= 20.0:
                        return 85.0, f"Significant reported decline ({pct_val:.1f}% drop reported)."
                    else:
                        return 75.0, f"Reported financial contraction ({pct_val:.1f}% decline reported)."
                else:
                    if pct_val >= 50.0:
                        return 90.0, f"Exceptional reported growth ({pct_val:.1f}% surge reported)."
                    elif pct_val >= 25.0:
                        return 80.0, f"Strong reported growth ({pct_val:.1f}% increase reported)."
                    elif pct_val >= 10.0:
                        return 70.0, f"Solid reported growth ({pct_val:.1f}% growth reported)."

            if cat == NewsCategory.PROFIT_WARNING.value or classification.expected_direction == "bearish":
                return 85.0, "Quarterly financial warning or significant earnings contraction."
            return 65.0, "Quarterly financial results released with operational update."

        elif cat in (
            NewsCategory.FRAUD_OR_GOVERNANCE.value,
            NewsCategory.REGULATORY_ACTION.value,
            NewsCategory.LEGAL_ISSUE.value,
            NewsCategory.CONTRACT_CANCELLATION.value,
        ):
            return 90.0, "High negative materiality: governance or regulatory actions usually trigger immediate repricing."

        elif cat in (
            NewsCategory.BUYBACK.value,
            NewsCategory.DIVIDEND.value,
        ):
            val = self.extract_monetary_value(full_text)
            if val:
                return 75.0, f"Capital return announcement worth ₹{val:,.1f} Cr."
            return 65.0, "Shareholder capital return announcement."

        # Default fallback materiality based on classification impact
        return classification.impact_score, classification.financial_materiality or "Standard operational update."
