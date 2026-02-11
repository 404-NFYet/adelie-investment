"""
Historical Cases 생성 스크립트 (6페이지 골든케이스)
- 각 키워드에 대해 LLM으로 역사적 유사 사례 + 6페이지 내러티브 생성
- pykrx 실시간 주가 데이터 주입으로 구체성 향상
- 페이지별 glossary + sources + hallucination_checklist 포함
- historical_cases, case_matches, case_stock_relations 테이블에 삽입
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from openai import OpenAI

from pipeline_config import PAGE_KEYS, MAX_RETRIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def strip_marks(text: str) -> str:
    """<mark class='term'>...</mark> 태그 제거."""
    return re.sub(r"<mark\s+class=['\"]term['\"]>(.*?)</mark>", r"\1", text)


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
    """6페이지 골든케이스 구조 검증. 문제점 리스트 반환 (빈 리스트=정상)."""
    issues = []

    # 6개 섹션 존재 확인
    for key in PAGE_KEYS:
        if key not in narrative:
            issues.append(f"섹션 누락: {key}")
            continue
        section = narrative[key]
        if not isinstance(section, dict):
            issues.append(f"{key}: dict가 아님")
            continue

        # content 최소 길이
        content = section.get("content", "")
        if len(str(content)) < 50:
            issues.append(f"{key}: content 50자 미만")

        # bullets 검증
        bullets = section.get("bullets", [])
        if not isinstance(bullets, list) or len(bullets) < 2:
            issues.append(f"{key}: bullets 2개 미만")

        # glossary 검증
        glossary = section.get("glossary", [])
        if not isinstance(glossary, list):
            issues.append(f"{key}: glossary가 list가 아님")

        # chart 검증 (null 허용 - caution 등)
        chart = section.get("chart")
        if chart is not None and isinstance(chart, dict):
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

    return issues


def generate_historical_case(keyword_title: str, category: str, stocks: list[str], stock_data: str = "") -> dict:
    """LLM으로 역사적 유사 사례 + 6페이지 골든케이스 내러티브 생성."""
    clean_title = strip_marks(keyword_title)

    stock_data_section = ""
    if stock_data:
        stock_data_section = f"""
실시간 종목 데이터 (pykrx 90일):
{stock_data}
위 수치를 활용하여 구체적인 내러티브를 작성하세요. 추상적 매크로 주제 대신 해당 종목/섹터의 구체적 이벤트 중심으로 작성하세요.
"""

    prompt = f"""당신은 친근한 금융 학습 메이트 '아델리'입니다. 2030세대를 위한 금융 교육 콘텐츠를 만듭니다.
현재 키워드: "{clean_title}" (카테고리: {category})
관련 종목 코드: {stocks}
{stock_data_section}

=== 과제 ===
이 키워드와 유사한 과거 한국 주식 시장의 역사적 사례를 선정하고, 6페이지 브리핑 콘텐츠를 생성하세요.

=== 6페이지 구조 ===
1. background (현재 배경) — 독자의 주의를 환기하고, 왜 지금 읽어야 하는지 설득
2. concept_explain (금융 개념 설명) — 이 시나리오의 핵심 금융 개념 1개를 초보자용으로 설명
3. history (과거 비슷한 사례) — 과거 유사 사례를 비교하여 패턴 학습
4. application (현재 상황에 적용) — 과거 교훈을 현재 상황에 3가지 포인트로 적용
5. caution (주의해야 할 점) — 반대 시나리오 3가지를 제시하여 균형 잡힌 시각 부여
6. summary (최종 정리) — 요약 + 독자가 실제로 써먹을 수 있는 관찰 지표 3가지

=== 차트 유형 카탈로그 (Plotly 기반) ===
데이터 특성에 맞는 차트를 선택하세요:
- 시계열 추세 → scatter (mode:"lines+markers") 또는 fill:"tozeroy" (area)
- 두 시계열 비교 → multi-trace scatter
- 항목별 수치 비교 → bar (vertical)
- 순위/랭킹/중요도 → bar (orientation:"h")
- 과거 vs 현재 비교 → grouped bar (barmode:"group", 2 traces)
- 비율/구성 → pie (labels:[], values:[])
- chart가 불필요한 페이지(텍스트 설명이 더 적절) → "chart": null

