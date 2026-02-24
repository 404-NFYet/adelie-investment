"""Canvas 사전 연산 — datapipeline 완료 후 Redis 캐시.

파이프라인이 당일 브리핑을 생성한 뒤, Canvas 초기 분석을
사전 연산하여 Redis에 캐싱합니다. 사용자 진입 시 0ms 지연.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger("narrative_api.canvas.precompute")

KST = timezone(timedelta(hours=9))

_CACHE_PREFIX = "canvas:precompute"
_CACHE_TTL = 86400  # 24시간


def _cache_key(mode: str, date: str) -> str:
    return f"{_CACHE_PREFIX}:{mode}:{date}"


def _kst_today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


async def get_precomputed_canvas(
    *,
    mode: str = "home",
    date: Optional[str] = None,
) -> dict[str, Any]:
    """사전 연산된 Canvas 데이터 조회.

    Args:
        mode: 분석 모드 (home/stock/education)
        date: 날짜 (YYYY-MM-DD), 기본값=오늘(KST)

    Returns:
        CanvasPrecomputedResponse 호환 dict
    """
    target_date = date or _kst_today()
    key = _cache_key(mode, target_date)

    try:
        from app.services import get_redis_cache
        redis = await get_redis_cache()
        if redis is None:
            return _empty_response(target_date, mode)

        cached = await redis.get(key)
        if not cached:
            return _empty_response(target_date, mode)

        data = json.loads(cached)
        return {
            "cached": True,
            "date": target_date,
            "mode": mode,
            "analysis_md": data.get("analysis_md"),
            "ctas": data.get("ctas", []),
            "chart_json": data.get("chart_json"),
            "sources": data.get("sources", []),
            "generated_at": data.get("generated_at"),
        }

    except Exception as e:
        logger.warning("Precomputed cache read failed: %s", e)
        return _empty_response(target_date, mode)


async def store_precomputed_canvas(
    *,
    mode: str,
    date: Optional[str] = None,
    analysis_md: str,
    ctas: list[dict[str, Any]],
    chart_json: Optional[dict[str, Any]] = None,
    sources: list[dict[str, Any]] = None,
) -> bool:
    """사전 연산된 Canvas 데이터 Redis 저장.

    Args:
        mode: 분석 모드
        date: 날짜, 기본값=오늘(KST)
        analysis_md: 마크다운 분석 텍스트
        ctas: CTA 목록
        chart_json: Plotly 차트 JSON (선택)
        sources: 소스 목록

    Returns:
        저장 성공 여부
    """
    target_date = date or _kst_today()
    key = _cache_key(mode, target_date)

    payload = {
        "analysis_md": analysis_md,
        "ctas": ctas,
        "chart_json": chart_json,
        "sources": sources or [],
        "generated_at": datetime.now(KST).isoformat(),
    }

    try:
        from app.services import get_redis_cache
        redis = await get_redis_cache()
        if redis is None:
            logger.warning("Redis not available for precompute storage")
            return False

        await redis.set(key, json.dumps(payload, ensure_ascii=False), ex=_CACHE_TTL)
        logger.info("Precomputed canvas stored: %s", key)
        return True

    except Exception as e:
        logger.error("Precomputed cache write failed: %s", e)
        return False


def _empty_response(date: str, mode: str) -> dict[str, Any]:
    return {
        "cached": False,
        "date": date,
        "mode": mode,
        "analysis_md": None,
        "ctas": [],
        "chart_json": None,
        "sources": [],
        "generated_at": None,
    }
