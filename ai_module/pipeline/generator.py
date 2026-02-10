"""브리핑 생성 오케스트레이터 (DEPRECATED).

⚠️ DEPRECATED: 이 파일은 더 이상 사용되지 않습니다.
현재는 scripts/keyword_pipeline_graph.py (LangGraph 기반)를 사용합니다.

기존 데이터 흐름:
  1. RSS 수집 → 2. 키워드 추출 → 3. 다양성 필터
  → 4. 병렬 리서치 → 5. 스토리 생성 → 6. 용어 사전
  → 7. PostgreSQL 저장 (daily_briefings + historical_cases + case_matches)
"""

from __future__ import annotations

import logging
import random
import re
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone, date
from typing import Any, Optional
from uuid import uuid4

from .ai_service import PipelineAIService
from .diversity import pick_diverse_keyword_plans
from .types import KeywordPlan

LOGGER = logging.getLogger(__name__)

# 기본 관련 기업 (리서치에서 못 찾았을 때 폴백)
DEFAULT_RELATED_COMPANIES = [
    {
        "name": "삼성전자",
        "code": "005930",
        "reason": "시장 대표주",
    }
]


class BriefingGenerator:
    """일일 브리핑 생성기.

    AI 파이프라인으로 RSS 뉴스에서 키워드를 추출하고,
    각 키워드에 대해 7단계 내러티브 시나리오를 생성한 뒤
    PostgreSQL에 저장한다.
    """

    def __init__(
        self,
        ai_service: PipelineAIService,
        target_scenario_count: int = 3,
        dry_run: bool = False,
    ) -> None:
        self.ai_service = ai_service
        self.target_count = target_scenario_count
        self.dry_run = dry_run

    def run(self, rss_text: str = "") -> dict:
        """동기 진입점 — 전체 파이프라인 실행 후 결과 dict 반환."""
        run_started = time.perf_counter()
        today_date = self._kst_today()
        now_iso = self._kst_now_iso()

        LOGGER.info("[1/7] 뉴스 텍스트 확인")
        if not rss_text:
            LOGGER.warning("뉴스 텍스트 없음 — 빈 텍스트로 진행")
        LOGGER.info("뉴스 텍스트: %d chars", len(rss_text))

        LOGGER.info("[2/7] 키워드 추출")
        candidates = self.ai_service.extract_top_keywords(rss_text, candidate_count=8)
        LOGGER.info("후보 키워드 %d개 추출", len(candidates))

        LOGGER.info("[3/7] 다양성 필터 적용")
        keyword_plans = pick_diverse_keyword_plans(candidates, self.target_count)

        # 부족하면 재시도
        if len(keyword_plans) < self.target_count:
            LOGGER.info("다양성 부족 → 재시도 (avoid-list 적용)")
            retry = self.ai_service.extract_top_keywords(
                rss_text,
                candidate_count=10,
                avoid_keywords=[p.keyword for p in candidates],
            )
            keyword_plans = pick_diverse_keyword_plans(
                candidates + retry, self.target_count,
            )

        if not keyword_plans:
            raise RuntimeError("키워드를 추출할 수 없습니다.")

        LOGGER.info("최종 키워드: %s", [p.keyword for p in keyword_plans])

        LOGGER.info("[4-5/7] 시나리오 생성 (%d개)", len(keyword_plans))
        scenarios = []
        for idx, plan in enumerate(keyword_plans, start=1):
            scenario = self._build_scenario(plan, idx, len(keyword_plans))
            scenarios.append(scenario)

        LOGGER.info("[6/7] 용어 사전 생성")
        all_terms = self._extract_terms(scenarios)
        glossary = self.ai_service.generate_glossary(all_terms)
        scenarios = self._sanitize_scenarios_with_glossary(scenarios, glossary)

        briefing_id = "briefing_" + now_iso.replace(":", "-").replace("+", "p")
        briefing_data = {
            "id": briefing_id,
            "date": now_iso,
            "today_date": today_date,
            "main_keywords": [p.keyword for p in keyword_plans],
            "scenarios": scenarios,
            "glossary": glossary,
            "keyword_plans": [
                {
                    "keyword": p.keyword,
                    "title": p.title,
                    "category": p.category,
                    "domain": p.domain,
                    "context": p.context,
                    "mirroring_hint": p.mirroring_hint,
                }
                for p in keyword_plans
            ],
        }

        LOGGER.info(
            "[7/7] 브리핑 생성 완료 (%.2fs), 시나리오 %d개",
            time.perf_counter() - run_started,
            len(scenarios),
        )
        return briefing_data

    def _build_scenario(self, plan: KeywordPlan, idx: int, total: int) -> dict:
        """단일 시나리오 빌드: 리서치 → 스토리 생성."""
        started = time.perf_counter()
        LOGGER.info("[SCENARIO %d/%d] keyword=%s 시작", idx, total, plan.keyword)

        # 리서치 (순차)
        LOGGER.info("[SCENARIO %d/%d] 배경 리서치", idx, total)
        ctx_research = self.ai_service.research_context(plan.keyword, plan.mirroring_hint)

        LOGGER.info("[SCENARIO %d/%d] 시뮬레이션 리서치", idx, total)
        sim_research = self.ai_service.research_simulation(plan.keyword, plan.mirroring_hint)

        # 스토리 생성
        LOGGER.info("[SCENARIO %d/%d] 스토리 생성", idx, total)
        narrative = self.ai_service.generate_story(
            theme=plan.keyword,
            context_research=ctx_research,
            simulation_research=sim_research,
            mirroring_hint=plan.mirroring_hint,
        )

        similarity_score = random.randint(65, 85)

        result = {
            "id": str(uuid4()),
            "title": plan.title or plan.keyword,
            "keyword": plan.keyword,
            "category": plan.category,
            "domain": plan.domain,
            "summary": self._safe_intro_content(narrative),
            "narrative": narrative,
            "mirroring_hint": plan.mirroring_hint,
            "context": plan.context,
            "similarity_score": similarity_score,
            "related_companies": DEFAULT_RELATED_COMPANIES,
        }

        LOGGER.info(
            "[SCENARIO %d/%d] keyword=%s 완료 (%.2fs)",
            idx, total, plan.keyword, time.perf_counter() - started,
        )
        return result

    # --- PostgreSQL 저장 ---

    def save_to_db(self, briefing_data: dict, db_url: str) -> dict:
        """생성된 브리핑 데이터를 PostgreSQL에 저장.

        저장 테이블:
          - daily_briefings: 날짜별 브리핑 + top_keywords
          - historical_cases: 시나리오별 케이스 + keywords.narrative
          - case_matches: 키워드 → 케이스 매칭
          - case_stock_relations: 관련 기업

        Returns:
            저장 결과 요약 dict
        """
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session

        # asyncpg → psycopg2 동기 URL로 변환
        sync_url = db_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
        if "psycopg2" not in sync_url and "postgresql://" in sync_url:
            sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

        engine = create_engine(sync_url, echo=False)
        today = briefing_data.get("today_date", self._kst_today())
        scenarios = briefing_data.get("scenarios", [])
        keyword_plans = briefing_data.get("keyword_plans", [])
        glossary = briefing_data.get("glossary", {})

        saved_case_ids = []

        with Session(engine) as session:
            try:
                # 1. daily_briefings 저장 (upsert)
                briefing_id = self._upsert_briefing(
                    session, today, briefing_data, keyword_plans, glossary,
                )
                LOGGER.info("daily_briefings 저장 완료: id=%s", briefing_id)

                # 2. 시나리오별 historical_cases + case_matches 저장
                for scenario in scenarios:
                    case_id = self._save_scenario(session, scenario, today, briefing_id)
                    saved_case_ids.append(case_id)
                    LOGGER.info(
                        "historical_case 저장: id=%d, keyword=%s",
                        case_id, scenario.get("keyword"),
                    )

                session.commit()
                LOGGER.info(
                    "DB 저장 완료: briefing_id=%s, cases=%d",
                    briefing_id, len(saved_case_ids),
                )

            except Exception as exc:
                session.rollback()
                LOGGER.error("DB 저장 실패: %s", exc)
                raise

        engine.dispose()
        return {
            "briefing_id": briefing_id,
            "case_ids": saved_case_ids,
            "scenario_count": len(saved_case_ids),
        }

    def _upsert_briefing(
        self,
        session,
        today: str,
        briefing_data: dict,
        keyword_plans: list[dict],
        glossary: dict,
    ) -> int:
        """daily_briefings 테이블에 브리핑 저장 (upsert)."""
        from sqlalchemy import text

        # top_keywords JSONB 구조 - keywords API가 읽는 형식
        keywords_list = []
        for plan in keyword_plans:
            keywords_list.append({
                "title": plan.get("keyword", ""),
                "category": plan.get("category", "GENERAL"),
                "description": plan.get("context", ""),
                "stocks": [],  # 종목은 case_stock_relations에서 관리
            })

        top_keywords_json = {
            "keywords": keywords_list,
            "glossary": glossary,
        }

        market_summary = f"오늘의 핵심 테마: {', '.join(p.get('keyword', '') for p in keyword_plans)}"

        # 기존 브리핑 확인
        existing = session.execute(
            text("SELECT id FROM daily_briefings WHERE briefing_date = :d"),
            {"d": today},
        ).fetchone()

        if existing:
            session.execute(
                text("""
                    UPDATE daily_briefings
                    SET market_summary = :summary, top_keywords = CAST(:kw AS jsonb), created_at = NOW()
                    WHERE briefing_date = :d
                """),
                {"summary": market_summary, "kw": _to_json(top_keywords_json), "d": today},
            )
            return existing[0]
        else:
            result = session.execute(
                text("""
                    INSERT INTO daily_briefings (briefing_date, market_summary, top_keywords, created_at)
                    VALUES (:d, :summary, CAST(:kw AS jsonb), NOW())
                    RETURNING id
                """),
                {"d": today, "summary": market_summary, "kw": _to_json(top_keywords_json)},
            )
            return result.fetchone()[0]

    def _save_scenario(self, session, scenario: dict, today: str, briefing_id: int) -> int:
        """시나리오를 historical_cases + case_matches + case_stock_relations에 저장."""
        from sqlalchemy import text

        keyword = scenario.get("keyword", "")
        title = scenario.get("title", keyword)
        summary = scenario.get("summary", "")
        narrative = scenario.get("narrative", {})
        similarity = scenario.get("similarity_score", 75)
        mirroring_hint = scenario.get("mirroring_hint", "")
        context = scenario.get("context", "")
        related = scenario.get("related_companies", [])

        # keywords JSONB - narrative_builder._build_from_llm()이 읽는 형식
        keywords_json = {
            "keywords": [keyword],
            "narrative": narrative,
            "comparison": {
                "sync_rate": similarity,
                "title": f"{keyword} vs {mirroring_hint}",
                "subtitle": context[:100] if context else "",
                "past_label": mirroring_hint,
                "present_label": keyword,
            },
        }

        # historical_cases 삽입
        result = session.execute(
            text("""
                INSERT INTO historical_cases
                    (title, event_date, event_year, summary, full_content, keywords, difficulty, view_count, created_at, updated_at)
                VALUES
                    (:title, :event_date, :event_year, :summary, :full_content, CAST(:kw AS jsonb), 'beginner', 0, NOW(), NOW())
                RETURNING id
            """),
            {
                "title": title,
                "event_date": today,
                "event_year": int(today[:4]) if today else 2026,
                "summary": summary,
                "full_content": summary,
                "kw": _to_json(keywords_json),
            },
        )
        case_id = result.fetchone()[0]

        # case_matches 삽입 (키워드 → 케이스 연결)
        session.execute(
            text("""
                INSERT INTO case_matches (current_keyword, matched_case_id, similarity_score, match_reason, matched_at)
                VALUES (:kw, :case_id, :score, :reason, NOW())
            """),
            {
                "kw": keyword,
                "case_id": case_id,
                "score": similarity / 100.0,
                "reason": f"{keyword} - {mirroring_hint} 유사도 매칭",
            },
        )

        # case_stock_relations 삽입
        for company in related:
            session.execute(
                text("""
                    INSERT INTO case_stock_relations (case_id, stock_code, stock_name, relation_type, impact_description)
                    VALUES (:case_id, :code, :name, 'related', :desc)
                """),
                {
                    "case_id": case_id,
                    "code": company.get("code", "005930"),
                    "name": company.get("name", ""),
                    "desc": company.get("reason", ""),
                },
            )

        return case_id

    # --- 유틸리티 ---

    @staticmethod
    def _kst_now_iso() -> str:
        kst = timezone(timedelta(hours=9))
        return datetime.now(kst).isoformat(timespec="seconds")

    @staticmethod
    def _kst_today() -> str:
        kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
        return kst_now.date().isoformat()

    @staticmethod
    def _safe_intro_content(narrative: dict) -> str:
        bg = narrative.get("background") if isinstance(narrative, dict) else None
        if isinstance(bg, dict):
            return str(bg.get("content", "내용을 요약할 수 없어요."))
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
            t = term.strip()
            if t and t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered

    @staticmethod
    def _sanitize_scenarios_with_glossary(
        scenarios: list[dict], glossary: dict[str, str],
    ) -> list[dict]:
        allowed_terms = {t.strip() for t in glossary.keys() if t.strip()}
        sanitized = deepcopy(scenarios)

        def _clean_marks(text: str) -> str:
            pattern = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")

            def replace(match):
                term = match.group(1).strip()
                if term in allowed_terms:
                    return f"<mark class='term'>{term}</mark>"
                return term

            return pattern.sub(replace, text)

        for scenario in sanitized:
            narrative = scenario.get("narrative")
            if not isinstance(narrative, dict):
                continue
            for section_name in [
                "background", "mirroring", "difference",
                "devils_advocate", "simulation", "result", "action",
            ]:
                section = narrative.get(section_name)
                if not isinstance(section, dict):
                    continue
                content = section.get("content")
                if isinstance(content, str):
                    section["content"] = _clean_marks(content)
                bullets = section.get("bullets")
                if isinstance(bullets, list):
                    section["bullets"] = [
                        _clean_marks(str(b)) if isinstance(b, str) else b
                        for b in bullets
                    ]
            summary = scenario.get("summary")
            if isinstance(summary, str):
                scenario["summary"] = _clean_marks(summary)

        return sanitized


def _to_json(obj: Any) -> str:
    """dict를 JSON 문자열로 변환."""
    import json
    return json.dumps(obj, ensure_ascii=False, default=str)
