"""Narrative repository - 일일 내러티브/시나리오 DB 쿼리."""
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.narrative import DailyNarrative, NarrativeScenario
from .base import GenericRepository


class NarrativeRepository(GenericRepository[DailyNarrative]):
    """DailyNarrative CRUD + 날짜별 조회."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(DailyNarrative, db)

    async def get_by_date(self, target_date: date) -> Optional[DailyNarrative]:
        """날짜로 내러티브 단일 조회."""
        return await self.get(narrative_date=target_date)

    async def list_recent(self, *, limit: int = 10) -> Sequence[DailyNarrative]:
        """최신 내러티브 목록 조회."""
        return await self.list(
            limit=limit,
            order_by=DailyNarrative.narrative_date.desc(),
        )

    async def get_scenarios(
        self,
        narrative_id: int,
        *,
        limit: int = 10,
    ) -> Sequence[NarrativeScenario]:
        """내러티브에 연결된 시나리오 목록 조회."""
        stmt = (
            select(NarrativeScenario)
            .where(NarrativeScenario.narrative_id == narrative_id)
            .order_by(NarrativeScenario.order_index)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_scenario_by_id(self, scenario_id: int) -> Optional[NarrativeScenario]:
        """시나리오 ID로 단일 조회."""
        result = await self.db.execute(
            select(NarrativeScenario).where(NarrativeScenario.id == scenario_id)
        )
        return result.scalar_one_or_none()
