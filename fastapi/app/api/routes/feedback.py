"""피드백 수집 API - 데모 기간 사용자 피드백 관리."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_optional
from app.core.database import get_db
from app.schemas.feedback import (
    AnalyticsEventBatch,
    BriefingFeedbackCreate,
    ContentReactionCreate,
    FeedbackCreate,
    FeedbackSurveyCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


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


@router.post("/reaction", status_code=201)
async def submit_content_reaction(
    reaction: ContentReactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """콘텐츠별 좋아요/싫어요 반응 (UPSERT)."""
    user_id = current_user["id"] if current_user else None
    try:
        await db.execute(
            text("""
                INSERT INTO content_reactions (user_id, content_type, content_id, reaction, created_at)
                VALUES (:user_id, :content_type, :content_id, :reaction, NOW())
                ON CONFLICT (user_id, content_type, content_id)
                DO UPDATE SET reaction = EXCLUDED.reaction, created_at = NOW()
            """),
            {
                "user_id": user_id,
                "content_type": reaction.content_type,
                "content_id": reaction.content_id,
                "reaction": reaction.reaction,
            },
        )
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"콘텐츠 반응 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="반응 저장에 실패했습니다")


@router.post("/survey", status_code=201)
async def submit_feedback_survey(survey: FeedbackSurveyCreate, db: AsyncSession = Depends(get_db)):
    """피드백 설문 제출 (1~5점 평가 + 코멘트)."""
    try:
        await db.execute(
            text("""
                INSERT INTO feedback_surveys
                    (ui_rating, feature_rating, content_rating, speed_rating, overall_rating, comment, screenshot_url, created_at)
                VALUES
                    (:ui_rating, :feature_rating, :content_rating, :speed_rating, :overall_rating, :comment, :screenshot_url, NOW())
            """),
            {
                "ui_rating": survey.ui_rating,
                "feature_rating": survey.feature_rating,
                "content_rating": survey.content_rating,
                "speed_rating": survey.speed_rating,
                "overall_rating": survey.overall_rating,
                "comment": survey.comment,
                "screenshot_url": survey.screenshot_url,
            },
        )
        await db.commit()
        return {"status": "success", "message": "설문이 접수되었습니다"}
    except Exception as e:
        logger.error(f"설문 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="설문 저장에 실패했습니다")


@router.post("/screenshot", status_code=200)
async def upload_screenshot(request: Request):
    """에러 스크린샷 업로드 (MinIO feedback-screenshots 버킷)."""
    import uuid
    from datetime import datetime

    # multipart form 파싱
    try:
        form = await request.form()
        file = form.get("file")
        if not file:
            raise HTTPException(status_code=422, detail="파일이 필요합니다")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="파일 업로드 형식이 올바르지 않습니다")

    # 파일 크기 제한 (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="파일 크기는 5MB 이하만 허용됩니다")

    # MIME 타입 검증
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="이미지 파일만 업로드할 수 있습니다")

    # MinIO 업로드 시도
    try:
        from app.core.config import settings
        from minio import Minio
        import io

        bucket_name = "feedback-screenshots"
        ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
        object_name = f"{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4().hex}.{ext}"

        client = Minio(
            settings.MINIO_ENDPOINT if hasattr(settings, "MINIO_ENDPOINT") else "minio:9000",
            access_key=settings.MINIO_ACCESS_KEY if hasattr(settings, "MINIO_ACCESS_KEY") else "minioadmin",
            secret_key=settings.MINIO_SECRET_KEY if hasattr(settings, "MINIO_SECRET_KEY") else "minioadmin",
            secure=False,
        )

        # 버킷 자동 생성
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        client.put_object(
            bucket_name,
            object_name,
            io.BytesIO(contents),
            length=len(contents),
            content_type=content_type,
        )

        url = f"/minio/{bucket_name}/{object_name}"
        return {"status": "success", "url": url}
    except ImportError:
        # MinIO 미설치 시 로컬 경로 반환 (개발 환경)
        logger.warning("MinIO 미설치 — 스크린샷 업로드 스킵")
        return {"status": "success", "url": f"/feedback-screenshots/{uuid.uuid4().hex}"}
    except Exception as e:
        logger.error(f"스크린샷 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail="스크린샷 업로드에 실패했습니다")


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
