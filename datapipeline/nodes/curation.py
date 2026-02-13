"""데이터 수집 노드: 요약 + 큐레이션 + CuratedContext 빌드.

4개 노드:
1. summarize_news: GPT-5 mini Map/Reduce 뉴스 요약
2. summarize_research: GPT-5 mini Map/Reduce 리포트 요약
3. curate_topics: GPT-5.2 web search 큐레이션
4. build_curated_context: topics[0] → CuratedContext 조립
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
from typing import Any

from langsmith import traceable

from ..schemas import CuratedContext

logger = logging.getLogger(__name__)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


# ── Mock 데이터 ──

_MOCK_SUMMARY = """\
## 반도체
반도체 업황 개선 신호가 나타나고 있어요. 재고 조정이 마무리 국면에 접어들었어요.

## AI/테크
AI 인프라 투자 확대로 관련 종목이 강세를 보이고 있어요."""

_MOCK_TOPICS = [
    {
        "topic": "반도체 업황 회복",
        "interface_1_curated_context": {
            "date": dt.date.today().isoformat(),
            "theme": "반도체 업황 회복과 AI 수요 확대",
            "one_liner": "재고 조정 마무리와 AI 수요 확대가 맞물리며 반도체 업황이 회복세를 보이고 있어요.",
            "selected_stocks": [
                {"ticker": "005930", "name": "삼성전자", "momentum": "상승", "change_pct": 8.5, "period_days": 5},
                {"ticker": "000660", "name": "SK하이닉스", "momentum": "상승", "change_pct": 15.3, "period_days": 126},
            ],
            "verified_news": [
                {
                    "title": "[Mock] 반도체 업황 개선 신호",
                    "url": "https://example.com/mock-news-1",
                    "source": "Mock Economy",
                    "summary": "반도체 재고 조정이 마무리 국면에 접어들었어요.",
                    "published_date": dt.date.today().isoformat(),
                },
            ],
            "reports": [
                {
                    "title": "[Mock] 산업 전망 리포트",
                    "source": "Mock Securities",
                    "summary": "2026년 반도체 업황은 하반기 회복이 예상돼요.",
                    "date": dt.date.today().isoformat(),
                },
            ],
            "concept": {
                "name": "반도체 사이클",
                "definition": "수요와 공급의 엇갈림으로 상승과 하락이 반복되는 주기예요.",
                "relevance": "현재는 재고 조정 마무리와 AI 신수요가 동시에 나타나는 전환점이에요.",
            },
            "source_ids": ["ws1_s1", "ws1_s2"],
            "evidence_source_urls": ["https://example.com/mock-evidence-1"],
        },
    },
    {
        "topic": "2차전지 공급과잉 우려",
        "interface_1_curated_context": {
            "date": dt.date.today().isoformat(),
            "theme": "2차전지 공급과잉 국면에서의 구조조정과 생존 전략",
            "one_liner": "전기차 판매는 늘고 있는데 배터리 기업 주가는 왜 빠질까요?",
            "selected_stocks": [
                {"ticker": "373220", "name": "LG에너지솔루션", "momentum": "하락", "change_pct": -12.3, "period_days": 30},
                {"ticker": "006400", "name": "삼성SDI", "momentum": "하락", "change_pct": -8.7, "period_days": 30},
            ],
            "verified_news": [
                {
                    "title": "[Mock] 2차전지 공급과잉 심화",
                    "url": "https://example.com/mock-news-2",
                    "source": "Mock Economy",
                    "summary": "글로벌 배터리 생산능력이 수요의 2배를 넘어섰어요.",
                    "published_date": dt.date.today().isoformat(),
                },
            ],
            "reports": [
                {
                    "title": "[Mock] 2차전지 산업 구조조정 전망",
                    "source": "Mock Securities",
                    "summary": "2026년 하반기까지 공급과잉 지속, 원가 경쟁력이 핵심이에요.",
                    "date": dt.date.today().isoformat(),
                },
            ],
            "concept": {
                "name": "공급과잉(Oversupply)",
                "definition": "시장에 공급되는 양이 수요보다 많아 가격이 하락하는 현상이에요.",
                "relevance": "배터리 업계의 공격적 증설이 가격 하락과 수익성 악화로 이어지고 있어요.",
            },
            "source_ids": ["ws2_s1", "ws2_s2"],
            "evidence_source_urls": ["https://example.com/mock-evidence-2"],
        },
    },
    {
        "topic": "AI 인프라 투자 확대",
        "interface_1_curated_context": {
            "date": dt.date.today().isoformat(),
            "theme": "AI 인프라 투자 사이클과 수혜 밸류체인 확장",
            "one_liner": "빅테크의 AI 투자가 폭발적인데, 한국 기업은 어디서 수혜를 받을까요?",
            "selected_stocks": [
                {"ticker": "035420", "name": "NAVER", "momentum": "상승", "change_pct": 11.2, "period_days": 20},
                {"ticker": "017670", "name": "SK텔레콤", "momentum": "상승", "change_pct": 6.8, "period_days": 20},
            ],
            "verified_news": [
                {
                    "title": "[Mock] 빅테크 AI 인프라 투자 급증",
                    "url": "https://example.com/mock-news-3",
                    "source": "Mock Economy",
                    "summary": "글로벌 빅테크 기업들의 AI 인프라 투자가 전년 대비 50% 이상 증가했어요.",
                    "published_date": dt.date.today().isoformat(),
                },
            ],
            "reports": [
                {
                    "title": "[Mock] AI 인프라 수혜 분석",
                    "source": "Mock Securities",
                    "summary": "데이터센터, 냉각장비, 전력 인프라 순으로 수혜가 확산될 전망이에요.",
                    "date": dt.date.today().isoformat(),
                },
            ],
            "concept": {
                "name": "밸류체인(Value Chain)",
                "definition": "제품이 만들어지기까지 거치는 기업 간 가치 사슬이에요.",
                "relevance": "AI 칩 → 서버 → 데이터센터 → 냉각/전력으로 이어지는 투자 파급 효과를 이해해야 해요.",
            },
            "source_ids": ["ws3_s1", "ws3_s2"],
            "evidence_source_urls": ["https://example.com/mock-evidence-3"],
        },
    },
]


@traceable(name="summarize_news", run_type="llm",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 4})
def summarize_news_node(state: dict) -> dict:
    """뉴스 GPT-5 mini Map/Reduce 요약."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] summarize_news")

    backend = state.get("backend", "live")
    raw_news = state.get("raw_news", [])

    if backend == "mock":
        logger.info("  summarize_news mock")
        return {
            "news_summary": _MOCK_SUMMARY,
            "metrics": _update_metrics(state, "summarize_news", time.time() - node_start),
        }

    try:
        from ..data_collection.news_summarizer import summarize_news
        summary = summarize_news(raw_news)
        logger.info("  summarize_news 완료: %d자", len(summary))
        return {
            "news_summary": summary,
            "metrics": _update_metrics(state, "summarize_news", time.time() - node_start),
        }
    except Exception as e:
        logger.warning("  summarize_news 실패 (비치명적): %s", e)
        return {
            "news_summary": "(뉴스 요약 실패)",
            "metrics": _update_metrics(state, "summarize_news", time.time() - node_start, "failed_nonfatal"),
        }


