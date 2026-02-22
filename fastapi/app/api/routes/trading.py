"""자유 매매 API - 종목 검색, 시세 조회, 주문, 관심종목."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.services.kis_service import get_kis_service
from app.services.stock_price_service import get_current_price

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trading", tags=["trading"])


class OrderRequest(BaseModel):
    stock_code: str
    stock_name: str
    order_type: str = Field(..., description="buy or sell")
    quantity: int = Field(..., ge=1)
    order_kind: str = Field(default="market", description="market or limit")
    target_price: Optional[int] = None
    position_side: str = Field(default="long", description="long or short")
    leverage: float = Field(default=1.0, ge=1.0, le=2.0)


class WatchlistAdd(BaseModel):
    stock_code: str
    stock_name: str


@router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """종목 검색."""
    kis = get_kis_service()
    results = await kis.search_stocks(q)
    return {"results": results, "count": len(results)}


@router.get("/stocks/{stock_code}")
async def get_stock_detail(stock_code: str):
    """종목 상세 시세 조회."""
    kis = get_kis_service()
    result = None
    if kis.is_configured:
        result = await kis.get_current_price(stock_code)
    if not result:
        result = await get_current_price(stock_code)
    if not result:
        raise HTTPException(status_code=404, detail="종목 정보를 찾을 수 없습니다")
    return result


@router.get("/ranking")
async def get_ranking(type: str = Query(default="volume")):
    """종목 랭킹."""
    kis = get_kis_service()
    results = await kis.get_ranking(type)
    return {"ranking": results, "type": type}


@router.get("/market-status")
async def get_market_status():
    """오늘 한국 주식시장 개장 여부."""
    from app.services.market_calendar import is_kr_market_open_today
    is_open = await is_kr_market_open_today()
    return {"is_trading_day": is_open}


@router.post("/order")
async def execute_order(
    order: OrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """자유 매매 주문. JWT 인증 필수."""
    user_id = current_user["id"]

    price_data = await get_current_price(order.stock_code)
    if not price_data:
        raise HTTPException(status_code=404, detail="가격 조회 불가")

    try:
        from app.services.portfolio_service import get_or_create_portfolio, execute_trade

        portfolio = await get_or_create_portfolio(db, user_id)
        execution = await execute_trade(
            db=db,
            portfolio=portfolio,
            stock_code=order.stock_code,
            stock_name=order.stock_name,
            trade_type=order.order_type,
            quantity=order.quantity,
            trade_reason="자유매매",
            order_kind=order.order_kind,
            target_price=order.target_price,
            position_side=order.position_side,
            leverage=order.leverage,
        )
        await db.refresh(portfolio)

        trade = execution.trade
        response_payload = {
            "id": trade.id,
            "trade_type": trade.trade_type,
            "stock_code": trade.stock_code,
            "stock_name": trade.stock_name,
            "quantity": trade.quantity,
            "filled_quantity": int(trade.filled_quantity or 0),
            "price": float(trade.price),
            "requested_price": float(trade.requested_price) if trade.requested_price is not None else None,
            "executed_price": float(trade.executed_price) if trade.executed_price is not None else None,
            "slippage_bps": float(trade.slippage_bps) if trade.slippage_bps is not None else None,
            "fee_amount": float(trade.fee_amount) if trade.fee_amount is not None else None,
            "order_kind": trade.order_kind,
            "order_status": trade.order_status,
            "position_side": trade.position_side,
            "leverage": float(trade.leverage or 1.0),
            "remaining_quantity": execution.remaining_quantity,
            "total_amount": float(trade.total_amount),
            "trade_reason": trade.trade_reason,
            "traded_at": trade.traded_at.isoformat() if trade.traded_at else None,
            "remaining_cash": int(portfolio.current_cash),
        }

        # 지정가 미체결/부분체결은 limit_orders에 함께 적재해 후속 체결 경로를 유지
        if order.order_kind == "limit" and trade.order_status in {"pending", "partial"}:
            await db.execute(
                text(
                    """
                    INSERT INTO limit_orders (
                        user_id, stock_code, stock_name, order_type, quantity, target_price, status
                    )
                    VALUES (:uid, :sc, :sn, :ot, :qty, :tp, :st)
                    """
                ),
                {
                    "uid": user_id,
                    "sc": order.stock_code,
                    "sn": order.stock_name,
                    "ot": order.order_type,
                    "qty": execution.remaining_quantity if trade.order_status == "partial" else order.quantity,
                    "tp": int(order.target_price or trade.requested_price or 0),
                    "st": "pending",
                },
            )
            await db.commit()

        return response_payload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("매매 실행 실패: %s", e)
        raise HTTPException(status_code=500, detail=f"매매 실행 실패: {str(e)}") from e


@router.get("/orders")
async def get_pending_orders(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """지정가 주문 목록. JWT 인증 필수."""
    user_id = current_user["id"]
    try:
        result = await db.execute(text(
            "SELECT * FROM limit_orders WHERE user_id = :uid AND status = :s ORDER BY created_at DESC"
        ), {"uid": user_id, "s": status})
        return {"orders": [dict(r._mapping) for r in result.fetchall()]}
    except Exception:
        return {"orders": []}


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """지정가 주문 취소. JWT 인증 필수 (본인 주문만 취소 가능)."""
    user_id = current_user["id"]
    await db.execute(text(
        "UPDATE limit_orders SET status='cancelled', cancelled_at=NOW() "
        "WHERE id=:id AND user_id=:uid AND status='pending'"
    ), {"id": order_id, "uid": user_id})
    await db.commit()
    return {"status": "cancelled"}


@router.get("/watchlist")
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """관심종목 목록. JWT 인증 필수."""
    user_id = current_user["id"]
    try:
        result = await db.execute(text(
            "SELECT * FROM watchlists WHERE user_id = :uid ORDER BY added_at DESC"
        ), {"uid": user_id})
        return {"watchlist": [dict(r._mapping) for r in result.fetchall()]}
    except Exception:
        return {"watchlist": []}


@router.post("/watchlist")
async def add_to_watchlist(
    item: WatchlistAdd,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """관심종목 추가. JWT 인증 필수."""
    user_id = current_user["id"]
    await db.execute(text(
        "INSERT INTO watchlists (user_id, stock_code, stock_name) VALUES (:uid, :sc, :sn) "
        "ON CONFLICT (user_id, stock_code) DO NOTHING"
    ), {"uid": user_id, "sc": item.stock_code, "sn": item.stock_name})
    await db.commit()
    return {"status": "success"}


@router.delete("/watchlist/{stock_code}")
async def remove_from_watchlist(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """관심종목 삭제. JWT 인증 필수."""
    user_id = current_user["id"]
    await db.execute(text(
        "DELETE FROM watchlists WHERE user_id = :uid AND stock_code = :sc"
    ), {"uid": user_id, "sc": stock_code})
    await db.commit()
    return {"status": "removed"}
