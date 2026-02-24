"""Canvas 분석 엔진 — SSE 스트리밍 분석 + CTA 생성.

tutor_engine.py의 컨텍스트 수집/가드레일/차트 생성을 재사용하되,
Canvas 전용 SSE 이벤트 + CTA 루프를 추가합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Callable, Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.guardrail import run_guardrail
from app.services.stock_resolver import (
    detect_stock_codes,
    fetch_stock_data_for_context,
    should_auto_visualize,
)
from app.services.tutor_engine import (
    _collect_db_context,
    _collect_glossary_context,
    _collect_stock_context,
    get_difficulty_prompt,
)
from app.services.investment_intel import (
    collect_stock_intelligence,
    annotate_reachable_links,
)

logger = logging.getLogger("narrative_api.canvas.analyzer")

# LangSmith 트레이싱 (선택)
try:
    from langsmith import traceable  # noqa: F401

    _HAS_LANGSMITH = True
except ImportError:
    _HAS_LANGSMITH = False

    def traceable(**kwargs):  # type: ignore[misc]
        def _wrap(fn):  # type: ignore[no-untyped-def]
            return fn

        return _wrap


# ───────────────────── 시스템 프롬프트 ─────────────────────

_CANVAS_SYSTEM_PROMPT = """\
당신은 금융 교육 AI 캔버스 분석가입니다.
사용자의 질문과 제공된 컨텍스트를 기반으로 심층 분석을 제공합니다.

## 응답 규칙
1. 마크다운 형식으로 구조화된 분석을 제공합니다
2. 핵심 포인트를 명확한 제목과 불릿으로 정리합니다
3. 수치/데이터가 있으면 반드시 포함합니다
4. 투자 자문이 아닌 교육/정보 목적임을 인지합니다
5. 한국어로 응답합니다
6. 500단어 이내로 핵심만 전달합니다

