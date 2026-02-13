"""Chart Agent Node: Reasoning -> Tool Execution -> Generation -> Verification.

Handles the creation of financial charts by actively fetching data.
6섹션 asyncio.gather 병렬 처리로 ~325s → ~55s 최적화.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable

from langsmith import traceable

from ..ai.llm_utils import call_llm_with_prompt
from ..config import COLOR_PALETTE, SECTION_MAP
from ..ai.tools import get_corp_financials, get_exchange_rate, search_web_for_chart_data

logger = logging.getLogger(__name__)

# Available tools map
AVAILABLE_TOOLS: dict[str, Callable] = {
    "get_corp_financials": get_corp_financials,
    "get_exchange_rate": get_exchange_rate,
    "search_web_for_chart_data": search_web_for_chart_data,
}


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


def _execute_tools(tool_calls: list[dict]) -> list[dict]:
    """tool_calls 리스트를 실행하고 결과를 반환 (동기)."""
    tool_outputs = []
    for call in tool_calls:
        tool_name = call.get("tool")
        args = call.get("args", {})

        if tool_name in AVAILABLE_TOOLS:
            try:
                logger.info(f"    Executing {tool_name} with {args}")
                output = AVAILABLE_TOOLS[tool_name](**args)
                tool_outputs.append({
                    "tool": tool_name,
                    "args": args,
                    "output": output,
                })
            except Exception as e:
                logger.error(f"    Tool {tool_name} failed: {e}")
                tool_outputs.append({
                    "tool": tool_name,
                    "error": str(e),
                })
        else:
            logger.warning(f"    Unknown tool: {tool_name}")
    return tool_outputs


async def _process_single_section(
    section_key: str,
    section: dict,
    step: int,
    title: str,
    viz_hint: str,
    internal_context_summary: str,
) -> tuple[str, Any, list[dict]]:
    """단일 섹션 차트: reasoning → tool → generation (병렬 실행 단위)."""
    try:
        # 1. Reasoning
        reasoning_result = await asyncio.to_thread(
            call_llm_with_prompt, "3_chart_reasoning", {
                "section_title": title,
                "content": section["content"],
                "viz_hint": viz_hint,
                "curated_context": internal_context_summary,
            },
        )

        tool_calls = reasoning_result.get("tool_calls", [])
        chart_type = reasoning_result.get("chart_type", "Unknown")
        logger.info(f"    [{section_key}] Reasoning: Type={chart_type}, Tools={len(tool_calls)}")

        # 2. Tool Execution
        tool_outputs = await asyncio.to_thread(_execute_tools, tool_calls)

        # 3. Generation
        generation_result = await asyncio.to_thread(
            call_llm_with_prompt, "3_chart_generation", {
                "section_title": title,
                "step": step,
                "viz_hint": viz_hint,
                "chart_type": chart_type,
                "internal_context_summary": internal_context_summary,
                "tool_outputs": json.dumps(tool_outputs, ensure_ascii=False),
                "color_palette": COLOR_PALETTE,
            },
        )

        generated_chart = generation_result.get("chart")
        generated_sources = generation_result.get("sources", [])

        if generated_chart:
            # 소스에 used_in_pages 기본값 설정
            for src in generated_sources:
                if not src.get("used_in_pages"):
                    src["used_in_pages"] = [step]
            return section_key, generated_chart, generated_sources
        else:
            logger.warning(f"    [{section_key}] Chart generation returned empty")
            return section_key, None, []

    except Exception as e:
        logger.warning(f"    [{section_key}] Chart failed (non-fatal): {e}")
        return section_key, None, []


@traceable(name="run_chart_agent", run_type="agent",
           metadata={"phase": "interface_3", "phase_name": "차트 생성", "step": 7})
async def run_chart_agent_node(state: dict) -> dict:
    """viz_hint -> Reasoning -> Tool Use -> Chart Generation (6섹션 병렬)."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_chart_agent (parallel)")

    try:
        raw = state["raw_narrative"]
        curated = state["curated_context"]
        narrative = raw["narrative"]
        backend = state.get("backend", "live")

        charts: dict[str, Any] = {}
        all_sources: list[dict] = []

        # context summary (reasoning 프롬프트에 공통 사용)
        internal_context_summary = json.dumps(curated, ensure_ascii=False)[:3000]

        if backend == "mock":
            # mock 모드: 순차 처리 (빠르므로 병렬화 불필요)
            for step, title, section_key in SECTION_MAP:
                section = narrative[section_key]
                viz_hint = section.get("viz_hint")
                if not viz_hint:
                    charts[section_key] = None
                    continue
                charts[section_key] = {
                    "data": [{"type": "bar", "x": ["Mock A", "Mock B"], "y": [10, 20], "name": "Mock Data"}],
                    "layout": {"title": f"[Mock] {viz_hint}"},
                }
                all_sources.append({
                    "name": "Mock Source",
                    "url_domain": "mock.com",
                    "used_in_pages": [step],
                })
        else:
            # live 모드: 6섹션 asyncio.gather 병렬
            tasks = []
            no_viz_sections = []
            for step, title, section_key in SECTION_MAP:
                section = narrative[section_key]
                viz_hint = section.get("viz_hint")
                if not viz_hint:
                    no_viz_sections.append(section_key)
                    continue
                logger.info(f"  Queuing chart for {section_key}: {viz_hint[:50]}...")
                tasks.append(_process_single_section(
                    section_key, section, step, title, viz_hint,
                    internal_context_summary,
                ))

            # viz_hint 없는 섹션은 None
            for sk in no_viz_sections:
                charts[sk] = None

            # 병렬 실행
            results = await asyncio.gather(*tasks)

            # 결과 병합
            for section_key, chart, sources in results:
                charts[section_key] = chart
                for src in sources:
                    existing = next((s for s in all_sources if s["name"] == src["name"]), None)
                    if existing:
                        for pg in src.get("used_in_pages", []):
                            if pg not in existing["used_in_pages"]:
                                existing["used_in_pages"].append(pg)
                    else:
                        all_sources.append(src)

        generated_count = len([k for k, v in charts.items() if v])
        logger.info(f"  run_chart_agent done. Generated {generated_count} charts.")

        return {
            "charts": charts,
            "sources": all_sources,
            "metrics": _update_metrics(state, "run_chart_agent", time.time() - node_start),
        }

    except Exception as e:
        logger.error(f"  run_chart_agent failed: {e}", exc_info=True)
        return {
            "error": f"run_chart_agent failed: {e}",
            "metrics": _update_metrics(state, "run_chart_agent", time.time() - node_start, "failed"),
        }


