"""Authentication business logic."""

from __future__ import annotations

import logging
import re
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import _get_jwt_key
from app.core.config import get_settings
from app.models.user import User
from app.services import get_redis_cache

if TYPE_CHECKING:
    import redis.asyncio as redis

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


def _build_token(subject: str, expires_in: int, extra_claims: dict | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
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

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _require_redis() -> "redis.Redis":
    cache = await get_redis_cache()
    if not cache.client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable for token management",
        )
    return cache.client


async def _store_refresh_token(*, user_id: int, jti: str, token_hash: str, ttl: int) -> None:
    client = await _require_redis()
    token_key = f"auth:rt:{jti}"
    user_key = f"auth:rt:uid:{user_id}"
    async with client.pipeline(transaction=True) as pipe:
        pipe.setex(token_key, ttl, token_hash)
        pipe.sadd(user_key, jti)
        pipe.expire(user_key, ttl)
        await pipe.execute()


async def _revoke_user_refresh_tokens(user_id: int) -> None:
    client = await _require_redis()
    user_key = f"auth:rt:uid:{user_id}"
    jtis = await client.smembers(user_key)
    if not jtis:
        await client.delete(user_key)
        return
    async with client.pipeline(transaction=True) as pipe:
        for jti in jtis:
            pipe.delete(f"auth:rt:{jti}")
        pipe.delete(user_key)
        await pipe.execute()



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


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    username: str | None,
    difficulty_level: str | None,
) -> dict:
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

    normalized_level = (difficulty_level or "beginner").strip().lower()
    allowed_levels = {"beginner", "elementary", "intermediate"}
    if normalized_level not in allowed_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="difficulty_level은 beginner, elementary, intermediate 중 하나여야 합니다.",
        )

    user = User(
        email=email,
        username=username,
        password_hash=_pwd_context.hash(password),
        difficulty_level=normalized_level,
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
    refresh_ttl = _get_refresh_exp_seconds(settings)
    refresh_jti = uuid.uuid4().hex
    refresh_token = _build_token(
        email,
        refresh_ttl,
        extra_claims={"jti": refresh_jti, "uid": user.id},
    )
    await _store_refresh_token(
        user_id=user.id,
        jti=refresh_jti,
        token_hash=_hash_token(refresh_token),
        ttl=refresh_ttl,
    )

    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "Bearer",
        "expiresIn": _get_access_exp_seconds(settings),
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "difficulty_level": user.difficulty_level,
        },
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
    refresh_ttl = _get_refresh_exp_seconds(settings)
    refresh_jti = uuid.uuid4().hex
    refresh_token = _build_token(
        email,
        refresh_ttl,
        extra_claims={"jti": refresh_jti, "uid": user.id},
    )
    await _store_refresh_token(
        user_id=user.id,
        jti=refresh_jti,
        token_hash=_hash_token(refresh_token),
        ttl=refresh_ttl,
    )
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "Bearer",
        "expiresIn": _get_access_exp_seconds(settings),
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "difficulty_level": user.difficulty_level,
        },
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
    jti = payload.get("jti")
    uid = payload.get("uid")
    if not email or not jti or uid is None:
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
    try:
        uid_int = int(uid)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )
    if user.id != uid_int:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    client = await _require_redis()
    token_key = f"auth:rt:{jti}"
    user_key = f"auth:rt:uid:{user.id}"
    stored_hash = await client.get(token_key)
    incoming_hash = _hash_token(refresh_token)
    if not stored_hash or stored_hash != incoming_hash:
        # Possible reuse or token store mismatch: revoke all refresh tokens
        await _revoke_user_refresh_tokens(user.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected",
        )

    access_token = _build_token(email, _get_access_exp_seconds(settings))
    refresh_ttl = _get_refresh_exp_seconds(settings)
    new_refresh_jti = uuid.uuid4().hex
    new_refresh_token = _build_token(
        email,
        refresh_ttl,
        extra_claims={"jti": new_refresh_jti, "uid": user.id},
    )
    async with client.pipeline(transaction=True) as pipe:
        pipe.delete(token_key)
        pipe.srem(user_key, jti)
        pipe.setex(f"auth:rt:{new_refresh_jti}", refresh_ttl, _hash_token(new_refresh_token))
        pipe.sadd(user_key, new_refresh_jti)
        pipe.expire(user_key, refresh_ttl)
        await pipe.execute()
    return {
        "accessToken": access_token,
        "refreshToken": new_refresh_token,
        "tokenType": "Bearer",
        "expiresIn": _get_access_exp_seconds(settings),
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "difficulty_level": user.difficulty_level,
        },
    }
