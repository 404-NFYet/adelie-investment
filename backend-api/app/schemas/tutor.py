"""AI Tutor related schemas."""

from typing import Literal, Optional

from pydantic import BaseModel


class TutorChatRequest(BaseModel):
    """Request for AI Tutor chat."""
    
    session_id: Optional[str] = None
    message: str
    context_type: Optional[Literal["briefing", "case", "comparison", "glossary"]] = None
    context_id: Optional[int] = None
    difficulty: str = "beginner"


class TutorChatEvent(BaseModel):
    """SSE event for AI Tutor chat."""
    
    type: Literal["thinking", "tool_call", "text_delta", "done", "error"]
    content: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[dict] = None
    session_id: Optional[str] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None
