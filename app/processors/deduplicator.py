"""Duplicate detection, noise filtering, and news event grouping."""

from __future__ import annotations

import difflib
import hashlib
import logging
import re
from datetime import timedelta
from typing import Dict, List, Set

from sqlalchemy.orm import Session

from app.database.models import NewsEvent, RawArticle
from app.database.repository import Repository
from app.processors.stock_mapper import StockMapper

logger = logging.getLogger("newsedge.processors.deduplicator")

# Non-equity macro noise patterns to skip
NOISE_PATTERNS = [
    r"\b(gold price|gold rate|silver price|silver rate|24k gold|22k gold|precious metal)\b",
    r"\b(crypto|bitcoin|ethereum|dogecoin|binance|solana|cryptocurrency)\b",
    r"\b(rupee falls|rupee drops|rupee rises|rupee gains|forex reserves|us dollar|dollar index)\b",
    r"\b(wall street|dow jones|s&p 500|nasdaq closes|asian shares|tokyo stocks|nikkei)\b",
    r"\b(fixed deposit|fd rate|income tax slab|itr filing|tax return|mutual fund schemes|sip investment)\b",
    r"\b(weather update|horoscope|astrology|cricket score|ipl auction)\b",
]


def is_macro_noise(headline: str) -> bool:
    """Return True if headline is clearly non-equity macro noise."""
    h_lower = headline.lower()
    return any(re.search(pat, h_lower) for pat in NOISE_PATTERNS)


class Deduplicator:
    """Groups multiple news coverage items covering the same announcement into a single NewsEvent."""

    def __init__(
        self,
        headline_similarity_threshold: float = 0.65,
        max_time_delta_hours: int = 14,
        stock_mapper: StockMapper | None = None,
    ):
        self.headline_similarity_threshold = headline_similarity_threshold
        self.max_time_delta = timedelta(hours=max_time_delta_hours)
        self.mapper = stock_mapper or StockMapper()

    @staticmethod
    def _clean_title(title: str) -> str:
        """Strip punctuation and extra spaces for similarity matching."""
        cleaned = re.sub(r"[^\w\s]", " ", title.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _are_headlines_similar(self, h1: str, h2: str) -> bool:
        t1 = self._clean_title(h1)
        t2 = self._clean_title(h2)
        ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
        return ratio >= self.headline_similarity_threshold

    def deduplicate_articles(
        self,
        articles: list[RawArticle],
        session: Session,
    ) -> list[NewsEvent]:
        """Group raw articles into unique NewsEvents and associate them.

        Filters out non-equity noise before grouping to maximize processing speed.
        """
        if not articles:
            return []

        # Identify companies and filter out noise
        article_companies: Dict[int, int | None] = {}
        filtered_articles: list[RawArticle] = []

        for art in articles:
            mention = self.mapper.resolve_company(art.headline, art.extracted_text, session)
            comp_id = mention.company_id if mention else None

            # If no company is identified AND headline is macro noise, skip it
            if comp_id is None and is_macro_noise(art.headline):
                logger.debug("Filtered out macro noise article: %s", art.headline[:60])
                continue

            article_companies[art.id] = comp_id
            filtered_articles.append(art)

        logger.info(
            "Retained %d relevant corporate/market articles (filtered %d noise items)",
            len(filtered_articles),
            len(articles) - len(filtered_articles),
        )

        groups: List[List[RawArticle]] = []
        visited_ids: Set[int] = set()

        sorted_articles = sorted(
            filtered_articles,
            key=lambda a: a.published_at or a.discovered_at,
            reverse=True,
        )

        for i, art_a in enumerate(sorted_articles):
            if art_a.id in visited_ids:
                continue

            current_group = [art_a]
            visited_ids.add(art_a.id)
            comp_a = article_companies[art_a.id]
            time_a = art_a.published_at or art_a.discovered_at

            for j in range(i + 1, len(sorted_articles)):
                art_b = sorted_articles[j]
                if art_b.id in visited_ids:
                    continue

                comp_b = article_companies[art_b.id]
                time_b = art_b.published_at or art_b.discovered_at

                same_company = comp_a is not None and comp_a == comp_b
                within_time = abs((time_a - time_b).total_seconds()) <= self.max_time_delta.total_seconds()
                similar_headline = self._are_headlines_similar(art_a.headline, art_b.headline)

                if (same_company and within_time and similar_headline) or (similar_headline and within_time):
                    current_group.append(art_b)
                    visited_ids.add(art_b.id)

            groups.append(current_group)

        created_events: list[NewsEvent] = []

        for group in groups:
            # Sort: highest source credibility and longest text first
            group.sort(
                key=lambda a: (a.source_credibility, len(a.extracted_text or "")),
                reverse=True,
            )
            primary_art = group[0]
            primary_comp_id = article_companies[primary_art.id]

            cleaned_headline = self._clean_title(primary_art.headline)
            date_str = (primary_art.published_at or primary_art.discovered_at).strftime("%Y-%m-%d")
            raw_hash_input = f"{primary_comp_id or 'NO_COMP'}|{cleaned_headline[:60]}|{date_str}"
            event_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest()

            event = Repository.get_event_by_hash(session, event_hash)
            if not event:
                event = Repository.create_event(
                    session=session,
                    primary_headline=primary_art.headline,
                    event_hash=event_hash,
                    primary_company_id=primary_comp_id,
                    is_processed=False,
                )
                created_events.append(event)

            # Link all articles in this group to the event
            for idx, member_art in enumerate(group):
                is_pri = (idx == 0)
                try:
                    Repository.link_article_to_event(
                        session=session,
                        event_id=event.id,
                        article_id=member_art.id,
                        is_primary=is_pri,
                    )
                except Exception:
                    pass

        logger.info(
            "Deduplication grouped %d articles into %d unique news events",
            len(filtered_articles),
            len(created_events),
        )
        return created_events
