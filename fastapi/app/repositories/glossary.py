"""Glossary repository - 투자 용어 DB 쿼리."""
from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.glossary import Glossary
from .base import GenericRepository


class GlossaryRepository(GenericRepository[Glossary]):
    """Glossary CRUD + 검색 쿼리."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Glossary, db)

    async def get_by_term(self, term: str) -> Optional[Glossary]:
        """정확한 용어명으로 조회 (ILIKE)."""
        stmt = (
            select(Glossary)
            .where(Glossary.term.ilike(f"%{term}%"))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        difficulty: Optional[str] = None,
    ) -> Sequence[Glossary]:
        """용어 + 설명 전문 검색."""
        stmt = select(Glossary).where(
            or_(
                Glossary.term.ilike(f"%{query}%"),
                Glossary.definition_short.ilike(f"%{query}%"),
            )
        )
        if difficulty:
            stmt = stmt.where(Glossary.difficulty == difficulty)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_difficulty(
        self,
        difficulty: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Glossary]:
        """난이도별 용어 목록."""
        return await self.list(
            difficulty=difficulty,
            limit=limit,
            offset=offset,
            order_by=Glossary.term,
        )
