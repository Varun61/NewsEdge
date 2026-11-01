"""Thematic and Sectoral News Intelligence Engine.

Identifies sector-wide government policies, regulatory interventions, capex allocations,
and macro commodity movements across Large, Mid, Small, and Micro-cap listed Indian equities.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.processors.company_knowledge import get_company_profile

logger = logging.getLogger("newsedge.intelligence.thematic")


@dataclass
class ThematicImpact:
    symbol: str
    company_name: str
    market_cap_category: str  # "large_cap", "mid_cap", "small_cap", "micro_cap"
    direction: str  # "bullish" or "bearish"
    impact_score: float  # 0 to 100
    theme_title: str
    rationale: str
    confidence: float = 85.0


@dataclass
class SectorRule:
    theme_id: str
    theme_title: str
    trigger_patterns: List[str]
    bullish_beneficiaries: List[Tuple[str, str, float]]  # (symbol, rationale, score)
    bearish_casualties: List[Tuple[str, str, float]]     # (symbol, rationale, score)


# Empirical sector-wide and government policy rules with rich small/mid/micro cap coverage
SECTOR_THEMATIC_RULES: List[SectorRule] = [
    # ── 1. RAILWAYS CAPEX, SIGNALING & KAVACH ─────────────────────────────────
    SectorRule(
        theme_id="RAILWAYS_CAPEX",
        theme_title="Indian Railways Capex, Track Expansion & Kavach Safety",
        trigger_patterns=[
            r"\b(?:railway|railways|ministry of railways)\b.*\b(?:capex|budget|modernis\w*|moderniz\w*|invest\w*|allocation|package|funds|infusion|track|electrif\w*)\b",
            r"\b(?:invest\w*|allot\w*|clears|approves)\b.*\b(?:railway|railways|vande bharat|bullet train|freight corridor)\b",
            r"\b(?:railway|railways)\b.*\b(?:order|tender|contract|procurement)\b.*\b(?:wagon\w*|coach\w*|locomotive\w*|trainset\w*)\b",
            r"\b(?:kavach|automatic train protection|tcas|anti-collision)\b.*\b(?:tender\w*|install\w*|rollout\w*|order\w*|safety)\b",
        ],
        bullish_beneficiaries=[
            ("KERNEX", "Micro-cap pure play in Kavach automatic train protection hardware and software.", 88.0),
            ("TITAGARH", "Mid-cap leader in freight wagons, metro coaches, and Vande Bharat passenger trainsets.", 86.0),
            ("JWL", "Small-cap freight wagon, specialized bogie, and braking systems manufacturer.", 86.0),
            ("RVNL", "Primary turnkey railway EPC executor for new lines, doubling, and electrification.", 85.0),
            ("TEXRAIL", "Small-cap wagon manufacturer and track renewal / overhead electrification contractor.", 84.0),
            ("IRFC", "Dedicated sovereign market borrowing arm financing all railway rolling stock and infrastructure.", 84.0),
            ("RAILTEL", "Rail telecom, signaling modernization, and optical fiber network partner for Indian Railways.", 83.0),
            ("IRCON", "Small-cap infrastructure PSU executing complex rail lines and highway networks.", 82.0),
            ("BEML", "Mid-cap builder of Vande Metro trainsets and heavy urban metro coaches.", 82.0),
            ("RITES", "Small-cap transport consultancy and custom locomotive export manufacturer.", 80.0),
            ("IRCTC", "Monopoly passenger ticketing, onboard catering, and tourism partner.", 78.0),
        ],
        bearish_casualties=[],
    ),

    # ── 2. INSURANCE REGULATION & COMMISSION CAPS ──────────────────────────────
    SectorRule(
        theme_id="INSURANCE_COMMISSION_CUT",
        theme_title="IRDAI Insurance Commission & Surrender Value Regulation",
        trigger_patterns=[
            r"\b(?:irdai|insurance regulator)\b.*\b(?:cut\w*|cap\w*|lower\w*|slash\w*|reduc\w*|curb\w*)\b.*\b(?:commission\w*|payout\w*|fee\w*|charge\w*)\b",
            r"\b(?:insurance|life insurance|health insurance)\b.*\b(?:commission\w*|broker fee\w*)\b.*\b(?:cut\w*|cap\w*|slash\w*|reduc\w*|limit\w*)\b",
            r"\b(?:irdai|insurance)\b.*\b(?:surrender value\w*|surrender payout\w*)\b.*\b(?:hike\w*|increase\w*|mandat\w*|rule\w*|norm\w*)\b",
        ],
        bullish_beneficiaries=[],
        bearish_casualties=[
            ("POLICYBZR", "Mid-cap PB Fintech distributor commissions directly compressed by regulatory caps.", 89.0),
            ("STARHEALTH", "Mid-cap standalone health insurer facing higher loss ratios and distributor remuneration caps.", 83.0),
            ("HDFCLIFE", "Higher surrender payouts or distributor margin curbs compress new business margins (VNB).", 82.0),
            ("SBILIFE", "Bancassurance commission dynamics and agency economics impacted by distribution rule changes.", 80.0),
            ("ICICIPRULI", "Product profitability and commission distribution model pressured by IRDAI regulations.", 80.0),
        ],
    ),

    # ── 3. DEFENCE INDIGENISATION, DRONES & RADARS ────────────────────────────
    SectorRule(
        theme_id="DEFENCE_PROCUREMENT",
        theme_title="Defence Capital Outlay, Drones & Indigenous Procurement",
        trigger_patterns=[
            r"\b(?:defence ministry|defense ministry|dac|rajnath singh)\b.*\b(?:clears|approves|procure|tender\w*|orders|contract\w*)\b",
            r"\b(?:positive indigenisation list|make in india defence|atmanirbhar defence)\b",
            r"\b(?:defence|defense)\b.*\b(?:budget|outlay|allocation|capex)\b.*\b(?:hike|boost|increase|surge)\b",
            r"\b(?:submarine|warship|fighter jet|missile|radar|drone|anti-drone)\b.*\b(?:order|procurement|contract|deal)\b",
        ],
        bullish_beneficiaries=[
            ("ZENTEC", "Small-cap pure play in indigenous anti-drone defense systems and combat simulators.", 89.0),
            ("PARAS", "Micro-cap specialist in defence opto-electronics, thermal imaging, and EMP shielding.", 88.0),
            ("DATAPATTNS", "Small-cap developer of airborne surveillance radars and missile seeker processors.", 87.0),
            ("HAL", "Large-cap aerospace company delivering Tejas fighter jets and combat helicopters.", 87.0),
            ("BEL", "Large-cap defence electronics major manufacturing naval surveillance radars and EW suites.", 86.0),
            ("MAZDOCK", "Mid-cap naval warship and conventional submarine builder with immense backlog.", 86.0),
            ("COCHINSHIP", "Mid-cap naval shipyard building aircraft carriers and ASW shallow water crafts.", 85.0),
            ("ASTRAMICRO", "Small-cap RF and microwave super-component manufacturer for missile radars.", 84.0),
            ("GRSE", "Small-cap warship builder delivering stealth frigates and anti-submarine corvettes.", 84.0),
            ("BDL", "Small-cap sovereign manufacturer of surface-to-air missiles and torpedoes.", 84.0),
            ("IDEAFORGE", "Micro-cap domestic market leader in tactical surveillance UAVs and military drones.", 84.0),
            ("MTARTECH", "Small-cap precision engineering firm manufacturing missile rocket engines.", 82.0),
        ],
        bearish_casualties=[],
    ),

    # ── 4. SOLAR, WIND, GREEN ENERGY & TRANSMISSION CORRIDORS ──────────────────
    SectorRule(
        theme_id="RENEWABLE_POWER_BOOST",
        theme_title="Renewable Energy Expansion, Solar Glass & Wind Capacity",
        trigger_patterns=[
            r"\b(?:solar|wind energy|renewable energy|green energy)\b.*\b(?:tender\w*|auction\w*|target\w*|capacity\w*|scheme|policy)\b",
            r"\b(?:pm surya ghar|rooftop solar|almm|solar glass|anti-dumping duty solar)\b",
            r"\b(?:green energy corridor|transmission grid|interconnection)\b.*\b(?:tender\w*|order\w*|capex)\b",
        ],
        bullish_beneficiaries=[
            ("BORORENEW", "Small-cap sole domestic manufacturer of specialized solar glass for PV modules.", 88.0),
            ("KPIGREEN", "Small-cap fast-growing solar and hybrid power producer with massive Gujarat pipeline.", 87.0),
            ("IREDA", "Mid-cap dedicated sovereign NBFC financing renewable and clean energy capacity.", 86.0),
            ("SUZLON", "Mid-cap wind turbine manufacturing leader with multi-gigawatt order book.", 85.0),
            ("INOXWIND", "Small-cap wind turbine OEM capturing large corporate and PSU wind orders.", 85.0),
            ("APARINDS", "Mid-cap global leader in high-efficiency transmission conductors for power grids.", 85.0),
            ("PREMIERENE", "Mid-cap integrated solar cell and TOPCon bifacial module manufacturer.", 84.0),
            ("WAAREEENER", "Large-cap largest solar module producer and major exporter to the US.", 84.0),
            ("KEC", "Small-cap power transmission line and substation EPC major.", 82.0),
        ],
        bearish_casualties=[],
    ),

    # ── 5. ELECTRIC VEHICLES & E-BUS PROCUREMENT ──────────────────────────────
    SectorRule(
        theme_id="ELECTRIC_VEHICLES_BOOST",
        theme_title="Electric Bus Tenders, Battery Gigafactories & EV Subsidies",
        trigger_patterns=[
            r"\b(?:pm-ebus sewa|electric bus|e-bus|cesl tender)\b.*\b(?:tender\w*|deploy\w*|order\w*|contract\w*)\b",
            r"\b(?:electric vehicle|ev adoption|fame|pli battery)\b.*\b(?:subsidy|incentive|scheme|growth|boost)\b",
            r"\b(?:lithium-ion|battery gigafactory|cell manufacturing)\b",
        ],
        bullish_beneficiaries=[
            ("OLECTRA", "Small-cap pioneer in electric bus manufacturing under PM-eBus Sewa contracts.", 88.0),
            ("JBMA", "Small-cap manufacturer of ECOLIFE electric buses and transit charging systems.", 86.0),
            ("SONACOMS", "Mid-cap global automotive driveline and EV traction motor manufacturer.", 84.0),
            ("EXIDEIND", "Mid-cap lead-acid major investing in multi-gigawatt lithium-ion cell gigafactory.", 83.0),
            ("ARE&M", "Mid-cap Amara Raja battery giant setting up 16 GWh EV lithium corridor.", 82.0),
        ],
        bearish_casualties=[],
    ),

    # ── 6. ELECTRONICS PLI & SEMICONDUCTOR SUBSIDIES (EMS) ─────────────────────
    SectorRule(
        theme_id="ELECTRONICS_PLI_BOOST",
        theme_title="Electronics Manufacturing Services (EMS) & Semiconductor PLI",
        trigger_patterns=[
            r"\b(?:electronics manufacturing|ems|pli scheme|semiconductor mission)\b.*\b(?:subsidy|approval|incentive|grant|clear\w*)\b",
            r"\b(?:osat|chip testing|semiconductor plant|pcba)\b.*\b(?:approv\w*|invest\w*|inaugurat\w*)\b",
        ],
        bullish_beneficiaries=[
            ("KAYNES", "Mid-cap industrial/defence EMS leader establishing advanced semiconductor OSAT facility.", 88.0),
            ("DIXON", "Large-cap electronics manufacturing giant capturing global mobile and IT hardware PLI.", 87.0),
            ("SYRMA", "Mid-cap precision engineering and PCBA manufacturer seeing record quarterly growth.", 86.0),
            ("CYIENTDLM", "Small-cap build-to-print specialist in aerospace and defence box-build electronics.", 84.0),
            ("PGEL", "Small-cap consumer durables ODM manufacturer expanding smart meter and AC lines.", 83.0),
        ],
        bearish_casualties=[],
    ),

    # ── 7. SUGAR ETHANOL POLICY & BIOFUEL MANDATES ─────────────────────────────
    SectorRule(
        theme_id="ETHANOL_POLICY_BOOST",
        theme_title="Ethanol Blending Price Hike & Distillery Capex Incentives",
        trigger_patterns=[
            r"\b(?:ethanol|blending)\b.*\b(?:price hike|procurement price|boost|incentive|e20|tender)\b",
            r"\b(?:sugar mills|sugar export)\b.*\b(?:quota|subsidy|msp hike|ethanol allocation)\b",
            r"\b(?:sustainable aviation fuel|saf|biofuel)\b.*\b(?:mandat\w*|blend\w*|policy)\b",
        ],
        bullish_beneficiaries=[
            ("PRAJIND", "Small-cap global leader in ethanol distillery technology and 2G biofuel plant EPC.", 88.0),
            ("BALRAMCHIN", "Mid-cap integrated sugar and ethanol distiller benefiting from OMC procurement hikes.", 86.0),
            ("BCLIND", "Micro-cap pure play in grain-based (maize/broken rice) ethanol distillation.", 85.0),
            ("TRIVENI", "Small-cap dual-feed sugar and ethanol distiller with high distillery capacity.", 84.0),
            ("EIDPARRY", "Mid-cap South India sugar producer and ethanol distiller.", 83.0),
        ],
        bearish_casualties=[],
    ),

    # ── 8. FERTILIZER SUBSIDY DISBURSEMENT & MONSOON SOWING ────────────────────
    SectorRule(
        theme_id="FERTILIZER_SUBSIDY_BOOST",
        theme_title="Fertilizer Nutrient Subsidy Package & Agricultural Revival",
        trigger_patterns=[
            r"\b(?:fertilizer subsidy|nutrient based subsidy|nbs rates)\b.*\b(?:approv\w*|clears\w*|releas\w*|package|infusion)\b",
            r"\b(?:urea|dap|npk|phosphatic fertilizer)\b.*\b(?:subsidy|concession|clearance)\b",
            r"\b(?:monsoon|kharif sowing|rabi sowing)\b.*\b(?:record|bumper|normal|above normal)\b.*\b(?:sowing|acreage)\b",
        ],
        bullish_beneficiaries=[
            ("FACT", "Mid-cap complex fertilizer producer in South India with high subsidy sensitivity.", 86.0),
            ("RCF", "Small-cap PSU producing Trombay and Thal complex fertilizers and industrial chemicals.", 85.0),
            ("NFL", "Small-cap national Urea manufacturer with extensive North India dealer reach.", 84.0),
            ("CHAMBLFERT", "Mid-cap energy-efficient private Urea and crop protection player in Rajasthan.", 84.0),
            ("COROMANDEL", "Large-cap phosphatic complex fertilizer and agrochemical leader.", 83.0),
        ],
        bearish_casualties=[],
    ),

    # ── 9. GOLD IMPORT DUTY CUT & JEWELLERY DEMAND ─────────────────────────────
    SectorRule(
        theme_id="GOLD_DUTY_CUT",
        theme_title="Basic Customs Duty Reduction on Gold & Precious Metals",
        trigger_patterns=[
            r"\b(?:gold|silver|precious metal)\b.*\b(?:import duty|customs duty|duty)\b.*\b(?:cut\w*|slash\w*|reduc\w*|lower\w*)\b",
            r"\b(?:cut\w*|slash\w*|reduc\w*|lower\w*)\b.*\b(?:import duty|customs duty|basic customs duty|duty)\b.*\b(?:gold|silver|precious metal)\b",
            r"\b(?:duty cut|duty reduction)\b.*\b(?:gold|silver|jewellery|bullion)\b",
            r"\b(?:festive demand|dhanteras|diwali|wedding season)\b.*\b(?:jewellery|gold sales)\b.*\b(?:record|surge|boom)\b",
        ],
        bullish_beneficiaries=[
            ("SENCO", "Small-cap fast-expanding eastern and northern jewellery retail chain.", 87.0),
            ("TITAN", "Large-cap market leader operating Tanishq, benefiting from formalization.", 87.0),
            ("KALYANKJIL", "Mid-cap pan-India and Middle East showroom network expanding rapidly.", 85.0),
            ("THANGAMAYL", "Small-cap regional Tamil Nadu jewellery retailer capturing tier-2/3 festive buying.", 84.0),
        ],
        bearish_casualties=[],
    ),

    # ── 10. REAL ESTATE DEMAND, STAMP DUTY & MORTGAGE INCENTIVES ───────────────
    SectorRule(
        theme_id="REALTY_POLICY_BOOST",
        theme_title="Real Estate Demand Incentives, Lower Mortgage Rates & Housing Handover",
        trigger_patterns=[
            r"\b(?:stamp duty|home loan rates|housing demand)\b.*\b(?:cut|concession|incentive|easing|rebate)\b",
            r"\b(?:housing sales|residential sales|pre-sales)\b.*\b(?:record|all-time high|surge|boom)\b",
        ],
        bullish_beneficiaries=[
            ("SIGNATURE", "Mid-cap high-growth Gurugram developer with strong pre-sales launch velocity.", 85.0),
            ("LODHA", "Large-cap Macrotech Developers pre-sales velocity in MMR and Pune.", 83.0),
            ("DLF", "Large-cap super-luxury developer in Gurugram with massive cash pre-sales.", 83.0),
            ("ASTRAL", "Large-cap CPVC plumbing pipes leader capturing construction finishing demand.", 82.0),
            ("KAJARIACER", "Mid-cap ceramic and vitrified floor tiles manufacturer capturing home completion demand.", 82.0),
        ],
        bearish_casualties=[],
    ),

    # ── 11. CITY GAS APM ALLOCATION CUT / COST SQUEEZE ──────────────────────────
    SectorRule(
        theme_id="CITY_GAS_APM_CUT",
        theme_title="Administered Price Mechanism (APM) Gas Allocation Cut",
        trigger_patterns=[
            r"\b(?:apm\w*|domestic gas|natural gas)\b.*\b(?:cut\w*|slash\w*|reduc\w*|curtail\w*|shortage)\b.*\b(?:city gas|cgd|cng|distributor\w*)\b",
            r"\b(?:cut\w*|slash\w*|reduc\w*|curtail\w*)\b.*\b(?:apm\w*|domestic gas|gas allocation)\b.*\b(?:city gas|cgd|cng|distributor\w*)\b",
            r"\b(?:city gas|cgd|igl|mgl)\b.*\b(?:gas allocation cut|apm supply reduced|margin hit|higher cost)\b",
            r"\b(?:imported lng|spot lng)\b.*\b(?:surge|spike|rallies)\b.*\b(?:city gas|cgd)\b",
        ],
        bullish_beneficiaries=[],
        bearish_casualties=[
            ("IGL", "Mid-cap Indraprastha Gas faces severe margin compression on forced imported LNG use.", 89.0),
            ("MGL", "Mid-cap Mahanagar Gas EBITDA/scm margins squeezed in Mumbai transport network.", 87.0),
            ("GUJGASLTD", "Mid-cap Gujarat Gas industrial and commercial PNG margins pressured.", 83.0),
        ],
    ),

    # ── 12. CRUDE OIL SURGE (UPSTREAM GAIN vs OMC/AVIATION LOSS) ────────────────
    SectorRule(
        theme_id="CRUDE_OIL_SURGE",
        theme_title="Global Crude Oil Price Spike / Geopolitical Supply Shock",
        trigger_patterns=[
            r"\b(?:crude oil|brent crude|oil price|oil prices)\b.*\b(?:surge|surges|rallies|jumps|spikes|soars|crosses \$|high)\b",
            r"\b(?:opec|middle east tension|iran strike|oil supply)\b.*\b(?:spike|surge|disrupt)\b",
        ],
        bullish_beneficiaries=[
            ("ONGC", "Large-cap upstream explorer gains from higher crude oil selling realizations.", 85.0),
            ("OIL", "Mid-cap pure-play upstream producer gains from expanded per-barrel realization.", 84.0),
        ],
        bearish_casualties=[
            ("INDIGO", "Large-cap airline margins crushed by Aviation Turbine Fuel (ATF) cost increases.", 86.0),
            ("IOC", "Large-cap fuel marketing margins squeezed without retail pump price hikes.", 84.0),
            ("BPCL", "Large-cap marketing margins on petrol/diesel compressed by elevated crude.", 83.0),
        ],
    ),

    # ── 13. DATA CENTER, AI COMPUTING & SERVER BOOM ─────────────────────────────
    SectorRule(
        theme_id="DATA_CENTER_AI_BOOM",
        theme_title="Data Centre Expansion, Hyperscaler Capex & AI Supercomputing",
        trigger_patterns=[
            r"\b(?:data centre|data center|server farm|hyperscaler)\b.*\b(?:boom|expansion|capex|invest\w*|buildout|billion|crore)\b",
            r"\b(?:ai supercomput\w*|india ai mission|nvidia partner|hpc server)\b",
            r"\b(?:data centre\w*|data center\w*)\b.*\b(?:power|cooling|rack|infrastructure)\b",
        ],
        bullish_beneficiaries=[
            ("NETWEB", "Small-cap indigenous AI supercomputing and high-density HPC server manufacturer.", 89.0),
            ("KAYNES", "Mid-cap electronic manufacturer building smart server assemblies and OSAT chips.", 86.0),
            ("APARINDS", "Mid-cap power cable manufacturer supplying high-spec data center cabling.", 84.0),
            ("DIXON", "Large-cap electronics major scaling IT server and hardware manufacturing.", 83.0),
        ],
        bearish_casualties=[],
    ),

    # ── 14. STEEL TRADE PROTECTION & ANTI-DUMPING TARIFFS ──────────────────────
    SectorRule(
        theme_id="STEEL_TRADE_PROTECTION",
        theme_title="Anti-Dumping Duty on Imported Steel & Safeguard Tariffs",
        trigger_patterns=[
            r"\b(?:anti-dumping duty|safeguard duty|countervailing duty)\b.*\b(?:steel|hot rolled|cold rolled|wire rod)\b",
            r"\b(?:steel import\w*|chinese steel dumping)\b.*\b(?:curb|tax|tariff|duty|penalt\w*)\b",
            r"\b(?:ministry of steel|dgtr)\b.*\b(?:recommends duty|proposes tariff|protection)\b",
        ],
        bullish_beneficiaries=[
            ("TATASTEEL", "Large-cap integrated steelmaker benefiting from domestic price realization floor.", 87.0),
            ("JSWSTEEL", "Large-cap domestic steel giant expanding capacity with protected spreads.", 86.0),
            ("NMDC", "Large-cap sovereign miner supplying domestic iron ore to operating blast furnaces.", 84.0),
        ],
        bearish_casualties=[],
    ),

    # ── 15. CEMENT INFRASTRUCTURE SPENDS & HIGHWAY CONSTRUCTION ────────────────
    SectorRule(
        theme_id="CEMENT_INFRA_SPURT",
        theme_title="Cement Price Firming, Highway Expansion & Infra Capex",
        trigger_patterns=[
            r"\b(?:cement price\w*|cement bag\w*)\b.*\b(?:hike|surge|firm|rise|increase)\b",
            r"\b(?:highway construction|nhai capex|affordable housing)\b.*\b(?:speed|record|target|boost)\b",
        ],
        bullish_beneficiaries=[
            ("ULTRACEMCO", "Large-cap market leader capturing infrastructure volumetric dispatch.", 86.0),
            ("STARCEMENT", "Small-cap North East cement leader with high pricing power and margin stability.", 85.0),
        ],
        bearish_casualties=[],
    ),

    # ── 16. GOLD LOAN EXPANSION & COLLATERAL APPRECIATION ───────────────────────
    SectorRule(
        theme_id="GOLD_FINANCE_EXPANSION",
        theme_title="Gold Loan Surge, Regulatory Headroom & Collateral Value Appreciation",
        trigger_patterns=[
            r"\b(?:gold loan\w*|gold collateral)\b.*\b(?:surge|jump|record|growth|boost|demand|boom|expansion)\b",
            r"\b(?:gold price\w*|bullion price\w*)\b.*\b(?:record high|all-time high|crosses|soars)\b.*\b(?:gold loan|nbfc)\b",
        ],
        bullish_beneficiaries=[
            ("MUTHOOTFIN", "Large-cap gold financing giant gaining from expanded collateral value and AUM surge.", 88.0),
            ("MANAPPURAM", "Mid-cap gold lender capturing high-yield short-tenure borrower demand.", 86.0),
            ("FEDERALBNK", "Mid-cap private bank with high-margin retail gold loan growth.", 83.0),
        ],
        bearish_casualties=[],
    ),
]


class ThematicEngine:
    """Detects sector-wide catalysts and maps impact across Large, Mid, Small, and Micro-cap stocks."""

    def __init__(self):
        self.rules = SECTOR_THEMATIC_RULES

    def detect_sector_catalysts(self, headline: str, text: str = "") -> List[ThematicImpact]:
        """Evaluate article text against all sector thematic rules.

        Returns a list of ThematicImpact candidates for affected stocks across market caps.
        """
        combined = f"{headline} {text[:400]}".lower()
        impacts: List[ThematicImpact] = []

        for rule in self.rules:
            if any(re.search(pat, combined) for pat in rule.trigger_patterns):
                logger.info("Matched thematic policy catalyst: '%s' on headline: %s", rule.theme_title, headline[:60])

                # Bullish beneficiaries across market caps
                for sym, rationale, score in rule.bullish_beneficiaries:
                    prof = get_company_profile(sym)
                    cname = prof.company_name if prof else sym
                    cap_cat = prof.market_cap_category if prof else "mid_cap"
                    impacts.append(
                        ThematicImpact(
                            symbol=sym,
                            company_name=cname,
                            market_cap_category=cap_cat,
                            direction="bullish",
                            impact_score=score,
                            theme_title=rule.theme_title,
                            rationale=rationale,
                            confidence=86.0,
                        )
                    )

                # Bearish casualties across market caps
                for sym, rationale, score in rule.bearish_casualties:
                    prof = get_company_profile(sym)
                    cname = prof.company_name if prof else sym
                    cap_cat = prof.market_cap_category if prof else "mid_cap"
                    impacts.append(
                        ThematicImpact(
                            symbol=sym,
                            company_name=cname,
                            market_cap_category=cap_cat,
                            direction="bearish",
                            impact_score=score,
                            theme_title=rule.theme_title,
                            rationale=rationale,
                            confidence=88.0,
                        )
                    )

        return impacts

    def evaluate_company_thematic_fit(
        self, symbol: str, headline: str, text: str = ""
    ) -> Optional[Tuple[str, float, str]]:
        """Check if a specific company's known positive/negative catalysts match the news."""
        prof = get_company_profile(symbol)
        if not prof:
            return None

        combined = f"{headline} {text[:300]}".lower()

        # Check positive catalyst alignments
        for cat in prof.positive_catalysts:
            cat_words = [w for w in cat.lower().split() if len(w) >= 4]
            if len(cat_words) >= 2 and all(w in combined for w in cat_words[:2]):
                return ("bullish", 85.0, f"Aligned with core operational catalyst: {cat}")

        # Check negative catalyst alignments
        for cat in prof.negative_catalysts:
            cat_words = [w for w in cat.lower().split() if len(w) >= 4]
            if len(cat_words) >= 2 and all(w in combined for w in cat_words[:2]):
                return ("bearish", 87.0, f"Vulnerable to core operational risk: {cat}")

        return None


# Global singleton instance
_THEMATIC_ENGINE = ThematicEngine()


def get_thematic_engine() -> ThematicEngine:
    """Return singleton instance of ThematicEngine."""
    return _THEMATIC_ENGINE
