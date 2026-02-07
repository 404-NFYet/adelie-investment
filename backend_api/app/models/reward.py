"""Briefing completion reward model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, BigInteger, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BriefingReward(Base):
    """Tracks briefing completion rewards and gamification multiplier.

    Lifecycle:
      pending → (7일 경과) → applied (수익+: 1.5배 보너스) or expired (손실: 보너스 소멸)
    """

    __tablename__ = "briefing_rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("user_portfolios.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="completed briefing case")
    base_reward: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="기본 보상 (원)")
    multiplier: Mapped[float] = mapped_column(Float, default=1.0, comment="gamification multiplier")
    final_reward: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="최종 지급액 (원)")
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
        comment="pending, applied, expired",
    )
    maturity_at: Mapped[datetime] = mapped_column(comment="multiplier 체크 시점")
    applied_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship()
    portfolio: Mapped["UserPortfolio"] = relationship()

    __table_args__ = (
        Index("ix_briefing_rewards_user_id", "user_id"),
        Index("ix_briefing_rewards_status", "status"),
        Index("ix_briefing_rewards_maturity", "maturity_at"),
    )


# Forward references
from app.models.user import User
from app.models.portfolio import UserPortfolio
