"""Keywords API routes - today's dynamic keyword themes with matched cases."""

import json
import json as json_module
from datetime import datetime, date, timezone, timedelta
from typing import Optional

KST = timezone(timedelta(hours=9))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.briefing import DailyBriefing
from app.models.historical_case import HistoricalCase, CaseMatch
from app.services.redis_cache import get_redis_cache

router = APIRouter(prefix="/keywords", tags=["keywords"])


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
        target_date = datetime.now(KST).date()

    # Redis 캐시 체크
    target_date_str = target_date.strftime("%Y%m%d")
    cache_key = f"api:keywords:today:{target_date_str}"
    try:
        cache = await get_redis_cache()
        cached = await cache.get(cache_key)
        if cached:
            return json_module.loads(cached)
    except Exception:
        pass

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
                sync_rate = comparison.get("sync_rate", 0)
                
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
                    "present_label": comparison.get("present_label", ""),
                }
        
        stocks = kw.get("stocks", [])

        keywords_with_cases.append({
            "id": i + 1,
            "category": kw.get("category", "GENERAL"),
            "title": kw_title,
            "description": kw.get("description", ""),
            "icon_key": kw.get("icon_key"),
            "sector": kw.get("sector"),
            "stocks": stocks,
            "trend_days": kw.get("trend_days"),
            "trend_type": kw.get("trend_type"),
            "catalyst": kw.get("catalyst"),
            "catalyst_url": kw.get("catalyst_url"),
            "catalyst_source": kw.get("catalyst_source"),
            "mirroring_hint": kw.get("mirroring_hint"),
            "quality_score": kw.get("quality_score"),
            # case_id를 명시적으로 반환 (null이면 프론트에서 버튼 비활성화)
            "case_id": case_info["case_id"] if case_info else None,
            "case_title": case_info["case_title"] if case_info else None,
            "event_year": case_info["event_year"] if case_info else None,
            "sync_rate": case_info["sync_rate"] if case_info else None,
            "past_event": case_info.get("past_event") if case_info else None,
            "present_label": case_info.get("present_label") if case_info else None,
        })
    
    result = {
        "date": target_date.strftime("%Y%m%d"),
        "market_summary": briefing.market_summary or "",
        "keywords": keywords_with_cases,
    }

    # Redis 캐시 저장 (5분)
    try:
        await cache.set(cache_key, json_module.dumps(result, ensure_ascii=False, default=str), 300)
    except Exception:
        pass

    return result


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
