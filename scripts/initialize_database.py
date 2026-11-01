"""Database seeding script for NewsEdge.

Initializes schema and seeds:
1. Default NewsSource records
2. Comprehensive NSE stock universe (300+ actively traded companies from NSE_MASTER_DATA)
3. Full NSE equity universe from EQUITY_L.csv (2,600+ stocks)
4. Aliases, abbreviations, and brand names
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from app.database.database import get_session, init_db
from app.database.models import MarketCapCategory, SourceType
from app.database.repository import Repository
from app.logger import setup_logging
from app.processors.nse_master import NSE_MASTER_DATA

logger = logging.getLogger("newsedge.scripts.init_db")

EQUITY_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "EQUITY_L.csv"

logger = logging.getLogger("newsedge.scripts.init_db")

SOURCES_DATA = [
    {
        "name": "Google News RSS",
        "source_type": SourceType.RSS,
        "url": "https://news.google.com/rss/search?q=NSE+OR+BSE+stocks+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        "enabled": True,
        "credibility_score": 0.75,
    },
    {
        "name": "Economic Times Markets",
        "source_type": SourceType.RSS,
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "enabled": True,
        "credibility_score": 0.85,
    },
    {
        "name": "Business Standard",
        "source_type": SourceType.RSS,
        "url": "https://www.business-standard.com/rss/markets-106.rss",
        "enabled": True,
        "credibility_score": 0.80,
    },
    {
        "name": "Mint",
        "source_type": SourceType.RSS,
        "url": "https://www.livemint.com/rss/markets",
        "enabled": True,
        "credibility_score": 0.80,
    },
    {
        "name": "Hindu BusinessLine Markets",
        "source_type": SourceType.RSS,
        "url": "https://www.thehindubusinessline.com/markets/stock-markets/feeder/default.rss",
        "enabled": True,
        "credibility_score": 0.80,
    },
    {
        "name": "Hindu BusinessLine Companies",
        "source_type": SourceType.RSS,
        "url": "https://www.thehindubusinessline.com/companies/feeder/default.rss",
        "enabled": True,
        "credibility_score": 0.85,
    },
    {
        "name": "Moneycontrol",
        "source_type": SourceType.RSS,
        "url": "https://news.google.com/rss/search?q=site:moneycontrol.com+(stocks+OR+shares+OR+results+OR+NSE+OR+BSE+OR+market)&hl=en-IN&gl=IN&ceid=IN:en",
        "enabled": True,
        "credibility_score": 0.80,
    },
    {
        "name": "Financial Express",
        "source_type": SourceType.RSS,
        "url": "https://news.google.com/rss/search?q=site:financialexpress.com+(stocks+OR+market+OR+results+OR+NSE)&hl=en-IN&gl=IN&ceid=IN:en",
        "enabled": True,
        "credibility_score": 0.75,
    },
    {
        "name": "CNBC-TV18",
        "source_type": SourceType.RSS,
        "url": "https://news.google.com/rss/search?q=site:cnbctv18.com+(stocks+OR+market+OR+results+OR+NSE)&hl=en-IN&gl=IN&ceid=IN:en",
        "enabled": True,
        "credibility_score": 0.80,
    },
    {
        "name": "Zerodha Pulse",
        "source_type": SourceType.RSS,
        "url": "https://pulse.zerodha.com/feed.xml",
        "enabled": True,
        "credibility_score": 0.85,
    },
    {
        "name": "Investing.com India",
        "source_type": SourceType.RSS,
        "url": "https://in.investing.com/rss/news_25.rss",
        "enabled": True,
        "credibility_score": 0.80,
    },
]


def seed_database():
    """Initializes tables and populates sources, stocks, and aliases."""
    setup_logging()
    logger.info("Initializing database schema...")
    init_db()

    with get_session() as session:
        # 1. Sources
        logger.info("Seeding NewsSources...")
        for src in SOURCES_DATA:
            existing = Repository.get_source_by_name(session, src["name"])
            if not existing:
                Repository.create_source(session, **src)

        # 2. Companies from comprehensive NSE Master and Heavy Knowledge Base
        logger.info("Seeding Companies from NSE Master Universe and Company Knowledge Base...")
        companies_to_insert = []
        for item in NSE_MASTER_DATA:
            cap_enum = (
                MarketCapCategory.LARGE_CAP if item.get("cap") == "large_cap"
                else MarketCapCategory.MID_CAP if item.get("cap") == "mid_cap"
                else MarketCapCategory.SMALL_CAP
            )
            companies_to_insert.append({
                "nse_symbol": item["symbol"].upper(),
                "company_name": item["name"],
                "sector": item.get("sector", "Diversified"),
                "industry": item.get("industry", "Diversified"),
                "annual_revenue": float(item.get("revenue", 10000.0)),
                "market_cap_category": cap_enum,
                "is_active": True,
            })

        from app.processors.company_knowledge import COMPANY_KNOWLEDGE_BASE
        for prof in COMPANY_KNOWLEDGE_BASE.values():
            sym = prof.symbol.upper()
            if not any(c["nse_symbol"] == sym for c in companies_to_insert):
                cap_enum = (
                    MarketCapCategory.LARGE_CAP if prof.market_cap_category == "large_cap"
                    else MarketCapCategory.MID_CAP if prof.market_cap_category == "mid_cap"
                    else MarketCapCategory.SMALL_CAP
                )
                companies_to_insert.append({
                    "nse_symbol": sym,
                    "company_name": prof.company_name,
                    "sector": prof.sector,
                    "industry": prof.industry,
                    "annual_revenue": 5000.0,
                    "market_cap_category": cap_enum,
                    "is_active": True,
                })

        inserted = Repository.bulk_upsert_companies(session, companies_to_insert)
        logger.info("Upserted %d companies into database.", inserted)

        # 2b. Bulk-import full NSE equity universe from EQUITY_L.csv
        #     This ensures ALL 2,600+ listed equities are searchable even if not
        #     in the hand-curated NSE_MASTER_DATA list.
        if EQUITY_CSV_PATH.exists():
            logger.info("Seeding full NSE equity universe from %s ...", EQUITY_CSV_PATH.name)
            csv_companies = []
            with EQUITY_CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sym = (row.get("SYMBOL") or "").strip().upper()
                    name = (row.get("NAME OF COMPANY") or "").strip()
                    series = (row.get(" SERIES") or row.get("SERIES") or "").strip()
                    if not sym or not name:
                        continue
                    # Only include equity-series (skip BE, BT, etc. — non-standard series)
                    if series and series not in ("EQ", ""):
                        continue
                    csv_companies.append({
                        "nse_symbol": sym,
                        "company_name": name,
                        "sector": "Diversified",
                        "industry": "Diversified",
                        "annual_revenue": 5000.0,
                        "market_cap_category": MarketCapCategory.SMALL_CAP,
                        "is_active": True,
                    })
            csv_inserted = Repository.bulk_upsert_companies(session, csv_companies)
            logger.info("Upserted %d equities from EQUITY_L.csv into database.", csv_inserted)
        else:
            logger.warning("EQUITY_L.csv not found at %s — skipping full universe seed.", EQUITY_CSV_PATH)

        # 3. Aliases from curated data + full NSEStockResolver universe
        logger.info("Seeding Company Aliases...")
        from sqlalchemy import select
        from app.database.models import Company, CompanyAlias
        from app.processors.nse_master import get_nse_resolver

        existing_aliases = set(session.scalars(select(CompanyAlias.alias_name)).all())
        existing_alias_lower = {a.lower() for a in existing_aliases}
        symbol_to_id = {c.nse_symbol.upper(): c.id for c in session.scalars(select(Company)).all()}

        aliases_to_add: list[CompanyAlias] = []

        # 3a. Curated aliases (0.95 confidence)
        for item in NSE_MASTER_DATA:
            sym = item["symbol"].upper()
            cid = symbol_to_id.get(sym)
            if not cid:
                continue

            for alias in item.get("aliases", []):
                if alias.lower() not in existing_alias_lower:
                    aliases_to_add.append(
                        CompanyAlias(
                            company_id=cid,
                            alias_name=alias,
                            alias_type="curated_brand",
                            confidence=0.95,
                        )
                    )
                    existing_alias_lower.add(alias.lower())

        # 3b. Auto-generated brand & company name phrases from NSEStockResolver
        resolver = get_nse_resolver()
        for phrase, sym in resolver._alias_map.items():
            sym_clean = sym.upper()
            cid = symbol_to_id.get(sym_clean)
            if cid and phrase.lower() not in existing_alias_lower and len(phrase) >= 3:
                aliases_to_add.append(
                    CompanyAlias(
                        company_id=cid,
                        alias_name=phrase,
                        alias_type="brand_phrase",
                        confidence=0.90,
                    )
                )
                existing_alias_lower.add(phrase.lower())

        if aliases_to_add:
            session.bulk_save_objects(aliases_to_add)
            logger.info("Added %d new company aliases to database.", len(aliases_to_add))
        else:
            logger.info("All company aliases are already up to date.")

        session.commit()

    logger.info("Database seeding successfully completed!")


if __name__ == "__main__":
    seed_database()
