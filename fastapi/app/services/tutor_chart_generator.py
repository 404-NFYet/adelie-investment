"""Tutor Chart Generator Service.

Handles the 2-step pipeline for generating Plotly JSON charts:
1. Classification: Maps user requests to 11 supported chart types.
2. Generation: Creates the Plotly JSON config ensuring standard formatting.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from fastapi.encoders import jsonable_encoder
from openai import AsyncOpenAI
import anthropic

from app.core.config import get_settings
from app.schemas.tutor import ChartType, ChartClassificationResult, ChartGenerationResult

logger = logging.getLogger("narrative.tutor_chart_generator")

# Shared Design Rules for all Plotly outputs
PLOTLY_DESIGN_RULES = (
    "디자인 규칙: 주요 색상 #FF6B00(주황), 보조 색상 #FF8C33, "
    "배경 투명(transparent: 'rgba(0,0,0,0)'), 한글 레이블 사용. "
    "폰트: 'IBM Plex Sans KR', size=12, color='#4E5968'. "
    "Y축에 단위 표기 (예: 'PER (배)', '원')."
)

async def classify_chart_request(user_request: str, assistant_response_context: str) -> ChartClassificationResult:
    """Step 1: Classifies the visualization request into one of the supported types."""
    prompt = (
        "다음 사용자의 질문과 튜터의 응답 맥락을 분석하여, 어떤 형태의 데이터 시각화가 가장 적절한지 11가지 차트 유형 중 하나로 분류하세요.\n\n"
        "[사용자 질문]\n" f"{user_request}\n\n"
        "[관련 데이터/문맥]\n" f"{assistant_response_context[:1000]}\n\n"
        "지원하는 차트 유형 (ChartType):\n"
        "line (주가 추이 등), bar (항목별 비교 등), pie (비율 등), area, scatter, heatmap, candlestick (봉차트), radar, bubble, combo_line_bar, funnel.\n"
        "질문이 위 11가지 형태에 전혀 맞지 않거나 3D 모델링, 비디오 생성 등 시각화 불가능한 내용일 경우 'unsupported'로 분류하세요."
    )

    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        return ChartClassificationResult(reasoning="API key missing", chart_type=ChartType.UNSUPPORTED)

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 데이터 시각화 의도 분석 전문가입니다. JSON 형식으로 엄격히 응답해야 합니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        result_json = json.loads(response.choices[0].message.content)
        return ChartClassificationResult(**result_json)
    except Exception as e:
        logger.warning(f"Chart classification failed: {e}")
        return ChartClassificationResult(reasoning="Classification API Error", chart_type=ChartType.UNSUPPORTED)


async def generate_chart_json(context: str, chart_type: ChartType) -> Optional[Dict[str, Any]]:
    """Step 2: Generate Plotly JSON config based on classified type and context data."""
    if chart_type == ChartType.UNSUPPORTED:
        return None  # Fallback gracefully handled by caller

    prompt = (
        f"다음 내용과 데이터를 기반으로 Plotly.js **{chart_type.value}** 차트 JSON을 생성하세요.\n\n"
        "반드시 요구되는 JSON 스키마 형식: `{\"data\": [트레이스 객체들], \"layout\": {레이아웃 옵션}}`\n"
        "단위가 명확하지 않다면 가상의 데이터를 생성해서라도 차트 구조를 렌더링하세요.\n\n"
        f"제공된 내용:\n{context[:1000]}\n"
    )

    system_prompt = (
        f"당신은 Plotly.js 차트 전문가입니다. 오직 JSON 형식의 결과만 반환해야 합니다. "
        f"마크다운 코드블록(```json) 없이 순수 JSON 문자열만 출력하세요. {PLOTLY_DESIGN_RULES}"
    )

    # Prefer Claude 3.5 Haiku as it handles Plotly JSON structures robustly
    claude_api_key = os.getenv("CLAUDE_API_KEY") or get_settings().ANTHROPIC_API_KEY
    try:
        if claude_api_key:
            client = anthropic.AsyncAnthropic(api_key=claude_api_key)
            response = await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2500,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            json_text = response.content[0].text.strip()
        else:
            # Fallback to OpenAI gpt-4o-mini
            openai_key = get_settings().OPENAI_API_KEY
            if not openai_key:
                return None
            o_client = AsyncOpenAI(api_key=openai_key)
            o_response = await o_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            json_text = o_response.choices[0].message.content.strip()

        # Clean markdown codeblocks if LLM incorrectly wraps it
        if json_text.startswith("```"):
            json_text = json_text.split("```", 2)[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
            json_text = json_text.strip()
            
        chart_result = json.loads(json_text)
        
        # Basic validation
        if "data" in chart_result and isinstance(chart_result["data"], list) and "layout" in chart_result:
            return chart_result
        return None

    except Exception as e:
        logger.warning(f"Chart JSON generation failed: {e}")
        return None
