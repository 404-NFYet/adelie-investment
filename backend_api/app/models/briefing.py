"""Morning Briefing models."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Text, Date, BigInteger, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DailyBriefing(Base):
    """Daily briefing model."""
    
    __tablename__ = "daily_briefings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    briefing_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    market_summary: Mapped[Optional[str]] = mapped_column(Text, comment="시장 요약")
    top_keywords: Mapped[Optional[dict]] = mapped_column(JSONB, comment="오늘의 키워드 배열")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    stocks: Mapped[list["BriefingStock"]] = relationship(back_populates="briefing", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_daily_briefings_date", "briefing_date"),
    )


class BriefingStock(Base):
    """Briefing stock model."""
    
    __tablename__ = "briefing_stocks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    briefing_id: Mapped[int] = mapped_column(ForeignKey("daily_briefings.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="종목 코드")
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="종목명")
    change_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), comment="등락률 (%)")
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, comment="거래량")
    selection_reason: Mapped[Optional[str]] = mapped_column(
        String(50), comment="top_gainer, top_loser, high_volume"
    )
    keywords: Mapped[Optional[dict]] = mapped_column(JSONB, comment="관련 키워드")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    briefing: Mapped["DailyBriefing"] = relationship(back_populates="stocks")
    
    __table_args__ = (
        Index("ix_briefing_stocks_briefing_id", "briefing_id"),
        Index("ix_briefing_stocks_stock_code", "stock_code"),
    )
