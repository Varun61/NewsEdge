"""Entity resolution and company extraction for Indian stocks.

Integrates fast in-memory NSEStockResolver with the database Company master
and alias registry. Prevents symbol hallucination and accurately identifies
listed Indian companies from news headlines and body text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Company, CompanyAlias
from app.processors.nse_master import get_nse_resolver

logger = logging.getLogger("newsedge.processors.entity_extractor")


@dataclass
class CompanyMention:
    """Represents an identified stock reference."""
    company_id: int
    nse_symbol: str
    company_name: str
    confidence: float
    is_primary_subject: bool
    match_type: str  # "nse_resolver", "symbol", "name", "alias", "pattern"


class EntityExtractor:
    """Extracts and maps NSE stock references from article headlines and bodies."""

    SYMBOL_STOPWORDS: Set[str] = {
        "A", "ALL", "AT", "AN", "AND", "AS", "BE", "BY", "FOR", "GO", "IN", "IS",
        "IT", "NEW", "NOW", "OF", "ON", "OR", "SO", "THE", "TO", "UP", "US", "WIN",
        "CAN", "BUY", "SELL", "HOLD", "GAIN", "FALL", "HIGH", "LOW", "NET", "ROAD",
        "GOOD", "FAST", "CARE", "AUTO", "NEWS", "BANK", "TRUE", "REAL", "BEST", "NEXT",
        "INDIA", "LIFE", "TECH", "POWER", "GOLD", "RATE", "CRUDE", "NIFTY", "SENSEX",
    }

    def __init__(self):
        self._resolver = get_nse_resolver()
        self._symbols_map: Dict[str, Tuple[int, str, str]] = {}  # SYMBOL -> (id, symbol, name)
        self._names_map: Dict[str, Tuple[int, str, str]] = {}    # normalized name -> (id, symbol, name)
        self._aliases_map: Dict[str, Tuple[int, str, str, float]] = {}  # alias -> (id, symbol, name, conf)
        self._is_loaded = False

    def load_cache(self, session: Session) -> None:
        """Load company database and alias table into memory for fast lookup."""
        companies = list(session.scalars(select(Company).where(Company.is_active.is_(True))))
        for c in companies:
            sym = c.nse_symbol.upper()
            self._symbols_map[sym] = (c.id, sym, c.company_name)

            norm_name = self._normalize_text(c.company_name)
            if norm_name:
                self._names_map[norm_name] = (c.id, sym, c.company_name)

        aliases = list(session.scalars(select(CompanyAlias)))
        for a in aliases:
            norm_alias = self._normalize_text(a.alias_name)
            if norm_alias and a.company:
                self._aliases_map[norm_alias] = (
                    a.company.id,
                    a.company.nse_symbol,
                    a.company.company_name,
                    a.confidence,
                )

        self._is_loaded = True
        logger.info(
            "EntityExtractor loaded %d companies and %d aliases into memory",
            len(self._symbols_map),
            len(self._aliases_map),
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Lowercase and remove special characters."""
        t = re.sub(r"[^\w\s]", " ", text.lower())
        return re.sub(r"\s+", " ", t).strip()

    def _ensure_company_in_db(self, session: Session, symbol: str, name: str, sector: str = "", industry: str = "", revenue: float = 10000.0) -> int:
        """Ensure company is persisted and return its ID."""
        from app.database.repository import Repository
        comp = Repository.get_company_by_symbol(session, symbol)
        if comp:
            return comp.id

        new_comp = Repository.create_company(
            session=session,
            nse_symbol=symbol,
            company_name=name,
            sector=sector or "Diversified",
            industry=industry or "Diversified",
            annual_revenue=revenue,
            is_active=True,
        )
        session.flush()
        # Update local cache
        self._symbols_map[symbol] = (new_comp.id, symbol, name)
        return new_comp.id

    def extract_mentions(
        self,
        headline: str,
        body: Optional[str],
        session: Session,
    ) -> List[CompanyMention]:
        """Identify companies mentioned in headline and body text."""
        if not self._is_loaded:
            self.load_cache(session)

        mentions: Dict[str, CompanyMention] = {}

        # 1. Regex Pattern check: (NSE: SYMBOL)
        norm_headline = self._normalize_text(headline)
        norm_body = self._normalize_text(body or "")
        headline_upper = headline.upper()

        pattern = r"\bNSE\s*:\s*([A-Z0-9\-]+)\b"
        for match in re.finditer(pattern, headline_upper + " " + (body or "").upper()):
            sym = match.group(1).upper()
            if sym in self._symbols_map:
                cid, s, cname = self._symbols_map[sym]
                in_headline = sym in headline_upper or cname.lower() in headline.lower()
                if sym not in mentions:
                    mentions[sym] = CompanyMention(
                        company_id=cid,
                        nse_symbol=sym,
                        company_name=cname,
                        confidence=0.98,
                        is_primary_subject=in_headline,
                        match_type="pattern",
                    )

        # 2. High-precision NSE Stock Resolver check
        resolved = self._resolver.resolve_from_text(headline, body or "")
        if resolved and resolved["symbol"] not in mentions:
            sym = resolved["symbol"]
            cname = resolved["name"]
            cid = self._ensure_company_in_db(
                session,
                symbol=sym,
                name=cname,
                sector=resolved.get("sector", ""),
                industry=resolved.get("industry", ""),
                revenue=resolved.get("revenue", 10000.0),
            )
            mentions[sym] = CompanyMention(
                company_id=cid,
                nse_symbol=sym,
                company_name=cname,
                confidence=float(resolved["confidence"]),
                is_primary_subject=True,
                match_type="nse_resolver",
            )

        # 3. Check Aliases
        sorted_aliases = sorted(self._aliases_map.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if len(alias) < 3:
                continue
            alias_pattern = rf"\b{re.escape(alias)}\b"
            in_headline = bool(re.search(alias_pattern, norm_headline))
            in_body = bool(re.search(alias_pattern, norm_body)) if not in_headline else False

            if in_headline or in_body:
                cid, sym, cname, alias_conf = self._aliases_map[alias]
                if sym not in mentions:
                    mentions[sym] = CompanyMention(
                        company_id=cid,
                        nse_symbol=sym,
                        company_name=cname,
                        confidence=alias_conf if in_headline else alias_conf * 0.85,
                        is_primary_subject=in_headline,
                        match_type="alias",
                    )

        results = list(mentions.values())
        results.sort(key=lambda m: (m.is_primary_subject, m.confidence), reverse=True)
        return results
