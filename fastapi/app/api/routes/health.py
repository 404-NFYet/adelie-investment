"""Health check endpoints — liveness / readiness 분리."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """통합 헬스체크 (하위호환)."""
    db_status = "healthy"
    redis_status = "healthy"
    db_error = None
    redis_error = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    try:
        from app.services.redis_cache import get_redis_cache
        cache = await get_redis_cache()
        await cache.client.ping()
    except Exception as e:
        redis_status = "unhealthy"
        redis_error = str(e)

    overall = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    if overall == "degraded":
        response.status_code = 503

    return {
        "status": overall,
        "services": {
            "api": "healthy",
            "database": db_status,
            "redis": redis_status,
        },
        "errors": {k: v for k, v in {"database": db_error, "redis": redis_error}.items() if v},
    }


@router.get("/health/live")
async def liveness() -> dict:
    """Liveness probe — 프로세스 살아있는지만 확인."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe — DB + Redis 연결 확인."""
    checks = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except Exception:
        checks["database"] = "not_ready"

    try:
        from app.services.redis_cache import get_redis_cache
        cache = await get_redis_cache()
        await cache.client.ping()
        checks["redis"] = "ready"
    except Exception:
        checks["redis"] = "not_ready"

    all_ready = all(v == "ready" for v in checks.values())
    if not all_ready:
        response.status_code = 503

    return {"status": "ready" if all_ready else "not_ready", "checks": checks}
