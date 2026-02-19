"""포트폴리오 및 모의투자 API 라우트."""

import logging
from calendar import monthrange
from datetime import datetime, timedelta
from time import perf_counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.core.redis_keys import key_portfolio_summary, TTL_MEDIUM
from app.services.redis_cache import get_redis_cache
from app.models.portfolio import SimulationTrade
from app.models.reward import BriefingReward, DwellReward
from app.schemas.portfolio import (
    PortfolioResponse,
    PortfolioSummary,
    RefreshPortfolioRequest,
    RefreshPortfolioResponse,
    RefreshInvalidatedInfo,
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
    LeaderboardEntry,
    LeaderboardResponse,
)
from app.services.portfolio_service import (
    get_or_create_portfolio,
    execute_trade,
    complete_briefing_reward,
    check_and_apply_multiplier,
)
from app.services.stock_price_service import get_current_price, get_batch_prices
from app.api.routes.notification import create_notification
from app.models.user import User
from app.models.portfolio import UserPortfolio

logger = logging.getLogger("narrative_api.portfolio")

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


async def invalidate_portfolio_summary_cache(user_id: int) -> None:
    """포트폴리오 요약 캐시를 즉시 무효화한다."""
    try:
        cache = await get_redis_cache()
        await cache.delete(key_portfolio_summary(user_id))
    except Exception:
        # 캐시 미사용 환경에서도 API 동작은 유지
        pass


async def invalidate_user_stock_price_caches(user_id: int, db: AsyncSession) -> RefreshInvalidatedInfo:
    """사용자 보유 종목의 가격 캐시와 summary 캐시를 무효화한다."""
    portfolio = await get_or_create_portfolio(db, user_id)
    stock_codes = sorted({h.stock_code for h in portfolio.holdings if h.stock_code})
    stock_price_deleted = 0
    kis_price_deleted = 0

    try:
        cache = await get_redis_cache()
        if cache.client:
            if stock_codes:
                stock_keys = [f"stock_price:{code}" for code in stock_codes]
                kis_keys = [f"kis:price:{code}" for code in stock_codes]
                stock_price_deleted = await cache.client.delete(*stock_keys)
                kis_price_deleted = await cache.client.delete(*kis_keys)
            await cache.client.delete(key_portfolio_summary(user_id))
        else:
            await invalidate_portfolio_summary_cache(user_id)
    except Exception:
        # 캐시 장애 시에도 포트폴리오 조회는 계속 진행
        await invalidate_portfolio_summary_cache(user_id)

    return RefreshInvalidatedInfo(
        summary=True,
        stock_price_keys=stock_price_deleted,
        kis_price_keys=kis_price_deleted,
    )


async def _load_portfolio_price_map(
    db: AsyncSession,
    user_id: int,
) -> tuple[UserPortfolio, dict[str, int]]:
    """포트폴리오와 보유 종목 가격 맵을 함께 조회한다."""
    portfolio = await get_or_create_portfolio(db, user_id)
    codes = [h.stock_code for h in portfolio.holdings]
    batch_results = await get_batch_prices(codes) if codes else []
    price_map = {p["stock_code"]: p["current_price"] for p in batch_results}
    return portfolio, price_map


def _build_portfolio_response(portfolio: UserPortfolio, price_map: dict[str, int]) -> PortfolioResponse:
    """포트폴리오 응답 모델을 생성한다."""
    holdings_response = []
    total_holdings_value = 0.0

    for h in portfolio.holdings:
        current_price = price_map.get(h.stock_code) or int(h.avg_buy_price)
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
    rewards = portfolio.total_rewards_received or 0
    total_pl = total_value - portfolio.initial_cash - rewards
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
        total_rewards_received=rewards,
    )


def _build_portfolio_summary(portfolio: UserPortfolio, price_map: dict[str, int]) -> PortfolioSummary:
    """포트폴리오 summary 응답 모델을 생성한다."""
    total_holdings = 0
    for h in portfolio.holdings:
        cp = price_map.get(h.stock_code) or int(h.avg_buy_price)
        total_holdings += cp * h.quantity

    total_value = portfolio.current_cash + total_holdings
    rewards = portfolio.total_rewards_received or 0
    total_pl = total_value - portfolio.initial_cash - rewards
    total_pl_pct = (total_pl / portfolio.initial_cash * 100) if portfolio.initial_cash > 0 else 0

    return PortfolioSummary(
        total_value=int(total_value),
        total_profit_loss=int(total_pl),
        total_profit_loss_pct=round(total_pl_pct, 2),
        total_rewards_received=rewards,
    )


