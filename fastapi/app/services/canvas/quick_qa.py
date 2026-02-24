"""Canvas Quick QA — 드래그 선택 텍스트 즉석 설명.

Canvas 본문의 텍스트를 드래그하면 메인 분석 세션과 분리된
경량 즉석 설명을 제공합니다. 종목 감지 시 자동으로 DART/pykrx 데이터를 조회합니다.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.stock_resolver import detect_stock_codes
from app.services.investment_intel import collect_stock_intelligence

logger = logging.getLogger("narrative_api.canvas.quick_qa")

_QUICK_QA_SYSTEM = """당신은 금융 교육 AI 어시스턴트입니다.
사용자가 선택한 텍스트를 간결하게 설명합니다.

## 규칙
1. 200자 이내로 핵심만 설명
2. 금융 용어는 초보자도 이해할 수 있게 풀어서 설명
3. 종목/수치가 포함되면 맥락을 설명
4. 한국어로 응답
5. 투자 자문은 제공하지 않음
"""


async def handle_quick_qa(
    *,
    db: AsyncSession,
    selected_text: str,
    canvas_context_summary: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """드래그 선택 텍스트에 대한 즉석 설명 생성.

    Args:
        db: DB 세션
        selected_text: 선택된 텍스트 (2~500자)
        canvas_context_summary: 현재 Canvas 분석 요약 (선택)
        session_id: Canvas 세션 ID (참조용)

    Returns:
        QuickQAResponse 호환 dict
    """
    settings = get_settings()
    sources: list[dict[str, Any]] = []
    stock_info: Optional[dict[str, Any]] = None
    detected_stock_name: Optional[str] = None

    # 종목 감지
    detected_stocks = detect_stock_codes(selected_text)

    if detected_stocks:
        detected_stock_name = detected_stocks[0][0]
        try:
            intel_context, intel_sources, intel_metrics = await collect_stock_intelligence(
                db, None, detected_stocks
            )
            if intel_metrics:
                stock_info = {
                    "name": detected_stock_name,
                    "code": detected_stocks[0][1],
                    "metrics": intel_metrics,
                }
            if intel_sources:
                sources.extend(intel_sources)
        except Exception as e:
            logger.warning("Quick QA stock intelligence failed: %s", e)

    # LLM 설명 생성
    user_prompt = f'다음 텍스트를 간결하게 설명해줘:\n"""{selected_text}"""'
    if canvas_context_summary:
        user_prompt += f"\n\n현재 분석 맥락: {canvas_context_summary[:500]}"
    if stock_info:
        user_prompt += f"\n\n감지된 종목: {detected_stock_name} ({detected_stocks[0][1]})"

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _QUICK_QA_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        explanation = response.choices[0].message.content or "설명을 생성할 수 없습니다."
    except Exception as e:
        logger.exception("Quick QA LLM error: %s", e)
        explanation = "설명 생성 중 오류가 발생했습니다."

    return {
        "explanation": explanation,
        "stock_info": stock_info,
        "sources": sources,
        "detected_stock": detected_stock_name,
    }
