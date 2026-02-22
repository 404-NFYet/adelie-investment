"""Portfolio management service - 포트폴리오/거래/보상 비즈니스 로직."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portfolio import PortfolioHolding, SimulationTrade, UserPortfolio
from app.models.reward import BriefingReward
from app.services.market_calendar import is_kr_market_open_today
from app.services.stock_price_service import get_batch_prices, get_current_price

logger = logging.getLogger(__name__)

BRIEFING_BASE_REWARD = 100_000  # 브리핑 완료 기본 보상 (10만원)
REWARD_MATURITY_DAYS = 7  # 멀티플라이어 체크까지 대기일
PROFIT_MULTIPLIER = 1.5  # 수익 시 보너스 배율

# 현실형 체결 시뮬레이션 파라미터
BASE_FEE_RATE = 0.00015  # 0.015%
BASE_SLIPPAGE_BPS = 6.0
MAX_MARKET_PARTICIPATION = 0.12  # 일 거래량의 12%
LOW_LIQUIDITY_VOLUME = 10_000
PRICE_LIMIT_NEAR_PCT = 28.5  # 상/하한 30% 근접 구간
SHORT_DEFAULT_BORROW_BPS = 8  # 일일 차입수수료(가정)
MAX_LEVERAGE = 2.0


@dataclass
class TradeExecutionResult:
    """체결 결과 + 실행 메타."""

    trade: SimulationTrade
    executed_quantity: int
    remaining_quantity: int
    requested_price: float
    executed_price: float | None
    slippage_bps: float
    fee_amount: float
    order_kind: str
    order_status: str
    position_side: str
    leverage: float


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _round_price(value: float) -> float:
    return round(float(value), 2)


def _estimate_fill_quantity(
    requested_quantity: int,
    volume: int,
    change_rate: float,
    *,
    is_buy_order: bool,
) -> tuple[int, str, float]:
    """유동성/상하한 근접도 기반 체결 수량 추정.

    Returns:
        executed_qty, order_status, participation_ratio
    """
    requested_quantity = max(1, int(requested_quantity))
    normalized_volume = max(0, int(volume or 0))

    if normalized_volume <= 0:
        return requested_quantity, "filled", 0.0

    max_fill = max(1, int(normalized_volume * MAX_MARKET_PARTICIPATION))

    near_upper = change_rate >= PRICE_LIMIT_NEAR_PCT
    near_lower = change_rate <= -PRICE_LIMIT_NEAR_PCT
    directional_pressure = (is_buy_order and near_upper) or ((not is_buy_order) and near_lower)
    if directional_pressure:
        max_fill = max(1, int(max_fill * 0.35))

    executed_qty = min(requested_quantity, max_fill)
    participation = requested_quantity / max(1, normalized_volume)
    status = "filled" if executed_qty >= requested_quantity else "partial"

    return executed_qty, status, participation


def _compute_slippage_bps(
    participation: float,
    volume: int,
    change_rate: float,
    *,
    is_buy_order: bool,
) -> float:
    bps = BASE_SLIPPAGE_BPS

    # 참여율이 높을수록 슬리피지 증가
    bps += min(42.0, max(0.0, participation - 0.01) * 2800.0)

    # 거래량이 적으면 추가 페널티
    if volume > 0 and volume < LOW_LIQUIDITY_VOLUME:
        bps += 8.0

    # 상/하한 근처에서 체결 난이도 상승
    near_upper = change_rate >= PRICE_LIMIT_NEAR_PCT
    near_lower = change_rate <= -PRICE_LIMIT_NEAR_PCT
    if (is_buy_order and near_upper) or ((not is_buy_order) and near_lower):
        bps += 16.0

    return round(bps, 2)


def _resolve_execution_price(
    current_price: float,
    order_kind: str,
    trade_type: str,
    slippage_bps: float,
    *,
    target_price: float | None = None,
) -> float:
    """주문 방향에 맞는 체결가 계산."""
    is_buy_order = trade_type == "buy"
    signed_bps = slippage_bps if is_buy_order else -slippage_bps

    executed = current_price * (1.0 + signed_bps / 10_000.0)

    if order_kind == "limit" and target_price is not None:
        if is_buy_order:
            executed = min(executed, target_price)
        else:
            executed = max(executed, target_price)

    return _round_price(executed)


def _require_trade_direction(position_side: str, trade_type: str) -> None:
    if position_side == "long":
        if trade_type not in {"buy", "sell"}:
            raise ValueError(f"잘못된 거래 타입: {trade_type}")
        return

    if position_side == "short":
        if trade_type not in {"sell", "buy"}:
            raise ValueError(f"잘못된 거래 타입: {trade_type}")
        return

    raise ValueError(f"지원하지 않는 포지션: {position_side}")


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
    portfolio = result.scalars().first()  # 중복 시 에러 대신 첫 번째 반환

    if not portfolio:
        portfolio = UserPortfolio(
            user_id=user_id,
            portfolio_name="내 포트폴리오",
            initial_cash=1_000_000,
            current_cash=1_000_000,
        )
        db.add(portfolio)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(stmt)
            portfolio = result.scalars().first()
        else:
            await db.commit()
            await db.refresh(portfolio, attribute_names=["holdings", "trades"])

    return portfolio


async def _get_holding(
    db: AsyncSession,
    portfolio_id: int,
    stock_code: str,
    position_side: str = "long",
) -> PortfolioHolding | None:
    stmt = select(PortfolioHolding).where(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.stock_code == stock_code,
        PortfolioHolding.position_side == position_side,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _apply_short_funding_cost(
    portfolio: UserPortfolio,
    holding: PortfolioHolding,
    *,
    now: datetime,
) -> float:
    """공매도 포지션의 누적 차입수수료를 차감한다."""
    if holding.position_side != "short" or holding.quantity <= 0:
        return 0.0

    last_funding = holding.last_funding_at or holding.updated_at or holding.created_at or now
    elapsed_days = (now - last_funding).total_seconds() / 86_400
    if elapsed_days <= 0:
        holding.last_funding_at = now
        return 0.0

    borrow_bps = int(holding.borrow_rate_bps or SHORT_DEFAULT_BORROW_BPS)
    notional = float(holding.avg_buy_price) * holding.quantity
    cost = notional * (borrow_bps / 10_000) * elapsed_days
    cost = max(0.0, cost)

    if cost > 0:
        portfolio.current_cash -= int(round(cost))
    holding.last_funding_at = now
    return round(cost, 2)


async def execute_trade(
    db: AsyncSession,
    portfolio: UserPortfolio,
    stock_code: str,
    stock_name: str,
    trade_type: str,
    quantity: int,
    trade_reason: str | None = None,
    *,
    order_kind: str = "market",
    target_price: int | None = None,
    position_side: str = "long",
    leverage: float = 1.0,
) -> TradeExecutionResult:
    """매수/매도 실행 (현실형 시뮬레이션).

    - 시장가/지정가
    - 슬리피지/유동성 cap
    - 부분체결/미체결 상태
    - 공매도(short)/레버리지(최대 2x)
    """
    if quantity <= 0:
        raise ValueError("수량은 1주 이상이어야 합니다")

    trade_type = str(trade_type or "").strip().lower()
    order_kind = str(order_kind or "market").strip().lower()
    position_side = str(position_side or "long").strip().lower()
    leverage = float(leverage or 1.0)

    if order_kind not in {"market", "limit"}:
        raise ValueError("order_kind는 market 또는 limit만 지원합니다")
    _require_trade_direction(position_side, trade_type)

    if leverage < 1.0 or leverage > MAX_LEVERAGE:
        raise ValueError(f"레버리지는 1.0~{MAX_LEVERAGE:.1f} 범위만 지원합니다")

    if order_kind == "limit" and (target_price is None or int(target_price) <= 0):
        raise ValueError("지정가 주문에는 target_price가 필요합니다")

    # 휴장일 체크
    if not await is_kr_market_open_today():
        raise ValueError("오늘은 한국 주식시장 휴장일입니다")

    price_data = await get_current_price(stock_code)
    if not price_data:
        raise ValueError(f"종목 {stock_code}의 가격을 조회할 수 없습니다")

    now = datetime.utcnow()
    current_price = float(price_data["current_price"])
    volume = int(price_data.get("volume") or 0)
    change_rate = float(price_data.get("change_rate") or 0.0)
    requested_price = float(target_price if target_price is not None else current_price)

    # 지정가 즉시체결 가능 여부 판정
    should_execute = order_kind == "market"
    if order_kind == "limit":
        if trade_type == "buy" and requested_price >= current_price:
            should_execute = True
        elif trade_type == "sell" and requested_price <= current_price:
            should_execute = True

    if not should_execute:
        pending_trade = SimulationTrade(
            portfolio_id=portfolio.id,
            trade_type=trade_type,
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            filled_quantity=0,
            price=requested_price,
            requested_price=requested_price,
            executed_price=None,
            slippage_bps=0,
            fee_amount=0,
            order_kind=order_kind,
            order_status="pending",
            position_side=position_side,
            leverage=leverage,
            total_amount=0,
            trade_reason=trade_reason,
        )
        db.add(pending_trade)
        await db.commit()
        await db.refresh(pending_trade)
        return TradeExecutionResult(
            trade=pending_trade,
            executed_quantity=0,
            remaining_quantity=quantity,
            requested_price=requested_price,
            executed_price=None,
            slippage_bps=0.0,
            fee_amount=0.0,
            order_kind=order_kind,
            order_status="pending",
            position_side=position_side,
            leverage=leverage,
        )

    is_buy_order = trade_type == "buy"
    executed_qty, order_status, participation = _estimate_fill_quantity(
        quantity,
        volume,
        change_rate,
        is_buy_order=is_buy_order,
    )
    if executed_qty <= 0:
        raise ValueError("현재 유동성으로는 체결 가능한 수량이 없습니다")

    slippage_bps = _compute_slippage_bps(
        participation,
        volume,
        change_rate,
        is_buy_order=is_buy_order,
    )
    executed_price = _resolve_execution_price(
        current_price,
        order_kind,
        trade_type,
        slippage_bps,
        target_price=requested_price if order_kind == "limit" else None,
    )

    trade_notional = executed_price * executed_qty
    fee_amount = round(trade_notional * BASE_FEE_RATE, 2)

    holding = await _get_holding(db, portfolio.id, stock_code, position_side)

    if position_side == "long":
        if trade_type == "buy":
            margin_required = trade_notional / leverage
            cash_needed = margin_required + fee_amount
            if portfolio.current_cash < cash_needed:
                raise ValueError(
                    f"잔액 부족: 필요 {cash_needed:,.0f}원, 보유 {portfolio.current_cash:,.0f}원"
                )
            portfolio.current_cash -= int(round(cash_needed))

            if holding:
                old_total = float(holding.avg_buy_price) * holding.quantity
                new_total = old_total + trade_notional
                holding.quantity += executed_qty
                holding.avg_buy_price = _round_price(new_total / holding.quantity)
                holding.leverage = _clamp(max(float(holding.leverage or 1.0), leverage), 1.0, MAX_LEVERAGE)
                holding.updated_at = now
            else:
                holding = PortfolioHolding(
                    portfolio_id=portfolio.id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=executed_qty,
                    avg_buy_price=executed_price,
                    position_side="long",
                    leverage=leverage,
                    borrow_rate_bps=0,
                    last_funding_at=None,
                )
                db.add(holding)

        else:  # long + sell (청산)
            if not holding or holding.quantity < executed_qty:
                available = holding.quantity if holding else 0
                raise ValueError(f"보유 수량 부족: 보유 {available}주")

            base_price = float(holding.avg_buy_price)
            effective_leverage = max(float(holding.leverage or 1.0), 1.0)
            margin_release = base_price * executed_qty / effective_leverage
            pnl = (executed_price - base_price) * executed_qty
            cash_delta = margin_release + pnl - fee_amount
            portfolio.current_cash += int(round(cash_delta))

            holding.quantity -= executed_qty
            holding.updated_at = now
            if holding.quantity == 0:
                await db.delete(holding)

    else:  # short 포지션
        if trade_type == "sell":  # short open/increase
            margin_required = trade_notional / leverage
            cash_needed = margin_required + fee_amount
            if portfolio.current_cash < cash_needed:
                raise ValueError(
                    f"증거금 부족: 필요 {cash_needed:,.0f}원, 보유 {portfolio.current_cash:,.0f}원"
                )

            portfolio.current_cash -= int(round(cash_needed))
            if holding:
                # 기존 공매도 포지션의 차입수수료 선반영
                await _apply_short_funding_cost(portfolio, holding, now=now)
                old_total = float(holding.avg_buy_price) * holding.quantity
                new_total = old_total + trade_notional
                holding.quantity += executed_qty
                holding.avg_buy_price = _round_price(new_total / holding.quantity)
                holding.leverage = _clamp(max(float(holding.leverage or 1.0), leverage), 1.0, MAX_LEVERAGE)
                holding.updated_at = now
                holding.last_funding_at = now
                if not holding.borrow_rate_bps:
                    holding.borrow_rate_bps = SHORT_DEFAULT_BORROW_BPS
            else:
                holding = PortfolioHolding(
                    portfolio_id=portfolio.id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=executed_qty,
                    avg_buy_price=executed_price,
                    position_side="short",
                    leverage=leverage,
                    borrow_rate_bps=SHORT_DEFAULT_BORROW_BPS,
                    last_funding_at=now,
                )
                db.add(holding)

        else:  # short + buy (buy to cover)
            if not holding or holding.quantity < executed_qty:
                available = holding.quantity if holding else 0
                raise ValueError(f"공매도 청산 수량 부족: 보유 {available}주")

            funding_cost = await _apply_short_funding_cost(portfolio, holding, now=now)
            base_price = float(holding.avg_buy_price)
            effective_leverage = max(float(holding.leverage or 1.0), 1.0)
            margin_release = base_price * executed_qty / effective_leverage
            pnl = (base_price - executed_price) * executed_qty
            cash_delta = margin_release + pnl - fee_amount
            portfolio.current_cash += int(round(cash_delta))

            # 과도한 손실 경고 로그
            if pnl < 0 and abs(pnl) > (margin_release * 0.8):
                logger.warning(
                    "short position near liquidation user_portfolio=%s stock=%s pnl=%.2f margin=%.2f funding=%.2f",
                    portfolio.id,
                    stock_code,
                    pnl,
                    margin_release,
                    funding_cost,
                )

            holding.quantity -= executed_qty
            holding.updated_at = now
            holding.last_funding_at = now
            if holding.quantity == 0:
                await db.delete(holding)

    remaining_quantity = max(0, quantity - executed_qty)

    trade = SimulationTrade(
        portfolio_id=portfolio.id,
        trade_type=trade_type,
        stock_code=stock_code,
        stock_name=stock_name,
        quantity=quantity,
        filled_quantity=executed_qty,
        price=executed_price,
        requested_price=requested_price,
        executed_price=executed_price,
        slippage_bps=slippage_bps,
        fee_amount=fee_amount,
        order_kind=order_kind,
        order_status=order_status,
        position_side=position_side,
        leverage=leverage,
        total_amount=trade_notional,
        trade_reason=trade_reason,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    return TradeExecutionResult(
        trade=trade,
        executed_quantity=executed_qty,
        remaining_quantity=remaining_quantity,
        requested_price=requested_price,
        executed_price=executed_price,
        slippage_bps=slippage_bps,
        fee_amount=fee_amount,
        order_kind=order_kind,
        order_status=order_status,
        position_side=position_side,
        leverage=leverage,
    )


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
        cp = price_map.get(h.stock_code) or int(h.avg_buy_price)
        total_holdings_value += cp * h.quantity

    total_value = portfolio.current_cash + total_holdings_value
    # 누적 보상액 차감하여 순수 투자 수익만 평가
    rewards = portfolio.total_rewards_received or 0
    profit = total_value - portfolio.initial_cash - rewards

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
