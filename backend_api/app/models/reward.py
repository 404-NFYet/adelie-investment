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


class DwellReward(Base):
    """체류 시간 보상 모델. 3분 이상 학습 시 5만원 지급."""

    __tablename__ = "dwell_rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("user_portfolios.id"), nullable=False)
    page: Mapped[str] = mapped_column(String(50), nullable=False, comment="narrative, story, comparison")
    dwell_seconds: Mapped[int] = mapped_column(Integer, nullable=False, comment="체류 시간 (초)")
    reward_amount: Mapped[int] = mapped_column(BigInteger, default=50_000, comment="보상 금액 (원)")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship()
    portfolio: Mapped["UserPortfolio"] = relationship()

    __table_args__ = (
        Index("ix_dwell_rewards_user_id", "user_id"),
        Index("ix_dwell_rewards_created_at", "created_at"),
    )


# Forward references
from app.models.user import User
from app.models.portfolio import UserPortfolio
