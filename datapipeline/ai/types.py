"""파이프라인 데이터 타입 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class KeywordPlan:
    """키워드 추출 결과."""
    category: str        # Macro Economy, Technology, Energy, Policy 등
    domain: str          # macro, technology, energy, policy 등
    keyword: str         # 핵심 키워드
    title: str           # 시나리오 제목
    context: str         # 왜 중요한지 설명
    mirroring_hint: str  # 유사한 과거 사례 힌트


@dataclass
class ScenarioResult:
    """시나리오 생성 결과."""
    keyword: KeywordPlan
    context_research: str
    simulation_research: str
    narrative: dict[str, Any]  # 7단계 내러티브
    glossary: dict[str, str]   # 용어 사전
    similarity_score: int = 75


@dataclass
class BriefingResult:
    """브리핑 생성 결과."""
    date: str
    scenarios: list[ScenarioResult]
    rss_source_count: int = 0
