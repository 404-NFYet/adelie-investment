"""Historical cases models."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Text, Date, Integer, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

from app.core.database import Base


class HistoricalCase(Base):
    """Historical case model."""
    
    __tablename__ = "historical_cases"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="사례 제목")
    event_date: Mapped[Optional[date]] = mapped_column(Date, comment="사건 발생일")
    event_year: Mapped[Optional[int]] = mapped_column(Integer, comment="사건 연도")
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="사례 요약")
    full_content: Mapped[Optional[str]] = mapped_column(Text, comment="전체 내용 (스토리텔링)")
    keywords: Mapped[Optional[dict]] = mapped_column(JSONB, comment="관련 키워드")
    source_urls: Mapped[Optional[dict]] = mapped_column(JSONB, comment="출처 URL 배열")
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(1536) if Vector else None, nullable=True, comment="OpenAI text-embedding-3-small 벡터"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock_relations: Mapped[list["CaseStockRelation"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    matches: Mapped[list["CaseMatch"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_historical_cases_event_year", "event_year"),
        Index("ix_historical_cases_keywords", "keywords", postgresql_using="gin"),
    )


class CaseStockRelation(Base):
    """Case-stock relation model."""
    
    __tablename__ = "case_stock_relations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("historical_cases.id"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    relation_type: Mapped[Optional[str]] = mapped_column(
        String(50), comment="main_subject, affected, related"
    )
    impact_description: Mapped[Optional[str]] = mapped_column(Text, comment="영향 설명")
    
    # Relationships
    case: Mapped["HistoricalCase"] = relationship(back_populates="stock_relations")
    
    __table_args__ = (
        Index("ix_case_stock_relations_case_id", "case_id"),
        Index("ix_case_stock_relations_stock_code", "stock_code"),
    )


class CaseMatch(Base):
    """Case match model - matches current events to historical cases."""
    
    __tablename__ = "case_matches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    current_keyword: Mapped[str] = mapped_column(String(100), nullable=False, comment="현재 키워드")
    current_stock_code: Mapped[Optional[str]] = mapped_column(String(10), comment="현재 관련 종목")
    matched_case_id: Mapped[int] = mapped_column(ForeignKey("historical_cases.id"), nullable=False)
    similarity_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), comment="유사도 점수 (0~1)")
    match_reason: Mapped[Optional[str]] = mapped_column(Text, comment="매칭 이유")
    matched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationships
    case: Mapped["HistoricalCase"] = relationship(back_populates="matches")
    
    __table_args__ = (
        Index("ix_case_matches_current_keyword", "current_keyword"),
        Index("ix_case_matches_matched_at", "matched_at"),
    )
