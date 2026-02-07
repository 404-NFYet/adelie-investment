"""AI Tutor API routes with Redis caching for term explanations."""

import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

logger = logging.getLogger("narrative_api.tutor")

from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.tutor import TutorSession, TutorMessage
from app.models.glossary import Glossary
from app.schemas.tutor import TutorChatRequest, TutorChatEvent
from app.services import get_redis_cache

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])


def get_difficulty_prompt(difficulty: str) -> str:
    """Get system prompt based on difficulty level."""
    prompts = {
        "beginner": (
            "당신은 친절한 주식 투자 튜터입니다. "
            "주식 초보자에게 설명하듯이 아주 쉽게, 일상적인 비유를 사용해서 답변해주세요. "
            "전문 용어는 최대한 피하고, 사용해야 할 때는 간단히 설명해주세요. "
            "답변은 짧고 명확하게 해주세요."
        ),
        "elementary": (
            "당신은 주식 투자 튜터입니다. "
            "기본적인 투자 용어를 알고 있는 초급자에게 설명하듯이 답변해주세요. "
            "주요 개념은 설명하되, 너무 상세한 기술적 분석은 피해주세요."
        ),
        "intermediate": (
            "당신은 주식 투자 전문가입니다. "
            "어느 정도 투자 경험이 있는 중급자에게 설명하듯이 답변해주세요. "
            "기술적 분석, 재무제표 분석 등 심화된 내용도 포함해도 됩니다."
        ),
    }
    return prompts.get(difficulty, prompts["beginner"])


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


async def generate_tutor_response(
    request: TutorChatRequest,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Generate streaming response for AI tutor."""
    
    session_id = request.session_id or str(uuid.uuid4())
    
    yield f"event: step\ndata: {json.dumps({'type': 'thinking', 'content': '질문을 분석하고 있습니다...'})}\n\n"
    
    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'OpenAI API key not configured'})}\n\n"
        return
    
    # 컨텍스트 주입 (사용자가 보고 있는 페이지 기반)
    page_context = ""
    if request.context_type and request.context_id:
        try:
            if request.context_type == "briefing":
                ctx_result = await db.execute(text(
                    "SELECT market_summary, top_keywords FROM daily_briefings WHERE id = :id"
                ), {"id": request.context_id})
                ctx_row = ctx_result.fetchone()
                if ctx_row:
                    page_context = f"\n\n[현재 보고 있는 브리핑]\n시장 요약: {ctx_row[0]}\n키워드: {ctx_row[1]}"
            elif request.context_type == "case":
                ctx_result = await db.execute(text(
                    "SELECT title, summary FROM historical_cases WHERE id = :id"
                ), {"id": request.context_id})
                ctx_row = ctx_result.fetchone()
                if ctx_row:
                    page_context = f"\n\n[현재 보고 있는 사례]\n제목: {ctx_row[0]}\n요약: {ctx_row[1]}"
        except Exception:
            pass  # 컨텍스트 로드 실패해도 대화는 계속

    system_prompt = get_difficulty_prompt(request.difficulty)
    if page_context:
        system_prompt += page_context

    # 용어 설명은 LLM이 응답 내에서 자연스럽게 처리하도록 프롬프트에 지시
    system_prompt += "\n\n투자 용어가 나오면 괄호 안에 쉬운 설명을 덧붙여주세요. 예: PER(주가수익비율, 주가를 이익으로 나눈 값)."
    
    # Load previous messages for multi-turn
    prev_msgs = []
    if request.session_id:
        try:
            existing_session = await db.execute(
                select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
            )
            session_obj = existing_session.scalar_one_or_none()
            if session_obj:
                prev_result = await db.execute(
                    select(TutorMessage)
                    .where(TutorMessage.session_id == session_obj.id)
                    .order_by(TutorMessage.created_at)
                    .limit(20)
                )
                for msg in prev_result.scalars():
                    prev_msgs.append({"role": msg.role, "content": msg.content})
        except Exception as e:
            logger.warning("Failed to load previous messages: %s", e)
    
    messages = [
        {"role": "system", "content": system_prompt},
        *prev_msgs,
        {"role": "user", "content": request.message},
    ]
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            stream=True,
        )
        
        total_tokens = 0
        full_response = ""
        
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"event: text_delta\ndata: {json.dumps({'content': content})}\n\n"
            
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
        
        try:
            session = TutorSession(
                session_uuid=uuid.UUID(session_id) if session_id else uuid.uuid4(),
                context_type=request.context_type,
                context_id=request.context_id,
            )
            db.add(session)
            await db.flush()
            
            user_msg = TutorMessage(
                session_id=session.id,
                role="user",
                content=request.message,
            )
            db.add(user_msg)
            
            assistant_msg = TutorMessage(
                session_id=session.id,
                role="assistant",
                content=full_response,
            )
            db.add(assistant_msg)
            
            await db.commit()
        except Exception as e:
            logger.warning("Failed to save tutor session: %s", e)
        
        yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'total_tokens': total_tokens})}\n\n"
        
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@router.post("/chat")
@limiter.limit("10/minute")
async def tutor_chat(
    request: Request,
    chat_request: TutorChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """AI Tutor chat endpoint with SSE streaming."""
    return StreamingResponse(
        generate_tutor_response(chat_request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
