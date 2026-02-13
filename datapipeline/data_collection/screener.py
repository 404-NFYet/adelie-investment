"""Attention 기반 스크리닝: 시가총액 top 유니버스에서 6-proxy z-score로 hot 종목 선별.

v3: 4-signal threshold → 6-proxy attention scoring으로 교체.
"""

from __future__ import annotations

import logging

from ..config import (
    ATTENTION_ALL_TARGET_PER_MARKET,
    ATTENTION_BENCHMARK_TOP_N,
    ATTENTION_HISTORICAL_YEARS,
    ATTENTION_NEWS_WORKERS,
    ATTENTION_PERCENTILE_MIN,
    ATTENTION_RECALC_MIN_COUNT,
    ATTENTION_RECALC_RECENCY_DAYS,
    ATTENTION_RECENCY_DAYS,
    ATTENTION_SHOW_PROGRESS,
    ATTENTION_SINGLE_MARKET_TARGET,
    ATTENTION_USE_GOOGLE_NEWS,
)
from .attention.scoring import compute_attention_scores
from .attention.universe import load_universe_top_marketcap

logger = logging.getLogger(__name__)

_LAST_SCREENING_META: dict = {}


def _to_screened_rows(rows: list[dict], market: str, recency_days: int) -> list[dict]:
    """attention score 결과를 screened stock 형태로 변환."""
    screened: list[dict] = []
    for row in rows:
        score_raw = row.get("attention_score")
        pct_raw = row.get("attention_percentile")
        if score_raw is None or pct_raw is None:
            continue

        score = float(score_raw)
        pct = float(pct_raw)
        vol_ratio = row.get("abnormal_volume_ratio")
        screened.append({
            "symbol": str(row.get("symbol", "")),
            "name": str(row.get("name", "")),
            "signal": "attention_hot",
            "return_pct": round(score, 4),
            "volume_ratio": round(float(vol_ratio), 2) if isinstance(vol_ratio, (int, float)) else 0.0,
            "period_days": recency_days,
            "attention_score": round(score, 4),
            "attention_percentile": round(pct, 1),
            "market": market,
            "recency_days": recency_days,
        })
    return screened


def _run_attention_market(market: str, target_count: int) -> tuple[list[dict], dict]:
    """단일 시장 attention scoring 실행."""
    universe = load_universe_top_marketcap(market=market, top_n=ATTENTION_BENCHMARK_TOP_N)
    logger.info("  유니버스 로딩 완료: %s %d종목", market, len(universe))

    rows = compute_attention_scores(
        universe,
        market=market,
        recency_days=ATTENTION_RECENCY_DAYS,
        historical_years=ATTENTION_HISTORICAL_YEARS,
        use_google_news=ATTENTION_USE_GOOGLE_NEWS,
        news_workers=ATTENTION_NEWS_WORKERS,
        show_progress=ATTENTION_SHOW_PROGRESS,
    )

    screened = _to_screened_rows(rows, market, ATTENTION_RECENCY_DAYS)
    filtered = [r for r in screened if r["attention_percentile"] >= ATTENTION_PERCENTILE_MIN]
    filtered.sort(key=lambda r: r["attention_score"], reverse=True)

    # 후보가 너무 적으면 recency 확장 재계산
    recalc_applied = False
    if len(filtered) < ATTENTION_RECALC_MIN_COUNT:
        recalc_applied = True
        logger.info("  후보 부족 (%d < %d), recency %d일로 재계산",
                     len(filtered), ATTENTION_RECALC_MIN_COUNT, ATTENTION_RECALC_RECENCY_DAYS)
        rows = compute_attention_scores(
            universe,
            market=market,
            recency_days=ATTENTION_RECALC_RECENCY_DAYS,
            historical_years=ATTENTION_HISTORICAL_YEARS,
            use_google_news=ATTENTION_USE_GOOGLE_NEWS,
            news_workers=ATTENTION_NEWS_WORKERS,
            show_progress=ATTENTION_SHOW_PROGRESS,
        )
        screened = _to_screened_rows(rows, market, ATTENTION_RECALC_RECENCY_DAYS)
        filtered = [r for r in screened if r["attention_percentile"] >= ATTENTION_PERCENTILE_MIN]
        filtered.sort(key=lambda r: r["attention_score"], reverse=True)

    selected = filtered[:max(0, target_count)]
    meta = {
        "market": market,
        "benchmark_top_n": ATTENTION_BENCHMARK_TOP_N,
        "percentile_threshold": ATTENTION_PERCENTILE_MIN,
        "target_count": target_count,
        "candidate_count": len(screened),
        "filtered_count": len(filtered),
        "selected_count": len(selected),
        "recalc_applied": recalc_applied,
        "base_recency_days": ATTENTION_RECENCY_DAYS,
        "recalc_recency_days": ATTENTION_RECALC_RECENCY_DAYS,
        "recalc_min_count": ATTENTION_RECALC_MIN_COUNT,
        "news_enabled": ATTENTION_USE_GOOGLE_NEWS,
    }
    return selected, meta


def get_last_screening_meta() -> dict:
    """마지막 screen_stocks 실행 메타 정보."""
    return dict(_LAST_SCREENING_META)


def screen_stocks(market: str = "KR") -> list[dict]:
    """Attention 점수 기반 hot 종목 선별. market=ALL이면 KR+US 통합."""
    global _LAST_SCREENING_META

    if market == "ALL":
        kr_rows, kr_meta = _run_attention_market("KR", ATTENTION_ALL_TARGET_PER_MARKET)
        us_rows, us_meta = _run_attention_market("US", ATTENTION_ALL_TARGET_PER_MARKET)
        combined = kr_rows + us_rows
        _LAST_SCREENING_META = {
            "method": "attention_score",
            "market": "ALL",
            "markets": {"KR": kr_meta, "US": us_meta},
            "total_selected": len(combined),
        }
        return combined

    target = ATTENTION_SINGLE_MARKET_TARGET
    selected, meta = _run_attention_market(market, target)
    _LAST_SCREENING_META = {
        "method": "attention_score",
        "market": market,
        "markets": {market: meta},
        "total_selected": len(selected),
    }
    return selected
