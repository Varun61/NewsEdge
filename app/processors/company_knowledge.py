"""Comprehensive Indian equity business models, revenue drivers, and catalyst sensitivities.

Heavy institutional knowledge base detailing business operations, revenue engines,
regulatory exposures, and macro/policy sensitivities across Large, Mid, Small, and
Micro-cap Indian equities on the NSE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CompanyProfile:
    symbol: str
    company_name: str
    sector: str
    industry: str
    market_cap_category: str  # "large_cap", "mid_cap", "small_cap", "micro_cap"
    business_summary: str
    primary_revenue_sources: list[str]
    positive_catalysts: list[str]
    negative_catalysts: list[str]
    regulatory_bodies: list[str] = field(default_factory=list)
    key_competitors: list[str] = field(default_factory=list)


# Heavy knowledge base of Indian equities across market cap spectrum
COMPANY_KNOWLEDGE_BASE: Dict[str, CompanyProfile] = {
    # ══════════════════════════════════════════════════════════════════════════
    # 1. RAILWAYS, ROLLING STOCK, SIGNALING & KAVACH
    # ══════════════════════════════════════════════════════════════════════════
    "RVNL": CompanyProfile(
        symbol="RVNL",
        company_name="Rail Vikas Nigam Limited",
        sector="Capital Goods",
        industry="Railway Infrastructure EPC",
        market_cap_category="mid_cap",
        business_summary="Executes fast-track railway projects: new lines, track doubling, gauge conversion, railway electrification, metro projects, and workshops on turnkey EPC basis.",
        primary_revenue_sources=["Railway EPC contract revenues", "Turnkey metro infrastructure projects", "Overseas rail contracts"],
        positive_catalysts=["Government hike in Railway capex budget", "Major contract wins for new lines/electrification", "Vande Bharat manufacturing/maintenance contracts", "High-speed rail packages"],
        negative_catalysts=["Slowdown in Ministry of Railways project awards", "Margin compression on EPC tenders", "Execution delays"],
        regulatory_bodies=["Ministry of Railways"]
    ),
    "IRFC": CompanyProfile(
        symbol="IRFC",
        company_name="Indian Railway Finance Corporation Limited",
        sector="Financial Services",
        industry="Railway Asset Financing",
        market_cap_category="large_cap",
        business_summary="Dedicated market borrowing arm of the Indian Railways. Borrows to finance acquisition of rolling stock (locomotives, wagons, coaches) and railway infrastructure assets.",
        primary_revenue_sources=["Lease rentals on rolling stock", "Interest income on railway infrastructure loans"],
        positive_catalysts=["Expansion in Indian Railways annual capex borrowing requirement", "Lower borrowing costs / favorable interest rate cycle", "Zero NPA sovereign-backed asset portfolio"],
        negative_catalysts=["Reduction in Indian Railways market borrowing dependency", "Spread compression on lease rentals"],
        regulatory_bodies=["Ministry of Railways", "RBI"]
    ),
    "TITAGARH": CompanyProfile(
        symbol="TITAGARH",
        company_name="Titagarh Rail Systems Limited",
        sector="Capital Goods",
        industry="Rolling Stock & Wagons",
        market_cap_category="mid_cap",
        business_summary="Premier manufacturer of freight wagons, passenger coaches, metro trainsets, electric propulsion systems, and naval ship components.",
        primary_revenue_sources=["Freight wagon sales to Indian Railways", "Metro trainset deliveries", "Passenger coach contracts"],
        positive_catalysts=["Indian Railways mega wagon tenders", "Metro rail coach order wins", "Vande Bharat trainset manufacturing consortia"],
        negative_catalysts=["Steel raw material price surge", "Delays in wagon procurement schedules", "Execution penalties"],
        regulatory_bodies=["Ministry of Railways"]
    ),
    "JWL": CompanyProfile(
        symbol="JWL",
        company_name="Jupiter Wagons Limited",
        sector="Capital Goods",
        industry="Railway Wagons & Castings",
        market_cap_category="small_cap",
        business_summary="Leading manufacturer of railway freight wagons, high-tensile couplers, bogies, CMS crossings, commercial automotive bodies, and braking systems.",
        primary_revenue_sources=["Railway freight wagons", "Bogie and coupler manufacturing", "Brake systems"],
        positive_catalysts=["Indian Railways wagon procurement orders", "Private freight operator wagon purchases", "Brake disc and casting contract awards"],
        negative_catalysts=["Steel input cost spikes", "Order postponement by railways"],
        regulatory_bodies=["Ministry of Railways"]
    ),
    "TEXRAIL": CompanyProfile(
        symbol="TEXRAIL",
        company_name="Texmaco Rail & Engineering Limited",
        sector="Capital Goods",
        industry="Wagons, Track Works & Bridges",
        market_cap_category="small_cap",
        business_summary="Specialized manufacturer of freight wagons, specialized container flats, hydro-mechanical equipment, steel bridges, and track laying EPC.",
        primary_revenue_sources=["Freight wagons for railways and private miners", "Track renewal and electrification EPC", "Steel bridge girders"],
        positive_catalysts=["Railways annual rolling stock tenders", "Dedicated Freight Corridor feeder line orders", "Wagon export contracts"],
        negative_catalysts=["High working capital intensity", "Steel price escalation clauses delay"],
        regulatory_bodies=["Ministry of Railways"]
    ),
    "KERNEX": CompanyProfile(
        symbol="KERNEX",
        company_name="Kernex Microsystems (India) Limited",
        sector="Information Technology",
        industry="Railway Safety & Kavach TCAS",
        market_cap_category="micro_cap",
        business_summary="Pioneer in railway automatic train collision prevention systems (Kavach / TCAS), electronic interlocking, level crossing protection, and railway signal safety software.",
        primary_revenue_sources=["Kavach on-board loco devices and station equipment", "Automatic level crossing gate systems", "Signaling turnkey supply"],
        positive_catalysts=["Indian Railways tenders for Kavach deployment across 10,000+ route km", "Mandatory train protection adoption", "High operating leverage on hardware deployment"],
        negative_catalysts=["Tender qualification delays", "Supply chain constraints in microcontrollers", "Slow milestone execution"],
        regulatory_bodies=["Ministry of Railways", "RDSO"]
    ),
    "RAILTEL": CompanyProfile(
        symbol="RAILTEL",
        company_name="RailTel Corporation of India Limited",
        sector="Telecommunication",
        industry="Telecom & Rail Signaling ICT",
        market_cap_category="small_cap",
        business_summary="Operates nationwide optical fiber network along railway corridors, data centers, station Wi-Fi, and electronic railway signaling / Kavach implementation.",
        primary_revenue_sources=["Telecom bandwidth & dark fiber", "Project execution (Kavach, signaling, CCTV)", "Data center and cloud hosting"],
        positive_catalysts=["Kavach automatic train protection rollouts across routes", "Govt optical fiber / BharatNet orders", "Signaling modernization orders"],
        negative_catalysts=["Lower telecom enterprise pricing", "Delay in Kavach tender rollouts"],
        regulatory_bodies=["Ministry of Railways", "DoT"]
    ),
    "IRCON": CompanyProfile(
        symbol="IRCON",
        company_name="Ircon International Limited",
        sector="Capital Goods",
        industry="Railway & Highway Construction EPC",
        market_cap_category="small_cap",
        business_summary="Turnkey construction PSU executing complex railway lines in hilly terrains (J&K rail link), highway EPC, bridges, tunnels, and international railway projects.",
        primary_revenue_sources=["Railway line construction EPC", "Highway road projects", "International rail infrastructure (Malaysia, Algeria, Sri Lanka)"],
        positive_catalysts=["High-speed railway construction packages", "Cross-border rail connectivity projects", "Healthy order book with sovereign backing"],
        negative_catalysts=["Sub-contractor execution defaults", "Geopolitical risks in overseas projects"],
        regulatory_bodies=["Ministry of Railways"]
    ),
    "RITES": CompanyProfile(
        symbol="RITES",
        company_name="RITES Limited",
        sector="Services",
        industry="Railway Consulting, Engineering & Export",
        market_cap_category="small_cap",
        business_summary="Leading transport infrastructure consultancy; provides project management, quality inspection, railway rolling stock leasing, and export of custom locomotives.",
        primary_revenue_sources=["Consultancy and engineering fees", "Locomotive and coach exports to Africa/Asia", "Rolling stock leasing to domestic ports/plants"],
        positive_catalysts=["Metro DPR preparation contracts", "Locomotive export orders to developing countries", "Third-party quality inspection mandates"],
        negative_catalysts=["Lower consultancy margins on competitive bidding", "Delay in export shipments"],
        regulatory_bodies=["Ministry of Railways"]
    ),
    "BEML": CompanyProfile(
        symbol="BEML",
        company_name="BEML Limited",
        sector="Capital Goods",
        industry="Metro Coaches, Mining & Defence",
        market_cap_category="mid_cap",
        business_summary="Diversified public engineering company manufacturing metro train coaches, high-tonnage mining dumpers, bulldozers, and heavy defence tactical military vehicles.",
        primary_revenue_sources=["Metro coach supplies (Vande Metro, Bangalore, Mumbai metro)", "Heavy mining dumpers and excavators for Coal India", "Defence tactical vehicles (Tatra)"],
        positive_catalysts=["Vande Bharat sleeper trainset orders", "Urban metro rail expansion tenders", "Defence Pinaka rocket launcher chassis orders"],
        negative_catalysts=["Coal India mining capex cutbacks", "Imported component currency depreciation"],
        regulatory_bodies=["Ministry of Defence", "Ministry of Railways"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 2. DEFENCE, AEROSPACE, DRONES & COMBAT SIMULATION
    # ══════════════════════════════════════════════════════════════════════════
    "HAL": CompanyProfile(
        symbol="HAL",
        company_name="Hindustan Aeronautics Limited",
        sector="Capital Goods",
        industry="Defence Aerospace & Aircraft",
        market_cap_category="large_cap",
        business_summary="Premier aerospace company manufacturing fighter jets (Tejas LCA, Su-30MKI), combat helicopters (Prachand LCH, Dhruv ALH), aero engines, and avionics.",
        primary_revenue_sources=["Defence aircraft and helicopter production", "Repair, overhaul (MRO) and spare parts for armed forces"],
        positive_catalysts=["DAC capital procurement approvals", "Tejas Mk1A bulk deliveries", "Aero-engine co-production deals (GE/Safran)", "Defence export orders"],
        negative_catalysts=["Delays in engine supply chains", "Defence capital budget cutbacks"],
        regulatory_bodies=["Ministry of Defence"]
    ),
    "BEL": CompanyProfile(
        symbol="BEL",
        company_name="Bharat Electronics Limited",
        sector="Capital Goods",
        industry="Defence Electronics & Radars",
        market_cap_category="large_cap",
        business_summary="Navratna defence PSU manufacturing naval and land surveillance radars, electronic warfare systems, missile electronics, electro-optics, and secure communications.",
        primary_revenue_sources=["Surveillance radars and sonar systems", "Electronic warfare and missile communications", "Non-defence electronics (EVMs, metro controls)"],
        positive_catalysts=["Mega radar/sonar orders from Indian Navy/Army", "Indigenous defence procurement mandates (Positive Indigenisation List)", "Order book exceeding ₹75,000 Cr"],
        negative_catalysts=["Global semiconductor component bottlenecks", "Lower gross margins on competitive tenders"],
        regulatory_bodies=["Ministry of Defence"]
    ),
    "MAZDOCK": CompanyProfile(
        symbol="MAZDOCK",
        company_name="Mazagon Dock Shipbuilders Limited",
        sector="Capital Goods",
        industry="Defence Shipbuilding & Submarines",
        market_cap_category="mid_cap",
        business_summary="Builds conventional diesel-electric attack submarines (Scorpene / Project 75), guided missile destroyers (Project 15B), and stealth frigates for the Indian Navy.",
        primary_revenue_sources=["Naval warship and submarine construction", "Ship repair and mid-life submarine upgrades", "Offshore engineering"],
        positive_catalysts=["Project 75(I) submarine construction sanction", "Next-Gen Corvette (NGC) contracts", "Export warship orders from foreign navies"],
        negative_catalysts=["Long gestation execution cycles", "Steel and specialized combat system cost escalations"],
        regulatory_bodies=["Ministry of Defence"]
    ),
    "COCHINSHIP": CompanyProfile(
        symbol="COCHINSHIP",
        company_name="Cochin Shipyard Limited",
        sector="Capital Goods",
        industry="Shipbuilding & Commercial Vessels",
        market_cap_category="mid_cap",
        business_summary="Built India's first indigenous aircraft carrier (INS Vikrant); builds anti-submarine warfare shallow water crafts, green zero-emission European vessels, and runs large ship repair dry docks.",
        primary_revenue_sources=["Defence warship construction", "Commercial shipbuilding for European/domestic clients", "Ship repair services across Indian ports"],
        positive_catalysts=["Second indigenous aircraft carrier (IAC-2) approval", "Green electric vessel export orders", "Expansion of ship repair dry docks"],
        negative_catalysts=["Steel input cost volatility", "Delay in naval procurement sanction"],
        regulatory_bodies=["Ministry of Ports, Shipping and Waterways", "Ministry of Defence"]
    ),
    "GRSE": CompanyProfile(
        symbol="GRSE",
        company_name="Garden Reach Shipbuilders & Engineers Limited",
        sector="Capital Goods",
        industry="Defence Warships & Fast Patrol Vessels",
        market_cap_category="small_cap",
        business_summary="Constructs stealth frigates (Project 17A), anti-submarine warfare corvettes, survey vessels, and fast patrol crafts for the Indian Navy and Coast Guard.",
        primary_revenue_sources=["Warship construction and survey ships", "Bailey bridge manufacturing", "Marine diesel engines"],
        positive_catalysts=["Next-Gen Offshore Patrol Vessel (NGOPV) orders", "Export contracts to friendly littoral nations", "Fast delivery milestone realizations"],
        negative_catalysts=["Lumpy quarterly revenue recognition", "Shipyard berth capacity constraints"],
        regulatory_bodies=["Ministry of Defence"]
    ),
    "BDL": CompanyProfile(
        symbol="BDL",
        company_name="Bharat Dynamics Limited",
        sector="Capital Goods",
        industry="Missiles & Munitions",
        market_cap_category="small_cap",
        business_summary="Sole national manufacturer of surface-to-air missiles (Akash), anti-tank guided missiles (Nag, Konkurs), underwater torpedoes, and counter-measure dispensing systems.",
        primary_revenue_sources=["Missile systems manufacturing", "Ammunition and counter-measure dispensing systems"],
        positive_catalysts=["Akash missile export contracts to friendly nations", "Domestic order intake for next-gen missile systems", "Army/Air Force munitions tenders"],
        negative_catalysts=["Supply chain constraints for missile seekers and propellant electronics", "Quarterly lumpy deliveries"],
        regulatory_bodies=["Ministry of Defence"]
    ),
    "ZENTEC": CompanyProfile(
        symbol="ZENTEC",
        company_name="Zen Technologies Limited",
        sector="Capital Goods",
        industry="Anti-Drone Systems & Combat Simulators",
        market_cap_category="small_cap",
        business_summary="Specializes in indigenous anti-drone defense systems (CUAS - soft & hard kill), combat training simulators, live firing ranges, and armor target systems for armed forces.",
        primary_revenue_sources=["Anti-drone detection & jammer hardware", "Military training simulators", "Annual maintenance contracts (AMC)"],
        positive_catalysts=["Drone and anti-drone procurement mandates by Indian Army and Air Force", "Export orders from Middle East and African defence forces", "High-margin proprietary IP and software"],
        negative_catalysts=["High single-quarter revenue volatility based on defence acceptance trials", "Working capital elongation"],
        regulatory_bodies=["Ministry of Defence"]
    ),
    "PARAS": CompanyProfile(
        symbol="PARAS",
        company_name="Paras Defence and Space Technologies Limited",
        sector="Capital Goods",
        industry="Defence Optics & EMP Protection",
        market_cap_category="micro_cap",
        business_summary="Niche manufacturer of military optics and opto-electronics (thermal imaging lenses, submarine periscopes), EMP protection shielding, and space satellite camera assemblies for ISRO.",
        primary_revenue_sources=["Defence opto-electronics", "EMP protection solutions for critical defence infrastructure", "Space mirrors and satellite structures"],
        positive_catalysts=["ISRO satellite launch payloads", "Anti-drone optical tracker integration", "Make-in-India optronics tenders"],
        negative_catalysts=["Customer concentration with government PSUs", "Long testing and certification cycles"],
        regulatory_bodies=["Ministry of Defence", "ISRO"]
    ),
    "DATAPATTNS": CompanyProfile(
        symbol="DATAPATTNS",
        company_name="Data Patterns (India) Limited",
        sector="Capital Goods",
        industry="Defence Avionics & Radars",
        market_cap_category="small_cap",
        business_summary="Vertically integrated defense electronics manufacturer specializing in airborne radars, electronic warfare (EW) suites, satellite electronics, and missile seeker processors.",
        primary_revenue_sources=["Radars and electronic warfare systems", "Avionics and flight computers", "Small satellite communication payloads"],
        positive_catalysts=["Tejas Mk1A radar processor integration", "Military satellite communication contracts", "Export orders for EW systems"],
        negative_catalysts=["High gestation product development cycles", "Shortage of high-reliability electronic chips"],
        regulatory_bodies=["Ministry of Defence", "DRDO"]
    ),
    "ASTRAMICRO": CompanyProfile(
        symbol="ASTRAMICRO",
        company_name="Astra Microwave Products Limited",
        sector="Capital Goods",
        industry="Microwave & RF Subsystems",
        market_cap_category="small_cap",
        business_summary="Designs and manufactures sub-systems for radio frequency (RF) and microwave super-components used in defence radars, telemetry, electronic warfare, and space payloads.",
        primary_revenue_sources=["Radar RF sub-systems and transceivers", "Electronic warfare modules", "Space and satellite microwave components"],
        positive_catalysts=["Uttam AESA radar series production for fighter jets", "Border surveillance radar expansion", "Space ground station equipment orders"],
        negative_catalysts=["Import dependency on foreign gallium nitride / specialized semiconductor dies", "Lumpy order placement"],
        regulatory_bodies=["Ministry of Defence", "DRDO"]
    ),
    "MTARTECH": CompanyProfile(
        symbol="MTARTECH",
        company_name="Mtar Technologies Limited",
        sector="Capital Goods",
        industry="Precision Engineering & Clean Energy",
        market_cap_category="small_cap",
        business_summary="Manufactures high-precision mission-critical assemblies for civilian nuclear power reactors, space satellite engines (Vikas engine for ISRO), missiles, and Bloom Energy fuel cells.",
        primary_revenue_sources=["Clean energy fuel cell hot boxes (Bloom Energy)", "Space launch vehicle propulsion engines", "Nuclear reactor control rod drive mechanisms"],
        positive_catalysts=["NPCIL 10-fleet nuclear reactor procurement orders", "ISRO Gaganyaan and commercial rocket launches", "Bloom Energy global hydrogen expansion"],
        negative_catalysts=["Client concentration with Bloom Energy export demand", "Raw material titanium and nickel alloy price surges"],
        regulatory_bodies=["Department of Atomic Energy", "ISRO"]
    ),
    "SOLARINDS": CompanyProfile(
        symbol="SOLARINDS",
        company_name="Solar Industries India Limited",
        sector="Chemicals",
        industry="Industrial Explosives & Defence Warheads",
        market_cap_category="large_cap",
        business_summary="Global leader in packaged industrial explosives for mining and infrastructure; expanded heavily into military ammunition, multi-mode hand grenades, Pinaka rockets, and loitering munitions.",
        primary_revenue_sources=["Industrial bulk explosives for mining (Coal India)", "Military ammunition and weaponized loitering munitions (drones)", "Defence rocket warheads (Pinaka)"],
        positive_catalysts=["Indian Army orders for Pinaka enhanced rockets and hand grenades", "Loitering munition export contracts", "Domestic mining volume growth"],
        negative_catalysts=["Ammonium nitrate raw material price spikes", "Export license delays"],
        regulatory_bodies=["PESO", "Ministry of Defence"]
    ),
    "IDEAFORGE": CompanyProfile(
        symbol="IDEAFORGE",
        company_name="Ideaforge Technology Limited",
        sector="Capital Goods",
        industry="UAVs & Surveillance Drones",
        market_cap_category="micro_cap",
        business_summary="Market leader in indigenous Unmanned Aerial Vehicles (UAVs) and surveillance drones for defense (border surveillance, high-altitude tactical ops) and civil mapping (SVAMITVA scheme).",
        primary_revenue_sources=["Surveillance drones for armed forces and police", "Civil drone mapping hardware and software services"],
        positive_catalysts=["High-altitude border surveillance procurement", "Police and homeland security drone contracts", "Agricultural drone adoption"],
        negative_catalysts=["Lumpy tender execution", "Intense competition from emerging private drone startups"],
        regulatory_bodies=["DGCA", "Ministry of Civil Aviation"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 3. POWER, RENEWABLE, SOLAR, WIND & TRANSMISSION
    # ══════════════════════════════════════════════════════════════════════════
    "SUZLON": CompanyProfile(
        symbol="SUZLON",
        company_name="Suzlon Energy Limited",
        sector="Capital Goods",
        industry="Wind Turbine Manufacturing & EPC",
        market_cap_category="mid_cap",
        business_summary="Pioneer and domestic leader in wind turbine generators (WTGs), offering complete EPC, wind farm commissioning, and long-term O&M service contracts.",
        primary_revenue_sources=["Sale of 2.1 MW and 3.14 MW wind turbines", "Operation & maintenance (O&M) service annuity contracts"],
        positive_catalysts=["MNRE aggressive wind auction schedules", "Large captive C&I and PSU wind order wins", "Net cash balance sheet expanding margins"],
        negative_catalysts=["Grid connectivity / substation transmission bottlenecks", "Tariff caps in competitive bidding", "Commodity steel inflation"],
        regulatory_bodies=["MNRE", "CERC"]
    ),
    "INOXWIND": CompanyProfile(
        symbol="INOXWIND",
        company_name="Inox Wind Limited",
        sector="Capital Goods",
        industry="Wind Turbine Generators",
        market_cap_category="small_cap",
        business_summary="Manufactures advanced wind turbine generators (3.3 MW platform), rotor blades, tubular towers, and provides turnkey balance-of-plant solutions.",
        primary_revenue_sources=["Wind turbine supply and installation", "EPC services for wind farms", "Power evacuation infrastructure"],
        positive_catalysts=["Reverse-auction transition to plain bidding", "Order book crossing 3,000 MW", "Debt reduction via parent support"],
        negative_catalysts=["Delays in land acquisition for wind sites", "Discom power purchase agreement renegotiations"],
        regulatory_bodies=["MNRE"]
    ),
    "BORORENEW": CompanyProfile(
        symbol="BORORENEW",
        company_name="Borosil Renewables Limited",
        sector="Capital Goods",
        industry="Solar Glass Manufacturing",
        market_cap_category="small_cap",
        business_summary="Sole domestic manufacturer of specialized solar glass used in photovoltaic (PV) modules, operating energy-efficient furnaces in Gujarat.",
        primary_revenue_sources=["Anti-reflective patterned solar glass sales to module makers"],
        positive_catalysts=["Government imposition of anti-dumping duty on cheap Chinese/Vietnamese solar glass", "ALMM (Approved List of Module Manufacturers) strict enforcement", "Domestic solar module manufacturing capacity boom"],
        negative_catalysts=["Unchecked Chinese solar glass dumping at below cost", "Natural gas / power input cost spikes at glass furnaces"],
        regulatory_bodies=["Directorate General of Trade Remedies (DGTR)", "MNRE"]
    ),
    "KPIGREEN": CompanyProfile(
        symbol="KPIGREEN",
        company_name="KPI Green Energy Limited",
        sector="Power",
        industry="Solar & Hybrid IPP & EPC",
        market_cap_category="small_cap",
        business_summary="Fast-growing solar and wind-solar hybrid power producer (IPP) and captive power producer (CPP) with massive multi-gigawatt pipeline in Gujarat.",
        primary_revenue_sources=["Sale of green electricity to commercial and industrial (C&I) clients", "Solar EPC contract execution"],
        positive_catalysts=["Gujarat solar policy incentives", "Open-access green energy adoption by industries", "Accelerated commissioning of solar-wind parks"],
        negative_catalysts=["Curtailment risk by state load dispatch centers", "Interest rate hikes on debt-funded capacity"],
        regulatory_bodies=["GERC", "Ministry of Power"]
    ),
    "IREDA": CompanyProfile(
        symbol="IREDA",
        company_name="Indian Renewable Energy Development Agency Limited",
        sector="Financial Services",
        industry="Green Energy Financing NBFC",
        market_cap_category="mid_cap",
        business_summary="Navratna PSU dedicated to financing renewable energy, solar parks, wind projects, hydro, green hydrogen, and EV infrastructure across India.",
        primary_revenue_sources=["Interest income on renewable energy project loans", "Financial advisory and syndication fees"],
        positive_catalysts=["National target of 500 GW non-fossil capacity by 2030", "Navratna upgrade lowering global borrowing costs", "Low NPA ratio backed by project escrow mechanisms"],
        negative_catalysts=["Slippages in small hydro or biomass loans", "Spread compression as private banks enter green lending"],
        regulatory_bodies=["MNRE", "RBI"]
    ),
    "WAAREEENER": CompanyProfile(
        symbol="WAAREEENER",
        company_name="Waaree Energies Limited",
        sector="Capital Goods",
        industry="Solar PV Modules & Cells",
        market_cap_category="large_cap",
        business_summary="India's largest solar PV module manufacturer with 12+ GW capacity; operates massive domestic plants and exports solar panels heavily to the US.",
        primary_revenue_sources=["Solar PV module sales to utility-scale solar developers", "Solar module exports to the United States", "EPC rooftop solar installations"],
        positive_catalysts=["PM Surya Ghar Muft Bijli Yojana (1 crore rooftop solar homes)", "US Section 301 tariffs on Chinese panels favoring Indian exports", "PLI solar cell integration"],
        negative_catalysts=["US customs detention or tariff shifts on Southeast Asian/Indian supply chains", "Polysilicon price volatility"],
        regulatory_bodies=["MNRE", "Ministry of Finance"]
    ),
    "PREMIERENE": CompanyProfile(
        symbol="PREMIERENE",
        company_name="Premier Energies Limited",
        sector="Capital Goods",
        industry="Solar Cells & Bifacial Modules",
        market_cap_category="mid_cap",
        business_summary="Leading integrated solar cell and module manufacturer, producing high-efficiency TOPCon solar cells and bifacial modules.",
        primary_revenue_sources=["Solar cell sales to domestic module makers", "High-efficiency bifacial solar modules for utility projects"],
        positive_catalysts=["Mandatory domestic content requirement (DCR) for government projects", "Rapid transition to TOPCon cell tech", "Expansion into US export markets"],
        negative_catalysts=["Polysilicon feedstock supply dependency", "Rapid technology obsolescence"],
        regulatory_bodies=["MNRE"]
    ),
    "APARINDS": CompanyProfile(
        symbol="APARINDS",
        company_name="Apar Industries Limited",
        sector="Capital Goods",
        industry="Transmission Conductors & Cables",
        market_cap_category="mid_cap",
        business_summary="World's largest manufacturer of aluminium and alloy transmission conductors, specialized electrical cables for renewables/defence, and transformer oils.",
        primary_revenue_sources=["HTLS and high-efficiency power transmission conductors", "Specialty cables for solar, wind, and rolling stock", "Transformer naphthenic oils"],
        positive_catalysts=["Global and domestic transmission grid expansion (Green Energy Corridors)", "US and European power grid re-conductoring demand", "Aluminium premium pass-through"],
        negative_catalysts=["Base metal aluminium and copper price volatility", "Shipping freight rate spikes for global exports"],
        regulatory_bodies=["Ministry of Power"]
    ),
    "KEC": CompanyProfile(
        symbol="KEC",
        company_name="KEC International Limited",
        sector="Capital Goods",
        industry="Power Transmission & Rail EPC",
        market_cap_category="small_cap",
        business_summary="Global infrastructure EPC major; designs and constructs high-voltage power transmission lines, substations, railway electrification, civil infrastructure, and solar projects.",
        primary_revenue_sources=["Power transmission line EPC in India, Middle East, and Americas", "Railway electrification and signaling", "Civil industrial plants"],
        positive_catalysts=["High-voltage Green Energy Corridor tenders in India", "Middle East grid interconnection orders", "Railway overhead electrification tenders"],
        negative_catalysts=["Execution delays in international geography", "High interest costs on working capital debt"],
        regulatory_bodies=["Ministry of Power"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 4. ELECTRIC VEHICLES, BATTERIES & AUTO ANCILLARIES
    # ══════════════════════════════════════════════════════════════════════════
    "OLECTRA": CompanyProfile(
        symbol="OLECTRA",
        company_name="Olectra Greentech Limited",
        sector="Automobile",
        industry="Electric Buses & Heavy Commercial EVs",
        market_cap_category="small_cap",
        business_summary="Pioneer in electric bus manufacturing in India with technical collaboration from BYD; operates and supplies thousands of zero-emission e-buses to state transport undertakings (STUs).",
        primary_revenue_sources=["Electric bus sales to state transport undertakings", "Gross cost contract (GCC) operating fee per kilometer"],
        positive_catalysts=["PM-eBus Sewa scheme (deploying 10,000 electric buses across Indian cities)", "State government electric bus tenders", "E-truck commercial launch"],
        negative_catalysts=["State transport undertaking delayed payment collections", "Battery cell supply chain dependence on China"],
        regulatory_bodies=["Ministry of Heavy Industries", "MORTH"]
    ),
    "JBMA": CompanyProfile(
        symbol="JBMA",
        company_name="JBM Auto Limited",
        sector="Automobile",
        industry="Electric Buses & Automotive Components",
        market_cap_category="small_cap",
        business_summary="Manufactures electric buses (ECOLIFE), EV charging infrastructure, lithium battery packs, and sheet metal auto components for Maruti, Tata, and M&M.",
        primary_revenue_sources=["ECOLIFE electric bus deliveries to transit authorities", "Automotive sheet metal stampings and exhaust systems"],
        positive_catalysts=["Bulk e-bus awards under CESL national tenders", "PM-eBus Sewa deployment contracts", "Auto component volume recovery"],
        negative_catalysts=["High debt for bus fleet capitalization", "Working capital drag from municipal transport corporations"],
        regulatory_bodies=["Ministry of Heavy Industries"]
    ),
    "EXIDEIND": CompanyProfile(
        symbol="EXIDEIND",
        company_name="Exide Industries Limited",
        sector="Automobile",
        industry="Lead-Acid & Lithium-Ion Gigafactory",
        market_cap_category="mid_cap",
        business_summary="India's largest lead-acid storage battery company; constructing multi-gigawatt lithium-ion battery cell gigafactory in Bengaluru with SVOLT tech partnership.",
        primary_revenue_sources=["Automotive OEM and replacement batteries", "Industrial telecom and UPS storage batteries", "Upcoming EV lithium battery cells"],
        positive_catalysts=["Commercial commissioning of lithium battery gigafactory", "OEM supply tie-ups for electric 2-wheelers and 4-wheelers", "Lead price softness"],
        negative_catalysts=["Lead metal price inflation", "Initial gestation losses at lithium gigafactory", "Rapid loss of lead-acid share in e-rickshaws"],
        regulatory_bodies=["Ministry of Heavy Industries"]
    ),
    "ARE&M": CompanyProfile(
        symbol="ARE&M",
        company_name="Amara Raja Energy & Mobility Limited",
        sector="Automobile",
        industry="Storage Batteries & EV Giga-Corridor",
        market_cap_category="mid_cap",
        business_summary="Major manufacturer of automotive (Amaron brand) and industrial batteries; investing in a 16 GWh lithium-ion cell gigafactory and battery pack assembly in Telangana.",
        primary_revenue_sources=["Automotive replacement batteries (Amaron)", "Industrial telecom and data center power backup", "EV 2W/3W lithium pack assembly"],
        positive_catalysts=["Tie-up with Gotion for LFP cell manufacturing", "Telecom 5G tower battery upgrade demand", "Expansion in international battery exports"],
        negative_catalysts=["High lead raw material prices", "Intense competition from Exide in automotive aftermarket"],
        regulatory_bodies=["Ministry of Heavy Industries"]
    ),
    "SONACOMS": CompanyProfile(
        symbol="SONACOMS",
        company_name="Sona BLW Precision Forgings Limited",
        sector="Automobile",
        industry="EV Driveline & Traction Motors",
        market_cap_category="mid_cap",
        business_summary="Global supplier of highly engineered automotive driveline systems, differential gears, traction motors, and motor control units with very high EV revenue share (30%+).",
        primary_revenue_sources=["Differential assemblies and gears for global electric vehicles", "Traction motors for electric 2W/3W and light commercial vehicles"],
        positive_catalysts=["Global electric vehicle volume growth (Tesla, European OEMs)", "New program wins for integrated motor-inverters", "High technological entry barriers"],
        negative_catalysts=["Slowdown in US/European EV adoption rates", "Rare earth magnet price volatility"],
        regulatory_bodies=["MORTH"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 5. ELECTRONICS MANUFACTURING SERVICES (EMS) & HARDWARE
    # ══════════════════════════════════════════════════════════════════════════
    "DIXON": CompanyProfile(
        symbol="DIXON",
        company_name="Dixon Technologies (India) Limited",
        sector="Consumer Durables",
        industry="Electronics Manufacturing Services (EMS)",
        market_cap_category="large_cap",
        business_summary="India's electronic manufacturing giant; manufactures smartphones (Motorola, Xiaomi), LED TVs, home appliances, telecom equipment, and laptops under government PLI schemes.",
        primary_revenue_sources=["Mobile phone contract manufacturing", "Consumer electronics (LED TVs, washing machines)", "Lighting products and security surveillance"],
        positive_catalysts=["Government Production Linked Incentive (PLI) approvals", "Global OEM shifting production from China to India", "Laptop / IT hardware PLI contract wins"],
        negative_catalysts=["Thin operating margins (3-4%) vulnerable to component price rises", "Loss of anchor client contract"],
        regulatory_bodies=["MeitY"]
    ),
    "KAYNES": CompanyProfile(
        symbol="KAYNES",
        company_name="Kaynes Technology India Limited",
        sector="Capital Goods",
        industry="High-Reliability Industrial & Defence EMS",
        market_cap_category="mid_cap",
        business_summary="Leading electronics system design and manufacturing (ESDM) player specialized in high-margin printed circuit board assemblies (PCBA) for automotive, railways (Kavach), defence, and aerospace; setting up advanced OSAT semiconductor testing facility.",
        primary_revenue_sources=["Industrial electronics and automotive PCBA", "Railway signaling and Kavach electronic units", "Aerospace and defence electronics"],
        positive_catalysts=["Semiconductor OSAT plant subsidies from central and state govt", "Kavach mass manufacturing orders", "Expansion into high-margin export box-builds"],
        negative_catalysts=["Working capital expansion during OSAT capex", "Semiconductor component delivery delays"],
        regulatory_bodies=["MeitY", "India Semiconductor Mission (ISM)"]
    ),
    "SYRMA": CompanyProfile(
        symbol="SYRMA",
        company_name="Syrma SGS Technology Limited",
        sector="Capital Goods",
        industry="Precision EMS & RFID Technology",
        market_cap_category="mid_cap",
        business_summary="Technology-focused engineering and electronics manufacturer; produces RFID tags, electromagnetic coils, memory modules, automotive electronics, and medical devices.",
        primary_revenue_sources=["Precision PCBA for consumer, healthcare, and industrial sectors", "RFID tags and magnetic components", "Box-build turnkey manufacturing"],
        positive_catalysts=["Record quarterly revenue expansion in industrial EMS", "Export demand in healthcare and RFID tracking", "Government electronic component PLI incentives"],
        negative_catalysts=["Pricing pressure from global EMS competitors", "Client concentration in consumer electronics"],
        regulatory_bodies=["MeitY"]
    ),
    "CYIENTDLM": CompanyProfile(
        symbol="CYIENTDLM",
        company_name="Cyient DLM Limited",
        sector="Capital Goods",
        industry="Aerospace & Defence EMS Box-Build",
        market_cap_category="small_cap",
        business_summary="Electronic manufacturing company focused exclusively on highly regulated mission-critical aerospace, defence, and medical electronics requiring build-to-print and build-to-spec capabilities.",
        primary_revenue_sources=["Cockpit avionics and aircraft navigation electronics", "Medical life-support equipment assemblies", "Industrial automation controllers"],
        positive_catalysts=["Offset contracts from global aerospace giants (Honeywell, Bharat Electronics)", "High-margin box-build share rising above 40%", "Defence order book growth"],
        negative_catalysts=["Lengthy certification and qualification cycles for aerospace parts", "Single-client program delivery delays"],
        regulatory_bodies=["DGCA", "FAA", "Ministry of Defence"]
    ),
    "PGEL": CompanyProfile(
        symbol="PGEL",
        company_name="PG Electroplast Limited",
        sector="Consumer Durables",
        industry="Consumer Durables EMS & Plastic Molding",
        market_cap_category="small_cap",
        business_summary="Integrated manufacturing partner for leading consumer durable brands; manufactures room air conditioners, washing machines, smart meters, and high-precision plastic components.",
        primary_revenue_sources=["Complete room air conditioner assembly", "Washing machine ODM/OEM manufacturing", "Plastic molding for consumer electronics"],
        positive_catalysts=["Heatwave and summer seasonal demand surge for air conditioners", "Smart meter manufacturing contract awards", "White goods PLI disbursement"],
        negative_catalysts=["Unseasonal rainfall cooling summer AC demand", "Polypropylene / ABS plastic resin price spikes"],
        regulatory_bodies=["DPIIT"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 6. SUGAR, BIOFUELS & ETHANOL DISTILLERIES
    # ══════════════════════════════════════════════════════════════════════════
    "BALRAMCHIN": CompanyProfile(
        symbol="BALRAMCHIN",
        company_name="Balrampur Chini Mills Limited",
        sector="FMCG",
        industry="Sugar & Ethanol Distilleries",
        market_cap_category="mid_cap",
        business_summary="Premier integrated sugar manufacturer in Uttar Pradesh; produces refined sugar, ethanol for fuel blending with OMCs, molasses, power cogeneration, and PLA bioplastics.",
        primary_revenue_sources=["Sugar sales to industrial/domestic users", "Ethanol supplies to OMCs for E20 national blending", "Co-generation power to state grid"],
        positive_catalysts=["Government hike in ethanol procurement prices for grain/B-heavy molasses", "Acceleration of 20% ethanol blending target", "Sugar Minimum Selling Price (MSP) hike", "Export quota allocations"],
        negative_catalysts=["Government ban/restriction on using sugarcane juice/syrup for ethanol", "Restrictions on sugar exports", "Imposition of stock limits on sugar mills", "Hike in State Advised Price (SAP) for cane"],
        regulatory_bodies=["Ministry of Consumer Affairs, Food and Public Distribution", "OOMCs"]
    ),
    "PRAJIND": CompanyProfile(
        symbol="PRAJIND",
        company_name="Praj Industries Limited",
        sector="Capital Goods",
        industry="Biofuel & Ethanol Plant Engineering",
        market_cap_category="small_cap",
        business_summary="World's leading bio-process technology company; engineers and builds over 70% of India's ethanol distilleries, 2G second-generation cellulosic ethanol plants, and sustainable aviation fuel (SAF) units.",
        primary_revenue_sources=["Ethanol plant turnkey engineering and equipment (1G/2G)", "Critical process equipment for breweries and wastewater treatment", "Biotech and enzyme solutions"],
        positive_catalysts=["Govt mandatory blending of Sustainable Aviation Fuel (SAF)", "Global grain-based and corn-based ethanol plant orders", "2G ethanol commercial commercialization"],
        negative_catalysts=["Domestic distillery capex cycle slowdown if sugar policy stalls", "Delayed milestone payments from private distillery promoters"],
        regulatory_bodies=["Ministry of Petroleum and Natural Gas"]
    ),
    "TRIVENI": CompanyProfile(
        symbol="TRIVENI",
        company_name="Triveni Engineering & Industries Limited",
        sector="FMCG",
        industry="Sugar, Ethanol & High-Speed Gears",
        market_cap_category="small_cap",
        business_summary="Diversified conglomerate with integrated sugar mills, modern dual-feed ethanol distilleries in UP, and an engineered industrial high-speed gear manufacturing division for naval and thermal plants.",
        primary_revenue_sources=["Sugar production and ethanol distillery sales", "High-speed industrial and naval marine gears", "Water and wastewater treatment EPC"],
        positive_catalysts=["OMC ethanol price increases", "Indian Navy marine gearbox contracts", "Sugar domestic price firming"],
        negative_catalysts=["Sugar export bans", "Cane SAP hike by UP state govt"],
        regulatory_bodies=["Ministry of Consumer Affairs", "Ministry of Defence"]
    ),
    "EIDPARRY": CompanyProfile(
        symbol="EIDPARRY",
        company_name="E.I.D. - Parry (India) Limited",
        sector="FMCG",
        industry="Sugar, Nutraceuticals & Agri Inputs",
        market_cap_category="mid_cap",
        business_summary="Murugappa Group company operating sugar mills and distilleries in South India; parent company of agrochem major Coromandel International.",
        primary_revenue_sources=["Sugar and ethanol sales", "Dividends and consolidated profits from Coromandel International", "Nutraceutical spirulina products"],
        positive_catalysts=["Ethanol blending price hikes", "Strong agricultural performance at subsidiary Coromandel", "Sugar realization increases"],
        negative_catalysts=["Drought in Southern cane growing belts", "Fertilizer subsidy cuts at subsidiary level"],
        regulatory_bodies=["Ministry of Consumer Affairs"]
    ),
    "BCLIND": CompanyProfile(
        symbol="BCLIND",
        company_name="Bcl Industries Limited",
        sector="FMCG",
        industry="Grain-Based Ethanol Distilleries",
        market_cap_category="micro_cap",
        business_summary="One of India's largest grain-based ethanol manufacturers operating distilleries in Punjab and West Bengal utilizing broken rice and maize, plus edible oil refining.",
        primary_revenue_sources=["Grain-based ethanol supply to oil marketing companies", "Edible oil extraction (Vanaspati, refined mustard oil)"],
        positive_catalysts=["Higher OMC procurement rates for maize and damaged food grain ethanol", "Capacity expansion in West Bengal distillery", "Zero reliance on cane restrictions"],
        negative_catalysts=["Maize and grain feedstock price spikes", "Working capital elongation"],
        regulatory_bodies=["Ministry of Petroleum and Natural Gas"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 7. FERTILIZERS, AGROCHEMICALS & SPECIALTY CHEMICALS
    # ══════════════════════════════════════════════════════════════════════════
    "FACT": CompanyProfile(
        symbol="FACT",
        company_name="Fertilisers and Chemicals Travancore Limited",
        sector="Chemicals",
        industry="Fertilizers & Caprolactam",
        market_cap_category="mid_cap",
        business_summary="Government PSU manufacturing complex fertilizers (Factamfos - NP 20:20:0:13), Ammonium Sulphate, and industrial Caprolactam in Kerala.",
        primary_revenue_sources=["Complex fertilizer sales to Southern farm markets", "Industrial Caprolactam used in nylon textiles"],
        positive_catalysts=["Government release of fertilizer subsidy dues", "High international fertilizer prices ensuring domestic demand", "Monsoon abundance"],
        negative_catalysts=["Reduction in Nutrient Based Subsidy (NBS) rates by Centre", "Natural gas feedstock price hikes at Kochi plant"],
        regulatory_bodies=["Department of Fertilizers"]
    ),
    "RCF": CompanyProfile(
        symbol="RCF",
        company_name="Rashtriya Chemicals and Fertilizers Limited",
        sector="Chemicals",
        industry="Urea & Complex Fertilizers",
        market_cap_category="small_cap",
        business_summary="Major fertilizer PSU producing Urea and complex NPK fertilizers (Suphala brand), plus industrial chemicals (nitric acid, methanol) at Trombay and Thal plants.",
        primary_revenue_sources=["Urea and complex fertilizer sales under NBS scheme", "Industrial chemicals for mining and pharma"],
        positive_catalysts=["Timely fertilizer subsidy disbursements from Ministry of Finance", "Normal South-West monsoon boosting kharif/rabi sowing", "Gas pooling benefits"],
        negative_catalysts=["Cut in government fertilizer subsidy allocation in Budget", "High pooling gas costs"],
        regulatory_bodies=["Department of Fertilizers"]
    ),
    "NFL": CompanyProfile(
        symbol="NFL",
        company_name="National Fertilizers Limited",
        sector="Chemicals",
        industry="Urea & Bio-Fertilizers",
        market_cap_category="small_cap",
        business_summary="Second largest producer of Urea in India; operates major natural gas-based plants in Punjab, Haryana, and MP with vast farmer dealer network.",
        primary_revenue_sources=["Urea manufacturing and marketing", "Trading of imported DAP, MoP, and complex fertilizers"],
        positive_catalysts=["Govt additional subsidy package for farmers", "Strong agricultural sowing acreages", "Energy consumption norm revisions"],
        negative_catalysts=["Subsidy payment backlogs creating short-term borrowing costs", "Plant maintenance shut-ins"],
        regulatory_bodies=["Department of Fertilizers"]
    ),
    "CHAMBLFERT": CompanyProfile(
        symbol="CHAMBLFERT",
        company_name="Chambal Fertilizers & Chemicals Limited",
        sector="Chemicals",
        industry="Urea, DAP & Crop Protection",
        market_cap_category="mid_cap",
        business_summary="Leading private fertilizer manufacturer operating ultra-modern energy-efficient Urea plants at Gadepan (Rajasthan), with diversified crop protection and specialty plant nutrients.",
        primary_revenue_sources=["Urea sales across North/Central India", "Marketing of DAP, complex fertilizers, and crop protection chemicals"],
        positive_catalysts=["Low energy consumption per tonne yielding operational efficiency incentives", "Crop protection margin expansion", "Subsidy clearance"],
        negative_catalysts=["Reduction in government nutrient subsidy rates", "High domestic pooling gas prices"],
        regulatory_bodies=["Department of Fertilizers"]
    ),
    "COROMANDEL": CompanyProfile(
        symbol="COROMANDEL",
        company_name="Coromandel International Limited",
        sector="Chemicals",
        industry="Phosphatic Fertilizers & Crop Protection",
        market_cap_category="large_cap",
        business_summary="India's top private phosphatic fertilizer player (Gromor brand); manufactures NPK, DAP, single super phosphate, crop protection chemicals, and bio-pesticides.",
        primary_revenue_sources=["Phosphatic complex fertilizer sales", "Crop protection chemical synthesis", "Specialty nutrients and retail stores"],
        positive_catalysts=["Government NBS subsidy revisions supporting phosphatic fertilizers", "Softening raw material phosphoric acid and rock phosphate import prices", "Monsoon strength"],
        negative_catalysts=["Spike in international phosphoric acid contracts", "Government delay in releasing subsidy payments"],
        regulatory_bodies=["Department of Fertilizers"]
    ),
    "DEEPAKNTR": CompanyProfile(
        symbol="DEEPAKNTR",
        company_name="Deepak Nitrite Limited",
        sector="Chemicals",
        industry="Phenol, Acetone & Basic Intermediates",
        market_cap_category="mid_cap",
        business_summary="Leading chemical intermediary producer with global market share in sodium nitrite/nitrate and India's largest phenol and acetone plant (Deepak Phenolics).",
        primary_revenue_sources=["Phenol, acetone, and IPA manufacturing", "Basic chemicals and fine & specialty chemical intermediates"],
        positive_catalysts=["Anti-dumping duty on imported phenol/acetone", "Expansion into polycarbonate and advanced optical resin polymers", "Global supply chain de-risking from China"],
        negative_catalysts=["Cheap Chinese dumping of chemical intermediates", "Benzene and propylene feedstock cost spikes"],
        regulatory_bodies=["Ministry of Chemicals and Fertilizers"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 8. JEWELLERY & PRECIOUS METALS RETAIL
    # ══════════════════════════════════════════════════════════════════════════
    "TITAN": CompanyProfile(
        symbol="TITAN",
        company_name="Titan Company Limited",
        sector="Consumer Durables",
        industry="Jewellery, Watches & Eyewear",
        market_cap_category="large_cap",
        business_summary="Operates iconic brands Tanishq, Mia, Zoya, Fastrack, and Titan Watches. Roughly 88% of consolidated revenue and profits stem from jewellery retail.",
        primary_revenue_sources=["Gold and diamond jewellery sales (Tanishq)", "Watches and wearables", "Eyewear (Titan Eye+)"],
        positive_catalysts=["Reduction in basic customs duty on gold and silver imports", "Strong festive (Dhanteras, Diwali) and wedding season demand", "Market share gains from unorganized jewellery sector due to mandatory hallmarking"],
        negative_catalysts=["Hike in customs import duty on gold", "Extreme gold price surges causing demand elasticity freeze among retail consumers", "Stricter PAN / cash transaction reporting thresholds on jewellery purchases"],
        regulatory_bodies=["Ministry of Consumer Affairs", "Ministry of Finance"]
    ),
    "KALYANKJIL": CompanyProfile(
        symbol="KALYANKJIL",
        company_name="Kalyan Jewellers India Limited",
        sector="Consumer Durables",
        industry="Jewellery Retail Chain",
        market_cap_category="mid_cap",
        business_summary="Prominent pan-India and Middle East jewellery retailer operating company-owned and asset-light franchisee (FOCO) showrooms under Kalyan Jewellers and Candere online.",
        primary_revenue_sources=["Gold, diamond, and precious stone jewellery sales", "Franchisee management fees"],
        positive_catalysts=["Gold import duty cut", "Franchise showroom expansion pace", "Strong same-store sales growth (SSSG) in weddings"],
        negative_catalysts=["Gold duty hike", "Gold price spike stalling gram volume growth", "Middle East regional geopolitical tensions"],
        regulatory_bodies=["Ministry of Finance"]
    ),
    "SENCO": CompanyProfile(
        symbol="SENCO",
        company_name="Senco Gold Limited",
        sector="Consumer Durables",
        industry="Lightweight & Bridal Jewellery",
        market_cap_category="small_cap",
        business_summary="Leading jewellery retailer in Eastern India expanding nationwide; specializes in handcrafted lightweight gold, bridal jewellery, diamond jewellery, and Everlite daily-wear.",
        primary_revenue_sources=["Gold jewellery sales (70%+)", "Diamond and studded jewellery (higher margin)"],
        positive_catalysts=["Customs duty reduction on gold", "Eastern India festive Durga Puja / Diwali demand", "Rapid store rollout into Northern/Western cities"],
        negative_catalysts=["Gold price volatility causing consumer deferrals", "Rising gold metal loan lease financing rates"],
        regulatory_bodies=["Ministry of Finance"]
    ),
    "THANGAMAYL": CompanyProfile(
        symbol="THANGAMAYL",
        company_name="Thangamayil Jewellery Limited",
        sector="Consumer Durables",
        industry="Regional Jewellery Retail",
        market_cap_category="small_cap",
        business_summary="Dominant regional retail jewellery chain in Tamil Nadu; operates 60+ retail outlets catering to tier-2, tier-3, and rural consumers for gold, silver, and platinum ornaments.",
        primary_revenue_sources=["Gold jewellery and ornaments", "Silver articles and wedding jewellery"],
        positive_catalysts=["Good agricultural monsoon boosting rural disposable income for gold", "Gold duty cut lowering showroom price tags", "New branch additions in South India"],
        negative_catalysts=["Rural drought or inflation curtailing discretionary jewellery spends", "Gold price run-up dampening gram volumes"],
        regulatory_bodies=["Ministry of Finance"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 9. TELECOMMUNICATION & NETWORKING INFRASTRUCTURE
    # ══════════════════════════════════════════════════════════════════════════
    "BHARTIARTL": CompanyProfile(
        symbol="BHARTIARTL",
        company_name="Bharti Airtel Limited",
        sector="Telecommunication",
        industry="Telecom & Digital Services",
        market_cap_category="large_cap",
        business_summary="Leading global telecommunications company operating 4G/5G mobile services, broadband, DTH, enterprise ICT services, and payments bank in India and 14 African countries.",
        primary_revenue_sources=["Mobile connectivity and data subscriptions", "Airtel Business B2B enterprise connectivity", "Home broadband and DTH services"],
        positive_catalysts=["Industry-wide mobile tariff hikes expanding ARPU", "2G to 4G/5G subscriber conversions", "Government waiver/relief on Adjusted Gross Revenue (AGR) bank guarantees", "Strong mobile revenue growth in Africa operations"],
        negative_catalysts=["Price wars / delayed tariff hikes", "Heavy 5G spectrum and network capex outflows", "Supreme Court AGR adverse rulings"],
        regulatory_bodies=["TRAI", "DoT"]
    ),
    "TEJASNET": CompanyProfile(
        symbol="TEJASNET",
        company_name="Tejas Networks Limited",
        sector="Telecommunication",
        industry="Optical & Wireless Telecom OEM",
        market_cap_category="mid_cap",
        business_summary="Tata Group telecom technology company; designs and manufactures carrier-class optical networking products (DWDM, OTN), broadband access, and 4G/5G Radio Access Network (RAN) equipment.",
        primary_revenue_sources=["BSNL 4G/5G national network equipment rollout", "Optical transport network gear for telecom operators and utilities", "BharatNet optical broadband routers"],
        positive_catalysts=["BSNL pan-India 4G/5G equipment delivery execution", "Telecom equipment PLI incentives", "Global telecom Tier-1 export contracts"],
        negative_catalysts=["Semiconductor component supply delays", "Single-customer concentration with BSNL rollout"],
        regulatory_bodies=["DoT", "TRAI"]
    ),
    "ITI": CompanyProfile(
        symbol="ITI",
        company_name="ITI Limited",
        sector="Telecommunication",
        industry="Telecom Equipment PSU & Defence ICT",
        market_cap_category="small_cap",
        business_summary="First public sector unit in India; manufactures telecom transmission equipment, electronic voting machines, defence tactical communication networks (ASCON), and solar panels.",
        primary_revenue_sources=["Army Static Communication Network (ASCON) execution", "BharatNet phase-3 optical fiber project execution", "Telecom equipment manufacturing"],
        positive_catalysts=["BharatNet village optical connectivity package awards", "Ministry of Defence tactical secure network contracts", "Make in India electronic mandates"],
        negative_catalysts=["High fixed employee overheads and historic accumulated losses", "Long payment recovery cycles from state agencies"],
        regulatory_bodies=["DoT", "Ministry of Defence"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 10. REAL ESTATE, TILES & BUILDING MATERIALS
    # ══════════════════════════════════════════════════════════════════════════
    "LODHA": CompanyProfile(
        symbol="LODHA",
        company_name="Macrotech Developers Limited (Lodha)",
        sector="Realty",
        industry="Residential Real Estate",
        market_cap_category="large_cap",
        business_summary="Premier residential developer in Mumbai Metropolitan Region (MMR), Pune, and Bengaluru, focusing on luxury, premium, and aspirational housing as well as logistics parks.",
        primary_revenue_sources=["Sale of residential apartments and luxury villas", "Commercial office leasing and digital infrastructure parks"],
        positive_catalysts=["Record pre-sales booking numbers", "RBI interest rate cut easing home loan EMI burden", "State stamp duty incentives"],
        negative_catalysts=["Interest rate hikes reducing housing affordability", "Cement and steel construction cost inflation", "Regulatory approval bottlenecks"],
        regulatory_bodies=["MahaRERA", "RERA"]
    ),
    "DLF": CompanyProfile(
        symbol="DLF",
        company_name="DLF Limited",
        sector="Realty",
        industry="Super-Luxury Real Estate & Leased Offices",
        market_cap_category="large_cap",
        business_summary="Largest real estate developer in India by market cap, with landmark super-luxury residential developments in Gurugram and high-margin Grade-A office parks under DCCDL REIT JV.",
        primary_revenue_sources=["Super-luxury residential pre-sales", "Office and retail mall lease rental income"],
        positive_catalysts=["Fast sell-out of luxury housing launches in NCR", "REIT asset monetization", "Lower interest rate cycle"],
        negative_catalysts=["Home loan interest rate spikes", "Slowdown in tech office leasing demand"],
        regulatory_bodies=["Haryana RERA", "RERA"]
    ),
    "SIGNATURE": CompanyProfile(
        symbol="SIGNATURE",
        company_name="Signatureglobal (India) Limited",
        sector="Realty",
        industry="Mid-Income & Premium Housing",
        market_cap_category="mid_cap",
        business_summary="Fast-growing real estate developer dominating Gurugram and Delhi-NCR, transitioning from affordable housing into high-margin premium and luxury residential high-rises.",
        primary_revenue_sources=["Residential flat sales in Gurugram corridors (Dwarka Expressway, Golf Course Extension)", "Commercial retail shops in residential complexes"],
        positive_catalysts=["Dwarka Expressway infrastructure commissioning unlocking land bank value", "Overwhelming launch pre-bookings", "Accelerated project delivery schedules"],
        negative_catalysts=["Construction ban during winter pollution in Delhi-NCR (GRAP restrictions)", "Land acquisition cost run-up in Gurugram"],
        regulatory_bodies=["Haryana RERA"]
    ),
    "ASTRAL": CompanyProfile(
        symbol="ASTRAL",
        company_name="Astral Limited",
        sector="Capital Goods",
        industry="CPVC Plumbing Pipes & Adhesives",
        market_cap_category="large_cap",
        business_summary="India's leading manufacturer of chlorinated polyvinyl chloride (CPVC) plumbing, drainage and agricultural pipes; operates expanding adhesives and bathware divisions.",
        primary_revenue_sources=["CPVC and PVC pipes & fittings for real estate construction", "Adhesives and sealants (Bondtite, Resinova)", "Sanitaryware and faucets"],
        positive_catalysts=["Real estate construction boom driving piping demand", "Government infrastructure water schemes (Jal Jeevan Mission)", "PVC resin price stability expanding gross margins"],
        negative_catalysts=["Sharp PVC resin inventory losses during price crashes", "Slowdown in residential plumbing starts"],
        regulatory_bodies=["Bureau of Indian Standards (BIS)"]
    ),
    "KAJARIACER": CompanyProfile(
        symbol="KAJARIACER",
        company_name="Kajaria Ceramics Limited",
        sector="Consumer Durables",
        industry="Ceramic & Vitrified Floor Tiles",
        market_cap_category="mid_cap",
        business_summary="Largest ceramic and vitrified tile manufacturer in India, operating modern plants with vast showroom distribution network across metropolitan and tier-2/3 cities.",
        primary_revenue_sources=["Vitrified tiles (polished and glazed)", "Ceramic wall and floor tiles", "Bathware and sanitaryware"],
        positive_catalysts=["Real estate renovation and home handover boom", "Drop in natural gas fuel prices used at tile kilns", "Anti-dumping duty on imported tiles"],
        negative_catalysts=["Spike in natural gas prices at Morbi and Northern kilns", "Sluggish residential real estate completions"],
        regulatory_bodies=["Ministry of Commerce"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 11. INSURANCE, FINTECH & BROKERAGE
    # ══════════════════════════════════════════════════════════════════════════
    "POLICYBZR": CompanyProfile(
        symbol="POLICYBZR",
        company_name="PB Fintech Limited (Policybazaar / Paisabazaar)",
        sector="Financial Services",
        industry="Fintech & Insurance Web Aggregator",
        market_cap_category="mid_cap",
        business_summary="Operates Policybazaar, India's largest online insurance broker and marketplace, and Paisabazaar for consumer credit. Revenue is heavily driven by commissions/fees on insurance distribution, renewals, and loan disbursement fees.",
        primary_revenue_sources=["Insurance distribution commissions", "Renewal commissions", "Credit marketplace referral fees"],
        positive_catalysts=[
            "Higher insurance premium growth", "Expansion in health and life coverage",
            "FDI limit hike in insurance", "Higher conversion rates and renewal volume",
            "Relaxation in distributor commission caps"
        ],
        negative_catalysts=[
            "IRDAI reduction or cap on insurance agent/broker commissions",
            "IRDAI mandatory surrender value hikes hurting life insurer margins",
            "Direct-to-consumer sales bypassing web aggregators",
            "RBI tighter norms on personal loan / credit card disbursements"
        ],
        regulatory_bodies=["IRDAI", "RBI"]
    ),
    "STARHEALTH": CompanyProfile(
        symbol="STARHEALTH",
        company_name="Star Health and Allied Insurance Company Limited",
        sector="Financial Services",
        industry="Standalone Health Insurance (SAHI)",
        market_cap_category="mid_cap",
        business_summary="India's largest standalone health insurance company with nationwide agency distribution and pre-agreed hospital cashless networks.",
        primary_revenue_sources=["Retail and group health insurance premiums", "Personal accident coverage", "Travel insurance"],
        positive_catalysts=["Post-COVID health insurance awareness", "Premium price revisions approved by IRDAI", "Cashless hospital settlement network expansion"],
        negative_catalysts=["Hospital treatment cost inflation", "Claims ratio spike during epidemics", "IRDAI distribution commission caps"],
        regulatory_bodies=["IRDAI"]
    ),
    "HDFCLIFE": CompanyProfile(
        symbol="HDFCLIFE",
        company_name="HDFC Life Insurance Company Limited",
        sector="Financial Services",
        industry="Life Insurance",
        market_cap_category="large_cap",
        business_summary="Leading private life insurer offering individual and group life insurance, pensions, annuities, and savings products across bancassurance and agency channels.",
        primary_revenue_sources=["Life insurance premiums", "Investment income on policyholder assets", "Fee income"],
        positive_catalysts=["Strong APE growth", "VNB margin expansion", "Tax incentives on insurance", "Pension/annuity demand"],
        negative_catalysts=["IRDAI higher surrender value payouts", "Taxation of high-value insurance proceeds", "ULIP outflows in weak stock markets"],
        regulatory_bodies=["IRDAI"]
    ),
    "SBILIFE": CompanyProfile(
        symbol="SBILIFE",
        company_name="SBI Life Insurance Company Limited",
        sector="Financial Services",
        industry="Life Insurance",
        market_cap_category="large_cap",
        business_summary="Top tier life insurer leveraging State Bank of India's nationwide branch network with high-margin protection and savings policies.",
        primary_revenue_sources=["Life insurance premiums", "Annuities", "Fund management charges"],
        positive_catalysts=["Bancassurance expansion", "VNB margin growth", "Tax relief for term insurance"],
        negative_catalysts=["Surrender value regulation changes", "IRDAI distribution commission caps", "Slowdown in retail protection"],
        regulatory_bodies=["IRDAI"]
    ),
    "ICICIPRULI": CompanyProfile(
        symbol="ICICIPRULI",
        company_name="ICICI Prudential Life Insurance Company Limited",
        sector="Financial Services",
        industry="Life Insurance",
        market_cap_category="large_cap",
        business_summary="Large private life insurer focused on protection, savings, ULIPs, and retirement solutions through diversified distribution.",
        primary_revenue_sources=["Protection and savings premiums", "ULIP fees", "Investment returns"],
        positive_catalysts=["Protection share expansion", "Bancassurance tie-ups", "Regulatory easing"],
        negative_catalysts=["IRDAI surrender regulations", "High surrender payouts", "ULIP outflows in weak stock markets"],
        regulatory_bodies=["IRDAI"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 12. CITY GAS DISTRIBUTION & OIL UPSTREAM / DOWNSTREAM
    # ══════════════════════════════════════════════════════════════════════════
    "IGL": CompanyProfile(
        symbol="IGL",
        company_name="Indraprastha Gas Limited",
        sector="Energy",
        industry="City Gas Distribution (CGD)",
        market_cap_category="mid_cap",
        business_summary="Operates CGD network in Delhi-NCR, supplying CNG for vehicles and piped natural gas (PNG) to domestic households, commercial establishments, and industries.",
        primary_revenue_sources=["CNG sales at automotive stations", "Domestic, commercial, and industrial PNG sales"],
        positive_catalysts=["Higher APM gas allocation from government", "Lower domestic gas prices", "EV adoption delay in public transport"],
        negative_catalysts=["Reduction in low-cost APM gas allocation forcing expensive imported LNG usage", "Spike in international spot LNG prices", "Aggressive EV mandates in Delhi-NCR"],
        regulatory_bodies=["PNGRB", "Ministry of Petroleum and Natural Gas"]
    ),
    "MGL": CompanyProfile(
        symbol="MGL",
        company_name="Mahanagar Gas Limited",
        sector="Energy",
        industry="City Gas Distribution (CGD)",
        market_cap_category="mid_cap",
        business_summary="Distributes CNG and domestic/commercial PNG across Mumbai, Thane, Navi Mumbai, and Raigad districts with high vehicular penetration.",
        primary_revenue_sources=["CNG sales for auto, taxi, bus, and private cars", "Domestic and industrial PNG"],
        positive_catalysts=["Higher APM gas allocation", "Reduction in domestic input gas ceiling price", "Geographical expansion into new licensed areas"],
        negative_catalysts=["APM domestic gas quota cut", "Surge in imported RLNG prices", "Aggressive EV transition in Mumbai public transport"],
        regulatory_bodies=["PNGRB", "Ministry of Petroleum and Natural Gas"]
    ),
    "GUJGASLTD": CompanyProfile(
        symbol="GUJGASLTD",
        company_name="Gujarat Gas Limited",
        sector="Energy",
        industry="City Gas Distribution (CGD)",
        market_cap_category="mid_cap",
        business_summary="India's largest city gas distributor by volume, supplying large industrial clusters (Morbi ceramic hub) as well as CNG and domestic PNG across Gujarat.",
        primary_revenue_sources=["Industrial PNG to ceramic and chemical manufacturers", "CNG for transport", "Commercial/domestic PNG"],
        positive_catalysts=["Morbi ceramic export demand revival", "Propane/LPG price rise making industrial natural gas cheaper"],
        negative_catalysts=["Cheaper alternative fuels (Propane) eating industrial PNG volume", "Imported LNG price spikes", "Morbi manufacturing slowdown"],
        regulatory_bodies=["PNGRB"]
    ),
    "ONGC": CompanyProfile(
        symbol="ONGC",
        company_name="Oil & Natural Gas Corporation Limited",
        sector="Energy",
        industry="Oil & Gas Exploration & Production (Upstream)",
        market_cap_category="large_cap",
        business_summary="India's largest upstream crude oil and natural gas producer, producing roughly 70% of domestic crude oil and 84% of natural gas.",
        primary_revenue_sources=["Crude oil sales to domestic refineries", "Natural gas production and sales", "Value-added products (LPG, naphtha)"],
        positive_catalysts=["Rise in international Brent crude oil prices ($80-$100/bbl)", "Reduction or elimination of Special Additional Excise Duty (Windfall Tax)", "Deepwater production ramp-up in KG basin"],
        negative_catalysts=["Sharp drop in global crude oil prices below $65/bbl", "Imposition or hike in domestic windfall tax on crude production"],
        regulatory_bodies=["Ministry of Petroleum and Natural Gas"]
    ),
    "OIL": CompanyProfile(
        symbol="OIL",
        company_name="Oil India Limited",
        sector="Energy",
        industry="Oil & Gas Exploration & Production (Upstream)",
        market_cap_category="mid_cap",
        business_summary="National upstream explorer focused on crude oil and natural gas production in Assam and Rajasthan, plus Numaligarh Refinery stake.",
        primary_revenue_sources=["Crude oil sales", "Natural gas pipeline transmission", "Refining margins via Numaligarh Refinery"],
        positive_catalysts=["Higher Brent crude realizations", "Windfall tax reduction", "Numaligarh refinery capacity expansion"],
        negative_catalysts=["Global crude oil price slump", "Hike in crude windfall tax", "Natural gas price ceiling reductions"],
        regulatory_bodies=["Ministry of Petroleum and Natural Gas"]
    ),
    "IOC": CompanyProfile(
        symbol="IOC",
        company_name="Indian Oil Corporation Limited",
        sector="Energy",
        industry="Oil Refining & Marketing (OMC Downstream)",
        market_cap_category="large_cap",
        business_summary="India's largest oil refining and fuel marketing PSU, operating 11 refineries, 36,000+ retail fuel stations, and an extensive pipeline network.",
        primary_revenue_sources=["Auto fuel sales (petrol, diesel)", "LPG and kerosene marketing", "Petrochemicals", "Aviation turbine fuel (ATF)"],
        positive_catalysts=["Lower global crude oil prices expanding retail auto fuel marketing margins", "High Gross Refining Margins (GRMs)", "Govt compensation for LPG under-recoveries"],
        negative_catalysts=["Surge in global crude prices ($90+) without retail price hike, crushing marketing margins", "Retail pump price cuts mandated by government"],
        regulatory_bodies=["Ministry of Petroleum and Natural Gas"]
    ),
    "BPCL": CompanyProfile(
        symbol="BPCL",
        company_name="Bharat Petroleum Corporation Limited",
        sector="Energy",
        industry="Oil Refining & Marketing (OMC Downstream)",
        market_cap_category="large_cap",
        business_summary="Leading downstream PSU operating modern refineries in Mumbai, Kochi, and Bina, with over 21,000 retail fuel outlets.",
        primary_revenue_sources=["Petrol and diesel retail marketing", "Refining throughput", "Aviation turbine fuel", "Lubricants"],
        positive_catalysts=["Low crude oil prices boosting fuel marketing margins", "Strong diesel/petrol crack spreads", "Govt LPG subsidies"],
        negative_catalysts=["Crude oil rally creating negative marketing margins", "Pre-election retail price cuts", "Crude supply disruption"],
        regulatory_bodies=["Ministry of Petroleum and Natural Gas"]
    ),
    "INDIGO": CompanyProfile(
        symbol="INDIGO",
        company_name="InterGlobe Aviation Limited (IndiGo)",
        sector="Services",
        industry="Aviation & Low-Cost Passenger Carrier",
        market_cap_category="large_cap",
        business_summary="India's dominant airline with over 60% domestic passenger market share, operating a large, fuel-efficient Airbus A320/A321 fleet across domestic and international routes.",
        primary_revenue_sources=["Passenger ticket fares", "Ancillary services (seat selection, baggage, onboard meals)", "Cargo (CarGo)"],
        positive_catalysts=["Reduction in Aviation Turbine Fuel (ATF) jet fuel prices (ATF accounts for ~40% of costs)", "Strong passenger load factors and festive travel demand", "Market share expansion"],
        negative_catalysts=["Sharp increase in ATF fuel prices due to global crude rally", "Pratt & Whitney engine grounding issues affecting fleet capacity", "Rupee depreciation against US dollar"],
        regulatory_bodies=["DGCA", "Ministry of Civil Aviation"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 13. IT MIDCAPS, DIGITAL ENGINEERING & DATA INFRASTRUCTURE
    # ══════════════════════════════════════════════════════════════════════════
    "PERSISTENT": CompanyProfile(
        symbol="PERSISTENT",
        company_name="Persistent Systems Limited",
        sector="Information Technology",
        industry="Digital Engineering & Enterprise Modernisation",
        market_cap_category="mid_cap",
        business_summary="Leading digital engineering and enterprise modernisation IT company; specializes in software product engineering, cloud, generative AI, and healthcare/BFSI enterprise platforms.",
        primary_revenue_sources=["Software engineering & digital services", "Cloud and infrastructure modernization", "BFSI and healthcare vertical IT solutions"],
        positive_catalysts=["Large multi-year deal wins in North America", "Generative AI enterprise platform deployment", "High BFSI and tech client retention"],
        negative_catalysts=["US enterprise IT spending slowdown", "Wage hikes and high offshore tech attrition", "Client budget freezes in discretionary tech"],
        regulatory_bodies=["US SEC", "MeitY"]
    ),
    "COFORGE": CompanyProfile(
        symbol="COFORGE",
        company_name="Coforge Limited",
        sector="Information Technology",
        industry="IT Solutions & Aviation/Insurance Platforms",
        market_cap_category="mid_cap",
        business_summary="Global digital services provider with high vertical specialization in travel/transportation, banking & financial services, and insurance systems; acquired Cigniti for advanced AI testing.",
        primary_revenue_sources=["Aviation and airline booking platforms", "Insurance core platform modernization", "Banking and payments engineering"],
        positive_catalysts=["Order intake crossing $300M+ per quarter", "Large airline digital modernization contracts", "Synergies from Cigniti engineering integration"],
        negative_catalysts=["Aviation industry disruption reducing IT outlays", "Integration friction in large acquisitions"],
        regulatory_bodies=["MeitY"]
    ),
    "KPITTECH": CompanyProfile(
        symbol="KPITTECH",
        company_name="KPIT Technologies Limited",
        sector="Information Technology",
        industry="Automotive Embedded Software & Mobility",
        market_cap_category="mid_cap",
        business_summary="Pure-play automotive software company; develops software-defined vehicle (SDV) architectures, autonomous driving (ADAS), electric powertrain software, and connected vehicle platforms.",
        primary_revenue_sources=["Autonomous driving / ADAS software development", "EV powertrain and battery management software", "Vehicle connected architectures for global OEMs"],
        positive_catalysts=["Global OEM acceleration into Software-Defined Vehicles", "Multi-year SDV platform partnerships (Honda, Renault)", "High client lock-in on proprietary automotive IP"],
        negative_catalysts=["Delays in OEM electric vehicle launch schedules", "European automotive industry capex cutbacks"],
        regulatory_bodies=["MeitY"]
    ),
    "TATAELXSI": CompanyProfile(
        symbol="TATAELXSI",
        company_name="Tata Elxsi Limited",
        sector="Information Technology",
        industry="Design & Technology Services (ER&D)",
        market_cap_category="mid_cap",
        business_summary="Tata Group engineering research and design (ER&D) leader; develops design-led digital products for transportation, healthcare/medical devices, and media/telecom industries.",
        primary_revenue_sources=["Transportation autonomous and EV design", "Medical devices software and regulatory compliance", "Broadcast media digital video platforms"],
        positive_catalysts=["Medical device FDA software approvals", "Connected car tech adoption by global luxury automakers", "High-margin design studio contracts"],
        negative_catalysts=["Slowdown in media and telecom R&D budgets", "Extended sales cycles in European automotive"],
        regulatory_bodies=["MeitY"]
    ),
    "LTIM": CompanyProfile(
        symbol="LTIM",
        company_name="LTIMindtree Limited",
        sector="Information Technology",
        industry="IT Services & Digital Consulting",
        market_cap_category="large_cap",
        business_summary="Tier-1 IT services company formed by merger of L&T Infotech and Mindtree; delivers enterprise cloud transformation, ERP, data analytics, and BFSI platform solutions.",
        primary_revenue_sources=["BFSI digital transformation", "Manufacturing and industrial high-tech IT", "Consumer and retail cloud solutions"],
        positive_catalysts=["Mega deal wins exceeding $1B+", "Synergy realization from post-merger cross-selling", "Recovery in US regional banking tech budgets"],
        negative_catalysts=["Slow decision-making in large enterprise contracts", "Higher employee attrition during delivery scaling"],
        regulatory_bodies=["MeitY"]
    ),
    "NETWEB": CompanyProfile(
        symbol="NETWEB",
        company_name="Netweb Technologies India Limited",
        sector="Information Technology",
        industry="High-Performance Computing (HPC) & AI Supercomputers",
        market_cap_category="small_cap",
        business_summary="India's leading indigenous high-performance computing (HPC) provider; manufactures AI supercomputers, private cloud servers, data center hardware, and NVIDIA Grace Hopper enterprise systems.",
        primary_revenue_sources=["AI-focused supercomputing systems and servers", "High-performance data center storage", "Private cloud and enterprise computing hardware"],
        positive_catalysts=["India AI Mission government supercomputing tenders", "NVIDIA certified OEM server manufacturing partnership", "Data center capex boom across Indian hyperscalers"],
        negative_catalysts=["Global semiconductor GPU component allocation shortages", "Customer concentration with government research labs"],
        regulatory_bodies=["MeitY", "India AI Mission"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 14. PHARMA, APIS, CDMO & HEALTHCARE
    # ══════════════════════════════════════════════════════════════════════════
    "SUNPHARMA": CompanyProfile(
        symbol="SUNPHARMA",
        company_name="Sun Pharmaceutical Industries Limited",
        sector="Healthcare",
        industry="Specialty Pharma & Generics",
        market_cap_category="large_cap",
        business_summary="India's largest pharmaceutical company and 4th largest global specialty generic company; market leader in domestic formulations and global dermatology/ophthalmology specialty products.",
        primary_revenue_sources=["Global specialty dermatology (Ilumya, Winlevi, Cequa)", "India domestic branded formulations (chronic therapies)", "US generic formulations"],
        positive_catalysts=["Specialty drug sales growth exceeding expectations", "New FDA drug approvals for innovative pipeline", "Domestic formulation market share gains"],
        negative_catalysts=["USFDA import alerts or warning letters on key manufacturing sites (e.g., Halol)", "Price erosion in US generic oral solids", "Adverse patent litigation rulings"],
        regulatory_bodies=["USFDA", "DCGI", "NPPA"]
    ),
    "CIPLA": CompanyProfile(
        symbol="CIPLA",
        company_name="Cipla Limited",
        sector="Healthcare",
        industry="Respiratory, Inhalation & Generics",
        market_cap_category="large_cap",
        business_summary="Global pharmaceutical company globally renowned for respiratory treatments (inhalers, nebulizers); dominant in chronic therapies in India and generic inhalation products in the US.",
        primary_revenue_sources=["India branded formulations (One-India market)", "US generic complex inhalation drugs (Lanreotide, Albuterol)", "South Africa private healthcare market"],
        positive_catalysts=["USFDA clearance of complex generic respiratory pipelines (generic Advair, Abraxane)", "Strong respiratory seasonal demand", "Domestic trade generics expansion"],
        negative_catalysts=["USFDA Form 483 with data integrity observations at formulation plants", "Price erosion in US generics", "NPPA price control drug list expansion"],
        regulatory_bodies=["USFDA", "DCGI", "NPPA"]
    ),
    "LAURUSLABS": CompanyProfile(
        symbol="LAURUSLABS",
        company_name="Laurus Labs Limited",
        sector="Healthcare",
        industry="Active Pharmaceutical Ingredients (APIs) & CDMO",
        market_cap_category="mid_cap",
        business_summary="Major manufacturer of active pharmaceutical ingredients (APIs) for antiretroviral (HIV), oncology, and cardiovascular therapies, expanding heavily into high-margin CDMO synthesis and bio-division.",
        primary_revenue_sources=["Antiretroviral (ARV) and oncology APIs", "CDMO custom synthesis contracts for global innovators", "Finished dosage formulations"],
        positive_catalysts=["Commercial ramp-up of multi-year CDMO contracts", "Diversification away from tender-based ARV sales", "USFDA clean plant inspections (EIR)"],
        negative_catalysts=["USFDA inspection observations / Form 483", "Sharp drops in global ARV tender pricing", "Delays in CDMO commercial batch validation"],
        regulatory_bodies=["USFDA", "DCGI"]
    ),
    "GLAND": CompanyProfile(
        symbol="GLAND",
        company_name="Gland Pharma Limited",
        sector="Healthcare",
        industry="Generic Injectables & Biologics CDMO",
        market_cap_category="mid_cap",
        business_summary="Pure-play generic injectable pharmaceutical manufacturer with extensive sterile manufacturing capabilities across vials, ampoules, pre-filled syringes, and lyophilized products.",
        primary_revenue_sources=["Sterile injectable contract manufacturing for US and Europe", "Domestic and rest-of-world hospital supply"],
        positive_catalysts=["Fast-track USFDA approvals for complex sterile injectables", "Capacity ramp-up at acquired European CDMO Cenexi", "Clean USFDA inspection reports without 483s"],
        negative_catalysts=["USFDA warning letter or Form 483 on sterile injectable lines", "Supply chain disruptions for specialized glass vials or stoppers"],
        regulatory_bodies=["USFDA", "DCGI"]
    ),
    "MARKSANS": CompanyProfile(
        symbol="MARKSANS",
        company_name="Marksans Pharma Limited",
        sector="Healthcare",
        industry="Formulations & OTC Generics",
        market_cap_category="small_cap",
        business_summary="Fast-growing formulations player focused on OTC and prescription generics in the UK, US, Australia, and Europe across pain management, cough/cold, and gastrointestinal products.",
        primary_revenue_sources=["OTC pharmaceutical sales in UK retail supermarket chains", "US generic ANDA product sales", "Soft gelatin capsule contract manufacturing"],
        positive_catalysts=["Commissioning of newly acquired Teva Goa manufacturing facility", "US FDA approval of new Abbreviated New Drug Applications (ANDAs)", "UK NHS volume growth"],
        negative_catalysts=["Regulatory scrutiny on Goa manufacturing unit", "Raw material gelatin and API cost inflation"],
        regulatory_bodies=["USFDA", "UK MHRA"]
    ),
    "NEULANDLAB": CompanyProfile(
        symbol="NEULANDLAB",
        company_name="Neuland Laboratories Limited",
        sector="Healthcare",
        industry="Specialty APIs & Complex Peptides CDMO",
        market_cap_category="small_cap",
        business_summary="Leading specialized active pharmaceutical ingredient (API) and peptide CDMO player; manufactures complex custom synthesis molecules for global pharma innovators and commercial APIs.",
        primary_revenue_sources=["Custom Manufacturing Solutions (CMS / CDMO)", "Specialty APIs (complex peptides, neurology, oncology)", "Prime active pharmaceutical ingredients"],
        positive_catalysts=["Commercialization of innovator clinical pipeline molecules", "Expansion into high-margin complex peptides", "Zero 483 observations from USFDA"],
        negative_catalysts=["Lumpy quarterly CDMO customer delivery schedules", "Termination of clinical trial programs by pharma innovators"],
        regulatory_bodies=["USFDA", "DCGI"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 15. BANKING, SFBs, GOLD LOANS & NBFCs
    # ══════════════════════════════════════════════════════════════════════════
    "HDFCBANK": CompanyProfile(
        symbol="HDFCBANK",
        company_name="HDFC Bank Limited",
        sector="Financial Services",
        industry="Private Sector Commercial Bank",
        market_cap_category="large_cap",
        business_summary="India's largest private sector bank; delivers retail banking, wholesale loans, credit cards, auto loans, and mortgages post-merger with parent HDFC Limited.",
        primary_revenue_sources=["Net interest income from retail and corporate loans", "Fee income from credit cards, wealth management, and forex", "Treasury gains"],
        positive_catalysts=["Improving Credit-to-Deposit (CD) ratio towards target", "Net Interest Margin (NIM) recovery", "Sustained deposit mobilization surpassing industry average", "Asset quality stability with low gross NPAs"],
        negative_catalysts=["Persistent liquidity tightness depressing deposit growth", "NIM contraction", "Regulatory restrictions on IT systems or credit card issuance by RBI"],
        regulatory_bodies=["RBI"]
    ),
    "ICICIBANK": CompanyProfile(
        symbol="ICICIBANK",
        company_name="ICICI Bank Limited",
        sector="Financial Services",
        industry="Private Sector Commercial Bank",
        market_cap_category="large_cap",
        business_summary="Top-tier private bank with industry-leading ROA (2.3%+), low cost-to-income ratio, and strong retail, SME, and digital banking franchises.",
        primary_revenue_sources=["Net interest income across retail, SME, and corporate lending", "Transaction and service fee income", "Subsidiary dividends"],
        positive_catalysts=["Best-in-class Return on Assets (RoA) and Return on Equity (RoE)", "Broad-based loan growth across retail and business banking", "Immaculate asset quality"],
        negative_catalysts=["General systemic deposit competition driving up cost of funds", "Unsecured retail credit risk normalization"],
        regulatory_bodies=["RBI"]
    ),
    "SBIN": CompanyProfile(
        symbol="SBIN",
        company_name="State Bank of India",
        sector="Financial Services",
        industry="Public Sector Commercial Bank",
        market_cap_category="large_cap",
        business_summary="India's largest commercial bank by assets, deposits, and branches; handles over 20% of domestic banking credit and operates dominant insurance/AMC subsidiaries.",
        primary_revenue_sources=["Net interest income across massive sovereign, retail, and corporate book", "Government transaction handling and treasury income", "Subsidiary value"],
        positive_catalysts=["Corporate capex revival expanding credit demand", "Low gross NPA ratio under 2.5%", "Subsidiary IPO monetization"],
        negative_catalysts=["Spike in wage revision provisions or pension liabilities", "Slippages in SME or agricultural loan portfolios"],
        regulatory_bodies=["RBI", "Ministry of Finance"]
    ),
    "FEDERALBNK": CompanyProfile(
        symbol="FEDERALBNK",
        company_name="The Federal Bank Limited",
        sector="Financial Services",
        industry="Private Sector Regional / Pan-India Bank",
        market_cap_category="mid_cap",
        business_summary="Well-established private bank headquartered in Kerala with pan-India branch footprint; leader in inward NRI remittances, retail gold loans, and fintech co-branded partnerships.",
        primary_revenue_sources=["Retail and commercial loan interest", "NRI inward remittance service fees", "Gold loan and commercial vehicle interest"],
        positive_catalysts=["High-margin fintech partnership asset origination", "Stable asset quality in retail and SME books", "Steady RoA expansion above 1.3%"],
        negative_catalysts=["RBI regulatory scrutiny on co-branded credit cards or fintech partnerships", "Competitive deposit pricing in NRI markets"],
        regulatory_bodies=["RBI"]
    ),
    "IDFCFIRSTB": CompanyProfile(
        symbol="IDFCFIRSTB",
        company_name="IDFC First Bank Limited",
        sector="Financial Services",
        industry="Private Sector Universal Bank",
        market_cap_category="mid_cap",
        business_summary="Fast-growing universal private bank focused on retail consumer financing, consumer durables, two-wheeler loans, MSME lending, and high CASA deposit growth.",
        primary_revenue_sources=["Net interest income from consumer retail and MSME loans", "Credit card and merchant fees", "Treasury and wholesale banking fees"],
        positive_catalysts=["Strong retail deposit and CASA ratio accretion", "Operating leverage improvement lowering cost-to-income", "Branch network maturity"],
        negative_catalysts=["Higher credit costs in microfinance / uncollateralized personal loans", "Margin compression from competitive deposit rates"],
        regulatory_bodies=["RBI"]
    ),
    "AUBANK": CompanyProfile(
        symbol="AUBANK",
        company_name="AU Small Finance Bank Limited",
        sector="Financial Services",
        industry="Small Finance Bank / Universal Banking Applicant",
        market_cap_category="mid_cap",
        business_summary="India's largest Small Finance Bank post-merger with Fincare SFB; specializes in vehicle finance, micro-SME loans, wheels, and universal banking transition.",
        primary_revenue_sources=["Used and new vehicle loans", "Micro-enterprise and commercial loans", "Housing loans and credit cards"],
        positive_catalysts=["RBI approval for transition to Universal Banking license", "Expansion in high-yield MSME loan book", "Fincare merger cost synergies"],
        negative_catalysts=["Microfinance slippages and localized flood/drought credit costs", "High cost of retail deposits"],
        regulatory_bodies=["RBI"]
    ),
    "MUTHOOTFIN": CompanyProfile(
        symbol="MUTHOOTFIN",
        company_name="Muthoot Finance Limited",
        sector="Financial Services",
        industry="Gold Financing NBFC",
        market_cap_category="large_cap",
        business_summary="India's largest gold financing NBFC, holding over 180 tonnes of gold jewellery as collateral across 5,000+ branches nationwide.",
        primary_revenue_sources=["Interest income on gold jewellery loans", "Foreign exchange and money transfer services"],
        positive_catalysts=["Surge in global gold prices expanding collateral value and borrowing headroom", "RBI restrictions on bank cash gold loans driving borrowers to NBFCs", "AUM growth surpassing 20%"],
        negative_catalysts=["Sharp crashes in gold prices requiring margin calls and auctions", "RBI tightening LTV (Loan-to-Value) caps below 75%"],
        regulatory_bodies=["RBI"]
    ),
    "MANAPPURAM": CompanyProfile(
        symbol="MANAPPURAM",
        company_name="Manappuram Finance Limited",
        sector="Financial Services",
        industry="Gold Loans, Microfinance & Vehicle NBFC",
        market_cap_category="mid_cap",
        business_summary="Diversified NBFC providing short-term gold loans, microfinance (Asirvad Microfinance), housing finance, and commercial vehicle loans across India.",
        primary_revenue_sources=["Gold loan interest income", "Microfinance loan interest (Asirvad)", "Vehicle and MSME lending"],
        positive_catalysts=["Gold price firmness supporting loan ticket sizes", "Asirvad Microfinance subsidiary value unlocking", "Diversification into non-gold assets"],
        negative_catalysts=["RBI regulatory curbs on microfinance interest margins or lending practices", "Localized microfinance delinquency spikes"],
        regulatory_bodies=["RBI"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 16. METALS, MINING & CEMENT INFRASTRUCTURE
    # ══════════════════════════════════════════════════════════════════════════
    "TATASTEEL": CompanyProfile(
        symbol="TATASTEEL",
        company_name="Tata Steel Limited",
        sector="Metals",
        industry="Integrated Steel Producer",
        market_cap_category="large_cap",
        business_summary="Top global steel producer with ultra-low-cost captive iron ore mines in India and extensive operations in Kalinganagar, Jamshedpur, and the UK (Port Talbot transition).",
        primary_revenue_sources=["Flat steel products (automotive, engineering)", "Long steel products (construction)", "Ferro alloys and tubes"],
        positive_catalysts=["Government anti-dumping duty or safeguard duty on cheap Chinese steel imports", "Domestic infrastructure and construction steel demand revival", "UK green electric arc furnace transition subsidies"],
        negative_catalysts=["Chinese steel dumping at multi-year low export prices", "Coking coal price spikes", "Losses at European operations"],
        regulatory_bodies=["Ministry of Steel", "DGTR"]
    ),
    "JSWSTEEL": CompanyProfile(
        symbol="JSWSTEEL",
        company_name="JSW Steel Limited",
        sector="Metals",
        industry="Integrated Steel Manufacturing",
        market_cap_category="large_cap",
        business_summary="Flagship company of JSW Group and India's largest steelmaker by domestic installed capacity (Vijayanagar, Dolvi, Bhushan Power & Steel).",
        primary_revenue_sources=["Automotive flat steel and galvanized products", "Construction long products and wire rods", "Coated steel export products"],
        positive_catalysts=["Steel safeguard tariffs", "High capacity utilization and brownfield expansion milestones", "Infrastructure budget outlays"],
        negative_catalysts=["Iron ore and imported coking coal price spikes", "Chinese steel export dumping"],
        regulatory_bodies=["Ministry of Steel", "DGTR"]
    ),
    "NMDC": CompanyProfile(
        symbol="NMDC",
        company_name="NMDC Limited",
        sector="Metals",
        industry="Iron Ore Mining PSU",
        market_cap_category="large_cap",
        business_summary="India's single largest iron ore producer; operates highly mechanized iron ore mines at Bailadila (Chhattisgarh) and Donimalai (Karnataka) with pristine balance sheet.",
        primary_revenue_sources=["Iron ore lump and fines sales to domestic steelmakers", "Pellet production and diamond mining"],
        positive_catalysts=["Monthly iron ore price hikes driven by domestic steel production", "Capacity expansion towards 50 MTPA production target", "High dividend payout yield"],
        negative_catalysts=["Mandatory royalty hikes by state governments", "Iron ore export duty increases", "Domestic steelmaker production curtailments"],
        regulatory_bodies=["Ministry of Mines"]
    ),
    "ULTRACEMCO": CompanyProfile(
        symbol="ULTRACEMCO",
        company_name="UltraTech Cement Limited",
        sector="Construction Materials",
        industry="Cement & Ready Mix Concrete",
        market_cap_category="large_cap",
        business_summary="Aditya Birla Group flagship and India's largest cement manufacturer with over 150 MTPA capacity, nationwide distribution, and extensive white cement/RMC operations.",
        primary_revenue_sources=["Grey cement sales for infrastructure and housing", "Ready Mix Concrete (RMC)", "White cement and wall putty (Birla White)"],
        positive_catalysts=["Cement price hikes across North, West, and East India", "Government highway and affordable housing infrastructure spends", "Softening petcoke and imported coal thermal fuel costs"],
        negative_catalysts=["Severe price competition from Adani/Ambuja cement acquisitions", "Petcoke and imported thermal coal cost spikes", "Monsoon construction slowdown"],
        regulatory_bodies=["Competition Commission of India (CCI)", "Ministry of Commerce"]
    ),
    "STARCEMENT": CompanyProfile(
        symbol="STARCEMENT",
        company_name="Star Cement Limited",
        sector="Construction Materials",
        industry="Cement & Clinker Manufacturing (North East)",
        market_cap_category="small_cap",
        business_summary="Dominant cement manufacturer in North Eastern India with over 25% regional market share; expanding clinker and grinding capacities into Eastern India (Assam, Meghalaya, Bengal).",
        primary_revenue_sources=["Grey cement sales in North Eastern states and West Bengal", "Clinker supplies"],
        positive_catalysts=["North East infrastructure and border road development packages", "New clinker unit commissioning in Meghalaya lowering freight costs", "Regional pricing premium in NE"],
        negative_catalysts=["Coal availability bottlenecks in North East", "Monsoon floods halting construction in Assam"],
        regulatory_bodies=["Ministry of Development of North Eastern Region", "CCI"]
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # 17. AUTO ANCILLARIES & SPECIALIZED ENGINEERING
    # ══════════════════════════════════════════════════════════════════════════
    "CRAFTSMAN": CompanyProfile(
        symbol="CRAFTSMAN",
        company_name="Craftsman Automation Limited",
        sector="Automobile",
        industry="Precision Machining & Powertrain Engineering",
        market_cap_category="small_cap",
        business_summary="Precision engineering manufacturer specializing in powertrain cylinder blocks, heads, cam shafts, transmission components for commercial vehicles, tractors, and industrial storage.",
        primary_revenue_sources=["Powertrain machining for commercial vehicles & tractors", "Aluminium die casting for passenger cars", "Industrial storage solutions and automated warehousing"],
        positive_catalysts=["Commercial vehicle freight tonnage recovery", "Acquisition of Sunbeam Lightweighting expanding passenger car casting", "Automated warehouse rack demand"],
        negative_catalysts=["Commercial vehicle downcycle", "Aluminium and cast iron raw material inflation"],
        regulatory_bodies=["MORTH"]
    ),
    "SUPRAJIT": CompanyProfile(
        symbol="SUPRAJIT",
        company_name="Suprajit Engineering Limited",
        sector="Automobile",
        industry="Mechanical Control Cables & Halogen Lighting",
        market_cap_category="small_cap",
        business_summary="Global leader in automotive mechanical control cables (clutch, brake, throttle cables) and aftermarket halogen lighting (Phoenix Lamps), supplying two-wheelers and passenger vehicles worldwide.",
        primary_revenue_sources=["Automotive mechanical control cables", "Automotive halogen and LED lighting lamps", "Aftermarket replacement cable sales"],
        positive_catalysts=["Global market share gains in automotive control cables", "Stribog / Kongsberg cable business acquisition synergies", "Domestic 2-wheeler rural recovery"],
        negative_catalysts=["Rapid electric vehicle simplification reducing cable count per vehicle", "Raw material steel wire price rises"],
        regulatory_bodies=["MORTH"]
    ),
    "BHARATFORG": CompanyProfile(
        symbol="BHARATFORG",
        company_name="Bharat Forge Limited",
        sector="Capital Goods",
        industry="Forgings, Defence Artillery & Auto Components",
        market_cap_category="large_cap",
        business_summary="World's largest forging company; manufactures crankshafts and chassis components for commercial vehicles, and established massive defence artillery business (ATAGS, Kalyani Strategic Systems).",
        primary_revenue_sources=["Automotive forgings for global Class 8 trucks and domestic CVs", "Defence artillery guns and armored vehicles", "Industrial aerospace and oil & gas forgings"],
        positive_catalysts=["Indian Army mega procurement orders for ATAGS 155mm artillery guns", "Defence export orders for towed gun systems", "US Class 8 truck order recovery"],
        negative_catalysts=["US/European Class 8 heavy truck order downturn", "Steel scrap input cost inflation"],
        regulatory_bodies=["Ministry of Defence", "MORTH"]
    ),
}


# Pre-computed sector keyword dictionaries for dynamic auto-inference of uncurated stocks
_SECTOR_KEYWORDS: Dict[str, Tuple[str, str, List[str], List[str], List[str]]] = {
    "bank": (
        "Financial Services",
        "Banking Services",
        ["Interest income on retail and corporate loans", "Transaction fees and treasury operations"],
        ["Credit expansion across retail and SME", "Asset quality improvement with lower NPAs", "RBI rate cut cycle easing deposit costs"],
        ["Slippage in loan recovery", "Margin compression from deposit competition", "Regulatory penalties from RBI"]
    ),
    "finance": (
        "Financial Services",
        "Non-Banking Financial Services (NBFC)",
        ["Loan interest and processing charges", "Fee-based investment and credit services"],
        ["AUM growth and strong borrower demand", "Lower wholesale borrowing costs", "Healthy collection efficiency"],
        ["Rise in borrowing cost", "Credit delinquencies in retail loans", "Stricter RBI capital adequacy norms"]
    ),
    "insur": (
        "Financial Services",
        "Insurance Underwriting & Distribution",
        ["Underwriting premiums", "Investment income on policyholder assets", "Distribution commissions"],
        ["Rise in insurance penetration", "Higher term and health insurance demand", "Favorable tax incentives"],
        ["Regulatory commission caps by IRDAI", "Higher surrender payouts", "Spike in claims loss ratio"]
    ),
    "pharma": (
        "Healthcare",
        "Pharmaceuticals & Active Ingredients",
        ["Formulation and generic drug sales", "Active Pharmaceutical Ingredient (API) exports"],
        ["New drug product approvals from USFDA", "Expansion in high-margin chronic formulations", "Clean regulatory plant audits"],
        ["USFDA Form 483 / Warning letters", "Price erosion in generic export markets", "Raw material API cost inflation"]
    ),
    "chem": (
        "Chemicals",
        "Specialty & Industrial Chemicals",
        ["Specialty and basic chemical synthesis", "Export supply to global agro and pharma clients"],
        ["Government anti-dumping duty on foreign imports", "China-plus-one global sourcing shift", "Margin expansion in derivatives"],
        ["Cheap dumping from overseas producers", "Feedstock petrochemical price volatility", "Environmental plant shutdowns"]
    ),
    "cement": (
        "Construction Materials",
        "Cement & Building Materials",
        ["Grey cement sales to infrastructure and housing", "Clinker and concrete ready-mix"],
        ["Sovereign infrastructure and highway budget boost", "Real estate housing construction boom", "Cement bag price hikes"],
        ["Severe price discounting among manufacturers", "Thermal coal and petcoke fuel cost spikes", "Monsoon construction slowdown"]
    ),
    "steel": (
        "Metals",
        "Steel Manufacturing & Processing",
        ["Hot rolled and cold rolled flat steel", "Long steel for construction and infrastructure"],
        ["Anti-dumping duty on imported steel", "Domestic infrastructure capex revival", "Lower coking coal prices"],
        ["Chinese steel dumping at discounted export prices", "Coking coal and iron ore price spikes", "Export tax imposition"]
    ),
    "metal": (
        "Metals",
        "Metals & Mining",
        ["Base metal extraction and smelting", "Mining and value-added alloy products"],
        ["Global LME metal price rally", "Domestic industrial manufacturing growth", "Lower power fuel costs"],
        ["Global commodity slump", "Surge in power and coal input costs", "Mining royalty hikes"]
    ),
    "sugar": (
        "FMCG",
        "Sugar Mills & Ethanol",
        ["Refined sugar production", "Ethanol supplies to OMCs for fuel blending", "Power co-generation"],
        ["Government hike in ethanol procurement prices", "Sugar MSP hike by Centre", "Ethanol blending target expansion"],
        ["Export bans on sugar", "Restrictions on using cane juice for ethanol", "Hike in State Advised Price (SAP) for sugarcane"]
    ),
    "power": (
        "Power",
        "Power Generation & Transmission",
        ["Electricity generation and merchant tariffs", "Grid transmission tariff fees"],
        ["Peak summer power demand surge", "Capacity addition in green renewables", "Prompt discom payment realizations"],
        ["Thermal coal supply shortages", "Discom payment defaults", "Plant grid curtailment"]
    ),
    "solar": (
        "Capital Goods",
        "Solar & Renewable Equipment",
        ["Solar module manufacturing and cells", "Turnkey solar EPC installation"],
        ["PM Surya Ghar rooftop solar scheme", "Domestic content requirement (DCR) rules", "Anti-dumping duty on imported modules"],
        ["Polysilicon and wafer price volatility", "Import tariff uncertainties", "Substation transmission bottlenecks"]
    ),
    "tech": (
        "Information Technology",
        "Software Engineering & IT Services",
        ["Enterprise software engineering", "Digital cloud and generative AI consulting"],
        ["Large multi-year digital transformation deals", "Expansion in generative AI customer outlays", "Offshore rupee depreciation benefits"],
        ["Slowdown in client IT discretionary budgets", "Wage inflation and high employee attrition", "US banking IT spend delays"]
    ),
    "soft": (
        "Information Technology",
        "Software & Digital Solutions",
        ["Enterprise software subscriptions and IT services", "Digital product development"],
        ["Strong deal wins in BFSI and healthcare", "Cloud migration adoption", "Generative AI platform commercialization"],
        ["Global IT spending slowdown", "Key client contract delays"]
    ),
    "infra": (
        "Capital Goods",
        "Civil Infrastructure & EPC",
        ["Highway, metro, and bridge construction contracts", "Urban infrastructure development"],
        ["Government infrastructure capex budget expansion", "Speedy project milestone billing and land clearance", "Robust order backlog"],
        ["Project execution delays and penalty clauses", "Raw material steel and bitumen inflation", "Working capital strain"]
    ),
    "rail": (
        "Capital Goods",
        "Railway Rolling Stock & EPC",
        ["Railway wagons, coaches, and tracks", "Railway signaling and electrification EPC"],
        ["Ministry of Railways mega capex budget", "Tenders for new Vande Bharat and freight trains", "Kavach safety deployment"],
        ["Delays in project award schedules", "Input steel price escalations", "Execution delays"]
    ),
    "auto": (
        "Automobile",
        "Automotive & Ancillaries",
        ["Vehicle and automotive component manufacturing", "Replacement aftermarket parts"],
        ["Festive vehicle retail volume boom", "Commodity metal price softness", "Electric vehicle and export growth"],
        ["Rural demand slowdown", "Raw material price spikes", "High interest rate auto loan cycle"]
    ),
    "textil": (
        "Textiles",
        "Yarn, Fabrics & Apparel Exports",
        ["Yarn spinning and garment exports to US/EU", "Home textiles and technical fabrics"],
        ["Cotton price softness expanding margins", "Free Trade Agreements (FTA) with UK/EU", "Global retail brand inventory restocking"],
        ["Cotton crop damage / price spike", "Global export apparel demand slump", "Currency appreciation"]
    ),
    "hotel": (
        "Consumer Services",
        "Hospitality, Tourism & Resorts",
        ["Room guest tariffs (RevPAR)", "Food, beverage, and banquet wedding events"],
        ["Boom in business travel and MICE conferences", "Surge in average room rates (ARR)", "Strong festive wedding season"],
        ["Travel disruption / pandemic fears", "Higher room supply causing local tariff wars"]
    ),
    "hospit": (
        "Healthcare",
        "Healthcare Delivery & Multi-Specialty Hospitals",
        ["Inpatient surgical and medical procedures", "Diagnostic and outpatient pharmacy"],
        ["High average revenue per occupied bed (ARPOB)", "Expansion in medical tourism", "Addition of tertiary care beds"],
        ["Government price caps on implants / treatments", "High doctor and nursing manpower costs"]
    ),
    "logist": (
        "Services",
        "Freight Forwarding & Supply Chain Logistics",
        ["Express parcel and freight movement", "Warehousing and supply chain management"],
        ["E-commerce festive shipment boom", "Dedicated Freight Corridor operationalization", "GST rationalization"],
        ["Diesel fuel cost surges", "Slowdown in industrial manufacturing shipments"]
    ),
    "paper": (
        "Forest Products",
        "Paper & Packaging Boards",
        ["Writing and printing paper", "Packaging boards for pharma and FMCG"],
        ["Domestic paper price realization firming", "Surge in e-commerce packaging box demand", "Anti-dumping duty on paper imports"],
        ["Spike in imported wood pulp and chemical costs", "Cheap Asian paper dumping"]
    ),
}


def _infer_profile_from_name_and_symbol(symbol: str, company_name: str) -> CompanyProfile:
    """Generate a high-fidelity business profile dynamically for any uncurated NSE equity."""
    clean_sym = symbol.upper().strip()
    name_lower = f"{company_name} {clean_sym}".lower()

    # Search keyword match
    for kw, (sec, ind, revs, pos_cats, neg_cats) in _SECTOR_KEYWORDS.items():
        if kw in name_lower:
            return CompanyProfile(
                symbol=clean_sym,
                company_name=company_name,
                sector=sec,
                industry=ind,
                market_cap_category="mid_cap",
                business_summary=f"NSE-listed equity operating in {sec} ({ind}). Principal operations and products aligned with {company_name}.",
                primary_revenue_sources=revs,
                positive_catalysts=pos_cats,
                negative_catalysts=neg_cats,
                regulatory_bodies=["SEBI", "BSE", "NSE"]
            )

    # General corporate fallback
    return CompanyProfile(
        symbol=clean_sym,
        company_name=company_name,
        sector="Diversified Commercial",
        industry="Industrial & Commercial Products",
        market_cap_category="small_cap",
        business_summary=f"NSE-listed corporate equity ({clean_sym}) engaging in commercial and industrial product operations.",
        primary_revenue_sources=["Domestic sales and commercial contracts", "Operational service revenues"],
        positive_catalysts=["Quarterly revenue and earnings beat", "Expansion in business order backlog", "Lower input commodity costs"],
        negative_catalysts=["Slowdown in sector volume growth", "Working capital elongation", "Margin pressure"],
        regulatory_bodies=["SEBI", "Ministry of Corporate Affairs"]
    )


def get_company_profile(symbol: str) -> Optional[CompanyProfile]:
    """Retrieve company profile for a given NSE ticker symbol.
    
    If not in curated registry, dynamically constructs an inferred profile using
    official NSE master registry metadata so that every listed stock is covered.
    """
    clean_sym = symbol.upper().strip()
    if clean_sym in COMPANY_KNOWLEDGE_BASE:
        return COMPANY_KNOWLEDGE_BASE[clean_sym]

    # Look up from official NSE resolver
    try:
        from app.processors.nse_master import get_nse_resolver
        resolver = get_nse_resolver()
        info = resolver.get_company_info(clean_sym)
        if info:
            inferred = _infer_profile_from_name_and_symbol(clean_sym, info.get("name", clean_sym))
            COMPANY_KNOWLEDGE_BASE[clean_sym] = inferred
            return inferred
    except Exception:
        pass

    return None


def get_profiles_by_sector(sector: str) -> List[CompanyProfile]:
    """Retrieve all company profiles belonging to a specific sector."""
    s = sector.lower()
    return [p for p in COMPANY_KNOWLEDGE_BASE.values() if s in p.sector.lower() or s in p.industry.lower()]


def get_profiles_by_market_cap(category: str) -> List[CompanyProfile]:
    """Retrieve all company profiles for a specific market cap category (large, mid, small, micro)."""
    cat = category.lower().strip()
    return [p for p in COMPANY_KNOWLEDGE_BASE.values() if p.market_cap_category == cat]
