"""Database configuration and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.metrics import DB_QUERY_TOTAL


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=50,
    max_overflow=100,
    pool_timeout=30,
    pool_recycle=1800,
)


def _extract_db_operation(statement: str) -> str:
    if not statement:
        return "other"
    op = statement.lstrip().split(None, 1)[0].lower()
    if op in {"select", "insert", "update", "delete"}:
        return op
    return "other"


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    DB_QUERY_TOTAL.labels(_extract_db_operation(statement), "success").inc()


@event.listens_for(engine.sync_engine, "handle_error")
def _handle_db_error(exception_context):
    statement = getattr(exception_context, "statement", "") or ""
    DB_QUERY_TOTAL.labels(_extract_db_operation(statement), "fail").inc()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
