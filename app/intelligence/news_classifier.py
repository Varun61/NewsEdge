"""High-level news event classifier orchestrating AI and scoring.

Generic mode: ALL news events are processed regardless of whether their company
is already in the DB. Entity resolution and Ollama identify the company from the article text,
and new Company records are created on the fly when needed.

Performance optimization:
- Sequential LLM access via a Mutex Lock to avoid Ollama queue timeouts on CPU.
- High-catalyst corporate news receives focused AI analysis.
- Non-catalyst or general updates are rapidly routed through high-precision heuristics.
- Concurrent workers via ThreadPoolExecutor with per-thread SQLAlchemy sessions for I/O.
"""

from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from sqlalchemy.orm import Session, sessionmaker

from app.database.models import (
    NewsCategory,
    NewsEvent,
    Sentiment,
    StockAnalysis,
)
from app.database.repository import Repository
from app.intelligence.ai_provider import BaseAIProvider, ClassificationResult
from app.intelligence.materiality_analyzer import MaterialityAnalyzer
from app.intelligence.scoring_engine import ScoringEngine
from app.processors.nse_master import get_nse_resolver

logger = logging.getLogger("newsedge.intelligence.classifier")

MAX_WORKERS = 3
INVALID_SYMBOLS = {"N/A", "NA", "UNKNOWN", "", "NSE", "BSE", "NIFTY", "SENSEX", "NONE", "INDIA", "MARKET"}

# LLM call concurrency lock (Ollama CPU server only has 1 active slot)
_LLM_LOCK = threading.Lock()

CATALYST_PATTERNS = [
    r"\b(order|contract|bags|wins|secures|awarded|l1 bidder|pact)\b",
    r"\b(profit|revenue|results|q[1-4]|ebitda|margin|loss|sales|quarterly)\b",
    r"\b(acquisition|acquires|merger|stake|buyout|jv|joint venture|demerger)\b",
    r"\b(dividend|buyback|bonus|split|rights issue|qip|fund raise|debt|prepayment)\b",
    r"\b(sebi|usfda|fda|warning letter|form 483|eir|penalty|raid|fraud|probe|nclt|cbi)\b",
    r"\b(plant|facility|capacity|expansion|commission|launch|inaugurate)\b",
    r"\b(upgrade|downgrade|target price|rating)\b",
    r"\b(resigns|appointed|resignation|steps down|ceo|cfo|md)\b",
    r"\b(share|stock|rally|surge|slump|plunge|crash|jumps|tumbles)\b",
    r"[₹]|rs\.?|\bcrore\b|\bcr\b|\blakh\b",
]


def _clean_symbol(raw: str) -> str:
    """Normalise an NSE symbol returned by the LLM."""
    sym = re.sub(r"[^A-Z0-9\-]", "", raw.upper().strip())
    # Correct known false mappings
    if sym in ("LARSUN", "LARSEN"):
        return "LT"
    if sym in ("DURABAR", "GAILINDIA"):
        return "GAIL"
    return sym


def _has_catalyst_signals(headline: str, text: str) -> bool:
    """Return True if the news text contains corporate catalyst triggers."""
    combined = (headline + " " + text[:300]).lower()
    return any(re.search(pat, combined) for pat in CATALYST_PATTERNS)


