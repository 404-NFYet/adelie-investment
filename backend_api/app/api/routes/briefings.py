"""Narrative Briefings API - 내러티브 브리핑 조회."""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.narrative import DailyNarrative, NarrativeScenario

router = APIRouter(prefix="/briefings", tags=["Briefings"])


@router.get("/latest")
async def get_latest_briefing(db: AsyncSession = Depends(get_db)):
    """최신 내러티브 브리핑 조회."""
    stmt = (
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .order_by(desc(DailyNarrative.date))
        .limit(1)
    )
    result = await db.execute(stmt)
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        raise HTTPException(status_code=404, detail="No briefing found")
    
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
                "sources": s.sources,
                "related_companies": s.related_companies,
                "mirroring_data": s.mirroring_data,
                "narrative_sections": s.narrative_sections,
                "sort_order": s.sort_order,
            }
            for s in sorted(narrative.scenarios, key=lambda x: x.sort_order)
        ],
    }


@router.get("/list")
async def list_briefings(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """브리핑 목록 조회."""
    stmt = (
        select(DailyNarrative)
        .order_by(desc(DailyNarrative.date))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    narratives = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(n.id),
                "date": n.date.isoformat(),
                "main_keywords": n.main_keywords or [],
            }
            for n in narratives
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/{briefing_id}")
async def get_briefing_by_id(
    briefing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """ID로 브리핑 조회."""
    stmt = (
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .where(DailyNarrative.id == briefing_id)
    )
    result = await db.execute(stmt)
    narrative = result.scalar_one_or_none()
    
    if not narrative:
        raise HTTPException(status_code=404, detail="Briefing not found")
    
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
                "sources": s.sources,
                "related_companies": s.related_companies,
                "mirroring_data": s.mirroring_data,
                "narrative_sections": s.narrative_sections,
                "sort_order": s.sort_order,
            }
            for s in sorted(narrative.scenarios, key=lambda x: x.sort_order)
        ],
    }

