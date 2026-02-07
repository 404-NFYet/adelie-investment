"""내러티브 스토리 API 라우트 (7단계).

빌더 로직은 app.services.narrative_builder로 분리됨.
이 파일은 DB 쿼리 + 빌더 호출 + 응답 조립만 담당.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.historical_case import HistoricalCase, CaseStockRelation
from app.models.briefing import DailyBriefing, BriefingStock
from app.schemas.narrative import NarrativeResponse
from app.services.narrative_builder import (
    split_paragraphs,
    build_all_steps,
)

logger = logging.getLogger("narrative_api.narrative")

router = APIRouter(prefix="/narrative", tags=["Narrative"])


# --- DB 쿼리 헬퍼 ---

async def _fetch_case(db: AsyncSession, case_id: int) -> Optional[HistoricalCase]:
    result = await db.execute(select(HistoricalCase).where(HistoricalCase.id == case_id))
    return result.scalar_one_or_none()


async def _fetch_case_stocks(db: AsyncSession, case_id: int) -> list[CaseStockRelation]:
    result = await db.execute(select(CaseStockRelation).where(CaseStockRelation.case_id == case_id))
    return list(result.scalars().all())


async def _fetch_latest_briefing(db: AsyncSession) -> Optional[DailyBriefing]:
    result = await db.execute(
        select(DailyBriefing).options(selectinload(DailyBriefing.stocks)).order_by(DailyBriefing.briefing_date.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def _fetch_market_history(db: AsyncSession, days: int = 5) -> list[dict]:
    try:
        result = await db.execute(
            text("SELECT date, index_code, open, high, low, close, volume FROM market_daily_history ORDER BY date DESC LIMIT :limit"),
            {"limit": days * 2},
        )
        rows = result.mappings().all()
        by_date: dict = {}
        for row in rows:
            d = str(row["date"])
            if d not in by_date:
                by_date[d] = {}
            idx = "kospi" if str(row["index_code"]) == "1001" else "kosdaq"
            by_date[d][idx] = {
                "open": float(row["open"]) if row["open"] else None,
                "high": float(row["high"]) if row["high"] else None,
                "low": float(row["low"]) if row["low"] else None,
                "close": float(row["close"]) if row["close"] else None,
                "volume": int(row["volume"]) if row["volume"] else None,
            }
        sorted_dates = sorted(by_date.keys(), reverse=True)[:days]
        return [{"date": d, **by_date[d]} for d in sorted_dates]
    except Exception as exc:
        logger.warning("market_daily_history 조회 실패: %s", exc)
        return []


# --- 엔드포인트 ---

@router.get("/{case_id}", response_model=NarrativeResponse)
async def get_narrative(case_id: int, db: AsyncSession = Depends(get_db)) -> NarrativeResponse:
    """사례 기반 내러티브 스토리를 7단계로 반환."""
    case = await _fetch_case(db, case_id)
    case_stocks = await _fetch_case_stocks(db, case_id)
    briefing = await _fetch_latest_briefing(db)
    market_history = await _fetch_market_history(db, days=5)

    if not case:
        raise HTTPException(status_code=404, detail="해당 사례를 찾을 수 없습니다.")

    kw_data: dict = case.keywords if isinstance(case.keywords, dict) else {}
    comparison: dict = kw_data.get("comparison", {})
    narrative_data: Optional[dict] = kw_data.get("narrative")
    keyword_list: list[str] = kw_data.get("keywords", [])
    keyword = keyword_list[0] if keyword_list else case.title
    sync_rate: int = comparison.get("sync_rate", 0)

    paragraphs = split_paragraphs(case.full_content or case.summary or "")
    briefing_stocks: list[BriefingStock] = list(briefing.stocks) if briefing else []

    # LLM narrative가 있으면 우선 사용, 없으면 fallback
    steps = build_all_steps(
        narrative_data=narrative_data,
        comparison=comparison,
        paragraphs=paragraphs,
        briefing=briefing,
        briefing_stocks=briefing_stocks,
        case_stocks=case_stocks,
    )

    related_companies = [
        {"stock_code": r.stock_code, "stock_name": r.stock_name, "relation_type": r.relation_type or "related", "impact_description": r.impact_description or ""}
        for r in case_stocks
    ]

    market_data = None
    if briefing:
        market_data = {"briefing_date": str(briefing.briefing_date), "market_summary": briefing.market_summary, "top_keywords": briefing.top_keywords}

    return NarrativeResponse(
        case_id=case.id, keyword=keyword, steps=steps, related_companies=related_companies,
        sync_rate=sync_rate, market_data=market_data, market_history=market_history or None,
    )
