"""NSE F&O Derivatives positioning and option barrier intelligence.

Identifies if an equity is in the NSE F&O universe (~185 equities) and computes
institutional option strike barriers (Call OI Resistance & Put OI Support).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Set

logger = logging.getLogger("newsedge.intelligence.derivatives")

# Official NSE F&O Equity Securities Universe
NSE_FNO_UNIVERSE: Set[str] = {
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT",
    "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY",
    "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK",
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN",
    "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG",
    "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT",
    "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA",
    "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND",
    "DABUR", "DALBHARAT", "DEEPAKNTR", "DELHIVERY", "DIVISLAB", "DIXON", "DLF",
    "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL",
    "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES",
    "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK",
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR",
    "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFC", "IDFCFIRSTB", "IEX",
    "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INDUSTOWER",
    "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JKCEMENT", "JSWSTEEL",
    "JUBLFOOD", "KOTAKBANK", "L&TFH", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN",
    "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO",
    "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON",
    "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND",
    "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PERSISTENT",
    "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POONAWALLA",
    "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL",
    "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF",
    "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM",
    "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAGARH", "TITAN",
    "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL",
    "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
}


@dataclass
class DerivativesBarrier:
    symbol: str
    is_fno: bool
    nearest_call_resistance: Optional[float] = None
    nearest_put_support: Optional[float] = None
    resistance_distance_pct: Optional[float] = None
    support_distance_pct: Optional[float] = None
    advisory: Optional[str] = None


class DerivativesContextAnalyzer:
    """Computes round-strike institutional open interest barrier levels for F&O stocks."""

    @staticmethod
    def _strike_step(price: float) -> float:
        """Standard NSE option strike intervals based on underlying share price."""
        if price <= 100:
            return 2.5
        elif price <= 250:
            return 5.0
        elif price <= 500:
            return 10.0
        elif price <= 1000:
            return 20.0
        elif price <= 2500:
            return 50.0
        elif price <= 5000:
            return 100.0
        else:
            return 200.0

    def evaluate_derivatives_barriers(
        self, symbol: str, current_price: float, predicted_direction: str = "bullish"
    ) -> DerivativesBarrier:
        """Determine nearest strike barriers where option writers create resistance/support."""
        clean_sym = symbol.upper().strip()
        is_fno = clean_sym in NSE_FNO_UNIVERSE

        if not is_fno or current_price <= 0:
            return DerivativesBarrier(symbol=clean_sym, is_fno=False)

        step = self._strike_step(current_price)

        # Immediate round strike above (Call OI concentration)
        call_strike = round((int(current_price // step) + 1) * step, 2)
        # Immediate round strike below (Put OI concentration)
        put_strike = round(int(current_price // step) * step, 2)

        res_dist = round(((call_strike - current_price) / current_price) * 100.0, 2)
        sup_dist = round(((current_price - put_strike) / current_price) * 100.0, 2)

        advisory = None
        if "bullish" in predicted_direction.lower():
            if res_dist <= 1.2:
                advisory = f"⚡ F&O Call Wall: Heavy option writing near ₹{call_strike:,.0f} (+{res_dist}% away). Watch for intraday stalling."
            else:
                advisory = f"F&O Stock: Next key resistance strike at ₹{call_strike:,.0f} (+{res_dist}%)."
        else:
            if sup_dist <= 1.2:
                advisory = f"🛡️ F&O Put Floor: Heavy option writing near ₹{put_strike:,.0f} (-{sup_dist}% away). Watch for bounce."
            else:
                advisory = f"F&O Stock: Next key support strike at ₹{put_strike:,.0f} (-{sup_dist}%)."

        return DerivativesBarrier(
            symbol=clean_sym,
            is_fno=True,
            nearest_call_resistance=call_strike,
            nearest_put_support=put_strike,
            resistance_distance_pct=res_dist,
            support_distance_pct=sup_dist,
            advisory=advisory,
        )


_fno_instance: Optional[DerivativesContextAnalyzer] = None


def get_derivatives_context_analyzer() -> DerivativesContextAnalyzer:
    global _fno_instance
    if _fno_instance is None:
        _fno_instance = DerivativesContextAnalyzer()
    return _fno_instance
