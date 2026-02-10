"""파이프라인 오케스트레이터 - 실험용.

RSS 뉴스 수집 -> 키워드 추출 -> 다양성 필터 -> 리서치(병렬)
-> 스토리 생성 -> 용어집 -> (선택) DB 저장

전체 파이프라인을 오케스트레이션하고, asyncio.gather로 병렬 처리한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pipeline.ai_service import AIPipelineService
from pipeline.config import PipelineConfig
from pipeline.diversity import pick_diverse_keyword_plans
from pipeline.rss_service import RSSService
from pipeline.types import KeywordPlan, PipelineResult, ScenarioResult

LOGGER = logging.getLogger(__name__)

# 기본 관련 기업 목록 (폴백)
DEFAULT_RELATED_COMPANIES = [
    {
        "name": "삼성전자",
        "code": "005930",
        "reason": "시장 대표주",
    }
]


class PipelineGenerator:
    """브리핑 생성 파이프라인 오케스트레이터 (실험용).

    DB 의존성을 제거하고, 결과를 JSON 파일로도 저장 가능.
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        ai_service: AIPipelineService | None = None,
        rss_service: RSSService | None = None,
    ) -> None:
        self.config = config or PipelineConfig()
        self.ai_service = ai_service or AIPipelineService(self.config)
        self.rss_service = rss_service or RSSService()

    async def generate(
        self,
        target_date: date | None = None,
        save_json: bool = True,
    ) -> PipelineResult:
        """전체 파이프라인 실행.

        Args:
            target_date: 대상 날짜 (기본: 오늘 KST)
            save_json: True면 결과를 JSON 파일로 저장
        """
        run_started = time.perf_counter()
        today = target_date or self._kst_today()
        result = PipelineResult(date=str(today))

        LOGGER.info("=" * 60)
        LOGGER.info("[1/6] 파이프라인 시작: %s", today)

        # [2/6] RSS 뉴스 수집
        LOGGER.info("[2/6] RSS 뉴스 수집 중...")
        rss_text = await self.rss_service.fetch_top_news()
        LOGGER.info("  수집된 텍스트: %d자", len(rss_text))

        if not rss_text.strip():
            result.errors.append("RSS 뉴스를 수집하지 못했어요.")
            return result

        # [3/6] 키워드 추출 + 다양성 필터
        LOGGER.info("[3/6] 키워드 추출 + 다양성 필터...")
        candidates = await self.ai_service.extract_top_keywords(
            rss_text, candidate_count=self.config.keyword_candidate_count,
        )
        keyword_plans = pick_diverse_keyword_plans(
            candidates, self.config.target_scenario_count,
        )

        if not keyword_plans:
            result.errors.append("키워드를 추출하지 못했어요.")
            return result

        LOGGER.info("  선택된 키워드: %s", [p.keyword for p in keyword_plans])

        # [4/6] 시나리오 병렬 생성
        LOGGER.info("[4/6] %d개 시나리오 병렬 생성...", len(keyword_plans))
        scenario_tasks = [
            self._build_scenario(plan, idx, len(keyword_plans))
            for idx, plan in enumerate(keyword_plans, start=1)
        ]
        scenario_results = await asyncio.gather(*scenario_tasks, return_exceptions=True)

        scenarios: list[dict[str, Any]] = []
        for i, res in enumerate(scenario_results):
            if isinstance(res, Exception):
                LOGGER.error("[시나리오 %d] 실패: %s", i + 1, res)
                result.errors.append(f"시나리오 {i + 1} 실패: {res}")
            else:
                scenarios.append(res)

        if not scenarios:
            result.errors.append("모든 시나리오 생성이 실패했어요.")
            return result

        LOGGER.info("  성공: %d/%d 시나리오", len(scenarios), len(keyword_plans))

        # [5/6] 용어집 생성
        LOGGER.info("[5/6] 용어집 생성...")
        terms = self._extract_terms(scenarios)
        glossary = await self.ai_service.generate_glossary(terms)
        result.glossary = glossary

        # ScenarioResult로 변환
        for scenario_data in scenarios:
            result.scenarios.append(ScenarioResult(
                keyword=scenario_data.get("keyword", ""),
                title=scenario_data.get("title", ""),
                summary=scenario_data.get("summary", ""),
                narrative=scenario_data.get("narrative", {}),
                sources=scenario_data.get("sources", []),
                related_companies=scenario_data.get("related_companies", []),
                mirroring_data=scenario_data.get("mirroring_data", {}),
                glossary=glossary,
            ))

        # [6/6] 결과 저장
        elapsed = time.perf_counter() - run_started
        result.elapsed_seconds = elapsed
        LOGGER.info("[6/6] 파이프라인 완료: %.2fs, %d개 시나리오", elapsed, len(result.scenarios))

        if save_json:
            self._save_to_json(result, today)

        LOGGER.info("=" * 60)
        return result

    async def _build_scenario(
        self, plan: KeywordPlan, idx: int, total: int,
    ) -> dict[str, Any]:
        """단일 시나리오: 리서치(병렬) -> 스토리 생성."""
        LOGGER.info("  [시나리오 %d/%d] %s", idx, total, plan.keyword)

        # 리서치 병렬 실행
        ctx_task = self.ai_service.research_context(plan.keyword, plan.mirroring_hint)
        sim_task = self.ai_service.research_simulation(plan.keyword, plan.mirroring_hint)
        (ctx_research, ctx_citations), (sim_research, sim_citations) = await asyncio.gather(
            ctx_task, sim_task,
        )

        # 스토리 생성
        narrative = await self.ai_service.generate_story(
            theme=plan.keyword,
            context_research=ctx_research,
            simulation_research=sim_research,
            mirroring_hint=plan.mirroring_hint,
        )

        # 인용 병합
        all_citations: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for cite in ctx_citations + sim_citations:
            url = cite.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_citations.append(cite)

        return {
            "keyword": plan.keyword,
            "title": plan.title or plan.keyword,
            "summary": self._safe_intro(narrative),
            "sources": all_citations[:5] or [{"name": "RSS Feed", "url": "#"}],
            "narrative": narrative,
            "related_companies": DEFAULT_RELATED_COMPANIES,
            "mirroring_data": {
                "target_event": plan.mirroring_hint or "과거 금융 사례",
            },
        }

    def _save_to_json(self, result: PipelineResult, target_date: date) -> None:
        """결과를 JSON 파일로 저장."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"briefing_{target_date}.json"

        import dataclasses
        data = dataclasses.asdict(result)
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("결과 저장: %s", filepath)

    @staticmethod
    def _safe_intro(narrative: dict) -> str:
        """배경 섹션에서 요약 텍스트 추출."""
        bg = narrative.get("background") if isinstance(narrative, dict) else None
        if isinstance(bg, dict):
            return str(bg.get("content") or "내용을 요약할 수 없어요.")
        return "내용을 요약할 수 없어요."

    @staticmethod
    def _extract_terms(scenarios: list[dict]) -> list[str]:
        """시나리오에서 <mark class='term'> 태그 내 용어 추출."""
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
        return [term for term in matches if not (term in seen or seen.add(term))]

    @staticmethod
    def _kst_today() -> date:
        """현재 KST 날짜."""
        kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
        return kst_now.date()
