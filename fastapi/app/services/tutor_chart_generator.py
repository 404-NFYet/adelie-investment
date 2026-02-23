"""튜터 시각화 생성 서비스 — Plotly.js JSON 직접 생성.

datapipeline chart_generation.md / hallcheck_chart.md 수준의
시스템 프롬프트 + 7-gate 검증 적용.
실제 chart_data(pykrx)만 사용, 가상 데이터 절대 금지.
"""
import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# ───────────────────── 상수 ─────────────────────

ESTIMATION_PATTERN = re.compile(
    r"\b(est(?:imated)?|mock|예상|forecast)\b|\(e\)|추정", re.IGNORECASE
)

BANNED_TRACE_TYPES = frozenset(
    {"candlestick", "waterfall", "sankey", "scatterpolar", "choropleth", "pie"}
)

# 우선순위 순서: 구체적 패턴 → 일반적 패턴 (line_trend가 마지막)
CHART_TYPE_PATTERNS = [
    ("volume", {
        "keywords": ["거래량", "매매량", "volume", "수급"],
        "hint": "이중축 혼합 (scatter + bar, yaxis2)",
    }),
    ("extremes", {
        "keywords": ["최고", "최저", "고점", "저점", "전환점", "급등", "급락"],
        "hint": "영역 scatter (fill tozeroy + annotations)",
    }),
    ("grouped_compare", {
        "keywords": ["비교", "대비", "차이", "vs", "versus"],
        "hint": "그룹 막대 (barmode group)",
    }),
    ("horizontal_rank", {
        "keywords": ["순위", "랭킹", "톱", "top", "상위"],
        "hint": "가로 막대 (bar orientation h)",
    }),
    ("bar_change", {
        "keywords": ["등락률", "변동", "수익률", "손실", "상승률", "하락률"],
        "hint": "세로 막대 (bar)",
    }),
    ("line_trend", {
        "keywords": ["추이", "흐름", "변화", "추세", "최근", "올랐", "빠졌", "시계열"],
        "hint": "라인 차트 (scatter lines+markers)",
    }),
]

# ───────────────────── 시스템 프롬프트 ─────────────────────

TUTOR_VIZ_SYSTEM_PROMPT = """당신은 Plotly.js 차트 전문가입니다. 제공된 실제 주식 데이터(OHLCV)만으로 모바일 친화적인 Plotly JSON을 생성합니다.

## 지원 차트 유형

1. **라인 차트** — scatter lines+markers: 종가 시계열 추이
2. **세로 막대** — bar: 등락률/거래량 비교. 양수 #FF6B35, 음수 #004E89
3. **가로 막대** — bar orientation h: 순위 나열
4. **그룹 막대** — 2+ bar traces, barmode group: 종목간 비교
5. **이중축 혼합** — scatter(주가, yaxis y) + bar(거래량, yaxis y2): 가격+거래량 동시
6. **영역 scatter** — scatter fill tozeroy + annotations: 추이+마일스톤 표시

## 금지 차트 유형

candlestick, waterfall, sankey, scatterpolar, choropleth, pie — 절대 사용 금지.

## 스타일 규칙

- 색상: ["#FF6B35", "#004E89", "#1A936F", "#C5D86D", "#8B95A1"] 순서 사용. 단일 종목이면 #FF6B35.
- 배경: paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
- 폰트: family='IBM Plex Sans KR', size=12, color='#4E5968'
- 그리드: y축만, gridcolor='#F2F4F6'
- 축 폰트: color='#8B95A1', size=11
- 마진: {"t": 40, "b": 50, "l": 55, "r": 25}
- y축 단위 필수 (예: "원 (KRW)", "변동률 (%)")
- annotation: showarrow=true, ax=0, ay=-30, 핵심 수치(최고가, 최저가, 최근 종가)에 표시
- trace 1개면 showlegend 생략, 2개 이상이면 showlegend=true + legend orientation "h" y=-0.25
- 날짜: "YYYY-MM-DD" 또는 "MM/DD"
- 모바일: 데이터 포인트 5~8개, 텍스트 짧게

## 이중축 레이아웃 (거래량 차트 전용)

yaxis2: {title: "거래량", overlaying: "y", side: "right"}
거래량 bar trace에 yaxis: "y2" 지정.

## 데이터 안전 규칙 (필수 준수)

1. 가상 데이터 절대 금지. chart_data에 없는 종목명/주가/수치를 만들지 마세요.
2. 추정치 라벨 금지 — (E), Est, 추정, 예상, mock 사용 금지.
3. x/y 배열 길이 반드시 동일.
4. 모든 수치 = 제공된 OHLCV 데이터 원본과 정확히 일치해야 합니다.
5. 데이터 3개 미만 → 빈 차트 반환: {"data": [], "layout": {}}.
6. 축 절단 금지 — y축 range가 데이터 전체 범위를 포함해야 합니다.
7. chart_data에 있는 날짜만 사용. 임의 날짜 생성 금지.

## 출력 규칙

JSON 객체만 출력. 설명/마크다운/코드블록 금지. 오직 {"data": [...], "layout": {...}}"""


