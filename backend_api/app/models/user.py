"""User related models."""

from datetime import datetime, time
from typing import Optional

from sqlalchemy import String, Boolean, Time, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty_level: Mapped[str] = mapped_column(
        String(20), default="beginner", comment="beginner, elementary, intermediate"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user", uselist=False)
    tutor_sessions: Mapped[list["TutorSession"]] = relationship(back_populates="user")
    learning_progress: Mapped[list["LearningProgress"]] = relationship(back_populates="user")
    portfolios: Mapped[list["UserPortfolio"]] = relationship(back_populates="user")
    
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
    )


class UserSettings(Base):
    """User settings model."""
    
    __tablename__ = "user_settings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    theme: Mapped[str] = mapped_column(String(10), default="light", comment="light, dark")
    push_notification: Mapped[bool] = mapped_column(Boolean, default=True)
    morning_briefing_time: Mapped[time] = mapped_column(Time, default=time(8, 0))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="settings")


# Forward references for type hints
from app.models.tutor import TutorSession
from app.models.learning import LearningProgress
from app.models.portfolio import UserPortfolio
