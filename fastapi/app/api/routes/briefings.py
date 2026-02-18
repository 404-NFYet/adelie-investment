"""브리핑 API 라우트 - /api/v1/briefings/*"""
import json as json_module

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import date, timedelta

from app.core.database import get_db
from app.models.narrative import DailyNarrative, NarrativeScenario
from app.services.redis_cache import get_redis_cache

router = APIRouter(prefix="/briefings", tags=["briefings"])


@router.get("/latest")
async def get_latest_briefing(db: AsyncSession = Depends(get_db)):
    """최신 브리핑 조회"""
    # Redis 캐시 체크
    cache_key = "api:briefings:latest"
    try:
        cache = await get_redis_cache()
        cached = await cache.get(cache_key)
        if cached:
            return json_module.loads(cached)
    except Exception:
        pass

    result = await db.execute(
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .order_by(desc(DailyNarrative.date))
        .limit(1)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(404, "No briefings available")

    data = _serialize_narrative(narrative)

    # Redis 캐시 저장 (5분)
    try:
        await cache.set(cache_key, json_module.dumps(data, ensure_ascii=False, default=str), 300)
    except Exception:
        pass

    return data


@router.get("/list")
async def list_briefings(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """브리핑 목록 조회 (페이지네이션)"""
    offset = (page - 1) * size
    result = await db.execute(
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .order_by(desc(DailyNarrative.date))
        .offset(offset)
        .limit(size)
    )
    narratives = result.scalars().all()
    return [_serialize_narrative(n) for n in narratives]


@router.get("/{briefing_id}")
async def get_briefing(briefing_id: str, db: AsyncSession = Depends(get_db)):
    """특정 브리핑 조회"""
    result = await db.execute(
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .where(DailyNarrative.id == briefing_id)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(404, "Briefing not found")
    return _serialize_narrative(narrative)


def _serialize_narrative(narrative):
    """내러티브 직렬화 헬퍼"""
    return {
        "id": str(narrative.id),
        "date": narrative.date.isoformat(),
        "main_keywords": narrative.main_keywords or [],
        "glossary": narrative.glossary or {},
        "scenarios": [
            {
                "id": str(s.id),
                "title": s.title,
                "summary": s.summary,
                "sources": s.sources or [],
                "related_companies": s.related_companies or [],
                "mirroring_data": s.mirroring_data or {},
                "narrative_sections": s.narrative_sections or {},
                "sort_order": s.sort_order,
            }
            for s in sorted(narrative.scenarios, key=lambda x: x.sort_order)
        ],
        "created_at": narrative.created_at.isoformat() if narrative.created_at else None,
    }
