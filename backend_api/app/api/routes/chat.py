"""Chat API - 용어 설명 등."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ai_pipeline_service import get_ai_pipeline_service

router = APIRouter(prefix="/chat", tags=["Chat"])


class ExplainRequest(BaseModel):
    term: str
    context: str = ""


class ExplainResponse(BaseModel):
    term: str
    explanation: str


@router.post("/explain", response_model=ExplainResponse)
async def explain_term(request: ExplainRequest, db: AsyncSession = Depends(get_db)):
    """용어 설명 API - 선택한 용어를 쉽게 설명합니다."""
    ai_service = get_ai_pipeline_service()
    
    prompt = f"""당신은 금융 교육 전문가입니다. 
다음 금융 용어를 초보자가 이해할 수 있도록 쉽게 설명해주세요.
일상적인 비유를 사용하고, 2-3문장으로 간결하게 답변하세요.

용어: {request.term}
맥락: {request.context if request.context else "일반적인 금융 맥락"}
"""
    
    try:
        explanation = await ai_service.call_openai(
            messages=[{"role": "user", "content": prompt}],
            temp=0.5,
            max_t=500,
        )
        return ExplainResponse(term=request.term, explanation=explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to explain term: {str(e)}")

