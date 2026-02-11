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


@router.post("/order")
async def execute_order(
    order: OrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """자유 매매 주문. JWT 인증 필수."""
    user_id = current_user["id"]

    if order.order_kind == "limit" and order.target_price:
        # 지정가 주문
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS limit_orders (
                id SERIAL PRIMARY KEY, user_id INTEGER,
                stock_code VARCHAR(10), stock_name VARCHAR(100),
                order_type VARCHAR(4), target_price INTEGER,
                quantity INTEGER, status VARCHAR(10) DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                filled_at TIMESTAMPTZ, cancelled_at TIMESTAMPTZ)
        """))
        await db.execute(text(
            "INSERT INTO limit_orders (user_id, stock_code, stock_name, order_type, target_price, quantity) "
            "VALUES (:uid, :sc, :sn, :ot, :tp, :q)"
        ), {"uid": user_id, "sc": order.stock_code, "sn": order.stock_name,
            "ot": order.order_type, "tp": order.target_price, "q": order.quantity})
        await db.commit()
        return {"status": "pending", "message": "지정가 주문 접수"}
    else:
        # 시장가 주문
        price_data = await get_current_price(order.stock_code)
        if not price_data:
            raise HTTPException(status_code=404, detail="가격 조회 불가")

        try:
            from app.services.portfolio_service import get_or_create_portfolio, execute_trade
            portfolio = await get_or_create_portfolio(db, user_id)
            result = await execute_trade(
                db=db,
                portfolio=portfolio,
                stock_code=order.stock_code,
                stock_name=order.stock_name,
                trade_type=order.order_type,
                quantity=order.quantity,
                trade_reason="자유매매",
            )
            return result
        except Exception as e:
            logger.error(f"매매 실행 실패: {e}")
            raise HTTPException(status_code=500, detail=f"매매 실행 실패: {str(e)}")


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
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS watchlists (
                id SERIAL PRIMARY KEY, user_id INTEGER,
                stock_code VARCHAR(10), stock_name VARCHAR(100),
                added_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(user_id, stock_code))
        """))
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
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id SERIAL PRIMARY KEY, user_id INTEGER,
            stock_code VARCHAR(10), stock_name VARCHAR(100),
            added_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(user_id, stock_code))
    """))
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
