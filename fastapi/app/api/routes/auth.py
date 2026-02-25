"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from typing import Optional
import secrets
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.metrics import AUTH_LOGIN_TOTAL, AUTH_REFRESH_TOTAL
from app.services.auth_service import login_user, refresh_tokens, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_access_cookie_max_age() -> int:
    settings = get_settings()
    if settings.JWT_ACCESS_EXPIRATION:
        return max(int(settings.JWT_ACCESS_EXPIRATION // 1000), 1)
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES:
        return max(int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60), 60)
    return max(int(settings.JWT_EXPIRE_MINUTES * 60), 60)


def _get_refresh_cookie_max_age() -> int:
    settings = get_settings()
    if settings.JWT_REFRESH_EXPIRATION:
        return max(int(settings.JWT_REFRESH_EXPIRATION // 1000), 1)
    return 60 * 60 * 24 * 7


def _set_access_cookie(response: Response, access_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.AUTH_ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.AUTH_ACCESS_COOKIE_SECURE,
        samesite=settings.AUTH_ACCESS_COOKIE_SAMESITE,
        path=settings.AUTH_ACCESS_COOKIE_PATH,
        domain=settings.AUTH_ACCESS_COOKIE_DOMAIN,
        max_age=_get_access_cookie_max_age(),
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
        max_age=_get_refresh_cookie_max_age(),
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.AUTH_ACCESS_COOKIE_NAME,
        path=settings.AUTH_ACCESS_COOKIE_PATH,
        domain=settings.AUTH_ACCESS_COOKIE_DOMAIN,
    )
    response.delete_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN,
    )
    response.delete_cookie(
        key=settings.AUTH_CSRF_COOKIE_NAME,
        path=settings.AUTH_CSRF_COOKIE_PATH,
        domain=settings.AUTH_CSRF_COOKIE_DOMAIN,
    )


def _set_csrf_cookie(response: Response) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.AUTH_CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        secure=settings.AUTH_CSRF_COOKIE_SECURE,
        samesite=settings.AUTH_CSRF_COOKIE_SAMESITE,
        path=settings.AUTH_CSRF_COOKIE_PATH,
        domain=settings.AUTH_CSRF_COOKIE_DOMAIN,
    )
    return token

@router.post("/register", response_model=AuthResponse, response_model_exclude_none=True)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    auth = await register_user(
        db,
        email=payload.email,
        password=payload.password,
        username=payload.username,
        difficulty_level=payload.difficulty_level
    )
    if auth.get("accessToken"):
        _set_access_cookie(response, auth["accessToken"])
        auth.pop("accessToken", None)
    if auth.get("refreshToken"):
        _set_refresh_cookie(response, auth["refreshToken"])
        auth.pop("refreshToken", None)
    _set_csrf_cookie(response)
    return auth


@router.post("/login", response_model=AuthResponse, response_model_exclude_none=True)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    try:
        auth = await login_user(db, email=payload.email, password=payload.password)
        AUTH_LOGIN_TOTAL.labels("success").inc()
    except Exception:
        AUTH_LOGIN_TOTAL.labels("fail").inc()
        raise
    if auth.get("accessToken"):
        _set_access_cookie(response, auth["accessToken"])
        auth.pop("accessToken", None)
    if auth.get("refreshToken"):
        _set_refresh_cookie(response, auth["refreshToken"])
        auth.pop("refreshToken", None)
    _set_csrf_cookie(response)
    return auth


@router.post("/refresh", response_model=AuthResponse, response_model_exclude_none=True)
async def refresh(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if not refresh_token and payload:
        refresh_token = payload.refreshToken
    if not refresh_token or not refresh_token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refreshToken is required",
        )
    try:
        auth = await refresh_tokens(db, refresh_token=refresh_token)
        AUTH_REFRESH_TOTAL.labels("success").inc()
    except Exception:
        AUTH_REFRESH_TOTAL.labels("fail").inc()
        raise
    if auth.get("accessToken"):
        _set_access_cookie(response, auth["accessToken"])
        auth.pop("accessToken", None)
    if auth.get("refreshToken"):
        _set_refresh_cookie(response, auth["refreshToken"])
        auth.pop("refreshToken", None)
    _set_csrf_cookie(response)
    return auth


@router.post("/logout")
async def logout(
    response: Response,
    user: dict | None = Depends(get_current_user_optional),
) -> dict:
    # Stateless JWT: client discards token. Keep endpoint for compatibility.
    if user:
        pass
    _clear_auth_cookies(response)
    return {}


@router.get("/csrf")
async def issue_csrf(response: Response) -> dict:
    token = _set_csrf_cookie(response)
    return {"csrfToken": token}


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "difficultyLevel": user.get("difficulty_level") or "beginner",
        "authenticated": True,
    }
