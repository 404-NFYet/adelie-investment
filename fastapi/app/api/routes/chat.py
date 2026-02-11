"""용어 설명 API - /api/v1/chat/*"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ExplainRequest(BaseModel):
    term: str
    context: str = ""


class ExplainResponse(BaseModel):
    term: str
    explanation: str


@router.post("/explain", response_model=ExplainResponse)
async def explain_term(req: ExplainRequest, current_user=Depends(get_current_user)):
    """용어 설명 API (OpenAI gpt-5-mini)"""
    from app.services.llm_client import LLMClient, extract_openai_content

    svc = LLMClient()

    messages = [
        {
            "role": "system",
            "content": "당신은 한국 주식시장 용어를 초보자에게 쉽게 설명해주는 전문가입니다. 한국어로 300자 이내로 설명하세요.",
        },
        {
            "role": "user",
            "content": f"'{req.term}' 용어를 설명해주세요."
            + (f" 맥락: {req.context}" if req.context else ""),
        },
    ]

    result = await svc.call_openai(messages, model="gpt-5-mini", max_tokens=500)
    explanation = extract_openai_content(result, fallback=f"{req.term}에 대한 설명을 생성하지 못했습니다.")
    return ExplainResponse(term=req.term, explanation=explanation)
