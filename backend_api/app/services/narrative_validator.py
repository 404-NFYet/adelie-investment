"""내러티브 구조 검증 모듈.

Pydantic v2 모델로 LLM이 생성한 7단계 내러티브 구조를 엄격히 검증한다.
"""

import logging
from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

LOGGER = logging.getLogger(__name__)

# 프론트엔드 표시 순서와 동일한 7단계
REQUIRED_STEP_KEYS = [
    "background", "mirroring", "simulation", "result",
    "difference", "devils_advocate", "action",
]


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
        # 첫 trace만 엄격 검증
        first = v[0]
        if not isinstance(first, dict):
            raise ValueError("첫 trace가 dict가 아님")
        ChartTrace(**first)
        return v


class QuizOption(BaseModel):
    """퀴즈 선택지."""
    id: str
    label: str
    explanation: str = ""


class QuizSchema(BaseModel):
    """퀴즈 데이터 검증."""
    context: str = ""
    question: str
    options: list[QuizOption]
    correct_answer: Literal["up", "down", "sideways"]
    actual_result: str = ""
    lesson: str = ""

    @field_validator("options")
    @classmethod
    def options_must_have_three(cls, v: list) -> list:
        if len(v) < 3:
            raise ValueError(f"options {len(v)}개, 최소 3개 필요")
        return v


class StepData(BaseModel):
    """한 섹션의 데이터 검증."""
    content: str
    bullets: list[str] = []
    chart: Optional[dict[str, Any]] = None
    quiz: Optional[dict[str, Any]] = None  # simulation 전용

    @field_validator("content")
    @classmethod
    def content_min_length(cls, v: str) -> str:
        if len(v.strip()) < 20:
            raise ValueError(f"content가 너무 짧음 ({len(v.strip())}자, 최소 20자)")
        return v

    @field_validator("bullets")
    @classmethod
    def bullets_min_one(cls, v: list) -> list:
        if len(v) < 1:
            raise ValueError("bullets가 최소 1개 필요")
        return v


class NarrativeSteps(BaseModel):
    """7단계 전체 내러티브 검증."""
    background: StepData
    mirroring: StepData
    simulation: StepData
    result: StepData
    difference: StepData
    devils_advocate: StepData
    action: StepData

    @model_validator(mode="after")
    def validate_section_specifics(self) -> "NarrativeSteps":
        # devils_advocate bullets 3개 필수
        if len(self.devils_advocate.bullets) < 3:
            raise ValueError(
                f"devils_advocate bullets {len(self.devils_advocate.bullets)}개, 3개 필수"
            )

        # simulation quiz 필수
        if not self.simulation.quiz:
            raise ValueError("simulation에 quiz가 없음")

        return self


# ── 검증 함수 ──

def validate_narrative(narrative_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """내러티브 구조를 검증한다.

    Returns:
        (is_valid, issues): 검증 통과 여부와 문제점 리스트
    """
    issues: list[str] = []

    # 7개 섹션 존재 확인
    for key in REQUIRED_STEP_KEYS:
        if key not in narrative_data:
            issues.append(f"섹션 누락: {key}")

    if issues:
        return False, issues

    # Pydantic 모델로 구조 검증
    try:
        NarrativeSteps(**narrative_data)
    except Exception as e:
        error_msg = str(e)
        # Pydantic ValidationError에서 개별 에러 추출
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = " → ".join(str(l) for l in err.get("loc", []))
                msg = err.get("msg", "")
                issues.append(f"{loc}: {msg}")
        else:
            issues.append(f"구조 검증 실패: {error_msg[:200]}")
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

    # simulation quiz 상세 검증
    sim_quiz = narrative_data.get("simulation", {}).get("quiz")
    if sim_quiz and isinstance(sim_quiz, dict):
        try:
            QuizSchema(**sim_quiz)
        except Exception as e:
            issues.append(f"simulation quiz: {e}")
            return False, issues

    return True, issues


def get_quality_score(narrative_data: dict[str, Any]) -> dict[str, Any]:
    """내러티브 품질 점수 계산.

    Returns:
        품질 메트릭 딕셔너리
    """
    metrics: dict[str, Any] = {
        "sections_count": 0,
        "sections_with_chart": 0,
        "chart_type_distribution": {},
        "has_quiz": False,
        "avg_content_length": 0,
        "total_bullets": 0,
        "mark_tag_count": 0,
    }

    total_content_len = 0
    import re

    for key in REQUIRED_STEP_KEYS:
        section = narrative_data.get(key)
        if not isinstance(section, dict):
            continue
        metrics["sections_count"] += 1

        content = str(section.get("content", ""))
        total_content_len += len(content)
        metrics["mark_tag_count"] += len(re.findall(r"<mark", content))

        bullets = section.get("bullets", [])
        if isinstance(bullets, list):
            metrics["total_bullets"] += len(bullets)

        chart = section.get("chart", {})
        if isinstance(chart, dict):
            data = chart.get("data", [])
            if isinstance(data, list) and len(data) > 0:
                metrics["sections_with_chart"] += 1
                first_trace = data[0]
                if isinstance(first_trace, dict):
                    ct = first_trace.get("type", "unknown")
                    metrics["chart_type_distribution"][ct] = (
                        metrics["chart_type_distribution"].get(ct, 0) + 1
                    )

        if key == "simulation" and isinstance(section.get("quiz"), dict):
            metrics["has_quiz"] = True

    if metrics["sections_count"] > 0:
        metrics["avg_content_length"] = round(
            total_content_len / metrics["sections_count"]
        )

    return metrics
