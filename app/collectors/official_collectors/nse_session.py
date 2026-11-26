"""Primed HTTP session for NSE India endpoints.

NSE's public JSON APIs reject requests that do not carry the cookies handed out
by the website on a normal browser visit. Without priming, every call to
``/api/corporate-announcements`` returns 401/403 and the collector silently
yields nothing. This helper performs the same warm-up a browser does: it hits
the home page (and the relevant landing page) first to collect cookies, then
reuses that session for the API call.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger("newsedge.collectors.nse_session")

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

_HOME_URL = "https://www.nseindia.com"

# A single warmed session is shared across collectors within a run. NSE cookies
# are short-lived, so we re-prime after _COOKIE_TTL seconds.
_COOKIE_TTL = 600.0
_lock = threading.Lock()
_session: Optional[requests.Session] = None
_primed_at: float = 0.0


def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_BROWSER_HEADERS)
    return s


def _prime(session: requests.Session, warmup_paths: tuple[str, ...], timeout: int) -> bool:
    """Visit NSE pages to collect cookies. Returns True if any cookies were set."""
    try:
        session.get(_HOME_URL, timeout=timeout)
        time.sleep(0.5)
        # A lightweight JSON API warms the bot-protection (bm_sv / nseappid) cookies
        # that the heavier endpoints require.
        try:
            session.get(
                f"{_HOME_URL}/api/marketStatus",
                timeout=timeout,
                headers={"Accept": "application/json, text/plain, */*", "Referer": _HOME_URL},
            )
            time.sleep(0.3)
        except requests.RequestException:
            pass
        for path in warmup_paths:
            try:
                session.get(f"{_HOME_URL}{path}", timeout=timeout)
                time.sleep(0.3)
            except requests.RequestException as exc:
                logger.debug("NSE warm-up path %s failed: %s", path, exc)
        return len(session.cookies) > 0
    except requests.RequestException as exc:
        logger.warning("NSE session priming failed: %s", exc)
        return False


def get_nse_session(
    warmup_paths: tuple[str, ...] = ("/companies-listing/corporate-filings-announcements",),
    timeout: int = 15,
    force_refresh: bool = False,
) -> requests.Session:
    """Return a cookie-primed :class:`requests.Session` for NSE API calls."""
    global _session, _primed_at
    with _lock:
        now = time.time()
        stale = (now - _primed_at) > _COOKIE_TTL
        if _session is None or stale or force_refresh:
            _session = _build_session()
            if _prime(_session, warmup_paths, timeout):
                _primed_at = now
            else:
                # Keep the session object; caller may still try. Reset timer so a
                # later call re-attempts priming.
                _primed_at = 0.0
        return _session


def fetch_nse_json(
    url: str,
    warmup_paths: tuple[str, ...] = ("/companies-listing/corporate-filings-announcements",),
    timeout: int = 15,
    retries: int = 2,
):
    """GET a NSE JSON endpoint with automatic priming and one re-prime retry.

    Returns the parsed JSON, or ``None`` on failure.
    """
    # NSE's JSON APIs reject requests that lack a matching Referer and the
    # XHR marker; without them the body comes back empty (-> "Expecting value").
    referer = f"{_HOME_URL}{warmup_paths[0]}" if warmup_paths else _HOME_URL
    api_headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": referer,
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }

    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        session = get_nse_session(warmup_paths, timeout, force_refresh=(attempt > 0))
        try:
            resp = session.get(url, timeout=timeout, headers=api_headers)
            body = (resp.text or "").strip()
            if resp.status_code == 200 and body and body[0] in "{[":
                try:
                    return resp.json()
                except ValueError as exc:
                    last_exc = exc
                    logger.debug("NSE returned non-JSON for %s (attempt %d)", url, attempt + 1)
            elif resp.status_code == 200:
                # 200 with an empty/HTML body = bot-protection challenge; re-prime.
                last_exc = ValueError("empty or non-JSON body (bot challenge)")
                logger.debug("NSE %s -> 200 but empty/HTML body (attempt %d)", url, attempt + 1)
            else:
                logger.debug("NSE %s -> HTTP %d (attempt %d)", url, resp.status_code, attempt + 1)
        except requests.RequestException as exc:
            last_exc = exc
            logger.debug("NSE request error for %s: %s (attempt %d)", url, exc, attempt + 1)
        time.sleep(1.0)
    if last_exc:
        logger.warning("NSE JSON fetch failed for %s: %s", url, last_exc)
    return None
