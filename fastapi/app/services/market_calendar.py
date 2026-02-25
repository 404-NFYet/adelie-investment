"""한국 주식시장 영업일 판별 유틸.

pykrx 대신 평일 체크 + KRX 공식 휴장일 목록 기반.
매년 초 KRX_HOLIDAYS 세트를 갱신해야 한다.
"""

import logging
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)

# 2026년 KRX 휴장일 (평일만 포함, 주말은 이미 제외)
# 출처: https://www.calendarlabs.com/krx-market-holidays-2026/
KRX_HOLIDAYS = {
    # 신정
    "20260101",
    # 설날 연휴
    "20260216", "20260217", "20260218",
    # 삼일절 대체공휴일 (3/1 일요일 → 3/2 월요일)
    "20260302",
    # 근로자의 날
    "20260501",
    # 어린이날
    "20260505",
    # 부처님오신날 대체공휴일 (5/24 일요일 → 5/25 월요일)
    "20260525",
    # 광복절 대체공휴일 (8/15 토요일 → 8/17 월요일)
    "20260817",
    # 추석 연휴
    "20260924", "20260925",
    # 개천절 대체공휴일 (10/3 토요일 → 10/5 월요일)
    "20261005",
    # 한글날
    "20261009",
    # 성탄절
    "20261225",
    # 연말 휴장
    "20261231",
}


def is_trading_day(date_str: str | None = None) -> bool:
    """한국 주식시장 영업일 여부를 확인한다.

    Args:
        date_str: "YYYYMMDD" 형식. None이면 오늘(KST).

    Returns:
        평일이고 KRX 휴장일이 아니면 True.
    """
    if date_str is None:
        date_str = datetime.now(KST).strftime("%Y%m%d")

    d = datetime.strptime(date_str, "%Y%m%d").date()

    # 주말 체크
    if d.weekday() >= 5:
        return False

    # KRX 휴장일 체크
    if date_str in KRX_HOLIDAYS:
        logger.info("KRX 휴장일: %s", date_str)
        return False

    return True


async def is_kr_market_open_today() -> bool:
    """오늘이 한국 주식시장 영업일인지 확인한다 (기존 인터페이스 호환)."""
    return is_trading_day()
