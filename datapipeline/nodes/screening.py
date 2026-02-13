"""데이터 수집 노드: 주가 스크리닝.

FinanceDataReader 기반 가격 변동 스크리닝 + MatchedStock 변환.
스크리닝 실패는 치명적 (종목 없으면 진행 불가).
"""

from __future__ import annotations

import logging
import time

from langsmith import traceable

logger = logging.getLogger(__name__)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


_MOCK_SCREENED = [
    {"symbol": "005930", "name": "삼성전자", "signal": "attention_hot",
     "return_pct": 0.8234, "volume_ratio": 2.1, "period_days": 7,
     "attention_score": 0.8234, "attention_percentile": 98.0,
     "market": "KR", "recency_days": 7},
    {"symbol": "000660", "name": "SK하이닉스", "signal": "attention_hot",
     "return_pct": 0.6512, "volume_ratio": 1.8, "period_days": 7,
     "attention_score": 0.6512, "attention_percentile": 92.0,
     "market": "KR", "recency_days": 7},
    {"symbol": "035420", "name": "NAVER", "signal": "attention_hot",
     "return_pct": 0.5103, "volume_ratio": 3.2, "period_days": 7,
     "attention_score": 0.5103, "attention_percentile": 85.0,
     "market": "KR", "recency_days": 7},
]


@traceable(name="screen_stocks", run_type="tool",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 3})
def screen_stocks_node(state: dict) -> dict:
    """가격 변동 기준 종목 스크리닝 + MatchedStock 변환."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] screen_stocks")

    backend = state.get("backend", "live")
    market = state.get("market", "KR")

    if backend == "mock":
        from ..data_collection.intersection import screened_to_matched
        matched = [screened_to_matched(s) for s in _MOCK_SCREENED]
        logger.info("  screen_stocks mock: %d종목", len(matched))
        return {
            "screened_stocks": _MOCK_SCREENED,
            "matched_stocks": matched,
            "metrics": _update_metrics(state, "screen_stocks", time.time() - node_start),
        }

    try:
        from ..data_collection.screener import screen_stocks
        from ..data_collection.intersection import screened_to_matched

        screened = screen_stocks(market=market)
        if not screened:
            return {
                "error": "스크리닝 결과가 없습니다. 시장 데이터를 확인하세요.",
                "metrics": _update_metrics(state, "screen_stocks", time.time() - node_start, "failed"),
            }

        matched = [screened_to_matched(s) for s in screened]
        logger.info("  screen_stocks 완료: %d종목 스크리닝, %d종목 매칭", len(screened), len(matched))

        return {
            "screened_stocks": screened,
            "matched_stocks": matched,
            "metrics": _update_metrics(state, "screen_stocks", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  screen_stocks 실패: %s", e)
        return {
            "error": f"screen_stocks 실패: {e}",
            "metrics": _update_metrics(state, "screen_stocks", time.time() - node_start, "failed"),
        }
