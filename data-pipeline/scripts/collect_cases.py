#!/usr/bin/env python3
"""
Step 2: 키워드별 Perplexity 유사사례 검색 + OpenAI 구조화 + DB 저장

각 키워드에 대해:
1. 기존 유사 사례 참조 조회 (중복 방지)
2. Perplexity로 역사적 유사사례 검색
3. OpenAI로 구조화 파싱
4. historical_cases + case_matches + case_stock_relations DB 저장
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from openai import OpenAI
from sqlalchemy import create_engine, text

from collectors.perplexity_case_collector import PerplexityCaseCollector


def get_db_engine():
    db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
    return create_engine(db_url)


def fetch_existing_cases(engine, keyword: str) -> list[dict]:
    """동일/유사 키워드의 기존 사례 조회 (참조용)."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT hc.title, hc.event_year, hc.summary, cm.matched_at
            FROM case_matches cm
            JOIN historical_cases hc ON cm.matched_case_id = hc.id
            WHERE cm.current_keyword ILIKE :kw
            ORDER BY cm.matched_at DESC
            LIMIT 5
        """), {"kw": f"%{keyword}%"}).fetchall()
    
    return [
        {"title": r[0], "event_year": r[1], "summary": r[2][:100], "matched_at": str(r[3])}
        for r in rows
    ]


def build_perplexity_context(keyword: str, existing_cases: list[dict]) -> str:
    """Perplexity 검색용 컨텍스트 생성."""
    context = ""
    if existing_cases:
        context += "기존에 분석된 유사 사례:\n"
        for c in existing_cases:
            context += f"- {c['title']} ({c['event_year']}년, {c['matched_at'][:10]} 분석)\n"
        context += "\n위 사례들과는 다른 새로운 관점의 역사적 유사 사례를 찾아주세요.\n"
    return context


def structure_case_with_openai(
    keyword_info: dict,
    perplexity_content: str,
    citations: list,
) -> dict:
    """OpenAI로 Perplexity 결과를 구조화된 JSON으로 파싱."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    keyword_title = keyword_info.get("title", "")
    keyword_stocks = keyword_info.get("stocks", [])
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """당신은 투자 교육 콘텐츠 전문가입니다. 
역사적 사례를 분석하여 교육용 구조화된 콘텐츠를 생성합니다.
반드시 JSON 형식으로 응답하세요."""
            },
            {
                "role": "user",
                "content": f"""아래는 "{keyword_title}" 키워드에 대해 검색된 역사적 유사 사례입니다.

--- 검색 결과 ---
{perplexity_content}
--- 끝 ---

이 내용을 다음 JSON 구조로 변환하세요:

{{
  "title": "사례의 핵심 교훈을 담은 제목 (예: '시스코(Cisco)의 교훈')",
  "event_year": 2000,
  "summary": "200자 이내 요약",
  "full_content": "스토리텔링 형식의 3-4문단 본문. 핵심 투자 용어는 [[PER(주가수익비율)]] 처럼 대괄호로 감싸세요. [[용어]]는 초보자가 모를 수 있는 금융 용어에만 적용하세요.",
  "thinking_point": "독자에게 던지는 사고 유도 질문 (1-2문장)",
  "comparison": {{
    "title": "비교 분석 소제목 (예: '엔비디아는 다를까?')",
    "subtitle": "비교 설명 한 줄",
    "past_label": "과거 시기 레이블 (예: 'Dot-com')",
    "present_label": "현재 시기 레이블 (예: 'AI Tech')",
    "past_metric": {{"name": "주요 지표명", "value": 150, "company": "대표 기업", "year": 2000}},
    "present_metric": {{"name": "주요 지표명", "value": 60, "company": "대표 기업", "year": 2026}},
    "analysis": ["분석 문단1 (핵심 용어는 [[용어]] 처리)", "분석 문단2"],
    "poll_question": "독자에게 의견을 묻는 질문"
  }},
  "related_stocks": [
    {{
      "code": "종목코드6자리",
      "name": "종목명",
      "role": "leader 또는 equipment 또는 potential",
      "role_label": "대장주 또는 장비주 또는 잠룡",
      "description": "한 줄 역할 설명",
      "detail": "2-3문장 상세 설명 (leader 역할만)"
    }}
  ],
  "sync_rate": 75
}}

참고 종목 코드: {json.dumps(keyword_stocks)}
sync_rate는 과거와 현재의 유사도를 0~100 사이 정수로 판단하세요.
related_stocks에는 현재 한국 시장에서 이 테마와 관련된 종목 3~5개를 포함하세요.
leader 역할 종목이 반드시 1개 이상 있어야 합니다."""
            }
        ],
        max_tokens=3000,
        temperature=0.5,
    )
    
    result = json.loads(response.choices[0].message.content)
    result["citations"] = citations or []
    return result


