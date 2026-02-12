"""JWT 인증 의존성 모듈."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

logger = logging.getLogger("narrative_api.auth")

security = HTTPBearer(auto_error=False)


def _get_jwt_key(secret: str) -> bytes:
    """Spring Boot JwtService와 동일한 키 바이트 생성."""
    key_bytes = secret.encode("utf-8")
    if len(key_bytes) < 32:
        key_bytes = key_bytes + b"\x00" * (32 - len(key_bytes))
    return key_bytes


def _decode_token(token: str) -> dict:
    """JWT 토큰 디코딩 공통 로직."""
    settings = get_settings()
    if not settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT not configured",
        )
    try:
        return jwt.decode(
            token,
            _get_jwt_key(settings.JWT_SECRET),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token error: {e}, token_prefix: {token[:50] if token else 'None'}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def _resolve_user_from_payload(payload: dict, db: AsyncSession) -> dict:
    """JWT payload의 sub(email)로 DB에서 사용자 정보를 조회하여 반환."""
    from app.models.user import User

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no subject",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("JWT 유효하지만 DB에 사용자 없음: %s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return {"id": user.id, "email": user.email, "username": user.username}


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    """선택적 인증 - 토큰이 있으면 검증 후 사용자 정보 반환, 없으면 None."""
    if not credentials:
        return None

    settings = get_settings()
    if not settings.JWT_SECRET:
        return None

    payload = _decode_token(credentials.credentials)
    return await _resolve_user_from_payload(payload, db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """필수 인증 - 토큰 필수. DB에서 사용자 정보 조회 후 dict 반환.

    Returns:
        {"id": int, "email": str, "username": str}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = _decode_token(credentials.credentials)
    return await _resolve_user_from_payload(payload, db)
