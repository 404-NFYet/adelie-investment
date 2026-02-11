"""Backend API services."""

from .redis_cache import (
    RedisCacheService,
    get_redis_cache,
    close_redis_cache,
    TTL_TERM_EXPLANATION,
    TTL_GLOSSARY,
    TTL_USER_SETTINGS,
)

__all__ = [
    "RedisCacheService",
    "get_redis_cache",
    "close_redis_cache",
    "TTL_TERM_EXPLANATION",
    "TTL_GLOSSARY",
    "TTL_USER_SETTINGS",
]
