"""Common schemas used across the API."""

from datetime import datetime
from typing import Optional, Generic, TypeVar, Literal, Any

from pydantic import BaseModel

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str
    code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()


class ApiResponse(BaseModel, Generic[T]):
    """Global API response envelope."""

    status: Literal["success", "error"]
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[dict[str, Any]] = None
