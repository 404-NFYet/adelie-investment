#!/usr/bin/env python3
"""
Step 1: briefing_stocks에서 동적(3~7개) 키워드 테마 생성

오늘의 급등/급락/거래량 종목들을 OpenAI로 분석하여
투자 키워드 테마를 3~7개 자동 생성합니다.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from openai import OpenAI
from sqlalchemy import create_engine, text


def get_db_engine():
    """동기 DB 엔진 생성."""
    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    return create_engine(db_url)


def fetch_today_stocks(engine, date: str) -> list[dict]:
    """오늘의 briefing_stocks 조회."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT bs.stock_code, bs.stock_name, bs.change_rate, bs.volume, bs.selection_reason
            FROM briefing_stocks bs
            JOIN daily_briefings db ON bs.briefing_id = db.id
            WHERE db.briefing_date = :date
            ORDER BY bs.selection_reason, bs.change_rate DESC
        """), {"date": date}).fetchall()
    
    return [
        {
            "stock_code": r[0],
            "stock_name": r[1],
            "change_rate": float(r[2]) if r[2] else 0.0,
            "volume": r[3] or 0,
            "selection_reason": r[4],
        }
        for r in rows
    ]


def generate_keyword_themes(stocks: list[dict]) -> list[dict]:
    """OpenAI로 종목 데이터에서 투자 키워드 테마를 동적 생성."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # 종목 데이터를 텍스트로 포맷
    stocks_text = ""
    for reason in ["top_gainer", "top_loser", "high_volume"]:
        group = [s for s in stocks if s["selection_reason"] == reason]
        label = {"top_gainer": "급등 종목", "top_loser": "급락 종목", "high_volume": "거래량 상위"}[reason]
        stocks_text += f"\n[{label}]\n"
        for s in group:
            stocks_text += f"  {s['stock_code']} {s['stock_name']} ({s['change_rate']:+.1f}%, 거래량: {s['volume']:,})\n"
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """당신은 한국 주식시장 분석 전문가입니다.
주어진 종목 데이터를 분석하여 투자 키워드 테마를 생성합니다.
반드시 JSON 형식으로 응답하세요."""
            },
            {
                "role": "user",
                "content": f"""아래는 오늘 한국 주식시장의 급등/급락/거래량 상위 종목입니다.

{stocks_text}

이 종목들을 분석하여 투자 키워드 테마를 생성하세요.

규칙:
- 테마 개수: 최소 3개, 최대 7개 (데이터가 뒷받침하는 만큼만 생성)
- 종목들 사이에서 공통 패턴, 섹터, 이슈를 찾아 테마화
- 직접 관련 없는 종목은 '시장 변동성' 등 포괄적 테마로 묶을 수 있음
- 각 테마에 해당하는 종목 코드를 반드시 포함
- category는 영문 대문자 (예: "AI & TECH", "BIO & PHARMA", "POLICY", "ECONOMY", "MATERIALS", "ENERGY")
- title은 한국어로 흥미롭고 도발적인 질문/주장 형태 (예: "AI 반도체 거품론", "바이오 신약의 빛과 그림자")
- description은 한국어 2-3문장으로 현재 상황과 투자 관점을 설명

JSON 형식:
{{"keywords": [
  {{"category": "...", "title": "...", "description": "...", "stocks": ["005930", "000660"]}}
]}}"""
            }
        ],
        max_tokens=2000,
        temperature=0.7,
    )
    
    result = json.loads(response.choices[0].message.content)
    keywords = result.get("keywords", [])
    
    # 3~7개 범위 검증
    if len(keywords) < 3:
        print(f"  Warning: Only {len(keywords)} keywords generated, minimum is 3")
    if len(keywords) > 7:
        keywords = keywords[:7]
        print(f"  Warning: Truncated to 7 keywords")
    
    return keywords


def save_keywords_to_db(engine, date: str, keywords: list[dict]):
    """키워드를 daily_briefings.top_keywords에 저장."""
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE daily_briefings 
            SET top_keywords = :keywords
            WHERE briefing_date = :date
        """), {
            "date": date,
            "keywords": json.dumps({"keywords": keywords}, ensure_ascii=False),
        })
        conn.commit()


def main(date: str):
    """메인 실행."""
    print(f"\n=== Step 1: 동적 키워드 테마 생성 ({date}) ===\n")
    
    engine = get_db_engine()
    
    # 1. 오늘 종목 데이터 조회
    stocks = fetch_today_stocks(engine, date)
    if not stocks:
        print(f"  ERROR: {date}에 대한 briefing_stocks 데이터가 없습니다.")
        return []
    
    print(f"  종목 {len(stocks)}개 조회 완료")
    
    # 2. OpenAI로 키워드 테마 생성
    print(f"  OpenAI로 키워드 테마 생성 중...")
    keywords = generate_keyword_themes(stocks)
    
    print(f"  {len(keywords)}개 키워드 테마 생성:")
    for i, kw in enumerate(keywords, 1):
        print(f"    {i}. [{kw['category']}] {kw['title']}")
        print(f"       종목: {', '.join(kw.get('stocks', []))}")
    
    # 3. DB에 저장
    save_keywords_to_db(engine, date, keywords)
    print(f"\n  DB 저장 완료 (daily_briefings.top_keywords)")
    
    return keywords


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYYMMDD")
    args = parser.parse_args()
    
    from datetime import datetime
    date = args.date or datetime.now().strftime("%Y%m%d")
    main(date)
