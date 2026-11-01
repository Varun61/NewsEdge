"""Generic RSS collector using feedparser."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import dateutil.parser
import feedparser
import requests

from app.collectors.base_collector import BaseCollector, CollectedArticle

logger = logging.getLogger("newsedge.collectors.rss")


class RSSCollector(BaseCollector):
    """Collector for RSS and Atom news feeds."""

    def __init__(
        self,
        source_name: str,
        feed_url: str,
        enabled: bool = True,
        credibility_score: float = 0.5,
        extract_full_text: bool = False,
        timeout_seconds: int = 15,
    ):
        super().__init__(
            source_name=source_name,
            source_url=feed_url,
            enabled=enabled,
            credibility_score=credibility_score,
        )
        self.feed_url = feed_url
        self.extract_full_text = extract_full_text
        self.timeout_seconds = timeout_seconds

    def _parse_published_date(self, entry: dict) -> Optional[datetime]:
        """Parse publication date from RSS entry and return as UTC datetime."""
        for field in ("published", "pubDate", "updated", "created"):
            val = entry.get(field)
            if val:
                try:
                    dt = dateutil.parser.parse(val)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    return dt
                except Exception as exc:
                    logger.debug("Date parsing failed for %s: %s", val, exc)

        # Fallback to parsed struct_time if present
        for field in ("published_parsed", "updated_parsed"):
            st = entry.get(field)
            if st:
                try:
                    dt = datetime(*st[:6], tzinfo=timezone.utc)
                    return dt
                except Exception:
                    pass

        return None

    def collect(self, since: datetime, until: datetime) -> list[CollectedArticle]:
        """Fetch and filter RSS entries published within the time window."""
        if not self.enabled:
            logger.info("Collector '%s' is disabled. Skipping.", self.source_name)
            return []

        logger.info("Collecting RSS feed from '%s' (%s)", self.source_name, self.feed_url)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = requests.get(self.feed_url, headers=headers, timeout=self.timeout_seconds)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            logger.error("Failed to fetch RSS from '%s': %s", self.source_name, exc)
            return []

        articles: list[CollectedArticle] = []
        for entry in feed.entries:
            headline = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not headline or not link:
                continue

            pub_date = self._parse_published_date(entry)
            if pub_date:
                # Filter strictly by window
                if pub_date < since or pub_date > until:
                    continue

            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            extracted = summary

            if self.extract_full_text and link:
                try:
                    import trafilatura
                    downloaded = trafilatura.fetch_url(link)
                    if downloaded:
                        text = trafilatura.extract(downloaded)
                        if text:
                            extracted = text
                except Exception as exc:
                    logger.debug("Trafilatura extraction failed for %s: %s", link, exc)

            articles.append(
                CollectedArticle(
                    headline=headline,
                    article_url=link,
                    source_name=self.source_name,
                    published_at=pub_date,
                    raw_content=summary,
                    extracted_text=extracted,
                    credibility_score=self.credibility_score,
                )
            )

        logger.info("Collector '%s' retrieved %d matching articles", self.source_name, len(articles))
        return articles
