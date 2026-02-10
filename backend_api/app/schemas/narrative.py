"""내러티브 스토리 응답 스키마 (7단계)."""

from typing import Any, Optional

from pydantic import BaseModel


class ChartDataPoint(BaseModel):
    """차트 데이터 포인트."""

    label: str
    value: float
    color: Optional[str] = None


class ChartData(BaseModel):
    """차트 데이터 (비교 바, 트렌드 라인, 리스크 지표 등)."""

    chart_type: Optional[str] = None  # comparison_bar, trend_line 등 (기존 호환)
    title: Optional[str] = None
    unit: Optional[str] = None
    data_points: list[ChartDataPoint] = []
    annotation: Optional[str] = None
    # Plotly 직접 렌더링용 (7단계 narrative)
    data: Optional[list[dict]] = None
    layout: Optional[dict] = None


class ComparisonPoint(BaseModel):
    """과거-현재 비교 포인트."""

    aspect: str
    past: str
    present: str
    similarity: str  # 유사, 상이, 부분 유사


class QuizOption(BaseModel):
    """퀴즈 선택지."""

    id: str
    label: str
    explanation: str = ""


class QuizData(BaseModel):
    """퀴즈 데이터."""

    context: str = ""
    question: str = ""
    options: list[QuizOption] = []
    correct_answer: str = "up"  # "up" | "down" | "sideways"
    actual_result: str = ""
    lesson: str = ""


class NarrativeSection(BaseModel):
    """내러티브 한 섹션."""

    bullets: list[str] = []
    content: str = ""
    chart: Optional[Any] = None  # ChartData 또는 Plotly {data, layout} dict
    comparison_points: Optional[list[ComparisonPoint]] = None
    quiz: Optional[QuizData] = None  # simulation 섹션 전용
    sources: Optional[list[dict]] = None  # Perplexity 출처 등


class NarrativeSteps(BaseModel):
    """7단계 내러티브 타입화."""

    background: NarrativeSection = NarrativeSection()
    mirroring: NarrativeSection = NarrativeSection()
    simulation: NarrativeSection = NarrativeSection()
    result: NarrativeSection = NarrativeSection()
    difference: NarrativeSection = NarrativeSection()
    devils_advocate: NarrativeSection = NarrativeSection()
    action: NarrativeSection = NarrativeSection()


class NarrativeResponse(BaseModel):
    """내러티브 전체 응답 (7단계)."""

    case_id: int
    keyword: str
    steps: dict[str, Any]  # NarrativeSteps 호환, dict로 유연하게 (기존 호환)
    related_companies: list[dict] = []
    sync_rate: int = 0
    market_data: Optional[dict] = None
    market_history: Optional[list[dict]] = None
