"""한국 주식시장 영업일 판별 유틸.

pykrx의 get_nearest_business_day_in_a_week 활용:
- 영업일이면 해당 날짜 그대로 반환 → nearest == today
- 휴장일이면 직전 영업일 반환 → nearest != today
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from functools import lru_cache

KST = timezone(timedelta(hours=9))

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def _check_business_day(date_str: str) -> bool:
    """pykrx로 영업일 여부를 확인한다 (동기, 캐싱).

    Args:
        date_str: "YYYYMMDD" 형식 날짜 문자열
    """
    try:
        from pykrx.stock import get_nearest_business_day_in_a_week
        nearest = get_nearest_business_day_in_a_week(date_str)
        return nearest == date_str
    except Exception as e:
        logger.warning("pykrx 영업일 조회 실패 (평일 fallback): %s", e)
        # fallback: 평일이면 영업일로 간주
        d = datetime.strptime(date_str, "%Y%m%d").date()
        return d.weekday() < 5  # 0=월 ~ 4=금


async def is_kr_market_open_today() -> bool:
    """오늘이 한국 주식시장 영업일인지 비동기로 확인한다."""
    today_str = datetime.now(KST).strftime("%Y%m%d")
    # pykrx는 동기 함수 → executor에서 실행
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_business_day, today_str)
