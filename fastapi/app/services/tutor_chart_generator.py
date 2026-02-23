"""튜터 시각화 생성 서비스 — Plotly.js JSON 직접 생성.

datapipeline chart_generation.md 방식을 튜터에 적용.
실제 chart_data(pykrx)만 사용, 가상 데이터 절대 금지.
"""
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

ESTIMATION_PATTERN = re.compile(
    r"\b(est(?:imated)?|mock)\b|\(e\)|추정", re.IGNORECASE
)

TUTOR_VIZ_SYSTEM_PROMPT = """당신은 Plotly.js 차트 전문가입니다. 제공된 실제 주식 데이터만으로 모바일 친화적인 Plotly JSON을 생성합니다.

## 디자인 규칙

1. 캔들스틱 차트 금지. scatter(lines+markers) 또는 bar를 사용하세요.
2. 색상: ["#FF6B35", "#004E89", "#1A936F", "#C5D86D", "#8B95A1"] 순서 사용. 단일 종목이면 #FF6B35.
3. 배경: paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
4. 폰트: family='IBM Plex Sans KR', size=12, color='#4E5968'
5. 그리드: y축만, gridcolor='#F2F4F6'
6. 축 폰트: color='#8B95A1', size=11
7. 마진: {"t": 50, "b": 60, "l": 60, "r": 30}
8. y축 단위 필수 (예: "원 (KRW)", "변동률 (%)")
9. annotation: 핵심 수치(최고가, 최저가, 최근 종가)에 표시
10. 모바일: 데이터 포인트 5~8개, 텍스트 짧게
11. trace 1개면 showlegend 생략, 2개 이상이면 showlegend=true + legend orientation "h" y=-0.25

## 데이터 안전 규칙

1. 가상 데이터 절대 금지. chart_data에 없는 종목명/주가/수치를 만들지 마세요.
2. 데이터 부족 시 빈 차트 반환: {"data": [], "layout": {}}
3. 날짜 형식: "YYYY-MM-DD" 또는 "MM/DD"

## 차트 유형 가이드

- 단일 종목 주가: scatter lines+markers
- 복수 종목 비교: multi-line scatter 또는 grouped bar
- 등락률 비교: bar with color-coded markers

## 출력 규칙

JSON 객체만 출력. 설명/마크다운/코드블록 금지. 오직 {"data": [...], "layout": {...}}"""


async def generate_tutor_chart(
    chart_data: dict,
    full_response: str,
    user_message: str,
) -> dict | None:
    """실제 chart_data 기반 Plotly.js JSON 생성. 데이터 없으면 None."""
    if not chart_data:
        return None

    user_prompt = _build_user_prompt(chart_data, full_response, user_message)
    raw_json = await _call_viz_llm(TUTOR_VIZ_SYSTEM_PROMPT, user_prompt)
    if not raw_json:
        return None

    try:
        parsed = json.loads(_strip_markdown_fences(raw_json))
    except (json.JSONDecodeError, TypeError):
        logger.warning("시각화 JSON 파싱 실패")
        return None

    return _validate_chart(parsed)


def _build_user_prompt(
    chart_data: dict, full_response: str, user_message: str
) -> str:
    """실제 주가 데이터를 포함한 유저 프롬프트 구성."""
    parts = [f"사용자 질문: {user_message}", "", "## 실제 주식 데이터"]
    for code, info in chart_data.items():
        name = info.get("name", code)
        history = info.get("history", [])
        parts.append(f"\n### {name} ({code})")
        recent = history[-8:] if len(history) > 8 else history
        for rec in recent:
            d = rec.get("date", "")
            c = rec.get("close", 0)
            pct = rec.get("change_pct", 0)
            parts.append(f"  {d}: {c:,.0f}원 ({pct:+.2f}%)")

    parts.append(
        f"\n## 튜터 응답 요약 (참고용, 차트 데이터로 사용 금지)\n{full_response[:500]}"
    )
    parts.append(
        "\n위 실제 주식 데이터를 기반으로 차트 JSON을 생성하세요. "
        "chart_data에 있는 수치만 사용하세요."
    )
    return "\n".join(parts)


async def _call_viz_llm(system: str, user: str) -> str | None:
    """Claude haiku → GPT-4o-mini fallback으로 JSON 생성."""
    # Claude 시도
    try:
        import anthropic

        api_key = os.getenv("CLAUDE_API_KEY")
        if api_key:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            resp = await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=0.2,
            )
            return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("Claude viz 실패: %s", e)

    # OpenAI fallback
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=2000,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("OpenAI viz 실패: %s", e)

    return None


def _strip_markdown_fences(text: str) -> str:
    """```json ... ``` 코드블록 제거."""
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _validate_chart(chart: dict) -> dict | None:
    """차트 JSON 검증: 데이터 포인트 수, 추정 마커."""
    data = chart.get("data")
    if not isinstance(data, list) or not data:
        return None

    # 유효 데이터 포인트 3개 이상 필요
    numeric_count = 0
    for trace in data:
        if not isinstance(trace, dict):
            continue
        for key in ("y", "values"):
            vals = trace.get(key)
            if isinstance(vals, list):
                numeric_count += sum(1 for v in vals if _is_numeric(v))
    if numeric_count < 3:
        logger.info("차트 검증 실패: 데이터 포인트 부족 (%d < 3)", numeric_count)
        return None

    # 추정 마커 감지
    text_fields = json.dumps(chart.get("layout", {}), ensure_ascii=False)
    if ESTIMATION_PATTERN.search(text_fields):
        logger.info("차트 검증 실패: 추정치 마커 감지")
        return None

    return chart


def _is_numeric(v) -> bool:
    try:
        return v is not None and float(v) == float(v)
    except (TypeError, ValueError):
        return False
