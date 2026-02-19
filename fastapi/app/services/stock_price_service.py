"""Real-time stock price service using pykrx + Redis cache."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from pykrx import stock

from app.services.kis_service import get_kis_service
from app.services.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)

TTL_STOCK_PRICE = 60  # 1분 캐시 (장중 실시간성 확보)
PYKRX_TIMEOUT = 5.0   # pykrx 동기 호출 타임아웃 (초)


def _fetch_price_sync(stock_code: str) -> Optional[dict]:
    """동기 pykrx 호출 (스레드풀에서 실행)."""
    today = datetime.now()
    for days_back in range(5):
        try_date = today - timedelta(days=days_back)
        try_date_str = try_date.strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(try_date_str, try_date_str, stock_code)
        if df.empty:
            continue

        # 컬럼명 정규화 (pykrx 버전에 따라 영문/한글)
        eng_to_kor = {
            "Open": "시가", "High": "고가", "Low": "저가",
            "Close": "종가", "Volume": "거래량", "Change": "등락률",
        }
        df = df.rename(columns={k: v for k, v in eng_to_kor.items() if k in df.columns})

        row = df.iloc[0]
        name = stock.get_market_ticker_name(stock_code)

        return {
            "stock_code": stock_code,
            "stock_name": name or stock_code,
            "current_price": int(row.get("종가", 0)),
            "change_rate": round(float(row.get("등락률", 0)), 2),
            "volume": int(row.get("거래량", 0)),
            "timestamp": try_date_str,
            "source": "pykrx",
        }

    return None


async def _fetch_price_from_kis(stock_code: str) -> Optional[dict]:
    """KIS 시세 조회를 표준 응답 포맷으로 정규화."""
    try:
        kis = get_kis_service()
        if not kis.is_configured:
            return None

        result = await kis.get_current_price(stock_code)
        if not result:
            return None

        return {
            "stock_code": result.get("stock_code", stock_code),
            "stock_name": result.get("stock_name", stock_code),
            "current_price": int(result.get("current_price", 0)),
            "change_rate": round(float(result.get("change_rate", 0)), 2),
            "volume": int(result.get("volume", 0)),
            "timestamp": str(result.get("timestamp") or datetime.now().strftime("%Y%m%d%H%M%S")),
            "source": "kis",
        }
    except Exception as e:
        logger.warning(f"KIS price lookup failed for {stock_code}: {e}")
        return None


async def get_current_price(stock_code: str) -> Optional[dict]:
    """단일 종목의 현재가(최신 종가)를 조회한다.

    Redis 캐시(60초 TTL)를 우선 확인하고, 없으면 KIS 우선/pykrx 폴백으로 조회한다.
    pykrx는 동기 HTTP 호출이므로 asyncio.to_thread로 스레드풀에서 실행한다.
    """
    cache = await get_redis_cache()
    cache_key = f"stock_price:{stock_code}"

    # 캐시 조회
    if cache.client:
        try:
            cached = await cache.client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    # 1) KIS 조회 우선
    result = await _fetch_price_from_kis(stock_code)

    # 2) pykrx 폴백 (스레드풀 + 타임아웃)
    if not result:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_fetch_price_sync, stock_code),
                timeout=PYKRX_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Price lookup timeout for {stock_code}")
        except Exception as e:
            logger.error(f"Failed to get price for {stock_code}: {e}")

    if result:
        if cache.client:
            try:
                await cache.client.setex(cache_key, TTL_STOCK_PRICE, json.dumps(result))
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
        return result

    return None


async def get_batch_prices(stock_codes: list[str]) -> list[dict]:
    """복수 종목의 현재가를 일괄 조회한다."""
    tasks = [get_current_price(code) for code in stock_codes]
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)
    results = []
    for r in results_raw:
        if isinstance(r, dict):
            results.append(r)
    return results
