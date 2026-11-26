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
    r"\b(profit|revenue|results|q[1-4]|ebitda|margin|loss|quarterly|earnings)\b",
    r"\b(acquisition|acquires|merger|stake|buyout|jv|joint venture|demerger)\b",
    r"\b(dividend|buyback|bonus|split|rights issue|qip|fund raise|debt|prepayment)\b",
    r"\b(sebi|usfda|fda|warning letter|form 483|eir|penalty|raid|fraud|probe|nclt|cbi)\b",
    r"\b(plant|facility|capacity|expansion|commission|launch|inaugurate)\b",
    r"\b(upgrade|downgrade|target price|rating)\b",
    r"\b(resigns|appointed|resignation|steps down|ceo|cfo|md)\b",
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

    # ── Filings-first fast-path helpers ─────────────────────────────────
    def _get_filing_context(self, event: NewsEvent) -> Optional[dict]:
        """Return authoritative filing context if any linked article is an
        official exchange filing (symbol + parsed catalyst). Prefers the
        primary-linked filing."""
        fallback: Optional[dict] = None
        for link in event.article_links:
            art = link.article
            if not art or not isinstance(art.company_mentions, dict):
                continue
            cm = art.company_mentions
            sym = cm.get("authoritative_symbol")
            cat = cm.get("filing_catalyst")
            if sym and isinstance(cat, dict):
                name = None
                mentions = cm.get("mentions")
                if isinstance(mentions, list) and len(mentions) >= 2:
                    name = mentions[1]
                ctx = {
                    "symbol": sym,
                    "isin": cm.get("authoritative_isin"),
                    "name": name,
                    "catalyst": cat,
                }
                if link.is_primary:
                    return ctx
                fallback = fallback or ctx
        return fallback

    @staticmethod
    def _mcap_category(mcap_cr: float):
        from app.database.models import MarketCapCategory
        if mcap_cr >= 20_000:
            return MarketCapCategory.LARGE_CAP
        if mcap_cr >= 5_000:
            return MarketCapCategory.MID_CAP
        if mcap_cr >= 1_000:
            return MarketCapCategory.SMALL_CAP
        return MarketCapCategory.MICRO_CAP

    def _enrich_company_fundamentals(self, company, session) -> None:
        """Populate market cap + annual revenue from Screener for a candidate.

        Fetched once per symbol and persisted, so later runs skip it. Market cap
        drives the liquidity gate; revenue drives order-win materiality. Both
        were previously missing/placeholder, quietly breaking those gates.
        """
        if company is None or company.market_cap is not None:
            return
        try:
            from app.market_data.fundamentals import get_fundamentals_provider
            f = get_fundamentals_provider().get(company.nse_symbol)
            if not f:
                return
            if f.market_cap_cr:
                company.market_cap = f.market_cap_cr
                company.market_cap_category = self._mcap_category(f.market_cap_cr)
            if f.revenue_cr and (not company.annual_revenue or company.annual_revenue in (5000.0, 10000.0)):
                company.annual_revenue = f.revenue_cr
            logger.info(
                "Enriched %s: market_cap=%s Cr, revenue=%s Cr",
                company.nse_symbol, f.market_cap_cr, f.revenue_cr,
            )
        except Exception as exc:
            logger.debug("Fundamentals enrichment skipped for %s: %s", getattr(company, "nse_symbol", "?"), exc)

    def _resolve_filing_company(self, session, symbol, isin, name):
        """Resolve/create the Company for an authoritative filing. The symbol is
        exchange-provided, so it is definitively NSE-listed — no grounding check."""
        symbol = (symbol or "").upper().strip()
        if not symbol:
            return None
        resolved = Repository.get_company_by_symbol(session, symbol)
        if not resolved and isin:
            resolved = Repository.get_company_by_isin(session, isin)
        if resolved:
            if isin and not resolved.isin:
                resolved.isin = isin
            return resolved
        info = self._resolver.get_company_info(symbol) or {}
        official_name = info.get("name") or name or symbol
        kwargs = dict(
            nse_symbol=symbol,
            company_name=official_name,
            is_active=True,
            sector=info.get("sector", "Diversified"),
            industry=info.get("industry", "Diversified"),
            annual_revenue=info.get("revenue", 5000.0),
        )
        if isin:
            kwargs["isin"] = isin
        try:
            resolved = Repository.create_company(session, **kwargs)
            session.flush()
            return resolved
        except Exception as exc:
            logger.warning("Could not register filing company %s: %s", symbol, exc)
            return None

    @staticmethod
    def _classification_from_catalyst(catalyst: dict, symbol: str, name: str, source_urls: list) -> ClassificationResult:
        """Build a ClassificationResult from an exchange-parsed filing catalyst."""
        direction = (catalyst.get("direction") or "neutral").lower()
        impact = float(catalyst.get("impact_hint", 50.0))
        confidence = float(catalyst.get("confidence", 85.0))
        category = catalyst.get("news_category") or "OTHER"

        if direction == "bullish":
            sentiment = "VERY_POSITIVE" if impact >= 78.0 else "POSITIVE"
        elif direction == "bearish":
            sentiment = "VERY_NEGATIVE" if impact >= 78.0 else "NEGATIVE"
        else:
            sentiment = "NEUTRAL"

        summary = (catalyst.get("summary") or "").strip()
        bits = []
        if catalyst.get("order_value_cr"):
            bits.append(f"order ₹{catalyst['order_value_cr']:,.0f} Cr")
        if catalyst.get("profit_growth_pct") is not None:
            bits.append(f"profit {catalyst['profit_growth_pct']:+.0f}% YoY")
        if catalyst.get("revenue_growth_pct") is not None:
            bits.append(f"revenue {catalyst['revenue_growth_pct']:+.0f}% YoY")
        if catalyst.get("penalty_amount_cr"):
            bits.append(f"penalty ₹{catalyst['penalty_amount_cr']:,.0f} Cr")
        materiality = summary + ((" | " + ", ".join(bits)) if bits else "")

        return ClassificationResult(
            company_name=name,
            nse_symbol=symbol,
            news_category=category,
            sentiment=sentiment,
            impact_score=round(impact, 1),
            confidence=round(confidence, 1),
            financial_materiality=materiality or "Official exchange filing.",
            expected_direction=direction,
            time_horizon="intraday",
            news_summary=summary or "Official exchange filing",
            reasoning=f"Official NSE filing ({catalyst.get('matched_rule', 'filing')}); exchange-categorised catalyst.",
            risks=["Gap-open exhaustion", "Broader market regime"],
            source_urls=source_urls,
        )

    def _process_filing_event(self, event, ctx, source_urls, session):
        """Classify + score an event straight from its authoritative filing."""
        resolved = self._resolve_filing_company(session, ctx["symbol"], ctx.get("isin"), ctx.get("name"))
        if not resolved:
            return None
        event.primary_company_id = resolved.id
        self._enrich_company_fundamentals(resolved, session)

        classification = self._classification_from_catalyst(
            ctx["catalyst"], resolved.nse_symbol, resolved.company_name, source_urls
        )

        mat_score, mat_explanation = self.materiality.analyze(event, classification, session)

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

        logger.info(
            "Event #%d classified from official NSE filing: %s (%s) [%s/%s]",
            event.id, resolved.company_name, resolved.nse_symbol,
            classification.news_category, classification.expected_direction,
        )
        return self.scoring.score_event(event, classification, mat_score, session)

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

        # ── Filings-first fast-path ──────────────────────────────────────
        # If this event carries an authoritative exchange filing, trust the
        # exchange's own catalyst categorisation instead of re-guessing the
        # company and catalyst from free text.
        filing_ctx = self._get_filing_context(event)
        if filing_ctx and (filing_ctx.get("catalyst") or {}).get("is_material"):
            filing_analysis = self._process_filing_event(event, filing_ctx, source_urls, session)
            if filing_analysis is not None:
                return filing_analysis
            # Could not resolve the filing company; fall through to standard path.

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

        # Discard unmapped non-equity events early
        # If no listed NSE equity could be resolved and no sector thematic matched, skip AI call
        if symbol == "UNKNOWN" and not event.primary_company_id and not thematic_matches:
            logger.debug("Skipping unmapped non-equity event #%d: %s", event.id, event.primary_headline[:60])
            event.is_processed = True
            return None

        is_catalyst = _has_catalyst_signals(event.primary_headline, combined_text) or bool(thematic_matches)

        # Smart quantitative fast-path routing:
        # If the news has quantifiable metrics (Rs crore, % profit surge/fall), routine corporate filings,
        # or clear regulatory actions, the deterministic catalyst engine evaluates it in 0.001s with exact math.
        h_lower = event.primary_headline.lower()
        has_clear_numbers = bool(
            re.search(r"(\d+(?:\.\d+)?)\s*%", event.primary_headline)
            or re.search(r"(?:(?:rs\.?|inr|₹)\s*)?([\d,]+(?:\.\d+)?)\s*(?:crore|cr)\b", event.primary_headline, re.I)
        )
        is_routine_filing = any(w in h_lower for w in ["agm", "annual general meeting", "board meeting", "board meets", "analyst meet", "investor presentation"])
        is_clear_regulatory = any(w in h_lower for w in ["sebi penalty", "sebi fine", "sebi ban", "usfda warning", "import alert", "cbi probe", "ed raid", "auditor resign"])

        clear_heuristic_trigger = (symbol != "UNKNOWN") and (
            bool(thematic_matches)
            or is_routine_filing
            or (has_clear_numbers and any(w in h_lower for w in ["order", "contract", "bags", "wins", "profit", "net", "loss", "revenue", "sales"]))
            or is_clear_regulatory
        )

        use_ai = not clear_heuristic_trigger and is_catalyst

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
                        # Link original articles so secondary picks retain clickable news source links
                        if event.article_links:
                            for link in event.article_links:
                                try:
                                    Repository.link_article_to_event(
                                        session=session,
                                        event_id=new_sec_event.id,
                                        article_id=link.raw_article_id,
                                        is_primary=link.is_primary,
                                    )
                                except Exception:
                                    pass
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

        # Enrich fundamentals (market cap + revenue) so materiality and the
        # liquidity gate operate on real figures, not placeholders.
        self._enrich_company_fundamentals(event.primary_company, session)

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
