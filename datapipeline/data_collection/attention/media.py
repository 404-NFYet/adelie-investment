"""Google News RSS 기반 미디어 커버리지 조회."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict
from urllib.parse import quote

import feedparser
import requests
from tqdm import tqdm

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20


@dataclass
class NewsSearchConfig:
    market: str = "KR"
    recency_days: int = 7

    @property
    def hl(self) -> str:
        return "ko" if self.market == "KR" else "en"

    @property
    def gl(self) -> str:
        return "KR" if self.market == "KR" else "US"

    @property
    def ceid(self) -> str:
        return "KR:ko" if self.market == "KR" else "US:en"


def build_google_news_query(name: str, symbol: str, market: str) -> str:
    """Google News RSS 검색 쿼리 생성."""
    name = (name or "").strip()
    symbol = (symbol or "").strip()

    if market == "KR":
        parts = [name]
        if symbol:
            parts.append(symbol)
        parts.append("주식")
        return " ".join([p for p in parts if p])

    parts = [name]
    if symbol:
        parts.append(symbol)
    parts.append("stock")
    return " ".join([p for p in parts if p])


def google_news_count(query: str, config: NewsSearchConfig) -> int:
    """Google News RSS에서 기사 수 조회."""
    q = quote(query)
    url = (
        "https://news.google.com/rss/search"
        f"?q={q}+when:{config.recency_days}d"
        f"&hl={config.hl}&gl={config.gl}&ceid={config.ceid}"
    )

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    return len(feed.entries or [])


def fetch_google_news_coverage(
    stocks: list[dict],
    market: str = "KR",
    recency_days: int = 7,
    max_workers: int = 1,
    show_progress: bool = True,
) -> Dict[str, int]:
    """종목별 Google News 기사 수 조회."""
    config = NewsSearchConfig(market=market, recency_days=recency_days)
    cache: Dict[str, int] = {}
    result: Dict[str, int] = {}
    lock = threading.Lock()

    def _work(item: dict) -> tuple[str, int]:
        symbol = (item.get("symbol") or item.get("ticker") or "").strip()
        name = (item.get("name") or "").strip()
        query = build_google_news_query(name, symbol, market)
        if not query:
            return symbol, 0

        with lock:
            if query in cache:
                return symbol, cache[query]

        try:
            count = google_news_count(query, config)
        except Exception:
            count = 0

        with lock:
            cache[query] = count
        return symbol, count

    if max_workers and max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_work, s) for s in stocks]
            iterator = as_completed(futures)
            if show_progress:
                iterator = tqdm(iterator, total=len(futures), desc="Google News", unit="query")
            for fut in iterator:
                try:
                    symbol, count = fut.result()
                except Exception:
                    continue
                if symbol:
                    result[symbol] = count
    else:
        iterator = stocks
        if show_progress:
            iterator = tqdm(iterator, total=len(stocks), desc="Google News", unit="query")
        for s in iterator:
            symbol, count = _work(s)
            if symbol:
                result[symbol] = count

    return result
