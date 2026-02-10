"""파이프라인 타입 정의 - 실험용."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KeywordPlan:
    """키워드 추출 결과."""

    category: str
    keyword: str
    title: str
    context: str
    domain: str = "macro"
    mirroring_hint: str = ""


@dataclass
class PromptSpec:
    """프롬프트 템플릿 파싱 결과."""

    body: str
    model_key: str = ""
    temperature: float = 0.7
    response_format: str | None = None
    role: str = ""
    system_message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    """시나리오 생성 결과."""

    keyword: str
    title: str
    summary: str
    narrative: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, str]] = field(default_factory=list)
    related_companies: list[dict[str, str]] = field(default_factory=list)
    mirroring_data: dict[str, Any] = field(default_factory=dict)
    glossary: dict[str, str] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """파이프라인 전체 실행 결과."""

    date: str
    scenarios: list[ScenarioResult] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
