"""브리핑 API 라우트 - /api/v1/briefings/*

통합: 시장 데이터(DailyBriefing) + 내러티브(DailyNarrative) 엔드포인트
"""
import json as json_module
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.briefing import DailyBriefing, BriefingStock
from app.models.narrative import DailyNarrative, NarrativeScenario
from app.schemas.briefing import BriefingResponse, BriefingStock as BriefingStockSchema
from app.services.redis_cache import get_redis_cache

KST = timezone(timedelta(hours=9))

router = APIRouter(prefix="/briefings", tags=["briefings"])


@router.get("/latest")
async def get_latest_briefing(db: AsyncSession = Depends(get_db)):
    """최신 브리핑 조회"""
    # Redis 캐시 체크
    cache_key = "api:briefings:latest"
    try:
        cache = await get_redis_cache()
        cached = await cache.get(cache_key)
        if cached:
            return json_module.loads(cached)
    except Exception:
        pass

    result = await db.execute(
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .order_by(desc(DailyNarrative.date))
        .limit(1)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(404, "No briefings available")

    data = _serialize_narrative(narrative)

    # Redis 캐시 저장 (5분)
    try:
        await cache.set(cache_key, json_module.dumps(data, ensure_ascii=False, default=str), 300)
    except Exception:
        pass

    return data


@router.get("/list")
async def list_briefings(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """브리핑 목록 조회 (페이지네이션)"""
    offset = (page - 1) * size
    result = await db.execute(
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .order_by(desc(DailyNarrative.date))
        .offset(offset)
        .limit(size)
    )
    narratives = result.scalars().all()
    return [_serialize_narrative(n) for n in narratives]


@router.get("/{briefing_id}")
async def get_briefing(briefing_id: str, db: AsyncSession = Depends(get_db)):
    """특정 브리핑 조회"""
    result = await db.execute(
        select(DailyNarrative)
        .options(selectinload(DailyNarrative.scenarios))
        .where(DailyNarrative.id == briefing_id)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(404, "Briefing not found")
    return _serialize_narrative(narrative)


@router.get("/today", response_model=BriefingResponse)
async def get_today_briefing(
    date: Optional[str] = Query(None, description="Date in YYYYMMDD format"),
    db: AsyncSession = Depends(get_db),
) -> BriefingResponse:
    """오늘의 시장 브리핑 조회 (상승/하락/거래량 종목)"""
    if date:
        try:
            briefing_date = datetime.strptime(date.replace("-", ""), "%Y%m%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD.")
    else:
        briefing_date = datetime.now(KST).date()

    stmt = select(DailyBriefing).where(DailyBriefing.briefing_date == briefing_date)
    result = await db.execute(stmt)
    briefing = result.scalar_one_or_none()

    if briefing:
        stocks_stmt = select(BriefingStock).where(BriefingStock.briefing_id == briefing.id)
        stocks_result = await db.execute(stocks_stmt)
        stocks = stocks_result.scalars().all()

        gainers, losers, high_volume = [], [], []
        for stock in stocks:
            stock_data = BriefingStockSchema(
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                change_rate=float(stock.change_rate) if stock.change_rate else 0.0,
                volume=stock.volume or 0,
                selection_reason=stock.selection_reason,
                keywords=stock.keywords.get("keywords", []) if stock.keywords else [],
            )
            if stock.selection_reason == "top_gainer":
                gainers.append(stock_data)
            elif stock.selection_reason == "top_loser":
                losers.append(stock_data)
            elif stock.selection_reason == "high_volume":
                high_volume.append(stock_data)

        return BriefingResponse(
            date=briefing_date.strftime("%Y%m%d"),
            market_summary=briefing.market_summary or "시장 요약이 없습니다.",
            top_keywords=briefing.top_keywords.get("keywords", []) if briefing.top_keywords else [],
            gainers=gainers,
            losers=losers,
            high_volume=high_volume,
        )

    # DB에 없으면 실시간 데이터 조회
    try:
        from collectors.stock_collector import (
            get_top_movers,
            get_high_volume_stocks,
            get_market_summary,
        )

        date_str = briefing_date.strftime("%Y%m%d")
        movers = None
        volume_data = None
        market = None
        actual_date_str = date_str

        for days_back in range(0, 5):
            try:
                try_date = briefing_date - timedelta(days=days_back)
                try_date_str = try_date.strftime("%Y%m%d")
                test_movers = get_top_movers(try_date_str, top_n=5)
                if test_movers.get("gainers") or test_movers.get("losers"):
                    movers = test_movers
                    volume_data = get_high_volume_stocks(try_date_str, top_n=5)
                    market = get_market_summary(try_date_str)
                    actual_date_str = try_date_str
                    break
            except Exception:
                continue

        if not movers:
            raise HTTPException(status_code=503, detail="No market data available for recent trading days")

        gainers = [
            BriefingStockSchema(
                stock_code=item["ticker"], stock_name=item.get("name", "Unknown"),
                change_rate=float(item.get("등락률", 0)), volume=int(item.get("거래량", 0)),
                selection_reason="top_gainer", keywords=[],
            ) for item in movers.get("gainers", [])
        ]
        losers = [
            BriefingStockSchema(
                stock_code=item["ticker"], stock_name=item.get("name", "Unknown"),
                change_rate=float(item.get("등락률", 0)), volume=int(item.get("거래량", 0)),
                selection_reason="top_loser", keywords=[],
            ) for item in movers.get("losers", [])
        ]
        high_volume = [
            BriefingStockSchema(
                stock_code=item["ticker"], stock_name=item.get("name", "Unknown"),
                change_rate=float(item.get("등락률", 0)), volume=int(item.get("거래량", 0)),
                selection_reason="high_volume", keywords=[],
            ) for item in volume_data.get("high_volume", [])
        ]

        kospi_close = market.get("kospi", {}).get("close") if market.get("kospi") else None
        kosdaq_close = market.get("kosdaq", {}).get("close") if market.get("kosdaq") else None
        summary = "오늘의 시장 현황입니다."
        if kospi_close:
            summary += f" KOSPI {kospi_close:,.0f}"
        if kosdaq_close:
            summary += f", KOSDAQ {kosdaq_close:,.0f}"
        if actual_date_str != date_str:
            summary = "최근 거래일 시장 현황입니다."

        return BriefingResponse(
            date=actual_date_str, market_summary=summary, top_keywords=[],
            gainers=gainers, losers=losers, high_volume=high_volume,
            kospi=market.get("kospi") if market else None,
            kosdaq=market.get("kosdaq") if market else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unable to fetch briefing data: {str(e)}")


def _serialize_narrative(narrative):
    """내러티브 직렬화 헬퍼"""
    return {
        "id": str(narrative.id),
        "date": narrative.date.isoformat(),
        "main_keywords": narrative.main_keywords or [],
        "glossary": narrative.glossary or {},
        "scenarios": [
            {
                "id": str(s.id),
                "title": s.title,
                "summary": s.summary,
                "sources": s.sources or [],
                "related_companies": s.related_companies or [],
                "mirroring_data": s.mirroring_data or {},
                "narrative_sections": s.narrative_sections or {},
                "sort_order": s.sort_order,
            }
            for s in sorted(narrative.scenarios, key=lambda x: x.sort_order)
        ],
        "created_at": narrative.created_at.isoformat() if narrative.created_at else None,
    }
