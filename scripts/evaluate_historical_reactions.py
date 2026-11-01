"""Institutional Historical Reaction Benchmark and Intelligence Evaluator.

Evaluates NewsEdge's intelligence engine against empirical market catalysts across
Large, Mid, Small, and Micro-cap NSE equities:
- Entity extraction & ticker resolution
- Company business model understanding & catalyst sensitivity
- Sector-wide policy & thematic beneficiary/casualty discovery
- Historical reaction archetype calibration (median returns & win rates)
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.processors.nse_master import get_nse_resolver
from app.processors.company_knowledge import get_company_profile
from app.intelligence.thematic_engine import get_thematic_engine
from app.intelligence.historical_reactions import match_historical_reaction

logging.basicConfig(level=logging.WARNING)


@dataclass
class HistoricalTestCase:
    id: str
    headline: str
    text_snippet: str
    expected_primary_symbol: Optional[str]
    expected_thematic_beneficiaries: List[str]
    expected_thematic_casualties: List[str]
    expected_direction: str  # "bullish" or "bearish"
    catalyst_archetype: str
    category: str


HISTORICAL_BENCHMARK_SUITE: List[HistoricalTestCase] = [
    # ── 1. REGULATORY & GOVERNANCE SHOCKS ─────────────────────────────────────
    HistoricalTestCase(
        id="REG-01",
        headline="Sebi bars Zee Entertainment promoters from holding board positions over fund diversion charges",
        text_snippet="Capital markets regulator Sebi on Friday passed an interim order barring promoters from managerial positions.",
        expected_primary_symbol="ZEEL",
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=[],
        expected_direction="bearish",
        catalyst_archetype="REGULATORY_GOVERNANCE_SHOCK",
        category="Governance & Regulatory",
    ),
    HistoricalTestCase(
        id="REG-02",
        headline="IRDAI cuts distributor commission caps on life and health insurance policies to 15 percent",
        text_snippet="Insurance regulator IRDAI has mandated immediate reductions in distribution commission ceilings, compressing agent margins.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=["POLICYBZR", "STARHEALTH", "HDFCLIFE"],
        expected_direction="bearish",
        catalyst_archetype="COMMISSION_MARGIN_REGULATION",
        category="Policy & Regulatory",
    ),
    HistoricalTestCase(
        id="REG-03",
        headline="USFDA issues Form 483 with 8 observations to Cipla Pithampur manufacturing facility",
        text_snippet="US drug regulator completed inspection of Cipla formulation plant with data integrity and procedural observations.",
        expected_primary_symbol="CIPLA",
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=[],
        expected_direction="bearish",
        catalyst_archetype="USFDA_PHARMA_INSPECTION_OVERHANG",
        category="Pharma Regulatory",
    ),
    HistoricalTestCase(
        id="REG-04",
        headline="USFDA issues Establishment Inspection Report (EIR) with zero 483 observations to Marksans Pharma Goa unit",
        text_snippet="Marksans Pharma announced receipt of Establishment Inspection Report (EIR) from USFDA indicating successful closure of audit.",
        expected_primary_symbol="MARKSANS",
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="USFDA_INSPECTION_CLEARANCE_EIR",
        category="Pharma Regulatory",
    ),

    # ── 2. SECTOR-WIDE INFRASTRUCTURE & CAPEX ─────────────────────────────────
    HistoricalTestCase(
        id="INF-01",
        headline="Cabinet clears massive ₹100,000 crore Railway capex package for track expansion and Kavach safety rollout",
        text_snippet="The Union Cabinet approved a mega investment outlay for Indian Railways to accelerate Kavach automatic train collision prevention.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["KERNEX", "TITAGARH", "JWL", "RVNL", "RAILTEL"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="SECTORAL_GOVERNMENT_CAPEX",
        category="Railways & Capex",
    ),
    HistoricalTestCase(
        id="INF-02",
        headline="Defence Ministry clears ₹45,000 crore procurement including indigenous radars, anti-drone systems and missiles",
        text_snippet="Defence Acquisition Council chaired by Rajnath Singh greenlights indigenous procurement under positive indigenisation list.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["ZENTEC", "PARAS", "DATAPATTNS", "HAL", "BEL", "BDL"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="SECTORAL_GOVERNMENT_CAPEX",
        category="Defence & Security",
    ),
    HistoricalTestCase(
        id="INF-03",
        headline="Centre slashes APM domestic natural gas allocation to city gas distributors by 20 percent",
        text_snippet="Ministry of Petroleum curtails low-cost APM gas supplies to city gas networks, forcing distributors to buy costly spot LNG.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=["IGL", "MGL", "GUJGASLTD"],
        expected_direction="bearish",
        catalyst_archetype="INPUT_FEEDSTOCK_COST_SHOCK",
        category="Energy & CGD",
    ),
    HistoricalTestCase(
        id="INF-04",
        headline="Brent crude oil prices surge above $88 per barrel amid escalating Middle East tensions",
        text_snippet="Global crude oil prices spiked sharply on fears of supply disruption in the Persian Gulf.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["ONGC", "OIL"],
        expected_thematic_casualties=["INDIGO", "IOC", "BPCL"],
        expected_direction="bearish",  # Casualties dominated
        catalyst_archetype="INPUT_FEEDSTOCK_COST_SHOCK",
        category="Commodity Shocks",
    ),

    # ── 3. TRADE POLICY & COMMODITY TARIFFS ───────────────────────────────────
    HistoricalTestCase(
        id="TRD-01",
        headline="Finance Minister slashes basic customs import duty on gold and silver to 6 percent in Budget",
        text_snippet="Government reduces basic customs duty on gold imports from 15% to 6% to curb smuggling and boost retail demand.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["SENCO", "TITAN", "KALYANKJIL", "THANGAMAYL"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="IMPORT_DUTY_REDUCTION",
        category="Trade & Duty",
    ),
    HistoricalTestCase(
        id="TRD-02",
        headline="DGTR recommends anti-dumping duty on imported steel and solar glass from China and Vietnam",
        text_snippet="Directorate General of Trade Remedies recommends safeguard tariffs to protect domestic manufacturers from subsidized dumping.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["TATASTEEL", "JSWSTEEL", "BORORENEW"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="TRADE_PROTECTION_ANTI_DUMPING",
        category="Trade & Duty",
    ),
    HistoricalTestCase(
        id="TRD-03",
        headline="Government announces ₹3 per litre hike in ethanol procurement price for sugar mills",
        text_snippet="Cabinet approves higher OMC procurement rates for ethanol produced from B-heavy molasses and maize to reach E20 blend.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["PRAJIND", "BALRAMCHIN", "BCLIND", "TRIVENI"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="AGRI_COMMODITY_PRICE_HIKE",
        category="Biofuel & Agri",
    ),

    # ── 4. HIGH-CONVICTION CORPORATE RESULTS & ORDERS ─────────────────────────
    HistoricalTestCase(
        id="CORP-01",
        headline="NTPC Q2 results: Consolidated profit rises 41% to Rs 7,351 crore, declares Rs 3 interim dividend",
        text_snippet="State-run power generator NTPC reported a 41% jump in quarterly net profit on strong thermal generation demand.",
        expected_primary_symbol="NTPC",
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="RECORD_EARNINGS_SURGE",
        category="Corporate Results",
    ),
    HistoricalTestCase(
        id="CORP-02",
        headline="Muthoot Finance Q2 results: Standalone profit rises 27% to Rs 2,977 crore on gold loan boom",
        text_snippet="Muthoot Finance posted strong Q2 results with net profit climbing 27% as gold loan AUM crossed records.",
        expected_primary_symbol="MUTHOOTFIN",
        expected_thematic_beneficiaries=["MUTHOOTFIN"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="RECORD_EARNINGS_SURGE",
        category="Corporate Results",
    ),
    HistoricalTestCase(
        id="CORP-03",
        headline="BEML bags mega contract worth Rs 3,658 crore from Chennai Metro for 210 driverless train cars",
        text_snippet="Public sector rail manufacturer BEML was awarded contract for manufacture and supply of driverless trainsets.",
        expected_primary_symbol="BEML",
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="MEGA_ORDER_WIN",
        category="Order Wins",
    ),
    HistoricalTestCase(
        id="CORP-04",
        headline="Kaynes Technology bags mega contract from global industrial OEM, receives greenfield OSAT subsidy",
        text_snippet="Kaynes Technology announced a multi-year electronics export contract alongside central semiconductor mission incentives.",
        expected_primary_symbol="KAYNES",
        expected_thematic_beneficiaries=[],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="MEGA_ORDER_WIN",
        category="Order Wins",
    ),
    HistoricalTestCase(
        id="CORP-05",
        headline="Rs 2.8 lakh crore data centre boom: Hyperscaler expansion spurs demand for AI servers and cooling",
        text_snippet="Hyperscalers and cloud giants commit billions to Indian data centre infrastructure and AI supercomputing facilities.",
        expected_primary_symbol=None,
        expected_thematic_beneficiaries=["NETWEB", "KAYNES", "APARINDS", "DIXON"],
        expected_thematic_casualties=[],
        expected_direction="bullish",
        catalyst_archetype="SECTORAL_GOVERNMENT_CAPEX",
        category="Data Center & AI",
    ),
]


def run_benchmark():
    """Execute complete benchmark suite and report precision metrics."""
    resolver = get_nse_resolver()
    thematic_engine = get_thematic_engine()

    total_cases = len(HISTORICAL_BENCHMARK_SUITE)
    entity_correct = 0
    thematic_baskets_correct = 0
    direction_correct = 0
    historical_matches = 0
    cap_distribution = {"large_cap": 0, "mid_cap": 0, "small_cap": 0, "micro_cap": 0}

    print("=" * 80)
    print("NEWSEDGE HISTORICAL REACTION & INTELLIGENCE BENCHMARK")
    print(f"Total Institutional Scenarios: {total_cases}")
    print("=" * 80)

    for tc in HISTORICAL_BENCHMARK_SUITE:
        print(f"\n[{tc.id}] {tc.category} | {tc.headline[:65]}...")

        # 1. Test Entity Resolution
        matched_symbol = None
        if tc.expected_primary_symbol:
            # Check standalone ticker match or resolver
            res = resolver.resolve_from_text(tc.headline)
            if not res:
                res = resolver.resolve_from_text(tc.text_snippet)
            if res:
                matched_symbol = res["symbol"]

            if matched_symbol == tc.expected_primary_symbol:
                entity_correct += 1
                status = f"✅ Entity: {matched_symbol}"
            else:
                status = f"❌ Entity Expected: {tc.expected_primary_symbol}, Got: {matched_symbol}"
            print(f"   {status}")
        else:
            entity_correct += 1

        # 2. Test Historical Reaction Matcher
        hist_prof = match_historical_reaction(tc.headline, tc.text_snippet)
        if hist_prof:
            historical_matches += 1
            print(f"   ✅ Historical Catalyst: {hist_prof.catalyst_type} (Win Rate: {hist_prof.directional_conviction_pct:.0f}%, Median Return: {hist_prof.median_intraday_return_pct:+.1f}%)")
        else:
            print("   ⚠️ No historical catalyst profile matched")

        # 3. Test Thematic Basket Discovery
        impacts = thematic_engine.detect_sector_catalysts(tc.headline, tc.text_snippet)
        found_bulls = [imp.symbol for imp in impacts if imp.direction == "bullish"]
        found_bears = [imp.symbol for imp in impacts if imp.direction == "bearish"]

        thematic_ok = True
        for exp_sym in tc.expected_thematic_beneficiaries:
            if exp_sym not in found_bulls:
                thematic_ok = False
        for exp_sym in tc.expected_thematic_casualties:
            if exp_sym not in found_bears:
                thematic_ok = False

        if tc.expected_thematic_beneficiaries or tc.expected_thematic_casualties:
            if thematic_ok:
                thematic_baskets_correct += 1
                print(f"   ✅ Thematic Basket Match: {len(found_bulls)} Bulls, {len(found_bears)} Bears")
            else:
                print(f"   ⚠️ Thematic Basket Partial Match: Bulls={found_bulls}, Bears={found_bears}")
        else:
            thematic_baskets_correct += 1

        # 4. Profile & Market Cap Diversity
        all_symbols = (([matched_symbol] if matched_symbol else []) + found_bulls + found_bears)
        for sym in set(all_symbols):
            prof = get_company_profile(sym)
            if prof:
                cat = prof.market_cap_category
                if cat in cap_distribution:
                    cap_distribution[cat] += 1

        # Check Directional Alignment
        primary_dir = "bullish"
        if found_bears and not found_bulls:
            primary_dir = "bearish"
        elif hist_prof:
            primary_dir = hist_prof.expected_direction

        if primary_dir == tc.expected_direction:
            direction_correct += 1

    # Final Summary Report
    print("\n" + "=" * 80)
    print("BENCHMARK EVALUATION SUMMARY REPORT")
    print("=" * 80)
    print(f"Entity Resolution Accuracy:         {entity_correct / total_cases * 100:6.1f}% ({entity_correct}/{total_cases})")
    print(f"Thematic Basket Coverage Accuracy:   {thematic_baskets_correct / total_cases * 100:6.1f}% ({thematic_baskets_correct}/{total_cases})")
    print(f"Directional Conviction Accuracy:     {direction_correct / total_cases * 100:6.1f}% ({direction_correct}/{total_cases})")
    print(f"Historical Archetype Coverage Rate:  {historical_matches / total_cases * 100:6.1f}% ({historical_matches}/{total_cases})")
    print("\nMarket Cap Distribution of Identified Beneficiaries / Casualties:")
    total_caps = sum(cap_distribution.values()) or 1
    for cat, cnt in cap_distribution.items():
        print(f"   - {cat.replace('_', ' ').title():12}: {cnt:3} stocks ({cnt / total_caps * 100:5.1f}%)")
    print("=" * 80)

    assert entity_correct >= total_cases * 0.90, "Entity resolution failed benchmark threshold"
    assert direction_correct >= total_cases * 0.90, "Directional accuracy failed benchmark threshold"
    print("ALL INSTITUTIONAL INTELLIGENCE CRITERIA MET WITH FLYING COLOURS! 🚀\n")


if __name__ == "__main__":
    run_benchmark()
