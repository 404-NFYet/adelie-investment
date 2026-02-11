"""8단계 AI 에이전트 오케스트레이터.

adelie_fe_test/pipeline/ai_service.py에서 이식.
OpenRouterClient -> MultiProviderClient로 교체.
프롬프트 로더를 통한 마크다운 기반 프롬프트 사용.
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any

from ..prompts import load_prompt
from ..services.multi_provider_client import MultiProviderClient, get_multi_provider_client
from .types import KeywordPlan

LOGGER = logging.getLogger(__name__)

# 7단계 내러티브 섹션
NARRATIVE_SECTIONS = [
    "background", "mirroring", "difference", "devils_advocate",
    "simulation", "result", "action",
]


def _extract_content(result: dict[str, Any], fallback: str = "") -> str:
    """API 응답에서 텍스트 콘텐츠 추출."""
    try:
        return result["choices"][0]["message"]["content"] or fallback
    except (KeyError, IndexError, TypeError):
        return fallback


def _extract_json(raw: str, start: str, end: str) -> str:
    """JSON 조각 추출."""
    s = raw.find(start)
    e = raw.rfind(end)
    if s != -1 and e != -1 and s <= e:
        return raw[s:e + 1]
    return raw


def _safe_json(raw: str, default: Any) -> Any:
    """안전한 JSON 파싱."""
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


class PipelineAIService:
    """8단계 내러티브 파이프라인 AI 서비스."""

    def __init__(self, client: MultiProviderClient | None = None, dry_run: bool = False):
        self.client = client or get_multi_provider_client()
        self.dry_run = dry_run

    def _call_prompt(self, name: str, **kwargs: str) -> dict[str, Any]:
        """마크다운 프롬프트 로드 -> 프로바이더 호출."""
        spec = load_prompt(name, **kwargs)

        messages: list[dict[str, str]] = []
        if spec.system_message:
            messages.append({"role": "system", "content": spec.system_message})
        messages.append({"role": "user", "content": spec.body})

        return self.client.chat_completion(
            provider=spec.provider,
            model=spec.model,
            messages=messages,
            thinking=spec.thinking,
            thinking_effort=spec.thinking_effort,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            response_format={"type": spec.response_format} if spec.response_format else None,
        )

    # ── 1. 키워드 추출 ──

    def extract_top_keywords(
        self,
        rss_text: str,
        candidate_count: int = 8,
        avoid_keywords: list[str] | None = None,
    ) -> list[KeywordPlan]:
        """RSS 헤드라인에서 투자 테마 키워드 추출."""
        if self.dry_run:
            return self._dry_run_keywords()

        avoid_section = ""
        if avoid_keywords:
            avoid_section = "[재생성 제약]\n금지 키워드: " + ", ".join(avoid_keywords)

        result = self._call_prompt(
            "keyword_extraction",
            count=str(max(6, min(12, candidate_count))),
            avoid_section=avoid_section,
            rss_text=rss_text[:8000],
        )

        content = _extract_content(result, "[]")
        parsed = _safe_json(_extract_json(content, "[", "]"), [])
        if not isinstance(parsed, list):
            parsed = [parsed]

        output: list[KeywordPlan] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            keyword = str(item.get("keyword", "")).strip()
            context = str(item.get("context", "")).strip()
            if not keyword or not context:
                continue
            output.append(KeywordPlan(
                category=str(item.get("category", "Market trend")),
                domain=str(item.get("domain", "macro")),
                keyword=keyword,
                title=str(item.get("title", keyword)),
                context=context,
                mirroring_hint=str(item.get("mirroringHint", "")),
            ))
        return output

    # ── 2a. 배경 리서치 ──

    def research_context(self, keyword: str, mirroring_hint: str = "") -> str:
        """배경 + 과거 사례 + 차이점 + 반대 시나리오 리서치."""
        if self.dry_run:
            return f"{keyword} 관련 배경 리서치 (dry-run)"

        result = self._call_prompt(
            "research_context",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        return _extract_content(result, "맥락 리서치 실패")

    # ── 2b. 시뮬레이션 리서치 ──

    def research_simulation(self, keyword: str, mirroring_hint: str = "") -> str:
        """과거 가격 데이터 + 모의투자 시뮬레이션 리서치."""
        if self.dry_run:
            return f"{keyword} 관련 시뮬레이션 리서치 (dry-run)"

        result = self._call_prompt(
            "research_simulation",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        return _extract_content(result, "시뮬레이션 리서치 실패")

    # ── 3~6. 스토리 생성 ──

    def generate_story(
        self, theme: str, context_research: str, simulation_research: str,
        mirroring_hint: str = "",
    ) -> dict[str, Any]:
        """3. Planner -> 4. Writer -> 5. Reviewer -> 6. Tone Corrector."""
        if self.dry_run:
            return self._dry_run_story(theme)

        # 3. 기획
        plan_result = self._call_prompt(
            "planner",
            theme=theme,
            mirroring_hint=mirroring_hint,
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        plan = _safe_json(_extract_json(_extract_content(plan_result, "{}"), "{", "}"), {})

        # 4. 작성 (Claude)
        draft_result = self._call_prompt(
            "writer",
            theme=theme,
            mirroring_hint=mirroring_hint,
            plan=json.dumps(plan, ensure_ascii=False),
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        draft = _safe_json(_extract_json(_extract_content(draft_result, "{}"), "{", "}"), {})

        # 5. 검수
        review_result = self._call_prompt("reviewer", draft=json.dumps(draft, ensure_ascii=False))
        reviewed = _safe_json(_extract_json(_extract_content(review_result, "{}"), "{", "}"), draft)

        # 6. 톤 교정
        tone_corrected = self._correct_tone(reviewed)

        return self._ensure_narrative_shape(tone_corrected, theme)

    def _correct_tone(self, narrative: dict[str, Any]) -> dict[str, Any]:
        """톤 교정 에이전트."""
        contents = []
        for section in NARRATIVE_SECTIONS:
            data = narrative.get(section)
            if isinstance(data, dict) and data.get("content"):
                contents.append(f"[{section}]: {data['content']}")

        if not contents:
            return narrative

        try:
            result = self._call_prompt("tone_corrector", sections_text="\n".join(contents))
            parsed = _safe_json(_extract_json(_extract_content(result, "{}"), "{", "}"), {})
            if isinstance(parsed, dict):
                for section, corrected in parsed.items():
                    if section in narrative and isinstance(narrative[section], dict) and isinstance(corrected, str):
                        narrative[section]["content"] = corrected
            return narrative
        except Exception as exc:
            LOGGER.warning("톤 교정 실패, 원본 유지: %s", exc)
            return narrative

    # ── 7. 용어 사전 ──

    def generate_glossary(self, terms: list[str]) -> dict[str, str]:
        """용어 정의 일괄 생성."""
        if not terms:
            return {}
        if self.dry_run:
            return {t: f"{t}은(는) 테스트용 설명이에요." for t in terms}

        result = self._call_prompt("glossary", terms=", ".join(terms))
        parsed = _safe_json(_extract_json(_extract_content(result, "{}"), "{", "}"), {})
        if isinstance(parsed, dict) and parsed:
            return {str(k): str(v) for k, v in parsed.items()}
        return {t: f"{t}은(는) 투자할 때 꼭 알아야 할 핵심 개념이에요." for t in terms[:5]}

    # ── 용어 추출 + sanitization (adelie_fe_test 패턴) ──

    @staticmethod
    def extract_terms(scenarios: list[dict] | dict) -> list[str]:
        """생성된 내러티브에서 <mark class='term'>용어</mark> 태그의 용어를 추출."""
        import re
        pattern = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")
        matches: list[str] = []

        def walk(node: object) -> None:
            if isinstance(node, str):
                matches.extend(pattern.findall(node))
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, dict):
                for value in node.values():
                    walk(value)

        walk(scenarios)

        seen: set[str] = set()
        ordered: list[str] = []
        for term in matches:
            t = term.strip()
            if t and t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered

    @staticmethod
    def sanitize_marks(text: str, allowed_terms: set[str]) -> str:
        """사전에 정의되지 않은 용어의 <mark> 태그를 제거."""
        import re
        pattern = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")

        def replace(match):
            term = match.group(1).strip()
            if allowed_terms and term in allowed_terms:
                return f"<mark class='term'>{term}</mark>"
            return term

        return pattern.sub(replace, text)

    def sanitize_narrative_with_glossary(self, narrative: dict[str, Any], glossary: dict[str, str]) -> dict[str, Any]:
        """내러티브에서 용어 사전에 없는 마크 태그를 제거."""
        allowed = set(glossary.keys())
        output = {}
        for key, value in narrative.items():
            if isinstance(value, dict):
                sanitized = {}
                for k, v in value.items():
                    if isinstance(v, str):
                        sanitized[k] = self.sanitize_marks(v, allowed)
                    elif isinstance(v, list):
                        sanitized[k] = [self.sanitize_marks(item, allowed) if isinstance(item, str) else item for item in v]
                    else:
                        sanitized[k] = v
                output[key] = sanitized
            else:
                output[key] = value
        return output

    # ── 후처리 ──

    def _ensure_narrative_shape(self, narrative: dict[str, Any], theme: str) -> dict[str, Any]:
        """7단계 구조 보장."""
        output: dict[str, Any] = {}
        for idx, section in enumerate(NARRATIVE_SECTIONS, start=1):
            raw = narrative.get(section)
            data = raw if isinstance(raw, dict) else {}
            content = str(data.get("content", f"{theme} 관련 내용을 정리했어요.")).strip()
            bullets = [str(b).strip() for b in (data.get("bullets") or []) if str(b).strip()]

            if section == "devils_advocate":
                bullets = bullets[:3]
                while len(bullets) < 3:
                    bullets.append(f"{theme} 관련 반대 시나리오")
            else:
                bullets = bullets[:2]
                if not bullets:
                    bullets = [f"{theme} 핵심 흐름", f"{theme} 체크 포인트"]

            chart = data.get("chart") if isinstance(data.get("chart"), dict) else {}
            if not chart.get("data"):
                chart = {
                    "data": [{"x": ["2020", "2021", "2022", "2023", "2024"],
                              "y": [idx + 8, idx + 10, idx + 9, idx + 12, idx + 13],
                              "type": "scatter", "name": section.title()}],
                    "layout": {"title": section.replace("_", " ").title()},
                }

            output[section] = {"content": content, "bullets": bullets, "chart": chart}
        return output

    # ── dry-run ──

    @staticmethod
    def _dry_run_keywords() -> list[KeywordPlan]:
        return [
            KeywordPlan("Macro", "macro", "미국 금리", "금리의 방향", "금리가 자산시장에 미치는 영향", "1995년 연착륙"),
            KeywordPlan("Tech", "technology", "AI 투자", "AI 사이클 점검", "AI 투자 사이클", "닷컴 버블"),
            KeywordPlan("Energy", "energy", "국제 유가", "유가 인플레이션", "유가 경로 재점검", "1970 오일쇼크"),
        ]

    @staticmethod
    def _dry_run_story(theme: str) -> dict[str, Any]:
        def _chart(name: str, base: int) -> dict:
            return {
                "data": [{"x": ["2020", "2021", "2022", "2023", "2024"],
                          "y": [base, base + 2, base + 1, base + 3, base + 4],
                          "type": "scatter", "name": name}],
                "layout": {"title": f"{name} 추이"},
            }
        return {
            s: {
                "content": f"{theme} 관련 {s} 내용이에요.",
                "bullets": [f"{theme} 포인트1", f"{theme} 포인트2"] + ([f"{theme} 포인트3"] if s == "devils_advocate" else []),
                "chart": _chart(s, 10 + i),
            }
            for i, s in enumerate(NARRATIVE_SECTIONS)
        }
