"""Abstract base collector interface for NewsEdge."""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger("newsedge.collectors")


@dataclass
class CollectedArticle:
    """Normalized article representation returned by collectors."""
    headline: str
    article_url: str
    source_name: str
    published_at: Optional[datetime] = None
    raw_content: Optional[str] = None
    extracted_text: Optional[str] = None
    company_mentions: list[str] = field(default_factory=list)
    credibility_score: float = 0.5

    @property
    def content_hash(self) -> str:
        """SHA-256 hash of normalized headline and url for deduplication."""
        raw = f"{self.headline.strip().lower()}|{self.article_url.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class BaseCollector(ABC):
    """Abstract base class for all news and announcement source collectors."""

    def __init__(self, source_name: str, source_url: str, enabled: bool = True, credibility_score: float = 0.5):
        self.source_name = source_name
        self.source_url = source_url
        self.enabled = enabled
        self.credibility_score = credibility_score

    @abstractmethod
    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        """Fetch articles published between *since* and *until* (both UTC-aware)."""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(source='{self.source_name}', enabled={self.enabled})>"
