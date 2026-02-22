"""GenericRepository - 공통 CRUD 기반 클래스."""
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class GenericRepository(Generic[ModelT]):
    """SQLAlchemy 비동기 모델 공통 CRUD 래퍼.

    사용 예:
        repo = GenericRepository(MyModel, db)
        item = await repo.get(id=1)
        items = await repo.list(limit=10)
    """

    def __init__(self, model: Type[ModelT], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, **filters: Any) -> Optional[ModelT]:
        """단일 레코드 조회. 없으면 None 반환."""
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Any] = None,
        **filters: Any,
    ) -> Sequence[ModelT]:
        """다수 레코드 조회."""
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, **data: Any) -> ModelT:
        """새 레코드 생성 후 반환."""
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **data: Any) -> ModelT:
        """기존 레코드 부분 업데이트."""
        for field, value in data.items():
            setattr(instance, field, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """레코드 삭제."""
        await self.db.delete(instance)
        await self.db.flush()
