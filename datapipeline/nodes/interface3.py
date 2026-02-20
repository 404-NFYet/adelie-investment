"""Interface 3 노드: theme → pages → hallcheck → glossary → hallcheck → tone_final → sources → output.

viz 브랜치 아키텍처 + jihoon v11 프롬프트 기반 10노드 순차 파이프라인.
(chart_agent 2노드는 nodes/chart_agent.py에 별도 정의)
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from langsmith import traceable

from ..ai.llm_utils import call_llm_with_prompt
from ..config import COLOR_PALETTE, OUTPUT_DIR, SECTION_MAP
from ..constants.home_icons import (
    DEFAULT_HOME_ICON_KEY,
    HOME_ICON_CANDIDATES,
    HOME_ICON_KEYS,
)
from ..schemas import (
    CuratedContext,
    FinalBriefing,
    FullBriefingOutput,
    RawNarrative,
)

logger = logging.getLogger(__name__)


def _update_metrics(state: dict, node_name: str, elapsed: float, status: str = "success") -> dict:
    metrics = dict(state.get("metrics") or {})
    metrics[node_name] = {"elapsed_s": round(elapsed, 2), "status": status}
    return metrics


DEFAULT_STEP_TITLES: dict[int, str] = {
    1: "왜 지금 중요할까",
    2: "핵심 개념 한눈에",
    3: "과거 패턴 되짚기",
    4: "지금 시장에 대입",
    5: "놓치면 위험한 점",
    6: "투자 전 체크포인트",
}
LEGACY_STEP_TITLES = {"현재 배경", "금융 개념 설명", "과거 비슷한 사례", "현재 상황에 적용", "주의해야 할 점", "최종 정리"}

DEFAULT_SECTION_HEADINGS: dict[int, tuple[str, str]] = {
    1: ("지금 무슨 일이야?", "왜 중요할까?"),
    2: ("개념 먼저 잡기", "지금 왜 필요할까?"),
    3: ("과거에선 어땠을까?", "이번에 주는 힌트"),
    4: ("닮은 점", "다른 점"),
    5: ("리스크 먼저 보기", "대응 포인트"),
}

PLACEHOLDER_HEADING_PATTERNS: tuple[str, ...] = (
    r"^\s*###\s*(?:소제목|접두사|heading|subheading|subtitle|title|제목)(?:\s*[:\-]?\s*\d+)?\s*[:\-]?\s*$",
)

MAX_SHORT_LINE_CHARS = 110
MAX_BULLETS_PER_PAGE = 5
MAX_BULLET_CHARS = 140
MAX_SECTION_SENTENCES = 6


def _soften_text(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n")
    if not normalized:
        return normalized
    # Markdown 강조 기호 잔여물과 [라벨] 플레이스홀더를 제거해 렌더 아티팩트를 방지한다.
    normalized = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", normalized)
    normalized = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", normalized)
    normalized = re.sub(r"(?<=[가-힣A-Za-z0-9.!?。！？])\*(?=\s|$)", "", normalized)
    normalized = re.sub(r"\[([가-힣A-Za-z0-9][^\[\]\n]{0,28})\]", r"\1", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    return normalized.strip()


def _shorten_text(text: str, max_chars: int = MAX_SHORT_LINE_CHARS) -> str:
    softened = _soften_text(text)
    if len(softened) <= max_chars:
        return softened
    # 문장 완결성을 우선한다. 중간 절단("...")은 금지.
    sentences = re.split(r"(?<=[.!?。！？])\s+", softened)
    picked: list[str] = []
    current_len = 0
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        add_len = len(s) + (1 if picked else 0)
        if picked and current_len + add_len > max_chars:
            break
        picked.append(s)
        current_len += add_len
        if current_len >= max_chars:
            break

    if picked:
        return " ".join(picked).strip()
    # 문장 구분자가 없고 한 문장만 매우 긴 경우: 원문 유지(의미 손실 방지)
    return softened


def _split_sentences(text: str) -> list[str]:
    cleaned = _soften_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    return [p.strip() for p in parts if p.strip()]


def _split_long_sentence(sentence: str, max_chars: int = 120) -> str:
    s = _soften_text(sentence)
    if len(s) <= max_chars:
        return s
    chunks = [c.strip() for c in re.split(r"[,:;]", s) if c.strip()]
    if len(chunks) < 2:
        return s
    short = chunks[:2]
    joined = ". ".join(short).strip()
    joined = re.sub(r"\.{2,}$", ".", joined)
    if not re.search(r"[.!?。！？]$", joined):
        joined += "."
    return joined


def _take_sentence_prefix(text: str, max_sentences: int = MAX_SECTION_SENTENCES) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return _soften_text(text)
    picked = [_split_long_sentence(s) for s in sentences[:max_sentences]]
    return " ".join(picked).strip()


def _linebreak_sentences(text: str) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return _soften_text(text)
    return "\n".join(sentences)


def _cleanup_label_artifacts(body_text: str, heading: str | None = None) -> str:
    text = _soften_text(body_text)
    if not text:
        return text

    # 문장/라인 끝에 실수로 붙는 라벨 꼬리 제거
    text = re.sub(r"(?:\s*\[?\s*과거\s*사이클\s*흐름\s*\]?)\s*$", "", text, flags=re.IGNORECASE)

    # 소제목과 중복되는 선행 라벨 제거
    if heading and "다른 점" in heading:
        text = re.sub(r"^\s*닮은\s*점[:\s-]+", "", text)
    if heading and "닮은 점" in heading:
        text = re.sub(r"^\s*닮은\s*점[:\s-]+", "", text)

    return text.strip()


def _compress_markdown_content(content: str, max_sentences_per_block: int = MAX_SECTION_SENTENCES) -> str:
    text = _soften_text(content)
    if not text:
        return text

    lines = text.split("\n")
    blocks: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    def _flush() -> None:
        nonlocal current_heading, current_body
        if current_heading is not None or any(line.strip() for line in current_body):
            blocks.append((current_heading, current_body[:]))
        current_heading = None
        current_body = []

    for raw_line in lines:
        line = raw_line.strip()
        if re.match(r"^###\s+", line):
            _flush()
            current_heading = line
            current_body = []
        else:
            current_body.append(line)
    _flush()

    if not blocks:
        return _linebreak_sentences(text)

    rendered: list[str] = []
    for heading, body_lines in blocks:
        body_text = " ".join(line for line in body_lines if line)
        body_text = re.sub(r"\b(?:Trigger|Process|Outcome|Variables)\s*:\s*", "", body_text, flags=re.IGNORECASE)
        body_text = _cleanup_label_artifacts(body_text, heading)
        compact_body = _linebreak_sentences(body_text)
        if heading:
            rendered.append(heading)
        if compact_body:
            rendered.append(compact_body)
        rendered.append("")

    return "\n".join(rendered).strip()


def _normalize_bullets(bullets: list[str], max_items: int = MAX_BULLETS_PER_PAGE) -> list[str]:
    compact: list[str] = []
    for bullet in bullets:
        if not isinstance(bullet, str):
            continue
        cleaned = _shorten_text(re.sub(r"^\s*[-*]\s*", "", bullet), MAX_BULLET_CHARS)
        if cleaned and cleaned not in compact:
            compact.append(cleaned)
        if len(compact) >= max_items:
            break
    return compact


def _trim_title(title: str, step: int) -> str:
    base = _soften_text(title)
    if not base or len(base) > 18 or base in LEGACY_STEP_TITLES:
        return DEFAULT_STEP_TITLES.get(step, "핵심 포인트")
    return base


def _extract_content_lines(content: str) -> list[str]:
    text = (content or "").replace("\r\n", "\n")
    lines: list[str] = []
    for line in text.split("\n"):
        cleaned = re.sub(r"^\s*(#{1,6}\s*|[-*]\s*|\d+[.)]\s*)", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _has_placeholder_heading(content: str) -> bool:
    text = str(content or "")
    for line in text.splitlines():
        for pattern in PLACEHOLDER_HEADING_PATTERNS:
            if re.match(pattern, line, flags=re.IGNORECASE):
                return True
    return False


def _contains_anchor(text: str, anchor: str) -> bool:
    if not anchor:
        return True
    return anchor.strip().lower() in str(text or "").lower()


def _contains_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _purpose_is_reflected(purpose: str, content: str) -> bool:
    purpose_clean = _soften_text(purpose)
    if not purpose_clean:
        return True

    content_lower = str(content or "").lower()
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", purpose_clean)
    if not tokens:
        return True
    checks = tokens[:3]
    return any(token.lower() in content_lower for token in checks)


def _align_content_with_purpose(purpose: str, content: str) -> str:
    text = _soften_text(content)
    purpose_clean = _shorten_text(purpose, 90)
    if not purpose_clean or _purpose_is_reflected(purpose_clean, text):
        return text
    return f"### 이 단계의 포인트\n{purpose_clean}\n\n{text}".strip()


def _inject_markdown_sections(step: int, content: str) -> str:
    text = _soften_text(content)
    if re.search(r"^\s*###\s+", text, flags=re.MULTILINE) and not _has_placeholder_heading(text):
        return text

    heading1, heading2 = DEFAULT_SECTION_HEADINGS.get(step, ("핵심 포인트", "체크 포인트"))
    if not text:
        text = "관련 내용을 정리 중이에요."

    lines = _extract_content_lines(text)
    if len(lines) >= 2:
        first = _shorten_text(lines[0])
        second = _shorten_text(" ".join(lines[1:3]))
    else:
        first = _shorten_text(text)
        second = "핵심 흐름을 짧게 나눠서 보면 더 쉽게 이해할 수 있어요."

    return f"### {heading1}\n{first}\n\n### {heading2}\n{second}"


def _normalize_summary_content(content: str, bullets: list[str]) -> str:
    collected: list[str] = []
    seen_norm: set[str] = set()
    heading_dup_phrases = ("투자 전에 꼭 확인할 포인트", "핵심 관찰 포인트")

    def _norm_key(text: str) -> str:
        no_tags = re.sub(r"<[^>]+>", "", str(text or ""))
        return re.sub(r"\s+", " ", no_tags).strip().lower()

    for item in bullets or []:
        if isinstance(item, str):
            cleaned = _shorten_text(item, MAX_BULLET_CHARS)
            if any(phrase in cleaned for phrase in heading_dup_phrases):
                continue
            norm = _norm_key(cleaned)
            if cleaned and norm and norm not in seen_norm:
                collected.append(cleaned)
                seen_norm.add(norm)

    for line in _extract_content_lines(content):
        softened = _shorten_text(line, MAX_BULLET_CHARS)
        if any(phrase in softened for phrase in heading_dup_phrases):
            continue
        norm = _norm_key(softened)
        if softened and norm and norm not in seen_norm:
            collected.append(softened)
            seen_norm.add(norm)
        if len(collected) >= 3:
            break

    defaults = [
        "핵심 지표가 같은 방향으로 움직이는지 확인해요.",
        "실적 가이던스 변화가 실제 수치로 이어지는지 체크해요.",
        "일정 지연이나 규제 변화 같은 변수 뉴스를 매일 확인해요.",
    ]
    for item in defaults:
        if len(collected) >= 3:
            break
        norm = _norm_key(item)
        if norm not in seen_norm:
            collected.append(item)
            seen_norm.add(norm)

    checklist = "\n".join(f"- {item}" for item in collected[:3])
    return f"### 투자 전에 꼭 확인할 포인트\n{checklist}"


def _normalize_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(pages, list):
        return []

    normalized: list[dict[str, Any]] = []

    for page in pages:
        if not isinstance(page, dict):
            continue
        current = dict(page)
        raw_step = current.get("step", 0)
        try:
            step = int(raw_step or 0)
        except (TypeError, ValueError):
            step = 0
        content = str(current.get("content", "") or "").strip()
        bullets = current.get("bullets", [])
        bullets = bullets if isinstance(bullets, list) else []
        bullets = _normalize_bullets([str(item) for item in bullets if str(item).strip()])
        current["bullets"] = bullets

        current["title"] = _trim_title(str(current.get("title", "") or ""), step)

        if step == 6:
            current["content"] = _normalize_summary_content(content, bullets)
            current["chart"] = None
        else:
            current["content"] = _compress_markdown_content(_inject_markdown_sections(step, content))

        normalized.append(current)

    return normalized


def _enforce_story_spine(pages: list[dict[str, Any]], raw_narrative: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(pages, list):
        return []

    concept = raw_narrative.get("concept") if isinstance(raw_narrative, dict) else {}
    historical_case = raw_narrative.get("historical_case") if isinstance(raw_narrative, dict) else {}

    concept_name = _soften_text(str((concept or {}).get("name", "") if isinstance(concept, dict) else ""))
    concept_definition = _soften_text(str((concept or {}).get("definition", "") if isinstance(concept, dict) else ""))
    concept_relevance = _soften_text(str((concept or {}).get("relevance", "") if isinstance(concept, dict) else ""))

    hist_period = _soften_text(str((historical_case or {}).get("period", "") if isinstance(historical_case, dict) else ""))
    hist_title = _soften_text(str((historical_case or {}).get("title", "") if isinstance(historical_case, dict) else ""))
    hist_summary = _soften_text(str((historical_case or {}).get("summary", "") if isinstance(historical_case, dict) else ""))

    enforced: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        current = dict(page)
        raw_step = current.get("step", 0)
        try:
            step = int(raw_step or 0)
        except (TypeError, ValueError):
            step = 0
        content = _soften_text(str(current.get("content", "") or ""))
        purpose = _soften_text(str(current.get("purpose", "") or ""))
        current["bullets"] = _normalize_bullets(
            [str(item) for item in (current.get("bullets", []) or []) if str(item).strip()]
        )

        if step in {1, 2, 3, 4, 5} and (not re.search(r"^\s*###\s+", content, flags=re.MULTILINE) or _has_placeholder_heading(content)):
            content = _inject_markdown_sections(step, content)

        if step in {1, 2, 3, 4, 5}:
            content = _align_content_with_purpose(purpose, content)

        if step == 2 and concept_name and not _contains_anchor(content, concept_name):
            if _contains_any_phrase(content, ("### 오늘 배울 개념", "오늘 배울 개념은")):
                current["content"] = content
                enforced.append(current)
                continue
            concept_lines = [f"오늘 배울 개념은 {concept_name}이에요."]
            if concept_definition:
                concept_lines.append(concept_definition)
            if concept_relevance:
                concept_lines.append(concept_relevance)
            concept_block = " ".join(line for line in concept_lines if line)
            content = f"### 오늘 배울 개념\n{concept_block}\n\n{content}".strip()

        if step == 3:
            has_period = bool(hist_period) and _contains_anchor(content, hist_period)
            has_title = bool(hist_title) and _contains_anchor(content, hist_title)
            if (hist_period or hist_title) and not (has_period or has_title):
                case_head = " ".join(part for part in [hist_period, hist_title] if part).strip()
                case_body = hist_summary or "같은 개념이 작동한 과거 사례를 먼저 확인해요."
                content = f"### 참고할 과거 사례\n{case_head}: {case_body}\n\n{content}".strip()

        if step == 4 and not (
            _contains_any_phrase(content, ("### 닮은 점", "닮은 점"))
            and _contains_any_phrase(content, ("### 다른 점", "다른 점"))
        ):
            lines = _extract_content_lines(content)
            similar = lines[0] if lines else "과거 사례와 닮은 흐름을 먼저 확인해요."
            different = " ".join(lines[1:3]) if len(lines) > 1 else "이번 국면의 다른 변수도 함께 확인해야 해요."
            content = f"### 닮은 점\n{similar}\n\n### 다른 점\n{different}".strip()

        if step == 6:
            bullets = current.get("bullets", [])
            bullets = bullets if isinstance(bullets, list) else []
            current["content"] = _normalize_summary_content(content, bullets)
            current["chart"] = None
        else:
            current["content"] = _compress_markdown_content(content)

        enforced.append(current)
    return enforced


# ────────────────────────────────────────────
# 1. run_theme — refined theme + one_liner
# ────────────────────────────────────────────

@traceable(name="run_theme", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "테마 생성", "step": 1})
def run_theme_node(state: dict) -> dict:
    """validated_interface_2 → refined theme/one_liner."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_theme")

    try:
        raw = state["raw_narrative"]
        backend = state.get("backend", "live")

        if backend == "mock":
            result = {"theme": raw["theme"], "one_liner": raw["one_liner"]}
        else:
            result = call_llm_with_prompt("3_theme", {
                "validated_interface_2": json.dumps(raw, ensure_ascii=False),
            })

        logger.info("  run_theme done: theme=%s", result.get("theme", "")[:50])
        return {
            "i3_theme": result,
            "metrics": _update_metrics(state, "run_theme", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  run_theme failed: %s", e, exc_info=True)
        return {
            "error": f"run_theme failed: {e}",
            "metrics": _update_metrics(state, "run_theme", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 2. run_pages — 6 pages (no chart)
# ────────────────────────────────────────────

@traceable(name="run_pages", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "페이지 생성", "step": 2})
def run_pages_node(state: dict) -> dict:
    """validated_interface_2 → 6 pages."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_pages")

    try:
        raw = state["raw_narrative"]
        backend = state.get("backend", "live")

        if backend == "mock":
            narrative = raw["narrative"]
            pages = []
            for step, title, section_key in SECTION_MAP:
                section = narrative[section_key]
                pages.append({
                    "step": step,
                    "title": title,
                    "purpose": section["purpose"],
                    "content": section["content"],
                    "bullets": section["bullets"][:2],
                })
            result = {"pages": pages}
        else:
            result = call_llm_with_prompt("3_pages", {
                "validated_interface_2": json.dumps(raw, ensure_ascii=False),
            })

        page_count = len(result.get("pages", []))
        logger.info("  run_pages done: %d pages", page_count)
        return {
            "i3_pages": result.get("pages", []),
            "metrics": _update_metrics(state, "run_pages", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  run_pages failed: %s", e, exc_info=True)
        return {
            "error": f"run_pages failed: {e}",
            "metrics": _update_metrics(state, "run_pages", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 3. run_hallcheck_pages — corrective hallcheck
# ────────────────────────────────────────────

@traceable(name="run_hallcheck_pages", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "페이지 검증", "step": 3})
def run_hallcheck_pages_node(state: dict) -> dict:
    """theme + pages 검증 → validated_theme/one_liner/pages 반환."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_hallcheck_pages")

    try:
        raw = state["raw_narrative"]
        i3_theme = state["i3_theme"]
        i3_pages = state["i3_pages"]
        backend = state.get("backend", "live")

        if backend == "mock":
            result = {
                "overall_risk": "low",
                "summary": "mock — 검증 미수행",
                "issues": [],
                "consistency_checks": [],
                "validated_theme": i3_theme.get("theme", raw["theme"]),
                "validated_one_liner": i3_theme.get("one_liner", raw["one_liner"]),
                "validated_pages": i3_pages,
            }
        else:
            result = call_llm_with_prompt("3_hallcheck_pages", {
                "validated_interface_2": json.dumps(raw, ensure_ascii=False),
                "theme_output": json.dumps(i3_theme, ensure_ascii=False),
                "pages_output": json.dumps(i3_pages, ensure_ascii=False),
            })

        risk = result.get("overall_risk", "unknown")
        issue_count = len(result.get("issues", []))
        logger.info("  run_hallcheck_pages done: risk=%s, issues=%d", risk, issue_count)

        return {
            "i3_validated": result,
            "metrics": _update_metrics(state, "run_hallcheck_pages", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  run_hallcheck_pages failed: %s", e, exc_info=True)
        return {
            "error": f"run_hallcheck_pages failed: {e}",
            "metrics": _update_metrics(state, "run_hallcheck_pages", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 3b. merge_theme_pages — hallcheck_pages 대체 (LLM 미호출)
# ────────────────────────────────────────────

def merge_theme_pages_node(state: dict) -> dict:
    """hallcheck_pages 대체: LLM 호출 없이 i3_validated 구성.

    validate_interface2에서 이미 수치/날짜 검증 완료.
    run_pages는 검증된 데이터 기반 서사 구성이므로 hallcheck 중복 제거.
    """
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] merge_theme_pages (lightweight, no LLM)")

    i3_theme = state["i3_theme"]
    i3_pages = state["i3_pages"]
    raw = state["raw_narrative"]

    return {
        "i3_validated": {
            "validated_theme": i3_theme.get("theme", raw["theme"]),
            "validated_one_liner": i3_theme.get("one_liner", raw["one_liner"]),
            "validated_pages": i3_pages,
        },
        "metrics": _update_metrics(state, "merge_theme_pages", time.time() - node_start),
    }


# ────────────────────────────────────────────
# 4. run_glossary — page_glossaries
# ────────────────────────────────────────────

@traceable(name="run_glossary", run_type="chain",
           metadata={"phase": "interface_3", "phase_name": "용어 생성", "step": 4})
def run_glossary_node(state: dict) -> dict:
    """validated_pages → term extraction → search → page_glossaries."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_glossary")

    try:
        raw = state["raw_narrative"]
        validated = state.get("i3_validated")
        if not validated:
            logger.warning("  run_glossary: i3_validated is None. Using raw i3_pages.")
            validated_pages = state.get("i3_pages", [])
        else:
            validated_pages = validated.get("validated_pages", [])
        backend = state.get("backend", "live")

        if backend == "mock":
            page_glossaries = []
            for step, _, section_key in SECTION_MAP:
                page_glossaries.append({
                    "step": step,
                    "glossary": [
                        {"term": f"용어-{section_key}", "definition": "mock 정의예요.", "domain": "일반"}
                    ],
                })
            return {
                "i3_glossaries": page_glossaries,
                "i3_glossary_search_context": "[Mock Search Results]",
                "metrics": _update_metrics(state, "run_glossary", time.time() - node_start),
            }

        # 1. Term Extraction
        extraction_result = call_llm_with_prompt("3_glossary_term_extraction", {
            "validated_pages": json.dumps(validated_pages, ensure_ascii=False),
        })
        terms_to_search = extraction_result.get("terms_to_search", [])
        logger.info("  Extracted %d terms to search.", len(terms_to_search))

        # 2. Web Search
        from ..ai.tools import search_web_for_chart_data

        search_results_text = ""
        if terms_to_search:
            unique_terms_map: dict[str, str] = {}
            for item in terms_to_search:
                term = item.get("term")
                context = item.get("context_sentence", "")
                if term and term not in unique_terms_map:
                    unique_terms_map[term] = context

            logger.info("  Searching for: %s", list(unique_terms_map.keys()))

            search_docs: list[str] = []
            for term, context in unique_terms_map.items():
                try:
                    if context:
                        query = f"주식 용어 {term} 뜻 의미 (문맥: {context})"
                    else:
                        query = f"주식 용어 {term} 뜻 의미"

                    search_output = search_web_for_chart_data.invoke(query)
                    search_docs.append(f"[{term}]\n(문맥: {context})\n{search_output}\n")
                except Exception as e:
                    logger.warning("  Search failed for %s: %s", term, e)

            search_results_text = "\n".join(search_docs)

        if not search_results_text:
            search_results_text = "(검색 결과 없음)"

        # 3. Glossary Generation (search_results 포함)
        result = call_llm_with_prompt("3_glossary", {
            "validated_interface_2": json.dumps(raw, ensure_ascii=False),
            "validated_pages": json.dumps(validated_pages, ensure_ascii=False),
            "search_results": search_results_text,
        })

        glossary_count = sum(
            len(pg.get("glossary", []))
            for pg in result.get("page_glossaries", [])
        )
        logger.info("  run_glossary done: %d terms across 6 pages", glossary_count)

        return {
            "i3_glossaries": result.get("page_glossaries", []),
            "i3_glossary_search_context": search_results_text,
            "metrics": _update_metrics(state, "run_glossary", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  run_glossary failed: %s", e, exc_info=True)
        return {
            "error": f"run_glossary failed: {e}",
            "metrics": _update_metrics(state, "run_glossary", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 5. run_hallcheck_glossary — validated_page_glossaries
# ────────────────────────────────────────────

@traceable(name="run_hallcheck_glossary", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "용어 검증", "step": 5})
def run_hallcheck_glossary_node(state: dict) -> dict:
    """page_glossaries 검증 → validated_page_glossaries 반환."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_hallcheck_glossary")

    try:
        raw = state["raw_narrative"]
        validated = state["i3_validated"]
        validated_pages = validated.get("validated_pages", [])
        i3_glossaries = state["i3_glossaries"]
        backend = state.get("backend", "live")

        if backend == "mock":
            result = {
                "overall_risk": "low",
                "summary": "mock — 검증 미수행",
                "issues": [],
                "validated_page_glossaries": i3_glossaries,
            }
        else:
            search_context = state.get("i3_glossary_search_context", "(검색 결과 없음)")
            result = call_llm_with_prompt("3_hallcheck_glossary", {
                "validated_interface_2": json.dumps(raw, ensure_ascii=False),
                "validated_pages": json.dumps(validated_pages, ensure_ascii=False),
                "page_glossaries": json.dumps(i3_glossaries, ensure_ascii=False),
                "search_results": search_context,
            })

        risk = result.get("overall_risk", "unknown")
        logger.info("  run_hallcheck_glossary done: risk=%s", risk)

        return {
            "i3_validated_glossaries": result.get("validated_page_glossaries", i3_glossaries),
            "metrics": _update_metrics(state, "run_hallcheck_glossary", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  run_hallcheck_glossary failed: %s", e, exc_info=True)
        return {
            "error": f"run_hallcheck_glossary failed: {e}",
            "metrics": _update_metrics(state, "run_hallcheck_glossary", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 6. run_tone_final — merge pages + glossaries, tone correction
# ────────────────────────────────────────────

@traceable(name="run_tone_final", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "톤 보정", "step": 6})
def run_tone_final_node(state: dict) -> dict:
    """validated pages + glossaries → final merged pages with tone correction."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_tone_final")

    try:
        validated = state["i3_validated"]
        validated_pages = validated.get("validated_pages", [])
        validated_theme = validated.get("validated_theme", "")
        validated_one_liner = validated.get("validated_one_liner", "")
        validated_glossaries = state["i3_validated_glossaries"]
        backend = state.get("backend", "live")

        if backend == "mock":
            glossary_map = {
                pg["step"]: pg.get("glossary", [])
                for pg in validated_glossaries
            }
            merged_pages = []
            for page in validated_pages:
                merged_page = dict(page)
                merged_page["glossary"] = glossary_map.get(page["step"], [])
                merged_pages.append(merged_page)

            result = {
                "interface_3_final_briefing": {
                    "theme": validated_theme,
                    "one_liner": validated_one_liner,
                    "pages": merged_pages,
                }
            }
        else:
            result = call_llm_with_prompt("3_tone_final", {
                "validated_theme": validated_theme,
                "validated_one_liner": validated_one_liner,
                "validated_pages": json.dumps(validated_pages, ensure_ascii=False),
                "validated_page_glossaries": json.dumps(validated_glossaries, ensure_ascii=False),
            })

        briefing = result.get("interface_3_final_briefing", {})
        normalized_pages = _normalize_pages(briefing.get("pages", []))
        normalized_pages = _enforce_story_spine(normalized_pages, state.get("raw_narrative", {}))
        page_count = len(normalized_pages)
        logger.info("  run_tone_final done: %d pages merged", page_count)

        return {
            "pages": normalized_pages,
            "theme": _soften_text(briefing.get("theme", validated_theme)),
            "one_liner": _soften_text(briefing.get("one_liner", validated_one_liner)),
            "metrics": _update_metrics(state, "run_tone_final", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  run_tone_final failed: %s", e, exc_info=True)
        return {
            "error": f"run_tone_final failed: {e}",
            "metrics": _update_metrics(state, "run_tone_final", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 7. run_home_icon_map — title/icon semantic mapping
# ────────────────────────────────────────────

@traceable(name="run_home_icon_map", run_type="llm",
           metadata={"phase": "interface_3", "phase_name": "홈 아이콘 매핑", "step": 7})
def run_home_icon_map_node(state: dict) -> dict:
    """theme/one_liner 기반 홈 카드 아이콘 key 선택."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] run_home_icon_map")

    fallback_icon = {"icon_key": DEFAULT_HOME_ICON_KEY}
    backend = state.get("backend", "live")
    theme = _soften_text(str(state.get("theme", "")))
    one_liner = _soften_text(str(state.get("one_liner", "")))

    if backend == "mock":
        logger.info("  run_home_icon_map done (mock): %s", DEFAULT_HOME_ICON_KEY)
        return {
            "home_icon": fallback_icon,
            "metrics": _update_metrics(state, "run_home_icon_map", time.time() - node_start),
        }

    try:
        payload = {
            "theme": theme,
            "one_liner": one_liner,
            "icon_candidates": json.dumps(HOME_ICON_CANDIDATES, ensure_ascii=False),
            "previous_icon_key": "",
        }
        result = call_llm_with_prompt("3_home_icon_map", payload)
        icon_key = _soften_text(str((result or {}).get("icon_key", "")))

        if icon_key not in HOME_ICON_KEYS:
            logger.warning(
                "  run_home_icon_map invalid icon_key=%s (1st pass), retrying once",
                icon_key or "<empty>",
            )
            retry_payload = dict(payload)
            retry_payload["previous_icon_key"] = icon_key
            retry_result = call_llm_with_prompt("3_home_icon_map", retry_payload)
            icon_key = _soften_text(str((retry_result or {}).get("icon_key", "")))

        if icon_key not in HOME_ICON_KEYS:
            raise ValueError(f"invalid icon_key after retry: {icon_key}")

        logger.info("  run_home_icon_map done: %s", icon_key)
        return {
            "home_icon": {"icon_key": icon_key},
            "metrics": _update_metrics(state, "run_home_icon_map", time.time() - node_start),
        }
    except Exception as e:
        logger.warning("  run_home_icon_map fallback: %s", e)
        return {
            "home_icon": fallback_icon,
            "metrics": _update_metrics(state, "run_home_icon_map", time.time() - node_start, "fallback"),
        }


# ────────────────────────────────────────────
# 9. collect_sources — deterministic
# ────────────────────────────────────────────

_STOPWORDS = frozenset({
    "하는", "있는", "이는", "했다", "한다", "되는", "이다", "에서", "으로", "부터",
    "까지", "하고", "그리고", "또한", "하며", "위해", "대한", "통해", "따르", "관련",
    "지난", "오전", "오후", "현재", "기준", "대비", "전날", "거래", "거래일",
})


def _extract_keywords(text: str) -> list[str]:
    """텍스트에서 핵심 키워드(2글자 이상 한글 단어) 추출."""
    words = re.findall(r"[가-힣]{2,}", text)
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]


@traceable(name="collect_sources", run_type="tool",
           metadata={"phase": "interface_3", "phase_name": "출처 수집", "step": 9})
def collect_sources_node(state: dict) -> dict:
    """출처 수집 (결정론적). chart_agent가 추가한 sources도 병합."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] collect_sources")

    try:
        curated = state["curated_context"]
        pages = state["pages"]

        # verified_news에서 출처 추출
        source_map: dict[str, dict] = {}
        for news in curated.get("verified_news", []):
            url = news.get("url", "")
            source_name = news.get("source", "")
            domain = url.split("//")[-1].split("/")[0] if "//" in url else url.split("/")[0]
            domain = domain.replace("www.", "")

            if source_name not in source_map:
                source_map[source_name] = {
                    "name": source_name,
                    "url_domain": domain,
                    "used_in_pages": [],
                }

        # 리포트에서 출처 추출
        for report in curated.get("reports", []):
            source_name = report.get("source", "")
            if source_name and source_name not in source_map:
                source_map[source_name] = {
                    "name": source_name,
                    "url_domain": "",
                    "used_in_pages": [],
                }

        # 소스별 키워드 추출
        source_keywords: dict[str, list[str]] = {}
        for news in curated.get("verified_news", []):
            sname = news.get("source", "")
            text = f"{news.get('title', '')} {news.get('summary', '')}"
            kws = _extract_keywords(text)
            if sname not in source_keywords:
                source_keywords[sname] = []
            source_keywords[sname].extend(kws)

        for report in curated.get("reports", []):
            sname = report.get("source", "")
            text = f"{report.get('title', '')} {report.get('summary', '')}"
            kws = _extract_keywords(text)
            if sname not in source_keywords:
                source_keywords[sname] = []
            source_keywords[sname].extend(kws)

        # 페이지별 출처 매칭 (키워드 기반)
        for page in pages:
            page_text = page.get("content", "") + " " + " ".join(page.get("bullets", []))
            for sname, sinfo in source_map.items():
                keywords = source_keywords.get(sname, [])
                match_count = sum(1 for kw in keywords if kw in page_text)
                if match_count >= 2 and page["step"] not in sinfo["used_in_pages"]:
                    sinfo["used_in_pages"].append(page["step"])

        # used_in_pages가 비어있으면 1페이지 배정
        sources = list(source_map.values())
        for s in sources:
            if not s["used_in_pages"]:
                s["used_in_pages"] = [1]

        # chart_agent가 추가한 sources 병합
        chart_sources = state.get("sources") or []
        for cs in chart_sources:
            existing = next((s for s in sources if s["name"] == cs.get("name")), None)
            if existing:
                for pg in cs.get("used_in_pages", []):
                    if pg not in existing["used_in_pages"]:
                        existing["used_in_pages"].append(pg)
            else:
                sources.append(cs)

        logger.info("  collect_sources done: %d sources", len(sources))
        return {
            "sources": sources,
            "metrics": _update_metrics(state, "collect_sources", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  collect_sources failed: %s", e, exc_info=True)
        return {
            "error": f"collect_sources failed: {e}",
            "metrics": _update_metrics(state, "collect_sources", time.time() - node_start, "failed"),
        }


# ────────────────────────────────────────────
# 10. assemble_output — Pydantic validation + JSON save
# ────────────────────────────────────────────

@traceable(name="assemble_output", run_type="tool",
           metadata={"phase": "interface_3", "phase_name": "최종 조립", "step": 10})
def assemble_output_node(state: dict) -> dict:
    """tone_final pages + charts 병합 → Pydantic 검증 → JSON 저장."""
    if state.get("error"):
        return {"error": state["error"]}

    node_start = time.time()
    logger.info("[Node] assemble_output")

    try:
        raw_narrative = state["raw_narrative"]
        curated = state["curated_context"]
        pages = state["pages"]
        charts = state.get("charts") or {}
        sources = state.get("sources", [])
        checklist = state.get("hallucination_checklist") or []
        home_icon = state.get("home_icon") or {"icon_key": DEFAULT_HOME_ICON_KEY}
        crawl_news_status = state.get("crawl_news_status")
        crawl_research_status = state.get("crawl_research_status")
        theme = state.get("theme", raw_narrative["theme"])
        one_liner = state.get("one_liner", raw_narrative["one_liner"])

        # charts를 pages에 병합
        for page in pages:
            step = page["step"]
            if step == 6:
                page["chart"] = None
                continue
            section_key = next(
                (sk for s, _, sk in SECTION_MAP if s == step), None
            )
            if section_key and charts.get(section_key):
                page["chart"] = charts[section_key]
            elif "chart" not in page:
                page["chart"] = None

            # glossary 스키마 안정화: LLM이 null을 주더라도 문자열로 보정
            glossary_items = page.get("glossary")
            if isinstance(glossary_items, list):
                normalized_glossary = []
                for item in glossary_items:
                    if not isinstance(item, dict):
                        continue
                    term = str(item.get("term") or "").strip()
                    definition = str(item.get("definition") or "").strip()
                    domain = str(item.get("domain") or "").strip()
                    if not term:
                        continue
                    normalized_glossary.append({
                        "term": term,
                        "definition": definition,
                        "domain": domain,
                    })
                page["glossary"] = normalized_glossary

        # FinalBriefing 조립
        final_briefing_data = {
            "theme": theme,
            "one_liner": one_liner,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "pages": pages,
            "home_icon": home_icon,
            "sources": sources,
            "hallucination_checklist": checklist,
        }
        data_collection_status = None
        if isinstance(crawl_news_status, dict) or isinstance(crawl_research_status, dict):
            data_collection_status = {
                "crawl_news": crawl_news_status if isinstance(crawl_news_status, dict) else None,
                "crawl_research": crawl_research_status if isinstance(crawl_research_status, dict) else None,
            }

        # Pydantic 검증
        output = FullBriefingOutput(
            topic=theme,
            interface_1_curated_context=CuratedContext.model_validate(curated),
            interface_2_raw_narrative=RawNarrative.model_validate(raw_narrative),
            interface_3_final_briefing=FinalBriefing.model_validate(final_briefing_data),
            data_collection_status=data_collection_status,
        )

        # 파일 저장
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"briefing_{timestamp}.json"
        output_path.write_text(
            json.dumps(output.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info("  assemble_output done: %s", output_path)
        return {
            "full_output": output.model_dump(),
            "output_path": str(output_path),
            "metrics": _update_metrics(state, "assemble_output", time.time() - node_start),
        }

    except Exception as e:
        logger.error("  assemble_output failed: %s", e, exc_info=True)
        return {
            "error": f"assemble_output failed: {e}",
            "metrics": _update_metrics(state, "assemble_output", time.time() - node_start, "failed"),
        }
