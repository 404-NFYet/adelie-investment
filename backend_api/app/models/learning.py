"""Learning progress model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningProgress(Base):
    """Learning progress model."""
    
    __tablename__ = "learning_progress"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="case, glossary, briefing"
    )
    content_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="viewed", comment="viewed, in_progress, completed"
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="learning_progress")
    
    __table_args__ = (
        Index("ix_learning_progress_user_id", "user_id"),
        Index("ix_learning_progress_content_type", "content_type"),
        UniqueConstraint("user_id", "content_type", "content_id", name="uq_learning_progress_user_content"),
    )


# Forward reference
from app.models.user import User
