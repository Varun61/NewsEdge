"""Comprehensive NSE stock universe and intelligent entity resolution.

Contains a curated master list of actively traded NSE stocks plus automatic
ingestion of the full official NSE equity list (EQUITY_L.csv, 2300+ equities).

Ensures only genuine NSE-listed equities are matched, completely eliminating
unlisted entities, media publishers, or phantom stock hallucinations.
"""

from __future__ import annotations

import csv
import difflib
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("newsedge.processors.nse_master")

PUBLISHER_SUFFIX_PATTERN = re.compile(
    r"\s*[-–|]\s*(?:Kalkine(?:\s+India)?|The\s+Economic\s+Times|Economic\s+Times|Mint|Livemint|Business\s+Standard|NDTV(?:\s+Profit)?|CNBC(?:-TV18|\s+TV18)?|Moneycontrol|Reuters|Bloomberg|Financial\s+Express|Zee\s+Business|ChiniMandi|HDFC\s+Sky|Goodreturns|BQ\s+Prime|[A-Za-z0-9\s.&]+)$",
    re.IGNORECASE,
)

ALIAS_STOPWORDS: Set[str] = {
    "india", "indian", "limited", "ltd", "the", "and", "life", "tech", "power", "gold", "rate",
    "bank", "auto", "news", "new", "good", "best", "next", "real", "true", "care", "fast",
    "high", "net", "win", "hold", "gain", "fall", "finance", "global", "services", "capital",
    "group", "holdings", "holding", "industries", "industry", "enterprises", "solutions",
    "corporation", "corp", "products", "systems", "infra", "infrastructure", "international",
    "first", "bharat", "national", "state", "general", "central", "united", "standard",
    "trust", "asset", "management", "housing", "retail", "digital", "energy", "petro",
    "metals", "mining", "pharma", "chemicals", "security", "securities", "market", "markets",
    "commercial", "development", "enterprise", "financial", "growth", "investment", "investing",
    "trading", "industrial", "engineering", "technologies", "technology", "logistics", "shipping",
    "premier", "universal", "supreme", "advanced", "applied", "associated", "integrated", "allied",
    "eastern", "western", "southern", "northern", "cooperative", "construction", "consultancy",
    "share", "shares", "stock", "stocks", "equity", "equities", "exchange", "exchanges",
    "fund", "funds", "bond", "bonds", "debt", "debts", "price", "prices", "rates"
}

SYMBOL_STOPWORDS: Set[str] = {
    "A", "ALL", "AT", "AN", "AND", "AS", "BE", "BY", "FOR", "GO", "IN", "IS",
    "IT", "NEW", "NOW", "OF", "ON", "OR", "SO", "THE", "TO", "UP", "US", "WIN",
    "CAN", "BUY", "SELL", "HOLD", "GAIN", "FALL", "HIGH", "LOW", "NET", "ROAD",
    "GOOD", "FAST", "CARE", "AUTO", "NEWS", "BANK", "TRUE", "REAL", "BEST", "NEXT",
    "INDIA", "LIFE", "TECH", "POWER", "GOLD", "RATE", "CRUDE", "NIFTY", "SENSEX",
    "OIL", "GAS", "PAY", "SET", "BIG", "TOP", "KEY", "MAX", "MID", "MAP", "DAY",
    "ONE", "TWO", "SIX", "TEN", "RED", "SEE", "YES", "TV", "IPO", "Q1", "Q2", "Q3", "Q4",
    "FY24", "FY25", "FY26", "FY27", "CEO", "CFO", "MD", "RBI", "FED", "GDP", "FII", "DII",
    "BSE", "NSE"
}


def clean_headline_publisher(headline: str) -> str:
    """Strip ' - Publisher Name' at the end of RSS article titles."""
    return PUBLISHER_SUFFIX_PATTERN.sub("", headline).strip()


