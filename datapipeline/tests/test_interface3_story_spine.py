"""Interface3 서사축/소제목 후처리 테스트."""

from __future__ import annotations

from datapipeline.nodes.interface3 import (
    _enforce_story_spine,
    _has_placeholder_heading,
    _inject_markdown_sections,
)


def test_placeholder_heading_detection_variants() -> None:
    assert _has_placeholder_heading("### 소제목\n내용")
    assert _has_placeholder_heading("### 소제목 1:\n내용")
    assert _has_placeholder_heading("### heading-2\ncontent")
    assert _has_placeholder_heading("### 접두사\n내용")
    assert not _has_placeholder_heading("### 닮은 점\n내용")


def test_inject_markdown_sections_replaces_placeholder_heading() -> None:
    content = "### 소제목\n핵심 내용을 정리해요."
    injected = _inject_markdown_sections(2, content)

    assert "### 소제목" not in injected
    assert "### 개념 먼저 잡기" in injected
    assert "### 지금 왜 필요할까?" in injected


def test_enforce_story_spine_injects_required_anchors() -> None:
    pages = [
        {
            "step": 2,
            "title": "개념",
            "purpose": "오늘 배울 개념을 먼저 이해해요.",
            "content": "### 핵심\n지금 흐름을 설명해요.",
            "bullets": ["a", "b"],
            "chart": None,
        },
        {
            "step": 3,
            "title": "사례",
            "purpose": "과거 사례를 통해 메커니즘을 확인해요.",
            "content": "### 흐름\n비슷한 일이 있었어요.",
            "bullets": ["a", "b"],
            "chart": None,
        },
        {
            "step": 4,
            "title": "적용",
            "purpose": "과거와 현재를 비교해요.",
            "content": "### 비교\n지금 시장에 적용해요.",
            "bullets": ["a", "b"],
            "chart": None,
        },
        {
            "step": 6,
            "title": "체크",
            "purpose": "핵심만 정리해요.",
            "content": "- 점검1\n- 점검2",
            "bullets": ["점검1", "점검2", "점검3"],
            "chart": {"dummy": True},
        },
    ]
    raw_narrative = {
        "concept": {
            "name": "영업 레버리지",
            "definition": "매출이 늘 때 이익이 더 크게 움직이는 구조예요.",
            "relevance": "요즘처럼 거래대금이 늘 때 자주 보이는 패턴이에요.",
        },
        "historical_case": {
            "period": "2020~2021년",
            "title": "증권주 거래대금 급증 구간",
            "summary": "거래대금 증가가 수수료 이익으로 이어졌어요.",
        },
    }

    enforced = _enforce_story_spine(pages, raw_narrative)
    by_step = {page["step"]: page for page in enforced}

    assert "영업 레버리지" in by_step[2]["content"]
    assert (
        "2020~2021년" in by_step[3]["content"]
        or "증권주 거래대금 급증 구간" in by_step[3]["content"]
    )
    assert "### 닮은 점" in by_step[4]["content"]
    assert "### 다른 점" in by_step[4]["content"]
    assert by_step[6]["chart"] is None
    assert by_step[6]["content"].startswith("### 투자 전에 꼭 확인할 포인트")
