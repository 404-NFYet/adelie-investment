"""Briefing Generator - 내러티브 브리핑 생성 파이프라인 (DEPRECATED).

⚠️ DEPRECATED: 이 파일은 더 이상 사용되지 않습니다.
현재는 scripts/keyword_pipeline_graph.py (LangGraph 기반)를 사용합니다.

기존 파이프라인: RSS 뉴스 수집 -> 키워드 추출 -> 다양성 필터 -> 리서치(병렬) -> 스토리 생성 -> 용어집 -> DB 저장
현재 파이프라인: keyword_pipeline_graph.py (Perplexity 기반 카탈리스트 검색)
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid as uuid_mod
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.narrative import DailyNarrative, NarrativeScenario
from app.services.ai_pipeline_service import (
    AIPipelineService,
    KeywordPlan,
    get_ai_pipeline_service,
)
# REMOVED: RSS 기반 뉴스 수집 (Perplexity로 대체됨)
# from app.services.rss_service import RSSService, get_rss_service

LOGGER = logging.getLogger(__name__)

# 기본 관련 기업 목록 (폴백)
DEFAULT_RELATED_COMPANIES = [
    {
        "name": "삼성전자",
        "code": "005930",
        "reason": "시장 대표주",
        "latest_disclosure": "분기보고서",
        "disclosure_url": "#",
    }
]


# ──────────────────────────────────────────────
# 다양성 필터 (Diversity Gate)
# ──────────────────────────────────────────────


def _normalize_text(value: str) -> str:
    """텍스트 정규화: 소문자, 특수문자 제거."""
    text = value.lower().strip()
    text = re.sub(r"^\[.*?\]\s*", "", text)
    text = re.sub(r"[\"'`]", "", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(value: str) -> set[str]:
    """텍스트를 2자 이상 토큰으로 분리."""
    return {token for token in _normalize_text(value).split(" ") if len(token) >= 2}


def _character_ngrams(value: str, n: int = 3) -> set[str]:
    """문자 n-gram 생성."""
    compact = re.sub(r"\s+", "", _normalize_text(value))
    return {compact[i : i + n] for i in range(0, max(0, len(compact) - n + 1))}


def _jaccard(left: set[str], right: set[str]) -> float:
    """자카드 유사도 계산."""
    if not left or not right:
        return 0.0
    intersection = len(left.intersection(right))
    return intersection / (len(left) + len(right) - intersection)


def _overlap_score(a: KeywordPlan, b: KeywordPlan) -> float:
    """두 키워드 플랜 사이의 중복 점수 계산.

    토큰 유사도, 문자 n-gram 유사도, 키워드 포함관계를 종합한다.
    """
    text_a = f"{a.keyword} {a.title} {a.context} {a.mirroring_hint}"
    text_b = f"{b.keyword} {b.title} {b.context} {b.mirroring_hint}"

    token_score = _jaccard(_tokenize(text_a), _tokenize(text_b))
    char_score = _jaccard(_character_ngrams(text_a), _character_ngrams(text_b))

    keyword_a = _normalize_text(a.keyword)
    keyword_b = _normalize_text(b.keyword)
    containment = (
        0.15
        if keyword_a and keyword_b and (keyword_a in keyword_b or keyword_b in keyword_a)
        else 0.0
    )

    return max(token_score, char_score) + containment


def pick_diverse_keyword_plans(
    plans: list[KeywordPlan],
    target_count: int,
) -> list[KeywordPlan]:
    """다양성 필터를 적용하여 키워드 플랜 선택.

    1차: 키워드/도메인/카테고리/힌트 중복 없이 엄격 선택
    2차: 부족한 경우 유사도 임계값만으로 완화 선택

    Args:
        plans: 키워드 후보 목록
        target_count: 목표 선택 개수

    Returns:
        다양성이 보장된 키워드 플랜 목록
    """
    # 유효한 항목만 필터링
    sanitized = [p for p in plans if p.keyword.strip() and p.context.strip()]
    selected: list[KeywordPlan] = []

    used_keywords: set[str] = set()
    used_domains: set[str] = set()
    used_categories: set[str] = set()
    used_hints: set[str] = set()

    # 컨텍스트가 긴(= 정보가 풍부한) 항목 우선
    sorted_plans = sorted(sanitized, key=lambda item: len(item.context), reverse=True)

    # 1차: 엄격한 다양성 필터
    for plan in sorted_plans:
        if len(selected) >= target_count:
            break

        keyword = _normalize_text(plan.keyword)
        domain = _normalize_text(plan.domain)
        category = _normalize_text(plan.category)
        hint = _normalize_text(plan.mirroring_hint)

        if not keyword or keyword in used_keywords:
            continue
        if domain and domain in used_domains:
            continue
        if category and category in used_categories:
            continue
        if hint and hint in used_hints:
            continue
        if any(_overlap_score(existing, plan) >= 0.45 for existing in selected):
            continue

        selected.append(plan)
        used_keywords.add(keyword)
        if domain:
            used_domains.add(domain)
        if category:
            used_categories.add(category)
        if hint:
            used_hints.add(hint)

    # 2차: 완화된 필터 (부족한 경우)
    if len(selected) < target_count:
        for plan in sorted_plans:
            if len(selected) >= target_count:
                break
            keyword = _normalize_text(plan.keyword)
            if not keyword or keyword in used_keywords:
                continue
            if any(_overlap_score(existing, plan) >= 0.55 for existing in selected):
                continue
            selected.append(plan)
            used_keywords.add(keyword)

    return selected[:target_count]


# ──────────────────────────────────────────────
# BriefingGenerator
# ──────────────────────────────────────────────


class BriefingGenerator:
    """일일 브리핑 생성 파이프라인 오케스트레이터.

    RSS 수집, 키워드 추출, 리서치, 스토리 생성, DB 저장을
    비동기로 실행하며, 시나리오 생성은 asyncio.gather로 병렬 처리한다.
    """

    def __init__(
        self,
        ai_service: AIPipelineService | None = None,
        rss_service: RSSService | None = None,
        target_scenario_count: int = 0,
    ) -> None:
        self.ai_service = ai_service or get_ai_pipeline_service()
        self.rss_service = rss_service or get_rss_service()
        self.target_scenario_count = target_scenario_count or getattr(
            settings, "TARGET_SCENARIO_COUNT", 3
        )

    async def generate_daily_briefing(
        self,
        db: AsyncSession,
        target_date: date | None = None,
        force: bool = False,
    ) -> DailyNarrative:
        """일일 브리핑 생성 메인 엔트리.

        Args:
            db: SQLAlchemy 비동기 세션
            target_date: 대상 날짜 (기본: 오늘 KST)
            force: True면 기존 브리핑이 있어도 재생성

        Returns:
            생성된 DailyNarrative ORM 객체
        """
        run_started = time.perf_counter()
        today = target_date or self._kst_today()
        LOGGER.info("[1/7] Starting daily briefing generation for date=%s", today)

        # 기존 브리핑 확인
        if not force:
            existing = await self._find_existing(db, today)
            if existing:
                LOGGER.info("Briefing already exists for date=%s, skipping", today)
                return existing

        LOGGER.info("[2/7] Generating new briefing for date=%s", today)

        # [3/7] RSS 뉴스 수집
        LOGGER.info("[3/7] Fetching RSS news")
        rss_text = await self.rss_service.fetch_top_news()
        LOGGER.info("RSS payload collected chars=%d", len(rss_text))

        if not rss_text.strip():
            raise RuntimeError("RSS 뉴스를 수집하지 못했어요. 피드 상태를 확인해주세요.")

        # [4/7] 키워드 추출 + 다양성 필터
        LOGGER.info("[4/7] Extracting keywords and applying diversity filter")
        candidates = await self.ai_service.extract_top_keywords(
            rss_text, candidate_count=8,
        )
        keyword_plans = pick_diverse_keyword_plans(
            candidates, self.target_scenario_count,
        )

        # 부족하면 avoid-list를 달아서 재시도
        if len(keyword_plans) < self.target_scenario_count:
            LOGGER.info(
                "Diversity filter selected too few (%d/%d). Retrying with avoid-lists.",
                len(keyword_plans),
                self.target_scenario_count,
            )
            retry_candidates = await self.ai_service.extract_top_keywords(
                rss_text,
                candidate_count=10,
                avoid_keywords=[p.keyword for p in candidates],
                avoid_categories=[p.category for p in candidates],
                avoid_mirroring_hints=[
                    p.mirroring_hint for p in candidates if p.mirroring_hint
                ],
            )
            keyword_plans = pick_diverse_keyword_plans(
                candidates + retry_candidates,
                self.target_scenario_count,
            )

        if not keyword_plans:
            raise RuntimeError(
                f"키워드 플랜을 하나도 생성하지 못했어요. RSS 텍스트 길이: {len(rss_text)}"
            )

        LOGGER.info("Keywords selected: %s", [p.keyword for p in keyword_plans])

        # [5/7] 시나리오 병렬 생성
        LOGGER.info(
            "[5/7] Generating %d scenarios in PARALLEL", len(keyword_plans),
        )
        scenario_tasks = [
            self._build_scenario(plan, idx, len(keyword_plans))
            for idx, plan in enumerate(keyword_plans, start=1)
        ]
        scenario_results = list(
            await asyncio.gather(*scenario_tasks, return_exceptions=True)
        )

        # 실패한 시나리오 필터링
        scenarios: list[dict[str, Any]] = []
        for i, result in enumerate(scenario_results):
            if isinstance(result, Exception):
                LOGGER.error(
                    "[SCENARIO %d] Failed: %s",
                    i + 1,
                    result,
                    exc_info=result,
                )
            else:
                scenarios.append(result)

        if not scenarios:
            raise RuntimeError("모든 시나리오 생성이 실패했어요.")

        LOGGER.info(
            "Successfully built %d/%d scenarios",
            len(scenarios),
            len(keyword_plans),
        )

        # [6/7] 용어집 생성
        LOGGER.info("[6/7] Generating glossary definitions")
        terms = self._extract_terms(scenarios)
        glossary = await self.ai_service.generate_batch_definitions(terms)
        scenarios = self._sanitize_scenarios_with_glossary(scenarios, glossary)

        # [7/7] DB 저장
        LOGGER.info("[7/7] Persisting briefing to database")
        narrative = await self._persist_to_db(
            db=db,
            target_date=today,
            keyword_plans=keyword_plans[: len(scenarios)],
            scenarios=scenarios,
            glossary=glossary,
        )

        elapsed = time.perf_counter() - run_started
        LOGGER.info(
            "Briefing generation complete: date=%s scenarios=%d elapsed=%.2fs",
            today,
            len(scenarios),
            elapsed,
        )
        return narrative

    # ──────────────────────────────────────────
    # 시나리오 빌드
    # ──────────────────────────────────────────

    async def _build_scenario(
        self,
        plan: KeywordPlan,
        idx: int,
        total: int,
    ) -> dict[str, Any]:
        """단일 시나리오 빌드: 리서치(병렬) -> 스토리 생성.

        context_research와 simulation_research를 병렬로 실행한 뒤,
        generate_story를 호출하여 7단계 내러티브를 생성한다.
        """
        scenario_started = time.perf_counter()
        LOGGER.info("[SCENARIO %d/%d] keyword=%s start", idx, total, plan.keyword)

        # 리서치 2단계 병렬 실행
        LOGGER.info(
            "[SCENARIO %d/%d] Parallel research (context + simulation)",
            idx, total,
        )
        ctx_task = self.ai_service.research_context(
            plan.keyword, plan.mirroring_hint,
        )
        sim_task = self.ai_service.research_simulation(
            plan.keyword, plan.mirroring_hint,
        )
        (ctx_research, ctx_citations), (sim_research, sim_citations) = (
            await asyncio.gather(ctx_task, sim_task)
        )

        # 스토리 생성
        LOGGER.info("[SCENARIO %d/%d] Story generation", idx, total)
        narrative = await self.ai_service.generate_story(
            theme=plan.keyword,
            context_research=ctx_research,
            simulation_research=sim_research,
            mirroring_hint=plan.mirroring_hint,
        )
        similarity = self.ai_service.calculate_similarity()

        # 인용 병합 (URL 중복 제거)
        all_citations: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for cite in ctx_citations + sim_citations:
            url = cite.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_citations.append(cite)
        sources = (
            all_citations[:5] if all_citations else [{"name": "RSS Feed", "url": "#"}]
        )

        result = {
            "title": plan.title or plan.keyword,
            "summary": self._safe_intro_content(narrative),
            "sources": sources,
            "narrative": narrative,
            "related_companies": DEFAULT_RELATED_COMPANIES,
            "mirroring_data": {
                "target_event": plan.mirroring_hint or "과거 금융 사례",
                "year": 0,
                "similarity_score": similarity["score"],
                "reasoning_log": similarity["reasoning_log"],
            },
        }

        elapsed = time.perf_counter() - scenario_started
        LOGGER.info(
            "[SCENARIO %d/%d] keyword=%s done elapsed=%.2fs",
            idx, total, plan.keyword, elapsed,
        )
        return result

    # ──────────────────────────────────────────
    # DB 저장
    # ──────────────────────────────────────────

    async def _persist_to_db(
        self,
        db: AsyncSession,
        target_date: date,
        keyword_plans: list[KeywordPlan],
        scenarios: list[dict[str, Any]],
        glossary: dict[str, str],
    ) -> DailyNarrative:
        """브리핑 결과를 DB에 저장 (upsert: 기존 데이터 교체)."""
        # 기존 브리핑 삭제
        existing = await self._find_existing(db, target_date)
        if existing:
            await db.execute(
                delete(NarrativeScenario).where(
                    NarrativeScenario.narrative_id == existing.id
                )
            )
            await db.delete(existing)
            await db.flush()

        # DailyNarrative 생성
        narrative = DailyNarrative(
            id=uuid_mod.uuid4(),
            date=target_date,
            main_keywords=[p.keyword for p in keyword_plans],
            glossary=glossary,
        )
        db.add(narrative)

        # NarrativeScenario 생성
        for idx, scenario_data in enumerate(scenarios):
            scenario = NarrativeScenario(
                id=uuid_mod.uuid4(),
                narrative_id=narrative.id,
                title=scenario_data.get("title", ""),
                summary=scenario_data.get("summary", ""),
                sources=scenario_data.get("sources", []),
                related_companies=scenario_data.get("related_companies", []),
                mirroring_data=scenario_data.get("mirroring_data", {}),
                narrative_sections=scenario_data.get("narrative", {}),
                sort_order=idx,
            )
            db.add(scenario)

        await db.commit()
        await db.refresh(narrative)
        LOGGER.info(
            "Persisted briefing id=%s date=%s scenarios=%d",
            narrative.id, target_date, len(scenarios),
        )
        return narrative

    async def _find_existing(
        self, db: AsyncSession, target_date: date,
    ) -> DailyNarrative | None:
        """지정 날짜의 기존 브리핑 조회."""
        result = await db.execute(
            select(DailyNarrative).where(DailyNarrative.date == target_date)
        )
        return result.scalar_one_or_none()

    # ──────────────────────────────────────────
    # 유틸리티 메서드
    # ──────────────────────────────────────────

    @staticmethod
    def _kst_today() -> date:
        """현재 KST 날짜 반환."""
        kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
        return kst_now.date()

    @staticmethod
    def _safe_intro_content(narrative: dict) -> str:
        """배경 섹션에서 요약 텍스트 추출."""
        background = narrative.get("background") if isinstance(narrative, dict) else None
        if isinstance(background, dict):
            return str(background.get("content") or "내용을 요약할 수 없어요.")
        return "내용을 요약할 수 없어요."

    @staticmethod
    def _extract_terms(scenarios: list[dict]) -> list[str]:
        """시나리오에서 <mark class='term'> 태그 내 용어 추출.

        중복을 제거하고 등장 순서를 유지한다.
        """
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
    def _sanitize_scenarios_with_glossary(
        scenarios: list[dict],
        glossary: dict[str, str],
    ) -> list[dict]:
        """용어집에 없는 <mark> 태그를 제거하여 정합성 유지."""
        allowed_terms = {term.strip() for term in glossary.keys() if term.strip()}
        sanitized = deepcopy(scenarios)

        for scenario in sanitized:
            narrative = scenario.get("narrative")
            if not isinstance(narrative, dict):
                continue

            for section_name in [
                "background",
                "mirroring",
                "difference",
                "devils_advocate",
                "simulation",
                "result",
                "action",
            ]:
                section = narrative.get(section_name)
                if not isinstance(section, dict):
                    continue

                content = section.get("content")
                if isinstance(content, str):
                    section["content"] = BriefingGenerator._sanitize_marks(
                        content, allowed_terms,
                    )

                bullets = section.get("bullets")
                if isinstance(bullets, list):
                    section["bullets"] = [
                        BriefingGenerator._sanitize_marks(str(item), allowed_terms)
                        for item in bullets
                    ]

            summary = scenario.get("summary")
            if isinstance(summary, str):
                scenario["summary"] = BriefingGenerator._sanitize_marks(
                    summary, allowed_terms,
                )

        return sanitized

    @staticmethod
    def _sanitize_marks(text: str, allowed_terms: set[str]) -> str:
        """허용된 용어만 <mark> 태그를 유지."""
        pattern = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")

        def replace(match: re.Match[str]) -> str:
            term = match.group(1).strip()
            if allowed_terms and term in allowed_terms:
                return f"<mark class='term'>{term}</mark>"
            return term

        return pattern.sub(replace, text)


# ──────────────────────────────────────────────
# 싱글톤 인스턴스
# ──────────────────────────────────────────────

_instance: BriefingGenerator | None = None


def get_briefing_generator() -> BriefingGenerator:
    """싱글톤 BriefingGenerator 인스턴스 반환."""
    global _instance
    if _instance is None:
        _instance = BriefingGenerator()
    return _instance
