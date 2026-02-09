"""RSS Service for fetching news feeds."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx


LOGGER = logging.getLogger(__name__)


class RSSService:
    """Service for fetching and parsing RSS feeds."""

    def __init__(self, feeds: list[str], timeout_seconds: int = 15) -> None:
        self.feeds = feeds
        self.timeout_seconds = timeout_seconds

    def fetch_top_news(self, retry_48h: bool = False) -> str:
        """Fetch top news from RSS feeds within time window.
        
        Args:
            retry_48h: If True, use 48h window instead of 24h
            
        Returns:
            Concatenated news items as text
        """
        LOGGER.info("Fetching RSS feeds (window=%s)", "48h" if retry_48h else "24h")
        now = datetime.now(timezone.utc)
        window = timedelta(hours=48 if retry_48h else 24)
        cutoff = now - window
        news_items: list[str] = []

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            for url in self.feeds:
                try:
                    response = client.get(url)
                    if response.status_code >= 400:
                        LOGGER.warning("RSS fetch failed: %s (%s)", url, response.status_code)
                        continue
                    xml = response.text
                    self._extract_items(xml, cutoff, news_items)
                except Exception:
                    LOGGER.exception("Failed to fetch RSS from %s", url)

        if len(news_items) < 3 and not retry_48h:
            LOGGER.info("Too few items in 24h. Retrying with 48h window.")
            return self.fetch_top_news(retry_48h=True)

        return "\n\n".join(news_items[:30])

    def _extract_items(self, xml: str, cutoff: datetime, collector: list[str]) -> None:
        """Extract news items from RSS/Atom XML."""
        # RSS <item> pattern
        item_regex = re.compile(
            r"<item>[\s\S]*?<title>(.*?)</title>[\s\S]*?<description>(.*?)</description>"
            r"[\s\S]*?(?:<pubDate>(.*?)</pubDate>|<dc:date>(.*?)</dc:date>)?[\s\S]*?</item>",
            re.IGNORECASE,
        )
        # Atom <entry> pattern
        entry_regex = re.compile(
            r"<entry>[\s\S]*?<title>(.*?)</title>[\s\S]*?<(?:summary|content)>(.*?)</(?:summary|content)>"
            r"[\s\S]*?<updated>(.*?)</updated>[\s\S]*?</entry>",
            re.IGNORECASE,
        )

        count = 0
        for match in item_regex.finditer(xml):
            if count >= 8:
                break
            title = self._clean_html(match.group(1))
            desc = self._clean_html(match.group(2))
            date_value = match.group(3) or match.group(4)
            if not title:
                continue
            if not self._is_recent(date_value, cutoff):
                continue
            collector.append(f"[News] {title}: {desc[:150]}{'...' if len(desc) > 150 else ''}")
            count += 1

        if count > 0:
            return

        for match in entry_regex.finditer(xml):
            if count >= 8:
                break
            title = self._clean_html(match.group(1))
            summary = self._clean_html(match.group(2))
            updated = match.group(3)
            if not title:
                continue
            if not self._is_recent(updated, cutoff):
                continue
            collector.append(f"[News] {title}: {summary[:150]}{'...' if len(summary) > 150 else ''}")
            count += 1

    @staticmethod
    def _clean_html(raw: str) -> str:
        """Remove HTML tags and CDATA wrappers."""
        text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", raw or "")
        text = re.sub(r"<[^>]*>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _is_recent(date_text: str | None, cutoff: datetime) -> bool:
        """Check if date is within the window."""
        if not date_text:
            return True
        try:
            normalized = date_text.strip()
            if re.search(r"\d{4}-\d{2}-\d{2}", normalized):
                published = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            else:
                published = parsedate_to_datetime(normalized)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            return published >= cutoff
        except (TypeError, ValueError):
            return True