# Curated baseline metadata for key traded Indian stocks
NSE_MASTER_DATA: list[dict] = [
    # --- NIFTY 50 & MEGA CAPS ---
    {"symbol": "RELIANCE", "name": "Reliance Industries Limited", "sector": "Energy", "industry": "Refineries & Retail", "revenue": 900000.0, "cap": "large_cap", "aliases": ["Reliance", "RIL", "Jio", "Reliance Retail"]},
    {"symbol": "TCS", "name": "Tata Consultancy Services Limited", "sector": "Information Technology", "industry": "IT Services", "revenue": 240000.0, "cap": "large_cap", "aliases": ["Tata Consultancy", "Tata Consultancy Services"]},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Limited", "sector": "Financial Services", "industry": "Private Bank", "revenue": 280000.0, "cap": "large_cap", "aliases": ["HDFC Bank", "HDFC"]},
    {"symbol": "INFY", "name": "Infosys Limited", "sector": "Information Technology", "industry": "IT Services", "revenue": 153000.0, "cap": "large_cap", "aliases": ["Infosys", "Infosys Ltd"]},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Limited", "sector": "Financial Services", "industry": "Private Bank", "revenue": 186000.0, "cap": "large_cap", "aliases": ["ICICI Bank", "ICICI"]},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Limited", "sector": "FMCG", "industry": "Consumer Goods", "revenue": 60000.0, "cap": "large_cap", "aliases": ["Hindustan Unilever", "HUL", "Unilever"]},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Financial Services", "industry": "Public Bank", "revenue": 440000.0, "cap": "large_cap", "aliases": ["State Bank", "State Bank of India", "SBI"]},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Limited", "sector": "Telecommunication", "industry": "Telecom Services", "revenue": 150000.0, "cap": "large_cap", "aliases": ["Bharti Airtel", "Airtel"]},
    {"symbol": "ITC", "name": "ITC Limited", "sector": "FMCG", "industry": "Cigarettes & Hotels", "revenue": 70000.0, "cap": "large_cap", "aliases": ["ITC", "ITC Ltd"]},
    {"symbol": "LT", "name": "Larsen & Toubro Limited", "sector": "Capital Goods", "industry": "Infrastructure & Engineering", "revenue": 221000.0, "cap": "large_cap", "aliases": ["Larsen & Toubro", "Larsen and Toubro", "L&T", "Larsen"]},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Limited", "sector": "Financial Services", "industry": "Private Bank", "revenue": 80000.0, "cap": "large_cap", "aliases": ["Kotak Mahindra Bank", "Kotak Bank", "Kotak"]},
    {"symbol": "AXISBANK", "name": "Axis Bank Limited", "sector": "Financial Services", "industry": "Private Bank", "revenue": 125000.0, "cap": "large_cap", "aliases": ["Axis Bank"]},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Limited", "sector": "Financial Services", "industry": "NBFC", "revenue": 54000.0, "cap": "large_cap", "aliases": ["Bajaj Finance"]},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Limited", "sector": "Consumer Durables", "industry": "Paints", "revenue": 35000.0, "cap": "large_cap", "aliases": ["Asian Paints", "Asian Paint"]},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Limited", "sector": "Automobile", "industry": "Passenger Cars", "revenue": 140000.0, "cap": "large_cap", "aliases": ["Maruti Suzuki", "Maruti"]},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Limited", "sector": "Healthcare", "industry": "Pharmaceuticals", "revenue": 48000.0, "cap": "large_cap", "aliases": ["Sun Pharma", "Sun Pharmaceuticals"]},
    {"symbol": "TITAN", "name": "Titan Company Limited", "sector": "Consumer Durables", "industry": "Jewellery & Watches", "revenue": 51000.0, "cap": "large_cap", "aliases": ["Titan", "Titan Company", "Tanishq"]},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Limited", "sector": "Construction Materials", "industry": "Cement", "revenue": 70000.0, "cap": "large_cap", "aliases": ["UltraTech Cement", "UltraTech"]},
    {"symbol": "WIPRO", "name": "Wipro Limited", "sector": "Information Technology", "industry": "IT Services", "revenue": 89000.0, "cap": "large_cap", "aliases": ["Wipro"]},
    {"symbol": "HCLTECH", "name": "HCL Technologies Limited", "sector": "Information Technology", "industry": "IT Services", "revenue": 109000.0, "cap": "large_cap", "aliases": ["HCL Tech", "HCL Technologies"]},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Limited", "sector": "Automobile", "industry": "Automobiles", "revenue": 437000.0, "cap": "large_cap", "aliases": ["Tata Motors", "TaMo", "Jaguar Land Rover", "JLR"]},
    {"symbol": "TATASTEEL", "name": "Tata Steel Limited", "sector": "Metals & Mining", "industry": "Steel", "revenue": 229000.0, "cap": "large_cap", "aliases": ["Tata Steel"]},
    {"symbol": "NTPC", "name": "NTPC Limited", "sector": "Power", "industry": "Power Generation", "revenue": 178000.0, "cap": "large_cap", "aliases": ["NTPC"]},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation of India Limited", "sector": "Power", "industry": "Power Transmission", "revenue": 45000.0, "cap": "large_cap", "aliases": ["Power Grid", "PowerGrid"]},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Limited", "sector": "Automobile", "industry": "Automobiles & Tractors", "revenue": 139000.0, "cap": "large_cap", "aliases": ["Mahindra & Mahindra", "Mahindra and Mahindra", "Mahindra", "M&M"]},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Limited", "sector": "Metals & Mining", "industry": "Steel", "revenue": 175000.0, "cap": "large_cap", "aliases": ["JSW Steel", "JSW"]},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Limited", "sector": "Metals & Minerals", "industry": "Trading & Infrastructure", "revenue": 96000.0, "cap": "large_cap", "aliases": ["Adani Enterprises"]},
    {"symbol": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Limited", "sector": "Services", "industry": "Port Infrastructure", "revenue": 26000.0, "cap": "large_cap", "aliases": ["Adani Ports", "APSEZ"]},
    {"symbol": "COALINDIA", "name": "Coal India Limited", "sector": "Energy", "industry": "Coal Mining", "revenue": 142000.0, "cap": "large_cap", "aliases": ["Coal India", "CIL"]},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corporation Limited", "sector": "Energy", "industry": "Oil & Gas Exploration", "revenue": 643000.0, "cap": "large_cap", "aliases": ["ONGC", "Oil and Natural Gas Corporation"]},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Limited", "sector": "Financial Services", "industry": "Financial Conglomerate", "revenue": 110000.0, "cap": "large_cap", "aliases": ["Bajaj Finserv"]},
    {"symbol": "TECHM", "name": "Tech Mahindra Limited", "sector": "Information Technology", "industry": "IT Services", "revenue": 52000.0, "cap": "large_cap", "aliases": ["Tech Mahindra"]},
    {"symbol": "GRASIM", "name": "Grasim Industries Limited", "sector": "Materials", "industry": "Diversified", "revenue": 130000.0, "cap": "large_cap", "aliases": ["Grasim Industries", "Grasim"]},
    {"symbol": "CIPLA", "name": "Cipla Limited", "sector": "Healthcare", "industry": "Pharmaceuticals", "revenue": 25000.0, "cap": "large_cap", "aliases": ["Cipla"]},
    {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories Limited", "sector": "Healthcare", "industry": "Pharmaceuticals", "revenue": 28000.0, "cap": "large_cap", "aliases": ["Dr Reddy", "Dr. Reddy's", "Dr Reddys"]},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Limited", "sector": "Automobile", "industry": "2-Wheelers", "revenue": 37000.0, "cap": "large_cap", "aliases": ["Hero MotoCorp", "Hero Moto", "Hero Honda"]},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Limited", "sector": "Automobile", "industry": "2-Wheelers & Commercial", "revenue": 16000.0, "cap": "large_cap", "aliases": ["Eicher Motors", "Eicher", "Royal Enfield"]},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories Limited", "sector": "Healthcare", "industry": "Active Pharma Ingredients", "revenue": 7800.0, "cap": "large_cap", "aliases": ["Divi's Lab", "Divis Laboratories", "Divi's"]},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Limited", "sector": "Healthcare", "industry": "Hospital Services", "revenue": 19000.0, "cap": "large_cap", "aliases": ["Apollo Hospitals", "Apollo Hospital"]},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corporation Limited", "sector": "Energy", "industry": "Refineries", "revenue": 500000.0, "cap": "large_cap", "aliases": ["Bharat Petroleum", "BPCL"]},
    {"symbol": "BRITANNIA", "name": "Britannia Industries Limited", "sector": "FMCG", "industry": "Food Products", "revenue": 16000.0, "cap": "large_cap", "aliases": ["Britannia Industries", "Britannia"]},
    {"symbol": "TATACONSUM", "name": "Tata Consumer Products Limited", "sector": "FMCG", "industry": "Foods & Beverages", "revenue": 15000.0, "cap": "large_cap", "aliases": ["Tata Consumer", "Tata Consumer Products", "Tata Tea"]},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Limited", "sector": "Metals & Mining", "industry": "Aluminium & Copper", "revenue": 215000.0, "cap": "large_cap", "aliases": ["Hindalco Industries", "Hindalco", "Novelis"]},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Limited", "sector": "Automobile", "industry": "2-Wheelers & 3-Wheelers", "revenue": 44000.0, "cap": "large_cap", "aliases": ["Bajaj Auto"]},

    # --- PSU, DEFENCE, RAILWAYS, RECOVERY ---
    {"symbol": "GAIL", "name": "GAIL (India) Limited", "sector": "Energy", "industry": "Gas Transmission & Trading", "revenue": 133000.0, "cap": "large_cap", "aliases": ["GAIL", "GAIL India", "GAIL (India)", "Gas Authority of India"]},
    {"symbol": "HAL", "name": "Hindustan Aeronautics Limited", "sector": "Capital Goods", "industry": "Defence & Aerospace", "revenue": 30000.0, "cap": "large_cap", "aliases": ["Hindustan Aeronautics", "HAL"]},
    {"symbol": "BEL", "name": "Bharat Electronics Limited", "sector": "Capital Goods", "industry": "Defence Electronics", "revenue": 20000.0, "cap": "large_cap", "aliases": ["Bharat Electronics", "BEL"]},
    {"symbol": "BHEL", "name": "Bharat Heavy Electricals Limited", "sector": "Capital Goods", "industry": "Heavy Electrical Equipment", "revenue": 23000.0, "cap": "mid_cap", "aliases": ["Bharat Heavy Electricals", "BHEL"]},
    {"symbol": "MAZDOCK", "name": "Mazagon Dock Shipbuilders Limited", "sector": "Capital Goods", "industry": "Shipbuilding & Defence", "revenue": 9500.0, "cap": "mid_cap", "aliases": ["Mazagon Dock", "Mazagon Dock Shipbuilders", "Mazdock", "MDL"]},
    {"symbol": "COCHINSHIP", "name": "Cochin Shipyard Limited", "sector": "Capital Goods", "industry": "Shipbuilding", "revenue": 3800.0, "cap": "mid_cap", "aliases": ["Cochin Shipyard"]},
    {"symbol": "GRSE", "name": "Garden Reach Shipbuilders & Engineers Limited", "sector": "Capital Goods", "industry": "Shipbuilding & Defence", "revenue": 3600.0, "cap": "small_cap", "aliases": ["Garden Reach Shipbuilders", "Garden Reach", "GRSE"]},
    {"symbol": "BDL", "name": "Bharat Dynamics Limited", "sector": "Capital Goods", "industry": "Missiles & Defence Systems", "revenue": 2500.0, "cap": "mid_cap", "aliases": ["Bharat Dynamics", "BDL"]},
    {"symbol": "BEML", "name": "BEML Limited", "sector": "Capital Goods", "industry": "Mining, Construction & Rail", "revenue": 4000.0, "cap": "small_cap", "aliases": ["BEML", "Bharat Earth Movers"]},
    {"symbol": "RVNL", "name": "Rail Vikas Nigam Limited", "sector": "Services", "industry": "Railway Infrastructure", "revenue": 21000.0, "cap": "mid_cap", "aliases": ["Rail Vikas Nigam", "Rail Vikas", "RVNL"]},
    {"symbol": "IRFC", "name": "Indian Railway Finance Corporation Limited", "sector": "Financial Services", "industry": "Railway Financing", "revenue": 26000.0, "cap": "large_cap", "aliases": ["Indian Railway Finance Corporation", "IRFC"]},
    {"symbol": "IRCTC", "name": "Indian Railway Catering and Tourism Corporation", "sector": "Consumer Services", "industry": "Rail Travel & Catering", "revenue": 4200.0, "cap": "mid_cap", "aliases": ["Indian Railway Catering", "IRCTC"]},
    {"symbol": "SIGNATURE", "name": "Signatureglobal (India) Limited", "sector": "Realty", "industry": "Real Estate Development", "revenue": 2800.0, "cap": "mid_cap", "aliases": ["Signatureglobal", "Signature Global", "Signatureglobal India"]},
    {"symbol": "ASTEC", "name": "Astec LifeSciences Limited", "sector": "Chemicals", "industry": "Agrochemicals", "revenue": 600.0, "cap": "small_cap", "aliases": ["Astec LifeSciences", "Astec Life"]},
    {"symbol": "SHAILY", "name": "Shaily Engineering Plastics Limited", "sector": "Capital Goods", "industry": "Plastics & Precision", "revenue": 650.0, "cap": "small_cap", "aliases": ["Shaily Engineering", "Shaily Engineering Plastics"]},
    {"symbol": "EPACK", "name": "EPACK Durable Limited", "sector": "Consumer Durables", "industry": "EMS & Appliances", "revenue": 1400.0, "cap": "small_cap", "aliases": ["EPACK Durable", "EPACK"]},
    {"symbol": "GRINFRA", "name": "G R Infraprojects Limited", "sector": "Capital Goods", "industry": "Roads & Highways", "revenue": 8500.0, "cap": "mid_cap", "aliases": ["G R Infraprojects", "GR Infra", "G R Infra"]},
    {"symbol": "CHEMFAB", "name": "Chemfab Alkalis Limited", "sector": "Chemicals", "industry": "Chlor-Alkali", "revenue": 350.0, "cap": "small_cap", "aliases": ["Chemfab Alkalis", "Chemfab"]},
    {"symbol": "SUZLON", "name": "Suzlon Energy Limited", "sector": "Capital Goods", "industry": "Wind Energy", "revenue": 6500.0, "cap": "mid_cap", "aliases": ["Suzlon Energy", "Suzlon"]},
    {"symbol": "TATAPOWER", "name": "Tata Power Company Limited", "sector": "Power", "industry": "Power & Renewables", "revenue": 61000.0, "cap": "large_cap", "aliases": ["Tata Power", "Tata Power Company"]},
    {"symbol": "ZOMATO", "name": "Zomato Limited", "sector": "Consumer Services", "industry": "Food & Quick Commerce", "revenue": 12000.0, "cap": "large_cap", "aliases": ["Zomato", "Blinkit"]},
    {"symbol": "TRENT", "name": "Trent Limited", "sector": "Consumer Services", "industry": "Retail & Apparel", "revenue": 12000.0, "cap": "large_cap", "aliases": ["Trent", "Westside", "Zudio"]},
    {"symbol": "EQUITASBNK", "name": "Equitas Small Finance Bank Limited", "sector": "Financial Services", "industry": "Small Finance Bank", "revenue": 5500.0, "cap": "mid_cap", "aliases": ["Equitas Small Finance Bank", "Equitas Bank", "Equitas SFB"]},
    {"symbol": "LAURUSLABS", "name": "Laurus Labs Limited", "sector": "Healthcare", "industry": "Pharmaceuticals", "revenue": 5000.0, "cap": "mid_cap", "aliases": ["Laurus Labs", "Laurus"]},
    {"symbol": "MOTILALOFS", "name": "Motilal Oswal Financial Services Limited", "sector": "Financial Services", "industry": "Brokerage & AMC", "revenue": 5200.0, "cap": "mid_cap", "aliases": ["Motilal Oswal", "Motilal Oswal Financial Services", "MOFSL"]},
    {"symbol": "IDBI", "name": "IDBI Bank Limited", "sector": "Financial Services", "industry": "Banking", "revenue": 25000.0, "cap": "large_cap", "aliases": ["IDBI Bank", "IDBI"]},
    {"symbol": "GREAVESCOT", "name": "Greaves Cotton Limited", "sector": "Capital Goods", "industry": "Engines & EV", "revenue": 2600.0, "cap": "small_cap", "aliases": ["Greaves Cotton", "Greaves"]},
    {"symbol": "BOROLTD", "name": "Borosil Limited", "sector": "Consumer Durables", "industry": "Glassware", "revenue": 1000.0, "cap": "small_cap", "aliases": ["Borosil", "Borosil Limited"]},
    {"symbol": "GODREJCP", "name": "Godrej Consumer Products Limited", "sector": "FMCG", "industry": "Consumer Goods", "revenue": 14000.0, "cap": "large_cap", "aliases": ["Godrej Consumer Products", "Godrej Consumer", "GCPL"]},
    {"symbol": "KAYNES", "name": "Kaynes Technology India Limited", "sector": "Capital Goods", "industry": "Electronics Manufacturing Services", "revenue": 1800.0, "cap": "mid_cap", "aliases": ["Kaynes Technology", "Kaynes Tech", "Kaynes"]},
    {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance Limited", "sector": "Financial Services", "industry": "Gold Financing NBFC", "revenue": 13000.0, "cap": "large_cap", "aliases": ["Muthoot Finance", "Muthoot"]},
    {"symbol": "TITAGARH", "name": "Titagarh Rail Systems Limited", "sector": "Capital Goods", "industry": "Rolling Stock & Wagons", "revenue": 3800.0, "cap": "mid_cap", "aliases": ["Titagarh Rail Systems", "Titagarh Rail", "Titagarh Wagons", "Titagarh"]},
    {"symbol": "JWL", "name": "Jupiter Wagons Limited", "sector": "Capital Goods", "industry": "Wagons & Castings", "revenue": 3500.0, "cap": "small_cap", "aliases": ["Jupiter Wagons", "Jupiter Wagons Limited"]},
    {"symbol": "KERNEX", "name": "Kernex Microsystems (India) Limited", "sector": "Information Technology", "industry": "Railway Safety & Kavach", "revenue": 150.0, "cap": "micro_cap", "aliases": ["Kernex Microsystems", "Kernex"]},
    {"symbol": "ZENTEC", "name": "Zen Technologies Limited", "sector": "Capital Goods", "industry": "Anti-Drone & Simulators", "revenue": 500.0, "cap": "small_cap", "aliases": ["Zen Technologies", "Zen Tech"]},
    {"symbol": "PARAS", "name": "Paras Defence and Space Technologies Limited", "sector": "Capital Goods", "industry": "Defence Optics & EMP", "revenue": 280.0, "cap": "micro_cap", "aliases": ["Paras Defence", "Paras Defence and Space"]},
    {"symbol": "DATAPATTNS", "name": "Data Patterns (India) Limited", "sector": "Capital Goods", "industry": "Defence Avionics & Radars", "revenue": 550.0, "cap": "small_cap", "aliases": ["Data Patterns", "Data Patterns India"]},
    {"symbol": "NETWEB", "name": "Netweb Technologies India Limited", "sector": "Information Technology", "industry": "HPC & AI Supercomputing", "revenue": 800.0, "cap": "small_cap", "aliases": ["Netweb Technologies", "Netweb"]},
    {"symbol": "MARKSANS", "name": "Marksans Pharma Limited", "sector": "Healthcare", "industry": "Formulations & Generics", "revenue": 2200.0, "cap": "small_cap", "aliases": ["Marksans Pharma", "Marksans"]},
]