차트 규칙:
- 실제 데이터 기반: pykrx 종목 데이터가 제공되면 실제 수치를 반영
- 맥락적 수치: 해당 케이스의 맥락에 맞는 단위 사용 (원, 조원, %, 달러 등)
- y축 단위 필수: layout.yaxis.title에 단위 명시
- chart.layout.title에 한국어 차트 제목 포함 (8~20자)
- 컬러 팔레트: ["#FF6B35", "#004E89", "#1A936F", "#C5D86D", "#8B95A1"]
- 모바일: 최대 4개 시리즈, 폰트 12px 이상, 범례는 하단
- 6페이지에서 최소 3가지 이상 다른 차트 유형 사용
- caution 페이지는 chart: null 가능 (텍스트 중심)

=== 콘텐츠 규칙 ===
- 해요체 필수: "~했어요", "~이에요", "~할까요?" (절대 "~합니다", "~입니다" 사용 금지)
- 각 페이지 content: 150~300자 (짧고 임팩트 있게)
- 첫 문장은 반드시 훅 (관심을 끄는 팩트 또는 질문)
- bullets: 2~3개 (핵심 포인트만)
- 투자 조언 금지: "매수", "매도", "추천" 등 사용 금지 → "점검이 필요해요", "주목할 지표예요" 등으로 대체
- 용어 마킹(<mark> 태그) 하지 마세요 (후처리에서 별도 처리)
- 실제 역사적 사건 기반, 2000~2025년 사이

=== 페이지별 glossary 규칙 ===
- 각 페이지에 해당 내용에서 등장하는 용어 1~3개 설명
- 해요체 정의 (초보자용)
- domain 태그: 금융, 경제, 산업, 국제, 기술 등

