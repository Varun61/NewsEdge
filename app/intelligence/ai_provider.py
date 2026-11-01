"""Abstract AI provider interface for news classification and sentiment analysis."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from app.processors.company_knowledge import get_company_profile
from app.processors.nse_master import get_nse_resolver
from app.intelligence.historical_reactions import match_historical_reaction
from app.intelligence.thematic_engine import get_thematic_engine

logger = logging.getLogger("newsedge.intelligence")


@dataclass
class ClassificationResult:
    """Structured output from AI classification of a market news event."""
    company_name: str = ""
    nse_symbol: str = ""
    news_category: str = "OTHER"
    sentiment: str = "NEUTRAL"
    impact_score: float = 50.0       # 0 to 100
    confidence: float = 50.0         # 0 to 100
    financial_materiality: str = ""
    expected_direction: str = "neutral"  # "bullish", "bearish", "neutral"
    time_horizon: str = "intraday"
    news_summary: str = ""
    reasoning: str = ""
    risks: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)


SYSTEM_PROMPT = """You are an expert equity research analyst specializing in the Indian stock market (NSE/BSE).
Your task is to analyze news announcements and determine their expected intraday price impact on the relevant stock.

Rules:
1. IDENTIFY COMPANY & NSE SYMBOL: If the company is not provided or is "Unknown Company", identify the exact listed company and its official NSE ticker symbol.
   Examples of valid NSE tickers:
   - Larsen & Toubro -> LT (NOT LARSUN)
   - GAIL (India) -> GAIL (NOT DURABAR)
   - Mazagon Dock -> MAZDOCK
   - State Bank of India -> SBIN
   - Tata Power -> TATAPOWER
   - Reliance Industries -> RELIANCE
   - Bharat Electronics -> BEL
   - Bharat Heavy Electricals -> BHEL
   - Cochin Shipyard -> COCHINSHIP
   - Zomato -> ZOMATO
   - Trent -> TRENT
2. DIRECTION & SENTIMENT:
   - Positive/Bullish catalysts: Order wins, contract awards, big profit surge, capacity expansion, debt reduction, share buyback, dividend, regulatory clearances.
   - Negative/Bearish catalysts: SEBI ban/fine, ED/CBI raid, fraud/accounting probe, USFDA warning letter, auditor resignation, earnings slump, loss, contract cancellation, promoter share sale/pledge.