# ───────────────────── 질문 분류 ─────────────────────

def _classify_question(user_message: str) -> str:
    """질문 키워드 기반으로 추천 차트 유형 힌트 반환."""
    msg_lower = user_message.lower()
    for _, info in CHART_TYPE_PATTERNS:
        for kw in info["keywords"]:
            if kw in msg_lower:
                return info["hint"]
    return "라인 차트 (scatter lines+markers)"


# ───────────────────── 유저 프롬프트 ─────────────────────

def _build_user_prompt(
    chart_data: dict, full_response: str, user_message: str
) -> str:
    """실제 OHLCV 데이터 전체를 포함한 유저 프롬프트 구성."""
    stock_count = len(chart_data)
    chart_hint = _classify_question(user_message)

    parts = [
        f"사용자 질문: {user_message}",
        f"추천 차트 유형: {chart_hint} (종목 수: {stock_count}개)",
        "",
        "## 실제 주식 데이터 (OHLCV)",
    ]

    for code, info in chart_data.items():
        name = info.get("name", code)
        history = info.get("history", [])
        recent = history[-8:] if len(history) > 8 else history
        if not recent:
            parts.append(f"\n### {name} ({code})")
            parts.append("  데이터 없음")
            continue

        # 요약 통계
        closes = [r.get("close", 0) for r in recent if r.get("close")]
        volumes = [r.get("volume", 0) for r in recent if r.get("volume")]
        pcts = [r.get("change_pct", 0) for r in recent]

        parts.append(f"\n### {name} ({code})")
        if len(recent) >= 2:
            parts.append(f"  기간: {recent[0].get('date', '?')} ~ {recent[-1].get('date', '?')}")
        if closes:
            parts.append(f"  종가 범위: {min(closes):,.0f}원 ~ {max(closes):,.0f}원")
        if pcts:
            total_change = sum(pcts)
            parts.append(f"  기간 변동률: {total_change:+.2f}%")
        if volumes:
            avg_vol = sum(volumes) / len(volumes)
            parts.append(f"  평균 거래량: {avg_vol:,.0f}주")

        # OHLCV 테이블
        parts.append("  일자       | 시가    | 고가    | 저가    | 종가    | 등락률  | 거래량")
        parts.append("  " + "-" * 74)
        for rec in recent:
            d = rec.get("date", "")
            o = rec.get("open", 0)
            h = rec.get("high", 0)
            lo = rec.get("low", 0)
            c = rec.get("close", 0)
            pct = rec.get("change_pct", 0)
            vol = rec.get("volume", 0)
            parts.append(
                f"  {d} | {o:>7,.0f} | {h:>7,.0f} | {lo:>7,.0f} | {c:>7,.0f} | {pct:>+6.2f}% | {vol:>11,.0f}"
            )

    parts.append(
        f"\n## 튜터 응답 요약 (참고용)\n{full_response[:400]}"
    )
    parts.append(
        "\n위 실제 OHLCV 데이터만으로 차트 JSON을 생성하세요."
    )
    return "\n".join(parts)


# ───────────────────── 메인 생성 함수 ─────────────────────

