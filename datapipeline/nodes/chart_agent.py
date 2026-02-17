"""Chart Agent Node: Reasoning -> Tool Execution -> Generation -> Verification.

Handles the creation of financial charts by actively fetching data.
6섹션 asyncio.gather 병렬 처리로 ~325s → ~55s 최적화.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import time
import re
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

RISK_ORDER = {"낮음": 0, "low": 0, "중간": 1, "medium": 1, "높음": 2, "high": 2}
ESTIMATION_PATTERN = re.compile(r"\b(est(?:imated)?|mock)\b|\(e\)|추정", re.IGNORECASE)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


def _iter_chart_text_fields(chart: dict) -> list[str]:
    texts: list[str] = []
    if not isinstance(chart, dict):
        return texts

    layout = chart.get("layout")
    if isinstance(layout, dict):
        title = layout.get("title")
        if isinstance(title, str):
            texts.append(title)
        elif isinstance(title, dict):
            texts.append(str(title.get("text", "")))

        for axis_name in ("xaxis", "yaxis"):
            axis = layout.get(axis_name)
            if isinstance(axis, dict):
                axis_title = axis.get("title")
                if isinstance(axis_title, str):
                    texts.append(axis_title)
                elif isinstance(axis_title, dict):
                    texts.append(str(axis_title.get("text", "")))

    for trace in chart.get("data", []) if isinstance(chart.get("data"), list) else []:
        if not isinstance(trace, dict):
            continue
        for key in ("name",):
            if trace.get(key):
                texts.append(str(trace.get(key)))
        for key in ("x", "labels", "text"):
            values = trace.get(key)
            if isinstance(values, list):
                texts.extend(str(v) for v in values if v is not None)

    return [t for t in texts if t]


def _contains_estimation_marker(chart: dict) -> bool:
    return any(ESTIMATION_PATTERN.search(text) for text in _iter_chart_text_fields(chart))


def _count_numeric_points(chart: dict) -> int:
    count = 0
    traces = chart.get("data", []) if isinstance(chart, dict) else []
    for trace in traces if isinstance(traces, list) else []:
        if not isinstance(trace, dict):
            continue
        for key in ("y", "values"):
            values = trace.get(key)
            if not isinstance(values, list):
                continue
            for value in values:
                try:
                    if value is not None and float(value) == float(value):
                        count += 1
                except (TypeError, ValueError):
                    continue
    return count


def _max_risk_label(items: list[dict]) -> str:
    max_score = 0
    max_label = "낮음"
    for item in items:
        risk = str(item.get("risk", "")).strip()
        score = RISK_ORDER.get(risk, 0)
        if score > max_score:
            max_score = score
            max_label = "중간" if score == 1 else "높음"
    return max_label


def _append_gate_item(checklist: list[dict], section_key: str, reason: str, risk: str = "높음") -> None:
    checklist.append({
        "claim": f"{section_key} 차트 비노출",
        "source": "chart_gate",
        "risk": risk,
        "note": reason,
    })


def _extract_selected_stock_names(curated_context: dict[str, Any], limit: int = 3) -> list[str]:
    selected = curated_context.get("selected_stocks") if isinstance(curated_context, dict) else None
    if not isinstance(selected, list):
        return []

    names: list[str] = []
    for stock in selected:
        if not isinstance(stock, dict):
            continue
        name = str(stock.get("name") or stock.get("ticker") or "").strip()
        if not name or name in names:
            continue
        names.append(name)
        if len(names) >= limit:
            break
    return names


def _needs_fx_context(text: str) -> bool:
    lower = text.lower()
    keywords = (
        "환율", "원달러", "원/달러", "usd", "dollar", "달러",
        "수출", "금리", "dxy", "외환",
    )
    return any(keyword in lower for keyword in keywords)


def _build_step_retry_tool_calls(
    *,
    section_title: str,
    section_key: str,
    section_content: str,
    viz_hint: str,
    curated_context: dict[str, Any],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    stock_names = _extract_selected_stock_names(curated_context, limit=3)
    current_year = dt.datetime.now().year

    for name in stock_names[:2]:
        calls.append({
            "tool": "get_corp_financials",
            "args": {"corp_name": name, "year": current_year},
        })
        calls.append({
            "tool": "get_corp_financials",
            "args": {"corp_name": name, "year": current_year - 1},
        })

    query_parts = [section_title.strip(), viz_hint.strip(), section_content.strip()[:140]]
    if stock_names:
        query_parts.append(f"관련 기업: {', '.join(stock_names)}")
    query_parts.append("정량 지표 데이터")
    query = " | ".join(part for part in query_parts if part)
    calls.append({
        "tool": "search_web_for_chart_data",
        "args": {"query": query},
    })

    combined_text = " ".join([section_title, section_key, viz_hint, section_content])
    if _needs_fx_context(combined_text):
        calls.append({
            "tool": "get_exchange_rate",
            "args": {"target_date": dt.datetime.now().strftime("%Y%m%d")},
        })

    return calls


def _dedupe_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for call in tool_calls:
        tool_name = str(call.get("tool", "")).strip()
        args = call.get("args", {})
        key = json.dumps({"tool": tool_name, "args": args}, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"tool": tool_name, "args": args})
    return deduped


def _normalize_sources_for_step(sources: list[dict[str, Any]], step: int) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        normalized_src = dict(src)
        if not normalized_src.get("used_in_pages"):
            normalized_src["used_in_pages"] = [step]
        normalized.append(normalized_src)
    return normalized


def _run_chart_generation(
    *,
    step: int,
    section_title: str,
    viz_hint: str,
    chart_type: str,
    internal_context_summary: str,
    tool_outputs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    generation_result = call_llm_with_prompt(
        "3_chart_generation",
        {
            "section_title": section_title,
            "step": step,
            "viz_hint": viz_hint,
            "chart_type": chart_type,
            "internal_context_summary": internal_context_summary,
            "tool_outputs": json.dumps(tool_outputs, ensure_ascii=False),
            "color_palette": COLOR_PALETTE,
        },
    )
    return generation_result.get("chart"), generation_result.get("sources", [])


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
    curated_context: dict[str, Any],
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
        raw_should_generate = reasoning_result.get("should_generate", True)
        if isinstance(raw_should_generate, bool):
            should_generate = raw_should_generate
        elif isinstance(raw_should_generate, str):
            should_generate = raw_should_generate.strip().lower() not in {"false", "0", "no", "n"}
        else:
            should_generate = bool(raw_should_generate)
        skip_reason = str(reasoning_result.get("skip_reason", "")).strip()

        if not should_generate or str(chart_type).strip().lower() in {"none", "no_chart", "null"}:
            logger.info(f"    [{section_key}] Skipped chart generation: {skip_reason or 'reasoning decided no chart'}")
            return section_key, None, []

        logger.info(f"    [{section_key}] Reasoning: Type={chart_type}, Tools={len(tool_calls)}")

        # 2. Tool Execution
        tool_outputs = await asyncio.to_thread(_execute_tools, _dedupe_tool_calls(tool_calls))

        # 3. Generation
        generated_chart, generated_sources = await asyncio.to_thread(
            _run_chart_generation,
            step=step,
            section_title=title,
            viz_hint=viz_hint,
            chart_type=str(chart_type),
            internal_context_summary=internal_context_summary,
            tool_outputs=tool_outputs,
        )

        if generated_chart:
            return section_key, generated_chart, _normalize_sources_for_step(generated_sources, step)
        logger.warning(f"    [{section_key}] Chart generation returned empty")

        if step <= 4:
            retry_calls = _build_step_retry_tool_calls(
                section_title=title,
                section_key=section_key,
                section_content=str(section.get("content") or ""),
                viz_hint=viz_hint,
                curated_context=curated_context,
            )
            retry_calls = _dedupe_tool_calls(retry_calls)
            if retry_calls:
                logger.info(
                    "    [%s] Retry chart generation with enriched data (tools=%d)",
                    section_key,
                    len(retry_calls),
                )
                retry_outputs = await asyncio.to_thread(_execute_tools, retry_calls)
                merged_outputs = tool_outputs + retry_outputs
                retry_chart, retry_sources = await asyncio.to_thread(
                    _run_chart_generation,
                    step=step,
                    section_title=title,
                    viz_hint=viz_hint,
                    chart_type=str(chart_type),
                    internal_context_summary=internal_context_summary,
                    tool_outputs=merged_outputs,
                )
                if retry_chart:
                    logger.info(f"    [{section_key}] Retry chart generation succeeded")
                    return section_key, retry_chart, _normalize_sources_for_step(retry_sources, step)
                logger.warning(f"    [{section_key}] Retry chart generation still empty")

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
                    curated,
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
        charts = dict(state.get("charts", {}) or {})
        checklist = list(state.get("hallucination_checklist", []) or [])
        sources = state.get("sources", []) or []
        backend = state.get("backend", "live")
        if backend == "mock":
             return {
                "charts": charts,
                "hallucination_checklist": checklist, # Pass through
                "metrics": _update_metrics(state, "run_hallcheck_chart", time.time() - node_start),
            }

        curated = state["curated_context"]

        for step, title, section_key in SECTION_MAP:
            chart = charts.get(section_key)
            if not chart:
                continue

            step_sources = [
                src for src in sources
                if step in (src.get("used_in_pages") or [])
            ]

            # Rule gate: source linkage, estimate markers, data adequacy
            if not step_sources:
                charts[section_key] = None
                _append_gate_item(checklist, section_key, "출처 연결이 없어 차트를 숨겼어요.")
                continue

            if _contains_estimation_marker(chart):
                charts[section_key] = None
                _append_gate_item(checklist, section_key, "추정치/Mock 표기가 있어 차트를 숨겼어요.")
                continue

            if _count_numeric_points(chart) < 3:
                charts[section_key] = None
                _append_gate_item(
                    checklist,
                    section_key,
                    "유효 데이터 포인트가 부족해 차트를 숨겼어요.",
                    risk="중간",
                )
                continue

            result = call_llm_with_prompt("3_hallcheck_chart", {
                "chart_json": json.dumps(chart, ensure_ascii=False),
                "source_context": json.dumps(curated, ensure_ascii=False)[:2000],
                "sources_metadata": json.dumps(step_sources, ensure_ascii=False)
            })

            new_items = result.get("hallucination_checklist", []) or []
            max_risk = _max_risk_label(new_items)
            if max_risk in {"중간", "높음"}:
                charts[section_key] = None
                _append_gate_item(checklist, section_key, f"팩트체크 위험도({max_risk})로 차트를 숨겼어요.", risk=max_risk)

            logger.info(f"  {section_key}: Found {len(new_items)} verification items. max_risk={max_risk}")
            checklist.extend(new_items)

        return {
            "charts": charts,
            "hallucination_checklist": checklist,
            "metrics": _update_metrics(state, "run_hallcheck_chart", time.time() - node_start),
        }

    except Exception as e:
        logger.error(f"  run_hallcheck_chart failed: {e}", exc_info=True)
        return {
            "error": f"run_hallcheck_chart failed: {e}",
            "metrics": _update_metrics(state, "run_hallcheck_chart", time.time() - node_start, "failed"),
        }
