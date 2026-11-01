"""Collection service coordinating collectors, normalization, and run metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.collectors.base_collector import CollectedArticle
from app.collectors.collector_registry import build_default_registry
from app.database.repository import Repository
from app.processors.article_normalizer import ArticleNormalizer

logger = logging.getLogger("newsedge.services.collection")


@dataclass
class CollectionResult:
    """Aggregated statistics from a collection execution."""
    total_sources_checked: int = 0
    successful_sources: int = 0
    failed_sources: List[str] = field(default_factory=list)
    total_articles_found: int = 0
    new_articles: int = 0
    duplicate_articles: int = 0
    new_article_ids: List[int] = field(default_factory=list)


class CollectionService:
    """Manages news collection from enabled sources for a specific time window."""

    def __init__(self, session: Session):
        self.session = session
        self.registry = build_default_registry()
        self.normalizer = ArticleNormalizer()

    def run_collection(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> CollectionResult:
        """Run all enabled collectors and normalize newly acquired items."""
        result = CollectionResult()
        enabled_collectors = self.registry.get_enabled_collectors()
        result.total_sources_checked = len(enabled_collectors)

        logger.info(
            "Starting news collection across %d enabled sources from %s to %s",
            len(enabled_collectors),
            window_start,
            window_end,
        )

        all_collected: List[CollectedArticle] = []

        for collector in enabled_collectors:
            run_start = datetime.now(timezone.utc)
            # Find DB source
            db_source = Repository.get_source_by_name(self.session, collector.source_name)
            run_record = Repository.create_run(
                session=self.session,
                source_id=db_source.id if db_source else None,
                run_type="batch",
                started_at=run_start,
                status="running",
            )

            try:
                articles = collector.collect(since=window_start, until=window_end)
                all_collected.extend(articles)
                result.successful_sources += 1

                # Update source status
                if db_source:
                    Repository.update_source_status(
                        self.session,
                        source_id=db_source.id,
                        last_collected_at=run_start,
                        last_error=None,
                    )

                Repository.complete_run(
                    session=self.session,
                    run_id=run_record.id,
                    articles_found=len(articles),
                    status="completed",
                )
            except Exception as exc:
                logger.error("Error running collector '%s': %s", collector.source_name, exc)
                result.failed_sources.append(collector.source_name)
                if db_source:
                    Repository.update_source_status(
                        self.session,
                        source_id=db_source.id,
                        last_collected_at=run_start,
                        last_error=str(exc),
                    )
                Repository.complete_run(
                    session=self.session,
                    run_id=run_record.id,
                    status="failed",
                    error=str(exc),
                )

        result.total_articles_found = len(all_collected)

        # Normalize and persist
        for art in all_collected:
            record, is_new = self.normalizer.process_article(art, self.session)
            if is_new:
                result.new_articles += 1
                result.new_article_ids.append(record.id)
            else:
                result.duplicate_articles += 1

        # Also include any previously collected articles that remain unprocessed
        unprocessed = Repository.get_unprocessed_articles(self.session)
        for u in unprocessed:
            if u.id not in result.new_article_ids:
                result.new_article_ids.append(u.id)

        self.session.commit()
        return result
