"""AI Tutor API routes with Redis caching for term explanations."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

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
from app.schemas.tutor import (
    TutorChatRequest,
    TutorChatEvent,
    TutorRouteRequest,
    TutorRouteResponse,
)
from app.services import get_redis_cache
from app.services.tutor_engine import (
    _collect_glossary_context,
    _collect_db_context,
    _collect_stock_context,
    get_difficulty_prompt,
)
from app.services.stock_resolver import detect_stock_codes
from app.services.guardrail import run_guardrail

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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_route_response(
    payload: dict,
    *,
    allowed_action_ids: list[str],
    confidence_threshold: float,
    fallback_prompt: str,
) -> TutorRouteResponse:
    decision = str(payload.get("decision") or "inline_reply").strip()
    if decision not in {"inline_action", "inline_reply", "open_canvas"}:
        decision = "inline_reply"

    confidence = max(0.0, min(1.0, _to_float(payload.get("confidence"), 0.0)))
    reason = str(payload.get("reason") or "router_default").strip()
    action_id = str(payload.get("action_id") or "").strip() or None
    inline_text = str(payload.get("inline_text") or "").strip() or None
    canvas_prompt = str(payload.get("canvas_prompt") or "").strip() or None

    if confidence < confidence_threshold:
        decision = "inline_reply"
        action_id = None
        if not inline_text:
            inline_text = "요청을 짧게 처리할게요. 필요하면 캔버스로 이어서 볼 수 있어요."
        reason = reason or "low_confidence"

    if decision == "inline_action":
        if not action_id or action_id not in allowed_action_ids:
            decision = "inline_reply"
            action_id = None
            inline_text = inline_text or "바로 실행 가능한 액션을 찾지 못했어요."
            reason = reason or "invalid_action_id"

    if decision == "open_canvas":
        canvas_prompt = canvas_prompt or fallback_prompt

    if decision == "inline_reply":
        inline_text = inline_text or "요청을 반영했어요. 더 깊게 보려면 캔버스로 이어갈 수 있어요."

    return TutorRouteResponse(
        decision=decision,  # type: ignore[arg-type]
        action_id=action_id,
        inline_text=inline_text,
        canvas_prompt=canvas_prompt,
        confidence=confidence,
        reason=reason or "ok",
    )


async def _route_with_llm(route_request: TutorRouteRequest) -> TutorRouteResponse:
    settings = get_settings()
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return TutorRouteResponse(
            decision="inline_reply",
            inline_text="현재는 인라인으로 안내할게요. 필요하면 캔버스로 이어갈 수 있어요.",
            canvas_prompt=route_request.message,
            confidence=0.0,
            reason="openai_key_missing",
        )

    action_catalog = route_request.action_catalog or []
    compact_actions = [
        {
            "id": str(item.get("id") or "").strip(),
            "label": str(item.get("label") or "").strip(),
            "risk": str(item.get("risk") or "").strip(),
            "description": str(item.get("description") or "").strip(),
        }
        for item in action_catalog
        if str(item.get("id") or "").strip()
    ]
    allowed_action_ids = [item["id"] for item in compact_actions]

    system_prompt = (
        "You are an action router for an investing app. "
        "Return JSON only with keys: decision, action_id, inline_text, canvas_prompt, confidence, reason. "
        "decision must be one of inline_action, inline_reply, open_canvas. "
        "Use inline_action only when one action_id from action_catalog can be safely executed now. "
        "Use open_canvas for analysis/deep explanation requests. "
        "Use inline_reply for short direct guidance. "
        "Never invent action_id outside action_catalog. "
        "confidence must be 0~1."
    )

    user_payload = {
        "message": route_request.message,
        "mode": route_request.mode,
        "context_text": route_request.context_text,
        "ui_snapshot": route_request.ui_snapshot,
        "interaction_state": route_request.interaction_state,
        "action_catalog": compact_actions,
    }

    client = AsyncOpenAI(api_key=api_key)
    route_model = settings.TUTOR_ROUTE_MODEL or "gpt-4o-mini"
    response = await client.chat.completions.create(
        model=route_model,
        temperature=0.1,
        max_tokens=280,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}

    return _normalize_route_response(
        parsed,
        allowed_action_ids=allowed_action_ids,
        confidence_threshold=settings.TUTOR_ROUTE_CONFIDENCE_THRESHOLD,
        fallback_prompt=route_request.message,
    )


def _normalize_reasoning_effort(value: str) -> str:
    effort = (value or "").strip().lower()
    if effort in {"minimal", "low", "medium", "high"}:
        return effort
    return ""


def _event_to_dict(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        try:
            dumped = event.model_dump()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            pass
    if hasattr(event, "to_dict"):
        try:
            dumped = event.to_dict()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            pass
    return {"type": getattr(event, "type", None)}


def _extract_usage_total(response_payload: dict[str, Any]) -> int:
    usage = response_payload.get("usage") or {}
    if isinstance(usage, dict):
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            return input_tokens + output_tokens
    return 0


def _extract_response_text(response_payload: dict[str, Any]) -> str:
    output = response_payload.get("output")
    if not isinstance(output, list):
        return ""

    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text:
                chunks.append(text)
    return "".join(chunks).strip()


def _extract_structured_from_markdown(markdown_text: str) -> Optional[dict[str, Any]]:
    text = (markdown_text or "").strip()
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    summary = ""
    for line in lines:
        cleaned = line.lstrip("#").strip()
        if cleaned:
            summary = cleaned
            break
    if not summary:
        summary = text[:200]

    key_points: list[str] = []
    suggested_actions: list[str] = []
    for line in lines:
        if line.startswith(("- ", "* ")):
            bullet = line[2:].strip()
        elif line[:2].isdigit() and line[1] == ".":
            bullet = line[2:].strip()
        else:
            bullet = ""

        if not bullet:
            continue

        if any(keyword in bullet for keyword in ["실행", "확인", "비교", "체크", "다음"]):
            suggested_actions.append(bullet)
        else:
            key_points.append(bullet)

    key_points = key_points[:5]
    suggested_actions = suggested_actions[:3]

    return {
        "summary": summary,
        "key_points": key_points,
        "suggested_actions": suggested_actions,
    }


@router.post("/route", response_model=TutorRouteResponse)
@limiter.limit("30/minute")
async def tutor_route(
    request: Request,
    route_request: TutorRouteRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
) -> TutorRouteResponse:
    """Route user prompt to inline action/reply or canvas transition."""
    _ = request
    _ = current_user
    try:
        return await _route_with_llm(route_request)
    except Exception as e:
        logger.warning("tutor route fallback: %s", e)
        return TutorRouteResponse(
            decision="inline_reply",
            inline_text="지금은 간단히 안내할게요. 자세한 답변은 캔버스로 이어볼 수 있어요.",
            canvas_prompt=route_request.message,
            confidence=0.0,
            reason="router_error",
        )


async def _collect_context(
    request: TutorChatRequest,
    db: AsyncSession,
    user_id: Optional[int],
) -> tuple[str, list, list, object]:
    """컨텍스트 수집 — 브리핑/사례/포트폴리오 쿼리 및 출처 수집."""
    page_context = ""

    # 프론트엔드에서 전달된 현재 스텝 텍스트 본문 (우선)
    if hasattr(request, "context_text") and request.context_text:
        page_context = (
            "\n\n[현재 학습/화면 문맥]\n"
            "사용자는 지금 애플리케이션 화면에서 아래의 내용을 직접 읽고 있는 중입니다:\n"
            f'"""\n{request.context_text}\n"""\n'
            "사용자가 질문을 할 때, 만약 사용자가 '이 화면', '방금 내용', '이 파트'와 같이 "
            "주어를 생략하더라도 반드시 위 문맥과 연관지어 자연스럽게 답변하세요."
        )
    elif request.context_type and request.context_id:
        # Fallback: context_text가 없는 경우 DB 기반 요약 사용
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
    chart_data = None
    detected_stocks = []
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

    return page_context, sources, detected_stocks, chart_data, extra_context


async def _build_llm_messages(
    request: TutorChatRequest,
    db: AsyncSession,
    page_context: str,
    extra_context: str,
) -> list:
    """LLM 메시지 배열 구성 — 시스템 프롬프트 + 이전 대화 + 현재 질문."""
    system_prompt = get_difficulty_prompt(request.difficulty)
    if page_context:
        system_prompt += page_context
    if extra_context:
        system_prompt += extra_context
    # 용어 설명은 LLM이 응답 내에서 자연스럽게 처리하도록 프롬프트에 지시
    system_prompt += "\n\n투자 용어가 나오면 괄호 안에 쉬운 설명을 덧붙여주세요. 예: PER(주가수익비율, 주가를 이익으로 나눈 값)."
    if request.response_mode == "canvas_markdown":
        system_prompt += (
            "\n\n응답 형식 규칙:\n"
            "- 반드시 Markdown으로 응답하세요.\n"
            "- 첫 문단에 핵심 요약 1~2문장을 먼저 제시하세요.\n"
            "- 핵심 포인트는 불릿 목록(3~5개)으로 정리하세요.\n"
            "- 필요한 경우 마지막에 '다음 액션' 섹션을 번호 목록으로 제시하세요.\n"
            "- 파이프(|) 같은 중간 메타 토큰이나 디버그 문자열은 출력하지 마세요.\n"
        )

    # 이전 대화 내역 로드 (멀티턴)
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

    return [
        {"role": "system", "content": system_prompt},
        *prev_msgs,
        {"role": "user", "content": request.message},
    ]


async def _save_tutor_session(
    db: AsyncSession,
    session_uuid_str: str,
    user_id: Optional[int],
    request: TutorChatRequest,
    assistant_content: str,
) -> None:
    """DB 저장 — 세션 upsert + 사용자/어시스턴트 메시지 insert."""
    try:
        session_obj = None
        if request.session_id:
            existing = await db.execute(
                select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
            )
            session_obj = existing.scalar_one_or_none()

        if not session_obj:
            session_obj = TutorSession(
                session_uuid=uuid.UUID(session_uuid_str),
                user_id=user_id,
                context_type=request.context_type,
                context_id=request.context_id,
                title=request.message[:50],
                message_count=0,
            )
            db.add(session_obj)
            await db.flush()

        db.add(TutorMessage(
            session_id=session_obj.id,
            role="user",
            content=request.message,
            message_type="text",
        ))
        db.add(TutorMessage(
            session_id=session_obj.id,
            role="assistant",
            content=assistant_content,
            message_type="text",
        ))

        session_obj.message_count = (session_obj.message_count or 0) + 2
        session_obj.last_message_at = datetime.utcnow()
        await db.commit()
    except Exception as e:
        logger.warning("Failed to save tutor session: %s", e)


async def generate_tutor_response(
    request: TutorChatRequest,
    db: AsyncSession,
    http_request: Request,
    current_user: Optional[dict] = None,
) -> AsyncGenerator[str, None]:
    """Generate streaming response for AI tutor."""

    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user["id"] if current_user else None

    yield f"event: step\ndata: {json.dumps({'type': 'thinking', 'content': '질문을 분석하고 있습니다...'})}\n\n"

    # 가드레일 검사
    try:
        guardrail_result = await run_guardrail(request.message)
        if not guardrail_result.is_allowed:
            # 차단 메시지를 스트리밍으로 전송 후 즉시 종료 (DB 저장 없음)
            yield f"event: text_delta\ndata: {json.dumps({'content': guardrail_result.block_message})}\n\n"
            yield f"event: done\ndata: {json.dumps({'type': 'done', 'session_id': session_id, 'total_tokens': 0, 'guardrail': guardrail_result.decision, 'response_mode': request.response_mode or 'plain', 'search_used': False})}\n\n"
            return
    except Exception as e:
        logger.warning("Guardrail check failed, falling open: %s", type(e).__name__)

    settings = get_settings()
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'OpenAI API key not configured'})}\n\n"
        return

    # 컨텍스트 수집
    page_context, sources, detected_stocks, chart_data, extra_context = await _collect_context(
        request, db, user_id
    )

    # LLM 메시지 배열 구성
    messages = await _build_llm_messages(request, db, page_context, extra_context)

    try:
        client = AsyncOpenAI(api_key=api_key)
        chat_model = settings.TUTOR_CHAT_MODEL or "gpt-5-mini"
        reasoning_effort = _normalize_reasoning_effort(settings.TUTOR_REASONING_EFFORT)
        response_mode = request.response_mode or "plain"
        use_web_search = bool(request.use_web_search)

        total_tokens = 0
        full_response = ""
        search_used = False
        used_responses_api = False
        stream_start = time.monotonic()
        chunk_count = 0

        if settings.TUTOR_USE_RESPONSES_API:
            response_input = [{"role": item["role"], "content": item["content"]} for item in messages]
            responses_kwargs: dict[str, Any] = {
                "model": chat_model,
                "input": response_input,
                "stream": True,
                "max_output_tokens": 1000,
            }

            if reasoning_effort:
                responses_kwargs["reasoning"] = {"effort": reasoning_effort}

            if use_web_search:
                responses_kwargs["tools"] = [{"type": "web_search_preview"}]

            try:
                responses_stream = await client.responses.create(**responses_kwargs)
                used_responses_api = True

                async for event in responses_stream:
                    chunk_count += 1

                    if chunk_count % 10 == 0:
                        if time.monotonic() - stream_start > 300:
                            logger.warning("Responses SSE 스트리밍 타임아웃 (300초 초과)")
                            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'Stream timeout'})}\n\n"
                            break
                        if await http_request.is_disconnected():
                            logger.info("클라이언트 연결 해제 감지, 스트리밍 중단")
                            break

                    event_data = _event_to_dict(event)
                    event_type = (event_data.get("type") or getattr(event, "type", "") or "").strip()

                    if event_type == "response.output_text.delta":
                        delta = event_data.get("delta") or getattr(event, "delta", "")
                        if isinstance(delta, str) and delta:
                            full_response += delta
                            yield f"event: text_delta\ndata: {json.dumps({'content': delta})}\n\n"
                        continue

                    if "web_search" in event_type:
                        search_used = True
                        yield f"event: step\ndata: {json.dumps({'type': 'tool_call', 'tool': 'web_search', 'content': '웹 검색 컨텍스트를 수집 중입니다.'})}\n\n"
                        continue

                    if "tool" in event_type and event_type not in {"response.output_text.annotation.added"}:
                        tool_name = "tool"
                        if "web_search" in event_type:
                            tool_name = "web_search"
                            search_used = True
                        yield f"event: step\ndata: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'content': '도구 실행 중입니다.'})}\n\n"
                        continue

                    if event_type in {"response.error", "error"}:
                        error_obj = event_data.get("error") or {}
                        if isinstance(error_obj, dict):
                            err_message = error_obj.get("message") or str(error_obj)
                        else:
                            err_message = str(error_obj)
                        raise RuntimeError(err_message or "Responses API stream error")

                    if event_type == "response.completed":
                        response_payload = event_data.get("response") or {}
                        if isinstance(response_payload, dict):
                            total_tokens = _extract_usage_total(response_payload)
                            if not full_response:
                                extracted_text = _extract_response_text(response_payload)
                                if extracted_text:
                                    full_response = extracted_text
                                    yield f"event: text_delta\ndata: {json.dumps({'content': extracted_text})}\n\n"
                        continue
            except Exception as responses_err:
                logger.warning(
                    "responses_api_fallback model=%s reason=%s",
                    chat_model,
                    type(responses_err).__name__,
                )
                used_responses_api = False
                total_tokens = 0
                full_response = ""
                search_used = False

        if not used_responses_api:
            completion_kwargs = {
                "model": chat_model,
                "messages": messages,
                "max_tokens": 1000,
                "stream": True,
            }

            if reasoning_effort:
                try:
                    response = await client.chat.completions.create(
                        **completion_kwargs,
                        reasoning_effort=reasoning_effort,
                    )
                except Exception as e:
                    logger.warning(
                        "reasoning_effort fallback model=%s effort=%s reason=%s",
                        chat_model,
                        reasoning_effort,
                        type(e).__name__,
                    )
                    response = await client.chat.completions.create(**completion_kwargs)
                    reasoning_effort = ""
            else:
                response = await client.chat.completions.create(**completion_kwargs)

            if use_web_search:
                yield f"event: step\ndata: {json.dumps({'type': 'tool_call', 'tool': 'web_search', 'content': '현재 모델 경로에서는 웹 검색 도구를 지원하지 않아 기본 분석으로 진행합니다.'})}\n\n"

            async for chunk in response:
                chunk_count += 1

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

        # DB 저장
        await _save_tutor_session(db, session_id, user_id, request, full_response)

        # 시각화 자동 감지: should_auto_visualize() + chart_data 존재 여부로 판단
        from app.services.stock_resolver import should_auto_visualize
        should_viz = should_auto_visualize(request.message, bool(detected_stocks))
        # chart_data가 이미 수집되어 있으면 자동 시각화
        if chart_data and not should_viz:
            should_viz = True

        if should_viz and full_response:
            try:
                import anthropic
                import os

                viz_prompt = (
                    "다음 내용을 Plotly.js 차트 JSON으로 변환하세요.\n"
                    "반드시 아래 형식의 JSON만 반환하세요 (마크다운 코드블록 없이):\n"
                    '{"data": [트레이스 객체들], "layout": {레이아웃 옵션}}\n\n'
                    f"내용:\n{full_response[:500]}"
                )

                claude_api_key = os.getenv("CLAUDE_API_KEY") or get_settings().ANTHROPIC_API_KEY
                if claude_api_key:
                    claude_client = anthropic.AsyncAnthropic(api_key=claude_api_key)
                    viz_response = await claude_client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=2000,
                        system=(
                            "당신은 Plotly.js 차트 전문가입니다. "
                            "주어진 내용을 시각화하는 Plotly JSON config를 생성하세요. "
                            '반드시 {"data": [...], "layout": {...}} 형식의 JSON만 반환하세요. '
                            "디자인 규칙: 주요 색상 #FF6B00(주황), 보조 색상 #FF8C33, "
                            "배경 투명(transparent), 한글 레이블 사용. "
                            "마크다운 코드블록(```)으로 감싸지 마세요. 오직 JSON만 반환하세요."
                        ),
                        messages=[{"role": "user", "content": viz_prompt}],
                    )
                    json_content = viz_response.content[0].text.strip()
                else:
                    # Claude API 키 없으면 OpenAI fallback
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
                logger.warning("시각화 생성 실패: %s", viz_err)

        structured = None
        if request.structured_extract and request.response_mode == "canvas_markdown":
            structured = _extract_structured_from_markdown(full_response)

        done_data = {'session_id': session_id, 'total_tokens': total_tokens}
        done_data['type'] = 'done'
        done_data['model'] = chat_model
        done_data['search_used'] = bool(search_used and use_web_search)
        done_data['response_mode'] = response_mode
        if reasoning_effort:
            done_data['reasoning_effort'] = reasoning_effort
        if sources:
            done_data['sources'] = sources
        if structured:
            done_data['structured'] = structured
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
