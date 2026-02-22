"""Portfolio repository - 포트폴리오 관련 DB 쿼리."""
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portfolio import UserPortfolio, SimulationTrade
from .base import GenericRepository


class PortfolioRepository(GenericRepository[UserPortfolio]):
    """UserPortfolio CRUD + 비즈니스 쿼리."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(UserPortfolio, db)

    async def get_by_user(self, user_id: int) -> Optional[UserPortfolio]:
        """유저 ID로 포트폴리오 단일 조회."""
        return await self.get(user_id=user_id)

    async def get_trades_by_portfolio(
        self,
        portfolio_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[SimulationTrade]:
        """포트폴리오 거래 내역 조회 (최신순)."""
        stmt = (
            select(SimulationTrade)
            .where(SimulationTrade.portfolio_id == portfolio_id)
            .order_by(SimulationTrade.traded_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_trade(
        self,
        portfolio_id: int,
        stock_code: str,
        stock_name: str,
        trade_type: str,
        quantity: int,
        price: int,
        **extra,
    ) -> SimulationTrade:
        """거래 기록 생성."""
        trade = SimulationTrade(
            portfolio_id=portfolio_id,
            stock_code=stock_code,
            stock_name=stock_name,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            traded_at=datetime.utcnow(),
            **extra,
        )
        self.db.add(trade)
        await self.db.flush()
        await self.db.refresh(trade)
        return trade
