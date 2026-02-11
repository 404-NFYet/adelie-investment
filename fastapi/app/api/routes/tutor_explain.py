"""용어 설명 API 엔드포인트."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.glossary import Glossary
from app.services import get_redis_cache

logger = logging.getLogger("narrative_api.tutor_explain")

router = APIRouter(prefix="/tutor", tags=["AI Tutor - Explain"])


async def _get_term_explanation_from_llm(term: str, difficulty: str) -> str:
    """LLM으로 용어 설명 생성."""
    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    client = AsyncOpenAI(api_key=api_key)
    difficulty_context = {
        "beginner": "주식 초보자도 이해할 수 있도록 아주 쉽게, 일상적인 비유를 사용해서",
        "elementary": "기본적인 투자 용어를 아는 사람에게",
        "intermediate": "투자 경험이 있는 중급자에게",
    }
    context = difficulty_context.get(difficulty, difficulty_context["beginner"])

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"주식/금융 용어를 {context} 설명하는 튜터입니다. 3-4문장으로 간결하게 설명해주세요."},
            {"role": "user", "content": f"'{term}'이(가) 무엇인지 설명해주세요."},
        ],
        max_tokens=300,
    )

    if not response.choices:
        return "설명을 생성할 수 없습니다."
    return response.choices[0].message.content


@router.get("/explain/{term}")
@limiter.limit("20/minute")
async def explain_term(
    request: Request,
    term: str,
    difficulty: str = Query("beginner", description="Difficulty: beginner, elementary, intermediate"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """AI 기반 용어 설명 (Redis 캐싱 포함)."""
    if len(term) > 50:
        raise HTTPException(status_code=400, detail="용어는 50자 이내로 입력해주세요.")

    cache = await get_redis_cache()
    cached = await cache.get_term_explanation(term, difficulty)
    if cached:
        return {"term": term, "difficulty": difficulty, "explanation": cached, "cached": True}

    result = await db.execute(select(Glossary).where(Glossary.term.ilike(f"%{term}%")))
    glossary_item = result.scalar_one_or_none()

    if glossary_item:
        explanation = glossary_item.definition_full or glossary_item.definition_short
        await cache.set_term_explanation(term, explanation, difficulty)
        return {"term": term, "difficulty": difficulty, "explanation": explanation, "source": "glossary", "cached": False}

    try:
        explanation = await _get_term_explanation_from_llm(term, difficulty)
        await cache.set_term_explanation(term, explanation, difficulty)
        return {"term": term, "difficulty": difficulty, "explanation": explanation, "source": "ai", "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
