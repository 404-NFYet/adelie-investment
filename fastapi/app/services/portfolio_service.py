"""Portfolio management service - 포트폴리오/거래/보상 비즈니스 로직."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portfolio import UserPortfolio, PortfolioHolding, SimulationTrade
from app.models.reward import BriefingReward
from app.services.stock_price_service import get_current_price, get_batch_prices

logger = logging.getLogger(__name__)

BRIEFING_BASE_REWARD = 100_000  # 브리핑 완료 기본 보상 (10만원)
REWARD_MATURITY_DAYS = 7  # 멀티플라이어 체크까지 대기일
PROFIT_MULTIPLIER = 1.5  # 수익 시 보너스 배율


async def get_or_create_portfolio(db: AsyncSession, user_id: int) -> UserPortfolio:
    """유저의 기본 포트폴리오를 조회하거나, 없으면 자동 생성한다."""
    stmt = (
        select(UserPortfolio)
        .where(UserPortfolio.user_id == user_id)
        .options(
            selectinload(UserPortfolio.holdings),
            selectinload(UserPortfolio.trades),
        )
    )
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        portfolio = UserPortfolio(
            user_id=user_id,
            portfolio_name="내 포트폴리오",
            initial_cash=1_000_000,
            current_cash=1_000_000,
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio, attribute_names=["holdings", "trades"])

    return portfolio


async def execute_trade(
    db: AsyncSession,
    portfolio: UserPortfolio,
    stock_code: str,
    stock_name: str,
    trade_type: str,
    quantity: int,
    trade_reason: str = None,
) -> SimulationTrade:
    """매수 또는 매도를 실행한다.

    Raises:
        ValueError: 잔액 부족, 보유 수량 부족, 또는 휴장일 시
    """
    # 휴장일 체크
    from app.services.market_calendar import is_kr_market_open_today
    if not await is_kr_market_open_today():
        raise ValueError("오늘은 한국 주식시장 휴장일입니다")

    price_data = await get_current_price(stock_code)
    if not price_data:
        raise ValueError(f"종목 {stock_code}의 가격을 조회할 수 없습니다")

    price = price_data["current_price"]
    total = price * quantity

    if trade_type == "buy":
        if portfolio.current_cash < total:
            raise ValueError(
                f"잔액 부족: 필요 {total:,.0f}원, 보유 {portfolio.current_cash:,.0f}원"
            )
        portfolio.current_cash -= int(total)

        # 기존 보유 종목이면 평균단가 재계산, 없으면 신규 생성
        holding = await _get_holding(db, portfolio.id, stock_code)
        if holding:
            old_total = float(holding.avg_buy_price) * holding.quantity
            new_total = old_total + total
            holding.quantity += quantity
            holding.avg_buy_price = new_total / holding.quantity
        else:
            holding = PortfolioHolding(
                portfolio_id=portfolio.id,
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                avg_buy_price=price,
            )
            db.add(holding)

    elif trade_type == "sell":
        holding = await _get_holding(db, portfolio.id, stock_code)
        if not holding or holding.quantity < quantity:
            available = holding.quantity if holding else 0
            raise ValueError(f"보유 수량 부족: 보유 {available}주")
        holding.quantity -= quantity
        portfolio.current_cash += int(total)

        if holding.quantity == 0:
            await db.delete(holding)
    else:
        raise ValueError(f"잘못된 거래 타입: {trade_type}")

    trade = SimulationTrade(
        portfolio_id=portfolio.id,
        trade_type=trade_type,
        stock_code=stock_code,
        stock_name=stock_name,
        quantity=quantity,
        price=price,
        total_amount=total,
        trade_reason=trade_reason,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def _get_holding(
    db: AsyncSession, portfolio_id: int, stock_code: str
) -> PortfolioHolding | None:
    stmt = select(PortfolioHolding).where(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.stock_code == stock_code,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def complete_briefing_reward(
    db: AsyncSession, user_id: int, case_id: int
) -> BriefingReward:
    """브리핑 완료 보상을 지급한다.

    기본 보상(10만원)을 즉시 현금에 추가하고,
    7일 후 포트폴리오 수익률에 따라 1.5배 보너스 적용/소멸을 결정한다.

    Raises:
        ValueError: 이미 해당 브리핑에 대한 보상을 받은 경우
    """
    portfolio = await get_or_create_portfolio(db, user_id)

    # 중복 보상 방지
    existing = await db.execute(
        select(BriefingReward).where(
            BriefingReward.user_id == user_id,
            BriefingReward.case_id == case_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("이미 이 브리핑에 대한 보상을 받았습니다")

    # 기본 보상 즉시 지급
    portfolio.current_cash += BRIEFING_BASE_REWARD
    portfolio.total_rewards_received += BRIEFING_BASE_REWARD

    reward = BriefingReward(
        user_id=user_id,
        portfolio_id=portfolio.id,
        case_id=case_id,
        base_reward=BRIEFING_BASE_REWARD,
        multiplier=1.0,
        final_reward=BRIEFING_BASE_REWARD,
        status="pending",
        maturity_at=datetime.utcnow() + timedelta(days=REWARD_MATURITY_DAYS),
    )
    db.add(reward)
    await db.commit()
    await db.refresh(reward)
    return reward


async def check_and_apply_multiplier(
    db: AsyncSession, reward: BriefingReward
) -> BriefingReward:
    """만기가 지난 보상의 멀티플라이어를 체크하고 적용/소멸 처리한다.

    - 포트폴리오 수익(+): 보너스 0.5배분 추가 지급 → status=applied
    - 포트폴리오 손실(-): 보너스 소멸 → status=expired
    """
    if reward.status != "pending":
        return reward
    if datetime.utcnow() < reward.maturity_at:
        return reward

    portfolio = await get_or_create_portfolio(db, reward.user_id)

    # 전체 포트폴리오 평가액 계산
    total_holdings_value = 0
    stmt = select(PortfolioHolding).where(
        PortfolioHolding.portfolio_id == portfolio.id
    )
    result = await db.execute(stmt)
    holdings = result.scalars().all()

    # 배치 가격 조회 (N+1 방지)
    codes = [h.stock_code for h in holdings]
    batch_results = await get_batch_prices(codes) if codes else []
    price_map = {p["stock_code"]: p["current_price"] for p in batch_results}

    for h in holdings:
        cp = price_map.get(h.stock_code)
        if cp:
            total_holdings_value += cp * h.quantity

    total_value = portfolio.current_cash + total_holdings_value
    profit = total_value - portfolio.initial_cash - portfolio.total_rewards_received

    if profit > 0:
        # 수익: 1.5배 보너스 (추가분만 지급)
        bonus = int(reward.base_reward * (PROFIT_MULTIPLIER - 1.0))
        reward.multiplier = PROFIT_MULTIPLIER
        reward.final_reward = reward.base_reward + bonus
        portfolio.current_cash += bonus
        portfolio.total_rewards_received += bonus
        reward.status = "applied"
    else:
        # 손실: 보너스 소멸
        reward.multiplier = 1.0
        reward.status = "expired"

    reward.applied_at = datetime.utcnow()
    await db.commit()
    return reward
