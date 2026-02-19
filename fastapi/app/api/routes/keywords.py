"""Keywords API routes - today's dynamic keyword themes with matched cases."""

import json
import json as json_module
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_keys import key_keywords_today
from app.models.briefing import DailyBriefing
from app.models.historical_case import CaseMatch, HistoricalCase
from app.services.redis_cache import get_redis_cache

KST = timezone(timedelta(hours=9))

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
    cache_key = key_keywords_today(target_date_str)
    cache = None
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

    # 해당 날짜에 실제 생성된 case 키워드를 우선 카드로 사용한다.
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    day_match_stmt = (
        select(CaseMatch, HistoricalCase)
        .join(HistoricalCase, HistoricalCase.id == CaseMatch.matched_case_id)
        .where(
            and_(
                CaseMatch.matched_at >= day_start,
                CaseMatch.matched_at < day_end,
            )
        )
        .order_by(CaseMatch.matched_at.desc())
    )
    day_match_rows = (await db.execute(day_match_stmt)).all()

    generated_by_key: dict[tuple[str, int], dict] = {}
    for match, case in day_match_rows:
        if not case:
            continue

        current_keyword = (match.current_keyword or "").strip()
        if not current_keyword:
            continue

        key = (current_keyword, case.id)
        item = generated_by_key.get(key)
        if item is None:
            case_kw = case.keywords if isinstance(case.keywords, dict) else json.loads(case.keywords) if case.keywords else {}
            comparison = case_kw.get("comparison", {})
            item = {
                "current_keyword": current_keyword,
                "case_id": case.id,
                "case_title": case.title,
                "event_year": case.event_year,
                "sync_rate": comparison.get("sync_rate", 0),
                "past_event": {
                    "year": case.event_year,
                    "title": case.title,
                    "label": comparison.get("past_label", str(case.event_year)),
                },
                "present_label": comparison.get("present_label", ""),
                "description": comparison.get("current_summary") or case.summary or "",
                "matched_stock_codes": set(),
                "latest_matched_at": match.matched_at,
            }
            generated_by_key[key] = item

        stock_code = (match.current_stock_code or "").strip()
        if stock_code:
            item["matched_stock_codes"].add(stock_code)
        if match.matched_at and match.matched_at > item["latest_matched_at"]:
            item["latest_matched_at"] = match.matched_at

    generated_cards = sorted(
        generated_by_key.values(),
        key=lambda x: x["latest_matched_at"] or datetime.min,
        reverse=True,
    )

    keywords_with_cases = []
    if generated_cards:
        for i, case_info in enumerate(generated_cards):
            fallback_kw = keywords_raw[i] if i < len(keywords_raw) else {}
            matched_stocks = [
                {
                    "stock_code": code,
                    "stock_name": code,
                    "reason": "case_match",
                }
                for code in sorted(case_info["matched_stock_codes"])
            ]

            keywords_with_cases.append(
                {
                    "id": i + 1,
                    "category": fallback_kw.get("category", "GENERATED_CASE"),
                    "title": case_info["current_keyword"],
                    "description": case_info["description"] or fallback_kw.get("description", ""),
                    "icon_key": fallback_kw.get("icon_key"),
                    "sector": fallback_kw.get("sector"),
                    "stocks": matched_stocks,
                    "trend_days": fallback_kw.get("trend_days"),
                    "trend_type": fallback_kw.get("trend_type"),
                    "catalyst": fallback_kw.get("catalyst"),
                    "catalyst_url": fallback_kw.get("catalyst_url"),
                    "catalyst_source": fallback_kw.get("catalyst_source"),
                    "mirroring_hint": fallback_kw.get("mirroring_hint"),
                    "quality_score": fallback_kw.get("quality_score"),
                    "case_id": case_info["case_id"],
                    "case_title": case_info["case_title"],
                    "event_year": case_info["event_year"],
                    "sync_rate": case_info["sync_rate"],
                    "past_event": case_info["past_event"],
                    "present_label": case_info["present_label"],
                }
            )
    else:
        # 생성된 case가 없으면 기존 키워드만 노출 (버튼 비활성)
        for i, kw in enumerate(keywords_raw):
            keywords_with_cases.append(
                {
                    "id": i + 1,
                    "category": kw.get("category", "GENERAL"),
                    "title": kw.get("title", ""),
                    "description": kw.get("description", ""),
                    "icon_key": kw.get("icon_key"),
                    "sector": kw.get("sector"),
                    "stocks": kw.get("stocks", []),
                    "trend_days": kw.get("trend_days"),
                    "trend_type": kw.get("trend_type"),
                    "catalyst": kw.get("catalyst"),
                    "catalyst_url": kw.get("catalyst_url"),
                    "catalyst_source": kw.get("catalyst_source"),
                    "mirroring_hint": kw.get("mirroring_hint"),
                    "quality_score": kw.get("quality_score"),
                    "case_id": None,
                    "case_title": None,
                    "event_year": None,
                    "sync_rate": None,
                    "past_event": None,
                    "present_label": None,
                }
            )

    response_payload = {
        "date": target_date.strftime("%Y%m%d"),
        "market_summary": briefing.market_summary or "",
        "keywords": keywords_with_cases,
    }

    # Redis 캐시 저장 (5분)
    try:
        if cache is None:
            cache = await get_redis_cache()
        await cache.set(cache_key, json_module.dumps(response_payload, ensure_ascii=False, default=str), 300)
    except Exception:
        pass

    return response_payload


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

        history.append(
            {
                "date": b.briefing_date.strftime("%Y%m%d") if isinstance(b.briefing_date, date) else str(b.briefing_date),
                "market_summary": b.market_summary or "",
                "keywords": [{"title": kw.get("title", ""), "category": kw.get("category", "")} for kw in keywords],
                "keywords_count": len(keywords),
            }
        )

    return {"history": history}