# ──────────────────── Leaderboard ────────────────────


@router.get("/leaderboard/ranking", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """수익률 리더보드 조회. 보상 제외 수익률 기준, 공동 등수, 페이지네이션 지원."""
    current_user_id = current_user["id"] if current_user else 0

    # 모든 포트폴리오 조회 (holdings eager loading)
    stmt = (
        select(UserPortfolio, User.username)
        .join(User, User.id == UserPortfolio.user_id)
        .options(selectinload(UserPortfolio.holdings))
        .order_by(UserPortfolio.user_id)
    )
    result = await db.execute(stmt)
    rows = result.unique().all()

    # 전체 종목 코드를 모아 배치 조회 (N+1 방지)
    all_codes = set()
    for portfolio, _ in rows:
        for h in portfolio.holdings:
            all_codes.add(h.stock_code)
    batch_results = await get_batch_prices(list(all_codes))
    price_map = {p["stock_code"]: p["current_price"] for p in batch_results}

    entries = []
    for portfolio, username in rows:
        total_holdings = 0.0
        for h in portfolio.holdings:
            cp = price_map.get(h.stock_code)
            total_holdings += (cp if cp else float(h.avg_buy_price)) * h.quantity

        total_value = portfolio.current_cash + total_holdings
        # 수익률 계산: 누적 보상액 제외
        rewards = getattr(portfolio, "total_rewards_received", 0) or 0
        profit_loss = total_value - portfolio.initial_cash - rewards
        profit_loss_pct = (profit_loss / portfolio.initial_cash * 100) if portfolio.initial_cash > 0 else 0

        entries.append({
            "user_id": portfolio.user_id,
            "username": username,
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_loss_pct": round(profit_loss_pct, 2),
        })

    # user_id 중복 제거 (UNIQUE 제약 이전 데이터 방어)
    seen_users = set()
    unique_entries = []
    for e in entries:
        if e["user_id"] not in seen_users:
            seen_users.add(e["user_id"])
            unique_entries.append(e)
    entries = unique_entries

    # 수익률 내림차순 정렬
    entries.sort(key=lambda e: e["profit_loss_pct"], reverse=True)

    # 순차 등수 부여 (1,2,3... — 공동 등수 없음)
    all_ranked = []
    my_entry = None
    my_rank = None

    for i, e in enumerate(entries):
        rank = i + 1
        is_me = e["user_id"] == current_user_id
        entry = LeaderboardEntry(
            rank=rank,
            user_id=e["user_id"],
            username=e["username"],
            total_value=e["total_value"] if is_me else 0.0,  # 타인 총자산 비공개
            profit_loss=e["profit_loss"] if is_me else 0.0,
            profit_loss_pct=e["profit_loss_pct"],
            is_me=is_me,
        )
        if is_me:
            my_entry = entry
            my_rank = rank
        all_ranked.append(entry)

    total_users = len(all_ranked)
    page_rankings = all_ranked[offset:offset + limit]
    has_more = (offset + limit) < total_users

    return LeaderboardResponse(
        my_rank=my_rank,
        my_entry=my_entry,
        rankings=page_rankings,
        total_users=total_users,
        offset=offset,
        has_more=has_more,
    )


# ──────────────────── Portfolio ────────────────────


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """포트폴리오 전체 조회 (실시간 평가액 포함). JWT 인증 필수."""
    user_id = current_user["id"]
    portfolio, price_map = await _load_portfolio_price_map(db, user_id)
    return _build_portfolio_response(portfolio, price_map)


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """경량 포트폴리오 요약 (BottomNav 뱃지용). JWT 인증 필수."""
    user_id = current_user["id"]

    # Redis 캐시 체크 (TTL 2분)
    import json as _json
    cache_key = key_portfolio_summary(user_id)
    try:
        cache = await get_redis_cache()
        cached = await cache.get(cache_key)
        if cached:
            return PortfolioSummary(**_json.loads(cached))
    except Exception:
        pass

    portfolio, price_map = await _load_portfolio_price_map(db, user_id)
    summary = _build_portfolio_summary(portfolio, price_map)

    # 캐시 저장 (2분)
    try:
        await cache.set(cache_key, _json.dumps(summary.model_dump()), TTL_MEDIUM)
    except Exception:
        pass

    return summary


@router.post("/refresh", response_model=RefreshPortfolioResponse)
async def refresh_portfolio(
    req: RefreshPortfolioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """포트폴리오 캐시 무효화 + 최신 데이터 즉시 재조회."""
    user_id = current_user["id"]
    started_at = perf_counter()

    if req.invalidate_scope != "summary_and_holdings":
        raise HTTPException(status_code=400, detail="지원하지 않는 invalidate_scope")

    invalidated = await invalidate_user_stock_price_caches(user_id, db)
    portfolio, price_map = await _load_portfolio_price_map(db, user_id)
    portfolio_response = _build_portfolio_response(portfolio, price_map)
    summary = _build_portfolio_summary(portfolio, price_map)

    # 최신 summary를 다시 캐싱해 이후 조회 지연을 줄인다.
    try:
        import json as _json
        cache = await get_redis_cache()
        await cache.set(key_portfolio_summary(user_id), _json.dumps(summary.model_dump()), TTL_MEDIUM)
    except Exception:
        pass

    duration_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "portfolio_refresh user_id=%s stock_price_keys=%s kis_price_keys=%s duration_ms=%s",
        user_id,
        invalidated.stock_price_keys,
        invalidated.kis_price_keys,
        duration_ms,
    )

    return RefreshPortfolioResponse(
        portfolio=portfolio_response,
        summary=summary,
        invalidated=invalidated,
        source_policy="kis_first_fallback_pykrx",
        refreshed_at=datetime.utcnow(),
    )


# ──────────────────── Trading ────────────────────


@router.post("/trade", response_model=TradeResponse)
async def create_trade(
    req: TradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """매수/매도 실행. JWT 인증 필수."""
    user_id = current_user["id"]
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
    await invalidate_portfolio_summary_cache(user_id)

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


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trade_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """거래 내역 조회. JWT 인증 필수."""
    user_id = current_user["id"]
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


@router.post("/reward", response_model=RewardResponse)
async def claim_briefing_reward(
    req: BriefingCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """브리핑 완료 보상 청구. JWT 인증 필수."""
    user_id = current_user["id"]
    try:
        reward = await complete_briefing_reward(db, user_id, req.case_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # 알림 생성
    await create_notification(
        db, user_id, "reward",
        "브리핑 완료 보상",
        f"+{reward.base_reward:,.0f}원 지급! 7일 후 수익률 보너스 기회",
        data={"case_id": req.case_id, "amount": reward.base_reward},
    )
    await db.commit()
    await invalidate_portfolio_summary_cache(user_id)

    return RewardResponse(
        reward_id=reward.id,
        base_reward=reward.base_reward,
        status=reward.status,
        maturity_at=reward.maturity_at,
        message=f"브리핑 완료! {reward.base_reward:,.0f}원 지급. 7일 후 수익률에 따라 1.5배 보너스!",
    )


@router.get("/rewards", response_model=RewardsListResponse)
async def get_rewards(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """보상 목록 조회 (만기 도래 시 자동 체크). JWT 인증 필수."""
    user_id = current_user["id"]
    stmt = (
        select(BriefingReward)
        .where(BriefingReward.user_id == user_id)
        .order_by(BriefingReward.created_at.desc())
    )
    result = await db.execute(stmt)
    rewards = result.scalars().all()

    items = []
    summary_changed = False
    for r in rewards:
        before_status = r.status
        before_final_reward = r.final_reward
        r = await check_and_apply_multiplier(db, r)
        if r.status != before_status or r.final_reward != before_final_reward:
            summary_changed = True
        items.append(RewardItem(
            reward_id=r.id,
            case_id=r.case_id,
            base_reward=r.base_reward,
            multiplier=r.multiplier,
            final_reward=r.final_reward,
            status=r.status,
            maturity_at=r.maturity_at.isoformat(),
        ))

    if summary_changed:
        await invalidate_portfolio_summary_cache(user_id)

    return RewardsListResponse(rewards=items)


# ──────────────────── Dwell Reward ────────────────────

DWELL_REWARD_AMOUNT = 50_000  # 체류 보상 5만원
DWELL_MIN_SECONDS = 180  # 최소 3분


class DwellRewardRequest(BaseModel):
    page: str
    dwell_seconds: int


@router.post("/dwell-reward")
async def claim_dwell_reward(
    req: DwellRewardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """체류 시간 보상 청구. 3분 이상 학습 시 5만원 지급. 페이지당 1일 1회. JWT 인증 필수."""
    user_id = current_user["id"]
    if req.dwell_seconds < DWELL_MIN_SECONDS:
        raise HTTPException(status_code=400, detail="체류 시간이 부족합니다 (최소 3분)")

    portfolio = await get_or_create_portfolio(db, user_id)

    # 오늘 같은 페이지에서 이미 보상을 받았는지 확인
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = await db.execute(
        select(DwellReward).where(
            and_(
                DwellReward.user_id == user_id,
                DwellReward.page == req.page,
                DwellReward.created_at >= today_start,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="오늘 이미 이 페이지에서 체류 보상을 받았습니다")

    # 보상 지급
    portfolio.current_cash += DWELL_REWARD_AMOUNT
    portfolio.total_rewards_received += DWELL_REWARD_AMOUNT
    reward = DwellReward(
        user_id=user_id,
        portfolio_id=portfolio.id,
        page=req.page,
        dwell_seconds=req.dwell_seconds,
        reward_amount=DWELL_REWARD_AMOUNT,
    )
    db.add(reward)

    # 알림 생성
    await create_notification(
        db, user_id, "dwell",
        "체류 보상",
        f"3분 이상 학습! +{DWELL_REWARD_AMOUNT:,}원 보상",
        data={"page": req.page, "amount": DWELL_REWARD_AMOUNT},
    )
    await db.commit()
    await invalidate_portfolio_summary_cache(user_id)

    return {
        "reward_amount": DWELL_REWARD_AMOUNT,
        "page": req.page,
        "message": f"+{DWELL_REWARD_AMOUNT:,}원 체류 보상 지급!",
    }


# ──────────────────── Stock Chart ────────────────────


@router.get("/stock/chart/{stock_code}")
async def get_stock_chart(
    stock_code: str,
    days: int = Query(20, ge=5, le=366),
    period: Optional[str] = Query(None, regex="^(1w|1m|3m|6m|1y)$"),
):
    """종목 가격 차트 데이터 (pykrx 일봉)."""
    def subtract_months(base_dt: datetime, months: int) -> datetime:
        year = base_dt.year
        month = base_dt.month - months
        while month <= 0:
            month += 12
            year -= 1
        day = min(base_dt.day, monthrange(year, month)[1])
        return base_dt.replace(year=year, month=month, day=day)

    try:
        from pykrx import stock
        now = datetime.now()
        end_date = now.strftime("%Y%m%d")

        if period:
            period_to_start = {
                "1w": now - timedelta(days=7),
                "1m": subtract_months(now, 1),
                "3m": subtract_months(now, 3),
                "6m": subtract_months(now, 6),
                "1y": subtract_months(now, 12),
            }
            start_dt = period_to_start[period]
            start_date = start_dt.strftime("%Y%m%d")
        else:
            lookback_days = max(days + 30, int(days * 1.8))
            start_dt = now - timedelta(days=lookback_days)
            start_date = start_dt.strftime("%Y%m%d")

        df = stock.get_market_ohlcv(start_date, end_date, stock_code)
        if df.empty:
            raise HTTPException(status_code=404, detail="차트 데이터 없음")

        if period:
            range_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            df = df[df.index >= range_start]
        else:
            df = df.tail(days)

        if df.empty:
            raise HTTPException(status_code=404, detail="선택 기간 차트 데이터 없음")

        return {
            "stock_code": stock_code,
            "period": period,
            "period_start": df.index[0].strftime("%Y-%m-%d"),
            "period_end": df.index[-1].strftime("%Y-%m-%d"),
            "dates": [d.strftime("%Y-%m-%d") for d in df.index],
            "opens": df["시가"].tolist(),
            "highs": df["고가"].tolist(),
            "lows": df["저가"].tolist(),
            "closes": df["종가"].tolist(),
            "volumes": df["거래량"].tolist(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"차트 데이터 조회 실패: {e}")
