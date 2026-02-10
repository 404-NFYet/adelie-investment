"""Historical cases API routes."""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI

from app.core.config import get_settings

# TODO: Phase 4에서 sys.path.insert 제거 예정 (패키지 구조 정리 후)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "ai-module"))

from app.core.database import get_db
from app.models.historical_case import HistoricalCase
from app.schemas.case import (
    CaseSearchRequest,
    CaseSearchResponse,
    HistoricalCase as HistoricalCaseSchema,
    StoryResponse,
    ComparisonPoint,
    ComparisonResponse,
    RelatedCompany,
    CompanyGraphResponse,
)

router = APIRouter(tags=["Cases"])


@router.get("/search/cases", response_model=CaseSearchResponse)
async def search_cases(
    query: str = Query(..., description="Search query"),
    recency: str = Query("year", description="Recency filter: year, month, week"),
    limit: int = Query(5, ge=1, le=10, description="Number of results"),
    db: AsyncSession = Depends(get_db),
) -> CaseSearchResponse:
    """
    Search for historical cases matching the query.
    
    Uses Perplexity API for web search and returns relevant historical cases.
    """
    # Try to search in database first
    stmt = select(HistoricalCase).where(
        HistoricalCase.summary.ilike(f"%{query}%")
    ).limit(limit)
    result = await db.execute(stmt)
    db_cases = result.scalars().all()
    
    if db_cases:
        cases = [
            HistoricalCaseSchema(
                id=case.id,
                title=case.title,
                event_year=case.event_year or 2020,
                summary=case.summary,
                keywords=case.keywords.get("keywords", []) if case.keywords else [],
                similarity_score=0.8,
                citations=[],
            )
            for case in db_cases
        ]
        return CaseSearchResponse(query=query, cases=cases, search_source="database")
    
    # Use Perplexity for web search
    try:
        perplexity_key = get_settings().PERPLEXITY_API_KEY
        if not perplexity_key:
            raise ValueError("PERPLEXITY_API_KEY not set")
        
        client = OpenAI(
            api_key=perplexity_key,
            base_url="https://api.perplexity.ai"
        )
        
        # Search for historical Korean stock market cases
        search_query = f"한국 주식시장 역사적 사례 {query} 비교 분석"
        
        recency_map = {"year": "year", "month": "month", "week": "week"}
        
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 한국 주식시장 역사 전문가입니다. "
                        "사용자의 질문에 대해 관련된 과거 한국 주식시장 사례를 찾아 정리해주세요. "
                        "각 사례에 대해 제목, 연도, 요약, 키워드를 JSON 형식으로 제공하세요."
                    ),
                },
                {"role": "user", "content": search_query},
            ],
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content
        
        # Parse response into cases (simplified parsing)
        # In production, use proper JSON parsing or structured output
        cases = [
            HistoricalCaseSchema(
                id=0,
                title=f"검색 결과: {query}",
                event_year=2024,
                summary=content[:500],
                keywords=[query],
                similarity_score=0.9,
                citations=[],
            )
        ]
        
        return CaseSearchResponse(query=query, cases=cases, search_source="perplexity")
        
    except Exception as e:
        # Return empty results on error
        return CaseSearchResponse(
            query=query,
            cases=[],
            search_source="error"
        )


