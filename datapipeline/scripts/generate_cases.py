"""
Historical Cases 생성 스크립트 (6페이지 골든케이스)
- 각 키워드에 대해 LLM으로 역사적 유사 사례 + 6페이지 내러티브 생성
- pykrx 실시간 주가 데이터 주입으로 구체성 향상
- 페이지별 glossary + sources + hallucination_checklist 포함
- historical_cases, case_matches, case_stock_relations 테이블에 삽입
- LangSmith @traceable 트레이싱 연동
"""
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 추가
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from datapipeline.ai.multi_provider_client import get_multi_provider_client
from datapipeline.scripts.pipeline_config import (
    PAGE_KEYS,
    MAX_RETRIES,
    MIN_CONTENT_LENGTH,
    MIN_BULLETS,
    MIN_GLOSSARY,
    MIN_UNIQUE_CHART_TYPES,
)

# LangSmith traceable (없으면 no-op)
try:
    from langsmith import traceable
except ImportError:
    def traceable(**kwargs):
        def decorator(func):
            return func
        return decorator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# MultiProviderClient (OpenAI/Perplexity/Anthropic 통합)
client = get_multi_provider_client()

# 프롬프트 파일 경로
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    """프롬프트 파일 로드."""
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning(f"프롬프트 파일 없음: {path}, 인라인 fallback 사용")
    return ""


def strip_marks(text: str) -> str:
    """<mark class='term'>...</mark> 태그 제거."""
    return re.sub(r"<mark\s+class=['\"]term['\"]>(.*?)</mark>", r"\1", text)


def fetch_stock_data(stock_codes: list[str]) -> str:
    """pykrx로 종목별 90일 OHLCV 요약 데이터 + 재무지표 + 애널리스트 리포트 조회."""
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
            avg_trade_val = int(df["거래대금"].mean()) if "거래대금" in df.columns else 0
            lines.append(
                f"- {name}({code}): 현재가 {current:,}원, 90일 등락률 {change_pct:+}%, "
                f"90일 고가 {high:,}원, 저가 {low:,}원, 평균거래량 {avg_vol:,}주"
                + (f", 평균거래대금 {avg_trade_val:,}원" if avg_trade_val else "")
            )

            # 재무지표 (PER/PBR/EPS) 추가
            try:
                from datapipeline.collectors.financial_collector import format_fundamentals_for_llm
                fundamentals = format_fundamentals_for_llm(code)
                if fundamentals and "찾을 수 없습니다" not in fundamentals:
                    lines.append(fundamentals)
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"  재무지표 조회 실패 ({code}): {e}")

        except Exception as e:
            logger.warning(f"  pykrx 조회 실패 ({code}): {e}")
            continue

    # 애널리스트 리포트 조회 (종목명 기반 필터링)
    try:
        from datapipeline.collectors.naver_report_crawler import fetch_report_list
        import asyncio
        reports = asyncio.get_event_loop().run_until_complete(fetch_report_list(page=1))
        stock_names = set()
        for code in stock_codes[:3]:
            if code:
                try:
                    stock_names.add(pykrx_stock.get_market_ticker_name(code) or "")
                except Exception:
                    pass
        matched = [r for r in reports if r.stock_name in stock_names]
        for r in matched[:3]:
            report_line = f"- [리포트] {r.stock_name}: {r.title} ({r.broker}, {r.date})"
            if r.target_price:
                report_line += f" 목표가: {r.target_price}"
            if r.opinion:
                report_line += f" 투자의견: {r.opinion}"
            lines.append(report_line)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"  애널리스트 리포트 조회 실패: {e}")

    return "\n".join(lines) if lines else ""


def validate_narrative(narrative: dict) -> list[str]:
    """6페이지 골든케이스 구조 검증 (강화 버전). 문제점 리스트 반환."""
    issues = []
    chart_types_seen = []

    for key in PAGE_KEYS:
        if key not in narrative:
            issues.append(f"섹션 누락: {key}")
            continue
        section = narrative[key]
        if not isinstance(section, dict):
            issues.append(f"{key}: dict가 아님")
            continue

        # content 최소 길이 (강화: 50 → MIN_CONTENT_LENGTH)
        content = str(section.get("content", ""))
        if len(content) < MIN_CONTENT_LENGTH:
            issues.append(f"{key}: content {len(content)}자 ({MIN_CONTENT_LENGTH}자 미만)")

        # 해요체 검증 (경고만, 실패는 아님)
        formal_patterns = re.findall(r"(?:합니다|입니다|했습니다|됩니다|있습니다)", content)
        if formal_patterns:
            logger.warning(f"  [해요체 위반] {key}: {formal_patterns[:3]}")

        # bullets 검증 (강화: 2 → MIN_BULLETS)
        bullets = section.get("bullets", [])
        if not isinstance(bullets, list) or len(bullets) < MIN_BULLETS:
            issues.append(f"{key}: bullets {len(bullets) if isinstance(bullets, list) else 0}개 ({MIN_BULLETS}개 미만)")

        # glossary 검증 (강화: 존재만 → MIN_GLOSSARY 이상)
        glossary = section.get("glossary", [])
        if not isinstance(glossary, list):
            issues.append(f"{key}: glossary가 list가 아님")
        elif len(glossary) < MIN_GLOSSARY:
            issues.append(f"{key}: glossary {len(glossary)}개 ({MIN_GLOSSARY}개 미만)")

        # chart 검증 (null 허용 - caution 등)
        chart = section.get("chart")
        if chart is not None and isinstance(chart, dict):
            data = chart.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                trace = data[0]
                if isinstance(trace, dict):
                    trace_type = trace.get("type", "scatter")
                    chart_types_seen.append(trace_type)

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

    # 차트 유형 다양성 체크 (강화)
    unique_chart_types = set(chart_types_seen)
    if len(chart_types_seen) >= 3 and len(unique_chart_types) < MIN_UNIQUE_CHART_TYPES:
        issues.append(f"차트 유형 다양성 부족: {len(unique_chart_types)}종류 ({MIN_UNIQUE_CHART_TYPES}종류 미만) - {chart_types_seen}")

    return issues


