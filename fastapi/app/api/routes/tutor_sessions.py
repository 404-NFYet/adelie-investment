"""튜터 세션 CRUD API 엔드포인트."""

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.tutor import TutorSession, TutorMessage
from app.services import get_redis_cache
from app.services.chart_storage import get_chart_presigned_url

logger = logging.getLogger("narrative_api.tutor_sessions")

router = APIRouter(prefix="/tutor", tags=["tutor sessions"])


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """채팅 세션 목록 조회 (최신순, 활성만)."""
    result = await db.execute(
        select(TutorSession)
        .where(
            TutorSession.is_active == True,  # noqa: E712
            TutorSession.user_id == current_user["id"],
        )
        .order_by(desc(TutorSession.last_message_at).nulls_last(), desc(TutorSession.started_at))
        .limit(limit)
    )
    sessions = result.scalars().all()

    session_list = []
    for s in sessions:
        title = s.title
        if not title:
            msg_result = await db.execute(
                select(TutorMessage.content)
                .where(TutorMessage.session_id == s.id, TutorMessage.role == "user")
                .order_by(TutorMessage.created_at)
                .limit(1)
            )
            first_msg = msg_result.scalar_one_or_none()
            title = (first_msg[:50] + "..." if first_msg and len(first_msg) > 50 else first_msg) if first_msg else "새 대화"

        session_list.append({
            "id": str(s.session_uuid),
            "title": title,
            "message_count": s.message_count,
            "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        })

    return session_list


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """특정 세션의 메시지 목록 조회 (Redis 캐시 우선)."""
    cache = await get_redis_cache()
    cached = await cache.get_chat_messages(session_id)
    if cached:
        return json.loads(cached)

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 세션 ID 형식입니다.")

    result = await db.execute(
        select(TutorSession).where(
            TutorSession.session_uuid == session_uuid,
            TutorSession.user_id == current_user["id"],
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    msg_result = await db.execute(
        select(TutorMessage).where(TutorMessage.session_id == session.id).order_by(TutorMessage.created_at)
    )
    messages = msg_result.scalars().all()

    formatted_messages = []
    for m in messages:
        msg_data = {
            "id": m.id, "role": m.role, "content": m.content,
            "message_type": m.message_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        # visualization 메시지 → presigned URL 추가
        if m.message_type == "visualization" and m.content:
            try:
                viz_info = json.loads(m.content)
                minio_path = viz_info.get("minio_path")
                if minio_path:
                    url = get_chart_presigned_url(minio_path)
                    if url:
                        msg_data["chart_url"] = url
                        msg_data["execution_time_ms"] = viz_info.get("execution_time_ms")
            except Exception:
                pass
        formatted_messages.append(msg_data)

    response_data = {
        "session_id": str(session.session_uuid),
        "title": session.title or "새 대화",
        "messages": formatted_messages,
    }

    await cache.set_chat_messages(session_id, json.dumps(response_data, ensure_ascii=False))
    return response_data


@router.post("/sessions/new")
async def create_new_session(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """새 채팅 세션 생성."""
    new_session = TutorSession(
        session_uuid=uuid.uuid4(),
        is_active=True,
        message_count=0,
        user_id=current_user["id"],
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return {"session_id": str(new_session.session_uuid)}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """세션 소프트 삭제 (is_active=False)."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 세션 ID 형식입니다.")

    result = await db.execute(
        select(TutorSession).where(
            TutorSession.session_uuid == session_uuid,
            TutorSession.user_id == current_user["id"],
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session.is_active = False
    session.ended_at = datetime.utcnow()
    await db.commit()

    cache = await get_redis_cache()
    await cache.invalidate_session_cache(session_id)
    return {"deleted": True}
