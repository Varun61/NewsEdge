"""Sector and broad market momentum context for conviction modifiers.

Checks if the broader market/sectoral index is in a sell-off or rally,
which affects how individual stock catalysts play out intraday.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger("newsedge.intelligence.sector_momentum")

# Sector classification for key high-volume NSE equities
STOCK_SECTOR_MAP: Dict[str, str] = {
    # Banking & Financial Services
    "HDFCBANK": "BANKING", "ICICIBANK": "BANKING", "SBIN": "BANKING",
    "AXISBANK": "BANKING", "KOTAKBANK": "BANKING", "BANDHANBNK": "BANKING",
    "IDFCFIRSTB": "BANKING", "FEDERALBNK": "BANKING", "INDUSINDBK": "BANKING",
    "PNB": "BANKING", "BANKBARODA": "BANKING", "CANBK": "BANKING",
    "AUBANK": "BANKING", "RBLBANK": "BANKING", "BAJFINANCE": "FINANCE",
    "BAJAJFINSV": "FINANCE", "CHOLAFIN": "FINANCE", "MUTHOOTFIN": "FINANCE",
    "SHRIRAMFIN": "FINANCE", "SBILIFE": "FINANCE", "HDFCLIFE": "FINANCE",
    "ICICIPRULI": "FINANCE",

    # IT Services & Tech
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "HCLTECH": "IT",
    "TECHM": "IT", "LTIM": "IT", "MPHASIS": "IT", "COFORGE": "IT",
    "PERSISTENT": "IT", "TATAELXSI": "IT", "KPITTECH": "IT", "LTTS": "IT",

    # FMCG & Retail
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG", "COLPAL": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG",
    "GODREJCP": "FMCG", "TATACONSUM": "FMCG", "EMAMILTD": "FMCG",
    "BAJAJCON": "FMCG", "VBL": "FMCG", "RADICO": "FMCG", "TRENT": "FMCG",

    # Pharma & Healthcare
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA",
    "DIVISLAB": "PHARMA", "AUROPHARMA": "PHARMA", "BIOCON": "PHARMA",
    "LUPIN": "PHARMA", "TORNTPHARM": "PHARMA", "MANKIND": "PHARMA",
    "APOLLOHOSP": "PHARMA", "MAXHEALTH": "PHARMA", "FORTIS": "PHARMA",

    # Auto & Ancillaries
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "TMCV": "AUTO", "TMPV": "AUTO",
    "M&M": "AUTO", "BAJAJ-AUTO": "AUTO", "EICHERMOT": "AUTO",
    "HEROMOTOCO": "AUTO", "ASHOKLEY": "AUTO", "TVSMOTOR": "AUTO",
    "BHARATFORG": "AUTO", "MOTHERSON": "AUTO", "BOSCHLTD": "AUTO",

    # Metals & Mining
    "JSWSTEEL": "METALS", "TATASTEEL": "METALS", "HINDALCO": "METALS",
    "VEDL": "METALS", "COALINDIA": "METALS", "NMDC": "METALS",
    "JINDALSTEL": "METALS", "SAIL": "METALS", "NATIONALUM": "METALS",

    # Energy, Oil & Gas, Power
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "BPCL": "ENERGY", "IOC": "ENERGY",
    "GAIL": "ENERGY", "NTPC": "ENERGY", "POWERGRID": "ENERGY",
    "ADANIGREEN": "ENERGY", "TATAPOWER": "ENERGY", "NHPC": "ENERGY",
    "IGL": "ENERGY", "MGL": "ENERGY", "GUJGASLTD": "ENERGY",

    # Infrastructure, Capital Goods, Defense
    "LT": "INFRA", "ADANIENT": "INFRA", "ADANIPORTS": "INFRA",
    "ULTRACEMCO": "INFRA", "GRASIM": "INFRA", "SHREECEM": "INFRA",
    "AMBUJACEM": "INFRA", "HAL": "DEFENSE", "BEL": "DEFENSE",
    "BDL": "DEFENSE", "MAZDOCK": "DEFENSE", "BHEL": "INFRA",
    "SIEMENS": "INFRA", "ABB": "INFRA", "TITAGARH": "INFRA", "RVNL": "INFRA",
    "IRFC": "INFRA", "RAILTEL": "INFRA",
}

SECTOR_INDEX_MAP: Dict[str, str] = {
    "BROAD": "^NSEI",          # Nifty 50
    "BANKING": "^NSEBANK",     # Bank Nifty
    "FINANCE": "^NSEBANK",
    "IT": "^CNXIT",            # Nifty IT
    "AUTO": "^CNXAUTO",
    "PHARMA": "^CNXPHARMA",
    "METALS": "^CNXMETAL",
    "FMCG": "^CNXFMCG",
    "ENERGY": "^CNXENERGY",
    "INFRA": "^CNXINFRA",
}


class SectorMomentumAnalyzer:
    """Caches recent sector/index returns to provide market tailwind/headwind context."""

    def __init__(self, cache_ttl_seconds: int = 14400):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_returns: Dict[str, float] = {}
        self._last_fetched_time: float = 0.0

    def _fetch_index_returns(self) -> Dict[str, float]:
        """Download latest 1-day returns for benchmark indices using yfinance."""
        now = time.time()
        if self._cached_returns and (now - self._last_fetched_time < self.cache_ttl_seconds):
            return self._cached_returns

        import yfinance as yf

        symbols_to_fetch = list(set(SECTOR_INDEX_MAP.values()))
        returns: Dict[str, float] = {}

        try:
            # Download 5 days to ensure we have the most recent 2 closes
            data = yf.download(
                " ".join(symbols_to_fetch),
                period="5d",
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            if not data.empty and "Close" in data:
                close_df = data["Close"]
                for ticker in symbols_to_fetch:
                    try:
                        s_series = close_df[ticker].dropna() if len(symbols_to_fetch) > 1 else close_df.dropna()
                        if len(s_series) >= 2:
                            prev = float(s_series.iloc[-2])
                            curr = float(s_series.iloc[-1])
                            if prev > 0:
                                pct_chg = ((curr - prev) / prev) * 100.0
                                returns[ticker] = round(pct_chg, 2)
                    except Exception as ex:
                        logger.debug("Failed to calculate return for %s: %s", ticker, ex)
            self._cached_returns = returns
            self._last_fetched_time = now
        except Exception as exc:
            logger.warning("Error fetching index momentum returns: %s", exc)

        return self._cached_returns

    def get_sector_modifier(self, nse_symbol: str) -> float:
        """Returns score modifier (-12.0 to +5.0) based on prevailing sector/index trend."""
        clean_sym = nse_symbol.upper().strip()
        sector = STOCK_SECTOR_MAP.get(clean_sym)

        # In offline or test environments, returns might be empty
        index_returns = self._fetch_index_returns()
        if not index_returns:
            return 0.0

        nifty_ret = index_returns.get("^NSEI", 0.0)
        sector_ticker = SECTOR_INDEX_MAP.get(sector, "^NSEI") if sector else "^NSEI"
        sector_ret = index_returns.get(sector_ticker, nifty_ret)

        # 1. Severe sector sell-off: drags even positive stock announcements down
        if sector_ret <= -2.0:
            return -12.0
        elif sector_ret <= -1.0:
            return -8.0

        # 2. Broad market panic (Nifty down > 1.5%)
        if nifty_ret <= -1.5:
            return -6.0

        # 3. Strong sector rally gives tailwind to positive catalyst
        if sector_ret >= 1.5:
            return +5.0

        return 0.0


_instance: Optional[SectorMomentumAnalyzer] = None


def get_sector_momentum_analyzer() -> SectorMomentumAnalyzer:
    global _instance
    if _instance is None:
        _instance = SectorMomentumAnalyzer()
    return _instance
