"""브리핑 파이프라인 결과를 PostgreSQL에 저장한다.

사용법:
    from datapipeline.db.writer import save_briefing_to_db

    result = await save_briefing_to_db(full_output_dict)
    # result = {"briefing_id": 42, "case_id": 7, "stocks_saved": 3, ...}

DATABASE_URL 환경변수가 없으면 skip (로컬 테스트 호환).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, date
from typing import Any, Optional

from ..config import kst_today
from ..constants.home_icons import DEFAULT_HOME_ICON_KEY

logger = logging.getLogger(__name__)


def _get_database_url() -> Optional[str]:
    """DATABASE_URL 환경변수에서 asyncpg 호환 URL 반환."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return None
    return url.replace("+asyncpg", "")


async def save_briefing_to_db(
    full_output: dict[str, Any],
    *,
    briefing_date: date | None = None,
) -> dict[str, Any]:
    """파이프라인 FullBriefingOutput을 DB에 저장한다.

    테이블 매핑:
        - daily_briefings: 날짜별 브리핑 메타
        - briefing_stocks: curated_context.selected_stocks
        - historical_cases: 역사적 사례
        - case_matches: 키워드-사례 매칭
        - case_stock_relations: 사례-종목 관계

    Returns:
        저장 결과 요약 dict. DATABASE_URL이 없으면 {"skipped": True}.
    """
    db_url = _get_database_url()
    if not db_url:
        logger.warning("DATABASE_URL이 설정되지 않아 DB 저장을 건너뜁니다.")
        return {"skipped": True}

    try:
        import asyncpg
    except ImportError:
        logger.warning("asyncpg 미설치 — DB 저장을 건너뜁니다.")
        return {"skipped": True, "reason": "asyncpg not installed"}

    conn = await asyncpg.connect(db_url)
    try:
        return await _save(conn, full_output, briefing_date)
    finally:
        await conn.close()