async def generate_tutor_chart(
    chart_data: dict,
    full_response: str,
    user_message: str,
) -> dict | None:
    """실제 chart_data 기반 Plotly.js JSON 생성. 데이터 없으면 None."""
    if not chart_data:
        return None

    # 사전 체크: LLM 호출 전 데이터 충분성 검사
    total_records = sum(len(info.get("history", [])) for info in chart_data.values())
    if total_records < 3:
        logger.info("시각화 사전 체크 실패: 총 레코드 %d < 3, LLM 호출 생략", total_records)
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

    return _validate_chart(parsed, chart_data)


# ───────────────────── LLM 호출 ─────────────────────

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


# ───────────────────── 검증 헬퍼 ─────────────────────

def _iter_chart_text_fields(chart: dict):
    """차트 내 모든 텍스트 필드를 순회 (layout + traces)."""
    layout = chart.get("layout") or {}

    # layout 제목들
    title = layout.get("title")
    if isinstance(title, str):
        yield title
    elif isinstance(title, dict):
        yield title.get("text", "")

    for axis_key in ("xaxis", "yaxis", "yaxis2"):
        axis = layout.get(axis_key) or {}
        ax_title = axis.get("title")
        if isinstance(ax_title, str):
            yield ax_title
        elif isinstance(ax_title, dict):
            yield ax_title.get("text", "")

    # annotations
    for ann in layout.get("annotations", []):
        if isinstance(ann, dict):
            yield ann.get("text", "")

    # traces
    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        yield trace.get("name", "")
        # x 값 (날짜/카테고리 라벨)
        for v in (trace.get("x") or []):
            if isinstance(v, str):
                yield v
        # text 배열
        for v in (trace.get("text") or []):
            if isinstance(v, str):
                yield v
        # labels (pie 등)
        for v in (trace.get("labels") or []):
            if isinstance(v, str):
                yield v


def _contains_estimation_marker(chart: dict) -> bool:
    """모든 텍스트 필드에서 추정치 마커 감지."""
    for text in _iter_chart_text_fields(chart):
        if text and ESTIMATION_PATTERN.search(text):
            return True
    return False


def _count_numeric_points(chart: dict) -> int:
    """유효 데이터 포인트(숫자) 수 카운트."""
    count = 0
    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        for key in ("y", "values"):
            vals = trace.get(key)
            if isinstance(vals, list):
                count += sum(1 for v in vals if _is_numeric(v))
    return count


def _validate_xy_lengths(chart: dict) -> bool:
    """모든 trace의 x/y 배열 길이 동일 여부 검증."""
    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        x = trace.get("x")
        y = trace.get("y")
        if isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                return False
    return True


def _contains_banned_trace_type(chart: dict) -> str | None:
    """금지 차트 유형 감지. 감지 시 해당 type 반환."""
    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        trace_type = trace.get("type", "scatter")
        if trace_type in BANNED_TRACE_TYPES:
            return trace_type
    return None


def _extract_source_dates(chart_data: dict) -> set[str]:
    """chart_data에서 모든 날짜를 추출."""
    dates = set()
    for info in chart_data.values():
        for rec in info.get("history", []):
            d = rec.get("date", "")
            if d:
                dates.add(d)
                # MM/DD 변환도 허용
                if _looks_like_date(d):
                    try:
                        dt = datetime.strptime(d, "%Y-%m-%d")
                        dates.add(dt.strftime("%m/%d"))
                    except ValueError:
                        pass
    return dates


def _looks_like_date(s: str) -> bool:
    """YYYY-MM-DD 형식인지 간단히 확인."""
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return True
    return False


def _validate_dates(chart: dict, chart_data: dict) -> bool:
    """차트의 x축 날짜가 chart_data에 존재하는지 검증."""
    source_dates = _extract_source_dates(chart_data)
    if not source_dates:
        return True  # 날짜 데이터 없으면 통과

    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        x_vals = trace.get("x", [])
        if not isinstance(x_vals, list):
            continue
        for v in x_vals:
            if not isinstance(v, str):
                continue
            # 날짜 형식인 x값만 검증
            if _looks_like_date(v) or re.match(r"^\d{2}/\d{2}$", v):
                if v not in source_dates:
                    return False
    return True