@traceable(name="generate_historical_case", run_type="llm")
def generate_historical_case(keyword_title: str, category: str, stocks: list[str], stock_data: str = "") -> dict:
    """LLM으로 역사적 유사 사례 + 6페이지 골든케이스 내러티브 생성."""
    clean_title = strip_marks(keyword_title)

    stock_data_section = ""
    if stock_data:
        stock_data_section = f"""
실시간 종목 데이터 (pykrx 90일):
{stock_data}
위 수치를 활용하여 구체적인 내러티브를 작성하세요. 추상적 매크로 주제 대신 해당 종목/섹터의 구체적 이벤트 중심으로 작성하세요.
차트에는 반드시 위 실제 데이터를 반영하세요.
"""

    # 프롬프트 파일 로드
    prompt_template = _load_prompt("generate_case_v1.md")
    if prompt_template:
        prompt = prompt_template.format(
            keyword=clean_title,
            category=category,
            stocks=stocks,
            stock_data_section=stock_data_section,
        )
    else:
        # fallback: 인라인 프롬프트 (기존 호환)
        prompt = _build_inline_prompt(clean_title, category, stocks, stock_data_section)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat_completion(
                provider="openai",
                model=os.getenv("OPENAI_MAIN_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=12000,
            )
            content = response["choices"][0]["message"]["content"].strip()

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
                        # 검증 실패 피드백을 프롬프트에 추가
                        prompt = prompt + f"\n\n[이전 시도 검증 실패: {'; '.join(issues)}. 각 페이지 content 250자 이상, bullets 3개 이상, glossary 1개 이상으로 수정해주세요.]"
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


def _build_inline_prompt(keyword: str, category: str, stocks: list, stock_data_section: str) -> str:
    """프롬프트 파일 없을 때 인라인 fallback."""
    return f"""당신은 친근한 금융 학습 메이트 '아델리'입니다. 2030세대를 위한 금융 교육 콘텐츠를 만듭니다.
현재 키워드: "{keyword}" (카테고리: {category})
관련 종목 코드: {stocks}
{stock_data_section}

=== 과제 ===
이 키워드와 유사한 과거 한국 주식 시장의 역사적 사례를 선정하고, 6페이지 브리핑 콘텐츠를 생성하세요.

=== 6페이지: background, concept_explain, history, application, caution, summary ===

=== 콘텐츠 규칙 ===
- 해요체 필수, 각 페이지 content 250~500자, bullets 3~5개, glossary 2~3개
- 6페이지에서 최소 4가지 다른 차트 유형 사용
- caution은 chart: null 가능

JSON만 출력하세요."""


@traceable(name="apply_term_marking", run_type="llm")
def apply_term_marking(case_data: dict) -> dict:
    """후처리: 전체 콘텐츠 분석 -> 핵심 용어/구문에 <mark class='term'> 태그 적용."""
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
    marking_template = _load_prompt("term_marking_v1.md")
    if marking_template:
        marking_prompt = marking_template.format(full_text=full_text)
    else:
        marking_prompt = f"""다음은 금융 교육 콘텐츠의 6개 섹션입니다.

{full_text}

위 텍스트에서 핵심 금융 용어/구문 15~25개를 추출하세요.
JSON 배열로만 응답:
[{{"text": "용어", "definition": "간단한 정의", "sections": ["background"]}}]
JSON만 출력하세요."""

    response = client.chat_completion(
        provider="openai",
        model=os.getenv("OPENAI_MAIN_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": marking_prompt}],
        temperature=0.3,
        max_tokens=2000,
    )
    raw_content = response["choices"][0]["message"]["content"].strip()

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
    total_bullets = 0
    total_glossary = 0
    mark_count = 0

    for key in PAGE_KEYS:
        section = narrative.get(key, {})
        if not isinstance(section, dict):
            continue

        content = str(section.get("content", ""))
        total_content_len += len(content)
        mark_count += len(re.findall(r"<mark", content))

        bullets = section.get("bullets", [])
        total_bullets += len(bullets) if isinstance(bullets, list) else 0

        glossary = section.get("glossary", [])
        total_glossary += len(glossary) if isinstance(glossary, list) else 0

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

    logger.info(
        f"  [품질] keyword={keyword} "
        f"charts={sections_with_chart}/6 "
        f"chart_types={type_dist} "
        f"unique={len(unique_types)} "
        f"avg_content={avg_content_len:.0f}자 "
        f"total_bullets={total_bullets} "
        f"total_glossary={total_glossary} "
        f"marks={mark_count}"
    )

    # 품질 경고
    if avg_content_len < MIN_CONTENT_LENGTH:
        logger.warning(f"  [품질 경고] avg_content {avg_content_len:.0f}자 < {MIN_CONTENT_LENGTH}자 목표")
    if len(unique_types) < MIN_UNIQUE_CHART_TYPES and len(chart_types) >= 3:
        logger.warning(f"  [품질 경고] chart type 다양성 부족: {type_dist}")


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
        print(f"  -> historical_cases: id={case_id}")

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
        print(f"  -> case_matches: id={match_id}")

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
            print(f"  -> case_stock_relations: id={rel_id} ({stock_code} - {stock_name})")

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
