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

logger = logging.getLogger("narrative_api.tutor")

from app.core.auth import get_current_user_optional
from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.tutor import TutorSession, TutorMessage
from app.models.glossary import Glossary
from app.schemas.tutor import TutorChatRequest, TutorChatEvent
from app.services import get_redis_cache
from app.services.tutor_engine import (
    _collect_glossary_context,
    _collect_db_context,
    _collect_stock_context,
    get_difficulty_prompt,
)
from app.services.stock_resolver import detect_stock_codes

router = APIRouter(prefix="/tutor", tags=["AI tutor"])


async def get_term_explanation_from_llm(term: str, difficulty: str) -> str:
    """Generate term explanation using LLM."""
    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    client = AsyncOpenAI(api_key=api_key, timeout=30.0)
    
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
    http_request: Request,
    current_user: Optional[dict] = None,
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

    # 포트폴리오 컨텍스트 주입 (개인화된 조언용)
    user_id = current_user["id"] if current_user else None
    if user_id:
        try:
            portfolio_result = await db.execute(text(
                "SELECT current_cash, initial_cash FROM user_portfolios WHERE user_id = :uid LIMIT 1"
            ), {"uid": user_id})
            pf_row = portfolio_result.fetchone()
            if pf_row:
                holdings_result = await db.execute(text(
                    "SELECT stock_name, quantity, avg_buy_price FROM portfolio_holdings WHERE portfolio_id = (SELECT id FROM user_portfolios WHERE user_id = :uid LIMIT 1)"
                ), {"uid": user_id})
                holdings = holdings_result.fetchall()
                holdings_text = ", ".join(f"{h[0]} {h[1]}주(평균 {int(h[2]):,}원)" for h in holdings) if holdings else "없음"
                page_context += f"\n\n[사용자 포트폴리오]\n보유 현금: {int(pf_row[0]):,}원 / 초기 자본: {int(pf_row[1]):,}원\n보유 종목: {holdings_text}"
        except Exception:
            pass

    # 출처 수집 (glossary, DB 사례/리포트, 주가/기업관계)
    sources = []
    extra_context = ""
    try:
        glossary_context, glossary_sources = await _collect_glossary_context(request.message, db)
        db_context, db_sources = await _collect_db_context(request.message, db)
        detected_stocks = detect_stock_codes(request.message)
        stock_context, chart_data, stock_sources = await _collect_stock_context(
            request.message, detected_stocks, db
        )
        sources = glossary_sources + db_sources + stock_sources
        if glossary_context:
            extra_context += f"\n\n참고할 용어 정의:{glossary_context}"
        if db_context:
            extra_context += f"\n\n참고할 내부 데이터:{db_context}"
        if stock_context:
            extra_context += f"\n\n참고할 종목 데이터:{stock_context}"
    except Exception as e:
        logger.warning("출처 수집 실패 (무시): %s", e)

    system_prompt = get_difficulty_prompt(request.difficulty)
    if page_context:
        system_prompt += page_context
    if extra_context:
        system_prompt += extra_context

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
        client = AsyncOpenAI(api_key=api_key, timeout=30.0)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            stream=True,
        )
        
        total_tokens = 0
        full_response = ""
        stream_start = time.monotonic()
        chunk_count = 0
        
        async for chunk in response:
            chunk_count += 1

            # 매 10번째 청크마다 연결 상태 및 타임아웃 확인
            if chunk_count % 10 == 0:
                if time.monotonic() - stream_start > 300:
                    logger.warning("SSE 스트리밍 타임아웃 (300초 초과)")
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'Stream timeout'})}\n\n"
                    break
                if await http_request.is_disconnected():
                    logger.info("클라이언트 연결 해제 감지, 스트리밍 중단")
                    break

            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"event: text_delta\ndata: {json.dumps({'content': content})}\n\n"
            
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
        
        try:
            # 기존 세션이 있으면 재사용, 없으면 생성
            session_obj = None
            if request.session_id:
                existing = await db.execute(
                    select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
                )
                session_obj = existing.scalar_one_or_none()

            if not session_obj:
                session_obj = TutorSession(
                    session_uuid=uuid.UUID(session_id) if session_id else uuid.uuid4(),
                    context_type=request.context_type,
                    context_id=request.context_id,
                    title=request.message[:50],
                    message_count=0,
                )
                db.add(session_obj)
                await db.flush()

            user_msg = TutorMessage(
                session_id=session_obj.id,
                role="user",
                content=request.message,
                message_type="text",
            )
            db.add(user_msg)

            assistant_msg = TutorMessage(
                session_id=session_obj.id,
                role="assistant",
                content=full_response,
                message_type="text",
            )
            db.add(assistant_msg)

            # 세션 메타데이터 업데이트
            session_obj.message_count = (session_obj.message_count or 0) + 2
            session_obj.last_message_at = datetime.utcnow()

            await db.commit()
        except Exception as e:
            logger.warning("Failed to save tutor session: %s", e)
        
        # 시각화 자동 감지: 사용자 메시지나 응답에 차트 키워드가 있으면 Plotly 생성
        viz_keywords = ["차트", "그래프", "시각화", "그려", "보여줘", "chart", "graph"]
        should_viz = any(kw in request.message.lower() for kw in viz_keywords)

        if should_viz and full_response:
            try:
                viz_prompt = (
                    "다음 내용을 Plotly.js 차트 JSON으로 변환하세요.\n"
                    "반드시 아래 형식의 JSON만 반환하세요 (마크다운 코드블록 없이):\n"
                    '{"data": [트레이스 객체들], "layout": {레이아웃 옵션}}\n\n'
                    f"내용:\n{full_response[:500]}"
                )
                viz_response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            "당신은 Plotly.js 차트 전문가입니다. "
                            "주어진 내용을 시각화하는 Plotly JSON config를 생성하세요. "
                            '반드시 {"data": [...], "layout": {...}} 형식의 JSON만 반환하세요. '
                            "디자인 규칙: 주요 색상 #FF6B00(주황), 보조 색상 #FF8C33, "
                            "배경 투명(transparent), 한글 레이블 사용. "
                            "마크다운 코드블록(```)으로 감싸지 마세요. 오직 JSON만 반환하세요."
                        )},
                        {"role": "user", "content": viz_prompt},
                    ],
                    max_tokens=2000,
                )
                json_content = viz_response.choices[0].message.content.strip()
                # ```json 코드 블록 제거 (LLM이 감쌀 수 있음)
                if json_content.startswith("```"):
                    json_content = json_content.split("```", 2)[1]
                    if json_content.startswith("json"):
                        json_content = json_content[4:]
                    if "```" in json_content:
                        json_content = json_content.rsplit("```", 1)[0]
                    json_content = json_content.strip()
                chart_data = json.loads(json_content)
                if "data" in chart_data and isinstance(chart_data["data"], list):
                    yield f"event: visualization\ndata: {json.dumps({'type': 'visualization', 'format': 'json', 'chartData': chart_data})}\n\n"
            except Exception as viz_err:
                logger.warning(f"시각화 생성 실패: {viz_err}")

        done_data = {'session_id': session_id, 'total_tokens': total_tokens}
        if sources:
            done_data['type'] = 'done'
            done_data['sources'] = sources
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
        
    except asyncio.TimeoutError:
        logger.warning("OpenAI API 호출 타임아웃")
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'AI 응답 시간 초과'})}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    finally:
        # DB 세션 및 리소스 정리
        try:
            await db.close()
        except Exception:
            pass
        logger.debug("SSE 스트리밍 리소스 정리 완료 (session=%s)", session_id)


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
        generate_tutor_response(chat_request, db, request, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
