"""내러티브 섹션 빌더 서비스 (6페이지 골든케이스).

6개 페이지(background, concept_explain, history, application, caution, summary)의
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

PAGE_KEYS = ["background", "concept_explain", "history", "application", "caution", "summary"]


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


# --- 6페이지 통합 빌더 ---


def build_all_steps(
    narrative_data: Optional[dict],
    comparison: dict,
    paragraphs: list[str],
    briefing: Optional[DailyBriefing],
    briefing_stocks: list[BriefingStock],
    case_stocks: list[CaseStockRelation],
) -> dict:
    """6페이지 steps를 빌드. LLM narrative가 있으면 우선 사용, 없으면 fallback."""
    if narrative_data and _is_valid_narrative(narrative_data):
        return _build_from_llm(narrative_data)

    # fallback: 기본 빌더 로직
    return _build_fallback(comparison, paragraphs, briefing, briefing_stocks, case_stocks)


def _is_valid_narrative(narrative_data: dict) -> bool:
    """LLM narrative 데이터가 6페이지 구조인지 확인."""
    if not all(key in narrative_data for key in PAGE_KEYS):
        return False

    for key in PAGE_KEYS:
        section = narrative_data.get(key, {})
        if not isinstance(section, dict):
            return False
        content = str(section.get("content", ""))
        if len(content.strip()) < 10:
            return False

    return True


def _inject_glossary_marks(content: str, glossary: list[dict]) -> str:
    """content 내 glossary 용어를 <mark> 태그로 감싸기 (각 용어 첫 등장 1회만)."""
    if not content or not glossary:
        return content
    for item in glossary:
        term = item.get("term", "")
        if not term or len(term) < 2:
            continue
        # 이미 <mark> 안에 있는 것은 건너뛰기
        pattern = re.compile(
            rf'(?<!<mark>)(?<!<mark class="term-highlight">)({re.escape(term)})(?!</mark>)',
            re.IGNORECASE,
        )
        content = pattern.sub(r'<mark class="term-highlight">\1</mark>', content, count=1)
    return content


def _build_from_llm(narrative_data: dict) -> dict:
    """LLM이 생성한 6페이지 narrative 데이터를 반환 (glossary 하이라이팅 포함)."""
    steps = {}
    for key in PAGE_KEYS:
        section = narrative_data.get(key, {})
        if isinstance(section, str):
            section = {"content": section, "bullets": []}

        content = section.get("content", "")
        glossary = section.get("glossary", [])

        # glossary 용어를 content에 하이라이팅
        content = _inject_glossary_marks(content, glossary)
        # 기존 [[term]] 패턴도 변환
        content = highlight_terms(content)

        step_data = {
            "bullets": section.get("bullets", []),
            "content": content,
            "chart": section.get("chart"),
            "glossary": glossary,
        }
        # sources/citations 전달 (Perplexity 출처)
        if section.get("sources"):
            step_data["sources"] = section["sources"]
        steps[key] = step_data
    return steps


def _build_fallback(
    comparison: dict,
    paragraphs: list[str],
    briefing: Optional[DailyBriefing],
    briefing_stocks: list[BriefingStock],
    case_stocks: list[CaseStockRelation],
) -> dict:
    """6페이지 fallback 빌더."""
    title = comparison.get("title", "이 테마")
    return {
        "background": _build_background(briefing, briefing_stocks),
        "concept_explain": _build_concept_explain(comparison),
        "history": _build_history(comparison, paragraphs),
        "application": _build_application(comparison, paragraphs),
        "caution": _build_caution(comparison, paragraphs),
        "summary": _build_summary(comparison, case_stocks),
    }


# --- 개별 섹션 빌더 (fallback용) ---

def _build_background(briefing: Optional[DailyBriefing], briefing_stocks: list[BriefingStock]) -> dict:
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


def _build_concept_explain(comparison: dict) -> dict:
    """concept_explain 섹션: 금융 개념 설명 (fallback)."""
    title = comparison.get("title", "이 테마")
    return NarrativeSection(
        bullets=[
            f"{title}의 핵심 금융 개념을 설명해요.",
            "초보 투자자도 이해할 수 있도록 쉽게 풀어볼게요.",
        ],
        content=f"{title} 관련 금융 개념의 상세 설명을 준비 중이에요.",
    ).model_dump()


def _build_history(comparison: dict, paragraphs: list[str]) -> dict:
    """history 섹션: 과거 비슷한 사례."""
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


def _build_application(comparison: dict, paragraphs: list[str]) -> dict:
    """application 섹션: 현재 상황에 적용."""
    analysis = comparison.get("analysis", [])
    bullets = analysis[:3] if analysis else ["과거 사례를 현재에 적용해 볼게요."]
    content = highlight_terms(paragraphs[1]) if len(paragraphs) > 1 else ""
    chart = ChartData(
        title="과거 vs 현재 비교",
        data=[
            {"x": ["금리", "환율", "성장률"], "y": [2.5, 1100, 3.1], "type": "bar", "name": "과거", "marker": {"color": "#8B95A1"}},
            {"x": ["금리", "환율", "성장률"], "y": [3.5, 1350, 1.8], "type": "bar", "name": "현재", "marker": {"color": "#3B82F6"}},
        ],
        layout={"barmode": "group", "yaxis": {"title": "수치"}, "showlegend": True},
    )
    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def _build_caution(comparison: dict, paragraphs: list[str]) -> dict:
    """caution 섹션: 주의해야 할 점."""
    title = comparison.get("title", "이 테마")
    bullets = [
        f"{title}의 예상과 다른 전개가 나올 수 있어요.",
        f"외부 변수(금리, 환율, 규제)가 {title} 흐름을 바꿀 수 있어요.",
        f"단기 모멘텀에 과도하게 베팅하면 손실 위험이 있어요.",
    ]
    content = highlight_terms(paragraphs[2]) if len(paragraphs) > 2 else f"{title} 관련 주의사항을 꼭 체크해야 해요."
    chart = ChartData(
        title="리스크 시나리오별 예상 손실",
        data=[{"x": ["금리 급등", "규제 강화", "글로벌 침체"], "y": [-15, -20, -30], "type": "bar",
               "marker": {"color": ["#F59E0B", "#EF4444", "#991B1B"]}}],
        layout={"yaxis": {"title": "예상 손실률 (%)"}},
    )
    return NarrativeSection(bullets=bullets, content=content, chart=chart).model_dump()


def _build_summary(comparison: dict, case_stocks: list[CaseStockRelation]) -> dict:
    """summary 섹션: 최종 정리."""
    title = comparison.get("title", "이 테마")
    bullets = [
        f"{title} 분석 핵심 포인트를 정리했어요.",
    ]
    if case_stocks:
        stock_names = [r.stock_name for r in case_stocks[:3]]
        bullets.append(f"관련 종목: {', '.join(stock_names)}")

    return NarrativeSection(
        bullets=bullets,
        content=f"{title} 분석을 바탕으로 핵심 포인트를 정리하고, 리스크 관리 포인트를 체크하세요.",
    ).model_dump()
