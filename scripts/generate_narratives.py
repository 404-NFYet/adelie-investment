"""
새로운 내러티브 생성 파이프라인
- pykrx로 시장 데이터 수집
- OpenAI로 키워드 추출 및 시나리오 생성 (최대 5개)
- daily_narratives, narrative_scenarios 테이블에 저장
- 7단계 내러티브 순서: background, mirroring, simulation, result, difference, devils_advocate, action
"""
import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from pykrx import stock
from openai import OpenAI

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 설정
MAX_SCENARIOS = 5
MAX_RETRIES = 2

def strip_marks(text: str) -> str:
    """<mark class='term'>...</mark> 태그 제거."""
    return re.sub(r"<mark\s+class=['\"]term['\"]>(.*?)</mark>", r"\1", text)


def collect_market_data():
    """pykrx로 시장 데이터 수집."""
    today = datetime.now()
    if today.weekday() >= 5:
        today -= timedelta(days=(today.weekday() - 4))

    df = None
    date_str = None
    for i in range(5):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y%m%d")
        print(f"수집 시도: {date_str}")
        
        try:
            df = stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
            df = df[df["거래량"] > 0]
            if len(df) > 0:
                print(f"✅ 데이터 수집 성공: {date_str}, 종목 수: {len(df)}")
                break
        except Exception as e:
            print(f"❌ 에러: {e}")
            continue

    if df is None or len(df) == 0:
        raise RuntimeError("최근 5일 내 거래 데이터 없음")

    df_sorted = df.sort_values("등락률", ascending=False)

    def extract_stocks(tickers, limit=5):
        result = []
        for t in list(tickers)[:limit]:
            name = stock.get_market_ticker_name(t)
            row = df.loc[t] if t in df.index else df_sorted.loc[t]
            result.append({
                "code": t, 
                "name": name,
                "close": int(row["종가"]), 
                "change_rate": round(float(row["등락률"]), 2),
                "volume": int(row["거래량"])
            })
        return result

    gainers = extract_stocks(df_sorted.head(10).index)
    losers = extract_stocks(df_sorted.tail(10).index)
    high_vol = extract_stocks(df.sort_values("거래량", ascending=False).head(10).index)

    # 지수 정보
    try:
        kospi = stock.get_index_ohlcv(date_str, date_str, "1001")
        kosdaq = stock.get_index_ohlcv(date_str, date_str, "2001")
        market_summary = f"KOSPI {kospi.iloc[0]['종가']:.2f}, KOSDAQ {kosdaq.iloc[0]['종가']:.2f}"
    except:
        market_summary = "시장 지수 조회 중"

    return {
        "date": date_str,
        "market_summary": market_summary,
        "gainers": gainers,
        "losers": losers,
        "high_volume": high_vol,
    }


def extract_keywords(market_data: dict) -> list:
    """OpenAI로 핵심 키워드 추출 (최대 5개)."""
    gainers_text = ", ".join([f"{s['name']}({s['change_rate']:+.1f}%)" for s in market_data["gainers"][:5]])
    losers_text = ", ".join([f"{s['name']}({s['change_rate']:.1f}%)" for s in market_data["losers"][:5]])
    high_vol_text = ", ".join([f"{s['name']}({s['volume']:,}주)" for s in market_data["high_volume"][:5]])

    prompt = f"""오늘 한국 주식 시장 데이터:
- 시장: {market_data["market_summary"]}
- 급등주: {gainers_text}
- 급락주: {losers_text}
- 거래량 상위: {high_vol_text}

위 데이터를 분석하여 금융 교육에 적합한 핵심 키워드를 {MAX_SCENARIOS}개 추출하세요.
각 키워드는 투자 전략, 시장 트렌드, 특정 섹터 동향 등 교육적 가치가 있어야 합니다.

JSON 형식으로 응답:
[
  {{
    "title": "키워드 제목 (질문 형태 권장)",
    "category": "카테고리 (급등주/급락주/거래량/투자전략/섹터 등)",
    "summary": "2-3문장 요약",
    "related_stocks": [
      {{"code": "종목코드", "name": "종목명", "reason": "관련 이유"}}
    ]
  }}
]

JSON만 출력하세요."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=2000,
    )
    content = response.choices[0].message.content.strip()
    
    # JSON 파싱
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    keywords = json.loads(content)
    return keywords[:MAX_SCENARIOS]


def generate_scenario(keyword: dict, market_data: dict) -> dict:
    """단일 키워드에 대해 7단계 내러티브 시나리오 생성."""
    clean_title = strip_marks(keyword.get("title", ""))
    stocks = keyword.get("related_stocks", [])
    stock_info = ", ".join([f"{s['name']}({s['code']})" for s in stocks[:3]])
    
    prompt = f"""당신은 금융 교육 전문가 '아델리'입니다.

