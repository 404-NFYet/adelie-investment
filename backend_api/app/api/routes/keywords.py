"""Keywords API routes - today's dynamic keyword themes with matched cases."""

import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.briefing import DailyBriefing
from app.models.historical_case import HistoricalCase, CaseMatch

router = APIRouter(prefix="/keywords", tags=["Keywords"])


@router.get("/today")
async def get_today_keywords(
    date: Optional[str] = Query(None, description="YYYYMMDD format"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get today's keyword themes with matched historical cases."""
    if date:
        try:
            target_date = datetime.strptime(date.replace("-", ""), "%Y%m%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now().date()
    
    # Get briefing with keywords
    stmt = select(DailyBriefing).where(DailyBriefing.briefing_date == target_date)
    result = await db.execute(stmt)
    briefing = result.scalar_one_or_none()
    
    if not briefing or not briefing.top_keywords:
        # 해당 날짜에 데이터 없으면 가장 최근 데이터로 폴백 (주말/공휴일 대응)
        fallback_stmt = (
            select(DailyBriefing)
            .where(DailyBriefing.top_keywords.isnot(None))
            .order_by(DailyBriefing.briefing_date.desc())
            .limit(1)
        )
        fallback_result = await db.execute(fallback_stmt)
        briefing = fallback_result.scalar_one_or_none()
        if not briefing or not briefing.top_keywords:
            raise HTTPException(status_code=404, detail="No keywords available")
        target_date = briefing.briefing_date
    
    kw_data = briefing.top_keywords if isinstance(briefing.top_keywords, dict) else json.loads(briefing.top_keywords)
    keywords_raw = kw_data.get("keywords", [])
    
    # For each keyword, find matched case
    keywords_with_cases = []
    for i, kw in enumerate(keywords_raw):
        kw_title = kw.get("title", "")
        
        # Find case match for this keyword (today)
        match_stmt = select(CaseMatch).where(
            and_(
                CaseMatch.current_keyword == kw_title,
                CaseMatch.matched_at >= target_date,
            )
        ).order_by(CaseMatch.matched_at.desc()).limit(1)
        
        match_result = await db.execute(match_stmt)
        match = match_result.scalar_one_or_none()
        
        case_info = None
        if match:
            case_stmt = select(HistoricalCase).where(HistoricalCase.id == match.matched_case_id)
            case_result = await db.execute(case_stmt)
            case = case_result.scalar_one_or_none()
            
            if case:
                case_kw = case.keywords if isinstance(case.keywords, dict) else json.loads(case.keywords) if case.keywords else {}
                comparison = case_kw.get("comparison", {})
                sync_rate = case_kw.get("sync_rate", 70)
                
                case_info = {
                    "case_id": case.id,
                    "case_title": case.title,
                    "event_year": case.event_year,
                    "sync_rate": sync_rate,
                    "past_event": {
                        "year": case.event_year,
                        "title": case.title,
                        "label": comparison.get("past_label", str(case.event_year)),
                    },
                    "present_label": comparison.get("present_label", "2026"),
                }
        
        # stocks 데이터 정규화: 문자열 배열 → 객체 배열 호환
        raw_stocks = kw.get("stocks", [])
        if raw_stocks and isinstance(raw_stocks[0], str):
            # 레거시: ["005930", "000660"] → 객체로 변환
            stocks_normalized = [
                {"stock_code": code, "stock_name": code, "reason": ""}
                for code in raw_stocks
            ]
        else:
            stocks_normalized = raw_stocks

        keywords_with_cases.append({
            "id": i + 1,
            "category": kw.get("category", "GENERAL"),
            "title": kw_title,
            "description": kw.get("description", ""),
            "stocks": stocks_normalized,
            **(case_info or {}),
        })
    
    return {
        "date": target_date.strftime("%Y%m%d"),
        "market_summary": briefing.market_summary or "",
        "keywords": keywords_with_cases,
    }


@router.get("/history")
async def get_keywords_history(
    limit: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get past keywords archive."""
    stmt = select(DailyBriefing).order_by(DailyBriefing.briefing_date.desc()).limit(limit)
    result = await db.execute(stmt)
    briefings = result.scalars().all()
    
    history = []
    for b in briefings:
        kw_data = b.top_keywords if isinstance(b.top_keywords, dict) else json.loads(b.top_keywords) if b.top_keywords else {}
        keywords = kw_data.get("keywords", [])
        
        history.append({
            "date": b.briefing_date.strftime("%Y%m%d") if isinstance(b.briefing_date, date) else str(b.briefing_date),
            "market_summary": b.market_summary or "",
            "keywords": [{"title": kw.get("title", ""), "category": kw.get("category", "")} for kw in keywords],
            "keywords_count": len(keywords),
        })
    
    return {"history": history}