3. INTRADAY REALISM: Positive news may be already priced in or exhausted at open gap-up. Explicitly note potential gap-up exhaustion or profit booking risks.
4. If the news does NOT clearly relate to any specific listed Indian company, set nse_symbol to "N/A" and confidence < 30.
5. Output MUST be strictly valid JSON matching this schema:
{
  "company_name": string,
  "nse_symbol": string,
  "news_category": string (Allowed: ORDER_WIN, QUARTERLY_RESULTS, REVENUE_GROWTH, PROFIT_GROWTH, PROFIT_WARNING, ACQUISITION, MERGER, FUND_RAISE, DEBT_REDUCTION, CAPACITY_EXPANSION, MANAGEMENT_CHANGE, REGULATORY_APPROVAL, REGULATORY_ACTION, LEGAL_ISSUE, FRAUD_OR_GOVERNANCE, PROMOTER_ACTIVITY, DIVIDEND, BUYBACK, SHAREHOLDING_CHANGE, CONTRACT_CANCELLATION, BUSINESS_UPDATE, OTHER),
  "sentiment": string (Allowed: VERY_POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, VERY_NEGATIVE, MIXED),
  "impact_score": number (0 to 100),
  "confidence": number (0 to 100),
  "financial_materiality": string,
  "expected_direction": string ("bullish", "bearish", "neutral"),
  "time_horizon": string ("intraday", "short_term"),
  "news_summary": string,
  "reasoning": string,
  "risks": [string]
}
Return ONLY valid JSON.
"""


class BaseAIProvider(ABC):
    """Abstract interface for AI intelligence providers (Ollama, OpenAI, etc.)."""

    @abstractmethod
    def classify_news(
        self,
        headline: str,
        content: str,
        company_name: str,
        nse_symbol: str,
        source_urls: list[str],
        additional_context: Optional[str] = None,
    ) -> ClassificationResult:
        """Analyze a single news event and return structured classification."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the AI backend is currently reachable."""
        pass

    def _heuristic_fallback(
        self, headline: str, company_name: str, nse_symbol: str, source_urls: list[str]
    ) -> ClassificationResult:
        """High-precision rule-based evaluation when LLM is unavailable or for fast-path routing."""
        h_lower = headline.lower()
        resolver = get_nse_resolver()

        # If symbol is unknown, resolve via NSEStockResolver
        resolved_sym = nse_symbol
        resolved_name = company_name
        match_confidence = 80.0
        if not resolved_sym or resolved_sym in ("UNKNOWN", "N/A", ""):
            res = resolver.resolve_from_text(headline)
            if res:
                resolved_sym = res["symbol"]
                resolved_name = res["name"]
                match_confidence = float(res.get("confidence", 80.0))
            else:
                match_confidence = 35.0

        # Extract numerical cues for dynamic impact scaling
        pct_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", headline)
        pct_val = max([float(p) for p in pct_matches]) if pct_matches else 0.0

        # Extract monetary values
        cr_matches = re.findall(r"(?:(?:rs\.?|inr|₹)\s*)?([\d,]+(?:\.\d+)?)\s*(?:crore|cr)\b", headline, re.IGNORECASE)
        cr_val = max([float(c.replace(",", "")) for c in cr_matches]) if cr_matches else 0.0

        # Defaults
        cat: Optional[str] = None
        sent = "NEUTRAL"
        direction = "neutral"
        impact = 50.0
        materiality = "Routine business announcement or sector commentary."
        risks = ["Lack of distinct price catalyst"]

        # 1. Strong Bearish Triggers (High Severity Intraday Downside)
        if any(w in h_lower for w in ["sebi", "penalty", "raid", "ed summons", "cbi probe", "fraud", "scam", "nclt insolvency", "warning letter", "form 483", "import alert", "auditor resign"]):
            cat = "REGULATORY_ACTION" if ("sebi" in h_lower or "penalty" in h_lower) else "FRAUD_OR_GOVERNANCE"
            sent = "VERY_NEGATIVE"
            direction = "bearish"
            impact = 88.0 + (5.0 if cr_val > 100 else 0.0)
            materiality = "Severe regulatory/governance risk with immediate intraday downside selling pressure."
            risks = ["Panic selling at open", "Prolonged institutional derating", "Reputational overhang"]
        elif any(w in h_lower for w in ["loss", "profit slumps", "net drops", "profit falls", "downgrade", "target cut", "resigns", "steps down"]):
            cat = "PROFIT_WARNING" if ("profit" in h_lower or "net" in h_lower or "loss" in h_lower) else "MANAGEMENT_CHANGE"
            sent = "NEGATIVE"
            direction = "bearish"
            impact = 75.0 + (10.0 if pct_val >= 35 else 5.0 if pct_val >= 15 else 0.0)
            materiality = f"Disappointing operating performance ({pct_val:.1f}% drop)" if pct_val else "Disappointing operating performance or leadership departure."
            risks = ["Gap-down open", "Negative earnings revision", "Further sell-off below key support"]

        # 2. Strong Bullish Triggers (High Conviction Intraday Upside)
        elif any(w in h_lower for w in ["order", "contract", "bags", "wins", "awarded", "l1 bidder", "secures deal"]):
            cat = "ORDER_WIN"
            sent = "POSITIVE"
            direction = "bullish"
            base_impact = 80.0
            if cr_val >= 5000:
                base_impact = 92.0
            elif cr_val >= 1000:
                base_impact = 86.0
            elif cr_val and cr_val < 100:
                base_impact = 72.0
            impact = base_impact
            materiality = f"Order win worth ₹{cr_val:,.1f} Cr strengthening revenue visibility." if cr_val else "New revenue order win strengthening future earnings visibility."
            risks = ["Gap-up exhaustion / sell-on-news", "Execution timeline delays", "Margin pressures"]
        elif any(w in h_lower for w in ["profit up", "profit jumps", "profit surges", "net doubles", "q4 profit", "q3 profit", "q2 profit", "q1 profit", "revenue rises"]):
            cat = "PROFIT_GROWTH"
            sent = "POSITIVE"
            direction = "bullish"
            impact = 78.0 + (12.0 if pct_val >= 50 else 7.0 if pct_val >= 25 else 0.0)
            materiality = f"Quarterly profit expansion ({pct_val:.1f}% surge) driving earnings momentum." if pct_val else "Strong quarterly financial expansion driving earnings momentum."
            risks = ["Already priced-in expectations", "Profit taking after initial surge", "General market headwinds"]
        elif any(w in h_lower for w in ["buyback", "dividend", "bonus issue", "capacity expansion", "commissions plant", "fda approval", "usfda approval"]):
            cat = "BUYBACK" if "buyback" in h_lower else "CAPACITY_EXPANSION" if "plant" in h_lower else "REGULATORY_APPROVAL"
            sent = "POSITIVE"
            direction = "bullish"
            impact = 76.0 + (6.0 if cr_val >= 500 else 0.0)
            materiality = "Shareholder value accretive action or strategic growth milestone."
            risks = ["Limited liquidity follow-through", "Broader sector weakness"]

        # 3. Check Thematic & Sectoral Catalysts for known stock
        thematic_engine = get_thematic_engine()
        thematic_fit = thematic_engine.evaluate_company_thematic_fit(resolved_sym, headline) if resolved_sym else None

        if thematic_fit:
            f_dir, f_score, f_exp = thematic_fit
            cat = "REGULATORY_ACTION" if f_dir == "bearish" else "BUSINESS_UPDATE"
            sent = "NEGATIVE" if f_dir == "bearish" else "POSITIVE"
            direction = f_dir
            impact = f_score
            materiality = f_exp
            risks = ["Policy implementation timeframe", "Sector-wide sentiment shift"]
        elif cat is None:
            cat = "BUSINESS_UPDATE"
            sent = "NEUTRAL"
            direction = "neutral"
            impact = 50.0
            materiality = "Routine business announcement or sector commentary."
            risks = ["Lack of distinct price catalyst"]

        # Check empirical historical reaction patterns
        hist_profile = match_historical_reaction(headline)
        hist_note = ""
        if hist_profile:
            match_confidence = max(match_confidence, hist_profile.directional_conviction_pct)
            hist_note = f" Historical backtest ({hist_profile.catalyst_type}): median return {hist_profile.median_intraday_return_pct:+.1f}%, win-rate {hist_profile.directional_conviction_pct:.0f}%."

        impact = max(10.0, min(98.0, impact))

        return ClassificationResult(
            company_name=resolved_name,
            nse_symbol=resolved_sym,
            news_category=cat or "BUSINESS_UPDATE",
            sentiment=sent,
            impact_score=round(impact, 1),
            confidence=round(match_confidence, 1) if resolved_sym and resolved_sym != "UNKNOWN" else 35.0,
            financial_materiality=materiality,
            expected_direction=direction,
            time_horizon="intraday",
            news_summary=headline,
            reasoning=f"Classified via quantitative catalyst engine: {direction.upper()} catalyst identified.{hist_note}",
            risks=risks,
            source_urls=source_urls,
        )
