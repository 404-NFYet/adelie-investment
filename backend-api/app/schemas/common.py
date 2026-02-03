"""Common schemas used across the API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str
    code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