=== JSON 출력 형식 ===
{{
    "title": "과거 사례 제목",
    "event_year": 연도(숫자),
    "summary": "2-3문장 요약",
    "full_content": "3-5문단 상세 스토리텔링",
    "theme": "현재 시나리오 전체 제목 (한국어)",
    "one_liner": "1줄 요약 (해요체, 관심을 끄는 훅)",
    "concept": {{
        "name": "핵심 금융 개념명",
        "definition": "초보자용 정의 (해요체)",
        "relevance": "이 시나리오에서 왜 중요한지 (해요체)"
    }},
    "historical_case": {{
        "period": "2022-2024",
        "title": "과거 사례 제목",
        "summary": "3-5문장 요약 (해요체)",
        "outcome": "1-2문장 결과 (해요체)",
        "lesson": "1-2문장 교훈 (해요체)"
    }},
    "sync_rate": 유사도(60-90),
    "past_label": "과거 라벨",
    "present_label": "현재 라벨",
    "narrative": {{
        "background": {{
            "content": "150-300자 본문 (해요체)",
            "bullets": ["포인트1", "포인트2"],
            "chart": {{"data": [...], "layout": {{"title": "한국어 제목", "yaxis": {{"title": "단위"}}}}}},
            "glossary": [{{"term": "용어", "definition": "해요체 정의", "domain": "금융"}}]
        }},
        "concept_explain": {{
            "content": "150-300자 본문 (해요체)",
            "bullets": ["포인트1", "포인트2"],
            "chart": {{"data": [...], "layout": {{"title": "한국어 제목"}}}},
            "glossary": [{{"term": "용어", "definition": "정의", "domain": "금융"}}]
        }},
        "history": {{
            "content": "150-300자 본문 (해요체)",
            "bullets": ["포인트1", "포인트2"],
            "chart": {{"data": [...], "layout": {{"title": "한국어 제목"}}}},
            "glossary": [...]
        }},
        "application": {{
            "content": "150-300자 본문 (해요체)",
            "bullets": ["포인트1", "포인트2", "포인트3"],
            "chart": {{"data": [...], "layout": {{"title": "한국어 제목"}}}},
            "glossary": [...]
        }},
        "caution": {{
            "content": "150-300자 본문 (해요체)",
            "bullets": ["반대 논거1", "반대 논거2", "반대 논거3"],
            "chart": null,
            "glossary": [...]
        }},
        "summary": {{
            "content": "150-300자 본문 (해요체, 관찰 지표 3가지 포함)",
            "bullets": ["핵심 요약1", "핵심 요약2"],
            "chart": {{"data": [{{"y": ["지표1","지표2","지표3"], "x": [7,8,9], "type": "bar", "orientation": "h"}}], "layout": {{"title": "핵심 관찰 지표"}}}},
            "glossary": [...]
        }}
    }},
    "sources": [
        {{"name": "출처명", "url_domain": "도메인", "used_in_pages": [1,3]}}
    ],
    "hallucination_checklist": [
        {{"claim": "주장 내용", "source": "출처", "risk": "낮음|중간|높음", "note": "비고"}}
    ],
    "past_metric": {{"value": 숫자, "company": "종목명", "metric_name": "지표명"}},
    "present_metric": {{"value": 숫자, "metric_name": "지표명"}},
    "key_insight": "6페이지 전체 스토리를 3~5문장으로 요약 (해요체)",
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
                issues = validate_narrative(narrative)
                if issues:
                    logger.warning(f"  [검증 실패 attempt={attempt}] {issues}")
                    if attempt < MAX_RETRIES:
                        last_error = RuntimeError(f"검증 실패: {issues}")
                        continue
                    else:
                        logger.warning(f"  [검증 최종 실패, 부분 데이터 사용] {issues}")
                else:
                    logger.info(f"  [검증 통과] 6개 섹션 정상")

            # 품질 메트릭 로깅
            _log_quality_metrics(narrative, clean_title)

            return case_data
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"  [RETRY {attempt}/{MAX_RETRIES}] JSON 파싱 실패: {e}")
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
    for key in PAGE_KEYS:
        section = narrative.get(key, {})
        if isinstance(section, dict):
            all_content[key] = section.get("content", "")

    full_text = "\n\n".join(f"[{k}]\n{v}" for k, v in all_content.items() if v)
    if len(full_text) < 200:
        logger.warning("  용어 마킹: 콘텐츠 부족으로 건너뜀")
        raw = case_data.get("key_insight", "")
        if isinstance(raw, str):
            case_data["key_insight"] = {"summary": raw, "term_definitions": []}
        return case_data

    # 2. LLM 호출: 용어/구문 추출
    marking_prompt = f"""다음은 금융 교육 콘텐츠의 6개 섹션입니다.

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
[{{"text": "용어 또는 구문", "definition": "간단한 정의", "sections": ["background", "history"]}}]
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
            if text in content and marked not in content:
                content = content.replace(text, marked, 1)
                section["content"] = content

    # 4. key_insight를 dict로 래핑 + term_definitions 추가
    raw_insight = case_data.get("key_insight", "")
    if isinstance(raw_insight, str):
        key_insight = {"summary": raw_insight, "term_definitions": []}
    else:
        key_insight = raw_insight

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

    for key in PAGE_KEYS:
        section = narrative.get(key, {})
        if not isinstance(section, dict):
            continue

        content = str(section.get("content", ""))
        total_content_len += len(content)
        mark_count += len(re.findall(r"<mark", content))

        chart = section.get("chart")
        if isinstance(chart, dict):
            data = chart.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                sections_with_chart += 1
                trace = data[0]
                if isinstance(trace, dict):
                    chart_types.append(trace.get("type", "unknown"))

    avg_content_len = total_content_len / max(len(PAGE_KEYS), 1)
    type_dist = {}
    for ct in chart_types:
        type_dist[ct] = type_dist.get(ct, 0) + 1

    unique_types = set(chart_types)
    if len(unique_types) == 1 and len(chart_types) >= 4:
        logger.warning(f"  [품질 경고] chart type 다양성 부족: {type_dist}")

    logger.info(
        f"  [품질] keyword={keyword} "
        f"charts={sections_with_chart}/6 "
        f"chart_types={type_dist} "
        f"unique={len(unique_types)} "
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

    print(f"=== Historical Cases 생성 시작 (6페이지 골든케이스) ===")
    print(f"DB: {db_url}")

    conn = await asyncpg.connect(db_url)

    # 1. 기존 데이터 확인 및 정리
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

        # historical_cases에 삽입 (6페이지 골든케이스 포함)
        keywords_jsonb = json.dumps({
            "theme": case_data.get("theme", ""),
            "one_liner": case_data.get("one_liner", ""),
            "concept": case_data.get("concept", {}),
            "historical_case": case_data.get("historical_case", {}),
            "comparison": {
                "past_metric": case_data.get("past_metric", {}),
                "present_metric": case_data.get("present_metric", {}),
                "sync_rate": case_data.get("sync_rate", 70),
                "past_label": case_data.get("past_label", "과거"),
                "present_label": case_data.get("present_label", "현재"),
            },
            "narrative": case_data.get("narrative", {}),
            "sources": case_data.get("sources", []),
            "hallucination_checklist": case_data.get("hallucination_checklist", []),
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
            case_data.get("sync_rate", 70) / 100.0,
            (case_data.get("key_insight", {}).get("summary", "") if isinstance(case_data.get("key_insight"), dict) else case_data.get("key_insight", "")) or "유사한 시장 패턴"
        )
        print(f"  → case_matches: id={match_id}")

        # case_stock_relations에 삽입
        for j, sc in enumerate(stock_codes):
            stock_code = sc
            stock_name = ""
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

    print(f"\n=== 생성 완료 (6페이지 골든케이스) ===")
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
