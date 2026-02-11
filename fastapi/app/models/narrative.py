"""Daily narrative models for the briefing system."""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Text, Integer, Date, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DailyNarrative(Base):
    """일일 내러티브 브리핑 메인 테이블.
    
    각 날짜별로 하나의 DailyNarrative가 생성되고,
    여기에 최대 5개의 NarrativeScenario가 연결됩니다.
    """

    __tablename__ = "daily_narratives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    main_keywords: Mapped[List[str]] = mapped_column(
        ARRAY(Text), 
        nullable=True,
        comment="주요 키워드 목록"
    )
    glossary: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=True, 
        default=dict,
        comment='{"용어": "설명"} 형태의 용어 사전'
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    # Relationships
    scenarios: Mapped[List["NarrativeScenario"]] = relationship(
        back_populates="narrative",
        cascade="all, delete-orphan",
        order_by="NarrativeScenario.sort_order"
    )

    __table_args__ = (
        Index("ix_daily_narratives_date", "date"),
    )


class NarrativeScenario(Base):
    """시나리오 테이블 (브리핑당 최대 5개).
    
    각 시나리오는 7단계 내러티브 섹션을 포함합니다:
    1. background (배경)
    2. mirroring (과거 사례)
    3. simulation (시뮬레이션 + 퀴즈)
    4. result (결과)
    5. difference (차이점)
    6. devils_advocate (악마의 변호인)
    7. action (액션 플랜)
    
    개편된 표시 순서: background, mirroring, simulation, result, difference, devils_advocate, action
    """

    __tablename__ = "narrative_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    narrative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_narratives.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, comment="시나리오 제목")
    summary: Mapped[str] = mapped_column(Text, nullable=True, comment="시나리오 요약")
    sources: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=True, 
        default=list,
        comment='[{name, url}] 형태의 출처 목록'
    )
    related_companies: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=True, 
        default=list,
        comment='[{code, name, reason}] 형태의 관련 기업 목록'
    )
    mirroring_data: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=True, 
        default=dict,
        comment='{target_event, year, reasoning_log} - similarity_score 제거됨'
    )
    narrative_sections: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=True, 
        default=dict,
        comment='7단계 내러티브 콘텐츠 {background, mirroring, simulation, result, difference, devils_advocate, action}'
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0,
        comment="표시 순서 (0-4)"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    narrative: Mapped["DailyNarrative"] = relationship(back_populates="scenarios")

    __table_args__ = (
        Index("ix_narrative_scenarios_narrative_id", "narrative_id"),
        Index("ix_narrative_scenarios_sort_order", "sort_order"),
    )
