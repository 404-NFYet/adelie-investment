"""
주식 용어 (Glossary) 모델
난이도: beginner(입문), elementary(초급), intermediate(중급)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Glossary(Base):
    """주식 용어 테이블"""
    
    __tablename__ = "glossary"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="용어 (한글)")
    term_en: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="용어 (영문)")
    abbreviation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="약어")
    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="beginner",
        comment="beginner, elementary, intermediate"
    )
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="basic",
        comment="basic, market, indicator, technical, product, strategy"
    )
    definition_short: Mapped[str] = mapped_column(String(200), nullable=False, comment="한줄 정의")
    definition_full: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="상세 설명")
    example: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="예시")
    formula: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="공식 (지표인 경우)")
    related_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="관련 용어 (쉼표 구분)")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_glossary_difficulty", "difficulty"),
        Index("ix_glossary_category", "category"),
        Index("ix_glossary_term", "term"),
    )

    def __repr__(self):
        return f"<Glossary(term='{self.term}', difficulty='{self.difficulty}')>"
