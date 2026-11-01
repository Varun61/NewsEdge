"""Article normalization and persistence."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy.orm import Session

from app.collectors.base_collector import CollectedArticle
from app.database.models import CollectionStatus, RawArticle, SourceType
from app.database.repository import Repository
from app.processors.nse_master import clean_headline_publisher

logger = logging.getLogger("newsedge.processors.normalizer")


class ArticleNormalizer:
    """Normalizes raw articles and manages persistence while preventing duplicates."""

    @staticmethod
    def clean_headline(text: str) -> str:
        """Strip HTML tags, collapse multiple whitespace characters, and remove publisher tails."""
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = clean_headline_publisher(cleaned)
        return cleaned

    def process_article(
        self,
        collected: CollectedArticle,
        session: Session,
    ) -> Tuple[RawArticle, bool]:
        """Normalize and persist an article.

        Returns (RawArticle, is_new).
        """
        headline = self.clean_headline(collected.headline)
        content_hash = collected.content_hash

        # Check existing by URL or content_hash
        existing = Repository.get_article_by_url(session, collected.article_url)
        if not existing:
            existing = Repository.get_article_by_hash(session, content_hash)

        if existing:
            return existing, False

        # Find or create source
        source = Repository.get_source_by_name(session, collected.source_name)
        if not source:
            source = Repository.create_source(
                session=session,
                name=collected.source_name,
                source_type=SourceType.RSS,
                url=None,
                enabled=True,
                credibility_score=collected.credibility_score,
            )

        now = datetime.now(timezone.utc)
        article = Repository.create_article(
            session=session,
            source_id=source.id,
            headline=headline,
            article_url=collected.article_url,
            published_at=collected.published_at,
            discovered_at=now,
            updated_at=now,
            raw_content=collected.raw_content,
            extracted_text=collected.extracted_text or collected.raw_content,
            company_mentions={"mentions": collected.company_mentions},
            source_credibility=source.credibility_score,
            content_hash=content_hash,
            collection_status=CollectionStatus.COLLECTED,
        )

        return article, True

    def process_batch(
        self,
        articles: list[CollectedArticle],
        session: Session,
    ) -> list[RawArticle]:
        """Normalize and persist a list of collected articles. Returns list of new RawArticles."""
        new_records: list[RawArticle] = []
        for art in articles:
            record, is_new = self.process_article(art, session)
            if is_new:
                new_records.append(record)
        return new_records
