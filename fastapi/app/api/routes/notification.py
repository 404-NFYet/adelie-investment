"""알림 API 라우트."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.notification import Notification

logger = logging.getLogger("narrative_api.notification")

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationItem(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    data: dict | None = None
    created_at: str


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationItem]
    total_count: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class ReadRequest(BaseModel):
    notification_ids: list[int] | None = None  # None이면 전체 읽음 처리


@router.get("", response_model=NotificationsListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """알림 목록 조회."""
    user_id = current_user["id"]
    offset = (page - 1) * per_page

    # 알림 목록
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset).limit(per_page)
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    # 전체 수
    count_stmt = select(func.count()).where(Notification.user_id == user_id)
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # 안읽은 수
    unread_stmt = select(func.count()).where(
        and_(Notification.user_id == user_id, Notification.is_read == False)
    )
    unread_count = (await db.execute(unread_stmt)).scalar() or 0

    return NotificationsListResponse(
        notifications=[
            NotificationItem(
                id=n.id,
                type=n.type,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                data=n.data,
                created_at=n.created_at.isoformat(),
            )
            for n in notifications
        ],
        total_count=total_count,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """안읽은 알림 수."""
    user_id = current_user["id"]
    stmt = select(func.count()).where(
        and_(Notification.user_id == user_id, Notification.is_read == False)
    )
    count = (await db.execute(stmt)).scalar() or 0
    return UnreadCountResponse(unread_count=count)


@router.post("/read")
async def mark_as_read(
    req: ReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """알림 읽음 처리."""
    user_id = current_user["id"]
    if req.notification_ids:
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.id.in_(req.notification_ids)))
            .values(is_read=True)
        )
    else:
        # 전체 읽음
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.is_read == False))
            .values(is_read=True)
        )
    await db.execute(stmt)
    await db.commit()
    return {"message": "읽음 처리 완료"}


@router.delete("/read", name="delete_read_notifications")
async def delete_read_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """읽은 알림 일괄 삭제."""
    user_id = current_user["id"]
    from sqlalchemy import delete as sa_delete
    stmt = sa_delete(Notification).where(
        and_(Notification.user_id == user_id, Notification.is_read == True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"message": f"{result.rowcount}개 알림 삭제 완료", "deleted_count": result.rowcount}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """단일 알림 삭제 (본인 것만)."""
    user_id = current_user["id"]
    result = await db.execute(
        select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    await db.delete(notification)
    await db.commit()
    return {"message": "삭제 완료"}


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: str,
    data: dict | None = None,
):
    """알림 생성 헬퍼 (다른 라우트에서 호출)."""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data,
    )
    db.add(notification)
    # commit은 호출자가 처리 (기존 트랜잭션에 포함)
