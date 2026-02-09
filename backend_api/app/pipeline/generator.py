"""Briefing Generator - Main orchestrator for narrative generation pipeline."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .ai_service import AIService, NARRATIVE_SECTIONS
from .config import PipelineConfig
from .diversity import pick_diverse_keyword_plans
from .llm_client import LLMClient
from .rss_service import RSSService
from .types import KeywordPlan


LOGGER = logging.getLogger(__name__)


class BriefingGenerator:
    """Main generator class that orchestrates the briefing generation pipeline."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        
        # Initialize LLM client
        self.llm_client = LLMClient(
            openai_api_key=config.openai_api_key,
            perplexity_api_key=config.perplexity_api_key,
            anthropic_api_key=config.anthropic_api_key,
        )
        
        # Initialize RSS service
        self.rss_service = RSSService(feeds=config.rss_feeds)
        
        # Initialize AI service
        self.ai_service = AIService(
            client=self.llm_client,
            keyword_model=config.keyword_model,
            research_model=config.research_model,
            planner_model=config.planner_model,
            story_model=config.story_model,
            reviewer_model=config.reviewer_model,
            glossary_model=config.glossary_model,
            tone_model=config.tone_model,
            prompts_dir=config.prompts_dir,
            dry_run=config.dry_run,
        )

    def run(self) -> dict:
        """Synchronous entry point — delegates to async_run() for parallel scenarios."""
        return asyncio.run(self.async_run())

    async def _build_scenario(self, plan: KeywordPlan, idx: int, total: int) -> dict:
        """Build a single scenario (research + story generation), async-capable."""
        scenario_started = time.perf_counter()
        LOGGER.info("[SCENARIO %d/%d] keyword=%s start", idx, total, plan.keyword)

        # Run both research stages in parallel
        LOGGER.info("[SCENARIO %d/%d] Parallel research (context + simulation)", idx, total)
        ctx_task = self.ai_service.async_research_context(plan.keyword, plan.mirroring_hint)
        sim_task = self.ai_service.async_research_simulation(plan.keyword, plan.mirroring_hint)
        (ctx_research, ctx_citations), (sim_research, sim_citations) = await asyncio.gather(ctx_task, sim_task)

        LOGGER.info("[SCENARIO %d/%d] Story generation", idx, total)
        narrative = await self.ai_service.async_generate_story(
            theme=plan.keyword,
            context_research=ctx_research,
            simulation_research=sim_research,
            mirroring_hint=plan.mirroring_hint,
        )
        similarity = self.ai_service.calculate_similarity()

        # Merge citations from both research stages, deduplicate by URL
        all_citations: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for cite in ctx_citations + sim_citations:
            url = cite.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_citations.append(cite)
        sources = all_citations[:5] if all_citations else [{"name": "RSS Feed", "url": "#"}]

        result = {
            "id": str(uuid4()),
            "title": plan.title or plan.keyword,
            "summary": self._safe_intro_content(narrative),
            "sources": sources,
            "narrative": narrative,
            "related_companies": self.config.default_related_companies,
            "mirroring_data": {
                "target_event": plan.mirroring_hint or "과거 금융 사례",
                "year": 0,
                "reasoning_log": similarity["reasoning_log"],
            },
            "sort_order": idx - 1,  # 0-indexed for DB
        }
        LOGGER.info(
            "[SCENARIO %d/%d] keyword=%s done elapsed=%.2fs",
            idx,
            total,
            plan.keyword,
            time.perf_counter() - scenario_started,
        )
        return result

    async def async_run(self) -> dict:
        """Main async pipeline — scenarios are built in parallel using asyncio.gather."""
        run_started = time.perf_counter()
        LOGGER.info("[1/7] Starting daily briefing generation (async)")
        today_date = self._kst_today()
        now_iso = self._kst_now_iso()

        LOGGER.info("[2/7] Generating new briefing for date=%s", today_date)

        LOGGER.info("[3/7] Fetching RSS news")
        rss_text = self.rss_service.fetch_top_news()
        LOGGER.info("RSS payload collected chars=%d", len(rss_text))

        LOGGER.info("[4/7] Extracting keyword candidates and applying diversity gate")
        candidates = self.ai_service.extract_top_keywords(rss_text, candidate_count=8)
        keyword_plans = pick_diverse_keyword_plans(candidates, self.config.target_scenario_count)

        if len(keyword_plans) < self.config.target_scenario_count:
            LOGGER.info("Diversity gate selected too few items. Retrying with avoid-lists.")
            retry_candidates = self.ai_service.extract_top_keywords(
                rss_text,
                candidate_count=10,
                avoid_keywords=[plan.keyword for plan in candidates],
                avoid_categories=[plan.category for plan in candidates],
                avoid_mirroring_hints=[plan.mirroring_hint for plan in candidates if plan.mirroring_hint],
            )
            keyword_plans = pick_diverse_keyword_plans(
                candidates + retry_candidates,
                self.config.target_scenario_count,
            )

        # Handle case where we have fewer plans than target
        actual_count = min(len(keyword_plans), self.config.target_scenario_count)
        if actual_count < self.config.target_scenario_count:
            LOGGER.warning(
                "Could only generate %d keyword plans (target: %d)",
                actual_count,
                self.config.target_scenario_count,
            )

        LOGGER.info("Keywords selected: %s", [plan.keyword for plan in keyword_plans[:actual_count]])
        LOGGER.info("[5/7] Generating scenarios in PARALLEL count=%d", actual_count)

        # Build all scenarios concurrently
        scenario_tasks = [
            self._build_scenario(plan, idx, actual_count)
            for idx, plan in enumerate(keyword_plans[:actual_count], start=1)
        ]
        scenarios = list(await asyncio.gather(*scenario_tasks))

        LOGGER.info("[6/7] Extracting glossary terms and generating definitions")
        glossary = self.ai_service.generate_batch_definitions(self._extract_terms(scenarios))
        scenarios = self._sanitize_scenarios_with_glossary(scenarios, glossary)
        
        # Use datetime-based id for uniqueness across same-day reruns
        briefing_id = "briefing_" + now_iso.replace(":", "-").replace("+", "p")
        briefing_data = {
            "id": briefing_id,
            "date": today_date,
            "datetime": now_iso,
            "main_keywords": [plan.keyword for plan in keyword_plans[:actual_count]],
            "scenarios": scenarios,
            "glossary": glossary,
        }

        LOGGER.info("[7/7] Briefing generation complete total_elapsed=%.2fs", time.perf_counter() - run_started)
        return briefing_data

    @staticmethod
    def _kst_now_iso() -> str:
        """Return current KST time as ISO 8601 string with timezone."""
        kst = timezone(timedelta(hours=9))
        return datetime.now(kst).isoformat(timespec="seconds")

    @staticmethod
    def _kst_today() -> str:
        """Return current KST date as YYYY-MM-DD (used for duplicate check)."""
        kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
        return kst_now.date().isoformat()

    @staticmethod
    def _safe_intro_content(narrative: dict) -> str:
        background = narrative.get("background") if isinstance(narrative, dict) else None
        if isinstance(background, dict):
            return str(background.get("content") or "내용을 요약할 수 없어요.")
        return "내용을 요약할 수 없어요."

    @staticmethod
    def _extract_terms(scenarios: list[dict]) -> list[str]:
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
            if term not in seen:
                seen.add(term)
                ordered.append(term)
        return ordered

    @staticmethod
    def _sanitize_scenarios_with_glossary(scenarios: list[dict], glossary: dict[str, str]) -> list[dict]:
        """Ensure only terms in glossary are marked."""
        allowed_terms = {term.strip() for term in glossary.keys() if term.strip()}
        sanitized = deepcopy(scenarios)
        for scenario in sanitized:
            narrative = scenario.get("narrative")
            if not isinstance(narrative, dict):
                continue

            for section_name in NARRATIVE_SECTIONS:
                section = narrative.get(section_name)
                if not isinstance(section, dict):
                    continue

                content = section.get("content")
                if isinstance(content, str):
                    section["content"] = BriefingGenerator._sanitize_marks(content, allowed_terms)

                bullets = section.get("bullets")
                if isinstance(bullets, list):
                    section["bullets"] = [
                        BriefingGenerator._sanitize_marks(str(item), allowed_terms) for item in bullets
                    ]

            summary = scenario.get("summary")
            if isinstance(summary, str):
                scenario["summary"] = BriefingGenerator._sanitize_marks(summary, allowed_terms)

        return sanitized

    @staticmethod
    def _sanitize_marks(text: str, allowed_terms: set[str]) -> str:
        """Remove marks for terms not in allowed set."""
        pattern = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")

        def replace(match: re.Match[str]) -> str:
            term = match.group(1).strip()
            if allowed_terms and term in allowed_terms:
                return f"<mark class='term'>{term}</mark>"
            return term

        return pattern.sub(replace, text)