키워드: "{clean_title}"
카테고리: {keyword.get("category", "")}
요약: {keyword.get("summary", "")}
관련 종목: {stock_info}
시장 상황: {market_data.get("market_summary", "")}

이 키워드에 대해 한국 주식 시장의 역사적 사례와 연결하여 7단계 내러티브를 생성하세요.

7단계 순서 (중요: 이 순서대로 작성):
1. background — 현재 배경: 왜 지금 이게 이슈인지, 트리거 이벤트
2. mirroring — 과거 유사 사례: 어떤 시절과 비슷한지 (2000-2023년)
3. simulation — 모의 투자: 과거 사례 기반 시뮬레이션 설정
4. result — 결과 보고: 시뮬레이션 결과 분석
5. difference — 차이점: 과거와 현재의 결정적 차이
6. devils_advocate — 반대 시나리오: 3가지 반대 관점
7. action — 실전 액션: 구체적 투자 전략

규칙:
- 각 섹션 content는 2-3문장, 핵심 용어는 <mark class="term">용어</mark>로 표시 (섹션당 1-2개)
- 모든 섹션에 Plotly chart 포함 (action 제외)
- 차트: 실제 연도/날짜, 실제 수치 사용 (0이나 빈 값 금지)
- devils_advocate bullets는 반드시 3개
- simulation에는 투자 금액, 기간, 수익률 포함

