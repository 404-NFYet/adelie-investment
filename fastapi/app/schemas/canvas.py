"""Canvas Engine schemas — AI 선제 제시 + CTA 기반 분석 시스템."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class CanvasAnalyzeRequest(BaseModel):
    """POST /api/v1/canvas/analyze — SSE 스트리밍 분석 요청."""
    session_id: Optional[str] = None
    message: str
    mode: Literal["home", "stock", "education"] = "home"
    context_type: Optional[Literal["briefing", "case", "comparison", "glossary"]] = None
    context_id: Optional[int] = None
    context_text: Optional[str] = None  # JSON string with context envelope
    difficulty: str = "beginner"
    use_web_search: bool = False
    cta_source: Optional[str] = None  # 이전 CTA에서 진입한 경우 CTA ID
    turn_index: int = 0  # 현재 턴 인덱스


class CanvasPrecomputedRequest(BaseModel):
    """GET /api/v1/canvas/precomputed 쿼리 파라미터."""
    mode: Literal["home", "stock", "education"] = "home"
    date: Optional[str] = None  # YYYY-MM-DD, default=today


class CanvasPrecomputedResponse(BaseModel):
    """사전 연산 캐시 응답."""
    cached: bool = False
    date: str
    mode: str
    analysis_md: Optional[str] = None
    ctas: list[dict[str, Any]] = Field(default_factory=list)
    chart_json: Optional[dict[str, Any]] = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: Optional[str] = None


class QuickQARequest(BaseModel):
    """POST /api/v1/canvas/quick-qa — 드래그 선택 즉석 설명."""
    selected_text: str = Field(..., min_length=2, max_length=500)
    canvas_context_summary: Optional[str] = None  # 현재 Canvas 분석 요약
    session_id: Optional[str] = None


class QuickQAResponse(BaseModel):
    """Quick QA 응답 (비스트리밍)."""
    explanation: str
    stock_info: Optional[dict[str, Any]] = None  # 종목 감지 시 enriched 데이터
    sources: list[dict[str, Any]] = Field(default_factory=list)
    detected_stock: Optional[str] = None  # 감지된 종목명


class CTAFeedbackRequest(BaseModel):
    """POST /api/v1/canvas/cta-feedback — CTA 피드백 기록."""
    session_id: str
    turn_index: int
    cta_id: str
    action: Literal["clicked", "ignored"]
    time_to_click_ms: Optional[int] = None


class CTAFeedbackResponse(BaseModel):
    """CTA 피드백 응답."""
    status: str = "ok"


class CanvasSSEEvent(BaseModel):
    """Canvas SSE 이벤트 구조."""
    type: Literal[
        "phase", "text_delta", "visualization", "cta",
        "sources", "done", "error", "guardrail_notice"
    ]
    content: Optional[str] = None
    phase: Optional[str] = None  # thinking, context_collection, analyzing, chart_generation
    chart_json: Optional[dict[str, Any]] = None
    ctas: Optional[list[dict[str, Any]]] = None
    sources: Optional[list[dict[str, Any]]] = None
    session_id: Optional[str] = None
    total_tokens: Optional[int] = None
    model: Optional[str] = None
    guardrail_decision: Optional[str] = None
    error: Optional[str] = None
