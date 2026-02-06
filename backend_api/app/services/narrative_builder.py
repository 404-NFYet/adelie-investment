"""내러티브 섹션 빌더 서비스.

6개 스텝(mirroring, intro, development, climax, conclusion, action)의
콘텐츠를 구성하는 빌더 함수를 제공한다.
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


# --- 섹션 빌더 ---

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


def build_intro(briefing: Optional[DailyBriefing], briefing_stocks: list[BriefingStock]) -> dict:
    """intro 섹션: 오늘의 시장 브리핑 요약."""
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


def build_development(comparison: dict, paragraphs: list[str]) -> dict:
    """development 섹션: 트렌드 분석."""
    trend_data = comparison.get("trend_data", {})
    analysis = comparison.get("analysis", [])

    bullets = [trend_data["title"]] if trend_data.get("title") else []
    content = highlight_terms(paragraphs[1]) if len(paragraphs) > 1 else (highlight_terms(analysis[0]) if analysis else "")

    chart_points = [ChartDataPoint(label=dp.get("label", ""), value=float(dp.get("value", 0))) for dp in trend_data.get("data_points", [])]
    chart = ChartData(chart_type="trend_line", title=trend_data.get("title", "트렌드"), unit=trend_data.get("unit", ""), data_points=chart_points) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def build_climax(comparison: dict, paragraphs: list[str]) -> dict:
    """climax 섹션: 리스크 지표."""
    risk_data = comparison.get("risk_data", {})
    analysis = comparison.get("analysis", [])

    bullets = [risk_data["title"]] if risk_data.get("title") else []
    bullets.extend(analysis[1:3])

    content = highlight_terms(paragraphs[2]) if len(paragraphs) > 2 else (highlight_terms(" ".join(analysis[1:])) if len(analysis) > 1 else "")

    chart_points = [ChartDataPoint(label=dp.get("label", ""), value=float(dp.get("value", 0)), color="#f59e0b") for dp in risk_data.get("data_points", [])]
    chart = ChartData(chart_type="risk_indicator", title=risk_data.get("title", "리스크 지표"), unit=risk_data.get("unit", ""), data_points=chart_points) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def build_conclusion(comparison: dict, paragraphs: list[str]) -> dict:
    """conclusion 섹션: 전략/교훈 요약."""
    strategy_data = comparison.get("strategy_data", {})

    bullets = [strategy_data["title"]] if strategy_data.get("title") else []
    if comparison.get("poll_question"):
        bullets.append(f"💡 {comparison['poll_question']}")

    remaining = paragraphs[3:] if len(paragraphs) > 3 else paragraphs[-1:] if paragraphs else []
    content = highlight_terms("\n\n".join(remaining)) if remaining else ""

    chart_points = [ChartDataPoint(label=dp.get("label", ""), value=float(dp.get("value", 0)), color="#8b5cf6") for dp in strategy_data.get("data_points", [])]
    chart = ChartData(chart_type="single_bar", title=strategy_data.get("title", "전략 비교"), unit=strategy_data.get("unit", ""), data_points=chart_points) if chart_points else None

    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def build_action(case_stocks: list[CaseStockRelation], comparison: dict) -> dict:
    """action 섹션: 투자 액션 요약."""
    bullets = [f"[{rel.relation_type or '관련'}] {rel.stock_name} — {rel.impact_description or ''}" for rel in case_stocks[:3]]
    if comparison.get("poll_question"):
        bullets.append(comparison["poll_question"])

    return NarrativeSection(
        bullets=bullets if bullets else ["관련 기업 정보를 확인하세요."],
        content="분석을 바탕으로 관련 기업들의 현재 포지션을 확인하고, 투자 의사결정에 참고하세요.",
        chart=None,
    ).model_dump()
