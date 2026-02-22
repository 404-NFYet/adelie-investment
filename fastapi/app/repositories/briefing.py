"""Briefing repository - DailyBriefing DB 쿼리."""
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.briefing import DailyBriefing, BriefingStock
from .base import GenericRepository


class BriefingRepository(GenericRepository[DailyBriefing]):
    """DailyBriefing CRUD + 날짜별 조회."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(DailyBriefing, db)

    async def get_by_date(self, briefing_date: date) -> Optional[DailyBriefing]:
        """날짜로 브리핑 단일 조회."""
        return await self.get(briefing_date=briefing_date)

    async def list_recent(self, *, limit: int = 30) -> Sequence[DailyBriefing]:
        """최신 브리핑 목록 조회."""
        return await self.list(
            limit=limit,
            order_by=DailyBriefing.briefing_date.desc(),
        )

    async def get_stocks(
        self,
        briefing_id: int,
    ) -> Sequence[BriefingStock]:
        """브리핑에 연결된 종목 목록 전체 조회."""
        stmt = (
            select(BriefingStock)
            .where(BriefingStock.briefing_id == briefing_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
