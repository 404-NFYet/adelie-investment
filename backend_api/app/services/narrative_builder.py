"""내러티브 섹션 빌더 서비스.

7개 스텝(background, mirroring, difference, devils_advocate, simulation, result, action)의
콘텐츠를 구성하는 빌더 함수를 제공한다.

LLM이 생성한 narrative 데이터가 있으면 그대로 사용하고,
없으면 기존 빌더 로직으로 fallback한다.
"""

import re
from typing import Optional

from app.models.historical_case import CaseStockRelation
from app.models.briefing import DailyBriefing, BriefingStock
from app.schemas.narrative import ChartData, ChartDataPoint, NarrativeSection

# --- 유틸 ---

_TERM_PATTERN = re.compile(r"\[\[(.+?)\]\]")


def highlight_terms(content: str) -> str:
    """[[term]] 패턴을 <mark>term</mark> 으로 치환."""
    if not content:
        return content
    return _TERM_PATTERN.sub(r"<mark>\1</mark>", content)


def split_paragraphs(content: str) -> list[str]:
    """본문을 문단(빈 줄 기준)으로 분리."""
    if not content:
        return []
    return [p.strip() for p in content.split("\n\n") if p.strip()]


# --- 7단계 통합 빌더 ---

STEP_KEYS = ["background", "mirroring", "simulation", "result", "difference", "devils_advocate", "action"]


def build_all_steps(
    narrative_data: Optional[dict],
    comparison: dict,
    paragraphs: list[str],
    briefing: Optional[DailyBriefing],
    briefing_stocks: list[BriefingStock],
    case_stocks: list[CaseStockRelation],
) -> dict:
    """7단계 steps를 빌드. LLM narrative가 있으면 우선 사용, 없으면 fallback."""
    if narrative_data and _is_valid_narrative(narrative_data):
        return _build_from_llm(narrative_data, case_stocks, comparison)

    # fallback: 기존 빌더 로직
    return _build_fallback(comparison, paragraphs, briefing, briefing_stocks, case_stocks)


def _is_valid_narrative(narrative_data: dict) -> bool:
    """LLM narrative 데이터가 7단계 구조인지 확인."""
    required = STEP_KEYS  # 7개 전체
    if not all(key in narrative_data for key in required):
        return False

    # 각 섹션의 content가 최소 길이 이상인지 확인
    for key in required:
        section = narrative_data.get(key, {})
        if not isinstance(section, dict):
            return False
        content = str(section.get("content", ""))
        if len(content.strip()) < 10:
            return False

    # simulation에 quiz 존재 여부 확인
    sim = narrative_data.get("simulation", {})
    if isinstance(sim, dict) and "quiz" not in sim:
        return False

    return True


def _build_from_llm(narrative_data: dict, case_stocks: list[CaseStockRelation], comparison: dict) -> dict:
    """LLM이 생성한 7단계 narrative 데이터를 그대로 반환."""
    steps = {}
    for key in STEP_KEYS:
        section = narrative_data.get(key, {})
        if isinstance(section, str):
            section = {"content": section, "bullets": []}
        step_data = {
            "bullets": section.get("bullets", []),
            "content": section.get("content", ""),
            "chart": section.get("chart"),
        }
        # sources/citations 전달 (Perplexity 출처)
        if section.get("sources"):
            step_data["sources"] = section["sources"]
        # simulation 스텝의 quiz 데이터 전달
        if key == "simulation" and "quiz" in section:
            step_data["quiz"] = section["quiz"]
        steps[key] = step_data
    return steps


def _build_fallback(
    comparison: dict,
    paragraphs: list[str],
    briefing: Optional[DailyBriefing],
    briefing_stocks: list[BriefingStock],
    case_stocks: list[CaseStockRelation],
) -> dict:
    """기존 6단계 빌더를 7단계에 맞게 매핑."""
    return {
        "background": build_background(briefing, briefing_stocks),
        "mirroring": build_mirroring(comparison, paragraphs),
        "difference": build_difference(comparison, paragraphs),
        "devils_advocate": build_devils_advocate(comparison, paragraphs),
        "simulation": build_simulation(comparison, paragraphs),
        "result": build_result(comparison, paragraphs),
        "action": build_action(case_stocks, comparison),
    }


# --- 개별 섹션 빌더 (fallback용) ---

