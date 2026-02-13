"""
# [2026-02-06] Redis 캐싱 서비스
AI Tutor 단어 설명, Glossary 조회를 위한 캐싱 레이어.

캐시 키 패턴:
- term:{term_name} - AI Tutor 용어 설명 (TTL: 24시간)
- glossary:{term_id} - 용어집 조회 (TTL: 24시간)
- user_settings:{user_id} - 사용자 설정 (TTL: 세션)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from ..core.config import settings

logger = logging.getLogger(__name__)

# TTL 설정 (초 단위)
TTL_TERM_EXPLANATION = 60 * 60 * 24  # 24시간
TTL_GLOSSARY = 60 * 60 * 24  # 24시간
TTL_USER_SETTINGS = 60 * 60 * 2  # 2시간 (세션)
TTL_CHAT_MESSAGES = 60 * 60  # 1시간


class RedisCacheService:
    """Redis 캐싱 서비스."""

    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Redis 연결 초기화."""
        if self._client is not None:
            return
        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=50,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info(f"Redis connected: {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._client = None

    async def disconnect(self) -> None:
        """Redis 연결 해제."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    @property
    def client(self) -> Optional[redis.Redis]:
        return self._client

    def _is_available(self) -> bool:
        return self._client is not None

    # ==================== Term Explanation (AI Tutor) ====================

    async def get_term_explanation(self, term: str, difficulty: str = "beginner") -> Optional[str]:
        """AI Tutor 용어 설명 캐시 조회."""
        if not self._is_available():
            return None
        key = f"term:{difficulty}:{term.lower()}"
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis get_term_explanation error: {e}")
            return None

    async def set_term_explanation(
        self, term: str, explanation: str, difficulty: str = "beginner"
    ) -> bool:
        """AI Tutor 용어 설명 캐시 저장."""
        if not self._is_available():
            return False
        key = f"term:{difficulty}:{term.lower()}"
        try:
            await self._client.setex(key, TTL_TERM_EXPLANATION, explanation)
            return True
        except Exception as e:
            logger.warning(f"Redis set_term_explanation error: {e}")
            return False

    # ==================== Glossary ====================

    async def get_glossary(self, term_id: int) -> Optional[dict]:
        """용어집 캐시 조회."""
        if not self._is_available():
            return None
        key = f"glossary:{term_id}"
        try:
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Redis get_glossary error: {e}")
            return None

    async def set_glossary(self, term_id: int, data: dict) -> bool:
        """용어집 캐시 저장."""
        if not self._is_available():
            return False
        key = f"glossary:{term_id}"
        try:
            await self._client.setex(key, TTL_GLOSSARY, json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"Redis set_glossary error: {e}")
            return False

    async def get_glossary_by_term(self, term_name: str) -> Optional[dict]:
        """용어명으로 용어집 캐시 조회."""
        if not self._is_available():
            return None
        key = f"glossary:name:{term_name.lower()}"
        try:
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Redis get_glossary_by_term error: {e}")
            return None

    async def set_glossary_by_term(self, term_name: str, data: dict) -> bool:
        """용어명으로 용어집 캐시 저장."""
        if not self._is_available():
            return False
        key = f"glossary:name:{term_name.lower()}"
        try:
            await self._client.setex(key, TTL_GLOSSARY, json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"Redis set_glossary_by_term error: {e}")
            return False

    # ==================== User Settings ====================

    async def get_user_settings(self, user_id: int) -> Optional[dict]:
        """사용자 설정 캐시 조회."""
        if not self._is_available():
            return None
        key = f"user_settings:{user_id}"
        try:
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Redis get_user_settings error: {e}")
            return None

    async def set_user_settings(self, user_id: int, data: dict) -> bool:
        """사용자 설정 캐시 저장."""
        if not self._is_available():
            return False
        key = f"user_settings:{user_id}"
        try:
            await self._client.setex(key, TTL_USER_SETTINGS, json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"Redis set_user_settings error: {e}")
            return False

    async def invalidate_user_settings(self, user_id: int) -> bool:
        """사용자 설정 캐시 무효화."""
        if not self._is_available():
            return False
        key = f"user_settings:{user_id}"
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis invalidate_user_settings error: {e}")
            return False

    # ==================== Chat Session Messages ====================

    async def get_chat_messages(self, session_id: str) -> Optional[str]:
        """채팅 세션 메시지 캐시 조회."""
        if not self._is_available():
            return None
        key = f"chat_messages:{session_id}"
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis get_chat_messages error: {e}")
            return None

    async def set_chat_messages(self, session_id: str, data: str, ttl: int = TTL_CHAT_MESSAGES) -> bool:
        """채팅 세션 메시지 캐시 저장."""
        if not self._is_available():
            return False
        key = f"chat_messages:{session_id}"
        try:
            await self._client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.warning(f"Redis set_chat_messages error: {e}")
            return False

    async def invalidate_session_cache(self, session_id: str) -> bool:
        """채팅 세션 캐시 무효화."""
        if not self._is_available():
            return False
        key = f"chat_messages:{session_id}"
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis invalidate_session_cache error: {e}")
            return False

    # ==================== Pipeline Cache Invalidation ====================

    async def invalidate_pipeline_caches(self) -> int:
        """파이프라인 실행 후 API 응답 캐시 일괄 무효화.

        Returns: 삭제된 키 수
        """
        if not self._is_available():
            return 0

        deleted = 0
        try:
            # 키워드 캐시: api:keywords:today:* 패턴 삭제
            cursor = b"0"
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor, match="api:keywords:today:*", count=100
                )
                if keys:
                    deleted += await self._client.delete(*keys)
                if cursor == b"0" or cursor == 0:
                    break

            # 브리핑 캐시 삭제
            for key in ["api:briefings:latest"]:
                result = await self._client.delete(key)
                deleted += result

            logger.info(f"파이프라인 캐시 무효화 완료: {deleted}개 키 삭제")
        except Exception as e:
            logger.warning(f"Redis invalidate_pipeline_caches error: {e}")

        return deleted

    # ==================== Generic Cache ====================

    async def get(self, key: str) -> Optional[str]:
        """일반 캐시 조회."""
        if not self._is_available():
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """일반 캐시 저장."""
        if not self._is_available():
            return False
        try:
            await self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """캐시 삭제."""
        if not self._is_available():
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False


# 싱글톤 인스턴스
_redis_cache: Optional[RedisCacheService] = None


async def get_redis_cache() -> RedisCacheService:
    """Redis 캐시 서비스 인스턴스 반환."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCacheService()
        await _redis_cache.connect()
    return _redis_cache


async def close_redis_cache() -> None:
    """Redis 캐시 서비스 연결 해제."""
    global _redis_cache
    if _redis_cache is not None:
        await _redis_cache.disconnect()
        _redis_cache = None
