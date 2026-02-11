"""
Historical Cases 생성 스크립트
- 각 키워드에 대해 LLM으로 역사적 유사 사례 생성
- pykrx 실시간 주가 데이터 주입으로 구체성 향상
- 퀴즈 생성 보장 + 내러티브 검증/재시도
- historical_cases, case_matches, case_stock_relations 테이블에 삽입
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def strip_marks(text: str) -> str:
    """<mark class='term'>...</mark> 태그 제거."""
    return re.sub(r"<mark\s+class=['\"]term['\"]>(.*?)</mark>", r"\1", text)


MAX_RETRIES = 3

# 7단계 내러티브 검증에 필요한 섹션 (프론트엔드 표시 순서)
REQUIRED_SECTIONS = ["background", "mirroring", "simulation", "result", "difference", "devils_advocate", "action"]


def fetch_stock_data(stock_codes: list[str]) -> str:
    """pykrx로 종목별 90일 OHLCV 요약 데이터 조회."""
    try:
        from pykrx import stock as pykrx_stock
    except ImportError:
        logger.warning("pykrx 미설치, 주가 데이터 없이 진행")
        return ""

    today = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
    lines = []

    for code in stock_codes[:3]:  # 최대 3종목
        if not code:
            continue
        try:
            name = pykrx_stock.get_market_ticker_name(code) or code
            df = pykrx_stock.get_market_ohlcv_by_date(start, today, code)
            if df.empty:
                continue
            current = int(df["종가"].iloc[-1])
            start_price = int(df["종가"].iloc[0])
            change_pct = round((current - start_price) / start_price * 100, 1)
            high = int(df["고가"].max())
            low = int(df["저가"].min())
            avg_vol = int(df["거래량"].mean())
            lines.append(
                f"- {name}({code}): 현재가 {current:,}원, 90일 등락률 {change_pct:+}%, "
                f"90일 고가 {high:,}원, 저가 {low:,}원, 평균거래량 {avg_vol:,}주"
            )
        except Exception as e:
            logger.warning(f"  pykrx 조회 실패 ({code}): {e}")
            continue

    return "\n".join(lines) if lines else ""


def validate_narrative(narrative: dict) -> list[str]:
    """내러티브 구조 검증. 문제점 리스트 반환 (빈 리스트=정상)."""
    issues = []

    # 7개 섹션 존재 확인
    for key in REQUIRED_SECTIONS:
        if key not in narrative:
            issues.append(f"섹션 누락: {key}")
            continue
        section = narrative[key]
        if not isinstance(section, dict):
            issues.append(f"{key}: dict가 아님")
            continue

        # content 최소 길이 (구조적 다문단 콘텐츠)
        content = section.get("content", "")
        if len(str(content)) < 100:
            issues.append(f"{key}: content 100자 미만")

        # chart 검증 (다양한 차트 유형 지원)
        chart = section.get("chart", {})
        if isinstance(chart, dict):
            data = chart.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                trace = data[0]
                if isinstance(trace, dict):
                    trace_type = trace.get("type", "scatter")
                    if trace_type == "pie":
                        labels = trace.get("labels", [])
                        values = trace.get("values", [])
                        if not labels or not values:
                            issues.append(f"{key}: pie chart labels/values 비어있음")
                        elif len(labels) != len(values):
                            issues.append(f"{key}: pie labels/values 길이 불일치")
                    elif trace_type == "waterfall":
                        x_vals = trace.get("x", [])
                        y_vals = trace.get("y", [])
                        if not x_vals or not y_vals:
                            issues.append(f"{key}: waterfall x/y 비어있음")
                    else:
                        x_vals = trace.get("x", [])
                        y_vals = trace.get("y", [])
                        if not x_vals or not y_vals:
                            issues.append(f"{key}: chart x/y 비어있음")
                        elif len(x_vals) != len(y_vals):
                            issues.append(f"{key}: chart x/y 길이 불일치")
                        elif not all(isinstance(v, (int, float)) for v in y_vals):
                            issues.append(f"{key}: chart y값에 비숫자 포함")

    # simulation quiz 필수
    sim = narrative.get("simulation", {})
    if isinstance(sim, dict):
        quiz = sim.get("quiz")
        if not quiz or not isinstance(quiz, dict):
            issues.append("simulation: quiz 누락")
        else:
            if quiz.get("correct_answer") not in ("up", "down", "sideways"):
                issues.append("simulation: quiz correct_answer 유효하지 않음")
            opts = quiz.get("options", [])
            if not isinstance(opts, list) or len(opts) < 3:
                issues.append("simulation: quiz options 3개 미만")

    return issues


def ensure_quiz_in_narrative(narrative: dict, keyword_title: str) -> dict:
    """simulation 섹션에 quiz가 없으면 맥락 기반 fallback 퀴즈 생성."""
    sim = narrative.get("simulation", {})
    if not isinstance(sim, dict):
        sim = {"content": "", "bullets": []}
        narrative["simulation"] = sim

    if "quiz" not in sim or not isinstance(sim.get("quiz"), dict):
        mirroring = narrative.get("mirroring", {})
        mirroring_content = mirroring.get("content", "") if isinstance(mirroring, dict) else ""
        context = mirroring_content[:100] if mirroring_content else f"{keyword_title} 관련 과거 유사 사례가 있었어요."

        sim["quiz"] = {
            "context": context,
            "question": "이 상황에서 시장은 어떻게 움직였을까요?",
            "options": [
                {"id": "up", "label": "올랐어요", "explanation": f"{keyword_title} 이슈로 시장이 상승했을 거예요."},
                {"id": "down", "label": "내렸어요", "explanation": f"{keyword_title} 이슈로 시장이 하락했을 거예요."},
                {"id": "sideways", "label": "횡보했어요", "explanation": f"{keyword_title} 이슈에도 시장은 큰 변동이 없었을 거예요."},
            ],
            "correct_answer": "up",
            "actual_result": "실제로는 단기 변동 후 점차 안정을 찾아갔어요.",
            "lesson": "과거 사례가 항상 반복되지는 않아요. 현재 상황만의 고유한 요인을 함께 고려해야 해요.",
        }
        logger.info("  퀴즈 fallback 생성 완료")

    return narrative


def generate_historical_case(keyword_title: str, category: str, stocks: list[str], stock_data: str = "") -> dict:
    """LLM으로 역사적 유사 사례 + 7단계 narrative 생성. 검증 포함."""
    clean_title = strip_marks(keyword_title)

    stock_data_section = ""
    if stock_data:
        stock_data_section = f"""