async def _save(
    conn: Any,
    full_output: dict[str, Any],
    briefing_date: date | None,
) -> dict[str, Any]:
    """트랜잭션 내에서 저장 수행."""

    curated = full_output.get("interface_1_curated_context", {})
    narrative = full_output.get("interface_2_raw_narrative", {})
    final = full_output.get("interface_3_final_briefing", {})

    # 날짜 결정
    if briefing_date is None:
        date_str = curated.get("date", "")
        try:
            briefing_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            briefing_date = kst_today()

    result: dict[str, Any] = {"briefing_date": str(briefing_date)}

    async with conn.transaction():
        # 동일 날짜에 대한 동시 쓰기 방지 (advisory lock)
        lock_key = int(briefing_date.toordinal()) & 0x7FFFFFFF
        await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

        # ── 1. daily_briefings (UPSERT) ──
        existing_id = await conn.fetchval(
            "SELECT id FROM daily_briefings WHERE briefing_date = $1",
            briefing_date,
        )

        if existing_id:
            # 기존 top_keywords 읽어서 새 키워드 누적 (덮어쓰기 방지)
            existing_kw_raw = await conn.fetchval(
                "SELECT top_keywords FROM daily_briefings WHERE id = $1",
                existing_id,
            )
            existing_kw = json.loads(existing_kw_raw) if existing_kw_raw else {"keywords": []}

            new_kw = _build_top_keywords(curated, final)
            existing_keywords = existing_kw.get("keywords", [])
            existing_titles = {k.get("title", "") for k in existing_keywords}
            latest_keywords = [
                kw
                for kw in new_kw.get("keywords", [])
                if kw.get("title", "") and kw.get("title", "") not in existing_titles
            ]
            # 최신 생성 키워드를 앞에 배치해서 홈 카드가 가장 최근 주제를 우선 노출하도록 한다.
            existing_kw["keywords"] = latest_keywords + existing_keywords

            # top_keywords만 업데이트 (market_summary 유지)
            await conn.execute(
                "UPDATE daily_briefings SET top_keywords = $1::jsonb WHERE id = $2",
                json.dumps(existing_kw, ensure_ascii=False),
                existing_id,
            )
            briefing_id = existing_id
            # briefing_stocks DELETE 제거 — 새 종목만 append
            logger.info("기존 브리핑에 키워드 누적: id=%d, date=%s, 키워드=%d개",
                        briefing_id, briefing_date, len(existing_kw["keywords"]))
        else:
            briefing_id = await conn.fetchval(
                """INSERT INTO daily_briefings (briefing_date, market_summary, top_keywords, created_at)
                   VALUES ($1, $2, $3::jsonb, NOW())
                   RETURNING id""",
                briefing_date,
                curated.get("theme", ""),
                json.dumps(_build_top_keywords(curated, final), ensure_ascii=False),
            )
            logger.info("새 브리핑 생성: id=%d, date=%s", briefing_id, briefing_date)

        result["briefing_id"] = briefing_id

        # ── 2. briefing_stocks ──
        stocks = curated.get("selected_stocks", [])
        verified_news = curated.get("verified_news", [])
        first_catalyst = verified_news[0] if verified_news else None
        if stocks:
            rows = []
            for s in stocks:
                rows.append((
                    briefing_id,
                    s.get("ticker", ""),
                    s.get("name", ""),
                    s.get("change_pct", 0.0),
                    None,  # volume (curated context에 없음)
                    s.get("momentum", ""),
                    datetime.utcnow(),
                    s.get("period_days"),
                    s.get("momentum", ""),
                    first_catalyst.get("title") if first_catalyst else None,
                    first_catalyst.get("url") if first_catalyst else None,
                    None,  # catalyst_published_at
                    first_catalyst.get("source") if first_catalyst else None,
                ))
            # UNIQUE 제약이 없는 환경에서도 중복 저장을 피하기 위해
            # ON CONFLICT 대신 NOT EXISTS 패턴을 사용한다.
            await conn.executemany(
                """INSERT INTO briefing_stocks
                   (briefing_id, stock_code, stock_name, change_rate, volume,
                    selection_reason, created_at, trend_days, trend_type,
                    catalyst, catalyst_url, catalyst_published_at, catalyst_source)
                   SELECT $1,$2::text,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13
                   WHERE NOT EXISTS (
                       SELECT 1 FROM briefing_stocks
                       WHERE briefing_id = $1 AND stock_code::text = $2::text
                   )""",
                rows,
            )
            result["stocks_saved"] = len(rows)
            logger.info("briefing_stocks 저장: %d건", len(rows))

        # ── 3. historical_cases ──
        hist = narrative.get("historical_case", {})
        if hist:
            # 기존 동일 제목 사례 확인
            event_year = _extract_year(hist.get("period", ""))
            keywords_jsonb = json.dumps(
                _build_case_keywords(curated, narrative, final),
                ensure_ascii=False,
            )
            full_content = _build_full_content(narrative, final)

            case_id = await conn.fetchval(
                """INSERT INTO historical_cases
                   (title, event_year, summary, full_content, keywords,
                    difficulty, view_count, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5::jsonb, 'beginner', 0, NOW(), NOW())
                   RETURNING id""",
                hist.get("title", curated.get("theme", "")),
                event_year,
                hist.get("summary", ""),
                full_content,
                keywords_jsonb,
            )
            result["case_id"] = case_id
            logger.info("historical_cases 저장: id=%d", case_id)

            # ── 4. case_matches ──
            theme = final.get("theme") or curated.get("theme", "")
            if theme and case_id:
                for s in stocks:
                    await conn.execute(
                        """INSERT INTO case_matches
                           (current_keyword, current_stock_code, matched_case_id,
                            similarity_score, match_reason, matched_at)
                           VALUES ($1, $2, $3, $4, $5, NOW())""",
                        theme,
                        s.get("ticker", ""),
                        case_id,
                        0.85,  # AI 생성 매칭이므로 기본 높은 유사도
                        hist.get("lesson", "AI 파이프라인 자동 매칭"),
                    )
                result["matches_saved"] = len(stocks)
                logger.info("case_matches 저장: %d건", len(stocks))

            # ── 5. case_stock_relations ──
            if case_id and stocks:
                for i, s in enumerate(stocks):
                    relation_type = "main_subject" if i == 0 else "related"
                    await conn.execute(
                        """INSERT INTO case_stock_relations
                           (case_id, stock_code, stock_name, relation_type, impact_description)
                           VALUES ($1, $2, $3, $4, $5)""",
                        case_id,
                        s.get("ticker", ""),
                        s.get("name", ""),
                        relation_type,
                        f"{s.get('momentum', '')} {s.get('change_pct', 0):.1f}%",
                    )
                result["relations_saved"] = len(stocks)
                logger.info("case_stock_relations 저장: %d건", len(stocks))

    return result


# ── 헬퍼 함수 ──

def _build_top_keywords(curated: dict, final: dict) -> dict:
    """daily_briefings.top_keywords JSONB 구성 (keywords API 호환)."""
    keywords_list = []
    theme = final.get("theme") or curated.get("theme", "")
    one_liner = final.get("one_liner") or curated.get("one_liner", "")
    home_icon = final.get("home_icon") if isinstance(final.get("home_icon"), dict) else {}
    icon_key = home_icon.get("icon_key") or DEFAULT_HOME_ICON_KEY
    if theme:
        selected_stocks = curated.get("selected_stocks", [])
        concept = curated.get("concept", {})
        news = curated.get("verified_news", [])
        catalyst = news[0] if news else None

        stocks = []
        for s in selected_stocks:
            parts = []
            attn_pct = s.get("attention_percentile")
            if attn_pct is not None:
                parts.append(f"주목도 상위 {100 - attn_pct:.0f}%")
            parts.append(f"{s.get('momentum', '변동')} {abs(s.get('change_pct', 0)):.1f}%")
            stocks.append({
                "stock_code": s.get("ticker", ""),
                "stock_name": s.get("name", ""),
                "reason": " | ".join(parts),
            })

        keywords_list.append({
            "title": theme,
            "description": one_liner,
            "category": "ATTENTION",
            "sector": concept.get("name", ""),
            "stocks": stocks,
            "trend_days": selected_stocks[0].get("period_days", 0) if selected_stocks else 0,
            "trend_type": _infer_trend_type(selected_stocks),
            "catalyst": catalyst.get("title") if catalyst else None,
            "catalyst_url": catalyst.get("url") if catalyst else None,
            "catalyst_source": catalyst.get("source") if catalyst else None,
            "quality_score": _calc_quality_score(curated),
            "icon_key": icon_key,
        })
    return {"keywords": keywords_list}


