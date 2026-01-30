"""
pykrx를 사용한 주식 데이터 수집 모듈
- 급등/급락 종목 수집
- 거래량 상위 종목 수집
"""

import logging
from datetime import datetime
from typing import Optional

from pykrx import stock

logger = logging.getLogger(__name__)


def get_top_movers(date: str, top_n: int = 10) -> dict:
    """
    급등/급락 종목 수집
    
    Args:
        date: 조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD)
        top_n: 상위 N개 종목
        
    Returns:
        dict: {"gainers": [...], "losers": [...]}
    """
    # 날짜 형식 정규화
    date_str = date.replace("-", "")
    
    try:
        # 전 종목 등락률 조회
        df = stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
        
        if df.empty:
            logger.warning(f"No data for date: {date_str}")
            return {"gainers": [], "losers": [], "date": date_str}
        
        # 등락률 기준 정렬
        df = df.reset_index()
        df = df.rename(columns={"티커": "ticker"})
        
        # 급등 종목 (상위 N개)
        gainers = df.nlargest(top_n, "등락률")[
            ["ticker", "시가", "고가", "저가", "종가", "거래량", "등락률"]
        ].to_dict("records")
        
        # 급락 종목 (하위 N개)
        losers = df.nsmallest(top_n, "등락률")[
            ["ticker", "시가", "고가", "저가", "종가", "거래량", "등락률"]
        ].to_dict("records")
        
        # 종목명 추가
        for item in gainers + losers:
            try:
                item["name"] = stock.get_market_ticker_name(item["ticker"])
            except Exception:
                item["name"] = "Unknown"
        
        logger.info(f"Collected {len(gainers)} gainers and {len(losers)} losers for {date_str}")
        
        return {
            "date": date_str,
            "gainers": gainers,
            "losers": losers
        }
        
    except Exception as e:
        logger.error(f"Failed to get top movers: {e}")
        raise


def get_high_volume_stocks(date: str, top_n: int = 10) -> dict:
    """
    거래량 상위 종목 수집
    
    Args:
        date: 조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD)
        top_n: 상위 N개 종목
        
    Returns:
        dict: {"high_volume": [...]}
    """
    date_str = date.replace("-", "")
    
    try:
        # 전 종목 OHLCV 조회
        df = stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
        
        if df.empty:
            logger.warning(f"No data for date: {date_str}")
            return {"high_volume": [], "date": date_str}
        
        df = df.reset_index()
        df = df.rename(columns={"티커": "ticker"})
        
        # 거래량 상위 종목
        high_volume = df.nlargest(top_n, "거래량")[
            ["ticker", "시가", "고가", "저가", "종가", "거래량", "등락률"]
        ].to_dict("records")
        
        # 종목명 추가
        for item in high_volume:
            try:
                item["name"] = stock.get_market_ticker_name(item["ticker"])
            except Exception:
                item["name"] = "Unknown"
        
        logger.info(f"Collected {len(high_volume)} high volume stocks for {date_str}")
        
        return {
            "date": date_str,
            "high_volume": high_volume
        }
        
    except Exception as e:
        logger.error(f"Failed to get high volume stocks: {e}")
        raise


def get_market_summary(date: str) -> dict:
    """
    시장 전체 요약 정보 수집
    
    Args:
        date: 조회 날짜 (YYYYMMDD 또는 YYYY-MM-DD)
        
    Returns:
        dict: 시장 요약 정보
    """
    date_str = date.replace("-", "")
    
    try:
        # KOSPI/KOSDAQ 지수 조회
        kospi = stock.get_index_ohlcv_by_date(date_str, date_str, "1001")  # KOSPI
        kosdaq = stock.get_index_ohlcv_by_date(date_str, date_str, "2001")  # KOSDAQ
        
        summary = {
            "date": date_str,
            "kospi": None,
            "kosdaq": None
        }
        
        if not kospi.empty:
            row = kospi.iloc[0]
            summary["kospi"] = {
                "open": float(row["시가"]),
                "high": float(row["고가"]),
                "low": float(row["저가"]),
                "close": float(row["종가"]),
                "volume": int(row["거래량"])
            }
        
        if not kosdaq.empty:
            row = kosdaq.iloc[0]
            summary["kosdaq"] = {
                "open": float(row["시가"]),
                "high": float(row["고가"]),
                "low": float(row["저가"]),
                "close": float(row["종가"]),
                "volume": int(row["거래량"])
            }
        
        logger.info(f"Collected market summary for {date_str}")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get market summary: {e}")
        raise


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    today = datetime.now().strftime("%Y%m%d")
    
    print("=== Top Movers ===")
    movers = get_top_movers(today, top_n=5)
    print(f"Gainers: {len(movers['gainers'])}")
    print(f"Losers: {len(movers['losers'])}")
    
    print("\n=== High Volume ===")
    volume = get_high_volume_stocks(today, top_n=5)
    print(f"High volume stocks: {len(volume['high_volume'])}")
    
    print("\n=== Market Summary ===")
    summary = get_market_summary(today)
    print(f"KOSPI: {summary['kospi']}")
    print(f"KOSDAQ: {summary['kosdaq']}")
