"""Groww Watchlist Synchronization and Export Module.

Allows NewsEdge to automatically synchronize the session's Top 10 Bullish and Top 10 Bearish
stocks directly into the user's Groww trading account watchlists:
- "NewsEdge Bullish"
- "NewsEdge Bearish"

Each pipeline run removes outdated stocks from the previous session and injects
the freshly identified candidates.

Also generates offline import-ready CSV and ticker lists in reports/ for instant
one-click manual copy-paste into Groww web or mobile apps.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("newsedge.integrations.groww")


@dataclass
class GrowwSyncResult:
    success: bool
    bullish_synced: int
    bearish_synced: int
    bullish_watchlist_name: str = "NewsEdge Bullish"
    bearish_watchlist_name: str = "NewsEdge Bearish"
    error_message: Optional[str] = None
    export_files: List[str] = None

    def __post_init__(self):
        if self.export_files is None:
            self.export_files = []


class GrowwWatchlistSync:
    """Manages watchlist synchronization with Groww web and generates broker import files."""

    GROWW_BASE_URL = "https://groww.in/v1/api/stocks_data/v1/watchlist"

    def __init__(
        self,
        auth_token: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
    ):
        """Initialize with Groww JWT / Bearer token or automated TOTP credentials."""
        self.auth_token = auth_token.strip() if auth_token else None
        self.email = email.strip() if email else None
        self.password = password.strip() if password else None
        self.totp_secret = totp_secret.strip() if totp_secret else None

        # If credentials provided, attempt automated session generation if token is missing
        if not self.auth_token and self.email and self.password and self.totp_secret:
            fresh = self.login_with_totp(self.email, self.password, self.totp_secret)
            if fresh:
                self.auth_token = fresh

    @classmethod
    def login_with_totp(cls, email: str, password: str, totp_secret: str) -> Optional[str]:
        """Automatically perform headless login using Email, Password and TOTP.
        
        Uses pyotp to generate a fresh 6-digit TOTP code on every run, so the session
        never permanently expires.
        """
        try:
            import pyotp
            totp = pyotp.TOTP(totp_secret.strip())
            totp_code = totp.now()

            login_url = "https://groww.in/v1/api/auth/v1/login"
            payload = {
                "email": email.strip(),
                "password": password.strip(),
                "totp": totp_code,
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            resp = requests.post(login_url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token") or data.get("jwt") or data.get("accessToken")
                if token:
                    logger.info("Successfully renewed Groww session token via automated TOTP.")
                    return token
        except Exception as exc:
            logger.warning("Automated Groww TOTP login failed: %s", exc)
        return None

    def _get_headers(self) -> Dict[str, str]:
        token = self.auth_token or ""
        if not token.lower().startswith("bearer ") and token:
            token = f"Bearer {token}"
        return {
            "Authorization": token,
            "x-app-id": "GrowwWeb",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }

    def export_offline_watchlists(
        self,
        bullish_items: List[Dict[str, str]],
        bearish_items: List[Dict[str, str]],
        output_dir: Path,
    ) -> List[str]:
        """Generate ready-to-use symbol lists and CSVs for Groww web/mobile."""
        output_dir.mkdir(parents=True, exist_ok=True)
        created_files = []

        # 1. Comma-separated and line-by-line Bullish symbols
        bull_symbols = [item["symbol"] for item in bullish_items]
        bull_path = output_dir / "groww_bullish_watchlist.txt"
        with open(bull_path, "w", encoding="utf-8") as f:
            f.write("# NewsEdge Top 10 Bullish Watchlist\n")
            f.write("# Comma-separated (paste into Groww search):\n")
            f.write(", ".join(bull_symbols) + "\n\n")
            f.write("# Individual Tickers:\n")
            for item in bullish_items:
                f.write(f"{item['symbol']} - {item['company_name']} (Score: {item['score']})\n")
        created_files.append(str(bull_path))

        # 2. Comma-separated and line-by-line Bearish symbols
        bear_symbols = [item["symbol"] for item in bearish_items]
        bear_path = output_dir / "groww_bearish_watchlist.txt"
        with open(bear_path, "w", encoding="utf-8") as f:
            f.write("# NewsEdge Top 10 Bearish Watchlist\n")
            f.write("# Comma-separated (paste into Groww search):\n")
            f.write(", ".join(bear_symbols) + "\n\n")
            f.write("# Individual Tickers:\n")
            for item in bearish_items:
                f.write(f"{item['symbol']} - {item['company_name']} (Score: {item['score']})\n")
        created_files.append(str(bear_path))

        # 3. Comprehensive CSV import file
        csv_path = output_dir / "groww_watchlist_import.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Watchlist", "NSE Symbol", "Company Name", "Direction", "Conviction Score", "Headline"])
            for it in bullish_items:
                writer.writerow(["NewsEdge Bullish", it["symbol"], it["company_name"], "Bullish", it["score"], it.get("headline", "")])
            for it in bearish_items:
                writer.writerow(["NewsEdge Bearish", it["symbol"], it["company_name"], "Bearish", it["score"], it.get("headline", "")])
        created_files.append(str(csv_path))

        logger.info("Saved Groww watchlist export files to: %s", output_dir)
        return created_files

    def sync_to_groww_account(
        self,
        bullish_symbols: List[str],
        bearish_symbols: List[str],
    ) -> GrowwSyncResult:
        """Call Groww API to clear and populate 'NewsEdge Bullish' and 'NewsEdge Bearish' watchlists."""
        if not self.auth_token:
            msg = (
                "Groww auth token not set. To enable direct cloud synchronization to your Groww account, "
                "set GROWW_AUTH_TOKEN in your .env file."
            )
            logger.info(msg)
            return GrowwSyncResult(
                success=False,
                bullish_synced=0,
                bearish_synced=0,
                error_message=msg,
            )

        headers = self._get_headers()

        try:
            # 1. Fetch user's existing watchlists
            resp = requests.get(f"{self.GROWW_BASE_URL}/user_watchlists", headers=headers, timeout=10)
            if resp.status_code in (401, 403) and self.email and self.password and self.totp_secret:
                logger.info("Groww token expired. Attempting automatic renewal via TOTP...")
                fresh_token = self.login_with_totp(self.email, self.password, self.totp_secret)
                if fresh_token:
                    self.auth_token = fresh_token
                    headers = self._get_headers()
                    resp = requests.get(f"{self.GROWW_BASE_URL}/user_watchlists", headers=headers, timeout=10)

            if resp.status_code in (401, 403):
                return GrowwSyncResult(
                    success=False,
                    bullish_synced=0,
                    bearish_synced=0,
                    error_message="Groww authentication failed. Token expired or invalid.",
                )

            watchlists_data = resp.json().get("watchlists", [])
            bull_wl_id = None
            bear_wl_id = None

            for wl in watchlists_data:
                name = wl.get("watchlistName", "")
                if name.lower() == "newsedge bullish":
                    bull_wl_id = wl.get("watchlistId")
                elif name.lower() == "newsedge bearish":
                    bear_wl_id = wl.get("watchlistId")

            # 2. Create watchlists if they don't exist
            if not bull_wl_id:
                create_resp = requests.post(
                    f"{self.GROWW_BASE_URL}/create",
                    headers=headers,
                    json={"watchlistName": "NewsEdge Bullish"},
                    timeout=10,
                )
                if create_resp.status_code == 200:
                    bull_wl_id = create_resp.json().get("watchlistId")

            if not bear_wl_id:
                create_resp = requests.post(
                    f"{self.GROWW_BASE_URL}/create",
                    headers=headers,
                    json={"watchlistName": "NewsEdge Bearish"},
                    timeout=10,
                )
                if create_resp.status_code == 200:
                    bear_wl_id = create_resp.json().get("watchlistId")

            # 3. Update stocks (clearing old stocks and replacing with fresh run)
            b_count = 0
            if bull_wl_id:
                up_resp = requests.post(
                    f"{self.GROWW_BASE_URL}/update_stocks",
                    headers=headers,
                    json={
                        "watchlistId": bull_wl_id,
                        "searchIds": [f"{s}-EQ" for s in bullish_symbols],
                    },
                    timeout=10,
                )
                if up_resp.status_code == 200:
                    b_count = len(bullish_symbols)

            bear_count = 0
            if bear_wl_id:
                up_resp = requests.post(
                    f"{self.GROWW_BASE_URL}/update_stocks",
                    headers=headers,
                    json={
                        "watchlistId": bear_wl_id,
                        "searchIds": [f"{s}-EQ" for s in bearish_symbols],
                    },
                    timeout=10,
                )
                if up_resp.status_code == 200:
                    bear_count = len(bearish_symbols)

            logger.info("Successfully synced Groww watchlists: %d Bullish, %d Bearish", b_count, bear_count)
            return GrowwSyncResult(
                success=True,
                bullish_synced=b_count,
                bearish_synced=bear_count,
            )

        except Exception as exc:
            logger.error("Failed to sync Groww watchlists: %s", exc)
            return GrowwSyncResult(
                success=False,
                bullish_synced=0,
                bearish_synced=0,
                error_message=str(exc),
            )

    def process_sync(
        self,
        bullish_items: List[Dict[str, str]],
        bearish_items: List[Dict[str, str]],
        reports_dir: Path,
    ) -> GrowwSyncResult:
        """High-level runner: generates export files and triggers cloud sync if configured."""
        export_files = self.export_offline_watchlists(bullish_items, bearish_items, reports_dir)
        bull_syms = [it["symbol"] for it in bullish_items]
        bear_syms = [it["symbol"] for it in bearish_items]

        result = self.sync_to_groww_account(bull_syms, bear_syms)
        result.export_files = export_files
        return result
