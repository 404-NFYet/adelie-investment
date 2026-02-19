"""Interface 3 Chatbot Suggestions Node."""

from __future__ import annotations

import logging
import time

from langsmith import traceable

from ..ai.llm_utils import call_llm_with_prompt

logger = logging.getLogger(__name__)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


@traceable(name="generate_suggestions", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "제안 생성", "step": 8})
def generate_suggestions_node(state: dict) -> dict:
    """Stage 3b: Chatbot Suggestions 생성."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] generate_suggestions")

    try:
        # 입력 추출
        theme = state.get("theme")
        one_liner = state.get("one_liner")
        
        # 내러티브 전체 내용 요약 또는 본문 사용
        # raw_narrative가 있으면 사용, 없으면 curated_context 사용
        narrative_output = state.get("narrative") # raw_narrative might be in "narrative" key depending on stage, check graph or interface2
        # interface2 returns "narrative": result
        # result structure has "narrative": { ... contents ... }
        
        if not theme:
            page_purpose = state.get("page_purpose", {})
            theme = page_purpose.get("theme")
            one_liner = page_purpose.get("one_liner")

        if not theme:
            curated = state.get("curated_context", {})
            theme = curated.get("theme", "No theme")
            one_liner = curated.get("one_liner", "")

        content_summary = ""
        if narrative_output:
            # narrative_output might have "narrative" key inside
            narrative = narrative_output.get("narrative", narrative_output)
            content_parts = []
            for key in ["background", "concept_explain", "history", "application", "caution", "summary"]:
                section = narrative.get(key, {})
                # section might be dict
                if isinstance(section, dict):
                    content_parts.append(f"## {section.get('purpose', key)}")
                    content_parts.append(section.get('content', ''))
                    for bullet in section.get('bullets', []):
                        content_parts.append(f"- {bullet}")
            content_summary = "\n".join(content_parts)
        else:
            # fallback: historical_case or curated summary
            hc = state.get("historical_case", {})
            if isinstance(hc, dict):
                hc_case = hc.get("historical_case", hc)
                content_summary = hc_case.get("summary", "No content available")

        backend = state.get("backend", "live")
        
        if backend == "mock":
             result = {
                 "questions": [
                     "이 현상이 내 포트폴리오에 어떤 영향을 미치나요?",
                     "관련된 다른 기업들은 어떤 움직임을 보이나요?",
                     "과거 사례와 비교했을 때 가장 큰 차이점은 무엇인가요?"
                 ]
             }
        else:
            result = call_llm_with_prompt("suggestions", {
                "theme": theme,
                "one_liner": one_liner,
                "content_summary": content_summary[:4000],  # Truncate to avoid token limit
            })

        questions = result.get("questions", [])
        logger.info("  generate_suggestions 완료: %d questions", len(questions))
        
        return {
            "suggested_questions": questions,
            "metrics": _update_metrics(state, "generate_suggestions", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  generate_suggestions 실패: %s", e)
        # 중요하지 않은 기능이므로 에러 시 빈 리스트 반환 (파이프라인 중단 방지)
        return {
            "suggested_questions": [],
            "metrics": _update_metrics(state, "generate_suggestions", time.time() - node_start, "failed_nonfatal"),
        }
