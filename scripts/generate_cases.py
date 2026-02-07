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


def generate_historical_case(keyword_title: str, category: str, stocks: list[str]) -> dict:
    """LLM으로 역사적 유사 사례 생성."""
    clean_title = strip_marks(keyword_title)
    
    prompt = f"""당신은 한국 주식 시장 역사 전문가입니다. 
현재 키워드: "{clean_title}" (카테고리: {category})
관련 종목 코드: {stocks}

이 키워드와 유사한 과거 한국 주식 시장의 역사적 사례를 생성해주세요.

다음 JSON 형식으로 응답해주세요:
{{
    "title": "과거 사례 제목 (예: 2000년 IT 버블과 바이오주 급등의 유사성)",
    "event_year": 연도 (숫자, 예: 2000),
    "summary": "2-3문장의 요약",
    "full_content": "3-5문단의 상세 스토리텔링 (과거 사건 설명, 현재와의 유사점, 투자자 교훈)",
    "sync_rate": 유사도 (60-90 사이 숫자),
    "past_label": "과거 라벨 (예: IT 버블)",
    "present_label": "현재 라벨 (예: 바이오 급등)",
    "past_metric": {{
        "value": 과거 지표값 (숫자),
        "company": "과거 대표 종목명",
        "metric_name": "지표명 (예: 등락률, PER)"
    }},
    "present_metric": {{
        "value": 현재 추정 지표값 (숫자),
        "metric_name": "지표명"
    }},
    "key_insight": "핵심 인사이트 (한 문장)",
    "glossary_terms": ["관련 용어1", "관련 용어2"]
}}

실제 역사적 사건을 기반으로 작성하되, 2000-2023년 사이의 사건이어야 합니다.
JSON만 출력하세요."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
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
        print(f"  [ERROR] LLM 생성 실패: {e}")
        # 기본값 반환
        return {
            "title": f"{clean_title}와 유사한 과거 사례",
            "event_year": 2008,
            "summary": "과거 유사한 시장 상황이 있었습니다.",
            "full_content": "상세 내용은 추후 업데이트 예정입니다.",
            "sync_rate": 70,
            "past_label": "과거 사례",
            "present_label": "현재 상황",
            "past_metric": {"value": 50, "company": "과거 기업", "metric_name": "등락률"},
            "present_metric": {"value": 40, "metric_name": "등락률"},
            "key_insight": "역사는 반복됩니다.",
            "glossary_terms": []
        }


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
    
    # 3. 각 키워드에 대해 historical_case 생성
    for i, kw in enumerate(keywords):
        kw_title = kw.get("title", f"키워드 {i+1}")
        kw_category = kw.get("category", "GENERAL")
        kw_stocks = kw.get("stocks", [])
        
        print(f"\n[{i+1}/{len(keywords)}] {kw_title}")
        
        # LLM으로 사례 생성
        case_data = generate_historical_case(kw_title, kw_category, kw_stocks)
        
        # historical_cases에 삽입
        keywords_jsonb = json.dumps({
            "comparison": {
                "past_metric": case_data.get("past_metric", {}),
                "present_metric": case_data.get("present_metric", {}),
                "sync_rate": case_data.get("sync_rate", 70),
                "past_label": case_data.get("past_label", "과거"),
                "present_label": case_data.get("present_label", "현재"),
            },
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
        stock_code = kw_stocks[0] if kw_stocks else None
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
        for j, stock_code in enumerate(kw_stocks):
            from pykrx import stock
            try:
                stock_name = stock.get_market_ticker_name(stock_code) or f"종목 {stock_code}"
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
    
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
