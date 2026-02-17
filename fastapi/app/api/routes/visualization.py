"""시각화 및 피드백 API 엔드포인트."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.limiter import limiter
from app.services.code_executor import get_executor

logger = logging.getLogger("narrative_api.visualization")

# 시각화 도구 임포트
try:
    from chatbot.tools.visualization_tool import _generate_with_claude, _generate_with_openai
    _VIZ_AVAILABLE = True
except ImportError:
    _VIZ_AVAILABLE = False

router = APIRouter(prefix="/tutor", tags=["visualization"])


@router.post("/visualize")
@limiter.limit("5/minute")
async def generate_chart(request: Request):
    """시각화 생성 엔드포인트 (rate limit: 5/분)."""
    if not _VIZ_AVAILABLE:
        raise HTTPException(status_code=500, detail="시각화 모듈을 불러올 수 없습니다.")

    body = await request.json()
    description = body.get("description", "")
    data_context = body.get("data_context", "")
    if not description:
        raise HTTPException(status_code=400, detail="description이 필요합니다.")
    if len(description) > 500:
        raise HTTPException(status_code=400, detail="시각화 설명은 500자 이내로 입력해주세요.")
    if len(data_context) > 5000:
        data_context = data_context[:5000]

    code = _generate_with_claude(description, data_context)
    if not code:
        code = _generate_with_openai(description, data_context)
    if not code:
        return {"success": False, "error": "코드 생성 실패"}

    executor = get_executor()
    result = await executor.execute(code)
    return {
        "success": result.success,
        "html": result.output_html,
        "error": result.error,
        "execution_time_ms": result.execution_time_ms,
    }


@router.post("/feedback")
async def submit_feedback(request: Request) -> dict:
    """LangSmith 피드백 전송."""
    body = await request.json()
    run_id = body.get("run_id")
    score = body.get("score", 0)

    if not run_id:
        raise HTTPException(status_code=400, detail="run_id가 필요합니다.")

    try:
        from langsmith import Client as LangSmithClient
        ls_client = LangSmithClient()
        ls_client.create_feedback(run_id=run_id, key="user-score", score=score)
        return {"success": True}
    except ImportError:
        logger.warning("langsmith 패키지가 설치되지 않았습니다.")
        return {"success": False, "reason": "langsmith not installed"}
    except Exception as e:
        logger.warning("LangSmith 피드백 전송 실패: %s", e)
        return {"success": False, "reason": str(e)}