def save_case_to_db(engine, date: str, keyword_title: str, case_data: dict) -> int:
    """구조화된 사례를 DB에 저장하고 case_id를 반환."""
    with engine.connect() as conn:
        # 1. historical_cases INSERT
        row = conn.execute(text("""
            INSERT INTO historical_cases (
                title, event_year, summary, full_content, 
                keywords, source_urls, difficulty, view_count, created_at, updated_at
            ) VALUES (
                :title, :year, :summary, :content, 
                :keywords, :urls, 'beginner', 0, NOW(), NOW()
            ) RETURNING id
        """), {
            "title": case_data.get("title", ""),
            "year": case_data.get("event_year", 2020),
            "summary": case_data.get("summary", ""),
            "content": case_data.get("full_content", ""),
            "keywords": json.dumps({
                "keywords": [keyword_title],
                "thinking_point": case_data.get("thinking_point", ""),
                "comparison": case_data.get("comparison", {}),
                "sync_rate": case_data.get("sync_rate", 70),
            }, ensure_ascii=False),
            "urls": json.dumps(case_data.get("citations", []), ensure_ascii=False),
        }).fetchone()
        
        case_id = row[0]
        
        # 2. case_matches INSERT
        conn.execute(text("""
            INSERT INTO case_matches (
                current_keyword, matched_case_id, similarity_score, 
                match_reason, matched_at
            ) VALUES (
                :keyword, :case_id, :score, :reason, NOW()
            )
        """), {
            "keyword": keyword_title,
            "case_id": case_id,
            "score": case_data.get("sync_rate", 70) / 100.0,
            "reason": f"Perplexity 검색 기반 자동 매칭 ({date})",
        })
        
        # 3. case_stock_relations INSERT
        for stock in case_data.get("related_stocks", []):
            conn.execute(text("""
                INSERT INTO case_stock_relations (
                    case_id, stock_code, stock_name, 
                    relation_type, impact_description
                ) VALUES (
                    :case_id, :code, :name, :type, :desc
                )
            """), {
                "case_id": case_id,
                "code": stock.get("code", ""),
                "name": stock.get("name", ""),
                "type": stock.get("role", "related"),
                "desc": stock.get("detail") or stock.get("description", ""),
            })
        
        conn.commit()
        return case_id


async def process_keyword(
    engine,
    collector: PerplexityCaseCollector,
    date: str,
    keyword_info: dict,
) -> dict:
    """단일 키워드에 대한 전체 처리 파이프라인."""
    title = keyword_info.get("title", "")
    
    print(f"\n  --- 키워드: {title} ---")
    
    # 2-1. 기존 사례 참조 조회
    existing = fetch_existing_cases(engine, title)
    if existing:
        print(f"    기존 유사 사례 {len(existing)}건 참조")
        for e in existing:
            print(f"      - {e['title']} ({e['event_year']})")
    
    # 2-2. Perplexity 검색
    context = build_perplexity_context(title, existing)
    print(f"    Perplexity 검색 중...")
    
    search_result = await collector.search_historical_case(
        topic=title,
        context=context,
    )
    
    if not search_result.get("success"):
        print(f"    ERROR: Perplexity 검색 실패 - {search_result.get('error')}")
        return {"keyword": title, "success": False, "error": search_result.get("error")}
    
    print(f"    Perplexity 응답 수신 ({len(search_result.get('content', ''))} chars)")
    
    # 2-3. OpenAI 구조화
    print(f"    OpenAI 구조화 파싱 중...")
    case_data = structure_case_with_openai(
        keyword_info=keyword_info,
        perplexity_content=search_result.get("content", ""),
        citations=search_result.get("citations", []),
    )
    
    print(f"    사례: {case_data.get('title', '?')} ({case_data.get('event_year', '?')})")
    print(f"    SYNC RATE: {case_data.get('sync_rate', '?')}%")
    print(f"    관련 종목: {len(case_data.get('related_stocks', []))}개")
    
    # 2-4. DB 저장
    case_id = save_case_to_db(engine, date, title, case_data)
    print(f"    DB 저장 완료 (case_id={case_id})")
    
    return {
        "keyword": title,
        "success": True,
        "case_id": case_id,
        "case_title": case_data.get("title", ""),
        "sync_rate": case_data.get("sync_rate", 0),
    }


async def main(date: str, keywords: list[dict] = None):
    """메인 실행."""
    print(f"\n=== Step 2: Perplexity 유사사례 검색 ({date}) ===\n")
    
    engine = get_db_engine()
    collector = PerplexityCaseCollector()
    
    # 키워드가 없으면 DB에서 조회
    if not keywords:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT top_keywords FROM daily_briefings WHERE briefing_date = :date
            """), {"date": date}).fetchone()
            
            if not row or not row[0]:
                print("  ERROR: 키워드 데이터가 없습니다. Step 1을 먼저 실행하세요.")
                return []
            
            kw_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            keywords = kw_data.get("keywords", [])
    
    print(f"  {len(keywords)}개 키워드에 대해 유사사례 검색 시작")
    
    results = []
    for kw in keywords:
        result = await process_keyword(engine, collector, date, kw)
        results.append(result)
    
    # 결과 요약
    print(f"\n=== 검색 결과 요약 ===")
    success_count = sum(1 for r in results if r.get("success"))
    print(f"  성공: {success_count}/{len(results)}")
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        print(f"  [{status}] {r.get('keyword', '?')} -> case_id={r.get('case_id', '?')} (sync={r.get('sync_rate', '?')}%)")
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    
    date = args.date or datetime.now().strftime("%Y%m%d")
    asyncio.run(main(date))
