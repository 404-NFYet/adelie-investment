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

import importlib
import logging as _logging

# 각 라우터를 개별적으로 import (Docker 환경에서 일부 모듈 미존재 시 graceful 처리)
_route_modules = {}
for _mod_name in [
    "health",
    "auth",
    "briefing",
    "glossary",
    "cases",
    "tutor",
    "pipeline",
    "highlight",
    "keywords",
    "feedback",
    "trading",
    "narrative",
    "portfolio",
    "tutor_sessions",
    "visualization",
    "notification",
    "briefings",
    "quiz_reward",
    "learning",
    "reports",
]:
    try:
        _route_modules[_mod_name] = importlib.import_module(f"app.api.routes.{_mod_name}")
    except Exception as _e:
        _logging.getLogger("startup").warning(f"라우터 '{_mod_name}' 로드 실패 (무시): {_e}")
from app.core.config import settings
from app.core.limiter import limiter
from app.services import get_redis_cache, close_redis_cache
from app.core.scheduler import start_scheduler, stop_scheduler

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
    # 데일리 파이프라인 스케줄러 시작
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()
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

# --- 글로벌 레이트 리미터 (IP당 100 req/min, Redis 기반) ---
_RATE_LIMIT_MAX = 100
_RATE_LIMIT_WINDOW = 60


@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    """IP 기반 글로벌 레이트 리미팅 (100 req/min, Redis INCR 패턴)."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"
    try:
        cache = await get_redis_cache()
        if cache.client:
            count = await cache.client.incr(key)
            if count == 1:
                await cache.client.expire(key, _RATE_LIMIT_WINDOW)
            if count > _RATE_LIMIT_MAX:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests",
                        "detail": f"Rate limit: {_RATE_LIMIT_MAX}/min",
                    },
                )
    except Exception:
        pass  # Redis 실패 시 rate limit 미적용 (graceful)
    return await call_next(request)


# Include routers (로드 성공한 모듈만 등록)
_router_config = {
    "health": ("health", "/api/v1"),
    "auth": ("auth", "/api/v1"),
    "briefing": ("briefing", "/api/v1"),
    "glossary": ("glossary", "/api/v1"),
    "cases": ("cases", "/api/v1"),
    "tutor": ("AI tutor", "/api/v1"),
    "pipeline": ("pipeline", "/api/v1"),
    "highlight": ("highlighting", "/api/v1"),
    "keywords": ("keywords", "/api/v1"),
    "feedback": ("feedback", "/api/v1"),
    "trading": ("trading", "/api/v1"),
    "narrative": ("narrative", "/api/v1"),
    "portfolio": ("portfolio", "/api/v1"),
    "tutor_sessions": ("tutor sessions", "/api/v1"),
    "visualization": ("visualization", "/api/v1"),
    "notification": ("notifications", "/api/v1"),
    "briefings": ("briefings", "/api/v1"),
    "quiz_reward": ("quiz", "/api/v1"),
    "learning": ("learning progress", "/api/v1"),
    "reports": ("broker reports", "/api/v1"),
}
for _name, (_tag, _prefix) in _router_config.items():
    _mod = _route_modules.get(_name)
    if _mod and hasattr(_mod, "router"):
        app.include_router(_mod.router, prefix=_prefix, tags=[_tag])
    else:
        logger.warning(f"라우터 '{_name}' 건너뜀 (미로드)")

# Legacy compatibility: /api/health (Spring Boot path)
_health_mod = _route_modules.get("health")
if _health_mod and hasattr(_health_mod, "router"):
    app.include_router(_health_mod.router, prefix="/api", tags=["health"], include_in_schema=False)


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
