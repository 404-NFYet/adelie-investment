"""피드백 수집 API - 데모 기간 사용자 피드백 관리."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


# ── Schemas ──


class FeedbackCreate(BaseModel):
    """피드백 생성 요청."""
    page: str = Field(..., max_length=50, description="현재 페이지 (home, narrative, portfolio, tutor, trading)")
    rating: Optional[int] = Field(None, ge=1, le=5, description="별점 (1~5)")
    category: Optional[str] = Field(None, max_length=20, description="카테고리 (design, feature, content, speed, other)")
    comment: Optional[str] = Field(None, max_length=1000, description="텍스트 의견")
    device_info: Optional[dict] = Field(None, description="디바이스 정보 (userAgent, screen, pwa여부)")


class BriefingFeedbackCreate(BaseModel):
    """브리핑 완독 피드백."""
    briefing_id: Optional[int] = None
    scenario_keyword: Optional[str] = None
    overall_rating: str = Field(..., description="good, neutral, bad")
    favorite_section: Optional[str] = Field(None, description="mirroring, devils_advocate, simulation, action")


class AnalyticsEventBatch(BaseModel):
    """사용 행동 이벤트 배치."""
    events: list[dict] = Field(..., description="이벤트 목록")


class FeedbackStats(BaseModel):
    """피드백 통계 응답."""
    total_count: int
    avg_rating: float
    category_distribution: dict
    page_distribution: dict


# ── API 엔드포인트 ──


@router.post("", status_code=201)
async def submit_feedback(feedback: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    """인앱 피드백 제출."""
    try:
        await db.execute(
            text("""
                INSERT INTO user_feedback (page, rating, category, comment, device_info, created_at)
                VALUES (:page, :rating, :category, :comment, CAST(:device_info AS JSONB), NOW())
            """),
            {
                "page": feedback.page,
                "rating": feedback.rating,
                "category": feedback.category,
                "comment": feedback.comment,
                "device_info": str(feedback.device_info) if feedback.device_info else None,
            },
        )
        await db.commit()
        return {"status": "success", "message": "피드백이 접수되었습니다"}
    except Exception as e:
        logger.error(f"피드백 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="피드백 저장에 실패했습니다")


@router.post("/briefing", status_code=201)
async def submit_briefing_feedback(feedback: BriefingFeedbackCreate, db: AsyncSession = Depends(get_db)):
    """브리핑 완독 후 미니 설문."""
    try:
        await db.execute(
            text("""
                INSERT INTO briefing_feedback (briefing_id, scenario_keyword, overall_rating, favorite_section, created_at)
                VALUES (:briefing_id, :scenario_keyword, :overall_rating, :favorite_section, NOW())
            """),
            {
                "briefing_id": feedback.briefing_id,
                "scenario_keyword": feedback.scenario_keyword,
                "overall_rating": feedback.overall_rating,
                "favorite_section": feedback.favorite_section,
            },
        )
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"브리핑 피드백 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="피드백 저장에 실패했습니다")


@router.get("/stats")
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    """관리자용 피드백 통계."""
    try:
        result = await db.execute(text("""
            SELECT
                COUNT(*) as total,
                ROUND(AVG(rating)::numeric, 2) as avg_rating
            FROM user_feedback
        """))
        row = result.fetchone()

        cat_result = await db.execute(text("""
            SELECT category, COUNT(*) as cnt
            FROM user_feedback
            WHERE category IS NOT NULL
            GROUP BY category
        """))

        page_result = await db.execute(text("""
            SELECT page, COUNT(*) as cnt, ROUND(AVG(rating)::numeric, 2) as avg
            FROM user_feedback
            GROUP BY page
        """))

        return {
            "total_count": row[0] if row else 0,
            "avg_rating": float(row[1]) if row and row[1] else 0,
            "category_distribution": {r[0]: r[1] for r in cat_result.fetchall()},
            "page_distribution": {r[0]: {"count": r[1], "avg_rating": float(r[2])} for r in page_result.fetchall()},
        }
    except Exception:
        return {"total_count": 0, "avg_rating": 0, "category_distribution": {}, "page_distribution": {}}


# ── 사용 행동 분석 ──


@router.post("/analytics/events", status_code=201)
async def submit_analytics_events(batch: AnalyticsEventBatch, db: AsyncSession = Depends(get_db)):
    """사용 행동 이벤트 배치 저장."""
    try:
        for event in batch.events[:50]:  # 최대 50개까지
            await db.execute(
                text("""
                    INSERT INTO usage_events (user_id, session_id, event_type, event_data, created_at)
                    VALUES (:user_id, :session_id, :event_type, :event_data::jsonb, NOW())
                """),
                {
                    "user_id": event.get("user_id"),
                    "session_id": event.get("session_id", ""),
                    "event_type": event.get("event_type", "unknown"),
                    "event_data": str(event.get("event_data", {})),
                },
            )
        await db.commit()
        return {"status": "success", "count": len(batch.events)}
    except Exception as e:
        logger.error(f"Analytics 이벤트 저장 실패: {e}")
        return {"status": "partial", "error": str(e)}