def build_background(briefing: Optional[DailyBriefing], briefing_stocks: list[BriefingStock]) -> dict:
    """background 섹션: 오늘의 시장 브리핑 요약."""
    bullets = []
    if briefing and briefing.top_keywords:
        for kw in briefing.top_keywords.get("keywords", [])[:3]:
            bullets.append(kw.get("title", "") if isinstance(kw, dict) else kw)

    content = highlight_terms(briefing.market_summary or "시장 요약이 없습니다.") if briefing else ""

    gainers = [s for s in briefing_stocks if s.selection_reason == "top_gainer"]
    chart_points = [
        ChartDataPoint(label=s.stock_name, value=float(s.change_rate) if s.change_rate else 0.0, color="#22c55e")
        for s in gainers[:5]
    ]
    chart = ChartData(chart_type="single_bar", title="오늘의 상승 TOP", unit="%", data_points=chart_points) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def build_mirroring(comparison: dict, paragraphs: list[str]) -> dict:
    """mirroring 섹션: 과거-현재 대비."""
    past_metric = comparison.get("past_metric", {})
    present_metric = comparison.get("present_metric", {})

    bullets = []
    if comparison.get("title"):
        bullets.append(comparison["title"])
    if comparison.get("subtitle"):
        bullets.append(comparison["subtitle"])
    if past_metric:
        bullets.append(
            f"{past_metric.get('company', '')} ({past_metric.get('year', '')}) "
            f"{past_metric.get('name', '')}: {past_metric.get('value', '')}"
        )

    content = highlight_terms(paragraphs[0]) if paragraphs else ""

    chart_points = []
    if past_metric.get("value") is not None:
        chart_points.append(ChartDataPoint(
            label=f"{past_metric.get('company', '')} ({past_metric.get('year', '')})",
            value=float(past_metric.get("value", 0)), color="#ef4444",
        ))
    if present_metric.get("value") is not None:
        chart_points.append(ChartDataPoint(
            label=f"{present_metric.get('company', '')} ({present_metric.get('year', '')})",
            value=float(present_metric.get("value", 0)), color="#3b82f6",
        ))

    chart = ChartData(
        chart_type="comparison_bar",
        title=f"{past_metric.get('name', '')} 비교",
        unit=past_metric.get("name", ""),
        data_points=chart_points,
    ) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def build_difference(comparison: dict, paragraphs: list[str]) -> dict:
    """difference 섹션: 과거와 현재의 차이."""
    analysis = comparison.get("analysis", [])
    bullets = analysis[:3] if analysis else ["과거와 현재의 차이를 분석합니다."]
    content = highlight_terms(paragraphs[1]) if len(paragraphs) > 1 else ""
    return NarrativeSection(bullets=bullets, content=content, chart=None).model_dump()


def build_devils_advocate(comparison: dict, paragraphs: list[str]) -> dict:
    """devils_advocate 섹션: 반대 시나리오."""
    title = comparison.get("title", "이 테마")
    bullets = [
        f"{title}의 예상과 다른 전개가 나올 수 있어요.",
        f"외부 변수(금리, 환율, 규제)가 {title} 흐름을 바꿀 수 있어요.",
        f"단기 모멘텀에 과도하게 베팅하면 손실 위험이 있어요.",
    ]
    content = highlight_terms(paragraphs[2]) if len(paragraphs) > 2 else f"{title} 관련 반대 시나리오도 꼭 체크해야 해요."
    return NarrativeSection(bullets=bullets, content=content, chart=None).model_dump()


def build_simulation(comparison: dict, paragraphs: list[str]) -> dict:
    """simulation 섹션: 과거 사례 시뮬레이션."""
    title = comparison.get("title", "이 테마")
    past = comparison.get("past_metric", {})
    year = past.get("year", "과거")
    bullets = [f"{title}의 {year} 사례를 기반으로 1,000만원 투자 시뮬레이션을 진행했어요."]
    content = highlight_terms(paragraphs[3]) if len(paragraphs) > 3 else f"{title} 과거 사례로 낙관/중립/비관 3가지 시나리오를 시뮬레이션했어요."
    return NarrativeSection(bullets=bullets, content=content, chart=None).model_dump()


def build_result(comparison: dict, paragraphs: list[str]) -> dict:
    """result 섹션: 시뮬레이션 결과."""
    title = comparison.get("title", "이 테마")
    bullets = [f"{title} 시뮬레이션 결과를 시나리오별로 정리했어요."]
    remaining = paragraphs[4:] if len(paragraphs) > 4 else paragraphs[-1:] if paragraphs else []
    content = highlight_terms("\n\n".join(remaining)) if remaining else f"{title} 투자 시뮬레이션에서 낙관 시나리오의 수익률이 가장 높았어요."
    return NarrativeSection(bullets=bullets, content=content, chart=None).model_dump()


def build_action(case_stocks: list[CaseStockRelation], comparison: dict) -> dict:
    """action 섹션: 투자 액션 요약."""
    title = comparison.get("title", "이 테마")
    bullets = [f"[{rel.relation_type or '관련'}] {rel.stock_name} — {rel.impact_description or ''}" for rel in case_stocks[:3]]
    if comparison.get("poll_question"):
        bullets.append(comparison["poll_question"])

    return NarrativeSection(
        bullets=bullets if bullets else [f"{title} 관련 종목들의 포지션을 확인해보세요."],
        content=f"{title} 분석을 바탕으로 관련 종목들의 비중을 조절하고, 리스크 관리 포인트를 체크하세요.",
        chart=None,
    ).model_dump()
