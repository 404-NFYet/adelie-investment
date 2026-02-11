"""내러티브 구조 검증 모듈.

Pydantic v2 모델로 LLM이 생성한 6페이지 골든케이스 구조를 검증한다.
"""

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator

LOGGER = logging.getLogger(__name__)

# 6페이지 골든케이스 키 (pipeline_config.PAGE_KEYS와 동일하나 Docker 의존성 최소화를 위해 로컬 정의)
REQUIRED_STEP_KEYS = [
    "background", "concept_explain", "history",
    "application", "caution", "summary",
]

# 콘텐츠 품질 기준 (pipeline_config 값과 동일)
MIN_CONTENT_LENGTH = 150
MIN_BULLETS = 3


# ── Pydantic 검증 모델 ──

class ChartTrace(BaseModel):
    """Plotly chart trace 검증."""
    x: list[Any]
    y: list[float | int]
    type: str = "scatter"

    @field_validator("y")
    @classmethod
    def y_must_have_numeric_values(cls, v: list) -> list:
        if not v:
            raise ValueError("y 리스트가 비어있음")
        if all(val == 0 for val in v):
            raise ValueError("y값이 모두 0")
        return v

    @model_validator(mode="after")
    def x_y_same_length(self) -> "ChartTrace":
        if len(self.x) != len(self.y):
            raise ValueError(f"x({len(self.x)})와 y({len(self.y)}) 길이 불일치")
        return self


class ChartSchema(BaseModel):
    """Plotly chart 전체 검증."""
    data: list[dict[str, Any]]
    layout: dict[str, Any] = {}

    @field_validator("data")
    @classmethod
    def data_must_have_valid_traces(cls, v: list) -> list:
        if not v:
            raise ValueError("chart data가 비어있음")
        first = v[0]
        if not isinstance(first, dict):
            raise ValueError("첫 trace가 dict가 아님")
        ChartTrace(**first)
        return v


class StepData(BaseModel):
    """한 페이지의 데이터 검증."""
    content: str
    bullets: list[str] = []
    glossary: list[str] = []
    chart: Optional[dict[str, Any]] = None

    @field_validator("content")
    @classmethod
    def content_min_length(cls, v: str) -> str:
        if len(v.strip()) < MIN_CONTENT_LENGTH:
            raise ValueError(
                f"content가 너무 짧음 ({len(v.strip())}자, 최소 {MIN_CONTENT_LENGTH}자)"
            )
        return v

    @field_validator("bullets")
    @classmethod
    def bullets_min_count(cls, v: list) -> list:
        if len(v) < MIN_BULLETS:
            raise ValueError(f"bullets가 {len(v)}개, 최소 {MIN_BULLETS}개 필요")
        return v


class NarrativeSteps(BaseModel):
    """6페이지 골든케이스 전체 내러티브 검증."""
    background: StepData
    concept_explain: StepData
    history: StepData
    application: StepData
    caution: StepData
    summary: StepData


# ── 검증 함수 ──

def validate_narrative(narrative_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """내러티브 구조를 검증한다.

    Returns:
        (is_valid, issues): 검증 통과 여부와 문제점 리스트
    """
    issues: list[str] = []

    # 6개 페이지 존재 확인
    for key in REQUIRED_STEP_KEYS:
        if key not in narrative_data:
            issues.append(f"페이지 누락: {key}")

    if issues:
        return False, issues

    # Pydantic 모델로 구조 검증
    try:
        NarrativeSteps(**narrative_data)
    except Exception as e:
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = " → ".join(str(l) for l in err.get("loc", []))
                msg = err.get("msg", "")
                issues.append(f"{loc}: {msg}")
        else:
            issues.append(f"구조 검증 실패: {str(e)[:200]}")
        return False, issues

    # 차트 검증 (경고 레벨, 실패하지는 않음)
    chart_issues: list[str] = []
    for key in REQUIRED_STEP_KEYS:
        section = narrative_data.get(key, {})
        chart = section.get("chart")
        if chart and isinstance(chart, dict):
            try:
                ChartSchema(**chart)
            except Exception as e:
                chart_issues.append(f"{key} chart: {e}")

    if chart_issues:
        for ci in chart_issues:
            LOGGER.warning("[VALIDATOR] %s", ci)

    return True, issues


def get_quality_score(narrative_data: dict[str, Any]) -> dict[str, Any]:
    """내러티브 품질 점수 계산.

    Returns:
        품질 메트릭 딕셔너리
    """
    metrics: dict[str, Any] = {
        "pages_count": 0,
        "pages_with_chart": 0,
        "chart_type_distribution": {},
        "avg_content_length": 0,
        "total_bullets": 0,
        "total_glossary_terms": 0,
        "mark_tag_count": 0,
    }

    total_content_len = 0

    for key in REQUIRED_STEP_KEYS:
        section = narrative_data.get(key)
        if not isinstance(section, dict):
            continue
        metrics["pages_count"] += 1

        content = str(section.get("content", ""))
        total_content_len += len(content)
        metrics["mark_tag_count"] += len(re.findall(r"<mark", content))

        bullets = section.get("bullets", [])
        if isinstance(bullets, list):
            metrics["total_bullets"] += len(bullets)

        glossary = section.get("glossary", [])
        if isinstance(glossary, list):
            metrics["total_glossary_terms"] += len(glossary)

        chart = section.get("chart", {})
        if isinstance(chart, dict):
            data = chart.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                metrics["pages_with_chart"] += 1
                first_trace = data[0]
                if isinstance(first_trace, dict):
                    ct = first_trace.get("type", "unknown")
                    metrics["chart_type_distribution"][ct] = (
                        metrics["chart_type_distribution"].get(ct, 0) + 1
                    )

    if metrics["pages_count"] > 0:
        metrics["avg_content_length"] = round(
            total_content_len / metrics["pages_count"]
        )

    return metrics
