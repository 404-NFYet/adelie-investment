"""
Historical Cases 생성 스크립트
- 각 키워드에 대해 LLM으로 역사적 유사 사례 생성
- historical_cases, case_matches, case_stock_relations 테이블에 삽입
"""
import asyncio
import json
import os
import re
from datetime import datetime
from openai import OpenAI

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def strip_marks(text: str) -> str:
    """<mark class='term'>...</mark> 태그 제거."""
    return re.sub(r"<mark\s+class=['\"]term['\"]>(.*?)</mark>", r"\1", text)


MAX_RETRIES = 2


def generate_historical_case(keyword_title: str, category: str, stocks: list[str]) -> dict:
    """LLM으로 역사적 유사 사례 + 7단계 narrative 생성. 실패 시 예외를 그대로 raise한다."""
    clean_title = strip_marks(keyword_title)

    prompt = f"""당신은 친근한 금융 학습 메이트 '아델리'입니다. 한국 주식 시장 역사 전문가이기도 합니다.
현재 키워드: "{clean_title}" (카테고리: {category})
관련 종목 코드: {stocks}

이 키워드와 유사한 과거 한국 주식 시장의 역사적 사례를 생성하고, 7단계 내러티브를 작성해주세요.

7단계 섹션:
1. background — 현재 배경 (지금 왜 이게 이슈인지)
2. mirroring — 과거 유사 사례 (어떤 시절과 비슷한지)
3. difference — 지금은 이게 달라요 (과거와의 차이)
4. devils_advocate — 반대 시나리오 3가지 (이런 관점도 있어요)
5. simulation — 모의 투자 (과거 사례로 시뮬레이션)
6. result — 결과 보고 (시뮬레이션 결과)
7. action — 실전 액션 (실전 전략)

규칙:
- 각 섹션 content는 2~3문장, 핵심 용어를 <mark class="term">단어</mark>로 감싸기 (섹션당 1~2개)
- background content 필수 포함: (1) 왜 지금 시장에서 중요한지 (트리거 이벤트), (2) 관련 수치/데이터, (3) 시장 참여자들이 주목하는 이유
- 모든 섹션에 Plotly chart 포함: data:[{{x:[],y:[],type,name}}], layout:{{title,xaxis:{{title}},yaxis:{{title}}}}
- 차트 요구사항: (1) 실제 연도/날짜 사용 (예: 2020, 2021, 2022), (2) 실제 수치 사용 (0이나 빈 값 금지), (3) title은 한국어로 간결하게, (4) xaxis.title, yaxis.title 필수
- bullets 포맷 규칙: (1) 종목명 포함 시 "종목명 (코드)" 형식 (예: "삼성전자 (005930)"), (2) 빈 괄호 () 금지, (3) 수치 포함 시 "종목명: 지표 값" 형식 (예: "삼성전자: PER 12.5배")
- devils_advocate의 bullets는 반드시 3개 (반대 포인트)
- simulation에는 투자 금액, 기간, 수익률이 포함된 chart
- 실제 역사적 사건 기반, 2000-2023년 사이

다음 JSON 형식으로 응답:
{{
    "title": "과거 사례 제목",
    "event_year": 연도(숫자),
    "summary": "2-3문장 요약",
    "full_content": "3-5문단 상세 스토리텔링",
    "sync_rate": 유사도(60-90),
    "past_label": "과거 라벨",
    "present_label": "현재 라벨",
    "narrative": {{
        "background": {{"bullets": ["포인트1", "포인트2"], "content": "현재 배경 설명", "chart": {{"data": [{{"x": [], "y": [], "type": "bar", "name": ""}}], "layout": {{"title": ""}}}}}},
        "mirroring": {{"bullets": [], "content": "과거 유사 사례 설명", "chart": {{"data": [], "layout": {{}}}}}},
        "difference": {{"bullets": [], "content": "과거와 현재 차이 설명", "chart": {{"data": [], "layout": {{}}}}}},
        "devils_advocate": {{"bullets": ["반대포인트1", "반대포인트2", "반대포인트3"], "content": "반대 시나리오 설명", "chart": {{"data": [], "layout": {{}}}}}},
        "simulation": {{"bullets": [], "content": "시뮬레이션 설명", "chart": {{"data": [], "layout": {{}}}}}},
        "result": {{"bullets": [], "content": "결과 설명", "chart": {{"data": [], "layout": {{}}}}}},
        "action": {{"bullets": [], "content": "투자 전략 설명"}}
    }},
    "past_metric": {{"value": 숫자, "company": "종목명", "metric_name": "지표명"}},
    "present_metric": {{"value": 숫자, "metric_name": "지표명"}},
    "key_insight": "핵심 인사이트",
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
                max_tokens=4000,
            )
            content = response.choices[0].message.content.strip()

            # JSON 파싱 (코드 블록 제거)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            return json.loads(content)
        except Exception as e:
            last_error = e
            print(f"  [RETRY {attempt}/{MAX_RETRIES}] {e}")

    raise RuntimeError(f"LLM 생성 {MAX_RETRIES}회 실패: {last_error}")


async def main():
    import asyncpg
    
    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    if not db_url:
        db_url = "postgresql://narative:password@postgres:5432/narrative_invest"
    
    print(f"=== Historical Cases 생성 시작 ===")
    print(f"DB: {db_url}")
    
    conn = await asyncpg.connect(db_url)
    
    # 1. 기존 데이터 확인 및 정리 (선택적)
    existing_cases = await conn.fetchval("SELECT COUNT(*) FROM historical_cases")
    existing_matches = await conn.fetchval("SELECT COUNT(*) FROM case_matches")
    existing_relations = await conn.fetchval("SELECT COUNT(*) FROM case_stock_relations")
    print(f"기존 데이터 - cases: {existing_cases}, matches: {existing_matches}, relations: {existing_relations}")
    
    # 기존 데이터 삭제 (새로 생성)
    if existing_relations > 0:
        await conn.execute("DELETE FROM case_stock_relations")
    if existing_matches > 0:
        await conn.execute("DELETE FROM case_matches")
    if existing_cases > 0:
        await conn.execute("DELETE FROM historical_cases")
    print("기존 데이터 삭제 완료")
    
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

    # 4. 각 키워드에 대해 historical_case 생성
    failed = []
    for i, kw in enumerate(keywords):
        kw_title = kw.get("title", "")
        kw_category = kw.get("category", "")
        kw_stocks = kw.get("stocks", [])

        if not kw_title:
            print(f"\n[{i+1}/{len(keywords)}] SKIP - 제목 없음")
            continue

        print(f"\n[{i+1}/{len(keywords)}] {kw_title}")

        # stocks에서 코드 추출
        stock_codes = [
            s.get("stock_code", "") if isinstance(s, dict) else s
            for s in kw_stocks
        ]

        # LLM으로 사례 생성
        try:
            case_data = generate_historical_case(kw_title, kw_category, stock_codes)
        except RuntimeError as e:
            print(f"  [SKIP] {e}")
            failed.append(kw_title)
            continue

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
            "key_insight": case_data.get("key_insight", "")
        }, ensure_ascii=False)
        
        case_id = await conn.fetchval("""
            INSERT INTO historical_cases 
            (title, event_year, summary, full_content, keywords, difficulty, view_count, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, 'beginner', 0, NOW(), NOW())
            RETURNING id
        """, 
            case_data.get("title", ""),
            case_data.get("event_year", 2000),
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
            case_data.get("key_insight", "유사한 시장 패턴")
        )
        print(f"  → case_matches: id={match_id}")
        
        # case_stock_relations에 삽입 (키워드 관련 종목들)
        for j, sc in enumerate(stock_codes):
            stock_code = sc
            # stocks가 객체 배열이면 stock_name 직접 사용
            if j < len(kw_stocks) and isinstance(kw_stocks[j], dict):
                stock_name = kw_stocks[j].get("stock_name", f"종목 {stock_code}")
            else:
                from pykrx import stock as pykrx_stock
                try:
                    stock_name = pykrx_stock.get_market_ticker_name(stock_code) or f"종목 {stock_code}"
                except Exception:
                    stock_name = f"종목 {stock_code}"
            
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
    
    # 4. 최종 확인
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
