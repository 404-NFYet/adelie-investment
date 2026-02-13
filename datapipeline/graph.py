"""LangGraph StateGraph 정의: 데이터 수집 + 내러티브 생성 + 최종 조립 파이프라인.

노드 흐름:
  START → [라우터: input_path 유무]
    ├─ 파일 로드: load_curated_context → run_page_purpose ...
    └─ 데이터 수집: [crawl_news || crawl_research] → screen_stocks
        → [summarize_news || summarize_research] → curate_topics
        → build_curated_context → run_page_purpose ...
  ... → run_page_purpose → run_historical_case → run_narrative_body
    → validate_interface2
    → [build_charts || build_glossary]
    → assemble_pages → collect_sources → run_final_check
    → assemble_output → END

병렬 분기 (asyncio.gather wrapper):
  1. collect_data_parallel: crawl_news + crawl_research 병렬
  2. summarize_parallel: summarize_news + summarize_research 병렬
  3. build_charts_glossary_parallel: build_charts + build_glossary 병렬
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
    assemble_output_node,
    assemble_pages_node,
    build_charts_node,
    build_glossary_node,
    collect_sources_node,
    run_final_check_node,
)
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
    charts: Optional[dict]
    glossaries: Optional[dict]
    pages: Optional[list]
    sources: Optional[list]
    hallucination_checklist: Optional[list]

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
    # metrics 병합
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


async def build_charts_glossary_parallel_node(state: dict) -> dict:
    """build_charts + build_glossary 병렬 실행."""
    if state.get("error"):
        return {"error": state["error"]}

    logger.info("[Node] build_charts_glossary_parallel (build_charts || build_glossary)")
    charts_result, glossary_result = await asyncio.gather(
        asyncio.to_thread(build_charts_node, state),
        asyncio.to_thread(build_glossary_node, state),
    )
    merged = {}
    merged.update(charts_result)
    merged.update(glossary_result)
    charts_metrics = charts_result.get("metrics", {})
    glossary_metrics = glossary_result.get("metrics", {})
    merged["metrics"] = {**charts_metrics, **glossary_metrics}
    # 에러 전파
    if charts_result.get("error"):
        merged["error"] = charts_result["error"]
    elif glossary_result.get("error"):
        merged["error"] = glossary_result["error"]
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

    # 병렬 wrapper 노드 (3개)
    graph.add_node("collect_data_parallel", collect_data_parallel_node)
    graph.add_node("summarize_parallel", summarize_parallel_node)
    graph.add_node("build_charts_glossary_parallel", build_charts_glossary_parallel_node)

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

    # Interface 3
    graph.add_node("assemble_pages", assemble_pages_node)
    graph.add_node("collect_sources", collect_sources_node)
    graph.add_node("run_final_check", run_final_check_node)
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

    # Interface 2 → Interface 3 (차트/용어 병렬)
    graph.add_conditional_edges(
        "validate_interface2",
        check_error,
        {"continue": "build_charts_glossary_parallel", "end": END},
    )
    graph.add_conditional_edges(
        "build_charts_glossary_parallel",
        check_error,
        {"continue": "assemble_pages", "end": END},
    )

    # assemble → collect → final_check → output
    graph.add_edge("assemble_pages", "collect_sources")
    graph.add_edge("collect_sources", "run_final_check")
    graph.add_edge("run_final_check", "assemble_output")
    graph.add_edge("assemble_output", "save_to_db")
    graph.add_edge("save_to_db", END)

    return graph.compile()
