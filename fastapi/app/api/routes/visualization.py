"""시각화 JSON 및 피드백 API 엔드포인트."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.limiter import limiter

logger = logging.getLogger("narrative.visualization")

router = APIRouter(prefix="/tutor", tags=["visualization"])


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
