"""
FinanceDataReader 기반 재무제표/주가 데이터 수집 모듈

주요 기능:
- 종목별 재무제표 수집 (PER, PBR, EPS, ROE 등)
- 종목 OHLCV 시계열 수집 (pykrx 보완)
- DART 공시 정보 연동용 헬퍼
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False
    logger.warning("FinanceDataReader가 설치되지 않았습니다: pip install FinanceDataReader")


def get_stock_fundamentals(ticker: str) -> dict:
    """
    종목 기본 재무 지표 조회 (PER, PBR, EPS, DIV 등).

    Args:
        ticker: 종목 코드 (예: "005930")

    Returns:
        dict: 재무 지표 또는 빈 dict
    """
    if not FDR_AVAILABLE:
        return {"error": "FinanceDataReader 미설치"}

    try:
        # KRX 종목 정보 조회
        krx = fdr.StockListing("KRX")
        row = krx[krx["Code"] == ticker]

        if row.empty:
            return {"ticker": ticker, "found": False}

        info = row.iloc[0].to_dict()
        return {
            "ticker": ticker,
            "found": True,
            "name": info.get("Name", ""),
            "market": info.get("Market", ""),
            "sector": info.get("Sector", ""),
            "industry": info.get("Industry", ""),
            "market_cap": info.get("Marcap", None),
            "per": info.get("PER", None),
            "pbr": info.get("PBR", None),
            "eps": info.get("EPS", None),
            "div": info.get("DIV", None),
            "bps": info.get("BPS", None),
        }
    except Exception as e:
        logger.error("재무 지표 조회 실패 (%s): %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}


def get_stock_ohlcv(ticker: str, days: int = 60) -> list[dict]:
    """
    종목 OHLCV 시계열 수집 (FinanceDataReader 사용).

    Args:
        ticker: 종목 코드
        days: 최근 N 거래일

    Returns:
        list[dict]: OHLCV 기록 리스트
    """
    if not FDR_AVAILABLE:
        return []

    try:
        start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")
        df = fdr.DataReader(ticker, start)

        if df.empty:
            return []

        df = df.tail(days)
        records = []
        for idx, row in df.iterrows():
            records.append({
                "date": idx.strftime("%Y%m%d") if hasattr(idx, "strftime") else str(idx),
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
                "volume": int(row.get("Volume", 0)),
                "change": float(row.get("Change", 0)),
            })

        logger.info("FDR OHLCV 수집 완료: %s (%d일)", ticker, len(records))
        return records
    except Exception as e:
        logger.error("FDR OHLCV 수집 실패 (%s): %s", ticker, e)
        return []


def get_financial_statements(ticker: str) -> dict:
    """
    종목 재무제표 요약 (매출액, 영업이익, 순이익 등) 조회.

    참고: FinanceDataReader의 재무제표 기능은 제한적이므로
    DART OpenAPI 또는 별도 크롤링이 필요할 수 있음.

    Args:
        ticker: 종목 코드

    Returns:
        dict: 재무제표 요약 데이터
    """
    if not FDR_AVAILABLE:
        return {"error": "FinanceDataReader 미설치"}

    try:
        # 기본 지표를 통한 간접 재무 데이터
        fundamentals = get_stock_fundamentals(ticker)
        if not fundamentals.get("found"):
            return fundamentals

        return {
            "ticker": ticker,
            "name": fundamentals.get("name", ""),
            "valuation": {
                "per": fundamentals.get("per"),
                "pbr": fundamentals.get("pbr"),
                "eps": fundamentals.get("eps"),
                "bps": fundamentals.get("bps"),
                "div_yield": fundamentals.get("div"),
            },
            "market_cap": fundamentals.get("market_cap"),
            "sector": fundamentals.get("sector", ""),
        }
    except Exception as e:
        logger.error("재무제표 조회 실패 (%s): %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}


def format_fundamentals_for_llm(ticker: str) -> str:
    """
    AI 튜터/챗봇에서 사용할 수 있도록 재무 지표를 텍스트로 포맷.

    Args:
        ticker: 종목 코드

    Returns:
        str: LLM 컨텍스트용 포맷된 텍스트
    """
    data = get_stock_fundamentals(ticker)

    if not data.get("found"):
        return f"종목 {ticker}: 데이터를 찾을 수 없습니다."

    lines = [f"[{data.get('name', ticker)}({ticker}) 재무 지표]"]

    if data.get("market_cap"):
        cap_billion = data["market_cap"] / 100_000_000
        lines.append(f"시가총액: {cap_billion:,.0f}억 원")
    if data.get("per") is not None:
        lines.append(f"PER: {data['per']:.1f}배")
    if data.get("pbr") is not None:
        lines.append(f"PBR: {data['pbr']:.2f}배")
    if data.get("eps") is not None:
        lines.append(f"EPS: {data['eps']:,.0f}원")
    if data.get("div") is not None:
        lines.append(f"배당수익률: {data['div']:.2f}%")
    if data.get("sector"):
        lines.append(f"섹터: {data['sector']}")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 테스트: 삼성전자
    print("=== 삼성전자 재무 지표 ===")
    print(format_fundamentals_for_llm("005930"))

    print("\n=== 삼성전자 OHLCV (5일) ===")
    ohlcv = get_stock_ohlcv("005930", days=5)
    for r in ohlcv:
        print(f"  {r['date']}: 종가 {r['close']:,.0f}")
