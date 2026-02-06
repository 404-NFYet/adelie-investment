"""FastAPI application entry point."""

import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import health, briefing, glossary, cases, tutor, pipeline, highlight, keywords
from app.core.config import settings
from app.core.limiter import limiter
from app.services import get_redis_cache, close_redis_cache

# --- 구조화된 로깅 설정 ---
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("narrative_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting %s v%s ...", settings.APP_NAME, settings.APP_VERSION)
    # Initialize Redis connection
    redis_cache = await get_redis_cache()
    if redis_cache.client:
        logger.info("Redis cache connected")
    else:
        logger.warning("Redis cache not available (running without cache)")
    yield
    # Shutdown
    await close_redis_cache()
    logger.info("%s shutting down...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Narrative Investment API - AI-powered historical case analysis for stock investors",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Rate Limiter 등록 ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- 글로벌 예외 핸들러 ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외를 안전한 JSON 응답으로 변환 (민감 정보 노출 방지)."""
    error_id = uuid.uuid4().hex[:12]
    logger.error(
        "Unhandled exception [error_id=%s] %s %s: %s\n%s",
        error_id,
        request.method,
        request.url.path,
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "detail": "An unexpected error occurred. Please contact support with the error_id.",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 유효성 검사 오류를 구조화된 JSON 응답으로 반환."""
    logger.warning(
        "Validation error %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": [
                {
                    "loc": list(err.get("loc", [])),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", ""),
                }
                for err in exc.errors()
            ],
        },
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(briefing.router, prefix="/api/v1", tags=["Briefing"])
app.include_router(glossary.router, prefix="/api/v1", tags=["Glossary"])
app.include_router(cases.router, prefix="/api/v1", tags=["Cases"])
app.include_router(tutor.router, prefix="/api/v1", tags=["AI Tutor"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["Pipeline"])
app.include_router(highlight.router, prefix="/api/v1", tags=["Highlighting"])
app.include_router(keywords.router, prefix="/api/v1", tags=["Keywords"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8082,
        reload=settings.DEBUG,
    )
