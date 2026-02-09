"""RSS Feed Service - 뉴스 피드 수집."""
import asyncio
from typing import List, Dict
from datetime import datetime
import httpx
import feedparser

RSS_FEEDS = [
    "https://www.hankyung.com/feed/finance",
    "https://rss.joins.com/joins_money_list.xml",
]

class RSSService:
    def __init__(self):
        self.feeds = RSS_FEEDS

    async def fetch_feed(self, url: str) -> List[Dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url)
                feed = feedparser.parse(resp.text)
                return [{"title": e.title, "link": e.link, 
                         "published": e.get("published", "")} 
                        for e in feed.entries[:10]]
            except Exception:
                return []

    async def fetch_all_feeds(self) -> List[Dict]:
        tasks = [self.fetch_feed(url) for url in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        for r in results:
            if isinstance(r, list):
                items.extend(r)
        return items

_instance = None
def get_rss_service():
    global _instance
    if not _instance:
        _instance = RSSService()
    return _instance

