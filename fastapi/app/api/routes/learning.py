"""학습 진도 API 라우트 - /api/v1/learning/*"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func, case as sql_case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.learning import LearningProgress

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning", tags=["Learning Progress"])


# ── Schemas ──


class LearningProgressRequest(BaseModel):
    """학습 진도 기록/업데이트 요청."""
    user_id: int = Field(..., description="사용자 ID")
    content_type: str = Field(..., max_length=50, description="콘텐츠 유형 (case, glossary, briefing)")
    content_id: int = Field(..., description="콘텐츠 ID")
    status: Optional[str] = Field(None, max_length=20, description="학습 상태 (viewed, in_progress, completed)")
    progress_percent: Optional[int] = Field(None, ge=0, le=100, description="진행률 (%)")


class LearningProgressResponse(BaseModel):
    """학습 진도 응답."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    content_type: str
    content_id: int
    status: str
    progress_percent: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class ContentTypeStats(BaseModel):
    """콘텐츠 유형별 통계."""
    content_type: str
    total: int
    completed: int
    in_progress: int


class LearningStatsResponse(BaseModel):
    """학습 통계 응답."""
    total: int
    completed_count: int
    in_progress_count: int
    completion_rate: float
    breakdown: list[ContentTypeStats]


# ── API 엔드포인트 ──


@router.post("/progress")
async def upsert_learning_progress(
    body: LearningProgressRequest,
    db: AsyncSession = Depends(get_db),
):
    """학습 진도 기록/업데이트 (upsert).

    동일한 (user_id, content_type, content_id) 조합이 이미 존재하면 업데이트,
    없으면 새로 생성한다.
    """
    now = datetime.utcnow()
    status = body.status or "viewed"
    progress_percent = body.progress_percent if body.progress_percent is not None else 0

    # completed 상태이면 completed_at 설정
    completed_at = now if status == "completed" else None

    # PostgreSQL INSERT ... ON CONFLICT DO UPDATE (upsert)
    stmt = pg_insert(LearningProgress).values(
        user_id=body.user_id,
        content_type=body.content_type,
        content_id=body.content_id,
        status=status,
        progress_percent=progress_percent,
        started_at=now,
        completed_at=completed_at,
    )

    # CONFLICT 시 업데이트할 컬럼 지정
    update_values = {
        "status": stmt.excluded.status,
        "progress_percent": stmt.excluded.progress_percent,
    }
    if completed_at:
        update_values["completed_at"] = stmt.excluded.completed_at

    stmt = stmt.on_conflict_do_update(
        constraint="uq_learning_progress_user_content",
        set_=update_values,
    ).returning(LearningProgress)

    result = await db.execute(stmt)
    await db.commit()

    record = result.fetchone()
    if record is None:
        raise HTTPException(status_code=500, detail="학습 진도 저장에 실패했습니다")

    # returning() 결과를 dict로 변환
    row = record._mapping
    data = {
        "id": row["id"],
        "user_id": row["user_id"],
        "content_type": row["content_type"],
        "content_id": row["content_id"],
        "status": row["status"],
        "progress_percent": row["progress_percent"],
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }

    return {"status": "success", "data": data}


@router.get("/progress/{user_id}")
async def get_user_progress(
    user_id: int,
    content_type: Optional[str] = Query(None, description="콘텐츠 유형 필터 (case, glossary, briefing)"),
    status: Optional[str] = Query(None, description="상태 필터 (viewed, in_progress, completed)"),
    db: AsyncSession = Depends(get_db),
):
    """사용자 학습 현황 조회.

    선택적으로 content_type, status 필터를 적용할 수 있다.
    """
    stmt = select(LearningProgress).where(LearningProgress.user_id == user_id)

    if content_type:
        stmt = stmt.where(LearningProgress.content_type == content_type)
    if status:
        stmt = stmt.where(LearningProgress.status == status)

    stmt = stmt.order_by(LearningProgress.started_at.desc())

    result = await db.execute(stmt)
    records = result.scalars().all()

    data = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "content_type": r.content_type,
            "content_id": r.content_id,
            "status": r.status,
            "progress_percent": r.progress_percent,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in records
    ]

    return {"status": "success", "data": data, "total": len(data)}


@router.get("/progress/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """사용자 학습 완료율/통계 조회.

    전체 통계와 content_type별 breakdown을 반환한다.
    """
    # 전체 통계 쿼리
    total_stmt = select(
        func.count(LearningProgress.id).label("total"),
        func.count(
            sql_case(
                (LearningProgress.status == "completed", 1),
            )
        ).label("completed_count"),
        func.count(
            sql_case(
                (LearningProgress.status == "in_progress", 1),
            )
        ).label("in_progress_count"),
    ).where(LearningProgress.user_id == user_id)

    total_result = await db.execute(total_stmt)
    total_row = total_result.fetchone()

    total = total_row.total if total_row else 0
    completed_count = total_row.completed_count if total_row else 0
    in_progress_count = total_row.in_progress_count if total_row else 0
    completion_rate = round((completed_count / total * 100), 2) if total > 0 else 0.0

    # content_type별 breakdown 쿼리
    breakdown_stmt = select(
        LearningProgress.content_type,
        func.count(LearningProgress.id).label("total"),
        func.count(
            sql_case(
                (LearningProgress.status == "completed", 1),
            )
        ).label("completed"),
        func.count(
            sql_case(
                (LearningProgress.status == "in_progress", 1),
            )
        ).label("in_progress"),
    ).where(
        LearningProgress.user_id == user_id
    ).group_by(
        LearningProgress.content_type
    )

    breakdown_result = await db.execute(breakdown_stmt)
    breakdown_rows = breakdown_result.fetchall()

    breakdown = [
        {
            "content_type": row.content_type,
            "total": row.total,
            "completed": row.completed,
            "in_progress": row.in_progress,
        }
        for row in breakdown_rows
    ]

    return {
        "status": "success",
        "data": {
            "total": total,
            "completed_count": completed_count,
            "in_progress_count": in_progress_count,
            "completion_rate": completion_rate,
            "breakdown": breakdown,
        },
    }
