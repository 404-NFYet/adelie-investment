"""복습카드 CRUD API 엔드포인트."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.flashcard import FlashCard

logger = logging.getLogger("narrative_api.flashcards")

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


class FlashCardCreate(BaseModel):
    title: str
    content_html: str
    source_session_id: Optional[int] = None


class FlashCardResponse(BaseModel):
    id: int
    title: str
    content_html: str
    source_session_id: Optional[int]
    created_at: datetime


@router.post("", response_model=FlashCardResponse)
async def create_flashcard(
    body: FlashCardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """복습카드 저장."""
    card = FlashCard(
        user_id=current_user["id"],
        title=body.title[:300],
        content_html=body.content_html,
        source_session_id=body.source_session_id,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    logger.info("복습카드 저장: user_id=%s, id=%s", current_user["id"], card.id)
    return FlashCardResponse(
        id=card.id,
        title=card.title,
        content_html=card.content_html,
        source_session_id=card.source_session_id,
        created_at=card.created_at,
    )


@router.get("", response_model=list[FlashCardResponse])
async def list_flashcards(
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """복습카드 목록 조회 (최신순)."""
    result = await db.execute(
        select(FlashCard)
        .where(FlashCard.user_id == current_user["id"])
        .order_by(desc(FlashCard.created_at))
        .limit(limit)
    )
    cards = result.scalars().all()
    return [
        FlashCardResponse(
            id=c.id,
            title=c.title,
            content_html=c.content_html,
            source_session_id=c.source_session_id,
            created_at=c.created_at,
        )
        for c in cards
    ]


@router.delete("/{card_id}")
async def delete_flashcard(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """복습카드 삭제."""
    result = await db.execute(
        select(FlashCard).where(
            FlashCard.id == card_id,
            FlashCard.user_id == current_user["id"],
        )
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="복습카드를 찾을 수 없습니다.")
    await db.delete(card)
    await db.commit()
    return {"ok": True}