@traceable(name="summarize_research", run_type="llm",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 5})
def summarize_research_node(state: dict) -> dict:
    """리포트 GPT-5 mini Map/Reduce 요약."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] summarize_research")

    backend = state.get("backend", "live")
    raw_reports = state.get("raw_reports", [])

    if backend == "mock":
        logger.info("  summarize_research mock")
        return {
            "research_summary": _MOCK_SUMMARY,
            "metrics": _update_metrics(state, "summarize_research", time.time() - node_start),
        }

    try:
        from ..data_collection.news_summarizer import summarize_research
        summary = summarize_research(raw_reports)
        logger.info("  summarize_research 완료: %d자", len(summary))
        return {
            "research_summary": summary,
            "metrics": _update_metrics(state, "summarize_research", time.time() - node_start),
        }
    except Exception as e:
        logger.warning("  summarize_research 실패 (비치명적): %s", e)
        return {
            "research_summary": "(리포트 요약 실패)",
            "metrics": _update_metrics(state, "summarize_research", time.time() - node_start, "failed_nonfatal"),
        }


@traceable(name="curate_topics", run_type="llm",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 6})
def curate_topics_node(state: dict) -> dict:
    """GPT-5.2 + web search → 투자 테마 큐레이션."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] curate_topics")

    backend = state.get("backend", "live")

    if backend == "mock":
        logger.info("  curate_topics mock: %d topics", len(_MOCK_TOPICS))
        return {
            "curated_topics": _MOCK_TOPICS,
            "websearch_log": {"mock": True},
            "metrics": _update_metrics(state, "curate_topics", time.time() - node_start),
        }

    try:
        from ..data_collection.openai_curator import curate_with_websearch

        news_summary = state.get("news_summary", "(뉴스 없음)")
        research_summary = state.get("research_summary", "(리포트 없음)")

        # 스크리닝 결과를 텍스트로 포맷
        matched = state.get("matched_stocks", [])
        screening_lines = []
        for s in matched:
            line = f"- {s['name']} ({s['symbol']})"
            if s.get("attention_score") is not None:
                line += (f": attention={s['attention_score']:.4f} "
                         f"(상위 {100 - s.get('attention_percentile', 0):.0f}%), "
                         f"거래량비 {s['volume_ratio']}x")
            else:
                line += f": {s['signal']}, 수익률 {s['return_pct']}%, 거래량비 {s['volume_ratio']}x"
            screening_lines.append(line)
        screening_results = "\n".join(screening_lines) or "(스크리닝 결과 없음)"

        market = state.get("market", "KR")
        date = dt.date.today().isoformat()

        topics, log_data = curate_with_websearch(
            news_summary=news_summary,
            reports_summary=research_summary,
            screening_results=screening_results,
            date=date,
            market=market,
        )

        logger.info("  curate_topics 완료: %d topics", len(topics))
        return {
            "curated_topics": topics,
            "websearch_log": log_data,
            "metrics": _update_metrics(state, "curate_topics", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  curate_topics 실패: %s", e)
        return {
            "error": f"curate_topics 실패: {e}",
            "metrics": _update_metrics(state, "curate_topics", time.time() - node_start, "failed"),
        }


@traceable(name="build_curated_context", run_type="tool",
           metadata={"phase": "data_collection", "phase_name": "데이터 수집", "step": 7})
def build_curated_context_node(state: dict) -> dict:
    """curated_topics[topic_index] → CuratedContext 조립 + Pydantic 검증."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] build_curated_context")

    try:
        topics = state.get("curated_topics", [])
        if not topics:
            return {
                "error": "큐레이션 결과가 없습니다.",
                "metrics": _update_metrics(state, "build_curated_context", time.time() - node_start, "failed"),
            }

        topic_index = state.get("topic_index", 0)
        if topic_index >= len(topics):
            topic_index = 0

        topic = topics[topic_index]
        raw_ctx = topic.get("interface_1_curated_context", topic)

        # Pydantic 검증
        curated = CuratedContext.model_validate(raw_ctx)

        # matched_stocks → selected_stocks attention 병합
        matched_stocks = state.get("matched_stocks") or []
        if matched_stocks:
            matched_map = {s["symbol"]: s for s in matched_stocks}
            enriched = []
            for stock in curated.selected_stocks:
                m = matched_map.get(stock.ticker)
                if m:
                    stock = stock.model_copy(update={
                        "attention_score": m.get("attention_score"),
                        "attention_percentile": m.get("attention_percentile"),
                        "volume_ratio": m.get("volume_ratio", 0.0),
                        "change_pct": m.get("return_pct", stock.change_pct),
                        "period_days": m.get("period_days", stock.period_days),
                    })
                enriched.append(stock)
            curated = curated.model_copy(update={"selected_stocks": enriched})

        logger.info("  build_curated_context 완료: theme=%s", curated.theme[:50])

        return {
            "curated_context": curated.model_dump(),
            "metrics": _update_metrics(state, "build_curated_context", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  build_curated_context 실패: %s", e)
        return {
            "error": f"build_curated_context 실패: {e}",
            "metrics": _update_metrics(state, "build_curated_context", time.time() - node_start, "failed"),
        }
