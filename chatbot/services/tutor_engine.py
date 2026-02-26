"""AI 튜터 응답 생성 엔진.

SSE 스트리밍 응답 생성, 컨텍스트 수집, 자동 시각화를 담당한다.
라우트 엔드포인트와 분리하여 핵심 비즈니스 로직만 포함.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import Request
from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.glossary import Glossary
from app.models.historical_case import HistoricalCase
from app.models.report import BrokerReport
from app.models.tutor import TutorMessage, TutorSession
from app.schemas.tutor import TutorChatRequest
from app.services import get_redis_cache
from app.services.llm_client import extract_citations, extract_openai_content, get_llm_client
from app.services.stock_resolver import (
    detect_stock_codes,
    fetch_stock_data_for_context,
    get_fundamentals_text,
    should_auto_visualize,
)
from chatbot.services.tutor_orchestrator_graph import (
    resolve_effective_message,
    run_ambiguity_orchestrator,
)

logger = logging.getLogger("narrative.tutor_engine")

CLARIFICATION_KEY_PREFIX = "tutor:clarify:"
CLARIFICATION_TTL_SECONDS = 15 * 60
KST = timezone(timedelta(hours=9))


# --- 난이도별 프롬프트 ---

def get_difficulty_prompt(difficulty: str) -> str:
    """난이도별 시스템 프롬프트 반환 (md 파일에서 로드)."""
    prompts_dir = Path(__file__).parent.parent / "prompts" / "templates"
    file_map = {
        "beginner": "tutor_beginner.md",
        "elementary": "tutor_elementary.md",
        "intermediate": "tutor_intermediate.md",
    }

    file_name = file_map.get(difficulty, "tutor_beginner.md")
    prompt_path = prompts_dir / file_name

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as exc:
        logger.error("Failed to load prompt file %s: %s", file_name, exc)
        return "당신은 친절한 주식 투자 튜터입니다. 쉽게 설명해주세요."


# --- 공통 유틸 ---

def _clarification_cache_key(session_id: str) -> str:
    return f"{CLARIFICATION_KEY_PREFIX}{session_id}"


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for src in sources:
        if not isinstance(src, dict):
            continue
        key = f"{src.get('url', '').strip()}::{src.get('title', '').strip()}::{src.get('name', '').strip()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(src)
    return deduped


def _build_kst_context_block() -> str:
    now_kst = datetime.now(KST)
    return (
        "\n\n[시간 기준]\n"
        f"현재 기준 시각(KST): {now_kst.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "오늘/어제/내일과 같은 상대 시점은 반드시 KST 기준으로 해석하세요.\n"
        "날짜 해석이 필요한 답변에는 절대 날짜(YYYY-MM-DD)를 함께 제시하세요."
    )


async def _ensure_session(
    db: AsyncSession,
    request: TutorChatRequest,
    session_id: str,
    current_user: dict | None,
) -> TutorSession:
    session_obj: TutorSession | None = None

    if request.session_id:
        try:
            existing = await db.execute(
                select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
            )
            session_obj = existing.scalar_one_or_none()
        except Exception:
            session_obj = None

    if not session_obj:
        user_id = current_user["id"] if current_user else None
        session_obj = TutorSession(
            session_uuid=uuid.UUID(session_id),
            user_id=user_id,
            context_type=request.context_type,
            context_id=request.context_id,
            title=request.message[:50],
            message_count=0,
        )
        db.add(session_obj)
        await db.flush()

    return session_obj


async def _persist_turn(
    db: AsyncSession,
    session_obj: TutorSession,
    user_message: str,
    assistant_message: str,
    assistant_message_type: str = "text",
    visualization_payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        TutorMessage(
            session_id=session_obj.id,
            role="user",
            content=user_message,
            message_type="text",
        )
    )

    increment = 2
    if visualization_payload:
        db.add(
            TutorMessage(
                session_id=session_obj.id,
                role="assistant",
                content=json.dumps(visualization_payload, ensure_ascii=False, default=str),
                message_type="visualization",
            )
        )
        increment += 1

    db.add(
        TutorMessage(
            session_id=session_obj.id,
            role="assistant",
            content=assistant_message,
            message_type=assistant_message_type,
        )
    )

    session_obj.message_count = (session_obj.message_count or 0) + increment
    session_obj.last_message_at = datetime.utcnow()
    await db.commit()


async def _load_previous_messages(db: AsyncSession, session_id: str | None) -> list[dict[str, str]]:
    prev_msgs: list[dict[str, str]] = []
    if not session_id:
        return prev_msgs

    try:
        existing_session = await db.execute(
            select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(session_id))
        )
        session_obj = existing_session.scalar_one_or_none()
        if not session_obj:
            return prev_msgs

        prev_result = await db.execute(
            select(TutorMessage)
            .where(TutorMessage.session_id == session_obj.id)
            .order_by(TutorMessage.created_at)
            .limit(20)
        )
        for msg in prev_result.scalars():
            if msg.message_type == "visualization":
                continue

            content = msg.content
            if msg.message_type == "clarification":
                try:
                    parsed = json.loads(msg.content)
                    content = f"[확인 질문] {parsed.get('question', '')}".strip()
                except Exception:
                    content = "[확인 질문]"

            if msg.role in {"user", "assistant"}:
                prev_msgs.append({"role": msg.role, "content": content})
    except Exception as exc:
        logger.warning("Failed to load previous messages: %s", exc)

    return prev_msgs


async def _get_pending_clarification(cache: Any, session_id: str) -> dict[str, Any] | None:
    try:
        raw = await cache.get(_clarification_cache_key(session_id))
    except Exception:
        return None

    if not raw:
        return None

    try:
        parsed = json.loads(raw)
    except Exception:
        return None

    created_at_raw = str(parsed.get("created_at_kst") or "")
    if created_at_raw:
        try:
            created_at = datetime.fromisoformat(created_at_raw)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=KST)
            if datetime.now(KST) - created_at > timedelta(seconds=CLARIFICATION_TTL_SECONDS):
                logger.info("clarification_ttl_expired session=%s", session_id)
                try:
                    await cache.delete(_clarification_cache_key(session_id))
                except Exception:
                    pass
                return None
        except Exception:
            pass

    return parsed


async def _set_pending_clarification(cache: Any, session_id: str, payload: dict[str, Any]) -> None:
    await cache.set(
        _clarification_cache_key(session_id),
        json.dumps(payload, ensure_ascii=False, default=str),
        ttl=CLARIFICATION_TTL_SECONDS,
    )


async def _clear_pending_clarification(cache: Any, session_id: str) -> None:
    try:
        await cache.delete(_clarification_cache_key(session_id))
    except Exception:
        pass


async def _collect_web_search_context(message: str) -> tuple[str, list[dict[str, Any]]]:
    llm_client = get_llm_client()
    if not llm_client.perplexity_key:
        raise RuntimeError("PERPLEXITY_API_KEY not configured")

    result = await llm_client.call_perplexity(
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 한국 금융시장 리서치 보조 도구다. "
                    "질문과 관련된 최신 사실을 한국어로 6문장 이내로 요약하고, "
                    "수치/날짜가 있으면 포함해라."
                ),
            },
            {"role": "user", "content": message},
        ],
        model="sonar-pro",
        temperature=0.2,
        max_tokens=700,
    )

    summary = extract_openai_content(result, "").strip()
    citations = extract_citations(result)
    web_sources = [
        {
            "type": "web",
            "title": citation.get("name") or "웹 검색",
            "url": citation.get("url"),
            "content": "Perplexity 웹 검색",
        }
        for citation in citations
        if citation.get("url")
    ]
    return summary, web_sources


# --- 컨텍스트 수집 ---

async def _collect_glossary_context(
    message: str, db: AsyncSession
) -> tuple[str, list[dict[str, Any]]]:
    """메시지에서 용어를 감지하고 glossary DB를 조회하여 컨텍스트와 출처를 반환."""
    common_terms = ["PER", "PBR", "EPS", "ROE", "ROA", "ETF", "배당", "시가총액"]
    terms_to_search = [term for term in common_terms if term.lower() in message.lower()]

    glossary_context = ""
    sources: list[dict[str, Any]] = []

    for term in terms_to_search:
        result = await db.execute(select(Glossary).where(Glossary.term.ilike(f"%{term}%")))
        item = result.scalar_one_or_none()
        if item:
            glossary_context += f"\n{item.term}: {item.definition_short}"
            sources.append(
                {
                    "type": "glossary",
                    "title": item.term,
                    "content": item.definition_short or "",
                    "url": f"/api/v1/glossary/{item.id}",
                }
            )

    return glossary_context, sources


async def _collect_db_context(
    message: str, db: AsyncSession
) -> tuple[str, list[dict[str, Any]]]:
    """DB에서 사례/리포트를 검색하여 컨텍스트와 출처를 반환."""
    db_context = ""
    sources: list[dict[str, Any]] = []

    try:
        case_result = await db.execute(
            select(HistoricalCase)
            .where(HistoricalCase.summary.ilike(f"%{message[:30]}%"))
            .order_by(HistoricalCase.created_at.desc())
            .limit(2)
        )
        for case in case_result.scalars():
            db_context += f"\n[사례] {case.title} ({case.event_year}년): {(case.summary or '')[:150]}"
            if case.source_urls:
                urls = case.source_urls if isinstance(case.source_urls, list) else []
                for url in urls[:2]:
                    if isinstance(url, str):
                        source_type = "dart" if "dart" in url.lower() else "news"
                        sources.append(
                            {
                                "type": source_type,
                                "title": "DART 공시" if source_type == "dart" else "뉴스 기사",
                                "url": url,
                            }
                        )
            sources.append(
                {
                    "type": "case",
                    "title": case.title,
                    "content": f"{case.event_year}년 — {(case.summary or '')[:80]}",
                    "url": f"/narrative?caseId={case.id}",
                }
            )
    except Exception as exc:
        logger.debug("사례 검색 실패: %s", exc)

    try:
        report_result = await db.execute(
            select(BrokerReport)
            .where(BrokerReport.report_title.ilike(f"%{message[:20]}%"))
            .order_by(BrokerReport.report_date.desc())
            .limit(2)
        )
        for report in report_result.scalars():
            db_context += f"\n[리포트] {report.broker_name}: {report.report_title} ({report.report_date})"
            sources.append(
                {
                    "type": "report",
                    "title": f"{report.broker_name} — {report.report_title}",
                    "content": f"{report.report_date}",
                    "url": report.pdf_url or "",
                }
            )
    except Exception as exc:
        logger.debug("리포트 검색 실패: %s", exc)

    return db_context, sources


async def _collect_stock_context(
    message: str, detected_stocks: list[tuple[str, str]], db: AsyncSession
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """종목 관련 데이터(주가, 재무지표)를 수집."""
    del db
    db_context = ""
    chart_data: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []

    if not detected_stocks:
        return db_context, chart_data, sources

    stock_context, chart_data = fetch_stock_data_for_context(detected_stocks)
    if stock_context:
        db_context += stock_context
        for name, code in detected_stocks:
            sources.append(
                {
                    "type": "stock_price",
                    "title": f"{name}({code}) 주가 데이터",
                    "content": "pykrx 실시간 조회",
                    "url": f"https://finance.naver.com/item/main.nhn?code={code}",
                }
            )

    for _, code in detected_stocks[:2]:
        fdr_text = get_fundamentals_text(code)
        if fdr_text:
            db_context += f"\n{fdr_text}"
            sources.append(
                {
                    "type": "financial",
                    "title": f"재무 지표 ({code})",
                    "content": fdr_text[:80],
                    "url": f"https://finance.naver.com/item/coinfo.naver?code={code}",
                }
            )

    return db_context, chart_data, sources


# --- 메인 응답 생성기 ---

async def generate_tutor_response_stream(
    request: TutorChatRequest,
    db: AsyncSession,
    http_request: Request,
    current_user: dict | None = None,
) -> AsyncGenerator[str, None]:
    """AI 튜터 스트리밍 응답을 생성한다 (Chart-First + Clarification Hybrid)."""

    session_id = request.session_id or str(uuid.uuid4())
    yield f"event: step\ndata: {json.dumps({'type': 'thinking', 'content': '질문을 분석하고 있습니다...'})}\n\n"

    settings = get_settings()
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'OpenAI API key not configured'})}\n\n"
        return

    cache = await get_redis_cache()

    page_context = ""
    if request.context_text:
        page_context = (
            "\n\n[현재 학습/화면 문맥]\n"
            "사용자는 지금 애플리케이션 화면에서 아래의 내용을 직접 읽고 있는 중입니다:\n"
            f'"""\n{request.context_text}\n"""\n'
            "사용자가 질문을 할 때, 만약 사용자가 '이 화면', '방금 내용', '이 파트'와 같이 "
            "주어를 생략하더라도 반드시 위 문맥과 연관지어 자연스럽게 답변하세요."
        )
    elif request.context_type and request.context_id:
        try:
            if request.context_type == "briefing":
                ctx_result = await db.execute(
                    text("SELECT market_summary, top_keywords FROM daily_briefings WHERE id = :id"),
                    {"id": request.context_id},
                )
                ctx_row = ctx_result.fetchone()
                if ctx_row:
                    page_context = f"\n\n[현재 보고 있는 브리핑]\n시장 요약: {ctx_row[0]}\n키워드: {ctx_row[1]}"
            elif request.context_type == "case":
                ctx_result = await db.execute(
                    text("SELECT title, summary FROM historical_cases WHERE id = :id"),
                    {"id": request.context_id},
                )
                ctx_row = ctx_result.fetchone()
                if ctx_row:
                    page_context = f"\n\n[현재 보고 있는 사례]\n제목: {ctx_row[0]}\n요약: {ctx_row[1]}"
        except Exception:
            pass

    user_id = current_user["id"] if current_user else None
    if user_id:
        try:
            portfolio_result = await db.execute(
                text("SELECT current_cash, initial_cash FROM user_portfolios WHERE user_id = :uid LIMIT 1"),
                {"uid": user_id},
            )
            pf_row = portfolio_result.fetchone()
            if pf_row:
                holdings_result = await db.execute(
                    text(
                        "SELECT stock_name, quantity, avg_buy_price FROM portfolio_holdings "
                        "WHERE portfolio_id = (SELECT id FROM user_portfolios WHERE user_id = :uid LIMIT 1)"
                    ),
                    {"uid": user_id},
                )
                holdings = holdings_result.fetchall()
                holdings_text = ", ".join(
                    f"{holding[0]} {holding[1]}주(평균 {int(holding[2]):,}원)"
                    for holding in holdings
                ) if holdings else "없음"
                page_context += (
                    "\n\n[사용자 포트폴리오]\n"
                    f"보유 현금: {int(pf_row[0]):,}원 / 초기 자본: {int(pf_row[1]):,}원\n"
                    f"보유 종목: {holdings_text}"
                )
        except Exception:
            pass

    prev_msgs = await _load_previous_messages(db, request.session_id)

    pending_clarification = await _get_pending_clarification(cache, session_id)
    if pending_clarification:
        original_question = str(pending_clarification.get("original_question") or "").strip() or request.message
        effective_message = await resolve_effective_message(original_question, request.message)
        await _clear_pending_clarification(cache, session_id)
        logger.info("clarification_resolved session=%s", session_id)
    else:
        orchestrated = await run_ambiguity_orchestrator(request.message)
        effective_message = str(orchestrated.get("effective_message") or request.message)

        if orchestrated.get("is_ambiguous"):
            clarification_question = str(orchestrated.get("clarification_question") or "의도를 정확히 이해하기 위해 한 가지 확인할게요. 어떤 기준으로 진행할까요?")
            clarification_options = orchestrated.get("clarification_options") or [
                {"id": "period_10d", "label": "최근 10거래일", "value": "최근 10거래일 기준으로 진행해줘"},
                {"id": "period_1m", "label": "1개월", "value": "최근 1개월 기준으로 진행해줘"},
                {"id": "period_3m", "label": "3개월", "value": "최근 3개월 기준으로 진행해줘"},
            ]

            clarification_payload = {
                "original_question": request.message,
                "question": clarification_question,
                "options": clarification_options,
                "missing_slots": orchestrated.get("missing_slots") or [],
                "context_type": request.context_type,
                "context_id": request.context_id,
                "created_at_kst": datetime.now(KST).isoformat(),
            }
            await _set_pending_clarification(cache, session_id, clarification_payload)
            logger.info(
                "clarification_requested session=%s missing_slots=%s",
                session_id,
                orchestrated.get("missing_slots") or [],
            )

            yield (
                "event: clarification\n"
                f"data: {json.dumps({'type': 'clarification', 'question': clarification_question, 'options': clarification_options, 'session_id': session_id}, ensure_ascii=False)}\n\n"
            )

            try:
                session_obj = await _ensure_session(db, request, session_id, current_user)
                await _persist_turn(
                    db,
                    session_obj,
                    user_message=request.message,
                    assistant_message=json.dumps(
                        {
                            "question": clarification_question,
                            "options": clarification_options,
                        },
                        ensure_ascii=False,
                    ),
                    assistant_message_type="clarification",
                )
                await cache.invalidate_session_cache(session_id)
            except Exception as exc:
                logger.warning("Failed to save clarification turn: %s", exc)

            yield f"event: done\ndata: {json.dumps({'type': 'done', 'session_id': session_id, 'total_tokens': 0})}\n\n"
            return

    logger.info("effective_message_applied session=%s", session_id)

    sources: list[dict[str, Any]] = []
    extra_context = ""
    detected_stocks: list[tuple[str, str]] = []
    chart_data: dict[str, Any] = {}

    try:
        glossary_context, glossary_sources = await _collect_glossary_context(effective_message, db)
        db_context, db_sources = await _collect_db_context(effective_message, db)
        detected_stocks = detect_stock_codes(effective_message)
        stock_context, chart_data, stock_sources = await _collect_stock_context(
            effective_message,
            detected_stocks,
            db,
        )

        sources = glossary_sources + db_sources + stock_sources
        if glossary_context:
            extra_context += f"\n\n참고할 용어 정의:{glossary_context}"
        if db_context:
            extra_context += f"\n\n참고할 내부 데이터:{db_context}"
        if stock_context:
            extra_context += f"\n\n참고할 종목 데이터:{stock_context}"
    except Exception as exc:
        logger.warning("출처 수집 실패 (무시): %s", exc)

    from chatbot.services.guardrail import run_guardrail

    guardrail_context = page_context
    last_assistant_msgs = [msg["content"] for msg in prev_msgs if msg["role"] == "assistant"]
    if last_assistant_msgs:
        guardrail_context += f"\n\n[직전 챗봇의 답변]\n{last_assistant_msgs[-1]}"

    try:
        guardrail_result = await run_guardrail(effective_message, context=guardrail_context)
        if not guardrail_result.is_allowed:
            yield f"event: text_delta\ndata: {json.dumps({'content': guardrail_result.block_message}, ensure_ascii=False)}\n\n"
            try:
                session_obj = await _ensure_session(db, request, session_id, current_user)
                await _persist_turn(
                    db,
                    session_obj,
                    user_message=request.message,
                    assistant_message=guardrail_result.block_message,
                    assistant_message_type="text",
                )
                await cache.invalidate_session_cache(session_id)
            except Exception as exc:
                logger.warning("가드레일 차단 내역 DB 저장 실패: %s", exc)

            yield (
                "event: done\n"
                f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_tokens': 0, 'guardrail': guardrail_result.decision}, ensure_ascii=False)}\n\n"
            )
            return
    except Exception as exc:
        logger.warning("Guardrail check failed, falling open: %s", exc)

    logger.info("websearch_called session=%s", session_id)
    try:
        web_summary, web_sources = await _collect_web_search_context(effective_message)
        if web_summary:
            extra_context += f"\n\n[웹 검색 요약]\n{web_summary}"
        sources = _dedupe_sources(sources + web_sources)
        logger.info("websearch_success session=%s citations=%d", session_id, len(web_sources))
    except Exception as exc:
        logger.warning("websearch_fail_reason session=%s reason=%s", session_id, exc)

    sources = _dedupe_sources(sources)

    dynamic_context = page_context + _build_kst_context_block() + extra_context

    from app.schemas.tutor import ChartClassificationResult, ChartType
    from chatbot.services.tutor_chart_generator import classify_chart_request, generate_chart_json

    user_requested_viz = should_auto_visualize(effective_message, bool(detected_stocks), prev_msgs)
    should_viz = user_requested_viz or bool(chart_data)
    logger.info(
        "chart_requested session=%s user_requested_viz=%s chart_data=%s should_viz=%s",
        session_id,
        user_requested_viz,
        bool(chart_data),
        should_viz,
    )

    chart_system_prompt = ""
    fallback_msg_sent = False
    visualization_payload: dict[str, Any] | None = None

    if should_viz:
        try:
            real_data_block = ""
            if chart_data:
                real_data_json = json.dumps(chart_data, ensure_ascii=False, default=str)[:2000]
                real_data_block = (
                    "\n\n[실제 조회된 주가 데이터 - 반드시 이 날짜/수치만 사용]\n"
                    f"{real_data_json}"
                )

            viz_context = (
                f"사용자 질문: {effective_message}\n"
                f"조회된 데이터: {dynamic_context[:800]}{real_data_block}"
            )

            unsupported_viz_keywords = ("3d", "3차원", "입체", "애니메이션", "동영상")
            unsupported_viz_token_keywords = ("vr", "ar")
            lower_message = effective_message.lower()
            has_unsupported_viz_keyword = any(
                keyword in lower_message for keyword in unsupported_viz_keywords
            ) or any(
                re.search(rf"(?<![a-z]){keyword}(?![a-z])", lower_message)
                for keyword in unsupported_viz_token_keywords
            )

            if has_unsupported_viz_keyword:
                classification = ChartClassificationResult(
                    reasoning="3D/애니메이션/VR/AR 시각화는 현재 미지원",
                    chart_type=ChartType.UNSUPPORTED,
                )
            else:
                classification = await classify_chart_request(effective_message, viz_context)

            logger.info("[Chart-First] classification result: chart_type=%s", classification.chart_type)

            if classification.chart_type == ChartType.UNSUPPORTED:
                if user_requested_viz:
                    fallback_msg = "지금은 해당 시각화를 지원하지 않아요. 빠르게 업데이트하도록 할게요! 🐧\n\n"
                    yield f"event: text_delta\ndata: {json.dumps({'content': fallback_msg}, ensure_ascii=False)}\n\n"
                    fallback_msg_sent = True
                    chart_system_prompt = (
                        "[시스템 안내] 차트 시각화가 기술적으로 불가능하거나 실패했습니다. "
                        "데이터의 흐름과 수치를 텍스트만으로 최대한 상세하고 직관적으로 설명해 주세요."
                    )
            else:
                yield (
                    "event: viz_intent\n"
                    f"data: {json.dumps({'type': 'viz_intent', 'content': '📊 차트를 그려볼게요! 잠시만 기다려주세요.'}, ensure_ascii=False)}\n\n"
                )

                chart_json = await generate_chart_json(viz_context, classification.chart_type)
                logger.info("[Chart-First] chart_json generated: %s", bool(chart_json))

                if chart_json and "data" in chart_json and isinstance(chart_json["data"], list):
                    for trace in chart_json["data"]:
                        if "type" not in trace:
                            trace["type"] = classification.chart_type.value

                    trace_count = len(chart_json.get("data", []))
                    if trace_count == 0:
                        logger.info("chart_empty_traces session=%s", session_id)
                    else:
                        logger.info("chart_generated session=%s traces=%d", session_id, trace_count)

                    chart_title = (
                        chart_json.get("layout", {}).get("title", {}).get("text")
                        if isinstance(chart_json.get("layout", {}).get("title"), dict)
                        else chart_json.get("layout", {}).get("title")
                    ) or ""

                    visualization_payload = {
                        "type": "visualization",
                        "format": "json",
                        "chartData": chart_json,
                        "title": chart_title,
                    }
                    yield (
                        "event: visualization\n"
                        f"data: {json.dumps(visualization_payload, ensure_ascii=False)}\n\n"
                    )

                    chart_data_summary = json.dumps(chart_json.get("data", []), ensure_ascii=False)[:800]
                    chart_system_prompt = (
                        "[[CRITICAL INSTRUCTION]]\n"
                        "이미 UI 상에 인터랙티브 차트(Plotly)가 성공적으로 렌더링되었습니다.\n"
                        "텍스트로 차트를 다시 그리거나(|, *, ─, _ 등 ASCII 기호 사용), "
                        "'아래 차트를 보세요' 같은 중복 멘트는 하지 마세요.\n\n"
                        "'아래의 시각화', '위 차트', '다음 그래프', '이 차트를 보면' 등 위치 지칭 표현은 사용하지 마세요.\n"
                        "차트를 직접 가리키는 대신 '데이터에 따르면', '수치를 보면', '최근 흐름을 분석하면' 같은 표현을 사용하세요.\n\n"
                        "반드시 아래 3단계 구조로 분석을 제공하세요:\n"
                        "1. 차트 핵심 수치 요약: 최고/최저값, 주요 변곡점, 전체 추이 방향\n"
                        "2. 투자자 관점 시사점: 위 수치가 의미하는 바, 주의 신호, 비교 관점\n"
                        "3. 메타인지 역질문: 사용자가 더 궁금해할 부분을 1가지 질문으로 유도\n\n"
                        "[생성된 차트 데이터 요약 - 반드시 이 수치를 근거로 분석]\n"
                        f"{chart_data_summary}"
                    )
                else:
                    logger.info("chart_empty_traces session=%s", session_id)
        except Exception as viz_err:
            logger.warning("시각화 파이프라인 실패: %s", viz_err)
            chart_system_prompt = "[시스템 안내] 차트 시각화가 시스템 오류로 중단되었습니다. 수치를 텍스트만으로 유용하게 설명해 주세요."

    system_base_rules = get_difficulty_prompt(request.difficulty)
    system_base_rules += (
        "\n\n[출력 형식 규칙]\n"
        "- 수식은 반드시 LaTeX로 렌더링되게 작성하세요: 인라인 $...$, 블록 $$...$$\n"
        "- 일반 텍스트는 마크다운: **볼드**, *이탤릭*, 불릿/번호 기호를 활용해 가독성을 높이세요.\n"
        "- 두 가지 이상의 상반된/비교 데이터를 설명할 때는 반드시 마크다운 테이블(| 컬럼1 | 컬럼2 |)을 사용하세요.\n"
        "- 소제목은 ## 또는 ### 를 사용하고 3줄 이상의 긴 답변은 문단 구분을 명확히 하세요.\n"
        "- 투자 용어가 나오면 괄호 안에 쉬운 설명을 덧붙여주세요. 예: PER(주가수익비율, 주가를 이익으로 나눈 값).\n"
        "- 오늘/어제/내일 표현을 사용할 때는 KST 기준 절대 날짜(YYYY-MM-DD)를 함께 명시하세요.\n"
        "\n[답변 구조 (3-Step 러닝 사이클)]\n"
        "반드시 답변 마지막 문단에는 사용자의 이해도를 묻는 '메타인지 역질문' 1개를 포함하세요.\n"
        "1. 질문에 대한 핵심 답변 (마크다운 포맷팅 적용)\n"
        "2. [자기 점검] 메타인지 역질문"
    )

    if prev_msgs:
        system_base_rules += "\n\n[중요] 이전 대화 기록입니다. 사용자와 이미 대화 중이므로 인사를 절대로 반복하지 마세요."

    messages: list[dict[str, str]] = [{"role": "system", "content": system_base_rules}]
    if dynamic_context:
        messages.append({"role": "system", "content": f"[참고용 동적 컨텍스트]\n{dynamic_context}"})
    if chart_system_prompt:
        messages.append({"role": "system", "content": chart_system_prompt})

    messages.extend(prev_msgs)
    messages.append({"role": "user", "content": effective_message})

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=4096,
            stream=True,
        )

        total_tokens = 0
        full_response = (
            "지금은 해당 시각화를 지원하지 않아요. 빠르게 업데이트하도록 할게요! 🐧\n\n"
            if fallback_msg_sent
            else ""
        )
        stream_start = time.monotonic()
        chunk_count = 0

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
                yield f"event: text_delta\ndata: {json.dumps({'type': 'text_delta', 'content': content}, ensure_ascii=False)}\n\n"

            if chunk.usage:
                total_tokens = chunk.usage.total_tokens

        try:
            session_obj = await _ensure_session(db, request, session_id, current_user)
            await _persist_turn(
                db,
                session_obj,
                user_message=request.message,
                assistant_message=full_response,
                assistant_message_type="text",
                visualization_payload=visualization_payload,
            )
            await cache.invalidate_session_cache(session_id)
        except Exception as exc:
            logger.warning("Failed to save tutor session: %s", exc)

        done_data: dict[str, Any] = {
            "type": "done",
            "session_id": session_id,
            "total_tokens": total_tokens,
        }
        if sources:
            done_data["sources"] = sources
        yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    except asyncio.TimeoutError:
        logger.warning("OpenAI API 호출 타임아웃")
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'AI 응답 시간 초과'}, ensure_ascii=False)}\n\n"
    except Exception as exc:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(exc)}, ensure_ascii=False)}\n\n"
