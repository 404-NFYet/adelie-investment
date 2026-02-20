from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis

from .config import settings


@dataclass
class _CacheEntry:
    value: dict[str, Any]
    expires_at: float


class CacheBackend:
    def __init__(self) -> None:
        self._memory: dict[str, _CacheEntry] = {}
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        if not settings.redis_url:
            return
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await self._redis.ping()
        except Exception:
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def get_json(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        entry = self._memory.get(key)
        if entry and entry.expires_at > now:
            return entry.value
        if entry:
            self._memory.pop(key, None)

        if self._redis is None:
            return None

        raw = await self._redis.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, payload: dict[str, Any], ttl: int | None = None) -> None:
        ttl_value = ttl or settings.cache_ttl_seconds
        self._memory[key] = _CacheEntry(value=payload, expires_at=time.time() + ttl_value)

        if self._redis is not None:
            await self._redis.setex(key, ttl_value, json.dumps(payload, ensure_ascii=False, default=str))


cache_backend = CacheBackend()
