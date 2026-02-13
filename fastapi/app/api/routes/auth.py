"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.services.auth_service import login_user, refresh_tokens, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=AuthResponse)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    return await register_user(
        db,
        email=payload.email,
        password=payload.password,
        username=payload.username,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    return await login_user(db, email=payload.email, password=payload.password)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    if not payload.refreshToken or not payload.refreshToken.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refreshToken is required",
        )
    return await refresh_tokens(db, refresh_token=payload.refreshToken)


@router.post("/logout")
async def logout(
    user: dict | None = Depends(get_current_user_optional),
) -> dict:
    # Stateless JWT: client discards token. Keep endpoint for compatibility.
    if user:
        pass
    return {}


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
