"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Health check endpoint.
    
    Returns the API status and database connection status.
    """
    db_status = "healthy"
    db_error = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "services": {
            "api": "healthy",
            "database": db_status,
        },
        "error": db_error,
    }
