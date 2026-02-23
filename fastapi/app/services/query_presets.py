"""질문 의도 분류 + DB 쿼리 사전 세팅 모듈.

사용자 메시지를 키워드 기반으로 의도 분류한 뒤,
해당 의도에 맞는 DB 쿼리를 실행하여 LLM 컨텍스트에 주입한다.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("narrative_api.query_presets")

KST = timezone(timedelta(hours=9))

# --- 의도 분류 키워드 ---
_INTENT_PATTERNS: dict[str, list[str]] = {
    "stock_analysis": [
        "주가", "차트", "매수", "매도", "전망", "분석", "목표가", "실적",
        "PER", "PBR", "EPS", "배당", "시가총액", "거래량", "수급",
    ],
    "market_overview": [
        "시장", "코스피", "코스닥", "장세", "오늘 시장", "시황", "이슈",
        "브리핑", "뉴스", "테마", "섹터",
    ],
    "glossary": [
        "뜻", "의미", "개념", "용어", "설명해", "알려줘",
        "무슨 뜻", "무엇", "정의",
    ],
    "historical_case": [
        "과거", "역사", "사례", "비슷한", "유사", "반복", "패턴",
        "과거에도", "전례", "역사적",
    ],
    "comparison": [
        "비교", "대비", "차이", "vs", "어떤 게 나아", "어디가",
        "비교분석", "비교해",
    ],
}


def classify_intent(message: str) -> str:
    """키워드 기반 의도 분류. 매칭 점수가 가장 높은 의도를 반환."""
    msg_lower = message.lower()
    scores: dict[str, int] = {}

    for intent, keywords in _INTENT_PATTERNS.items():
        score = sum(1 for kw in keywords if kw.lower() in msg_lower)
        if score > 0:
            scores[intent] = score

    if not scores:
        return "general"

    return max(scores, key=scores.get)


async def fetch_intent_context(
    intent: str,
    message: str,
    db: AsyncSession,
    stock_codes: Optional[list[str]] = None,
) -> str:
    """의도에 따라 적절한 DB 쿼리를 실행하여 추가 컨텍스트 문자열을 반환."""
    try:
        if intent == "market_overview":
            return await _fetch_market_overview(db)
        elif intent == "glossary":
            return await _fetch_glossary_terms(message, db)
        elif intent == "historical_case":
            return await _fetch_historical_cases(message, db)
        elif intent == "stock_analysis" and stock_codes:
            return await _fetch_stock_analysis(stock_codes, db)
        elif intent == "comparison" and stock_codes and len(stock_codes) >= 2:
            return await _fetch_comparison_data(stock_codes, db)
    except Exception as e:
        logger.warning("의도 기반 컨텍스트 조회 실패 (%s): %s", intent, e)

    return ""


async def _fetch_market_overview(db: AsyncSession) -> str:
    """당일 브리핑 요약 조회."""
    today = datetime.now(KST).date()
    result = await db.execute(
        text(
            "SELECT market_summary, top_keywords FROM daily_briefings "
            "WHERE DATE(created_at AT TIME ZONE 'Asia/Seoul') = :today "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"today": today},
    )
    row = result.fetchone()
    if row:
        return f"\n\n[오늘의 시장 브리핑]\n시장 요약: {row[0]}\n주요 키워드: {row[1]}"
    return ""


async def _fetch_glossary_terms(message: str, db: AsyncSession) -> str:
    """메시지에서 용어를 추출하여 glossary DB에서 조회."""
    # 간단한 한글 단어 추출 → glossary 매칭
    words = re.findall(r"[가-힣A-Za-z]{2,}", message)
    if not words:
        return ""

    placeholders = ", ".join(f":w{i}" for i in range(min(len(words), 10)))
    params = {f"w{i}": w for i, w in enumerate(words[:10])}
    result = await db.execute(
        text(
            f"SELECT term, definition FROM glossary "
            f"WHERE term IN ({placeholders}) LIMIT 5"
        ),
        params,
    )
    rows = result.fetchall()
    if rows:
        terms_text = "\n".join(f"- {r[0]}: {r[1]}" for r in rows)
        return f"\n\n[관련 용어 사전]\n{terms_text}"
    return ""


async def _fetch_historical_cases(message: str, db: AsyncSession) -> str:
    """메시지 키워드로 역사적 사례 검색."""
    # 핵심 단어 추출 (2글자 이상 한글)
    keywords = re.findall(r"[가-힣]{2,}", message)
    if not keywords:
        return ""

    # 제목/요약 ILIKE 검색
    conditions = " OR ".join(
        f"title ILIKE :kw{i} OR summary ILIKE :kw{i}" for i in range(min(len(keywords), 5))
    )
    params = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(keywords[:5])}
    result = await db.execute(
        text(
            f"SELECT title, summary FROM historical_cases "
            f"WHERE {conditions} ORDER BY created_at DESC LIMIT 3"
        ),
        params,
    )
    rows = result.fetchall()
    if rows:
        cases_text = "\n".join(f"- {r[0]}: {r[1][:200]}" for r in rows)
        return f"\n\n[관련 역사적 사례]\n{cases_text}"
    return ""


async def _fetch_stock_analysis(stock_codes: list[str], db: AsyncSession) -> str:
    """종목 코드로 최근 30일 시세 조회."""
    code = stock_codes[0]
    thirty_days_ago = (datetime.now(KST) - timedelta(days=30)).date()
    result = await db.execute(
        text(
            "SELECT trade_date, close_price, volume FROM market_daily_history "
            "WHERE stock_code = :code AND trade_date >= :since "
            "ORDER BY trade_date DESC LIMIT 30"
        ),
        {"code": code, "since": thirty_days_ago},
    )
    rows = result.fetchall()
    if rows:
        recent = rows[0]
        oldest = rows[-1]
        price_change = ((recent[1] - oldest[1]) / oldest[1] * 100) if oldest[1] else 0
        avg_vol = sum(r[2] for r in rows) / len(rows) if rows else 0
        return (
            f"\n\n[종목 분석 데이터 ({code})]\n"
            f"최근 종가: {recent[1]:,}원 (30일 변동: {price_change:+.1f}%)\n"
            f"평균 거래량: {int(avg_vol):,}주 (최근 30일)\n"
            f"데이터 기간: {oldest[0]} ~ {recent[0]}"
        )
    return ""


async def _fetch_comparison_data(stock_codes: list[str], db: AsyncSession) -> str:
    """복수 종목 비교 데이터 조회."""
    codes = stock_codes[:4]  # 최대 4종목
    placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
    params = {f"c{i}": c for i, c in enumerate(codes)}
    params["since"] = (datetime.now(KST) - timedelta(days=30)).date()

    result = await db.execute(
        text(
            f"SELECT stock_code, MAX(close_price) as high, MIN(close_price) as low, "
            f"AVG(volume) as avg_vol "
            f"FROM market_daily_history "
            f"WHERE stock_code IN ({placeholders}) AND trade_date >= :since "
            f"GROUP BY stock_code"
        ),
        params,
    )
    rows = result.fetchall()
    if rows:
        comp_text = "\n".join(
            f"- {r[0]}: 고가 {r[1]:,}원 / 저가 {r[2]:,}원 / 평균거래량 {int(r[3]):,}주"
            for r in rows
        )
        return f"\n\n[종목 비교 데이터 (최근 30일)]\n{comp_text}"
    return ""