@router.get("/story/{case_id}", response_model=StoryResponse)
async def get_story(
    case_id: int,
    difficulty: str = Query("beginner", description="Difficulty level"),
    db: AsyncSession = Depends(get_db),
) -> StoryResponse:
    """
    Get storytelling content for a historical case.
    
    The content is adjusted based on the difficulty level.
    """
    # Get case from database
    result = await db.execute(
        select(HistoricalCase).where(HistoricalCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # full_content 우선, 없으면 summary 사용
    content = case.full_content or case.summary
    
    # keywords JSONB에서 용어 및 thinking_point 추출
    glossary_terms = []
    thinking_point = ""
    if case.keywords:
        kw_data = case.keywords if isinstance(case.keywords, dict) else {}
        glossary_terms = kw_data.get("keywords", [])[:5]
        thinking_point = kw_data.get("thinking_point", "")
    
    # 읽기 시간 계산 (200 words per minute)
    word_count = len(content.split())
    reading_time = max(1, word_count // 200)
    
    return StoryResponse(
        case_id=case.id,
        title=case.title,
        difficulty=difficulty,
        content=content,
        glossary_terms=glossary_terms,
        reading_time_minutes=reading_time,
        thinking_point=thinking_point,
    )


@router.get("/comparison/{case_id}", response_model=ComparisonResponse)
async def get_comparison(
    case_id: int,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """
    Get past-present comparison for a historical case.
    """
    # Get case from database
    result = await db.execute(
        select(HistoricalCase).where(HistoricalCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # keywords JSONB에서 comparison 데이터 및 key_insight 추출
    kw_data = case.keywords if isinstance(case.keywords, dict) else {} if not case.keywords else case.keywords
    comparison_data = kw_data.get("comparison", {})
    key_insight = kw_data.get("key_insight", "")
    
    # comparison.points가 있으면 실 데이터 사용, 없으면 기본값
    raw_points = comparison_data.get("points", [])
    if raw_points:
        comparison_points = [
            ComparisonPoint(
                aspect=pt.get("aspect", ""),
                past=pt.get("past", ""),
                present=pt.get("present", ""),
                similarity=pt.get("similarity", "부분 유사"),
            )
            for pt in raw_points
        ]
    else:
        comparison_points = [
            ComparisonPoint(
                aspect="시장 상황",
                past=f"{case.event_year or 2020}년 당시 상황",
                present="현재 시장 상황",
                similarity="부분 유사",
            ),
        ]
    
    lessons = comparison_data.get("lessons", ["과거 사례로부터 배울 수 있는 교훈"])
    
    return ComparisonResponse(
        case_id=case.id,
        past_event={
            "title": case.title,
            "year": case.event_year,
            "summary": case.summary,
            "label": comparison_data.get("past_label", str(case.event_year or "")),
        },
        current_situation={
            "summary": comparison_data.get("current_summary", "현재 시장 상황 분석"),
            "label": comparison_data.get("present_label", "2026"),
        },
        comparison_points=comparison_points,
        lessons=lessons,
        # 실 비교 데이터 (JSONB에서 직접 추출)
        comparison_title=comparison_data.get("title", ""),
        past_metric=comparison_data.get("past_metric"),
        present_metric=comparison_data.get("present_metric"),
        analysis=comparison_data.get("analysis", []),
        poll_question=comparison_data.get("poll_question", ""),
        summary=case.summary or "",
        key_insight=key_insight or None,  # 핵심 인사이트
    )


@router.get("/companies/{case_id}", response_model=CompanyGraphResponse)
async def get_related_companies(
    case_id: int,
    db: AsyncSession = Depends(get_db),
) -> CompanyGraphResponse:
    """
    Get related companies for a historical case.
    """
    # Get case from database
    result = await db.execute(
        select(HistoricalCase).where(HistoricalCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get stock relations
    from app.models.historical_case import CaseStockRelation
    
    relations_result = await db.execute(
        select(CaseStockRelation).where(CaseStockRelation.case_id == case_id)
    )
    relations = relations_result.scalars().all()
    
    # Format related companies
    related_companies = []
    center_company = ""
    
    for rel in relations:
        if rel.relation_type == "main_subject":
            center_company = rel.stock_name
        
        related_companies.append(
            RelatedCompany(
                stock_code=rel.stock_code,
                stock_name=rel.stock_name,
                relation_type=rel.relation_type or "related",
                relation_detail=rel.impact_description or "",
                hops=1,
            )
        )
    
    if not center_company and related_companies:
        center_company = related_companies[0].stock_name
    
    return CompanyGraphResponse(
        case_id=case.id,
        center_company=center_company or "Unknown",
        related_companies=related_companies,
        graph_data={
            "nodes": [{"id": c.stock_code, "name": c.stock_name} for c in related_companies],
            "edges": [],
        },
    )