## 분석 구조
- **핵심 요약**: 1-2문장
- **상세 분석**: 3-5개 포인트
- **시사점**: 투자자가 알아야 할 점
"""


# ───────────────────── 헬퍼: 빈 async 반환 ─────────────────────


async def _empty_context_2() -> tuple[str, list[dict]]:
    """빈 2-tuple 반환용 async 헬퍼."""
    return "", []


async def _empty_context_3() -> tuple[str, list[dict], dict]:
    """빈 3-tuple 반환용 async 헬퍼."""
    return "", [], {}


async def _empty_stock_context() -> tuple[str, dict, list[dict]]:
    """빈 stock context 반환용 async 헬퍼 (context, chart_data, sources)."""
    return "", {}, []


# ───────────────────── 메인 분석 제너레이터 ─────────────────────


async def run_canvas_analysis(
    *,
    db: AsyncSession,
    request: Any,  # CanvasAnalyzeRequest
    user: Optional[Any] = None,
    disconnect_check: Optional[Callable] = None,
) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """Canvas 분석 SSE 스트리밍 제너레이터.

    Yields: (event_type, payload) 튜플
        event_type: phase | text_delta | visualization | cta | sources | done | error | guardrail_notice
    """
    session_id = request.session_id or str(uuid.uuid4())
    message = request.message
    mode = request.mode
    settings = get_settings()
    start_time = time.time()

    # ── 1. 가드레일 ──────────────────────────────────────────
    yield ("phase", {"phase": "guardrail", "text": "안전성 확인 중..."})

    guardrail_result = await run_guardrail(message, policy="soft")

    if not guardrail_result.is_allowed:
        yield (
            "guardrail_notice",
            {
                "decision": guardrail_result.decision,
                "notice": guardrail_result.block_message or "요청을 처리할 수 없습니다.",
            },
        )
        yield ("done", {"session_id": session_id})
        return

    # soft 경고 (투자 자문, 주제 이탈 등)
    if guardrail_result.decision in ("ADVICE", "OFF_TOPIC"):
        yield (
            "guardrail_notice",
            {
                "decision": guardrail_result.decision,
                "notice": guardrail_result.soft_notice or guardrail_result.block_message or "",
                "mode": "soft",
            },
        )

    # ── 2. 컨텍스트 수집 (병렬) ──────────────────────────────
    yield ("phase", {"phase": "context_collection", "text": "데이터 수집 중..."})

    detected_stocks = detect_stock_codes(message)
    stock_detected = len(detected_stocks) > 0

    # 병렬 태스크 구성
    # _collect_glossary_context(message, db) → (str, list[dict])
    # _collect_db_context(message, db)       → (str, list[dict])
    # _collect_stock_context(message, detected_stocks, db) → (str, dict, list[dict])
    # collect_stock_intelligence(db, context_text, detected_stocks) → (str, list[dict], dict)
    task_glossary = _collect_glossary_context(message, db)
    task_db = _collect_db_context(message, db)

    if stock_detected or mode == "stock":
        task_stock = _collect_stock_context(message, detected_stocks, db)
        task_intel = collect_stock_intelligence(db, request.context_text, detected_stocks)
    else:
        task_stock = _empty_stock_context()
        task_intel = _empty_context_3()

    results = await asyncio.gather(
        task_glossary,
        task_db,
        task_stock,
        task_intel,
        return_exceptions=True,
    )

    # 결과 병합
    all_context_parts: list[str] = []
    all_sources: list[dict] = []
    chart_data_from_stock: dict = {}

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Context collection task %d failed: %s", i, result)
            continue

        if isinstance(result, tuple):
            if len(result) == 2:
                # glossary / db context → (context_str, sources)
                ctx, srcs = result
                if ctx:
                    all_context_parts.append(ctx)
                if isinstance(srcs, list):
                    all_sources.extend(srcs)
            elif len(result) == 3:
                # stock context → (context_str, chart_data_or_sources, sources_or_metrics)
                if i == 2:
                    # _collect_stock_context → (str, dict[chart_data], list[sources])
                    ctx, c_data, srcs = result
                    if ctx:
                        all_context_parts.append(ctx)
                    if isinstance(c_data, dict):
                        chart_data_from_stock.update(c_data)
                    if isinstance(srcs, list):
                        all_sources.extend(srcs)
                else:
                    # collect_stock_intelligence → (str, list[sources], dict[metrics])
                    ctx, srcs, _ = result
                    if ctx:
                        all_context_parts.append(ctx)
                    if isinstance(srcs, list):
                        all_sources.extend(srcs)

    # 추가 컨텍스트: request.context_text (페이지 컨텍스트 JSON)
    if request.context_text:
        try:
            ctx_payload = json.loads(request.context_text)
            if isinstance(ctx_payload, dict):
                step = ctx_payload.get("stepContent") or ctx_payload.get(
                    "context", {}
                ).get("summary", "")
                if step:
                    all_context_parts.append(
                        f"\n[페이지 컨텍스트]\n{step[:2000]}"
                    )
        except (json.JSONDecodeError, AttributeError):
            pass

    merged_context = "\n\n".join(all_context_parts)

    # ── 3. LLM 분석 스트리밍 ─────────────────────────────────
    yield ("phase", {"phase": "analyzing", "text": "분석 중..."})

    system_prompt = _CANVAS_SYSTEM_PROMPT + "\n\n" + get_difficulty_prompt(request.difficulty)
    if merged_context:
        system_prompt += f"\n\n## 참고 데이터\n{merged_context[:6000]}"

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model_used = settings.TUTOR_CHAT_MODEL or "gpt-4o-mini"

    llm_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    full_response = ""
    total_tokens = 0

    try:
        stream = await client.chat.completions.create(
            model=model_used,
            messages=llm_messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            # 클라이언트 연결 끊김 감지
            if disconnect_check and await disconnect_check():
                break

            if chunk.usage:
                total_tokens = chunk.usage.total_tokens

            for choice in chunk.choices or []:
                delta = choice.delta
                if delta and delta.content:
                    full_response += delta.content
                    yield ("text_delta", {"delta": delta.content})

    except Exception as e:
        logger.exception("Canvas LLM streaming error: %s", e)
        yield ("error", {"message": "AI 분석 중 오류가 발생했습니다."})
        return

    # ── 4. 차트 자동 생성 ────────────────────────────────────
    chart_json = None
    if should_auto_visualize(message, stock_detected, []):
        yield ("phase", {"phase": "chart_generation", "text": "차트 생성 중..."})
        try:
            # chart_data_from_stock 이 이미 있으면 재사용, 없으면 직접 조회
            if not chart_data_from_stock and detected_stocks:
                _, chart_data_from_stock = await asyncio.to_thread(
                    fetch_stock_data_for_context, detected_stocks[:2]
                )

            if chart_data_from_stock:
                from app.services.tutor_chart_generator import generate_tutor_chart

                chart_json = await generate_tutor_chart(
                    chart_data_from_stock, full_response, message
                )
                if chart_json:
                    yield ("visualization", {"chart_json": chart_json})
        except Exception as e:
            logger.warning("Canvas chart generation failed: %s", e)

    # ── 5. CTA 생성 ──────────────────────────────────────────
    try:
        from app.services.canvas.cta_generator import generate_ctas

        ctas = await generate_ctas(
            analysis_text=full_response,
            mode=mode,
            detected_stocks=detected_stocks,
            context_type=request.context_type,
        )
        if ctas:
            yield ("cta", {"ctas": ctas})
    except ImportError:
        logger.debug("cta_generator 모듈 미존재 — CTA 생성 생략")
    except Exception as e:
        logger.warning("CTA generation failed: %s", e)

    # ── 6. 소스 정리 ─────────────────────────────────────────
    if all_sources:
        try:
            annotated_sources = await annotate_reachable_links(all_sources)
            yield ("sources", {"sources": annotated_sources})
        except Exception as e:
            logger.warning("Source annotation failed: %s", e)
            yield ("sources", {"sources": all_sources})

    # ── 7. 완료 ──────────────────────────────────────────────
    elapsed_ms = int((time.time() - start_time) * 1000)
    yield (
        "done",
        {
            "session_id": session_id,
            "total_tokens": total_tokens,
            "model": model_used,
            "elapsed_ms": elapsed_ms,
            "turn_index": request.turn_index,
        },
    )
