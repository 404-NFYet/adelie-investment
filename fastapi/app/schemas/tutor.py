"""AI Tutor related schemas."""

from typing import Literal, Optional

from pydantic import BaseModel


class TutorChatRequest(BaseModel):
    """Request for AI Tutor chat."""
    
    session_id: Optional[str] = None
    message: str
    context_type: Optional[Literal["briefing", "case", "comparison", "glossary"]] = None
    context_id: Optional[int] = None
    context_text: Optional[str] = None
    difficulty: str = "beginner"


class TutorChatEvent(BaseModel):
    """SSE event for AI Tutor chat."""

    type: Literal["thinking", "tool_call", "text_delta", "visualization", "ui_action", "done", "error"]
    content: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[dict] = None
    session_id: Optional[str] = None
    total_tokens: Optional[int] = None
    sources: Optional[list[dict]] = None
    actions: Optional[list[dict]] = None
    model: Optional[str] = None
    error: Optional[str] = None