실시간 종목 데이터 (pykrx 90일):
{stock_data}
위 수치를 활용하여 구체적인 내러티브를 작성하세요. 추상적 매크로 주제 대신 해당 종목/섹터의 구체적 이벤트(실적, 수주, 규제) 중심으로 작성하세요.
"""

    prompt = f"""당신은 친근한 금융 학습 메이트 '아델리'입니다. 한국 주식 시장 역사 전문가이기도 합니다.
현재 키워드: "{clean_title}" (카테고리: {category})
관련 종목 코드: {stocks}
{stock_data_section}
이 키워드와 유사한 과거 한국 주식 시장의 역사적 사례를 생성하고, 7단계 내러티브를 작성해주세요.

=== 차트 유형 카탈로그 (Plotly 기반) ===
데이터 특성에 맞는 차트를 자유롭게 선택하세요:
1. 시계열 추세 → scatter (mode:"lines+markers") 또는 fill:"tozeroy" (area)
   예: 주가 6개월 변동, 금리 추이, 매출 성장
2. 두 시계열 비교 → multi-trace scatter (2개 trace, 각각 name 지정)
   예: 과거 vs 현재 주가, A기업 vs B기업 매출
3. 3개 이상 시나리오 비교 → multi-trace scatter (3+ traces)
   예: 낙관/중립/비관 자산 변화
4. 항목별 수치 비교 → bar (vertical)
   예: 종목별 수익률, 분기별 실적
5. 순위/랭킹 → bar (orientation:"h")
   예: 시나리오별 수익률 순위
6. 과거 vs 현재 비교 → grouped bar (barmode:"group", 2 traces)
   예: 과거/현재 PER, 과거/현재 금리
7. 비율/구성 → pie (labels:[], values:[])
   예: 포트폴리오 비중, 섹터별 비중
8. 누적 변화/손익 분해 → waterfall (type:"waterfall", x:[], y:[], measure:[])
   예: 수익 기여 요인 분해
9. OHLC 주가 → candlestick (open/high/low/close)
   예: 핵심 종목 3개월 캔들차트