def _build_case_keywords(curated: dict, narrative: dict, final: dict) -> dict:
    """historical_cases.keywords JSONB 구성 (narrative/comparison/cases API 호환)."""
    hist_case = narrative.get("historical_case", {})
    narrative_sections = narrative.get("narrative", {})
    concept = narrative.get("concept", curated.get("concept", {}))
    final_theme = final.get("theme") or curated.get("theme", "")
    final_one_liner = final.get("one_liner") or curated.get("one_liner", "")
    pages = final.get("pages", [])
    sources = final.get("sources", [])
    checklist = final.get("hallucination_checklist", [])
    selected_stocks = curated.get("selected_stocks", [])

    # 키워드 리스트 (story API: kw_data.get("keywords", []))
    kw_set = {final_theme, concept.get("name", "")}
    kw_set |= {s.get("name", "") for s in selected_stocks}
    kw_set.discard("")

    # narrative 섹션에 chart/glossary 병합
    KEYS = ["background", "concept_explain", "history", "application", "caution", "summary"]
    merged_narrative = {}
    for i, key in enumerate(KEYS):
        section = narrative_sections.get(key, {})
        page = pages[i] if i < len(pages) else {}
        page_title = page.get("title", "")
        page_content = page.get("content", "")
        page_bullets = page.get("bullets", [])
        merged_narrative[key] = {
            "title": page_title,
            "content": page_content or section.get("content", ""),
            "bullets": page_bullets or section.get("bullets", []),
            "chart": None if key == "summary" else page.get("chart"),
            "glossary": page.get("glossary", []),
        }

    # comparison 조립
    comparison = {
        "sync_rate": 75,
        "past_label": hist_case.get("period", "과거"),
        "present_label": "2026",
        "title": hist_case.get("title", final_theme),
        "current_summary": final_one_liner,
        "points": [{
            "aspect": "핵심 이슈",
            "past": hist_case.get("summary", ""),
            "present": final_one_liner,
            "similarity": "부분 유사",
        }],
        "lessons": [hist_case.get("lesson", "")] if hist_case.get("lesson") else [],
    }

    return {
        "theme": final_theme,
        "one_liner": final_one_liner,
        "generated_at": final.get("generated_at", ""),
        "keywords": sorted(kw_set),
        "concept": concept,
        "historical_case": hist_case,
        "comparison": comparison,
        "narrative": merged_narrative,
        "sources": sources,
        "hallucination_checklist": checklist,
        "key_insight": {
            "summary": hist_case.get("lesson", ""),
            "term_definitions": [
                {"term": g["term"], "definition": g["definition"]}
                for p in pages for g in p.get("glossary", [])[:1]
            ],
        },
    }


def _infer_trend_type(stocks: list[dict]) -> str:
    """종목 등락률 평균으로 트렌드 타입 추론."""
    if not stocks:
        return "mixed"
    avg = sum(s.get("change_pct", 0) for s in stocks) / len(stocks)
    if avg > 3: return "급등"
    if avg > 0: return "상승"
    if avg < -3: return "급락"
    if avg < 0: return "하락"
    return "횡보"


def _calc_quality_score(curated: dict) -> float:
    """브리핑 품질 점수 계산 (0~1)."""
    score = 0.5
    if curated.get("verified_news"): score += 0.2
    if curated.get("reports"): score += 0.15
    if curated.get("source_ids"): score += 0.15
    return min(score, 1.0)


def _build_full_content(narrative: dict, final: dict) -> str:
    """historical_cases.full_content 구성 (내러티브 + 6페이지 브리핑)."""
    parts = []

    # 내러티브 섹션
    body = narrative.get("narrative", {})
    for section_name in ["background", "concept_explain", "history", "application", "caution", "summary"]:
        section = body.get(section_name, {})
        if section:
            parts.append(f"## {section.get('purpose', section_name)}")
            parts.append(section.get("content", ""))
            for b in section.get("bullets", []):
                parts.append(f"- {b}")
            parts.append("")

    # 6페이지 브리핑
    pages = final.get("pages", [])
    for page in pages:
        parts.append(f"### Step {page.get('step', 0)}: {page.get('title', '')}")
        parts.append(page.get("content", ""))
        for b in page.get("bullets", []):
            parts.append(f"- {b}")
        parts.append("")

    return "\n".join(parts)


def _extract_year(period: str) -> int | None:
    """기간 문자열에서 연도 추출 (예: '2008년' → 2008)."""
    import re
    match = re.search(r"(\d{4})", period)
    return int(match.group(1)) if match else None
