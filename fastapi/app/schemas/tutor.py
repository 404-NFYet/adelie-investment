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

    decision: Literal["inline_action", "inline_reply", "open_canvas", "confirm_action"]
    action_id: Optional[str] = None
    action_params: Optional[dict] = None
    inline_text: Optional[str] = None
    canvas_prompt: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    confirmation_required: bool = False
    confirmation_message: Optional[str] = None
    risk_level: Literal["low", "medium", "high"] = "low"


class CtaButton(BaseModel):
    """CTA 버튼 정의."""
    label: str
    action: str
    prompt: Optional[str] = None


class TodoItem(BaseModel):
    """To-do 항목 정의."""
    id: str
    title: str
    status: Literal["pending", "in_progress", "completed", "error"] = "pending"


class TutorChatEvent(BaseModel):
    """SSE event for AI Tutor chat."""

    type: Literal["thinking", "tool_call", "guardrail_notice", "text_delta", "visualization", "ui_action", "todo_update", "done", "error"]
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
    guardrail_decision: Optional[str] = None
    guardrail_mode: Optional[str] = None
    error: Optional[str] = None
    cta_buttons: Optional[list[CtaButton]] = None
    todo_list: Optional[list[TodoItem]] = None
