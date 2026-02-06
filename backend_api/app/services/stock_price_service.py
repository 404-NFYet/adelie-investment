"""Real-time stock price service using pykrx + Redis cache."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from pykrx import stock

from app.services.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)

TTL_STOCK_PRICE = 60  # 1분 캐시 (장중 실시간성 확보)


async def get_current_price(stock_code: str) -> Optional[dict]:
    """단일 종목의 현재가(최신 종가)를 조회한다.

    Redis 캐시(60초 TTL)를 우선 확인하고, 없으면 pykrx로 조회한다.
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

    # pykrx 조회 (오늘 → 최대 5일 전까지 fallback)
    try:
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

            result = {
                "stock_code": stock_code,
                "stock_name": name or stock_code,
                "current_price": int(row.get("종가", 0)),
                "change_rate": round(float(row.get("등락률", 0)), 2),
                "volume": int(row.get("거래량", 0)),
                "timestamp": try_date_str,
            }

            # 캐시 저장
            if cache.client:
                try:
                    await cache.client.setex(cache_key, TTL_STOCK_PRICE, json.dumps(result))
                except Exception as e:
                    logger.warning(f"Redis cache write error: {e}")

            return result

    except Exception as e:
        logger.error(f"Failed to get price for {stock_code}: {e}")

    return None


async def get_batch_prices(stock_codes: list[str]) -> list[dict]:
    """복수 종목의 현재가를 일괄 조회한다."""
    results = []
    for code in stock_codes:
        price = await get_current_price(code)
        if price:
            results.append(price)
    return results
