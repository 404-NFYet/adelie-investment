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

    # Phase 1: 멀티데이 트렌드 메타데이터
    trend_days: Mapped[Optional[int]] = mapped_column(comment="연속 트렌드 일수 (3, 4, 5...)")
    trend_type: Mapped[Optional[str]] = mapped_column(
        String(20), comment="consecutive_rise, consecutive_fall, volume_surge"
    )

    # Phase 3: 뉴스 카탈리스트 정보
    catalyst: Mapped[Optional[str]] = mapped_column(Text, comment="RSS 뉴스에서 추출한 카탈리스트 제목")
    catalyst_url: Mapped[Optional[str]] = mapped_column(Text, comment="카탈리스트 뉴스 원문 링크")
    catalyst_published_at: Mapped[Optional[datetime]] = mapped_column(comment="뉴스 발행 시각")
    catalyst_source: Mapped[Optional[str]] = mapped_column(String(50), comment="뉴스 출처 (네이버, 조선경제 등)")

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    briefing: Mapped["DailyBriefing"] = relationship(back_populates="stocks")

    __table_args__ = (
        Index("ix_briefing_stocks_briefing_id", "briefing_id"),
        Index("ix_briefing_stocks_stock_code", "stock_code"),
    )
