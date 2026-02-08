"""AI Tutor session models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Integer, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TutorSession(Base):
    """AI Tutor session model."""
    
    __tablename__ = "tutor_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    session_uuid: Mapped[str] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    context_type: Mapped[Optional[str]] = mapped_column(
        String(50), comment="briefing, case, comparison, glossary"
    )
    context_id: Mapped[Optional[int]] = mapped_column(comment="관련 컨텐츠 ID")
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="세션 제목")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 세션 여부")
    message_count: Mapped[int] = mapped_column(Integer, default=0, comment="메시지 수")
    last_message_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="마지막 메시지 시각")
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="tutor_sessions")
    messages: Mapped[list["TutorMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_tutor_sessions_user_id", "user_id"),
        Index("ix_tutor_sessions_session_uuid", "session_uuid"),
    )


class TutorMessage(Base):
    """AI Tutor message model."""
    
    __tablename__ = "tutor_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("tutor_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="user, assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="text, visualization")
    term_asked: Mapped[Optional[str]] = mapped_column(String(100), comment="질문한 용어 (있는 경우)")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    session: Mapped["TutorSession"] = relationship(back_populates="messages")
    
    __table_args__ = (
        Index("ix_tutor_messages_session_id", "session_id"),
        Index("ix_tutor_messages_created_at", "created_at"),
    )


# Forward reference
from app.models.user import User