def _validate_numeric_range(chart: dict, chart_data: dict) -> bool:
    """차트 y값이 원본 데이터 범위 ±10% 내인지 교차 검증.

    가격(OHLC)과 거래량을 분리하여 각각 상한 체크.
    """
    price_values = []
    volume_values = []

    for info in chart_data.values():
        for rec in info.get("history", []):
            for key in ("close", "open", "high", "low"):
                v = rec.get(key)
                if v is not None and _is_numeric(v):
                    price_values.append(abs(float(v)))
            vol = rec.get("volume")
            if vol is not None and _is_numeric(vol):
                volume_values.append(float(vol))

    if not price_values and not volume_values:
        return True

    price_upper = max(price_values) * 1.10 if price_values else 0
    volume_upper = max(volume_values) * 1.10 if volume_values else 0

    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        y_vals = trace.get("y", [])
        if not isinstance(y_vals, list):
            continue
        for v in y_vals:
            if not _is_numeric(v):
                continue
            abs_v = abs(float(v))
            # 매우 작은 값(퍼센트 등)은 통과
            if abs_v < 200:
                continue
            # 가격 범위 또는 거래량 범위 중 하나에 포함되면 OK
            if price_upper and abs_v <= price_upper:
                continue
            if volume_upper and abs_v <= volume_upper:
                continue
            return False
    return True


def _warn_axis_truncation(chart: dict) -> bool:
    """y축 range가 데이터를 포함하지 않는 축 절단 감지. True=경고."""
    layout = chart.get("layout") or {}
    yaxis = layout.get("yaxis") or {}
    y_range = yaxis.get("range")
    if not isinstance(y_range, list) or len(y_range) != 2:
        return False  # range 미설정 → autorange, 문제 없음

    try:
        range_min = float(y_range[0])
        range_max = float(y_range[1])
    except (TypeError, ValueError):
        return False

    # 모든 trace의 y값 수집
    all_y = []
    for trace in chart.get("data", []):
        if not isinstance(trace, dict):
            continue
        # yaxis2 trace는 별도 축이므로 제외
        if trace.get("yaxis") == "y2":
            continue
        for v in (trace.get("y") or []):
            if _is_numeric(v):
                all_y.append(float(v))

    if not all_y:
        return False

    data_min = min(all_y)
    data_max = max(all_y)

    # y range가 데이터를 포함하지 않으면 경고
    if range_min > data_min or range_max < data_max:
        return True
    return False


def _validate_chart(chart: dict, chart_data: dict | None = None) -> dict | None:
    """7-gate 차트 JSON 검증 (datapipeline hallcheck_chart.md 수준)."""
    data = chart.get("data")
    if not isinstance(data, list) or not data:
        return None

    # Gate 1: 유효 데이터 포인트 ≥ 3
    numeric_count = _count_numeric_points(chart)
    if numeric_count < 3:
        logger.info("차트 검증 실패 [G1]: 데이터 포인트 부족 (%d < 3)", numeric_count)
        return None

    # Gate 2: 추정치 마커 감지 (trace data + layout + annotations 전체)
    if _contains_estimation_marker(chart):
        logger.info("차트 검증 실패 [G2]: 추정치 마커 감지")
        return None

    # Gate 3: x/y 배열 길이 동일
    if not _validate_xy_lengths(chart):
        logger.info("차트 검증 실패 [G3]: x/y 배열 길이 불일치")
        return None

    # Gate 4: 금지 차트 유형
    banned = _contains_banned_trace_type(chart)
    if banned:
        logger.info("차트 검증 실패 [G4]: 금지 차트 유형 '%s'", banned)
        return None

    # chart_data 의존 검증 (Gate 5~7)
    if chart_data:
        # Gate 5: 날짜 정합성
        if not _validate_dates(chart, chart_data):
            logger.info("차트 검증 실패 [G5]: chart_data에 없는 날짜 사용")
            return None

        # Gate 6: 수치 범위 교차 검증
        if not _validate_numeric_range(chart, chart_data):
            logger.info("차트 검증 실패 [G6]: 수치 범위 원본 대비 ±10% 초과")
            return None

        # Gate 7: 축 절단 경고 (경고만, 차트 제거하지 않음)
        if _warn_axis_truncation(chart):
            logger.warning("차트 검증 경고 [G7]: y축 range가 데이터 범위를 포함하지 않음 (축 절단 의심)")

    return chart


def _is_numeric(v) -> bool:
    try:
        return v is not None and float(v) == float(v)
    except (TypeError, ValueError):
        return False
