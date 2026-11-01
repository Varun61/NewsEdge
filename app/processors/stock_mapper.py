"""Convenience interface for stock mapping using EntityExtractor."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.processors.entity_extractor import CompanyMention, EntityExtractor

logger = logging.getLogger("newsedge.processors.stock_mapper")


class StockMapper:
    """Wrapper around EntityExtractor providing high-level company resolution."""

    def __init__(self, extractor: Optional[EntityExtractor] = None):
        self.extractor = extractor or EntityExtractor()

    def resolve_company(
        self,
        headline: str,
        body_text: Optional[str],
        session: Session,
    ) -> Optional[CompanyMention]:
        """Return the highest-confidence primary company mention."""
        mentions = self.extractor.extract_mentions(headline, body_text, session)
        if mentions:
            return mentions[0]
        return None

    def resolve_all_companies(
        self,
        headline: str,
        body_text: Optional[str],
        session: Session,
    ) -> List[CompanyMention]:
        """Return all companies mentioned in the text."""
        return self.extractor.extract_mentions(headline, body_text, session)
