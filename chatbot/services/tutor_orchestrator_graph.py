"""Tutor orchestration graph for ambiguity handling and clarification."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger("narrative.tutor_orchestrator")


class OrchestratorState(TypedDict):
    original_message: str
    user_answer: str
    has_pending: bool
    effective_message: str
    resolved_message: str
    is_ambiguous: bool
    missing_slots: list[str]
    clarification_question: str
    clarification_options: list[dict[str, str]]
    reasoning: str


PERIOD_OPTIONS = [
    {"id": "period_10d", "label": "최근 10거래일", "value": "최근 10거래일 기준으로 진행해줘"},
    {"id": "period_1m", "label": "1개월", "value": "최근 1개월 기준으로 진행해줘"},
    {"id": "period_3m", "label": "3개월", "value": "최근 3개월 기준으로 진행해줘"},
]

GENERAL_OPTIONS = [
    {"id": "scope_current_screen", "label": "현재 화면 기준", "value": "현재 화면 내용을 기준으로 설명해줘"},
    {"id": "scope_specific_stock", "label": "특정 종목 기준", "value": "특정 종목 기준으로 설명해줘"},
    {"id": "scope_recent_data", "label": "최근 데이터 기준", "value": "최근 데이터 기준으로 설명해줘"},
]


def _is_period_related(message: str, missing_slots: list[str]) -> bool:
    lower = message.lower()
    period_keywords = ("기간", "언제", "최근", "시점", "range", "period", "월", "주", "일")
    if any(slot in {"period", "time_range", "date_range"} for slot in missing_slots):
        return True
    return any(keyword in lower for keyword in period_keywords)


def _heuristic_ambiguity(message: str) -> tuple[bool, list[str], str]:
    cleaned = message.strip()
    if not cleaned:
        return True, ["topic"], "입력이 비어 있음"

    pronoun_like = ("이거", "저거", "그거", "이 내용", "이 화면", "방금", "그냥")
    vague_verbs = ("해줘", "알려줘", "보여줘", "설명해줘", "자세히")
    has_pronoun = any(token in cleaned for token in pronoun_like)
    has_vague_verb = any(token in cleaned for token in vague_verbs)

    if len(cleaned) <= 8 and (has_pronoun or has_vague_verb):
        return True, ["topic"], "짧고 지시 대상이 불명확함"
    if has_pronoun and has_vague_verb:
        return True, ["topic"], "지시 대상/범위가 불명확함"
    return False, [], "명확한 요청"


def _normalize_options(options: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if isinstance(options, list):
        for idx, raw in enumerate(options):
            if not isinstance(raw, dict):
                continue
            label = str(raw.get("label") or "").strip()
            value = str(raw.get("value") or "").strip()
            if not label or not value:
                continue
            option_id = str(raw.get("id") or f"option_{idx + 1}")
            normalized.append({"id": option_id, "label": label, "value": value})
    return normalized[:3]


def _route_after_analyze(state: OrchestratorState) -> str:
    if state.get("has_pending"):
        return "resolve_clarification"
    if state.get("is_ambiguous"):
        return "build_clarification"
    return "pass_through"


async def analyze_ambiguity(state: OrchestratorState) -> OrchestratorState:
    if state.get("has_pending"):
        return {
            **state,
            "is_ambiguous": False,
            "missing_slots": [],
            "reasoning": "pending clarification detected",
        }

    message = (state.get("original_message") or "").strip()
    heuristic_ambiguous, heuristic_slots, heuristic_reasoning = _heuristic_ambiguity(message)

    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        return {
            **state,
            "is_ambiguous": heuristic_ambiguous,
            "missing_slots": heuristic_slots,
            "reasoning": f"heuristic(no_api_key): {heuristic_reasoning}",
        }

    prompt = (
        "사용자 질문이 모호한지 판정하세요. 모호하면 추가 확인 질문을 해야 합니다.\n"
        "모호한 경우 예시: 지시 대상이 불명확(이거/그거), 범위가 불명확, 기간이 불명확.\n"
        "반드시 JSON으로만 답하세요.\n"
        "{\n"
        '  "is_ambiguous": true,\n'
        '  "missing_slots": ["topic", "period"],\n'
        '  "reasoning": "판정 근거"\n'
        "}\n\n"
        f"[사용자 질문]\n{message}"
    )

    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "너는 사용자 질문의 모호성을 판정하는 분류기다. JSON만 출력한다.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        is_ambiguous = bool(parsed.get("is_ambiguous"))
        missing_slots = [str(v) for v in parsed.get("missing_slots", []) if str(v).strip()]
        reasoning = str(parsed.get("reasoning") or "").strip() or "llm analysis"
        return {
            **state,
            "is_ambiguous": is_ambiguous,
            "missing_slots": missing_slots,
            "reasoning": reasoning,
        }
    except Exception as exc:
        logger.warning("orchestrator ambiguity parse fallback: %s", exc)
        return {
            **state,
            "is_ambiguous": heuristic_ambiguous,
            "missing_slots": heuristic_slots,
            "reasoning": f"heuristic(fallback): {heuristic_reasoning}",
        }


async def build_clarification(state: OrchestratorState) -> OrchestratorState:
    message = state.get("original_message", "")
    missing_slots = list(state.get("missing_slots") or [])

    question = "요청 의도를 정확히 맞추기 위해 한 가지만 확인할게요. 어떤 기준으로 진행할까요?"
    options = GENERAL_OPTIONS
    if _is_period_related(message, missing_slots):
        question = "시각화 기준 기간을 확인할게요. 어떤 기간으로 진행할까요?"
        options = PERIOD_OPTIONS

    api_key = get_settings().OPENAI_API_KEY
    if api_key:
        prompt = (
            "사용자 질문에 대한 확인 질문 1개와 선택지 2~3개를 JSON으로 생성하세요.\n"
            "선택지는 간결하고 상호배타적이어야 합니다.\n"
            "{\n"
            '  "question": "확인 질문",\n'
            '  "options": [\n'
            '    {"id": "opt1", "label": "선택지1", "value": "LLM이 해석할 실제 답변 문장"}\n'
            "  ]\n"
            "}\n\n"
            f"[사용자 질문]\n{message}\n"
            f"[missing_slots]\n{missing_slots}"
        )
        try:
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "너는 대화형 금융 튜터의 확인 질문 생성기다. JSON만 출력한다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            parsed = json.loads(response.choices[0].message.content or "{}")
            llm_question = str(parsed.get("question") or "").strip()
            llm_options = _normalize_options(parsed.get("options"))
            if llm_question and llm_options:
                question = llm_question
                options = llm_options
        except Exception as exc:
            logger.warning("orchestrator clarification generation fallback: %s", exc)

    return {
        **state,
        "clarification_question": question,
        "clarification_options": options,
    }


async def pass_through(state: OrchestratorState) -> OrchestratorState:
    message = (state.get("original_message") or "").strip()
    return {
        **state,
        "effective_message": message,
        "resolved_message": message,
    }


async def resolve_clarification(state: OrchestratorState) -> OrchestratorState:
    original = (state.get("original_message") or "").strip()
    answer = (state.get("user_answer") or "").strip()
    merged = (
        f"{original}\n\n"
        f"[추가 확인 답변]\n{answer}\n\n"
        "위의 추가 확인 답변을 반영하여 사용자의 최종 의도를 해석하세요."
    ).strip()
    return {
        **state,
        "effective_message": merged,
        "resolved_message": merged,
        "is_ambiguous": False,
        "missing_slots": [],
    }


workflow = StateGraph(OrchestratorState)
workflow.add_node("analyze_ambiguity", analyze_ambiguity)
workflow.add_node("build_clarification", build_clarification)
workflow.add_node("pass_through", pass_through)
workflow.add_node("resolve_clarification", resolve_clarification)

workflow.set_entry_point("analyze_ambiguity")
workflow.add_conditional_edges(
    "analyze_ambiguity",
    _route_after_analyze,
    {
        "build_clarification": "build_clarification",
        "pass_through": "pass_through",
        "resolve_clarification": "resolve_clarification",
    },
)
workflow.add_edge("build_clarification", END)
workflow.add_edge("pass_through", END)
workflow.add_edge("resolve_clarification", END)

orchestrator_app = workflow.compile()


async def run_ambiguity_orchestrator(message: str) -> dict[str, Any]:
    initial: OrchestratorState = {
        "original_message": message,
        "user_answer": "",
        "has_pending": False,
        "effective_message": message,
        "resolved_message": message,
        "is_ambiguous": False,
        "missing_slots": [],
        "clarification_question": "",
        "clarification_options": [],
        "reasoning": "",
    }
    result = await orchestrator_app.ainvoke(initial)
    return {
        "effective_message": result.get("effective_message") or message,
        "is_ambiguous": bool(result.get("is_ambiguous")),
        "missing_slots": result.get("missing_slots") or [],
        "clarification_question": result.get("clarification_question") or "",
        "clarification_options": result.get("clarification_options") or [],
        "reasoning": result.get("reasoning") or "",
    }


async def resolve_effective_message(original_question: str, user_answer: str) -> str:
    initial: OrchestratorState = {
        "original_message": original_question,
        "user_answer": user_answer,
        "has_pending": True,
        "effective_message": original_question,
        "resolved_message": original_question,
        "is_ambiguous": False,
        "missing_slots": [],
        "clarification_question": "",
        "clarification_options": [],
        "reasoning": "",
    }
    result = await orchestrator_app.ainvoke(initial)
    return str(result.get("resolved_message") or result.get("effective_message") or original_question)