JSON 형식:
{{
    "title": "시나리오 제목",
    "summary": "2-3문장 요약",
    "mirroring_data": {{
        "target_event": "과거 사건명",
        "year": 연도(숫자),
        "reasoning_log": "왜 이 사례와 비슷한지 설명"
    }},
    "sources": [{{"name": "출처명", "url": "URL"}}],
    "related_companies": [
        {{"code": "종목코드", "name": "종목명", "reason": "관련 이유"}}
    ],
    "narrative_sections": {{
        "background": {{"bullets": ["포인트1", "포인트2"], "content": "설명", "chart": {{"data": [...], "layout": {{...}}}}}},
        "mirroring": {{"bullets": [], "content": "", "chart": {{}}}},
        "simulation": {{"bullets": [], "content": "", "chart": {{}}}},
        "result": {{"bullets": [], "content": "", "chart": {{}}}},
        "difference": {{"bullets": [], "content": "", "chart": {{}}}},
        "devils_advocate": {{"bullets": ["반대1", "반대2", "반대3"], "content": "", "chart": {{}}}},
        "action": {{"bullets": [], "content": ""}}
    }},
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
            
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            return json.loads(content)
        except Exception as e:
            last_error = e
            print(f"  [RETRY {attempt}/{MAX_RETRIES}] {e}")

    raise RuntimeError(f"시나리오 생성 {MAX_RETRIES}회 실패: {last_error}")


async def main():
    import asyncpg
    
    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    if not db_url:
        db_url = "postgresql://narative:password@postgres:5432/narrative_invest"
    
    print(f"=== 내러티브 생성 파이프라인 시작 ===")
    print(f"DB: {db_url}")
    
    # OPENAI_API_KEY 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("[FATAL] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        raise SystemExit(1)
    
    # 1. 시장 데이터 수집
    print("\n[1/4] 시장 데이터 수집...")
    market_data = collect_market_data()
    print(f"시장: {market_data['market_summary']}")
    print(f"급등 상위: {[s['name'] for s in market_data['gainers'][:3]]}")
    print(f"급락 상위: {[s['name'] for s in market_data['losers'][:3]]}")
    
    # 2. 키워드 추출
    print(f"\n[2/4] 키워드 추출 (최대 {MAX_SCENARIOS}개)...")
    keywords = extract_keywords(market_data)
    print(f"추출된 키워드: {[k['title'] for k in keywords]}")
    
    # 3. DB 연결 및 기존 데이터 정리
    conn = await asyncpg.connect(db_url)
    
    today = datetime.now().date()
    existing = await conn.fetchrow(
        "SELECT id FROM daily_narratives WHERE date = $1", today
    )
    if existing:
        print(f"\n오늘({today}) 데이터 이미 존재, 삭제 후 재생성...")
        await conn.execute("DELETE FROM daily_narratives WHERE date = $1", today)
    
    # 4. DailyNarrative 생성
    narrative_id = uuid.uuid4()
    main_keywords = [k["title"] for k in keywords]
    
    # 용어 사전 생성 (시나리오 생성 후 수집)
    all_glossary_terms = {}
    
    print(f"\n[3/4] DailyNarrative 생성...")
    await conn.execute("""
        INSERT INTO daily_narratives (id, date, main_keywords, glossary, created_at, updated_at)
        VALUES ($1, $2, $3, $4, NOW(), NOW())
    """, narrative_id, today, main_keywords, json.dumps({}, ensure_ascii=False))
    print(f"  → daily_narratives: id={narrative_id}")
    
    # 5. 각 키워드에 대해 NarrativeScenario 생성
    print(f"\n[4/4] 시나리오 생성 ({len(keywords)}개)...")
    failed = []
    
    for i, kw in enumerate(keywords):
        print(f"\n  [{i+1}/{len(keywords)}] {kw['title']}")
        
        try:
            scenario_data = generate_scenario(kw, market_data)
        except RuntimeError as e:
            print(f"    [SKIP] {e}")
            failed.append(kw["title"])
            continue
        
        scenario_id = uuid.uuid4()
        
        # 관련 기업 정보 (키워드에서 가져오거나 시나리오 결과 사용)
        related_companies = scenario_data.get("related_companies", kw.get("related_stocks", []))
        
        await conn.execute("""
            INSERT INTO narrative_scenarios 
            (id, narrative_id, title, summary, sources, related_companies, mirroring_data, narrative_sections, sort_order, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
        """,
            scenario_id,
            narrative_id,
            scenario_data.get("title", kw["title"]),
            scenario_data.get("summary", kw.get("summary", "")),
            json.dumps(scenario_data.get("sources", []), ensure_ascii=False),
            json.dumps(related_companies, ensure_ascii=False),
            json.dumps(scenario_data.get("mirroring_data", {}), ensure_ascii=False),
            json.dumps(scenario_data.get("narrative_sections", {}), ensure_ascii=False),
            i,  # sort_order
        )
        print(f"    → narrative_scenarios: id={scenario_id}")
        
        # 용어 수집
        for term in scenario_data.get("glossary_terms", []):
            if term and term not in all_glossary_terms:
                all_glossary_terms[term] = f"{term}에 대한 설명"
    
    # 6. 용어 사전 업데이트
    if all_glossary_terms:
        await conn.execute(
            "UPDATE daily_narratives SET glossary = $1 WHERE id = $2",
            json.dumps(all_glossary_terms, ensure_ascii=False),
            narrative_id
        )
        print(f"\n  → 용어 사전 업데이트: {len(all_glossary_terms)}개 용어")
    
    # 7. 최종 확인
    final_narratives = await conn.fetchval("SELECT COUNT(*) FROM daily_narratives")
    final_scenarios = await conn.fetchval("SELECT COUNT(*) FROM narrative_scenarios")
    
    print(f"\n=== 생성 완료 ===")
    print(f"daily_narratives: {final_narratives}건")
    print(f"narrative_scenarios: {final_scenarios}건")
    if failed:
        print(f"실패 ({len(failed)}건): {failed}")
    
    await conn.close()
    
    if failed:
        raise SystemExit(f"{len(failed)}건 실패")


if __name__ == "__main__":
    asyncio.run(main())
