"""프로덕션 DB → dev DB 콘텐츠 테이블 자동 동기화.

파이프라인 완료 후 _post_pipeline_hooks()에서 호출.
DEV_DATABASE_URL 환경변수가 설정된 경우에만 동작한다.
"""

import io
import logging
import os
import time

import asyncpg

logger = logging.getLogger("narrative_api.dev_db_sync")

# 동기화 대상 콘텐츠 테이블 (FK 의존 순서)
CONTENT_TABLES = [
    "stock_listings",
    "daily_briefings",
    "briefing_stocks",
    "historical_cases",
    "case_matches",
    "case_stock_relations",
    "broker_reports",
]


def _normalize_dsn(url: str) -> str:
    """SQLAlchemy DSN → asyncpg DSN 변환."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def sync_content_to_dev_db() -> None:
    """프로덕션 DB에서 dev DB로 콘텐츠 테이블을 asyncpg binary COPY로 동기화."""
    dev_url = os.getenv("DEV_DATABASE_URL", "")
    if not dev_url:
        logger.debug("DEV_DATABASE_URL 미설정 — dev DB 동기화 스킵")
        return

    from app.core.config import settings
    prod_dsn = _normalize_dsn(settings.DATABASE_URL)
    dev_dsn = _normalize_dsn(dev_url)

    logger.info("=== dev DB 동기화 시작 ===")
    start = time.monotonic()

    prod_conn: asyncpg.Connection | None = None
    dev_conn: asyncpg.Connection | None = None
    try:
        prod_conn = await asyncpg.connect(prod_dsn, timeout=15)
        dev_conn = await asyncpg.connect(dev_dsn, timeout=15)

        # FK 제약 임시 비활성화
        await dev_conn.execute("SET session_replication_role = replica")

        for table in CONTENT_TABLES:
            await _sync_table(prod_conn, dev_conn, table)

        await dev_conn.execute("SET session_replication_role = DEFAULT")

        elapsed = time.monotonic() - start
        logger.info("=== dev DB 동기화 완료 (%.1f초) ===", elapsed)
    except Exception as e:
        logger.error("dev DB 동기화 실패: %s", e)
        raise
    finally:
        if prod_conn:
            await prod_conn.close()
        if dev_conn:
            await dev_conn.close()


async def _sync_table(
    prod_conn: asyncpg.Connection,
    dev_conn: asyncpg.Connection,
    table: str,
) -> None:
    """단일 테이블을 binary COPY로 동기화."""
    buf = io.BytesIO()

    # prod에서 binary COPY OUT
    await prod_conn.copy_from_table(table, output=buf, format="binary")
    row_bytes = buf.tell()
    buf.seek(0)

    # dev 테이블 TRUNCATE → binary COPY IN
    await dev_conn.execute(f"TRUNCATE TABLE {table} CASCADE")
    await dev_conn.copy_to_table(table, source=buf, format="binary")

    count = await dev_conn.fetchval(f"SELECT count(*) FROM {table}")
    logger.info("  %s: %d rows (%.1f KB)", table, count, row_bytes / 1024)