7단계 섹션 + 시각화 가이드 (차트 유형은 데이터에 맞게 자유 선택):
1. background — 현재 배경 (지금 왜 이게 이슈인지)
   시각화 목표: 현재 이슈의 핵심 데이터 트렌드 (시계열이면 line/area, 종목 비교면 bar)
2. mirroring — 과거 유사 사례
   시각화 목표: 과거 사례와 현재의 데이터 대비 (dual scatter 또는 grouped bar)
3. simulation — 모의 투자 (1,000만원 기준 3시나리오: 낙관/중립/비관)
   시각화 목표: 3시나리오 자산 변화 (multi-trace scatter 또는 grouped bar)
4. result — 결과 보고
   시각화 목표: 시나리오별 최종 수익률/금액 (horizontal bar, bar, 또는 pie)
5. difference — 과거와 현재 차이
   시각화 목표: 핵심 차이점 수치 비교 (grouped bar 또는 horizontal bar)
6. devils_advocate — 반대 시나리오 3가지
   시각화 목표: 리스크/손실 크기 (bar with 음수값, pie, 또는 waterfall)
7. action — 실전 액션
   시각화 목표: 추천 투자 전략의 구체적 비중 (pie, horizontal bar)

차트 데이터 규칙 (매우 중요):
- 실제 데이터 기반: pykrx 종목 데이터가 제공되면 실제 수치를 차트에 반영
- 맥락적 수치: 해당 케이스의 맥락에 맞는 수치 사용 (배터리→GWh, 금리→%, 무역→억달러)
- x축/y축에 반드시 의미있는 라벨 사용 (연도, 종목명, 시나리오명 등)
- y값은 실제 숫자여야 하며, 0이나 빈 값 금지
- 7단계 차트가 최소 3가지 이상 서로 다른 유형이 되도록 의식적으로 다양화!
- pie 차트는 "labels"와 "values" 사용, 나머지는 "x"와 "y" 사용

