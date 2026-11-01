"""Tests for company entity resolution and alias mapping."""

from app.database.models import Company, CompanyAlias
from app.processors.entity_extractor import EntityExtractor


def test_entity_extraction_patterns(session):
    # Setup test companies
    comp_sbi = Company(nse_symbol="SBIN", company_name="State Bank of India")
    comp_lt = Company(nse_symbol="LT", company_name="Larsen & Toubro")
    session.add_all([comp_sbi, comp_lt])
    session.flush()

    session.add(CompanyAlias(company_id=comp_sbi.id, alias_name="SBI", alias_type="abbreviation", confidence=0.98))
    session.add(CompanyAlias(company_id=comp_lt.id, alias_name="L&T", alias_type="abbreviation", confidence=0.98))
    session.commit()

    extractor = EntityExtractor()

    # 1. Direct Alias Match in Headline
    mentions_sbi = extractor.extract_mentions("SBI reports 25% surge in quarterly net profit", None, session)
    assert len(mentions_sbi) > 0
    assert mentions_sbi[0].nse_symbol == "SBIN"
    assert mentions_sbi[0].is_primary_subject is True

    # 2. Company Name Match
    mentions_lt = extractor.extract_mentions("Larsen & Toubro bags infrastructure order", None, session)
    assert len(mentions_lt) > 0
    assert mentions_lt[0].nse_symbol == "LT"

    # 3. Explicit Pattern Match: (NSE: SYMBOL)
    mentions_pattern = extractor.extract_mentions("Mega merger announced (NSE: SBIN) today", None, session)
    assert len(mentions_pattern) > 0
    assert mentions_pattern[0].nse_symbol == "SBIN"
    assert mentions_pattern[0].match_type == "pattern"


def test_nse_resolver_and_guess():
    from app.processors.nse_master import get_nse_resolver
    resolver = get_nse_resolver()

    # 1. Headline with uppercase ticker
    res_bhel = resolver.resolve_from_text("BHEL wins ₹2,400 crore contract from NTPC")
    assert res_bhel is not None
    assert res_bhel["symbol"] in ("BHEL", "NTPC")

    # 2. Headline with uncurated equity from EQUITY_L.csv
    res_syrma = resolver.resolve_from_text("Syrma SGS posts record quarterly growth")
    assert res_syrma is not None
    assert res_syrma["symbol"] == "SYRMA"

    # 3. Symbol guess rescue
    guess_tp = resolver.resolve_from_symbol_guess("TATAPOWR")
    assert guess_tp is not None
    assert guess_tp["symbol"] == "TATAPOWER"

    # 4. Strict check rejects unlisted publisher / phantom names
    assert resolver.is_valid_nse_symbol("KALKINE") is False
    assert resolver.is_valid_nse_symbol("UNKNOWN") is False
    assert resolver.is_valid_nse_symbol("LT") is True
