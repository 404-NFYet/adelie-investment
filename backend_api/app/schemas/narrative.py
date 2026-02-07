"""내러티브 스토리 응답 스키마."""

from typing import Optional

from pydantic import BaseModel


class ChartDataPoint(BaseModel):
    """차트 데이터 포인트."""

    label: str
    value: float
    color: Optional[str] = None


class ChartData(BaseModel):
    """차트 데이터 (비교 바, 트렌드 라인, 리스크 지표 등)."""

    chart_type: str  # comparison_bar, trend_line, risk_indicator, single_bar 등
    title: Optional[str] = None
    unit: Optional[str] = None
    data_points: list[ChartDataPoint] = []
    annotation: Optional[str] = None


class ComparisonPoint(BaseModel):
    """과거-현재 비교 포인트."""

    aspect: str
    past: str
    present: str
    similarity: str  # 유사, 상이, 부분 유사


class NarrativeSection(BaseModel):
    """내러티브 한 섹션 (도입, 전개, 절정, 결론 등)."""

    bullets: list[str] = []
    content: str = ""
    chart: Optional[ChartData] = None
    comparison_points: Optional[list[ComparisonPoint]] = None


class NarrativeResponse(BaseModel):
    """내러티브 전체 응답."""

    case_id: int
    keyword: str
    steps: dict  # keys: mirroring, intro, development, climax, conclusion
    related_companies: list[dict] = []
    sync_rate: int = 0
    market_data: Optional[dict] = None
    market_history: Optional[list[dict]] = None
