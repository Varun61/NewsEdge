"""Symbol token resolver — maps NSE symbols to Angel One token IDs.

Angel One uses numeric token IDs (not NSE symbols) for all API calls.
This module loads the official Angel One scrip master CSV and builds
an in-memory lookup: NSE_SYMBOL -> token_id.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Dict, Optional

import requests

logger = logging.getLogger("newsedge.market_data.symbol_resolver")

# Angel One scrip master URL (updated daily)
SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
_CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "angel_scrip_master.json"

# In-memory cache: "NSE:SYMBOL" -> {"token": "...", "symbol": "...", "name": "..."}
_symbol_map: Dict[str, dict] = {}
_loaded = False


def get_token(nse_symbol: str) -> Optional[str]:
    """Return Angel One token for an NSE equity symbol. Returns None if not found."""
    _ensure_loaded()
    key = f"NSE:{nse_symbol.upper()}"
    entry = _symbol_map.get(key)
    return entry["token"] if entry else None


def get_token_info(nse_symbol: str) -> Optional[dict]:
    """Return full scrip info dict for an NSE symbol."""
    _ensure_loaded()
    return _symbol_map.get(f"NSE:{nse_symbol.upper()}")


def resolve_many(nse_symbols: list[str]) -> Dict[str, Optional[str]]:
    """Batch resolve: returns {symbol -> token} dict. Missing symbols get None."""
    _ensure_loaded()
    return {sym: get_token(sym) for sym in nse_symbols}


def reload_scrip_master(force: bool = False) -> int:
    """Download and cache the Angel One scrip master. Returns count of NSE equities loaded."""
    global _loaded
    _ensure_data_dir()

    if _CACHE_PATH.exists() and not force:
        import json, time
        age_hours = (time.time() - _CACHE_PATH.stat().st_mtime) / 3600
        if age_hours < 20:  # Reuse cache if < 20 hours old
            logger.debug("Using cached scrip master (%.1fh old).", age_hours)
            return _load_from_cache()

    logger.info("Downloading Angel One scrip master...")
    try:
        resp = requests.get(SCRIP_MASTER_URL, timeout=30)
        resp.raise_for_status()
        _CACHE_PATH.write_bytes(resp.content)
        logger.info("Scrip master downloaded (%d bytes).", len(resp.content))
    except Exception as exc:
        logger.warning("Scrip master download failed: %s. Using stale cache if available.", exc)
        if _CACHE_PATH.exists():
            return _load_from_cache()
        return 0

    return _load_from_cache()


def _load_from_cache() -> int:
    global _symbol_map, _loaded
    import json
    _symbol_map.clear()

    try:
        data = json.loads(_CACHE_PATH.read_bytes())
        count = 0
        for item in data:
            exch = item.get("exch_seg", "")
            sym = item.get("symbol", "").upper()
            inst = item.get("instrumenttype", "")
            # Only load NSE cash-market equities (not derivatives, indices, etc.)
            if exch == "NSE" and inst in ("", "EQ"):
                # Angel symbol field: "RELIANCE-EQ" or "RELIANCE" -> normalize
                clean_sym = sym.replace("-EQ", "").replace("-BE", "").replace("-N1", "").strip()
                key = f"NSE:{clean_sym}"
                _symbol_map[key] = {
                    "token":  item.get("token", ""),
                    "symbol": clean_sym,
                    "name":   item.get("name", ""),
                    "lotsize": item.get("lotsize", 1),
                    "tick_size": item.get("tick_size", 0.05),
                }
                count += 1
        _loaded = True
        logger.info("Loaded %d NSE equities from Angel One scrip master.", count)
        return count
    except Exception as exc:
        logger.error("Failed to parse scrip master: %s", exc)
        return 0


def _ensure_loaded() -> None:
    global _loaded
    if not _loaded:
        reload_scrip_master()


def _ensure_data_dir() -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
