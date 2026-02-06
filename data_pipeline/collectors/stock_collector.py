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
        
        # pykrx 버전에 따라 컬럼명이 다를 수 있음 (한글/영문)
        col_map = {}
        if "티커" in df.columns:
            col_map["티커"] = "ticker"
        elif "Ticker" in df.columns:
            col_map["Ticker"] = "ticker"
        # 인덱스가 리셋된 경우 첫 컬럼이 ticker일 수 있음
        if "ticker" not in df.columns and "ticker" not in col_map.values():
            first_col = df.columns[0]
            col_map[first_col] = "ticker"
        
        if col_map:
            df = df.rename(columns=col_map)
        
        # 컬럼명 정규화: 영문 컬럼명을 한글로 통일
        eng_to_kor = {
            "시가": "시가", "고가": "고가", "저가": "저가", "종가": "종가",
            "거래량": "거래량", "등락률": "등락률",
            "Open": "시가", "High": "고가", "Low": "저가", "Close": "종가",
            "Volume": "거래량", "Change": "등락률",
        }
        df = df.rename(columns={k: v for k, v in eng_to_kor.items() if k in df.columns})
        
        # 필수 컬럼 확인
        required_cols = ["등락률", "거래량"]
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"Column '{col}' not found. Available: {list(df.columns)}")
                return {"gainers": [], "losers": [], "date": date_str}
        
        # 선택할 컬럼 (존재하는 것만)
        select_cols = ["ticker"] + [c for c in ["시가", "고가", "저가", "종가", "거래량", "등락률"] if c in df.columns]
        
        # 급등 종목 (상위 N개)
        gainers = df.nlargest(top_n, "등락률")[select_cols].to_dict("records")
        
        # 급락 종목 (하위 N개)
        losers = df.nsmallest(top_n, "등락률")[select_cols].to_dict("records")
        
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
        
        # pykrx 버전에 따라 컬럼명이 다를 수 있음
        col_map = {}
        if "티커" in df.columns:
            col_map["티커"] = "ticker"
        elif "Ticker" in df.columns:
            col_map["Ticker"] = "ticker"
        if "ticker" not in df.columns and "ticker" not in col_map.values():
            first_col = df.columns[0]
            col_map[first_col] = "ticker"
        if col_map:
            df = df.rename(columns=col_map)
        
        # 영문 컬럼명 -> 한글 정규화
        eng_to_kor = {
            "Open": "시가", "High": "고가", "Low": "저가", "Close": "종가",
            "Volume": "거래량", "Change": "등락률",
        }
        df = df.rename(columns={k: v for k, v in eng_to_kor.items() if k in df.columns})
        
        if "거래량" not in df.columns:
            logger.warning(f"Column '거래량' not found. Available: {list(df.columns)}")
            return {"high_volume": [], "date": date_str}
        
        select_cols = ["ticker"] + [c for c in ["시가", "고가", "저가", "종가", "거래량", "등락률"] if c in df.columns]
        
        # 거래량 상위 종목
        high_volume = df.nlargest(top_n, "거래량")[select_cols].to_dict("records")
        
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
        
        def _parse_index_row(row):
            """인덱스 OHLCV 행을 dict로 변환 (한글/영문 컬럼 모두 지원)."""
            def _get(kor, eng):
                if kor in row.index:
                    return row[kor]
                if eng in row.index:
                    return row[eng]
                return None
            
            open_val = _get("시가", "Open")
            high_val = _get("고가", "High")
            low_val = _get("저가", "Low")
            close_val = _get("종가", "Close")
            volume_val = _get("거래량", "Volume")
            
            return {
                "open": float(open_val) if open_val is not None else 0.0,
                "high": float(high_val) if high_val is not None else 0.0,
                "low": float(low_val) if low_val is not None else 0.0,
                "close": float(close_val) if close_val is not None else 0.0,
                "volume": int(volume_val) if volume_val is not None else 0,
            }
        
        if not kospi.empty:
            summary["kospi"] = _parse_index_row(kospi.iloc[0])
        
        if not kosdaq.empty:
            summary["kosdaq"] = _parse_index_row(kosdaq.iloc[0])
        
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