class NewsClassifier:
    """Coordinates AI extraction, materiality evaluation, and scoring for NewsEvents."""

    def __init__(
        self,
        ai_provider: BaseAIProvider,
        scoring_engine: ScoringEngine,
        materiality_analyzer: Optional[MaterialityAnalyzer] = None,
    ):
        self.ai = ai_provider
        self.scoring = scoring_engine
        self.materiality = materiality_analyzer or MaterialityAnalyzer()
        self._resolver = get_nse_resolver()

    def process_event(
        self,
        event: NewsEvent,
        session: Session,
    ) -> StockAnalysis | None:
        """Classify, evaluate materiality, score, and update NewsEvent record."""
        company = event.primary_company
        comp_name = company.company_name if company else "Unknown Company"
        symbol = company.nse_symbol if company else "UNKNOWN"

        source_urls = [
            link.article.article_url for link in event.article_links if link.article
        ]
        combined_text = " ".join(
            (link.article.extracted_text or link.article.raw_content or "")[:350]
            for link in event.article_links
            if link.article
        )

        # Pre-resolve company using NSEStockResolver if missing
        if symbol == "UNKNOWN" or not event.primary_company_id:
            resolved_dict = self._resolver.resolve_from_text(event.primary_headline, combined_text)
            if resolved_dict:
                symbol = resolved_dict["symbol"]
                comp_name = resolved_dict["name"]

        # Check for Sector-Wide Thematic Policy Catalysts (e.g. Railway capex, Insurance commission cuts, APM gas cuts)
        from app.intelligence.thematic_engine import get_thematic_engine
        thematic_engine = get_thematic_engine()
        thematic_matches = thematic_engine.detect_sector_catalysts(event.primary_headline, combined_text)

        if thematic_matches and (symbol == "UNKNOWN" or not event.primary_company_id):
            primary_thematic = thematic_matches[0]
            symbol = primary_thematic.symbol
            comp_name = primary_thematic.company_name
            logger.info("Event #%d mapped to sector beneficiary/casualty: %s (%s) [%s]", event.id, comp_name, symbol, primary_thematic.theme_title)

        # Filter out macro noise or unmapped general news early
        from app.processors.deduplicator import is_macro_noise
        if symbol == "UNKNOWN" and not event.primary_company_id and not thematic_matches:
            if is_macro_noise(event.primary_headline) or not _has_catalyst_signals(event.primary_headline, combined_text):
                logger.debug("Skipping unmapped general event #%d: %s", event.id, event.primary_headline[:50])
                event.is_processed = True
                return None

        is_catalyst = _has_catalyst_signals(event.primary_headline, combined_text) or bool(thematic_matches)
        
        # High confidence heuristic pattern for known stocks
        clear_heuristic_trigger = (symbol != "UNKNOWN") and (bool(thematic_matches) or any(
            re.search(pat, event.primary_headline.lower())
            for pat in [
                r"\b(profit\s+(?:jumps|surges|doubles|rises|up)|order\s+win|bags\s+(?:contract|order|deal)|secures\s+order)\b",
                r"\b(sebi\s+(?:penalty|ban|fine)|usfda\s+warning|profit\s+(?:falls|slumps|drops))\b",
            ]
        ))

        use_ai = (not clear_heuristic_trigger and is_catalyst) or (symbol == "UNKNOWN" and is_catalyst)

        if thematic_matches:
            primary_thematic = thematic_matches[0]
            classification = ClassificationResult(
                company_name=comp_name,
                nse_symbol=symbol,
                news_category="REGULATORY_ACTION" if primary_thematic.direction == "bearish" else "ORDER_WIN",
                sentiment="VERY_NEGATIVE" if primary_thematic.direction == "bearish" else "VERY_POSITIVE",
                impact_score=primary_thematic.impact_score,
                confidence=primary_thematic.confidence,
                financial_materiality=f"[{primary_thematic.theme_title}] {primary_thematic.rationale}",
                expected_direction=primary_thematic.direction,
                time_horizon="intraday",
                news_summary=event.primary_headline,
                reasoning=f"Sector-wide thematic policy catalyst: {primary_thematic.theme_title}. Stock sensitivity: {primary_thematic.direction.upper()}.",
                risks=["Policy implementation timeline", "Sector sentiment shift"],
                source_urls=source_urls,
            )
            # Propagate secondary basket stocks in background
            import hashlib
            for secondary in thematic_matches[1:4]:
                sec_sym = secondary.symbol
                sec_name = secondary.company_name
                sec_comp = Repository.get_company_by_symbol(session, sec_sym)
                if not sec_comp:
                    info = self._resolver.get_company_info(sec_sym) or {}
                    sec_comp = Repository.create_company(
                        session,
                        nse_symbol=sec_sym,
                        company_name=info.get("name") or sec_name,
                        sector=info.get("sector", "Diversified"),
                        industry=info.get("industry", "Diversified"),
                        annual_revenue=info.get("revenue", 5000.0),
                        is_active=True,
                    )
                    session.flush()

                sec_hash = hashlib.sha256(f"{sec_sym}|{event.primary_headline[:50]}".encode()).hexdigest()
                existing_ev = Repository.get_event_by_hash(session, sec_hash)
                if not existing_ev and sec_comp:
                    try:
                        sec_cat = NewsCategory.REGULATORY_ACTION if secondary.direction == "bearish" else NewsCategory.ORDER_WIN
                        sec_sent = Sentiment.VERY_NEGATIVE if secondary.direction == "bearish" else Sentiment.VERY_POSITIVE
                        new_sec_event = Repository.create_event(
                            session=session,
                            primary_headline=event.primary_headline,
                            event_hash=sec_hash,
                            primary_company_id=sec_comp.id,
                            news_category=sec_cat,
                            sentiment=sec_sent,
                            impact_score=secondary.impact_score,
                            confidence=secondary.confidence,
                            financial_materiality=f"[{secondary.theme_title}] {secondary.rationale}",
                            expected_direction=secondary.direction,
                            time_horizon="intraday",
                            news_summary=event.primary_headline,
                            reasoning=f"Sector-wide thematic policy catalyst: {secondary.theme_title}.",
                            is_processed=True,
                        )
                        sec_class = ClassificationResult(
                            company_name=sec_comp.company_name,
                            nse_symbol=sec_sym,
                            news_category=sec_cat.value,
                            sentiment=sec_sent.value,
                            impact_score=secondary.impact_score,
                            confidence=secondary.confidence,
                            financial_materiality=f"[{secondary.theme_title}] {secondary.rationale}",
                            expected_direction=secondary.direction,
                        )
                        self.scoring.score_event(new_sec_event, sec_class, secondary.impact_score, session)
                    except Exception as exc:
                        logger.debug("Secondary thematic propagation skip: %s", exc)

        elif use_ai and self.ai.is_available():
            logger.info("Classifying event #%d via AI for %s (%s)", event.id, comp_name, symbol)
            # Acquire lock so only one thread queries Ollama at a time
            with _LLM_LOCK:
                classification = self.ai.classify_news(
                    headline=event.primary_headline,
                    content=combined_text,
                    company_name=comp_name,
                    nse_symbol=symbol,
                    source_urls=source_urls,
                )
        else:
            logger.debug("Fast-path heuristic evaluation for event #%d (%s)", event.id, comp_name)
            classification = self.ai._heuristic_fallback(  # type: ignore[attr-defined]
                event.primary_headline, comp_name, symbol, source_urls
            )

        # Dynamic company resolution: verify against official NSE equity universe
        if not event.primary_company_id:
            ai_symbol = _clean_symbol(classification.nse_symbol or "")
            ai_name = (classification.company_name or "").strip()

            # Ensure symbol is an officially traded NSE equity stock
            if not self._resolver.is_valid_nse_symbol(ai_symbol):
                # 1. Try symbol guess
                guess = self._resolver.resolve_from_symbol_guess(ai_symbol)
                if guess and self._resolver.is_valid_nse_symbol(guess["symbol"]):
                    ai_symbol = guess["symbol"]
                    ai_name = guess["name"]
                else:
                    # 2. Try resolving from headline/text
                    res = self._resolver.resolve_from_text(event.primary_headline, combined_text)
                    if res and self._resolver.is_valid_nse_symbol(res["symbol"]):
                        ai_symbol = res["symbol"]
                        ai_name = res["name"]
                    elif ai_name:
                        # 3. Try resolving from AI company name
                        res_name = self._resolver.resolve_from_text(ai_name)
                        if res_name and self._resolver.is_valid_nse_symbol(res_name["symbol"]):
                            ai_symbol = res_name["symbol"]
                            ai_name = res_name["name"]

                if not self._resolver.is_valid_nse_symbol(ai_symbol):
                    # Exclude unlisted entities, publishers, or general commentary
                    logger.debug(
                        "Excluding unlisted or invalid symbol '%s' for event #%d",
                        ai_symbol,
                        event.id,
                    )
                    event.is_processed = True
                    return None

            # Grounding check: ensure company or ticker actually appears in the article text
            comp_info = self._resolver.get_company_info(ai_symbol)
            comp_official_name = (comp_info.get("name") if comp_info else "") or ai_name
            full_event_text = f"{event.primary_headline} {combined_text}"
            if not self._resolver.verify_mention_presence(ai_symbol, comp_official_name, full_event_text):
                logger.debug(
                    "Excluding ungrounded stock '%s' (%s) not mentioned in text for event #%d",
                    ai_symbol,
                    comp_official_name,
                    event.id,
                )
                event.is_processed = True
                return None

            resolved = None
            if ai_symbol and self._resolver.is_valid_nse_symbol(ai_symbol):
                # 1. Exact symbol match in DB
                resolved = Repository.get_company_by_symbol(session, ai_symbol)

                # 2. Company alias match in DB
                if not resolved and ai_name:
                    resolved = Repository.find_company_by_alias(session, ai_name)

                # 3. Create verified Company record from official NSE master info
                if not resolved:
                    info = self._resolver.get_company_info(ai_symbol) or {}
                    official_name = info.get("name") or ai_name
                    try:
                        resolved = Repository.create_company(
                            session,
                            nse_symbol=ai_symbol,
                            company_name=official_name,
                            is_active=True,
                            sector=info.get("sector", "Diversified"),
                            industry=info.get("industry", "Diversified"),
                            annual_revenue=info.get("revenue", 5000.0),
                        )
                        session.flush()
                        logger.info(
                            "Registered verified NSE stock: %s (%s) for event #%d",
                            official_name,
                            ai_symbol,
                            event.id,
                        )
                    except Exception as exc:
                        logger.warning("Could not register company %s: %s", ai_symbol, exc)
                        resolved = None

            if resolved:
                event.primary_company_id = resolved.id
                event.company_mentions = {
                    "ai_identified": True,
                    "symbol": resolved.nse_symbol,
                    "name": resolved.company_name,
                }
            else:
                # General commentary without identifiable entity
                event.is_processed = True
                return None

        # Materiality Analysis
        mat_score, mat_explanation = self.materiality.analyze(event, classification, session)

        # Update NewsEvent record
        try:
            event.news_category = NewsCategory(classification.news_category)
        except ValueError:
            event.news_category = NewsCategory.OTHER

        try:
            event.sentiment = Sentiment(classification.sentiment)
        except ValueError:
            event.sentiment = Sentiment.NEUTRAL

        event.impact_score = classification.impact_score
        event.confidence = classification.confidence
        event.financial_materiality = mat_explanation
        event.expected_direction = classification.expected_direction
        event.time_horizon = classification.time_horizon
        event.news_summary = classification.news_summary
        event.reasoning = classification.reasoning
        event.risks = classification.risks
        event.is_processed = True

        # Score candidate
        analysis = self.scoring.score_event(event, classification, mat_score, session)
        return analysis

    def process_batch(
        self,
        events: List[NewsEvent],
        session_factory: sessionmaker,  # type: ignore[type-arg]
    ) -> List[int]:
        """Process events concurrently using a thread pool with serialised LLM access.

        Returns a list of created StockAnalysis IDs.
        """
        unprocessed = [ev for ev in events if not ev.is_processed]
        if not unprocessed:
            logger.info("All events already processed; nothing to do.")
            return []

        logger.info(
            "Processing %d events with %d workers (serialised LLM calls)...",
            len(unprocessed),
            MAX_WORKERS,
        )
        analysis_ids: List[int] = []
        event_ids = [ev.id for ev in unprocessed]

        def _process_one(event_id: int) -> Optional[int]:
            thread_session: Session = session_factory()
            try:
                from sqlalchemy import select as _select
                ev = thread_session.scalar(_select(NewsEvent).where(NewsEvent.id == event_id))
                if ev is None or ev.is_processed:
                    return None

                result = self.process_event(ev, thread_session)
                analysis_id = result.id if result else None
                thread_session.commit()
                return analysis_id
            except Exception as exc:
                thread_session.rollback()
                logger.error("Worker failed on event #%d: %s", event_id, exc)
                return None
            finally:
                thread_session.close()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {
                executor.submit(_process_one, eid): eid for eid in event_ids
            }
            for future in as_completed(future_map):
                eid = future_map[future]
                try:
                    res_id = future.result()
                    if res_id is not None:
                        analysis_ids.append(res_id)
                except Exception as exc:
                    logger.error("Future for event #%d raised: %s", eid, exc)

        logger.info(
            "Batch complete: %d/%d events produced candidate analyses.",
            len(analysis_ids),
            len(unprocessed),
        )
        return analysis_ids
