"""
주식 용어 (Glossary) 모델
난이도: beginner(입문), elementary(초급), intermediate(중급)
"""

from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class DifficultyLevel(str, enum.Enum):
    """난이도 레벨"""
    BEGINNER = "beginner"        # 입문: 가장 기초적인 용어
    ELEMENTARY = "elementary"    # 초급: 기본 투자 용어
    INTERMEDIATE = "intermediate"  # 중급: 심화 분석 용어


class GlossaryCategory(str, enum.Enum):
    """용어 카테고리"""
    BASIC = "basic"              # 기본 개념
    MARKET = "market"            # 시장 관련
    INDICATOR = "indicator"      # 투자 지표
    TECHNICAL = "technical"      # 기술적 분석
    PRODUCT = "product"          # 투자 상품
    STRATEGY = "strategy"        # 투자 전략


class Glossary(Base):
    """주식 용어 테이블"""
    __tablename__ = "glossary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(100), nullable=False, unique=True, comment="용어 (한글)")
    term_en = Column(String(100), nullable=True, comment="용어 (영문)")
    abbreviation = Column(String(20), nullable=True, comment="약어")
    difficulty = Column(
        Enum(DifficultyLevel),
        nullable=False,
        default=DifficultyLevel.BEGINNER,
        comment="난이도"
    )
    category = Column(
        Enum(GlossaryCategory),
        nullable=False,
        default=GlossaryCategory.BASIC,
        comment="카테고리"
    )
    definition_short = Column(String(200), nullable=False, comment="한줄 정의")
    definition_full = Column(Text, nullable=True, comment="상세 설명")
    example = Column(Text, nullable=True, comment="예시")
    formula = Column(String(200), nullable=True, comment="공식 (지표인 경우)")
    related_terms = Column(Text, nullable=True, comment="관련 용어 (쉼표 구분)")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Glossary(term='{self.term}', difficulty='{self.difficulty}')>"
