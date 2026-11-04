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


SYSTEM_PROMPT = """You are an institutional equity research analyst for the Indian stock market (NSE/BSE).
Your task: analyze news and determine INTRADAY price impact on the relevant NSE-listed stock.

━━━ STEP 1: IDENTIFY STOCK ━━━
Map the news to exactly ONE listed NSE equity. Use the official NSE ticker (e.g. LT, RELIANCE, SBIN, TATASTEEL).
If multiple companies are mentioned, pick the PRIMARY subject. If no specific listed company is identifiable, set nse_symbol to "N/A" and confidence < 25.
Common ticker corrections: LARSEN/LARSUN→LT, DURABAR/GAILINDIA→GAIL.

━━━ STEP 2: SCORE impact_score (0-100) ━━━
This is the expected INTRADAY price move magnitude. Be conservative — most news has limited intraday impact.
Use these anchors:
  90-100 → SEBI ban/trading halt, USFDA import alert, confirmed fraud/ED raid, auditor resignation. Expect 8-15%+ move.
  78-89  → Order win >10% of annual revenue, quarterly profit surge >50% YoY, debt default, NPA classification, promoter pledge call. Expect 4-8% move.
  65-77  → Order win 2-10% of revenue, quarterly profit +25-50%, management departure (CEO/CFO), credit rating downgrade, NCLT filing. Expect 2-4% move.
  50-64  → Routine order win <2% of revenue, profit growth 10-25%, MoU signing, capacity expansion announcement, capacity commissioning. Expect 1-2% move.
  35-49  → AGM notice, shareholding update, analyst meeting, dividend under ₹5/share, minor management change. Expect <1% or no meaningful move.
  10-34  → Sector commentary, general business update, no company-specific catalyst. Expect 0% move.

━━━ STEP 3: SCORE confidence (0-100) ━━━
This is your conviction that the news is REAL, STOCK-SPECIFIC, and MATERIAL.
Use these anchors:
  85-95 → Official exchange filing (BSE/NSE), confirmed SEBI order, audited quarterly results.
  70-84 → Named company in headline with confirmed order value or specific ₹ figure.
  55-69 → Company named but order value unspecified, or article is a secondary report.
  40-54 → Company implied but not named directly, or article is from a blog/opinion piece.
  25-39 → General sector article, analyst speculation, or company identification is uncertain.
  10-24 → News does not relate to a specific listed stock.

━━━ STEP 4: DIRECTION & CATEGORY ━━━
Bullish catalysts: order wins, profit surge (>25%), revenue growth, buyback, dividend, regulatory approval, regulatory fee cuts/relaxation of compliance norms, debt reduction, capacity expansion.
Bearish catalysts: SEBI action/penalties, ED/CBI/fraud probe, USFDA warning/import alert, auditor resignation, loss, profit warning, NPA, credit downgrade, contract cancellation, promoter pledging/selling.
IMPORTANT:
- Regulatory fee cuts (e.g. IRDAI cutting processing fees, SEBI reducing transaction charges) or approvals (e.g. CCI approving M&A) are BULLISH/POSITIVE (operational cost savings/business expansion), NOT bearish!
- If impact_score > 75, you are placing this stock in the TOP watchlist. Only do this for TRULY MATERIAL events. When in doubt, score lower.

━━━ STEP 5: REALISM CHECK ━━━
- Profit growth under 15% (especially single digits e.g. 6%) when revenue is high shows margin compression = impact_score ≤ 55
- Routine quarterly results with <10% growth = impact_score ≤ 55
- Anil Ambani (ADAG, Reliance Power, Reliance Infra) legal/enforcement actions must NOT be assigned to Mukesh Ambani's Reliance Industries (RELIANCE)
- Headlines describing past market rallies (e.g. "shares surge 17%", "rallied 80% from IPO") reflect ALREADY-PRICED past momentum = impact_score ≤ 50, expected_direction = neutral
- MoU/LoI (letter of intent, not confirmed order) = impact_score ≤ 60, confidence ≤ 60
- Order win with no ₹ value stated = impact_score ≤ 65
- Any news where the company is mentioned only incidentally = confidence ≤ 40
- Gap-up exhaustion: note if positive news may already be priced in

━━━ OUTPUT FORMAT ━━━
Return ONLY valid compact JSON (no markdown, no extra text):
{
  "company_name": string,
  "nse_symbol": string,
  "news_category": string (ORDER_WIN|QUARTERLY_RESULTS|REVENUE_GROWTH|PROFIT_GROWTH|PROFIT_WARNING|ACQUISITION|MERGER|FUND_RAISE|DEBT_REDUCTION|CAPACITY_EXPANSION|MANAGEMENT_CHANGE|REGULATORY_APPROVAL|REGULATORY_ACTION|LEGAL_ISSUE|FRAUD_OR_GOVERNANCE|PROMOTER_ACTIVITY|DIVIDEND|BUYBACK|SHAREHOLDING_CHANGE|CONTRACT_CANCELLATION|BUSINESS_UPDATE|OTHER),
  "sentiment": string (VERY_POSITIVE|POSITIVE|NEUTRAL|NEGATIVE|VERY_NEGATIVE|MIXED),
  "impact_score": number,
  "confidence": number,
  "financial_materiality": string,
  "expected_direction": string (bullish|bearish|neutral),
  "time_horizon": string (intraday|short_term),
  "news_summary": string (max 15 words),
  "reasoning": string (max 25 words),
  "risks": [string]
}
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
        # Start conservative — confidence is earned, not assumed
        match_confidence = 72.0
        if not resolved_sym or resolved_sym in ("UNKNOWN", "N/A", ""):
            res = resolver.resolve_from_text(headline)
            if res:
                resolved_sym = res["symbol"]
                resolved_name = res["name"]
                match_confidence = float(res.get("confidence", 62.0))  # text-resolved = less certain
            else:
                match_confidence = 28.0  # truly unknown

        # Extract numerical cues for dynamic impact scaling
        pct_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", headline)
        pct_val = max([float(p) for p in pct_matches]) if pct_matches else 0.0

        # Extract specific profit percentage vs revenue percentage
        profit_pct_match = re.search(r"(?:net\s+)?profit\s+(?:rises|jumps|surges|up|grows)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", headline, re.IGNORECASE)
        revenue_pct_match = re.search(r"(?:revenue|sales)\s+(?:rises|jumps|surges|up|grows)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%", headline, re.IGNORECASE)
        profit_pct = float(profit_pct_match.group(1)) if profit_pct_match else None
        revenue_pct = float(revenue_pct_match.group(1)) if revenue_pct_match else None

        # Extract monetary values (crores)
        cr_matches = re.findall(r"(?:(?:rs\.?|inr|₹)\s*)?([\d,]+(?:\.\d+)?)\s*(?:crore|cr)\b", headline, re.IGNORECASE)
        cr_val = max([float(c.replace(",", "")) for c in cr_matches]) if cr_matches else 0.0

        # Defaults
        cat: Optional[str] = None
        sent = "NEUTRAL"
        direction = "neutral"
        impact = 50.0
        materiality = "Routine business announcement or sector commentary."
        risks = ["Lack of distinct price catalyst"]

        # ── 0. Deregulatory Relief / Fee Cuts ───────────────────────────────────
        is_regulatory_relief = (
            bool(re.search(r"\b(?:cuts?|slashes?|reduces?|lowers?)\b.*\b(?:processing\s+|application\s+|compliance\s+|registration\s+)?fee", h_lower))
            or any(
                phrase in h_lower
                for phrase in [
                    "fee cut", "processing fee cut", "fee reduction",
                    "relaxes norm", "eases norm", "eases rule", "relaxes rule", "compliance relief"
                ]
            )
        )

        # ── 1. Severe Bearish Triggers ──────────────────────────────────────────
        SEVERE_BEARISH = [
            "sebi ban", "sebi suspension", "sebi order", "sebi penalty", "sebi fine",
            "usfda import alert", "usfda warning letter", "form 483", "import alert",
            "ed raid", "ed summons", "cbi probe", "enforcement directorate",
            "auditor resign", "auditor quits", "statutory auditor",
            "nclt insolvency", "insolvency petition", "fraud", "scam", "embezzle",
        ]
        MODERATE_BEARISH = [
            "net loss", "quarterly loss", "profit falls", "profit slumps", "profit drops",
            "net drops", "revenue declines", "sales fall", "margin contracts",
            "npa", "non-performing asset", "credit rating downgrade", "rating cut",
            "promoter pledge", "promoter pledging", "pledge invoked", "margin call",
            "debt covenant", "loan default", "default on",
            "contract cancelled", "contract cancellation", "order cancelled",
            "ceo resigns", "md resigns", "cfo resigns", "steps down", "downgrade", "target cut",
        ]

        if is_regulatory_relief:
            cat = "REGULATORY_APPROVAL"
            sent = "POSITIVE"
            direction = "bullish"
            impact = 65.0
            match_confidence = max(match_confidence, 72.0)
            materiality = "Deregulatory fee reduction or administrative compliance easing reducing operational overhead."
            risks = ["Marginal financial impact", "Sector-wide rather than company-specific"]

        elif any(w in h_lower for w in SEVERE_BEARISH):
            cat = "REGULATORY_ACTION" if any(x in h_lower for x in ["sebi", "penalty", "fine", "usfda"]) else "FRAUD_OR_GOVERNANCE"
            sent = "VERY_NEGATIVE"
            direction = "bearish"
            impact = 88.0 + (5.0 if cr_val > 100 else 0.0)
            match_confidence = max(match_confidence, 82.0)  # confirmed regulatory = high conviction
            materiality = "Severe regulatory/governance risk with immediate intraday downside selling pressure."
            risks = ["Panic selling at open", "Prolonged institutional derating", "Reputational overhang"]

        elif any(w in h_lower for w in MODERATE_BEARISH):
            cat = (
                "PROFIT_WARNING" if any(x in h_lower for x in ["profit", "net", "loss", "npa", "revenue"])
                else "MANAGEMENT_CHANGE" if any(x in h_lower for x in ["resign", "steps down"])
                else "REGULATORY_ACTION" if any(x in h_lower for x in ["downgrade", "rating"])
                else "LEGAL_ISSUE"
            )
            sent = "NEGATIVE"
            direction = "bearish"
            impact = 74.0 + (10.0 if pct_val >= 35 else 6.0 if pct_val >= 15 else 0.0)
            # Known symbol + confirmed bad metric = decent confidence
            if pct_val >= 15:
                match_confidence = max(match_confidence, 70.0)
            materiality = f"Disappointing operating performance ({pct_val:.1f}% drop)" if pct_val else "Disappointing operating performance or governance concern."
            risks = ["Gap-down open", "Negative earnings revision", "Further sell-off below key support"]

        # ── 2. Strong Bullish Triggers ──────────────────────────────────────────
        ORDER_KEYWORDS = [
            "order win", "wins order", "bags order", "bags contract", "secures order", "secures deal",
            "awarded contract", "awarded order", "l1 bidder", "receives order", "gets order",
            "signs contract", "gets nod", "receives approval", "completes acquisition",
        ]
        PROFIT_KEYWORDS = [
            "profit up", "profit jumps", "profit surges", "profit doubles", "profit rises",
            "net profit up", "net profit jumps", "net doubles", "q4 profit", "q3 profit",
            "q2 profit", "q1 profit", "revenue rises", "revenue surges", "sales surge",
            "ebitda jumps", "ebitda rises",
        ]
        SHAREHOLDER_BULLISH = [
            "buyback", "bonus issue", "stock split", "special dividend",
            "fda approval", "usfda approval", "gets usfda", "receives fda",
            "capacity expansion", "commissions plant", "inaugurates plant",
        ]
        GENERAL_BULLISH = [
            "signs mou", "mou signed", "strategic partnership", "debt free",
            "prepays debt", "acquires stake", "qip launch", "preferential allotment",
        ]

        if any(w in h_lower for w in ORDER_KEYWORDS):
            cat = "ORDER_WIN"
            sent = "POSITIVE"
            direction = "bullish"
            if cr_val >= 5000:
                impact = 92.0
                match_confidence = max(match_confidence, 85.0)
            elif cr_val >= 1000:
                impact = 86.0
                match_confidence = max(match_confidence, 80.0)
            elif cr_val >= 100:
                impact = 78.0
                match_confidence = max(match_confidence, 75.0)
            elif cr_val > 0:
                impact = 68.0
                match_confidence = max(match_confidence, 70.0)
            else:
                impact = 60.0  # no ₹ value = lower conviction
                match_confidence = min(match_confidence, 58.0)  # cap unquantified order
            materiality = (
                f"Order win worth ₹{cr_val:,.1f} Cr strengthening revenue visibility."
                if cr_val
                else "Order win announced (value undisclosed); limited impact without ₹ figure."
            )
            risks = ["Gap-up exhaustion / sell-on-news", "Execution timeline delays", "Margin pressures"]

        elif any(w in h_lower for w in PROFIT_KEYWORDS):
            cat = "PROFIT_GROWTH"
            direction = "bullish"
            effective_pct = profit_pct if profit_pct is not None else pct_val

            if profit_pct is not None and profit_pct < 15.0:
                # Modest profit growth (especially when revenue is high) signals margin compression
                sent = "NEUTRAL"
                impact = 56.0
                match_confidence = min(match_confidence, 60.0)
                materiality = f"Modest profit growth ({profit_pct:.1f}%); potential margin compression vs expectations."
                risks = ["Margin compression", "Profit booking on subdued bottom-line growth"]
            else:
                sent = "VERY_POSITIVE" if effective_pct >= 50 else "POSITIVE"
                impact = 76.0 + (12.0 if effective_pct >= 50 else 7.0 if effective_pct >= 25 else 0.0)
                if effective_pct >= 20:
                    match_confidence = max(match_confidence, 78.0)
                materiality = (
                    f"Quarterly profit expansion ({effective_pct:.1f}% surge) driving earnings momentum."
                    if effective_pct
                    else "Strong quarterly financial expansion driving earnings momentum."
                )
                risks = ["Already priced-in expectations", "Profit taking after initial surge", "General market headwinds"]
            risks = ["Already priced-in expectations", "Profit taking after initial surge", "General market headwinds"]

        elif any(w in h_lower for w in SHAREHOLDER_BULLISH):
            cat = (
                "BUYBACK" if "buyback" in h_lower
                else "REGULATORY_APPROVAL" if any(x in h_lower for x in ["fda", "usfda"])
                else "CAPACITY_EXPANSION"
            )
            sent = "VERY_POSITIVE" if any(x in h_lower for x in ["fda", "usfda", "buyback"]) else "POSITIVE"
            direction = "bullish"
            impact = 78.0 + (6.0 if cr_val >= 500 else 0.0)
            if any(x in h_lower for x in ["fda", "usfda"]):
                match_confidence = max(match_confidence, 80.0)
            materiality = "Shareholder value accretive action or strategic regulatory milestone."
            risks = ["Limited liquidity follow-through", "Broader sector weakness"]

        elif any(w in h_lower for w in GENERAL_BULLISH):
            cat = (
                "ACQUISITION" if any(x in h_lower for x in ["acquires", "acquisition"])
                else "FUND_RAISE" if any(x in h_lower for x in ["qip", "allotment"])
                else "BUSINESS_UPDATE"
            )
            sent = "POSITIVE"
            direction = "bullish"
            impact = 60.0
            match_confidence = min(match_confidence, 60.0)  # MoU/LoI = lower certainty
            materiality = "Strategic business development; outcome-dependent on deal confirmation."
            risks = ["MoU/LoI may not result in confirmed deal", "Execution timeline", "Market sentiment"]

        # ── 3. Routine Low-Signal Events — downgrade confidence ─────────────────
        ROUTINE_EVENTS = [
            "agm", "annual general meeting", "board meeting", "board meets",
            "investor presentation", "analyst meet", "shareholding pattern",
            "regulatory filing", "corporate action date",
        ]
        if any(w in h_lower for w in ROUTINE_EVENTS) and cat is None:
            cat = "BUSINESS_UPDATE"
            sent = "NEUTRAL"
            direction = "neutral"
            impact = 35.0
            match_confidence = min(match_confidence, 42.0)
            materiality = "Routine corporate governance event with negligible intraday impact."
            risks = ["No meaningful catalyst"]

        # ── 4. Thematic & Sectoral Catalysts ────────────────────────────────────
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

        # ── 5. Historical Pattern Boost ──────────────────────────────────────────
        hist_profile = match_historical_reaction(headline)
        hist_note = ""
        if hist_profile:
            match_confidence = max(match_confidence, hist_profile.directional_conviction_pct)
            hist_note = f" Historical backtest ({hist_profile.catalyst_type}): median return {hist_profile.median_intraday_return_pct:+.1f}%, win-rate {hist_profile.directional_conviction_pct:.0f}%."

        impact = max(10.0, min(98.0, impact))
        match_confidence = max(10.0, min(95.0, match_confidence))

        return ClassificationResult(
            company_name=resolved_name,
            nse_symbol=resolved_sym,
            news_category=cat or "BUSINESS_UPDATE",
            sentiment=sent,
            impact_score=round(impact, 1),
            confidence=round(match_confidence, 1) if resolved_sym and resolved_sym != "UNKNOWN" else 28.0,
            financial_materiality=materiality,
            expected_direction=direction,
            time_horizon="intraday",
            news_summary=headline,
            reasoning=f"Heuristic catalyst engine: {direction.upper()} signal detected.{hist_note}",
            risks=risks,
            source_urls=source_urls,
        )
