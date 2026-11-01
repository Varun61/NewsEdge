"""Analysis service orchestrating deduplication, classification, and scoring.

Changes from v1:
- Generic mode: ALL news events are processed, not just company-matched ones.
  Ollama identifies the company from the article text when no DB match exists.
- Concurrent processing via NewsClassifier.process_batch() which internally
  uses ThreadPoolExecutor with one DB session per worker thread.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database.database import get_session_factory
from app.database.models import NewsEvent, RawArticle, StockAnalysis
from app.database.repository import Repository
from app.intelligence.ai_provider import BaseAIProvider
from app.intelligence.news_classifier import NewsClassifier
from app.intelligence.scoring_engine import ScoringEngine
from app.processors.deduplicator import Deduplicator
from app.processors.stock_mapper import StockMapper

logger = logging.getLogger("newsedge.services.analysis")


@dataclass
class AnalysisResult:
    """Metrics produced by the analysis stage."""
    total_events: int = 0
    classified_events: int = 0
    scored_analyses: List[int] = field(default_factory=list)  # StockAnalysis IDs
    errors: List[str] = field(default_factory=list)


class AnalysisService:
    """Processes newly collected raw articles into grouped, classified, and scored candidates."""

    def __init__(self, session: Session, ai_provider: BaseAIProvider):
        self.session = session
        self.ai = ai_provider
        self.settings = get_settings()
        self.mapper = StockMapper()
        self.deduplicator = Deduplicator(stock_mapper=self.mapper)
        self.scoring = ScoringEngine(self.settings)
        self.classifier = NewsClassifier(self.ai, self.scoring)
        self._session_factory = get_session_factory()

    def run_analysis(self, article_ids: List[int]) -> AnalysisResult:
        """Run deduplication, AI classification, materiality analysis, and scoring."""
        result = AnalysisResult()

        events: list[NewsEvent] = []
        if article_ids:
            # Fetch newly collected raw articles
            articles = list(
                self.session.scalars(
                    select(RawArticle).where(RawArticle.id.in_(article_ids))
                )
            )
            logger.info("Analyzing %d raw articles...", len(articles))
            # 1. Deduplicate & group into NewsEvents
            events = self.deduplicator.deduplicate_articles(articles, self.session)
            self.session.commit()

        # Also pick up any existing unanalyzed events (e.g. from restarted pipeline)
        unprocessed_db_events = Repository.get_unprocessed_events(self.session)
        for ev in unprocessed_db_events:
            if ev not in events:
                events.append(ev)

        result.total_events = len(events)
        if not events:
            logger.info("No news events to analyze.")
            return result

        # ── GENERIC MODE: process ALL events (no company filter) ──────────────
        logger.info(
            "Starting generic classification for %d news events "
            "(Ollama will identify company from article text for unresolved events).",
            len(events),
        )

        # Use concurrent batch processing; each worker uses its own DB session
        analysis_ids = self.classifier.process_batch(events, self._session_factory)

        result.classified_events = len(events)
        result.scored_analyses = analysis_ids

        # Commit any remaining state in the main session
        self.session.commit()
        logger.info(
            "Analysis complete: %d events submitted, %d scored candidate records created.",
            result.classified_events,
            len(result.scored_analyses),
        )
        return result
