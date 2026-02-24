"""Canvas Engine API routes (deprecated — /api/v1/agent/* 사용 권장).

기존 /canvas/* 엔드포인트는 하위 호환성을 위해 유지한다.
신규 클라이언트는 /api/v1/agent/* 경로를 사용해야 한다.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.schemas.canvas import (
    CanvasAnalyzeRequest,
    CanvasPrecomputedResponse,
    CTAFeedbackRequest,
    CTAFeedbackResponse,
    QuickQARequest,
    QuickQAResponse,
)

logger = logging.getLogger("narrative_api.canvas")

router = APIRouter(prefix="/canvas", tags=["canvas"])


def _sse_event(event_type: str, data: dict) -> str:
    """SSE 이벤트 포맷."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/analyze", deprecated=True)
async def analyze_canvas(
    request: CanvasAnalyzeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    """Canvas 분석 SSE 스트리밍 엔드포인트.

    AI가 컨텍스트를 수집하고 분석을 스트리밍하며,
    완료 시 다음 CTA를 생성하여 전달합니다.
    """
    from app.services.canvas.analyzer import run_canvas_analysis

    async def event_generator():
        try:
            async for event_type, payload in run_canvas_analysis(
                db=db,
                request=request,
                user=user,
                disconnect_check=http_request.is_disconnected,
            ):
                yield _sse_event(event_type, payload)
        except Exception as e:
            logger.exception("Canvas analysis error: %s", e)
            yield _sse_event("error", {"message": "분석 중 오류가 발생했습니다."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/precomputed", response_model=CanvasPrecomputedResponse, deprecated=True)
async def get_precomputed(
    mode: str = Query("home", regex="^(home|stock|education)$"),
    date: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$"),
    user=Depends(get_current_user_optional),
):
    """사전 연산된 Canvas 데이터 조회 (Redis 캐시)."""
    from app.services.canvas.precompute import get_precomputed_canvas

    result = await get_precomputed_canvas(mode=mode, date=date)
    return result


@router.post("/quick-qa", response_model=QuickQAResponse, deprecated=True)
async def quick_qa(
    request: QuickQARequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    """드래그 선택 텍스트 즉석 설명 (비스트리밍)."""
    from app.services.canvas.quick_qa import handle_quick_qa

    return await handle_quick_qa(
        db=db,
        selected_text=request.selected_text,
        canvas_context_summary=request.canvas_context_summary,
        session_id=request.session_id,
    )


@router.post("/cta-feedback", response_model=CTAFeedbackResponse, deprecated=True)
async def cta_feedback(
    request: CTAFeedbackRequest,
    user=Depends(get_current_user_optional),
):
    """CTA 피드백 기록 (LangSmith 전송)."""
    from app.services.canvas.cta_generator import record_cta_feedback

    await record_cta_feedback(
        session_id=request.session_id,
        turn_index=request.turn_index,
        cta_id=request.cta_id,
        action=request.action,
        time_to_click_ms=request.time_to_click_ms,
    )
    return CTAFeedbackResponse(status="ok")
