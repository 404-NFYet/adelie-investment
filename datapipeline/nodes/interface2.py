"""Interface 2 노드: 4단계 내러티브 생성 파이프라인.

generate_interface2.py의 4단계 로직을 LangGraph 노드로 분리:
1. page_purpose → theme, one_liner, concept
2. historical_case → 과거 사례 매칭
3. narrative_body → 6단계 내러티브 본문
4. validate_interface2 → 할루시네이션 체크 + 조립
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from langsmith import traceable

from ..ai.llm_utils import JSONResponseParseError, call_llm_with_prompt
from ..schemas import RawNarrative

logger = logging.getLogger(__name__)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


MAX_VALIDATION_STOCKS = 8
MAX_VALIDATION_NEWS = 8
MAX_VALIDATION_REPORTS = 6
MAX_SHORT_TEXT = 280
MAX_LONG_TEXT = 1600

NARRATIVE_SECTION_KEYS = (
    "background",
    "concept_explain",
    "history",
    "application",
    "caution",
    "summary",
)


def _truncate_text(value: Any, max_chars: int = MAX_SHORT_TEXT) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1].rstrip()}…"


def _compact_concept(concept: Any) -> dict[str, str]:
    if not isinstance(concept, dict):
        return {"name": "", "definition": "", "relevance": ""}
    return {
        "name": _truncate_text(concept.get("name"), 120),
        "definition": _truncate_text(concept.get("definition"), 320),
        "relevance": _truncate_text(concept.get("relevance"), 320),
    }


def _compact_curated_context_for_validation(curated: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(curated, dict):
        return {}

    selected_stocks: list[dict[str, Any]] = []
    for stock in (curated.get("selected_stocks") or [])[:MAX_VALIDATION_STOCKS]:
        if not isinstance(stock, dict):
            continue
        selected_stocks.append({
            "ticker": _truncate_text(stock.get("ticker"), 20),
            "name": _truncate_text(stock.get("name"), 40),
            "momentum": _truncate_text(stock.get("momentum"), 20),
            "change_pct": stock.get("change_pct"),
            "period_days": stock.get("period_days"),
            "attention_score": stock.get("attention_score"),
            "attention_percentile": stock.get("attention_percentile"),
            "volume_ratio": stock.get("volume_ratio"),
        })

    verified_news: list[dict[str, str]] = []
    for news in (curated.get("verified_news") or [])[:MAX_VALIDATION_NEWS]:
        if not isinstance(news, dict):
            continue
        verified_news.append({
            "title": _truncate_text(news.get("title"), 180),
            "source": _truncate_text(news.get("source"), 60),
            "published_date": _truncate_text(news.get("published_date"), 20),
            "summary": _truncate_text(news.get("summary"), MAX_SHORT_TEXT),
        })

    reports: list[dict[str, str]] = []
    for report in (curated.get("reports") or [])[:MAX_VALIDATION_REPORTS]:
        if not isinstance(report, dict):
            continue
        reports.append({
            "title": _truncate_text(report.get("title"), 180),
            "source": _truncate_text(report.get("source"), 60),
            "date": _truncate_text(report.get("date"), 20),
            "summary": _truncate_text(report.get("summary"), MAX_SHORT_TEXT),
        })

    return {
        "date": _truncate_text(curated.get("date"), 20),
        "theme": _truncate_text(curated.get("theme"), 120),
        "one_liner": _truncate_text(curated.get("one_liner"), 180),
        "concept": _compact_concept(curated.get("concept")),
        "selected_stocks": selected_stocks,
        "verified_news": verified_news,
        "reports": reports,
        "source_ids": [
            _truncate_text(source_id, 80)
            for source_id in (curated.get("source_ids") or [])[:20]
        ],
    }


def _compact_page_purpose_for_validation(page_purpose: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(page_purpose, dict):
        return {}
    return {
        "theme": _truncate_text(page_purpose.get("theme"), 120),
        "one_liner": _truncate_text(page_purpose.get("one_liner"), 180),
        "concept": _compact_concept(page_purpose.get("concept")),
    }


def _compact_historical_case_for_validation(historical_case_output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(historical_case_output, dict):
        return {"historical_case": {}}

    historical_case = historical_case_output.get("historical_case", historical_case_output)
    if not isinstance(historical_case, dict):
        return {"historical_case": {}}

    return {
        "historical_case": {
            "period": _truncate_text(historical_case.get("period"), 80),
            "title": _truncate_text(historical_case.get("title"), 160),
            "summary": _truncate_text(historical_case.get("summary"), 420),
            "outcome": _truncate_text(historical_case.get("outcome"), 420),
            "lesson": _truncate_text(historical_case.get("lesson"), 420),
        }
    }


def _compact_narrative_output_for_validation(narrative_output: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(narrative_output, dict):
        return {"narrative": {}}

    narrative = narrative_output.get("narrative", narrative_output)
    if not isinstance(narrative, dict):
        return {"narrative": {}}

    compact_narrative: dict[str, Any] = {}
    for key in NARRATIVE_SECTION_KEYS:
        section = narrative.get(key, {})
        if not isinstance(section, dict):
            section = {}
        compact_narrative[key] = {
            "purpose": _truncate_text(section.get("purpose"), 220),
            "content": _truncate_text(section.get("content"), MAX_LONG_TEXT),
            "bullets": [
                _truncate_text(bullet, 180)
                for bullet in (section.get("bullets") or [])[:3]
            ],
            "viz_hint": (
                _truncate_text(section.get("viz_hint"), 220)
                if section.get("viz_hint") is not None
                else None
            ),
        }

    return {"narrative": compact_narrative}


def _json_size(payload: Any) -> int:
    try:
        return len(json.dumps(payload, ensure_ascii=False))
    except Exception:
        return 0


def _build_hallucination_check_inputs(
    curated: dict[str, Any],
    page_purpose: dict[str, Any],
    historical_case_output: dict[str, Any],
    narrative_output: dict[str, Any],
) -> dict[str, Any]:
    return {
        "curated_context": _compact_curated_context_for_validation(curated),
        "page_purpose_output": _compact_page_purpose_for_validation(page_purpose),
        "historical_case_output": _compact_historical_case_for_validation(historical_case_output),
        "narrative_output": _compact_narrative_output_for_validation(narrative_output),
    }


def _build_unvalidated_interface2(
    page_purpose: dict[str, Any],
    historical_case_output: dict[str, Any],
    narrative_output: dict[str, Any],
) -> dict[str, Any]:
    return {
        "theme": page_purpose.get("theme"),
        "one_liner": page_purpose.get("one_liner"),
        "concept": page_purpose.get("concept"),
        "historical_case": historical_case_output.get("historical_case", historical_case_output),
        "narrative": narrative_output.get("narrative", narrative_output),
    }


# ── Mock 함수들 (테스트용) ──

def _mock_page_purpose(curated: dict) -> dict:
    return {
        "theme": curated.get("theme", "핵심 산업 내 구조적 전환 국면"),
        "one_liner": curated.get("one_liner", "핵심 지표가 개선되는데 왜 주가는 아직 반응하지 못할까요?"),
        "concept": curated.get("concept", {
            "name": "핵심 산업 사이클",
            "definition": "수요와 공급의 엇갈림으로 상승과 하락이 반복되는 주기예요.",
            "relevance": "현재는 기존 수요 둔화와 신수요 확장이 동시에 나타나는 전환점이에요.",
        }),
    }


def _mock_historical_case(curated: dict, pp: dict) -> dict:
    concept_name = pp.get("concept", {}).get("name", "사이클")
    return {
        "historical_case": {
            "period": "과거 유사 사이클 구간",
            "title": f"{concept_name} 조정기와 회복기 전환 사례",
            "summary": "수요 급증 이후 공급이 빠르게 늘며 재고가 쌓였고, 가격 하락이 이어졌어요.",
            "outcome": "바닥 신호가 먼저 나타나도 시장은 추가 확인을 요구해서 반등이 지연될 수 있었어요.",
            "lesson": "재고 감소는 선행 신호이고 가격 반등은 후행 신호라는 시차를 분리해서 봐야 해요.",
        }
    }


def _mock_narrative(curated: dict, pp: dict, hc: dict) -> dict:
    stock_names = [
        s.get("name") for s in curated.get("selected_stocks", [])
        if isinstance(s, dict) and s.get("name")
    ]
    stock_label = " vs ".join(stock_names[:2]) if stock_names else "관련 기업들"

    return {
        "narrative": {
            "background": {
                "purpose": "독자의 주의를 환기하고 지금 읽어야 하는 이유를 제시",
                "content": f"최근 {stock_label}의 흐름이 크게 엇갈리면서 시장의 혼란이 커졌어요.",
                "bullets": ["업황 개선 신호와 주가 반응 사이의 괴리", "기업별 수혜 강도 차이 확대"],
                "viz_hint": f"line - {stock_label} 최근 주가 추이",
            },
            "concept_explain": {
                "purpose": "핵심 개념을 쉽게 설명하고 현재 맥락과 연결",
                "content": f"{pp['concept']['definition']}",
                "bullets": ["사이클은 선행지표와 후행지표의 시간차가 커요", "동일 산업 내에서도 제품군별 국면이 다를 수 있어요"],
                "viz_hint": None,
            },
            "history": {
                "purpose": "과거 메커니즘을 통해 현재 패턴 해석",
                "content": "과거 사례에서도 재고 감소와 가격 반등 사이에 시차가 있었어요.",
                "bullets": ["재고 지표 개선이 먼저 나타났어요", "가격과 실적 확인 후 주가 반응이 본격화됐어요"],
                "viz_hint": "dual_line - 재고 지표 vs 가격/주가",
            },
            "application": {
                "purpose": "과거 교훈을 현재 상황에 적용",
                "content": "현재도 재고 조정의 진전이라는 닮은 점이 있지만, 고부가 제품 경쟁력이라는 변수가 더 크게 작동하고 있어요.",
                "bullets": ["닮은 점: 재고 조정 진행", "다른 점: 고부가 제품 주도권 경쟁"],
                "viz_hint": "grouped_bar - 제품군별 매출 비중 비교",
            },
            "caution": {
                "purpose": "반대 시나리오와 리스크 균형 제시",
                "content": "바닥 신호가 나와도 반등 시점은 늦어질 수 있어요.",
                "bullets": [
                    "재고 감소만으로 가격 반등을 단정하기 어려워요",
                    "핵심 제품 품질/고객 인증 일정이 변수예요",
                    "대외 규제 강화는 추가 하방 리스크예요",
                ],
                "viz_hint": None,
            },
            "summary": {
                "purpose": "핵심 요약과 관찰 포인트 제시",
                "content": "### 투자 전에 꼭 확인할 포인트\n- 재고 지표가 연속으로 개선되는지 확인해요.\n- 가격 반등이 단기 반짝인지 지속 신호인지 구분해요.\n- 핵심 고객과 제품 관련 일정 변화를 매일 체크해요.",
                "bullets": ["재고 지표의 연속 개선 여부", "가격 반등의 지속성", "핵심 고객/제품 경쟁력 이벤트"],
                "viz_hint": None,
            },
        }
    }


def _mock_hallucination_check(pp: dict, hc: dict, narr: dict) -> dict:
    return {
        "overall_risk": "low",
        "summary": "mock 모드 결과예요. 실제 사실성 검증은 수행하지 않았어요.",
        "issues": [],
        "consistency_checks": [],
        "validated_interface_2": {
            "theme": pp["theme"],
            "one_liner": pp["one_liner"],
            "concept": pp["concept"],
            "historical_case": hc.get("historical_case", hc),
            "narrative": narr.get("narrative", narr),
        },
    }


# ── LangGraph 노드들 ──

@traceable(name="run_page_purpose", run_type="llm",
           metadata={"phase": "interface_2", "phase_name": "내러티브 생성", "step": 1})
def run_page_purpose_node(state: dict) -> dict:
    """Stage 1: theme, one_liner, concept 추출."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_page_purpose")

    try:
        curated = state["curated_context"]
        backend = state.get("backend", "live")

        if backend == "mock":
            result = _mock_page_purpose(curated)
        else:
            result = call_llm_with_prompt("page_purpose", {
                "curated_context": curated,
            })

        logger.info("  page_purpose 완료: theme=%s", result.get("theme", "")[:50])
        return {
            "page_purpose": result,
            "metrics": _update_metrics(state, "run_page_purpose", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  page_purpose 실패: %s", e)
        return {
            "error": f"page_purpose 실패: {e}",
            "metrics": _update_metrics(state, "run_page_purpose", time.time() - node_start, "failed"),
        }


@traceable(name="run_historical_case", run_type="llm",
           metadata={"phase": "interface_2", "phase_name": "내러티브 생성", "step": 2})
def run_historical_case_node(state: dict) -> dict:
    """Stage 2: 과거 사례 매칭."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_historical_case")

    try:
        pp = state["page_purpose"]
        curated = state["curated_context"]
        backend = state.get("backend", "live")

        if backend == "mock":
            result = _mock_historical_case(curated, pp)
        else:
            result = call_llm_with_prompt("historical_case", {
                "theme": pp["theme"],
                "one_liner": pp["one_liner"],
                "concept": pp["concept"],
                "curated_context": curated,
            })

        logger.info("  historical_case 완료")
        return {
            "historical_case": result,
            "metrics": _update_metrics(state, "run_historical_case", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  historical_case 실패: %s", e)
        return {
            "error": f"historical_case 실패: {e}",
            "metrics": _update_metrics(state, "run_historical_case", time.time() - node_start, "failed"),
        }


@traceable(name="run_narrative_body", run_type="llm",
           metadata={"phase": "interface_2", "phase_name": "내러티브 생성", "step": 3})
def run_narrative_body_node(state: dict) -> dict:
    """Stage 3: 6단계 내러티브 본문 생성."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_narrative_body")

    try:
        pp = state["page_purpose"]
        hc = state["historical_case"]
        curated = state["curated_context"]
        backend = state.get("backend", "live")

        if backend == "mock":
            result = _mock_narrative(curated, pp, hc)
        else:
            result = call_llm_with_prompt("narrative_body", {
                "theme": pp["theme"],
                "one_liner": pp["one_liner"],
                "concept": pp["concept"],
                "historical_case": hc.get("historical_case", hc),
                "curated_context": curated,
            })

        logger.info("  narrative_body 완료")
        return {
            "narrative": result,
            "metrics": _update_metrics(state, "run_narrative_body", time.time() - node_start),
        }

    except JSONResponseParseError as e:
        logger.error(
            "JSON_PARSE_FAILURE narrative_body 실패: prompt=%s provider=%s model=%s detail=%s",
            e.prompt_name,
            e.provider,
            e.model,
            e,
        )
        return {
            "error": (
                "narrative_body 실패: 모델 응답 JSON 불량 "
                f"(prompt={e.prompt_name}, provider={e.provider}, model={e.model})"
            ),
            "metrics": _update_metrics(
                state, "run_narrative_body", time.time() - node_start, "failed"
            ),
        }
    except Exception as e:
        logger.error("  narrative_body 실패: %s", e)
        return {
            "error": f"narrative_body 실패: {e}",
            "metrics": _update_metrics(state, "run_narrative_body", time.time() - node_start, "failed"),
        }


@traceable(name="validate_interface2", run_type="llm",
           metadata={"phase": "interface_2", "phase_name": "내러티브 생성", "step": 4})
def validate_interface2_node(state: dict) -> dict:
    """Stage 4: 할루시네이션 체크 + interface2 조립."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] validate_interface2")

    try:
        pp = state["page_purpose"]
        hc = state["historical_case"]
        narr = state["narrative"]
        curated = state["curated_context"]
        backend = state.get("backend", "live")
        fallback_validated = _build_unvalidated_interface2(pp, hc, narr)

        if backend == "mock":
            result = _mock_hallucination_check(pp, hc, narr)
        else:
            raw_payload = {
                "curated_context": curated,
                "page_purpose_output": pp,
                "historical_case_output": hc,
                "narrative_output": narr,
            }
            compact_payload = _build_hallucination_check_inputs(curated, pp, hc, narr)
            logger.info(
                "  validate_interface2 입력 축소: %.1fKB -> %.1fKB",
                _json_size(raw_payload) / 1024,
                _json_size(compact_payload) / 1024,
            )
            try:
                result = call_llm_with_prompt("hallucination_check", compact_payload)
            except Exception as hallcheck_exc:
                err_text = str(hallcheck_exc).lower()
                if "timed out" in err_text or "timeout" in err_text:
                    logger.warning(
                        "  validate_interface2 hallcheck timeout -> fallback 사용: %s",
                        hallcheck_exc,
                    )
                    result = {
                        "overall_risk": "medium",
                        "summary": "hallucination_check timeout으로 검증을 건너뛰고 원본 출력을 사용했어요.",
                        "issues": [],
                        "consistency_checks": [],
                        "validated_interface_2": fallback_validated,
                    }
                else:
                    raise

        # validated_interface_2 추출
        validated = result.get("validated_interface_2", fallback_validated)

        # summary는 텍스트 체크리스트 섹션으로 고정 (차트 생성 방지)
        summary_section = validated.get("narrative", {}).get("summary")
        if isinstance(summary_section, dict):
            summary_section["viz_hint"] = None

        # Pydantic 검증
        raw_narr = RawNarrative.model_validate(validated)
        logger.info("  validate_interface2 완료: overall_risk=%s", result.get("overall_risk"))

        return {
            "raw_narrative": raw_narr.model_dump(),
            "metrics": _update_metrics(state, "validate_interface2", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  validate_interface2 실패: %s", e)
        return {
            "error": f"validate_interface2 실패: {e}",
            "metrics": _update_metrics(state, "validate_interface2", time.time() - node_start, "failed"),
        }


@traceable(name="generate_suggestions", run_type="llm",
           metadata={"phase": "interface_2", "phase_name": "내러티브 생성", "step": 5})
def generate_suggestions_node(state: dict) -> dict:
    """Stage 5: 챗봇 추천 질문 생성."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] generate_suggestions")

    try:
        narr = state["narrative"]
        # 내러티브 본문 텍스트 추출 (요약 및 본문)
        narrative_text = ""
        if isinstance(narr, dict) and "narrative" in narr:
             n = narr["narrative"]
             if isinstance(n, dict):
                 narrative_text = f"배경: {n.get('background', {}).get('content', '')}\\n"
                 narrative_text += f"개념: {n.get('concept_explain', {}).get('content', '')}\\n"
                 narrative_text += f"적용: {n.get('application', {}).get('content', '')}\\n"
                 narrative_text += f"요약: {n.get('summary', {}).get('content', '')}"

        backend = state.get("backend", "live")

        if backend == "mock":
            result = ["(Mock) 이 현상이 지속될까요?", "(Mock) 과거와 다른 점은 무엇인가요?", "(Mock) 주요 리스크는 무엇인가요?"]
        else:
            # glossary 용어 추출 (간이)
            # 실제로는 DB나 state에서 가져와야 하지만, 여기서는 프롬프트에서 처리하도록 텍스트만 전달
            result = call_llm_with_prompt("suggested_questions", {
                "content": narrative_text[:3000], # 길이 제한
                "excluded_terms": [], # 필요시 추가
            })

        logger.info("  generate_suggestions 완료: %d개", len(result))
        
        # raw_narrative에 suggested_questions 필드가 없으므로 state에 별도 저장하거나
        # RawNarrative 스키마를 수정해야 함.
        # 여기서는 state에 'suggested_questions' 키로 추가하여 writer가 처리하도록 함.
        return {
            "suggested_questions": result,
            "metrics": _update_metrics(state, "generate_suggestions", time.time() - node_start),
        }

    except Exception as e:
        logger.warning("  generate_suggestions 실패 (무시됨): %s", e)
        return {
            # 실패해도 전체 파이프라인을 중단하지 않음
            "suggested_questions": [],
            "metrics": _update_metrics(state, "generate_suggestions", time.time() - node_start, "failed"),
        }
