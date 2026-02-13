"""LangGraph StateGraph 정의: 데이터 수집 + 내러티브 생성 + 최종 조립 파이프라인.

노드 흐름:
  START → [라우터: input_path 유무]
    ├─ 파일 로드: load_curated_context → run_page_purpose ...
    └─ 데이터 수집: [crawl_news || crawl_research] → screen_stocks
        → [summarize_news || summarize_research] → curate_topics
        → build_curated_context → run_page_purpose ...
  ... → run_page_purpose → run_historical_case → run_narrative_body
    → validate_interface2
    → run_theme → run_pages → merge_theme_pages
    → glossary_and_chart_parallel
        ├── run_glossary → run_hallcheck_glossary
        └── run_chart_agent (6섹션 asyncio.gather)
    → run_tone_final → collect_sources → assemble_output → save_to_db → END

병렬 분기 (asyncio.gather wrapper):
  1. collect_data_parallel: crawl_news + crawl_research 병렬
  2. summarize_parallel: summarize_news + summarize_research 병렬
  3. glossary_and_chart_parallel: glossary pipeline + chart_agent 병렬
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .nodes.crawlers import crawl_news_node, crawl_research_node
from .nodes.curation import (
    build_curated_context_node,
    curate_topics_node,
    summarize_news_node,
    summarize_research_node,
)
from .nodes.interface1 import load_curated_context_node
from .nodes.interface2 import (
    run_historical_case_node,
    run_narrative_body_node,
    run_page_purpose_node,
    validate_interface2_node,
)
from .nodes.interface3 import (
    run_theme_node,
    run_pages_node,
    merge_theme_pages_node,
    run_glossary_node,
    run_hallcheck_glossary_node,
    run_tone_final_node,
    collect_sources_node,
    assemble_output_node,
)
from .nodes.chart_agent import run_chart_agent_node
from .nodes.db_save import save_to_db_node
from .nodes.screening import screen_stocks_node

logger = logging.getLogger(__name__)


# ── State 정의 ──

class BriefingPipelineState(TypedDict):
    """파이프라인 전체 상태."""

    # 입력
    input_path: Optional[str]     # None이면 데이터 수집 모드
    topic_index: int
    backend: str                  # "live" | "mock"
    market: str                   # "KR" | "US" | "ALL"

    # Data Collection 중간 결과
    raw_news: Optional[list]
    raw_reports: Optional[list]
    screened_stocks: Optional[list]
    matched_stocks: Optional[list]
    news_summary: Optional[str]
    research_summary: Optional[str]
    curated_topics: Optional[list]
    websearch_log: Optional[dict]

    # Interface 1 출력
    curated_context: Optional[dict]

    # Interface 2 중간 결과
    page_purpose: Optional[dict]
    historical_case: Optional[dict]
    narrative: Optional[dict]
    raw_narrative: Optional[dict]

    # Interface 3 중간 결과
    i3_theme: Optional[dict]
    i3_pages: Optional[list]
    i3_validated: Optional[dict]
    i3_glossaries: Optional[list]
    i3_validated_glossaries: Optional[list]
    charts: Optional[dict]
    pages: Optional[list]
    sources: Optional[list]
    hallucination_checklist: Optional[list]
    theme: Optional[str]
    one_liner: Optional[str]

    # 최종 출력
    full_output: Optional[dict]
    output_path: Optional[str]

    # DB 저장 결과
    db_result: Optional[dict]

    # 메타
    error: Optional[str]
    metrics: Annotated[dict, lambda a, b: {**a, **b}]


# ── 병렬 wrapper 노드 ──

async def collect_data_parallel_node(state: dict) -> dict:
    """crawl_news + crawl_research 병렬 실행."""
    if state.get("error"):
        return {"error": state["error"]}

    logger.info("[Node] collect_data_parallel (crawl_news || crawl_research)")
    news_result, research_result = await asyncio.gather(
        asyncio.to_thread(crawl_news_node, state),
        asyncio.to_thread(crawl_research_node, state),
    )
    merged = {}
    merged.update(news_result)
    merged.update(research_result)
    news_metrics = news_result.get("metrics", {})
    research_metrics = research_result.get("metrics", {})
    merged["metrics"] = {**news_metrics, **research_metrics}
    return merged


async def summarize_parallel_node(state: dict) -> dict:
    """summarize_news + summarize_research 병렬 실행."""
    if state.get("error"):
        return {"error": state["error"]}

    logger.info("[Node] summarize_parallel (summarize_news || summarize_research)")
    news_result, research_result = await asyncio.gather(
        asyncio.to_thread(summarize_news_node, state),
        asyncio.to_thread(summarize_research_node, state),
    )
    merged = {}
    merged.update(news_result)
    merged.update(research_result)
    news_metrics = news_result.get("metrics", {})
    research_metrics = research_result.get("metrics", {})
    merged["metrics"] = {**news_metrics, **research_metrics}
    return merged


async def glossary_and_chart_parallel_node(state: dict) -> dict:
    """glossary pipeline(glossary→hallcheck_glossary)과 chart_agent를 병렬 실행."""
    if state.get("error"):
        return {"error": state["error"]}

    logger.info("[Node] glossary_and_chart_parallel (glossary pipeline || chart_agent)")

    async def _glossary_pipeline():
        g_result = await asyncio.to_thread(run_glossary_node, state)
        if g_result.get("error"):
            return g_result
        merged_state = {**state, **g_result}
        hg_result = await asyncio.to_thread(run_hallcheck_glossary_node, merged_state)
        return {**g_result, **hg_result}

    async def _chart_pipeline():
        # run_chart_agent_node는 async이므로 직접 await
        return await run_chart_agent_node(state)

    glossary_result, chart_result = await asyncio.gather(
        _glossary_pipeline(), _chart_pipeline(),
    )

    # glossary에서 에러 발생 시 전파
    if glossary_result.get("error"):
        return glossary_result

    merged = {}
    merged.update(glossary_result)
    merged.update(chart_result)

    # metrics 병합
    g_metrics = glossary_result.get("metrics", {})
    c_metrics = chart_result.get("metrics", {})
    merged["metrics"] = {**g_metrics, **c_metrics}
    return merged


# ── 조건부 라우팅 ──

def route_data_source(state: BriefingPipelineState) -> str:
    """input_path 유무로 데이터 소스 결정."""
    if state.get("input_path"):
        return "load_from_file"
    return "collect_data"


def check_error(state: BriefingPipelineState) -> str:
    """에러가 있으면 END로 라우팅."""
    if state.get("error"):
        return "end"
    return "continue"


# ── 그래프 빌더 ──

def build_graph() -> Any:
    """브리핑 파이프라인 LangGraph 컴파일."""
    graph = StateGraph(BriefingPipelineState)

    # 병렬 wrapper 노드 (2개)
    graph.add_node("collect_data_parallel", collect_data_parallel_node)
    graph.add_node("summarize_parallel", summarize_parallel_node)

    # Data Collection 노드
    graph.add_node("screen_stocks", screen_stocks_node)
    graph.add_node("curate_topics", curate_topics_node)
    graph.add_node("build_curated_context", build_curated_context_node)

    # Interface 1 (파일 로드)
    graph.add_node("load_curated_context", load_curated_context_node)

    # Interface 2 (순차 4단계)
    graph.add_node("run_page_purpose", run_page_purpose_node)
    graph.add_node("run_historical_case", run_historical_case_node)
    graph.add_node("run_narrative_body", run_narrative_body_node)
    graph.add_node("validate_interface2", validate_interface2_node)

    # Interface 3 (병렬 최적화: 8노드)
    graph.add_node("run_theme", run_theme_node)
    graph.add_node("run_pages", run_pages_node)
    graph.add_node("merge_theme_pages", merge_theme_pages_node)
    graph.add_node("glossary_and_chart_parallel", glossary_and_chart_parallel_node)
    graph.add_node("run_tone_final", run_tone_final_node)
    graph.add_node("collect_sources", collect_sources_node)
    graph.add_node("assemble_output", assemble_output_node)
    graph.add_node("save_to_db", save_to_db_node)

    # ── 엣지 ──

    # START → 라우터
    graph.add_conditional_edges(START, route_data_source, {
        "load_from_file": "load_curated_context",
        "collect_data": "collect_data_parallel",
    })

    # 파일 로드 → Interface 2
    graph.add_conditional_edges(
        "load_curated_context",
        check_error,
        {"continue": "run_page_purpose", "end": END},
    )

    # 데이터 수집 체인 (병렬 분기 적용)
    graph.add_edge("collect_data_parallel", "screen_stocks")
    graph.add_conditional_edges(
        "screen_stocks",
        check_error,
        {"continue": "summarize_parallel", "end": END},
    )
    graph.add_edge("summarize_parallel", "curate_topics")
    graph.add_conditional_edges(
        "curate_topics",
        check_error,
        {"continue": "build_curated_context", "end": END},
    )
    graph.add_conditional_edges(
        "build_curated_context",
        check_error,
        {"continue": "run_page_purpose", "end": END},
    )

    # Interface 2: 순차 실행
    graph.add_conditional_edges(
        "run_page_purpose",
        check_error,
        {"continue": "run_historical_case", "end": END},
    )
    graph.add_conditional_edges(
        "run_historical_case",
        check_error,
        {"continue": "run_narrative_body", "end": END},
    )
    graph.add_conditional_edges(
        "run_narrative_body",
        check_error,
        {"continue": "validate_interface2", "end": END},
    )

    # Interface 2 → Interface 3 (병렬 최적화)
    graph.add_conditional_edges(
        "validate_interface2",
        check_error,
        {"continue": "run_theme", "end": END},
    )
    graph.add_edge("run_theme", "run_pages")
    graph.add_edge("run_pages", "merge_theme_pages")
    graph.add_edge("merge_theme_pages", "glossary_and_chart_parallel")
    graph.add_edge("glossary_and_chart_parallel", "run_tone_final")
    graph.add_edge("run_tone_final", "collect_sources")
    graph.add_edge("collect_sources", "assemble_output")
    graph.add_edge("assemble_output", "save_to_db")
    graph.add_edge("save_to_db", END)

    return graph.compile()