@traceable(name="run_hallcheck_chart", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "차트 검증", "step": 8})
def run_hallcheck_chart_node(state: dict) -> dict:
    """Generated Chart Hallucination Check."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_hallcheck_chart")
    
    try:
        charts = state.get("charts", {})
        # Existing checklist from previous steps (Interface 2/3 hallchecks)
        # Note: In the new flow, hallchecks might be accumulated.
        # But let's check input state.
        checklist = state.get("hallucination_checklist", [])
        
        backend = state.get("backend", "live")
        if backend == "mock":
             return {
                "hallucination_checklist": checklist, # Pass through
                "metrics": _update_metrics(state, "run_hallcheck_chart", time.time() - node_start),
            }

        curated = state["curated_context"]
        
        for step, title, section_key in SECTION_MAP:
            chart = charts.get(section_key)
            if not chart:
                continue
                
            # Run verification
            # We need to construct the context used for generation. 
            # Re-creating exact context is hard without saving tool outputs in state.
            # Ideally, state should have 'tool_outputs' from previous step if we want strict check.
            # For now, we use 'curated_context' + 'chart itself' + 'sources' metadata.
            # The prompt asks for 'source_context'.
            # We can pass the chart data and ask the LLM to verify against common knowledge or consistency.
            # Since we don't have the transient tool outputs here, we might miss some context.
            # Limitation: Hallcheck might flag "Low Risk" if it can't verify, or "High" if data looks weird.
            
            # Improvement: We should probably store tool outputs in state["chart_logs"] or similar if we want deep verification.
            # For this MVP, we'll verify consistency between Chart and Sources Metadata.
            
            result = call_llm_with_prompt("3_hallcheck_chart", {
                "chart_json": json.dumps(chart, ensure_ascii=False),
                "source_context": json.dumps(curated, ensure_ascii=False)[:2000],
                "sources_metadata": json.dumps(state.get("sources", []), ensure_ascii=False)
            })
            
            new_items = result.get("hallucination_checklist", [])
            logger.info(f"  {section_key}: Found {len(new_items)} verification items.")
            checklist.extend(new_items)

        return {
            "hallucination_checklist": checklist,
            "metrics": _update_metrics(state, "run_hallcheck_chart", time.time() - node_start),
        }

    except Exception as e:
        logger.error(f"  run_hallcheck_chart failed: {e}", exc_info=True)
        return {
            "error": f"run_hallcheck_chart failed: {e}",
            "metrics": _update_metrics(state, "run_hallcheck_chart", time.time() - node_start, "failed"),
        }
