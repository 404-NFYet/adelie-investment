"""Lua 기반 원자적 슬라이딩 윈도우 레이트리밋 미들웨어."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis_keys import key_rate_limit
from app.services.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)

# Sliding window Lua script (원자적 처리)
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, math.ceil(window / 1000))
    return {1, limit - count - 1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset = oldest[2] and (tonumber(oldest[2]) + window) or (now + window)
    return {0, 0, reset}
end
"""

RATE_LIMIT = 100       # 요청/분
WINDOW_MS = 60_000     # 1분 (ms)

# rate limit 제외 경로
_EXEMPT_PATHS = {"/metrics", "/docs", "/redoc", "/openapi.json", "/"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 기반 슬라이딩 윈도우 레이트리밋 (100 req/min)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        try:
            cache = await get_redis_cache()
            if cache.client:
                now_ms = int(time.time() * 1000)
                k = key_rate_limit("ip", client_ip)
                result = await cache.client.eval(
                    SLIDING_WINDOW_LUA, 1, k,
                    now_ms, WINDOW_MS, RATE_LIMIT
                )
                allowed, remaining, reset_ms = result
                if not allowed:
                    retry_after = max(1, int((reset_ms - now_ms) / 1000))
                    return Response(
                        content='{"detail":"Too Many Requests"}',
                        status_code=429,
                        headers={
                            "Content-Type": "application/json",
                            "X-RateLimit-Limit": str(RATE_LIMIT),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(reset_ms / 1000)),
                            "Retry-After": str(retry_after),
                        },
                    )
        except Exception as e:
            # Redis 장애 시 레이트리밋 미적용 (graceful)
            logger.warning(f"RateLimit Redis error (fallback=allow): {e}")

        return await call_next(request)
