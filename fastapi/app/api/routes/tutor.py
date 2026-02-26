"""AI Tutor API routes with Redis caching for term explanations."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

logger = logging.getLogger("narrative.tutor")

from app.core.auth import get_current_user_optional
from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.tutor import TutorSession, TutorMessage
from app.models.glossary import Glossary
from app.schemas.tutor import TutorChatRequest, TutorChatEvent
from app.services import get_redis_cache
from chatbot.services.tutor_engine import generate_tutor_response_stream

router = APIRouter(prefix="/tutor", tags=["AI tutor"])


async def get_term_explanation_from_llm(term: str, difficulty: str) -> str:
    """Generate term explanation using LLM."""
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
            {
                "role": "system",
                "content": f"주식/금융 용어를 {context} 설명하는 튜터입니다. 3-4문장으로 간결하게 설명해주세요."
            },
            {
                "role": "user",
                "content": f"'{term}'이(가) 무엇인지 설명해주세요."
            }
        ],
        max_tokens=300,
    )
    
    return response.choices[0].message.content


@router.get("/explain/{term}")
async def explain_term(
    term: str,
    difficulty: str = Query("beginner", description="Difficulty: beginner, elementary, intermediate"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get AI-generated explanation for a term with Redis caching.
    
    - **term**: The term to explain
    - **difficulty**: Explanation difficulty level
    
    Returns cached explanation if available (TTL: 24h).
    """
    # Check Redis cache first
    cache = await get_redis_cache()
    cached = await cache.get_term_explanation(term, difficulty)
    if cached:
        return {
            "term": term,
            "difficulty": difficulty,
            "explanation": cached,
            "cached": True,
        }
    
    # Check glossary database
    result = await db.execute(
        select(Glossary).where(
            Glossary.term.ilike(f"%{term}%"),
            Glossary.difficulty == difficulty,
        )
    )
    glossary_item = result.scalar_one_or_none()
    if not glossary_item:
        result = await db.execute(
            select(Glossary).where(Glossary.term.ilike(f"%{term}%"))
        )
        glossary_item = result.scalar_one_or_none()
    
    if glossary_item:
        explanation = glossary_item.definition_full or glossary_item.definition_short
        # Cache glossary explanation
        await cache.set_term_explanation(term, explanation, difficulty)
        return {
            "term": term,
            "difficulty": difficulty,
            "explanation": explanation,
            "source": "glossary",
            "cached": False,
        }
    
    # Generate from LLM
    try:
        explanation = await get_term_explanation_from_llm(term, difficulty)
        # Cache the LLM explanation
        await cache.set_term_explanation(term, explanation, difficulty)
        return {
            "term": term,
            "difficulty": difficulty,
            "explanation": explanation,
            "source": "ai",
            "cached": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/chat")
@limiter.limit("10/minute")
async def tutor_chat(
    request: Request,
    chat_request: TutorChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
) -> StreamingResponse:
    """AI Tutor chat endpoint with SSE streaming."""
    return StreamingResponse(
        generate_tutor_response_stream(chat_request, db, request, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


