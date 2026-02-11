"""내러티브 스토리 응답 스키마 (6페이지 골든케이스)."""

from typing import Any, Optional

from pydantic import BaseModel


class ChartDataPoint(BaseModel):
    """차트 데이터 포인트."""

    label: str
    value: float
    color: Optional[str] = None


class ChartData(BaseModel):
    """차트 데이터 (비교 바, 트렌드 라인, 리스크 지표 등)."""

    chart_type: Optional[str] = None  # comparison_bar, trend_line 등 (fallback용)
    title: Optional[str] = None
    unit: Optional[str] = None
    data_points: list[ChartDataPoint] = []
    annotation: Optional[str] = None
    # Plotly 직접 렌더링용
    data: Optional[list[dict]] = None
    layout: Optional[dict] = None


class ComparisonPoint(BaseModel):
    """과거-현재 비교 포인트."""

    aspect: str
    past: str
    present: str
    similarity: str  # 유사, 상이, 부분 유사


class GlossaryItem(BaseModel):
    """페이지별 용어 설명."""

    term: str
    definition: str
    domain: str = ""  # 금융, 산업, 국제 등


class SourceInfo(BaseModel):
    """출처 정보."""

    name: str
    url_domain: str
    used_in_pages: list[int] = []


class HallucinationCheck(BaseModel):
    """환각 체크리스트."""

    claim: str
    source: str
    risk: str = "중간"  # 낮음, 중간, 높음
    note: str = ""


class ConceptInfo(BaseModel):
    """핵심 금융 개념."""

    name: str
    definition: str
    relevance: str = ""


class HistoricalCaseInfo(BaseModel):
    """과거 유사 사례 구조화 정보."""

    period: str = ""
    title: str = ""
    summary: str = ""
    outcome: str = ""
    lesson: str = ""


class NarrativeSection(BaseModel):
    """내러티브 한 섹션 (6페이지 골든케이스)."""

    content: str = ""
    bullets: list[str] = []
    chart: Optional[Any] = None  # Plotly {data, layout} dict
    glossary: list[GlossaryItem] = []  # 페이지별 용어
    sources: Optional[list[dict]] = None  # Perplexity 출처 등


class NarrativeSteps(BaseModel):
    """6페이지 골든케이스 내러티브."""

    background: NarrativeSection = NarrativeSection()
    concept_explain: NarrativeSection = NarrativeSection()
    history: NarrativeSection = NarrativeSection()
    application: NarrativeSection = NarrativeSection()
    caution: NarrativeSection = NarrativeSection()
    summary: NarrativeSection = NarrativeSection()


class NarrativeResponse(BaseModel):
    """내러티브 전체 응답 (6페이지 골든케이스)."""

    case_id: int
    keyword: str
    theme: str = ""
    one_liner: str = ""
    generated_at: Optional[str] = None
    steps: dict[str, Any]  # NarrativeSteps 호환, dict로 유연하게
    concept: Optional[ConceptInfo] = None
    historical_case: Optional[HistoricalCaseInfo] = None
    sources: list[dict] = []
    hallucination_checklist: list[dict] = []
    related_companies: list[dict] = []
    sync_rate: int = 0
    market_data: Optional[dict] = None
    market_history: Optional[list[dict]] = None