콘텐츠 규칙:
- 각 섹션 content는 마크다운 형식으로 구조화:
  - 2~3개 소제목(### 사용)으로 구분
  - 각 소제목 아래 1~2문단 (문단당 2~4문장)
  - 소제목은 한국어로, 해당 섹션의 핵심 내용을 요약
  - 용어 마킹(<mark> 태그)은 하지 마세요 (후처리에서 별도 처리)
- chart.layout.title에 반드시 한국어 차트 제목 포함 (8~20자)
- 구체성 필수: mirroring에 "종목명 + 연도 + 주가 변동폭" 포함
- background content 필수 포함: (1) 트리거 이벤트, (2) 관련 수치/데이터, (3) 시장 주목 이유
- simulation에는 반드시 "quiz" 객체 포함 (아래 형식 엄수)
- 실제 역사적 사건 기반, 2000-2023년 사이

simulation.quiz 형식 (필수):
{{
    "context": "mirroring의 과거 사례 1~2문장 요약",
    "question": "이 상황에서 시장은 어떻게 움직였을까요?",
    "options": [
        {{"id": "up", "label": "올랐어요", "explanation": "상승 이유 설명"}},
        {{"id": "down", "label": "내렸어요", "explanation": "하락 이유 설명"}},
        {{"id": "sideways", "label": "횡보했어요", "explanation": "횡보 이유 설명"}}
    ],
    "correct_answer": "up 또는 down 또는 sideways 중 하나",
    "actual_result": "실제 결과 (구체적 수치 포함, 2~3문장)",
    "lesson": "현재 상황에서의 시사점 (2~3문장)"
}}

다음 JSON 형식으로 응답 (chart의 type은 카탈로그에서 데이터에 맞게 선택):
{{
    "title": "과거 사례 제목",
    "event_year": 연도(숫자),
    "summary": "2-3문장 요약",
    "full_content": "3-5문단 상세 스토리텔링",
    "sync_rate": 유사도(60-90),
    "past_label": "과거 라벨",
    "present_label": "현재 라벨",
    "narrative": {{
        "background": {{"content": "### 소제목1\n내용 문단...\n\n### 소제목2\n내용 문단...", "chart": {{"data": [카탈로그에서 적합한 차트 유형 선택], "layout": {{"title": "한국어 제목", "xaxis": {{"title": ""}}, "yaxis": {{"title": ""}}}}}}}},
        "mirroring": {{"content": "### 소제목\n마크다운 구조 콘텐츠...", "chart": {{"data": [{{"x": [], "y": [], "type": "scatter", "name": "과거"}}, {{"x": [], "y": [], "type": "scatter", "name": "현재"}}], "layout": {{"title": "한국어 제목", "showlegend": true}}}}}},
        "simulation": {{"content": "### 소제목\n마크다운 구조 콘텐츠...", "chart": {{"data": [{{"x": ["시작","3개월","6개월","12개월"], "y": [], "type": "scatter", "name": "낙관"}}, {{"x": [...], "y": [], "type": "scatter", "name": "중립"}}, {{"x": [...], "y": [], "type": "scatter", "name": "비관"}}], "layout": {{"title": "1,000만원 투자 시뮬레이션", "showlegend": true}}}}, "quiz": {{...}}}},
        "result": {{"content": "### 소제목\n마크다운 구조 콘텐츠...", "chart": {{"data": [카탈로그에서 선택], "layout": {{"title": "시나리오별 수익률"}}}}}},
        "difference": {{"content": "### 소제목\n마크다운 구조 콘텐츠...", "chart": {{"data": [카탈로그에서 선택], "layout": {{"title": "한국어 제목", "barmode": "group"}}}}}},
        "devils_advocate": {{"content": "### 소제목\n마크다운 구조 콘텐츠...", "chart": {{"data": [카탈로그에서 선택], "layout": {{"title": "한국어 제목"}}}}}},
        "action": {{"content": "### 소제목\n마크다운 구조 콘텐츠...", "chart": {{"data": [{{"labels": ["항목1","항목2","항목3","항목4"], "values": [비중1,비중2,비중3,비중4], "type": "pie"}}], "layout": {{"title": "추천 포트폴리오 구성"}}}}}}
    }},
    "past_metric": {{"value": 숫자, "company": "종목명", "metric_name": "지표명"}},
    "present_metric": {{"value": 숫자, "metric_name": "지표명"}},
    "key_insight": "7단계 전체 스토리를 3~5문장으로 요약. background부터 action까지 핵심 흐름 서술.",
    "glossary_terms": ["용어1", "용어2"]
}}

JSON만 출력하세요."""

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=8000,
            )
            content = response.choices[0].message.content.strip()

            # JSON 파싱 (코드 블록 제거)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            case_data = json.loads(content)

            # 내러티브 검증
            narrative = case_data.get("narrative", {})
            if isinstance(narrative, dict):
                # 퀴즈 보장
                narrative = ensure_quiz_in_narrative(narrative, clean_title)
                case_data["narrative"] = narrative

                # 검증
                issues = validate_narrative(narrative)
                if issues:
                    logger.warning(f"  [검증 실패 attempt={attempt}] {issues}")
                    if attempt < MAX_RETRIES:
                        last_error = RuntimeError(f"검증 실패: {issues}")
                        continue
                    else:
                        # 마지막 시도: 검증 실패해도 반환 (부분 데이터라도 사용)
                        logger.warning(f"  [검증 최종 실패, 부분 데이터 사용] {issues}")
                else:
                    logger.info(f"  [검증 통과] 7개 섹션 + 퀴즈 정상")

            # 품질 메트릭 로깅
            _log_quality_metrics(narrative, clean_title)

            return case_data
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"  [RETRY {attempt}/{MAX_RETRIES}] JSON 파싱 실패: {e}")
            # 재시도 시 에러 피드백 프롬프트 추가
            if attempt < MAX_RETRIES:
                prompt = prompt + f"\n\n[이전 시도에서 JSON 파싱 오류 발생: {e}. 올바른 JSON만 출력해주세요.]"
        except Exception as e:
            last_error = e
            logger.warning(f"  [RETRY {attempt}/{MAX_RETRIES}] {e}")

    raise RuntimeError(f"LLM 생성 {MAX_RETRIES}회 실패: {last_error}")


def apply_term_marking(case_data: dict) -> dict:
    """후처리: 전체 콘텐츠 분석 → 핵심 용어/구문에 <mark class='term'> 태그 적용.

    1단계: 모든 섹션의 content를 하나로 합침
    2단계: LLM에게 용어/구문 목록 + 정의를 추출
    3단계: 원래 content에 <mark class='term'> 태그 적용
    4단계: key_insight를 dict로 래핑 + term_definitions 추가
    """
    narrative = case_data.get("narrative", {})
    if not isinstance(narrative, dict):
        return case_data

    # 1. 전체 콘텐츠 수집
    all_content = {}
    for key in REQUIRED_SECTIONS:
        section = narrative.get(key, {})
        if isinstance(section, dict):
            all_content[key] = section.get("content", "")

    full_text = "\n\n".join(f"[{k}]\n{v}" for k, v in all_content.items() if v)
    if len(full_text) < 200:
        logger.warning("  용어 마킹: 콘텐츠 부족으로 건너뜀")
        # key_insight dict 래핑만 수행
        raw = case_data.get("key_insight", "")
        if isinstance(raw, str):
            case_data["key_insight"] = {"summary": raw, "term_definitions": []}
        return case_data

    # 2. LLM 호출: 용어/구문 추출
    marking_prompt = f"""다음은 금융 교육 콘텐츠의 7개 섹션입니다.

{full_text}

위 텍스트에서 다음 유형의 용어와 구문을 추출하세요:
1. 핵심 금융 용어 (예: PER, 금리, 변동성, 포트폴리오)
2. 의미있는 금융 구문/절 (예: '변동성이 크게 확대된다', '시장 유동성이 풍부해진', '금리 인하 기대감')
3. 이해가 필요한 핵심 개념 (예: '섹터 로테이션', '캐리 트레이드')

규칙:
- 총 15~25개 추출
- 각 섹션당 2~4개가 되도록 분배
- 구문은 3~15단어 이내 자연스러운 절 단위
- 각 용어/구문에 초보자용 간단 정의(1문장) 포함
- sections 필드에 해당 용어가 등장하는 섹션 키 목록 포함

JSON 배열로만 응답:
[{{"text": "용어 또는 구문", "definition": "간단한 정의", "sections": ["background", "mirroring"]}}]
JSON만 출력하세요."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": marking_prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    raw_content = response.choices[0].message.content.strip()

    # JSON 파싱
    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.strip()

    terms = json.loads(raw_content)
    if not isinstance(terms, list):
        logger.warning("  용어 마킹: LLM 응답이 배열이 아님")
        terms = []

    logger.info(f"  용어 마킹: {len(terms)}개 추출")

    # 3. content에 <mark class='term'>...</mark> 태그 적용 (각 섹션 첫 등장만)
    for item in terms:
        text = item.get("text", "")
        if not text or len(text) < 2:
            continue
        for section_key in item.get("sections", []):
            section = narrative.get(section_key, {})
            if not isinstance(section, dict):
                continue
            content = section.get("content", "")
            marked = f"<mark class='term'>{text}</mark>"
            # 이미 마킹되어 있지 않은 경우에만 첫 등장 마킹
            if text in content and marked not in content:
                content = content.replace(text, marked, 1)
                section["content"] = content

    # 4. key_insight를 dict로 래핑 + term_definitions 추가
    raw_insight = case_data.get("key_insight", "")
    if isinstance(raw_insight, str):
        key_insight = {"summary": raw_insight, "term_definitions": []}
    else:
        key_insight = raw_insight

    # term_definitions에 추출된 용어 추가
    existing_terms = {td.get("term", "") for td in key_insight.get("term_definitions", [])}
    for item in terms:
        term_text = item.get("text", "")
        definition = item.get("definition", "")
        if term_text and term_text not in existing_terms:
            key_insight.setdefault("term_definitions", []).append({
                "term": term_text,
                "definition": definition,
            })

    case_data["key_insight"] = key_insight
    return case_data


def _log_quality_metrics(narrative: dict, keyword: str) -> None:
    """생성된 내러티브의 품질 지표를 로깅."""
    if not isinstance(narrative, dict):
        return

    sections_with_chart = 0
    chart_types = []
    total_content_len = 0
    mark_count = 0
    has_quiz = False

    for key in REQUIRED_SECTIONS:
        section = narrative.get(key, {})
        if not isinstance(section, dict):
            continue

        content = str(section.get("content", ""))
        total_content_len += len(content)
        mark_count += len(re.findall(r"<mark", content))

        chart = section.get("chart", {})
        if isinstance(chart, dict):
            data = chart.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                sections_with_chart += 1
                trace = data[0]
                if isinstance(trace, dict):
                    chart_types.append(trace.get("type", "unknown"))

        if key == "simulation" and isinstance(section.get("quiz"), dict):
            has_quiz = True

    avg_content_len = total_content_len / max(len(REQUIRED_SECTIONS), 1)
    type_dist = {}
    for ct in chart_types:
        type_dist[ct] = type_dist.get(ct, 0) + 1

    # 차트 유형 다양성 체크
    unique_types = set(chart_types)
    if len(unique_types) == 1 and len(chart_types) >= 5:
        logger.warning(f"  [품질 경고] chart type 다양성 부족: {type_dist} (모두 {list(unique_types)[0]})")

    logger.info(
        f"  [품질] keyword={keyword} "
        f"charts={sections_with_chart}/7 "
        f"chart_types={type_dist} "
        f"unique={len(unique_types)} "
        f"quiz={has_quiz} "
        f"avg_content={avg_content_len:.0f}자 "
        f"marks={mark_count}"
    )


async def main():
    import asyncpg

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
        raise SystemExit(1)
    db_url = db_url.replace("+asyncpg", "")

    print(f"=== Historical Cases 생성 시작 ===")
    print(f"DB: {db_url}")

    conn = await asyncpg.connect(db_url)

    # 1. 기존 데이터 확인 및 정리 (선택적)
    existing_cases = await conn.fetchval("SELECT COUNT(*) FROM historical_cases")
    existing_matches = await conn.fetchval("SELECT COUNT(*) FROM case_matches")
    existing_relations = await conn.fetchval("SELECT COUNT(*) FROM case_stock_relations")
    print(f"기존 데이터 - cases: {existing_cases}, matches: {existing_matches}, relations: {existing_relations}")

    # 기존 데이터 삭제 (트랜잭션으로 원자적 처리)
    async with conn.transaction():
        if existing_relations > 0:
            await conn.execute("DELETE FROM case_stock_relations")
        if existing_matches > 0:
            await conn.execute("DELETE FROM case_matches")
        if existing_cases > 0:
            await conn.execute("DELETE FROM historical_cases")
    logger.info("기존 데이터 삭제 완료")

    # 2. 최신 briefing에서 키워드 가져오기
    row = await conn.fetchrow("""
        SELECT id, briefing_date, top_keywords
        FROM daily_briefings
        WHERE top_keywords IS NOT NULL
        ORDER BY briefing_date DESC
        LIMIT 1
    """)

    if not row:
        print("[ERROR] daily_briefings에 키워드 데이터가 없습니다. seed_fresh_data.py를 먼저 실행하세요.")
        await conn.close()
        return

    briefing_id = row["id"]
    briefing_date = row["briefing_date"]
    top_keywords = row["top_keywords"] if isinstance(row["top_keywords"], dict) else json.loads(row["top_keywords"])
    keywords = top_keywords.get("keywords", [])

    print(f"Briefing ID: {briefing_id}, 날짜: {briefing_date}")
    print(f"키워드 {len(keywords)}개 발견")

    # 3. OPENAI_API_KEY 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("[FATAL] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        await conn.close()
        raise SystemExit(1)

    # 종목명 캐시 빌드 (pykrx 중복 호출 방지)
    stock_name_cache = {}
    for kw in keywords:
        for s in kw.get("stocks", []):
            if isinstance(s, dict) and s.get("stock_code") and s.get("stock_name"):
                stock_name_cache[s["stock_code"]] = s["stock_name"]

    # 4. 각 키워드에 대해 historical_case 생성
    import time as _time
    pipeline_start = _time.time()
    failed = []
    for i, kw in enumerate(keywords):
        kw_title = kw.get("title", "")
        kw_category = kw.get("category", "")
        kw_stocks = kw.get("stocks", [])

        if not kw_title:
            logger.info(f"[{i+1}/{len(keywords)}] SKIP - 제목 없음")
            continue

        elapsed = _time.time() - pipeline_start
        avg_per_kw = elapsed / max(i, 1)
        remaining = avg_per_kw * (len(keywords) - i - 1)
        logger.info(f"[{i+1}/{len(keywords)}] {kw_title}" + (f" (예상 잔여: {remaining:.0f}초)" if i > 0 else ""))

        # stocks에서 코드 추출
        stock_codes = [
            s.get("stock_code", "") if isinstance(s, dict) else s
            for s in kw_stocks
        ]

        # pykrx로 실시간 주가 데이터 조회
        stock_data = fetch_stock_data(stock_codes)
        if stock_data:
            logger.info(f"  pykrx 데이터 로드 완료 ({len(stock_codes)}종목)")

        # LLM으로 사례 생성 (pykrx 데이터 주입)
        try:
            case_data = generate_historical_case(kw_title, kw_category, stock_codes, stock_data)
        except RuntimeError as e:
            print(f"  [SKIP] {e}")
            failed.append(kw_title)
            continue

        # 후처리: 용어/구문 마킹 + key_insight dict 변환
        try:
            case_data = apply_term_marking(case_data)
            logger.info("  용어 마킹 후처리 완료")
        except Exception as e:
            logger.warning(f"  용어 마킹 후처리 실패 (원본 사용): {e}")
            raw = case_data.get("key_insight", "")
            if isinstance(raw, str):
                case_data["key_insight"] = {"summary": raw, "term_definitions": []}

        # historical_cases에 삽입 (7단계 narrative 포함)
        keywords_jsonb = json.dumps({
            "comparison": {
                "past_metric": case_data.get("past_metric", {}),
                "present_metric": case_data.get("present_metric", {}),
                "sync_rate": case_data.get("sync_rate", 70),
                "past_label": case_data.get("past_label", "과거"),
                "present_label": case_data.get("present_label", "현재"),
            },
            "narrative": case_data.get("narrative", {}),
            "glossary_terms": case_data.get("glossary_terms", []),
            "key_insight": case_data.get("key_insight", {"summary": "", "term_definitions": []})
        }, ensure_ascii=False)

        # event_year 검증
        event_year = case_data.get("event_year", 2000)
        if not isinstance(event_year, int) or not (1900 <= event_year <= datetime.now().year):
            logger.warning(f"  event_year 범위 초과: {event_year}, 기본값 2000 사용")
            event_year = 2000

        case_id = await conn.fetchval("""
            INSERT INTO historical_cases
            (title, event_year, summary, full_content, keywords, difficulty, view_count, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, 'beginner', 0, NOW(), NOW())
            RETURNING id
        """,
            case_data.get("title", ""),
            event_year,
            case_data.get("summary", ""),
            case_data.get("full_content", ""),
            keywords_jsonb
        )
        print(f"  → historical_cases: id={case_id}")

        # case_matches에 삽입
        stock_code = stock_codes[0] if stock_codes else None
        match_id = await conn.fetchval("""
            INSERT INTO case_matches
            (current_keyword, current_stock_code, matched_case_id, similarity_score, match_reason, matched_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """,
            kw_title,
            stock_code,
            case_id,
            case_data.get("sync_rate", 70) / 100.0,  # 0-1 범위로 변환
            (case_data.get("key_insight", {}).get("summary", "") if isinstance(case_data.get("key_insight"), dict) else case_data.get("key_insight", "")) or "유사한 시장 패턴"
        )
        print(f"  → case_matches: id={match_id}")

        # case_stock_relations에 삽입 (키워드 관련 종목들)
        for j, sc in enumerate(stock_codes):
            stock_code = sc
            # 종목명 조회 (캐시 우선, kw_stocks 폴백)
            if j < len(kw_stocks) and isinstance(kw_stocks[j], dict):
                stock_name = kw_stocks[j].get("stock_name", "")
            if not stock_name:
                stock_name = stock_name_cache.get(stock_code, f"종목 {stock_code}")

            relation_type = "main_subject" if j == 0 else "related"
            rel_id = await conn.fetchval("""
                INSERT INTO case_stock_relations
                (case_id, stock_code, stock_name, relation_type, impact_description)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """,
                case_id,
                stock_code,
                stock_name,
                relation_type,
                f"{kw_category} 관련 종목"
            )
            print(f"  → case_stock_relations: id={rel_id} ({stock_code} - {stock_name})")

    # 5. 최종 확인
    final_cases = await conn.fetchval("SELECT COUNT(*) FROM historical_cases")
    final_matches = await conn.fetchval("SELECT COUNT(*) FROM case_matches")
    final_relations = await conn.fetchval("SELECT COUNT(*) FROM case_stock_relations")

    print(f"\n=== 생성 완료 ===")
    print(f"historical_cases: {final_cases}건")
    print(f"case_matches: {final_matches}건")
    print(f"case_stock_relations: {final_relations}건")
    if failed:
        print(f"실패 ({len(failed)}건): {failed}")

    await conn.close()

    if failed:
        raise SystemExit(f"{len(failed)}건 실패")


if __name__ == "__main__":
    asyncio.run(main())
