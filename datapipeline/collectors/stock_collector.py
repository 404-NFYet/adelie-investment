"""pykrx 기반 주식 데이터 수집기.

급등/급락 종목, 거래량 상위 종목, 시장 지수 요약, 종목별 히스토리를 제공한다.
"""

from datetime import datetime, timedelta

from pykrx import stock as pykrx_stock


def get_top_movers(date_str: str, top_n: int = 10) -> dict:
    """급등/급락 종목 조회.

    Args:
        date_str: 날짜 (YYYYMMDD)
        top_n: 상위 N개

    Returns:
        {"date": str, "gainers": [...], "losers": [...]}
    """
    df = pykrx_stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
    if df is None or df.empty:
        return {"date": date_str, "gainers": [], "losers": []}

    # 거래량 0인 종목 제외
    df = df[df["거래량"] > 0]

    # 등락률 기준 정렬
    sorted_up = df.sort_values("등락률", ascending=False).head(top_n)
    sorted_down = df.sort_values("등락률", ascending=True).head(top_n)

    def _row_to_dict(ticker, row):
        try:
            name = pykrx_stock.get_market_ticker_name(ticker)
        except Exception:
            name = ticker
        return {
            "ticker": ticker,
            "name": name,
            "등락률": round(float(row["등락률"]), 2),
            "거래량": int(row["거래량"]),
            "종가": int(row["종가"]),
        }

    gainers = [_row_to_dict(t, r) for t, r in sorted_up.iterrows()]
    losers = [_row_to_dict(t, r) for t, r in sorted_down.iterrows()]

    return {"date": date_str, "gainers": gainers, "losers": losers}


def get_high_volume_stocks(date_str: str, top_n: int = 10) -> dict:
    """거래량 상위 종목 조회.

    Args:
        date_str: 날짜 (YYYYMMDD)
        top_n: 상위 N개

    Returns:
        {"date": str, "high_volume": [...]}
    """
    df = pykrx_stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
    if df is None or df.empty:
        return {"date": date_str, "high_volume": []}

    df = df[df["거래량"] > 0]
    sorted_vol = df.sort_values("거래량", ascending=False).head(top_n)

    results = []
    for ticker, row in sorted_vol.iterrows():
        try:
            name = pykrx_stock.get_market_ticker_name(ticker)
        except Exception:
            name = ticker
        results.append({
            "ticker": ticker,
            "name": name,
            "거래량": int(row["거래량"]),
            "등락률": round(float(row["등락률"]), 2),
            "종가": int(row["종가"]),
        })

    return {"date": date_str, "high_volume": results}


def get_market_summary(date_str: str) -> dict:
    """KOSPI/KOSDAQ 지수 요약.

    Args:
        date_str: 날짜 (YYYYMMDD)

    Returns:
        {"date": str, "kospi": {open,high,low,close,volume}, "kosdaq": {...}}
    """
    result: dict = {"date": date_str, "kospi": None, "kosdaq": None}

    for index_code, key in [("1001", "kospi"), ("2001", "kosdaq")]:
        try:
            df = pykrx_stock.get_index_ohlcv(date_str, date_str, index_code)
            if df is not None and not df.empty:
                row = df.iloc[0]
                result[key] = {
                    "open": float(row["시가"]),
                    "high": float(row["고가"]),
                    "low": float(row["저가"]),
                    "close": float(row["종가"]),
                    "volume": int(row["거래량"]),
                }
        except Exception:
            pass

    return result


def get_stock_history(code: str, days: int = 10) -> dict:
    """종목별 기간 OHLCV 조회.

    Args:
        code: 종목 코드 (6자리)
        days: 조회 일수

    Returns:
        {"name": str, "history": [{date, close, change_pct, open, high, low, volume}, ...]}
    """
    end = datetime.now()
    start = end - timedelta(days=days * 2)  # 영업일 고려 여유분
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    df = pykrx_stock.get_market_ohlcv_by_date(start_str, end_str, code)
    if df is None or df.empty:
        return {"name": code, "history": []}

    try:
        name = pykrx_stock.get_market_ticker_name(code)
    except Exception:
        name = code

    # 최근 N일만
    df = df.tail(days)

    history = []
    for date_idx, row in df.iterrows():
        history.append({
            "date": date_idx.strftime("%Y-%m-%d"),
            "close": int(row["종가"]),
            "change_pct": round(float(row["등락률"]), 2),
            "open": int(row["시가"]),
            "high": int(row["고가"]),
            "low": int(row["저가"]),
            "volume": int(row["거래량"]),
        })

    return {"name": name, "history": history}
