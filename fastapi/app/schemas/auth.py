"""Authentication related schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Register request payload."""

    email: EmailStr
    password: str = Field(min_length=8)
    username: Optional[str] = Field(default=None, min_length=2, max_length=10)
    difficulty_level: Optional[str] = Field(
        default="beginner",
        description="beginner, elementary, intermediate",
    )

class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refreshToken: str


class AuthUserInfo(BaseModel):
    """User info included in auth response."""

    id: int
    email: EmailStr
    username: str
    difficulty_level: str


class AuthResponse(BaseModel):
    """Authentication response."""

    accessToken: str
    refreshToken: str
    tokenType: str
    expiresIn: int
    user: AuthUserInfo
