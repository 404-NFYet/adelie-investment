"""캐시 헬퍼 — cache-aside + stampede 방지."""

import json
import logging
import random
from typing import Any, Callable, Optional

from app.services.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)


async def get_or_set(
    key: str,
    ttl: int,
    loader_fn: Callable,
    negative_ttl: int = 30,
    jitter: float = 0.1,
) -> Any:
    """cache-aside with TTL jitter.

    loader_fn이 None을 반환하면 negative_ttl 동안 '__null__' 캐시.
    Redis 장애 시 loader_fn을 직접 호출하여 graceful fallback.
    """
    cache = await get_redis_cache()

    # 1. 캐시 조회
    try:
        raw = await cache.get(key)
        if raw is not None:
            return None if raw == "__null__" else json.loads(raw)
    except Exception as e:
        logger.warning(f"cache get error [{key}]: {e}")

    # 2. 캐시 미스 → DB/외부 호출
    try:
        result = await loader_fn()
    except Exception as e:
        logger.warning(f"cache loader_fn error [{key}]: {e}")
        return None

    # 3. 캐시 저장 (jitter 적용으로 thundering herd 방지)
    actual_ttl = int(ttl * (1 + random.uniform(-jitter, jitter)))
    try:
        if result is None:
            await cache.set(key, "__null__", negative_ttl)
        else:
            await cache.set(key, json.dumps(result, ensure_ascii=False, default=str), actual_ttl)
    except Exception as e:
        logger.warning(f"cache set error [{key}]: {e}")

    return result


async def invalidate(key: str) -> bool:
    """캐시 키 단건 무효화."""
    try:
        cache = await get_redis_cache()
        return await cache.delete(key)
    except Exception as e:
        logger.warning(f"cache invalidate error [{key}]: {e}")
        return False