class NSEStockResolver:
    """High-speed in-memory resolution of company mentions to verified official NSE symbols."""

    def __init__(self):
        self._symbol_map: Dict[str, dict] = {}       # SYMBOL -> company info
        self._name_map: Dict[str, str] = {}          # normalized name -> SYMBOL
        self._alias_map: Dict[str, str] = {}         # normalized alias -> SYMBOL
        self._sorted_aliases: List[Tuple[str, str]] = []  # (phrase, SYMBOL) sorted by length desc

        self._build_index()

    @staticmethod
    def normalize_text(text: str) -> str:
        """Lowercase, remove punctuation, collapse whitespace."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _build_index(self):
        # 1. First ingest all official equities from data/EQUITY_L.csv if present
        csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "EQUITY_L.csv"
        if csv_path.exists():
            try:
                with open(csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
                        sym = clean_row.get("SYMBOL", "").upper()
                        name = clean_row.get("NAME OF COMPANY", "")
                        series = clean_row.get("SERIES", "")
                        isin = clean_row.get("ISIN NUMBER", "")

                        if sym and series == "EQ":
                            self._symbol_map[sym] = {
                                "symbol": sym,
                                "name": name,
                                "isin": isin,
                                "sector": "Diversified",
                                "industry": "Diversified",
                                "revenue": 5000.0,
                                "cap": "mid_cap",
                            }
                            norm_name = self.normalize_text(name)
                            # 1. Clean corporate legal suffixes (limited, ltd, pvt, india)
                            clean_base = re.sub(r"\b(private|pvt|limited|ltd|india)\b", "", norm_name).strip()
                            clean_base = re.sub(r"\s+", " ", clean_base).strip()
                            if clean_base and len(clean_base) >= 4 and clean_base not in ALIAS_STOPWORDS:
                                self._name_map[clean_base] = sym

                            base_words = clean_base.split()
                            # If company name was genuinely 1 distinctive word (e.g. Infosys, Wipro, TCS)
                            if len(base_words) == 1:
                                single = base_words[0]
                                if len(single) >= 4 and single not in ALIAS_STOPWORDS:
                                    self._alias_map[single] = sym
                            elif len(base_words) >= 2:
                                # 2-word brand prefix (e.g. "Action Construction", "Silver Touch", "Tata Steel")
                                two_words = " ".join(base_words[:2])
                                if len(two_words) >= 5 and two_words not in ALIAS_STOPWORDS:
                                    self._alias_map[two_words] = sym
                            if len(base_words) >= 3:
                                three_words = " ".join(base_words[:3])
                                if len(three_words) >= 7 and three_words not in ALIAS_STOPWORDS:
                                    self._alias_map[three_words] = sym
                logger.info("Loaded %d official equities from EQUITY_L.csv", len(self._symbol_map))
            except Exception as exc:
                logger.warning("Could not parse EQUITY_L.csv: %s", exc)

        # 2. Ingest / override with rich curated metadata
        for item in NSE_MASTER_DATA:
            sym = item["symbol"].upper()
            self._symbol_map[sym] = item

            norm_name = self.normalize_text(item["name"])
            self._name_map[norm_name] = sym

            bare_name = re.sub(
                r"\b(limited|ltd|corporation|corp|industries|industry|enterprises|enterprise|holdings|holding|company|india)\b",
                "",
                norm_name,
            ).strip()
            bare_name = re.sub(r"\s+", " ", bare_name).strip()
            if bare_name and len(bare_name) >= 3 and bare_name not in ALIAS_STOPWORDS:
                self._name_map[bare_name] = sym

            for alias in item.get("aliases", []):
                norm_alias = self.normalize_text(alias)
                if norm_alias and norm_alias not in ALIAS_STOPWORDS:
                    self._alias_map[norm_alias] = sym

        # 3. Build sorted phrases list for greedy matching
        all_phrases = [(k, v) for k, v in self._alias_map.items()] + [(k, v) for k, v in self._name_map.items()]
        seen = set()
        unique_phrases = []
        for phrase, sym in all_phrases:
            if phrase not in seen and len(phrase) >= 3 and phrase not in ALIAS_STOPWORDS:
                seen.add(phrase)
                unique_phrases.append((phrase, sym))

        unique_phrases.sort(key=lambda x: len(x[0]), reverse=True)
        self._sorted_aliases = unique_phrases

    def is_valid_nse_symbol(self, symbol: str) -> bool:
        """Return True if and only if symbol is a verified listed NSE equity."""
        return symbol.upper().strip() in self._symbol_map

    def get_company_info(self, symbol: str) -> Optional[dict]:
        """Return company metadata for a valid NSE symbol."""
        return self._symbol_map.get(symbol.upper().strip())

    def verify_mention_presence(self, symbol: str, name: str, text: str) -> bool:
        """Verify that either the symbol, full name, or a distinctive token is in text."""
        if not text:
            return False
        clean_text = self.normalize_text(clean_headline_publisher(text))
        sym = symbol.upper().strip()

        # Check explicit uppercase symbol
        if re.search(rf"\b{re.escape(sym)}\b", text.upper()):
            return True

        # Check company name or alias
        norm_name = self.normalize_text(name)
        if norm_name and norm_name in clean_text:
            return True

        # Check distinctive word tokens (>=4 chars, not a stopword)
        tokens = [t for t in norm_name.split() if len(t) >= 4 and t not in ALIAS_STOPWORDS]
        for tok in tokens:
            if re.search(rf"\b{re.escape(tok)}\b", clean_text):
                return True

        # Also check registered aliases for curated stocks
        info = self._symbol_map.get(sym)
        if info:
            for al in info.get("aliases", []):
                nal = self.normalize_text(al)
                if nal and len(nal) >= 4 and nal not in ALIAS_STOPWORDS:
                    if re.search(rf"\b{re.escape(nal)}\b", clean_text):
                        return True

        return False

    def resolve_from_symbol_guess(self, raw_symbol: str) -> Optional[dict]:
        """Rescue an LLM-suggested symbol by validating or finding closest valid NSE symbol."""
        if not raw_symbol:
            return None
        sym = re.sub(r"[^A-Z0-9\-]", "", raw_symbol.upper().strip())
        if not sym or sym in SYMBOL_STOPWORDS:
            return None
        if sym in self._symbol_map:
            return self._symbol_map[sym]

        for suffix in ("IND", "INDIA", "LTD", "LIMITED"):
            if sym.endswith(suffix) and len(sym) > len(suffix) + 2:
                cand = sym[:-len(suffix)]
                if cand in self._symbol_map:
                    return self._symbol_map[cand]

        matches = difflib.get_close_matches(sym, list(self._symbol_map.keys()), n=1, cutoff=0.84)
        if matches:
            return self._symbol_map[matches[0]]
        return None

    def resolve_from_text(self, headline: str, body_text: str = "") -> Optional[dict]:
        """Identify the primary listed company and its exact NSE symbol from article text.

        Returns metadata dict or None if no valid NSE listed equity matches.
        """
        # Clean headline from publisher suffixes first
        cleaned_hl = clean_headline_publisher(headline)
        combined = f"{cleaned_hl} {body_text[:500]}"
        norm_headline = self.normalize_text(cleaned_hl)
        norm_combined = self.normalize_text(combined)

        # 1. Check for explicit ticker mentions like "(NSE: LT)", "NSE: GAIL"
        ticker_match = re.search(r"\b(?:NSE|BSE)\s*:\s*([A-Z0-9\-]+)\b", cleaned_hl.upper())
        if ticker_match:
            cand = ticker_match.group(1).upper()
            if cand in self._symbol_map:
                info = self._symbol_map[cand]
                return {**info, "confidence": 98.0, "match_source": "explicit_ticker"}

        # 2. Check for standalone uppercase ticker symbol in headline (e.g. "TCS Q2 results", "BHEL bags order")
        upper_tokens = re.findall(r"\b([A-Z0-9\-]{3,15})\b", cleaned_hl)
        for tok in upper_tokens:
            if tok in self._symbol_map and tok not in SYMBOL_STOPWORDS:
                info = self._symbol_map[tok]
                return {**info, "confidence": 96.0, "match_source": f"headline_symbol:{tok}"}

        # 3. Check for exact alias/name matches in cleaned headline (longest phrase first)
        for phrase, sym in self._sorted_aliases:
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, norm_headline):
                info = self._symbol_map[sym]
                return {**info, "confidence": 95.0, "match_source": f"headline_match:{phrase}"}

        # 4. Check for 2-word n-grams in cleaned headline
        hl_words = norm_headline.split()
        if len(hl_words) >= 2:
            for k in range(len(hl_words) - 1):
                pair = f"{hl_words[k]} {hl_words[k+1]}"
                if pair in self._alias_map:
                    sym = self._alias_map[pair]
                    info = self._symbol_map[sym]
                    return {**info, "confidence": 92.0, "match_source": f"headline_ngram:{pair}"}
                elif pair in self._name_map:
                    sym = self._name_map[pair]
                    info = self._symbol_map[sym]
                    return {**info, "confidence": 92.0, "match_source": f"headline_name_ngram:{pair}"}

        # 5. Check for exact alias/name matches in combined body text
        for phrase, sym in self._sorted_aliases:
            pattern = rf"\b{re.escape(phrase)}\b"
            if re.search(pattern, norm_combined):
                info = self._symbol_map[sym]
                return {**info, "confidence": 85.0, "match_source": f"body_match:{phrase}"}

        # 6. Fuzzy fallback match on headline words against aliases (cutoff 0.88, length >= 6)
        headline_tokens = [w for w in norm_headline.split() if len(w) >= 6 and w not in ALIAS_STOPWORDS]
        for token in headline_tokens:
            matches = difflib.get_close_matches(token, [a for a in self._alias_map.keys() if len(a) >= 6 and a not in ALIAS_STOPWORDS], n=1, cutoff=0.88)
            if matches:
                sym = self._alias_map[matches[0]]
                info = self._symbol_map[sym]
                if self.verify_mention_presence(sym, info.get("name", sym), headline):
                    return {**info, "confidence": 75.0, "match_source": f"fuzzy:{matches[0]}"}

        return None


# Singleton instance
_RESOLVER = NSEStockResolver()


def get_nse_resolver() -> NSEStockResolver:
    """Return singleton NSE stock resolver."""
    return _RESOLVER
