"""LLM 사용량 가드레일 테스트."""

from __future__ import annotations

from datapipeline.ai.llm_observability import (
    record_llm_call,
    record_llm_event,
    reset_llm_stats,
    snapshot_llm_stats,
)


def test_observability_totals_guardrail() -> None:
    reset_llm_stats()
    record_llm_call(
        prompt_name="narrative_body",
        provider="openai",
        model="gpt-5.2",
        usage={"prompt_tokens": 700, "completion_tokens": 420},
        elapsed_s=1.25,
    )
    record_llm_call(
        prompt_name="3_tone_final",
        provider="openai",
        model="gpt-5.2",
        usage={"prompt_tokens": 500, "completion_tokens": 280},
        elapsed_s=0.95,
    )
    record_llm_event(prompt_name="narrative_body", event="json_parse_retry")

    snap = snapshot_llm_stats()

    assert snap["totals"]["calls"] <= 3
    assert snap["totals"]["prompt_tokens"] <= 1500
    assert snap["totals"]["completion_tokens"] <= 800
    assert snap["by_prompt"]["narrative_body"]["events"]["json_parse_retry"] == 1
