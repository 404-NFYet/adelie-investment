"""Briefing API routes."""

import sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional

KST = timezone(timedelta(hours=9))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Add datapipeline to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "datapipeline"))

from app.core.database import get_db
from app.models.briefing import DailyBriefing, BriefingStock
from app.schemas.briefing import BriefingResponse, BriefingStock as BriefingStockSchema

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/today", response_model=BriefingResponse)
async def get_today_briefing(
    date: Optional[str] = Query(None, description="Date in YYYYMMDD format"),
    db: AsyncSession = Depends(get_db),
) -> BriefingResponse:
    """
    Get today's morning briefing.
    
    Returns market summary, top movers (gainers/losers), and high volume stocks.
    """
    # Parse date or use today
    if date:
        try:
            briefing_date = datetime.strptime(date.replace("-", ""), "%Y%m%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD.")
    else:
        briefing_date = datetime.now(KST).date()
    
    # Try to get from database first
    stmt = select(DailyBriefing).where(DailyBriefing.briefing_date == briefing_date)
    result = await db.execute(stmt)
    briefing = result.scalar_one_or_none()
    
    if briefing:
        # Get stocks for this briefing
        stocks_stmt = select(BriefingStock).where(BriefingStock.briefing_id == briefing.id)
        stocks_result = await db.execute(stocks_stmt)
        stocks = stocks_result.scalars().all()
        
        gainers = []
        losers = []
        high_volume = []
        
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
    
    # If not in DB, fetch live data
    try:
        from collectors.stock_collector import (
            get_top_movers,
            get_high_volume_stocks,
            get_market_summary,
        )
        
        # 오늘 데이터가 없을 수 있으므로 (주말/공휴일) 최근 거래일을 탐색
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
        
        # Format gainers
        gainers = [
            BriefingStockSchema(
                stock_code=item["ticker"],
                stock_name=item.get("name", "Unknown"),
                change_rate=float(item.get("등락률", 0)),
                volume=int(item.get("거래량", 0)),
                selection_reason="top_gainer",
                keywords=[],
            )
            for item in movers.get("gainers", [])
        ]
        
        # Format losers
        losers = [
            BriefingStockSchema(
                stock_code=item["ticker"],
                stock_name=item.get("name", "Unknown"),
                change_rate=float(item.get("등락률", 0)),
                volume=int(item.get("거래량", 0)),
                selection_reason="top_loser",
                keywords=[],
            )
            for item in movers.get("losers", [])
        ]
        
        # Format high volume
        high_volume = [
            BriefingStockSchema(
                stock_code=item["ticker"],
                stock_name=item.get("name", "Unknown"),
                change_rate=float(item.get("등락률", 0)),
                volume=int(item.get("거래량", 0)),
                selection_reason="high_volume",
                keywords=[],
            )
            for item in volume_data.get("high_volume", [])
        ]
        
        # Create market summary
        kospi_close = market.get("kospi", {}).get("close") if market.get("kospi") else None
        kosdaq_close = market.get("kosdaq", {}).get("close") if market.get("kosdaq") else None
        
        summary = f"오늘의 시장 현황입니다."
        if kospi_close:
            summary += f" KOSPI {kospi_close:,.0f}"
        if kosdaq_close:
            summary += f", KOSDAQ {kosdaq_close:,.0f}"
        
        if actual_date_str != date_str:
            summary = f"최근 거래일 시장 현황입니다."
        
        return BriefingResponse(
            date=actual_date_str,
            market_summary=summary,
            top_keywords=[],
            gainers=gainers,
            losers=losers,
            high_volume=high_volume,
            kospi=market.get("kospi") if market else None,
            kosdaq=market.get("kosdaq") if market else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch briefing data: {str(e)}"
        )
