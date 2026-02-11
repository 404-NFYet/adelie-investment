"""pykrx 기반 재무 지표 수집기.

PER, PBR, EPS, DIV 등 기본 재무 지표를 텍스트로 포맷팅한다.
"""

from datetime import datetime, timedelta

from pykrx import stock as pykrx_stock


def format_fundamentals_for_llm(ticker: str) -> str:
    """종목 재무 지표를 LLM 컨텍스트용 텍스트로 반환.

    Args:
        ticker: 종목 코드 (6자리)

    Returns:
        재무 지표 텍스트 (PER, PBR, EPS, 배당수익률)
    """
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")

    # 최근 영업일 탐색
    df = None
    for days_back in range(7):
        try_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")
        try:
            result = pykrx_stock.get_market_fundamental_by_ticker(try_date, market="ALL")
            if result is not None and not result.empty and ticker in result.index:
                df = result
                date_str = try_date
                break
        except Exception:
            continue

    if df is None or ticker not in df.index:
        return f"{ticker}: 재무 지표를 찾을 수 없습니다."

    row = df.loc[ticker]
    try:
        name = pykrx_stock.get_market_ticker_name(ticker)
    except Exception:
        name = ticker

    per = row.get("PER", 0)
    pbr = row.get("PBR", 0)
    eps = row.get("EPS", 0)
    div_yield = row.get("DIV", 0)

    lines = [
        f"[{name}({ticker}) 재무 지표 ({date_str})]",
        f"  PER: {per:.2f}배" if per else "  PER: N/A",
        f"  PBR: {pbr:.2f}배" if pbr else "  PBR: N/A",
        f"  EPS: {eps:,.0f}원" if eps else "  EPS: N/A",
        f"  배당수익률: {div_yield:.2f}%" if div_yield else "  배당수익률: N/A",
    ]

    return "\n".join(lines)
