"""복습카드 모델."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FlashCard(Base):
    """사용자 복습카드 모델."""

    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="카드 제목")
    content_html: Mapped[str] = mapped_column(Text, nullable=False, comment="복습카드 HTML 전체")
    source_session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tutor_sessions.id"), nullable=True, comment="출처 튜터 세션"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_flashcards_user_id", "user_id"),
    )
