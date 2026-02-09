"""AI Service - Keyword extraction, research, and story generation pipeline."""
from __future__ import annotations

import json as _json
import logging
import random
import re
from typing import Any

from .llm_client import (
    LLMClient,
    extract_citations,
    extract_json_fragment,
    extract_message_content,
    safe_load_json,
)
from .prompt_loader import load_prompt
from .types import KeywordPlan


LOGGER = logging.getLogger(__name__)
MARK_PATTERN = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")

# 7-step narrative sections - 순서 변경됨: (1,2,5,6,3,4,7)
# background, mirroring, simulation, result, difference, devils_advocate, action
NARRATIVE_SECTIONS = [
    "background",
    "mirroring",
    "simulation",
    "result",
    "difference",
    "devils_advocate",
    "action",
]


class AIService:
    """AI Service for narrative generation pipeline."""

    def __init__(
        self,
        client: LLMClient,
        keyword_model: str,
        research_model: str,
        planner_model: str,
        story_model: str,
        reviewer_model: str,
        glossary_model: str,
        tone_model: str = "",
        prompts_dir: str = "",
        dry_run: bool = False,
    ) -> None:
        self.client = client
        self.models = {
            "keyword_model": keyword_model,
            "research_model": research_model,
            "planner_model": planner_model,
            "story_model": story_model,
            "reviewer_model": reviewer_model,
            "glossary_model": glossary_model,
            "tone_model": tone_model or glossary_model,
        }
        self.prompts_dir = prompts_dir or ""
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self, model_key: str) -> str:
        """Resolve a model_key (from frontmatter) to actual model name."""
        return self.models.get(model_key, self.models.get("keyword_model", ""))

    def _load(self, name: str, **kwargs: str) -> Any:
        """Load prompt and return PromptSpec."""
        loader_kwargs: dict[str, Any] = {}
        if self.prompts_dir:
            loader_kwargs["prompts_dir"] = self.prompts_dir
        return load_prompt(name, **loader_kwargs, **kwargs)

    def _call_prompt(self, name: str, **kwargs: str) -> dict[str, Any]:
        """Load a prompt template, resolve model, and call appropriate LLM API."""
        spec = self._load(name, **kwargs)
        model_key = spec.model_key
        model = self._get_model(model_key)

        messages: list[dict[str, str]] = []
        if spec.system_message:
            messages.append({"role": "system", "content": spec.system_message})
        messages.append({"role": "user", "content": spec.body})

        # Route to appropriate API based on model
        if model_key == "research_model" or model.startswith("sonar"):
            # Perplexity
            return self.client.call_perplexity(
                messages=messages,
                model=model,
                temperature=spec.temperature,
            )
        elif model_key == "story_model" or "claude" in model.lower():
            # Claude
            return self.client.call_claude(
                model=model,
                messages=messages,
                temperature=spec.temperature,
            )
        else:
            # OpenAI (default)
            response_format = None
            if spec.response_format:
                response_format = {"type": spec.response_format}
            return self.client.call_openai(
                model=model,
                messages=messages,
                temperature=spec.temperature,
                response_format=response_format,
            )

    async def _async_call_prompt(self, name: str, **kwargs: str) -> dict[str, Any]:
        """Async version of _call_prompt."""
        spec = self._load(name, **kwargs)
        model_key = spec.model_key
        model = self._get_model(model_key)

        messages: list[dict[str, str]] = []
        if spec.system_message:
            messages.append({"role": "system", "content": spec.system_message})
        messages.append({"role": "user", "content": spec.body})

        # Route to appropriate API based on model
        if model_key == "research_model" or model.startswith("sonar"):
            # Perplexity
            return await self.client.async_call_perplexity(
                messages=messages,
                model=model,
                temperature=spec.temperature,
            )
        elif model_key == "story_model" or "claude" in model.lower():
            # Claude
            return await self.client.async_call_claude(
                model=model,
                messages=messages,
                temperature=spec.temperature,
            )
        else:
            # OpenAI (default)
            response_format = None
            if spec.response_format:
                response_format = {"type": spec.response_format}
            return await self.client.async_call_openai(
                model=model,
                messages=messages,
                temperature=spec.temperature,
                response_format=response_format,
            )

    # ------------------------------------------------------------------
    # Keyword extraction
    # ------------------------------------------------------------------

    def extract_top_keywords(
        self,
        rss_text: str,
        candidate_count: int = 8,
        avoid_keywords: list[str] | None = None,
        avoid_categories: list[str] | None = None,
        avoid_mirroring_hints: list[str] | None = None,
    ) -> list[KeywordPlan]:
        """Extract top keywords from RSS text."""
        if self.dry_run:
            return self._dry_run_keywords(rss_text)

        avoid_keywords = avoid_keywords or []
        avoid_categories = avoid_categories or []
        avoid_mirroring_hints = avoid_mirroring_hints or []

        avoid_lines = []
        if avoid_keywords:
            avoid_lines.append("- 금지 Keyword: " + ", ".join(avoid_keywords))
        if avoid_categories:
            avoid_lines.append("- 금지 Category: " + ", ".join(avoid_categories))
        if avoid_mirroring_hints:
            avoid_lines.append("- 금지 Mirroring Hint: " + ", ".join(avoid_mirroring_hints))
        avoid_guideline = "\n".join(avoid_lines)
        avoid_section = "[재생성 제약 - 반드시 준수]\n" + avoid_guideline if avoid_guideline else ""

        result = self._call_prompt(
            "keyword_extraction",
            count=str(max(6, min(12, candidate_count))),
            avoid_section=avoid_section,
            rss_text=rss_text[:8000],
        )
        content = extract_message_content(result, "[]")
        json_text = extract_json_fragment(content, "[", "]")
        parsed = safe_load_json(json_text, [])
        if not isinstance(parsed, list):
            parsed = [parsed]

        output: list[KeywordPlan] = []
        for item in parsed:
            category = str(item.get("category", "Market trend")).strip() or "Market trend"
            domain = str(item.get("domain", "macro")).strip().lower().replace(" ", "_") or "macro"
            keyword = str(item.get("keyword", "")).strip()
            title = str(item.get("title", "")).strip()
            context = str(item.get("context", "")).strip()
            hint = str(item.get("mirroringHint", "")).strip()
            if not keyword or not context:
                continue
            if not title or len(title) < 8 or title.upper() == "AI":
                title = "[" + keyword + "] 시장이 주목하는 핵심 포인트"
            title = re.sub(r"^\[.*?\]\s*", "", title).strip()

            output.append(
                KeywordPlan(
                    category=category,
                    domain=domain,
                    keyword=keyword,
                    title=title,
                    context=context,
                    mirroring_hint=hint,
                )
            )
        return output

    # ------------------------------------------------------------------
    # Research: 2-stage
    # ------------------------------------------------------------------

    def deep_dive_keyword(self, keyword: str, mirroring_hint: str = "") -> str:
        """Legacy single-call research (kept for backward compatibility)."""
        if self.dry_run:
            return keyword + " 관련 최근 동향과 과거 사례를 비교한 더미 리서치 결과입니다."

        query = (
            keyword + "와 관련하여 " + mirroring_hint + "의 관점에서 심층 분석하고 최신 동향과 과거 사례의 공통점을 요약해주세요."
            if mirroring_hint
            else keyword + "에 대해 심층 분석하고 최신 시장 동향을 요약해주세요."
        )

        result = self._call_prompt("deep_dive", query=query)
        return extract_message_content(result, "상세 분석 실패")

    def research_context(self, keyword: str, mirroring_hint: str = "") -> tuple[str, list[dict[str, str]]]:
        """Research stage 1: background + historical case + differences + contrarian views.

        Returns:
            Tuple of (research_text, citations_list)
        """
        if self.dry_run:
            return (
                keyword + " 관련 현재 배경, " + (mirroring_hint or "과거 사례")
                + " 비교, 차이점, 반대 시나리오를 포함한 더미 리서치입니다.",
                [],
            )

        result = self._call_prompt(
            "research_context",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        text = extract_message_content(result, "맥락 리서치 실패")
        citations = extract_citations(result)
        return text, citations

    def research_simulation(self, keyword: str, mirroring_hint: str = "") -> tuple[str, list[dict[str, str]]]:
        """Research stage 2: historical price data + simulation scenarios.

        Returns:
            Tuple of (research_text, citations_list)
        """
        if self.dry_run:
            return (
                keyword + " 관련 과거 가격 데이터, 모의 투자 시뮬레이션, "
                "투자 전략을 포함한 더미 리서치입니다.",
                [],
            )

        result = self._call_prompt(
            "research_simulation",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        text = extract_message_content(result, "시뮬레이션 리서치 실패")
        citations = extract_citations(result)
        return text, citations

    # ------------------------------------------------------------------
    # Story generation pipeline
    # ------------------------------------------------------------------

    def generate_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        mirroring_hint: str = "",
    ) -> dict:
        """Generate 7-step narrative story."""
        if self.dry_run:
            return self._dry_run_story(theme)

        plan = self._plan_story(theme, context_research, simulation_research, mirroring_hint)
        draft = self._write_story(theme, context_research, simulation_research, plan, mirroring_hint)
        reviewed = self._review_story(theme, draft)
        tone_corrected = self._correct_tone(reviewed)
        marked = self._enrich_marks(tone_corrected)
        return self._ensure_narrative_shape(marked, theme)

    def _plan_story(
        self, theme: str, context_research: str, simulation_research: str, mirroring_hint: str,
    ) -> dict[str, Any]:
        result = self._call_prompt(
            "planner",
            theme=theme,
            mirroring_hint=mirroring_hint,
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        raw = extract_json_fragment(extract_message_content(result, "{}"), "{", "}")
        parsed = safe_load_json(raw, {})
        return parsed if isinstance(parsed, dict) else {}

    def _write_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        plan: dict[str, Any],
        mirroring_hint: str,
    ) -> dict[str, Any]:
        result = self._call_prompt(
            "writer",
            theme=theme,
            mirroring_hint=mirroring_hint,
            plan=str(plan),
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        raw = extract_json_fragment(extract_message_content(result, "{}"), "{", "}")
        parsed = safe_load_json(raw, {})
        if not isinstance(parsed, dict):
            raise RuntimeError("Story draft is invalid for theme: " + theme)
        return parsed

    def _review_story(self, theme: str, draft: dict[str, Any]) -> dict[str, Any]:
        result = self._call_prompt("reviewer", draft=str(draft))
        raw = extract_json_fragment(extract_message_content(result, "{}"), "{", "}")
        parsed = safe_load_json(raw, {})
        if not isinstance(parsed, dict):
            raise RuntimeError("Story review is invalid for theme: " + theme)
        return parsed

    def _correct_tone(self, narrative: dict[str, Any]) -> dict[str, Any]:
        """AI tone correction layer."""
        if self.dry_run:
            return narrative

        contents_to_fix: list[tuple[str, str]] = []
        for section in NARRATIVE_SECTIONS:
            sec_data = narrative.get(section)
            if isinstance(sec_data, dict):
                content = sec_data.get("content", "")
                if content:
                    contents_to_fix.append((section, content))

        if not contents_to_fix:
            return narrative

        sections_text = "\n".join(
            "[" + section + "]: " + content for section, content in contents_to_fix
        )

        try:
            result = self._call_prompt("tone_corrector", sections_text=sections_text)
            raw = extract_json_fragment(extract_message_content(result, "{}"), "{", "}")
            parsed = safe_load_json(raw, {})

            if isinstance(parsed, dict):
                for section, corrected in parsed.items():
                    if section in narrative and isinstance(narrative[section], dict) and isinstance(corrected, str):
                        narrative[section]["content"] = corrected
                LOGGER.info("[TONE] Successfully corrected tone for %d sections", len(parsed))
            return narrative
        except Exception as exc:
            LOGGER.warning("[TONE] Tone correction failed, using original: %s", exc)
            return narrative

    def _enrich_marks(self, narrative: dict[str, Any]) -> dict[str, Any]:
        """Post-tone-correction marker enrichment layer."""
        if self.dry_run:
            return narrative

        # Build a compact JSON of only content/bullets for each section
        slim: dict[str, Any] = {}
        for section in NARRATIVE_SECTIONS:
            sec_data = narrative.get(section)
            if isinstance(sec_data, dict):
                slim[section] = {
                    "content": sec_data.get("content", ""),
                    "bullets": sec_data.get("bullets", []),
                }

        if not slim:
            return narrative

        try:
            result = self._call_prompt(
                "marker",
                narrative_json=_json.dumps(slim, ensure_ascii=False),
            )
            raw = extract_json_fragment(extract_message_content(result, "{}"), "{", "}")
            parsed = safe_load_json(raw, {})

            if isinstance(parsed, dict):
                applied = 0
                for section in NARRATIVE_SECTIONS:
                    enriched = parsed.get(section)
                    if not isinstance(enriched, dict):
                        continue
                    original = narrative.get(section)
                    if not isinstance(original, dict):
                        continue
                    enriched_content = enriched.get("content")
                    if isinstance(enriched_content, str) and enriched_content.strip():
                        original["content"] = enriched_content
                    enriched_bullets = enriched.get("bullets")
                    if isinstance(enriched_bullets, list) and enriched_bullets:
                        original["bullets"] = enriched_bullets
                    applied += 1
                LOGGER.info("[MARKER] Enriched marks for %d sections", applied)
            return narrative
        except Exception as exc:
            LOGGER.warning("[MARKER] Mark enrichment failed, using original: %s", exc)
            return narrative

    # ------------------------------------------------------------------
    # Glossary
    # ------------------------------------------------------------------

    def generate_batch_definitions(self, terms: list[str]) -> dict[str, str]:
        """Generate glossary definitions for terms."""
        if not terms:
            return {}
        if self.dry_run:
            return {term: term + "은(는) 테스트용 더미 설명입니다." for term in terms}

        result = self._call_prompt("glossary", terms=", ".join(terms))
        raw = extract_message_content(result, "{}")
        raw = extract_json_fragment(raw, "{", "}")
        parsed = safe_load_json(raw, {})
        if isinstance(parsed, dict) and parsed:
            return {str(key): str(value) for key, value in parsed.items()}
        if terms:
            fallback_terms = terms[:5]
            return {term: term + "은(는) 시장을 볼 때 꼭 체크할 핵심 개념이에요." for term in fallback_terms}
        return {}

    # ------------------------------------------------------------------
    # Post-processing utilities
    # ------------------------------------------------------------------

    def _ensure_narrative_shape(self, narrative: dict[str, Any], theme: str) -> dict[str, Any]:
        output: dict[str, Any] = {}

        for idx, section in enumerate(NARRATIVE_SECTIONS, start=1):
            raw = narrative.get(section)
            data = raw if isinstance(raw, dict) else {}
            content = str(data.get("content") or (theme + " 관련 핵심 내용을 쉽게 정리했어요.")).strip()
            raw_bullets = data.get("bullets")
            bullets_source: list[Any] = raw_bullets if isinstance(raw_bullets, list) else []
            bullets = [str(item).strip() for item in bullets_source if str(item).strip()]

            if section == "devils_advocate":
                bullets = bullets[:3]
                while len(bullets) < 3:
                    bullets.append(theme + " 관련 반대 시나리오")
            else:
                bullets = bullets[:2]
                if not bullets:
                    bullets = [theme + " 핵심 흐름", theme + " 체크 포인트"]

            raw_chart = data.get("chart")
            chart: dict[str, Any] = raw_chart if isinstance(raw_chart, dict) else {}
            section_output: dict[str, Any] = {
                "content": self._ensure_mark_presence(self._to_friendly_tone(self._shorten_content(content)), theme),
                "bullets": bullets,
                "chart": self._ensure_chart(chart, section, idx),
            }

            # Validate quiz field for simulation section
            if section == "simulation":
                raw_quiz = data.get("quiz")
                quiz = self._ensure_quiz(raw_quiz, theme) if isinstance(raw_quiz, dict) else self._fallback_quiz(theme)
                section_output["quiz"] = quiz

            output[section] = section_output

        return output

    @staticmethod
    def _shorten_content(content: str) -> str:
        normalized = re.sub(r"\s+", " ", content).strip()
        if not normalized:
            return "핵심만 쉽게 정리해드릴게요."
        sentences = re.split(r"(?<=[.!?다요죠])\s+", normalized)
        filtered = [sentence.strip() for sentence in sentences if sentence.strip()]
        return " ".join(filtered[:3])

    @staticmethod
    def _ensure_mark_presence(content: str, theme: str) -> str:
        if MARK_PATTERN.search(content):
            return content
        candidates = [token for token in re.split(r"[\s\-_/]+", theme) if len(token.strip()) >= 2]
        if not candidates:
            return content
        term = candidates[0].strip()
        return "<mark class='term'>" + term + "</mark> " + content

    @staticmethod
    def _to_friendly_tone(content: str) -> str:
        replacements = {
            "합니다.": "해요.",
            "있습니다.": "있어요.",
            "됩니다.": "돼요.",
            "보입니다.": "보여요.",
            "필요합니다.": "필요해요.",
            "중요합니다.": "중요해요.",
            "의미합니다.": "의미해요.",
            "나타납니다.": "나타나요.",
            "예상됩니다.": "예상돼요.",
            "전망됩니다.": "전망이에요.",
            "분석됩니다.": "분석돼요.",
        }
        updated = content
        for source, target in replacements.items():
            updated = updated.replace(source, target)
        return updated

    @staticmethod
    def _ensure_quiz(raw_quiz: dict[str, Any], theme: str) -> dict[str, Any]:
        """Validate and normalize quiz data from AI output."""
        context = str(raw_quiz.get("context") or theme + " 관련 과거 사례가 있었어요.").strip()
        question = str(raw_quiz.get("question") or "이 상황에서 시장은 어떻게 움직였을까요?").strip()
        correct_answer = str(raw_quiz.get("correct_answer", "up")).strip()
        actual_result = str(raw_quiz.get("actual_result") or "구체적 결과 데이터를 확인할 수 없었어요.").strip()
        lesson = str(raw_quiz.get("lesson") or "과거 사례와 현재 상황을 함께 고려하며 투자 결정을 내려야 해요.").strip()

        # Validate correct_answer
        if correct_answer not in ("up", "down", "sideways"):
            correct_answer = "up"

        # Validate options
        raw_options = raw_quiz.get("options")
        default_options = [
            {"id": "up", "label": "올랐어요", "explanation": theme + " 이슈로 시장이 상승했을 거예요."},
            {"id": "down", "label": "내렸어요", "explanation": theme + " 이슈로 시장이 하락했을 거예요."},
            {"id": "sideways", "label": "횡보했어요", "explanation": theme + " 이슈에도 시장은 큰 변동이 없었을 거예요."},
        ]

        if isinstance(raw_options, list) and len(raw_options) >= 3:
            options = []
            for opt in raw_options[:3]:
                if isinstance(opt, dict):
                    options.append({
                        "id": str(opt.get("id", "")).strip() or default_options[len(options)]["id"],
                        "label": str(opt.get("label", "")).strip() or default_options[len(options)]["label"],
                        "explanation": str(opt.get("explanation", "")).strip() or default_options[len(options)]["explanation"],
                    })
                else:
                    options.append(default_options[len(options)])
        else:
            options = default_options

        return {
            "context": context,
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "actual_result": actual_result,
            "lesson": lesson,
        }

    @staticmethod
    def _fallback_quiz(theme: str) -> dict[str, Any]:
        """Generate a fallback quiz when AI doesn't produce one."""
        return {
            "context": theme + "과(와) 유사한 상황이 과거에도 있었어요.",
            "question": "이 상황에서 시장은 어떻게 움직였을까요?",
            "options": [
                {"id": "up", "label": "올랐어요", "explanation": "긍정적 요인이 더 크게 작용해서 시장이 상승했을 거예요."},
                {"id": "down", "label": "내렸어요", "explanation": "불확실성이 커지며 시장이 하락했을 거예요."},
                {"id": "sideways", "label": "횡보했어요", "explanation": "상승과 하락 요인이 팽팽해서 큰 변동이 없었을 거예요."},
            ],
            "correct_answer": "up",
            "actual_result": "실제로는 단기 변동 후 점차 안정을 찾아갔어요.",
            "lesson": "과거 사례가 항상 반복되지는 않아요. 현재 상황만의 고유한 요인을 함께 고려해야 해요.",
        }

    @staticmethod
    def _ensure_chart(chart: dict[str, Any], section: str, seed: int) -> dict[str, Any]:
        raw_data = chart.get("data")
        data: list[Any] = raw_data if isinstance(raw_data, list) else []
        raw_layout = chart.get("layout")
        layout: dict[str, Any] = raw_layout if isinstance(raw_layout, dict) else {}

        valid_trace = False
        if data:
            trace = data[0]
            if isinstance(trace, dict):
                x_values = trace.get("x")
                y_values = trace.get("y")
                if isinstance(x_values, list) and isinstance(y_values, list):
                    if len(x_values) > 0 and len(x_values) == len(y_values):
                        valid_trace = True

        if not valid_trace:
            years = ["2020", "2021", "2022", "2023", "2024"]
            values = [seed + 8, seed + 10, seed + 9, seed + 12, seed + 13]
            data = [{"x": years, "y": values, "type": "scatter", "name": section.title()}]

        if "title" not in layout:
            section_titles = {
                "background": "현재 시장 배경",
                "mirroring": "과거 유사 사례",
                "simulation": "모의 투자 시뮬레이션",
                "result": "시뮬레이션 결과",
                "difference": "과거 vs 현재",
                "devils_advocate": "반대 시나리오 분석",
                "action": "투자 액션 플랜",
            }
            layout = {**layout, "title": section_titles.get(section, section.title() + " Insight")}

        return {"data": data, "layout": layout}

    @staticmethod
    def calculate_similarity() -> dict[str, str | int]:
        return {
            "score": random.randint(65, 85),
            "reasoning_log": "현재 시장의 추세와 과거의 특정 지점이 높은 유사성을 보이고 있습니다.",
        }

    # ------------------------------------------------------------------
    # Async methods for parallel execution
    # ------------------------------------------------------------------

    async def async_research_context(self, keyword: str, mirroring_hint: str = "") -> tuple[str, list[dict[str, str]]]:
        """Async research stage 1."""
        if self.dry_run:
            return (
                keyword + " 관련 현재 배경, " + (mirroring_hint or "과거 사례")
                + " 비교, 차이점, 반대 시나리오를 포함한 더미 리서치입니다.",
                [],
            )

        result = await self._async_call_prompt(
            "research_context",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        text = extract_message_content(result, "맥락 리서치 실패")
        citations = extract_citations(result)
        return text, citations

    async def async_research_simulation(self, keyword: str, mirroring_hint: str = "") -> tuple[str, list[dict[str, str]]]:
        """Async research stage 2."""
        if self.dry_run:
            return (
                keyword + " 관련 과거 가격 데이터, 모의 투자 시뮬레이션, "
                "투자 전략을 포함한 더미 리서치입니다.",
                [],
            )

        result = await self._async_call_prompt(
            "research_simulation",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        text = extract_message_content(result, "시뮬레이션 리서치 실패")
        citations = extract_citations(result)
        return text, citations

    async def async_generate_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        mirroring_hint: str = "",
    ) -> dict:
        """Async version of generate_story. Internal steps remain sync (CPU-bound)."""
        if self.dry_run:
            return self._dry_run_story(theme)

        plan = self._plan_story(theme, context_research, simulation_research, mirroring_hint)
        draft = self._write_story(theme, context_research, simulation_research, plan, mirroring_hint)
        reviewed = self._review_story(theme, draft)
        tone_corrected = self._correct_tone(reviewed)
        marked = self._enrich_marks(tone_corrected)
        return self._ensure_narrative_shape(marked, theme)

    # ------------------------------------------------------------------
    # Dry-run stubs
    # ------------------------------------------------------------------

    @staticmethod
    def _dry_run_keywords(rss_text: str) -> list[KeywordPlan]:
        base_items = [line for line in rss_text.split("\n") if line.strip()][:10]
        seed = [
            ("Macro Economy", "fixed_income", "미국 국채 금리", "금리의 방향이 자산시장에 미치는 영향", "1995년 연착륙"),
            ("Energy & Environment", "energy", "국제 유가", "유가와 인플레이션 경로 재점검", "1970년대 오일쇼크"),
            ("Policy & Strategy", "policy", "중앙은행 통화정책", "통화정책 전환 시그널 분석", "2018 긴축 전환기"),
            ("Technology", "technology", "AI 인프라 투자", "AI 투자 사이클의 지속성 점검", "닷컴 버블"),
        ]
        output: list[KeywordPlan] = []
        for idx, item in enumerate(seed):
            context = base_items[idx] if idx < len(base_items) else item[3]
            output.append(
                KeywordPlan(
                    category=item[0], domain=item[1], keyword=item[2],
                    title="[" + item[2] + "] 오늘의 핵심 포인트",
                    context=context, mirroring_hint=item[4],
                )
            )
        return output

    @staticmethod
    def _dry_run_story(theme: str) -> dict:
        return {
            "background": {
                "bullets": ["현재 시장 상황", "주요 이슈"],
                "content": "지금 " + theme + " 이슈가 뜨거운 이유, 쉽게 정리해드릴게요.",
                "chart": {
                    "data": [{"x": ["2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12"],
                              "y": [3.2, 3.5, 3.1, 3.8, 4.0, 4.2],
                              "type": "scatter", "mode": "lines+markers", "name": theme + " 지표", "line": {"width": 3}}],
                    "layout": {"title": "최근 6개월 " + theme + " 추이", "xaxis": {"title": "기간"}, "yaxis": {"title": "지표값"}},
                },
            },
            "mirroring": {
                "bullets": ["과거 사례 비교", "유사 패턴"],
                "content": "과거에도 " + theme + "과(와) 비슷한 상황이 있었어요.",
                "chart": {
                    "data": [
                        {"x": ["T-5", "T-4", "T-3", "T-2", "T-1", "T"],
                         "y": [100, 105, 98, 110, 115, 108],
                         "type": "scatter", "mode": "lines+markers", "name": "2008년 사례", "line": {"width": 2}},
                        {"x": ["T-5", "T-4", "T-3", "T-2", "T-1", "T"],
                         "y": [100, 103, 97, 108, 112, 106],
                         "type": "scatter", "mode": "lines+markers", "name": "2024년 현재", "line": {"width": 2}},
                    ],
                    "layout": {"title": "과거 vs 현재 패턴 비교", "xaxis": {"title": "상대 시점"}, "yaxis": {"title": "지수 (기준=100)"},
                               "showlegend": True, "legend": {"orientation": "h", "y": -0.25}},
                },
            },
            "simulation": {
                "bullets": ["모의 투자 조건", "시뮬레이션 결과"],
                "content": "과거 " + theme + " 사례로 1000만 원을 투자했다면 어떻게 됐을까요?",
                "chart": {
                    "data": [
                        {"x": ["시작", "3개월", "6개월", "9개월", "12개월"],
                         "y": [1000, 1050, 980, 1120, 1180],
                         "type": "scatter", "mode": "lines+markers", "name": "자산 변화 (만원)", "line": {"width": 3}},
                        {"x": ["낙관", "중립", "비관"],
                         "y": [18, 8, -12],
                         "type": "bar", "name": "수익률 (%)",
                         "text": ["+18%", "+8%", "-12%"], "textposition": "outside"},
                    ],
                    "layout": {"title": "1,000만원 투자 시뮬레이션 (12개월)", "xaxis": {"title": "기간 / 시나리오"},
                               "yaxis": {"title": "가치 (만원) / 수익률 (%)"},
                               "showlegend": True, "legend": {"orientation": "h", "y": -0.25}},
                },
                "quiz": {
                    "context": "2008년에도 " + theme + "과(와) 유사한 시장 상황이 있었어요. 당시 중앙은행이 급격히 금리를 인상하면서 시장에 충격을 줬죠.",
                    "question": "이 상황에서 이후 12개월간 시장은 어떻게 움직였을까요?",
                    "options": [
                        {"id": "up", "label": "올랐어요", "explanation": "위기 이후 대규모 부양책이 시행되면서 V자 반등이 나타났어요."},
                        {"id": "down", "label": "내렸어요", "explanation": "금리 인상의 여파가 실물경제에 전이되면서 추가 하락했어요."},
                        {"id": "sideways", "label": "횡보했어요", "explanation": "상승과 하락 요인이 팽팽하게 대립하며 큰 변동 없이 횡보했어요."},
                    ],
                    "correct_answer": "up",
                    "actual_result": "실제로 12개월 후 시장은 약 18% 상승했어요. 초기 3개월은 추가 하락이 있었지만, 이후 강력한 부양책이 시행되면서 빠르게 회복했어요.",
                    "lesson": "과거에는 부양책 규모가 매우 컸지만, 현재는 인플레이션 우려로 같은 수준의 부양이 어려울 수 있어요. 회복 속도가 다를 수 있다는 점을 고려해야 해요.",
                },
            },
            "result": {
                "bullets": ["수익률 분석", "시사점"],
                "content": "시뮬레이션 결과, 이런 인사이트를 얻을 수 있었어요.",
                "chart": {
                    "data": [{"x": ["최적", "평균", "최악"],
                              "y": [18, 8, -12],
                              "type": "bar", "name": "수익률 (%)",
                              "text": ["+18% (1,180만원)", "+8% (1,080만원)", "-12% (880만원)"],
                              "textposition": "outside",
                              "marker": {"color": ["#4CAF50", "#2196F3", "#F44336"]}}],
                    "layout": {"title": "시나리오별 수익률 요약 (1,000만원 기준)", "xaxis": {"title": "시나리오"}, "yaxis": {"title": "수익률 (%)"}},
                },
            },
            "difference": {
                "bullets": ["핵심 차이점", "달라진 환경"],
                "content": "그때와 지금은 이런 점이 달라요.",
                "chart": {
                    "data": [
                        {"x": ["금리", "인플레이션", "고용률"], "y": [5.25, 8.5, 4.2], "type": "bar", "name": "과거"},
                        {"x": ["금리", "인플레이션", "고용률"], "y": [4.5, 3.2, 3.8], "type": "bar", "name": "현재"},
                    ],
                    "layout": {"title": "핵심 지표 비교", "xaxis": {"title": "항목"}, "yaxis": {"title": "%"},
                               "barmode": "group", "showlegend": True, "legend": {"orientation": "h", "y": -0.25}},
                },
            },
            "devils_advocate": {
                "bullets": [
                    "반대 시나리오 1: 예상과 다른 방향으로 흘러갈 수 있어요",
                    "반대 시나리오 2: 외부 충격 가능성이 있어요",
                    "반대 시나리오 3: 시장이 이미 반영했을 수 있어요",
                ],
                "content": theme + "에 대해 반대로 생각해볼 포인트 세 가지를 준비했어요.",
                "chart": {
                    "data": [{"x": ["급격한 긴축", "지정학 리스크", "이미 반영"],
                              "y": [-15, -22, -5],
                              "type": "bar", "name": "하락률 (%)",
                              "text": ["확률 20%", "확률 10%", "확률 35%"], "textposition": "outside"}],
                    "layout": {"title": "반대 시나리오별 예상 하락률", "xaxis": {"title": "시나리오"}, "yaxis": {"title": "하락률 (%)"}},
                },
            },
            "action": {
                "bullets": ["실전 체크리스트", "투자 전략"],
                "content": "자, 이제 진짜 투자해볼까요? 핵심 전략을 정리했어요.",
                "chart": {
                    "data": [{"x": ["국내 주식", "미국 주식", "채권", "현금성"],
                              "y": [35, 30, 25, 10],
                              "type": "bar", "name": "포트폴리오 비중 (%)"}],
                    "layout": {"title": "추천 포트폴리오 구성 (%)", "xaxis": {"title": "자산"}, "yaxis": {"title": "비중 (%)"}},
                },
            },
        }
