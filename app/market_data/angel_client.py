"""Angel One SmartAPI client — authentication and session management.

Handles TOTP generation, login, token refresh, and expiry.
Single shared session used by all market data modules.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

import pyotp

logger = logging.getLogger("newsedge.market_data.angel_client")

_session_lock = threading.Lock()
_singleton: Optional["AngelOneClient"] = None


def get_angel_client() -> "AngelOneClient":
    """Return the shared singleton AngelOneClient, creating it if needed."""
    global _singleton
    with _session_lock:
        if _singleton is None:
            from app.config import get_settings
            s = get_settings()
            _singleton = AngelOneClient(
                api_key=s.angel_api_key,
                client_id=s.angel_client_id,
                password=s.angel_password,
                totp_secret=s.angel_totp_secret,
            )
        return _singleton


class AngelOneClient:
    """Thin wrapper around SmartConnect that auto-refreshes the session."""

    def __init__(
        self,
        api_key: str,
        client_id: str,
        password: str,
        totp_secret: str,
    ) -> None:
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret

        self._smart = None
        self._auth_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._session_expiry: Optional[datetime] = None
        self._lock = threading.Lock()
        self._rate_lock = threading.Lock()
        self._last_candle_call: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def smart(self):
        """Return an authenticated SmartConnect object, refreshing if needed."""
        with self._lock:
            if self._needs_refresh():
                self._login()
            return self._smart

    def get_candles(
        self,
        symbol_token: str,
        exchange: str = "NSE",
        interval: str = "FIVE_MINUTE",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        """Fetch OHLCV candles. Returns list of dicts with keys:
        timestamp, open, high, low, close, volume.

        interval options: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE,
                          THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        """
        from datetime import datetime as dt

        now = dt.now()
        if from_date is None:
            from_date = now.strftime("%Y-%m-%d 09:15")
        if to_date is None:
            to_date = now.strftime("%Y-%m-%d %H:%M")

        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date,
        }

        for attempt in range(3):
            with self._rate_lock:
                elapsed = time.monotonic() - self._last_candle_call
                if elapsed < 0.55:
                    time.sleep(0.55 - elapsed)
                self._last_candle_call = time.monotonic()

            try:
                resp = self.smart.getCandleData(params)
                if resp and resp.get("status") and resp.get("data"):
                    candles = []
                    for row in resp["data"]:
                        # Angel returns [timestamp, open, high, low, close, volume]
                        candles.append({
                            "timestamp": row[0],
                            "open":   float(row[1]),
                            "high":   float(row[2]),
                            "low":    float(row[3]),
                            "close":  float(row[4]),
                            "volume": int(row[5]),
                        })
                    return candles
                elif resp and "exceeding access rate" in str(resp.get("message", "")).lower():
                    time.sleep(1.2 * (attempt + 1))
                    continue
                else:
                    logger.warning("No candle data for token %s: %s", symbol_token, resp)
                    return []
            except Exception as exc:
                if "access rate" in str(exc).lower() and attempt < 2:
                    logger.debug("Rate limited on token %s, retrying (%d/3)...", symbol_token, attempt + 1)
                    time.sleep(1.2 * (attempt + 1))
                    continue
                logger.error("getCandleData failed for token %s: %s", symbol_token, exc)
                return []
        return []

    def get_ltp(self, exchange: str, trading_symbol: str, symbol_token: str) -> Optional[float]:
        """Get Last Traded Price for a single symbol."""
        try:
            resp = self.smart.ltpData(exchange, trading_symbol, symbol_token)
            if resp and resp.get("status") and resp.get("data"):
                return float(resp["data"].get("ltp", 0))
            return None
        except Exception as exc:
            logger.error("ltpData failed for %s: %s", trading_symbol, exc)
            return None

    def search_scrip(self, exchange: str, trading_symbol: str) -> Optional[str]:
        """Resolve trading symbol to Angel One token. Returns token string or None."""
        try:
            resp = self.smart.searchScrip(exchange, trading_symbol)
            if resp and resp.get("status") and resp.get("data"):
                for item in resp["data"]:
                    if item.get("tradingsymbol", "").upper() == trading_symbol.upper():
                        return str(item.get("symboltoken", ""))
            return None
        except Exception as exc:
            logger.error("searchScrip failed for %s: %s", trading_symbol, exc)
            return None

    # ── Private helpers ───────────────────────────────────────────────────

    def _needs_refresh(self) -> bool:
        if self._smart is None or self._auth_token is None:
            return True
        if self._session_expiry and datetime.now() >= self._session_expiry:
            return True
        return False

    def _login(self) -> None:
        from SmartApi import SmartConnect
        logger.info("Logging into Angel One SmartAPI (client: %s)...", self.client_id)

        totp_code = pyotp.TOTP(self.totp_secret).now()
        smart = SmartConnect(api_key=self.api_key)

        for attempt in range(3):
            try:
                data = smart.generateSession(
                    self.client_id, self.password, totp_code
                )
                if data and data.get("status"):
                    self._smart = smart
                    self._auth_token = data["data"]["jwtToken"]
                    self._refresh_token = data["data"].get("refreshToken", "")
                    self._feed_token = smart.getfeedToken()
                    # Sessions typically last ~8 hours; refresh after 7h
                    self._session_expiry = datetime.now() + timedelta(hours=7)
                    logger.info("Angel One session established. Expires: %s", self._session_expiry.strftime("%H:%M"))
                    return
                else:
                    logger.warning("Login attempt %d failed: %s", attempt + 1, data)
            except Exception as exc:
                logger.warning("Login attempt %d exception: %s", attempt + 1, exc)
            # Regenerate TOTP for next attempt (code rotates every 30s)
            totp_code = pyotp.TOTP(self.totp_secret).now()
            time.sleep(2)

        raise RuntimeError(
            f"Angel One login failed after 3 attempts for client {self.client_id}"
        )
