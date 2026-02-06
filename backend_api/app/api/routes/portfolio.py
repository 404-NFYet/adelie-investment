"""포트폴리오 및 모의투자 API 라우트."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.portfolio import SimulationTrade
from app.models.reward import BriefingReward
from app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioSummary,
    HoldingResponse,
    TradeRequest,
    TradeResponse,
    TradeHistoryResponse,
    StockPriceResponse,
    BatchStockPriceResponse,
    BriefingCompleteRequest,
    RewardResponse,
    RewardItem,
    RewardsListResponse,
)
from app.services.portfolio_service import (
    get_or_create_portfolio,
    execute_trade,
    complete_briefing_reward,
    check_and_apply_multiplier,
)
from app.services.stock_price_service import get_current_price, get_batch_prices

logger = logging.getLogger("narrative_api.portfolio")

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


# ──────────────────── Portfolio ────────────────────


@router.get("/{user_id}", response_model=PortfolioResponse)
async def get_portfolio(user_id: int, db: AsyncSession = Depends(get_db)):
    """포트폴리오 전체 조회 (실시간 평가액 포함)."""
    portfolio = await get_or_create_portfolio(db, user_id)

    holdings_response = []
    total_holdings_value = 0.0

    for h in portfolio.holdings:
        price_data = await get_current_price(h.stock_code)
        current_price = price_data["current_price"] if price_data else 0
        current_value = current_price * h.quantity
        invested = float(h.avg_buy_price) * h.quantity
        profit_loss = current_value - invested
        profit_loss_pct = (profit_loss / invested * 100) if invested > 0 else 0

        total_holdings_value += current_value
        holdings_response.append(HoldingResponse(
            stock_code=h.stock_code,
            stock_name=h.stock_name,
            quantity=h.quantity,
            avg_buy_price=float(h.avg_buy_price),
            current_price=current_price,
            current_value=current_value,
            profit_loss=profit_loss,
            profit_loss_pct=round(profit_loss_pct, 2),
        ))

    total_value = portfolio.current_cash + total_holdings_value
    total_pl = total_value - portfolio.initial_cash
    total_pl_pct = (total_pl / portfolio.initial_cash * 100) if portfolio.initial_cash > 0 else 0

    return PortfolioResponse(
        id=portfolio.id,
        portfolio_name=portfolio.portfolio_name,
        initial_cash=portfolio.initial_cash,
        current_cash=portfolio.current_cash,
        holdings=holdings_response,
        total_value=total_value,
        total_profit_loss=total_pl,
        total_profit_loss_pct=round(total_pl_pct, 2),
    )


@router.get("/{user_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(user_id: int, db: AsyncSession = Depends(get_db)):
    """경량 포트폴리오 요약 (BottomNav 뱃지용)."""
    portfolio = await get_or_create_portfolio(db, user_id)
    total_holdings = 0
    for h in portfolio.holdings:
        price_data = await get_current_price(h.stock_code)
        if price_data:
            total_holdings += price_data["current_price"] * h.quantity

    total_value = portfolio.current_cash + total_holdings
    total_pl = total_value - portfolio.initial_cash
    total_pl_pct = (total_pl / portfolio.initial_cash * 100) if portfolio.initial_cash > 0 else 0

    return PortfolioSummary(
        total_value=int(total_value),
        total_profit_loss=int(total_pl),
        total_profit_loss_pct=round(total_pl_pct, 2),
    )


# ──────────────────── Trading ────────────────────


@router.post("/{user_id}/trade", response_model=TradeResponse)
async def create_trade(
    user_id: int, req: TradeRequest, db: AsyncSession = Depends(get_db)
):
    """매수/매도 실행."""
    portfolio = await get_or_create_portfolio(db, user_id)
    try:
        trade = await execute_trade(
            db, portfolio,
            req.stock_code, req.stock_name,
            req.trade_type, req.quantity,
            req.trade_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.refresh(portfolio)

    return TradeResponse(
        id=trade.id,
        trade_type=trade.trade_type,
        stock_code=trade.stock_code,
        stock_name=trade.stock_name,
        quantity=trade.quantity,
        price=float(trade.price),
        total_amount=float(trade.total_amount),
        trade_reason=trade.trade_reason,
        traded_at=trade.traded_at,
        remaining_cash=portfolio.current_cash,
    )


@router.get("/{user_id}/trades", response_model=TradeHistoryResponse)
async def get_trade_history(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """거래 내역 조회."""
    portfolio = await get_or_create_portfolio(db, user_id)
    stmt = (
        select(SimulationTrade)
        .where(SimulationTrade.portfolio_id == portfolio.id)
        .order_by(SimulationTrade.traded_at.desc())
        .offset(offset).limit(limit)
    )
    result = await db.execute(stmt)
    trades = result.scalars().all()

    return TradeHistoryResponse(
        trades=[
            TradeResponse(
                id=t.id,
                trade_type=t.trade_type,
                stock_code=t.stock_code,
                stock_name=t.stock_name,
                quantity=t.quantity,
                price=float(t.price),
                total_amount=float(t.total_amount),
                trade_reason=t.trade_reason,
                traded_at=t.traded_at,
                remaining_cash=portfolio.current_cash,
            )
            for t in trades
        ],
        total_count=len(trades),
    )


# ──────────────────── Stock Prices ────────────────────


@router.get("/stock/price/{stock_code}", response_model=StockPriceResponse)
async def get_stock_price(stock_code: str):
    """단일 종목 현재가 조회."""
    price_data = await get_current_price(stock_code)
    if not price_data:
        raise HTTPException(status_code=404, detail=f"종목 {stock_code} 가격 조회 실패")
    return StockPriceResponse(**price_data)


@router.post("/stock/prices", response_model=BatchStockPriceResponse)
async def get_batch_stock_prices(stock_codes: list[str]):
    """복수 종목 현재가 일괄 조회."""
    prices = await get_batch_prices(stock_codes)
    return BatchStockPriceResponse(
        prices=[StockPriceResponse(**p) for p in prices],
        date=datetime.now().strftime("%Y%m%d"),
    )


# ──────────────────── Rewards ────────────────────


@router.post("/{user_id}/reward", response_model=RewardResponse)
async def claim_briefing_reward(
    user_id: int, req: BriefingCompleteRequest, db: AsyncSession = Depends(get_db)
):
    """브리핑 완료 보상 청구."""
    try:
        reward = await complete_briefing_reward(db, user_id, req.case_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return RewardResponse(
        reward_id=reward.id,
        base_reward=reward.base_reward,
        status=reward.status,
        maturity_at=reward.maturity_at,
        message=f"브리핑 완료! {reward.base_reward:,.0f}원 지급. 7일 후 수익률에 따라 1.5배 보너스!",
    )


@router.get("/{user_id}/rewards", response_model=RewardsListResponse)
async def get_rewards(user_id: int, db: AsyncSession = Depends(get_db)):
    """보상 목록 조회 (만기 도래 시 자동 체크)."""
    stmt = (
        select(BriefingReward)
        .where(BriefingReward.user_id == user_id)
        .order_by(BriefingReward.created_at.desc())
    )
    result = await db.execute(stmt)
    rewards = result.scalars().all()

    items = []
    for r in rewards:
        r = await check_and_apply_multiplier(db, r)
        items.append(RewardItem(
            reward_id=r.id,
            case_id=r.case_id,
            base_reward=r.base_reward,
            multiplier=r.multiplier,
            final_reward=r.final_reward,
            status=r.status,
            maturity_at=r.maturity_at.isoformat(),
        ))

    return RewardsListResponse(rewards=items)
