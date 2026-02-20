from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html import unescape

import feedparser
import requests

from app.core.config import settings
from app.core.models import HeadlineItem
from app.services.source_catalog import get_source_by_id, get_sources


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class FetchWarning:
    source_id: str
    message: str


def _parse_published(entry: feedparser.FeedParserDict) -> dt.datetime | None:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None
    try:
        parsed = parsedate_to_datetime(str(published))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _fetch_feed(feed_url: str) -> feedparser.FeedParserDict:
    response = requests.get(
        feed_url,
        headers={"User-Agent": USER_AGENT},
        timeout=settings.request_timeout_seconds,
    )
    response.raise_for_status()
    return feedparser.parse(response.content)


def _extract_image_url(entry: feedparser.FeedParserDict) -> str | None:
    media_content = entry.get("media_content") or []
    if media_content and isinstance(media_content, list):
        first = media_content[0]
        if isinstance(first, dict) and first.get("url"):
            return str(first.get("url")).strip()

    media_thumbnail = entry.get("media_thumbnail") or []
    if media_thumbnail and isinstance(media_thumbnail, list):
        first = media_thumbnail[0]
        if isinstance(first, dict) and first.get("url"):
            return str(first.get("url")).strip()

    links = entry.get("links") or []
    for link in links:
        if not isinstance(link, dict):
            continue
        if str(link.get("type", "")).startswith("image") and link.get("href"):
            return str(link.get("href")).strip()

    return None


def _looks_mojibake(text: str) -> bool:
    if "�" in text:
        return True
    if re.search(r"[ìëêã]{3,}", text):
        return True
    return False


def _title_quality_score(title: str) -> int:
    score = 0
    if 16 <= len(title) <= 120:
        score += 2
    if re.search(r"[가-힣A-Za-z]", title):
        score += 2
    if re.search(r"\d", title):
        score += 1
    if title.count(" ") >= 2:
        score += 1
    return score


def _is_title_quality_ok(title: str) -> bool:
    cleaned = " ".join(unescape(str(title or "")).split())
    if not cleaned:
        return False

    if _looks_mojibake(cleaned):
        return False

    title_len = len(cleaned)
    if title_len < 12 or title_len > 180:
        return False

    symbol_ratio = len(re.findall(r"[^0-9A-Za-z가-힣\s\-\.,:'\"()\[\]·]", cleaned)) / max(title_len, 1)
    if symbol_ratio > 0.18:
        return False

    if re.search(r"(.)\1{6,}", cleaned):
        return False

    return True


def fetch_headlines(market: str, source_id: str | None = None, limit: int = 20) -> tuple[list[HeadlineItem], list[FetchWarning]]:
    warnings: list[FetchWarning] = []

    if source_id:
        source = get_source_by_id(market, source_id)
        sources = [source] if source else []
    else:
        sources = get_sources(market)

    source_rank = {src.id: rank for rank, src in enumerate(s for s in sources if s is not None)}

    headlines: list[HeadlineItem] = []

    for source in sources:
        if source is None:
            warnings.append(FetchWarning(source_id=source_id or "unknown", message="source not found"))
            continue

        try:
            parsed = _fetch_feed(str(source.feed_url))
        except Exception as exc:
            warnings.append(FetchWarning(source_id=source.id, message=str(exc)))
            continue

        for entry in parsed.entries:
            link = str(entry.get("link", "")).strip()
            title = " ".join(unescape(str(entry.get("title", ""))).split())
            if not link or not title:
                continue
            if not _is_title_quality_ok(title):
                continue

            headlines.append(
                HeadlineItem(
                    title=title,
                    url=link,
                    source_id=source.id,
                    source=source.name,
                    published_at=_parse_published(entry),
                    image_url=_extract_image_url(entry),
                )
            )

    deduped: list[HeadlineItem] = []
    seen: set[str] = set()
    for item in headlines:
        normalized_title = re.sub(r"\s+", " ", item.title.lower()).strip()
        key = f"{normalized_title}|{item.source_id}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(
        key=lambda x: (
            x.published_at or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
            _title_quality_score(x.title),
            -source_rank.get(x.source_id, 999),
        ),
        reverse=True,
    )

    return deduped[: max(1, min(limit, 100))], warnings
