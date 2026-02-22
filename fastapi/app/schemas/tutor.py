"""AI Tutor related schemas."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TutorChatRequest(BaseModel):
    """Request for AI Tutor chat."""

    session_id: Optional[str] = None
    message: str
    context_type: Optional[Literal["briefing", "case", "comparison", "glossary"]] = None
    context_id: Optional[int] = None
    context_text: Optional[str] = None
    difficulty: str = "beginner"
    use_web_search: bool = False
    response_mode: Literal["plain", "canvas_markdown"] = "plain"
    structured_extract: bool = False


class TutorRouteRequest(BaseModel):
    """Request for route decision between inline action/reply and canvas."""

    message: str
    mode: Literal["home", "stock", "education", "my", "agent"] = "home"
    context_text: Optional[str] = None
    ui_snapshot: Optional[dict] = None
    action_catalog: list[dict] = Field(default_factory=list)
    interaction_state: Optional[dict] = None


class TutorRouteResponse(BaseModel):
    """Route decision response for AgentDock."""

    decision: Literal["inline_action", "inline_reply", "open_canvas"]
    action_id: Optional[str] = None
    inline_text: Optional[str] = None
    canvas_prompt: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


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
    reasoning_effort: Optional[str] = None
    search_used: Optional[bool] = None
    response_mode: Optional[str] = None
    structured: Optional[dict[str, Any]] = None
    error: Optional[str] = None
