"""Authentication business logic for FastAPI (Spring Boot parity)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import _get_jwt_key
from app.core.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_access_exp_seconds(settings) -> int:
    if settings.JWT_ACCESS_EXPIRATION:
        return max(int(settings.JWT_ACCESS_EXPIRATION // 1000), 1)
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES:
        return max(int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60), 60)
    return max(int(settings.JWT_EXPIRE_MINUTES * 60), 60)


def _get_refresh_exp_seconds(settings) -> int:
    if settings.JWT_REFRESH_EXPIRATION:
        return max(int(settings.JWT_REFRESH_EXPIRATION // 1000), 1)
    # 7 days default
    return 60 * 60 * 24 * 7


def _build_token(subject: str, expires_in: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(
        payload,
        _get_jwt_key(settings.JWT_SECRET),
        algorithm=settings.JWT_ALGORITHM,
    )


def _validate_email_domain(email: str, blocked_domains: list[str]) -> None:
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 이메일 형식입니다.",
        )
    domain = email.split("@", 1)[1].lower()
    for blocked in blocked_domains:
        if domain == blocked.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"허용되지 않는 이메일 도메인입니다: {domain}",
            )


def _validate_username(username: str, pattern: re.Pattern) -> None:
    if not username or not username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자명은 비어있을 수 없습니다.",
        )
    if pattern.match(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용할 수 없는 사용자명입니다.",
        )


async def register_user(db: AsyncSession, *, email: str, password: str, username: str | None) -> dict:
    settings = get_settings()

    _validate_email_domain(email, settings.registration_blocked_domains)

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    if not username:
        username = email.split("@", 1)[0]

    pattern = re.compile(settings.REGISTRATION_BLOCKED_USERNAME_PATTERN, re.IGNORECASE)
    _validate_username(username, pattern)

    # Optional: avoid username uniqueness conflicts early
    existing_username = await db.execute(select(User).where(User.username == username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 사용 중인 사용자명입니다.",
        )

    user = User(
        email=email,
        username=username,
        password_hash=_pwd_context.hash(password),
        difficulty_level="beginner",
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 사용자 정보입니다.",
        )

    access_token = _build_token(email, _get_access_exp_seconds(settings))
    refresh_token = _build_token(email, _get_refresh_exp_seconds(settings))

    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "Bearer",
        "expiresIn": _get_access_exp_seconds(settings),
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }


async def login_user(db: AsyncSession, *, email: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not _pwd_context.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()

    settings = get_settings()
    access_token = _build_token(email, _get_access_exp_seconds(settings))
    refresh_token = _build_token(email, _get_refresh_exp_seconds(settings))

    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "Bearer",
        "expiresIn": _get_access_exp_seconds(settings),
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }


async def refresh_tokens(db: AsyncSession, *, refresh_token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            refresh_token,
            _get_jwt_key(settings.JWT_SECRET),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = _build_token(email, _get_access_exp_seconds(settings))
    new_refresh_token = _build_token(email, _get_refresh_exp_seconds(settings))

    return {
        "accessToken": access_token,
        "refreshToken": new_refresh_token,
        "tokenType": "Bearer",
        "expiresIn": _get_access_exp_seconds(settings),
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }
