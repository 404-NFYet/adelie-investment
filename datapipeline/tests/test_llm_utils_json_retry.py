"""JSON 파싱 실패 재시도/폴백 동작 테스트."""

from __future__ import annotations

import pytest

from datapipeline.ai.llm_observability import reset_llm_stats
from datapipeline.ai.llm_response_cache import reset_llm_cache
from datapipeline.ai.llm_utils import JSONResponseParseError, call_llm_with_prompt
from datapipeline.prompts.prompt_loader import PromptSpec


def _json_prompt_spec() -> PromptSpec:
    return _json_prompt_spec_for("anthropic", "claude-sonnet-4-5-20250929")


def _json_prompt_spec_for(provider: str, model: str) -> PromptSpec:
    return PromptSpec(
        body='{"request":"test"}',
        provider=provider,
        model=model,
        temperature=0.7,
        response_format="json_object",
        system_message="테스트 시스템 메시지",
        max_tokens=1024,
        thinking=False,
        thinking_effort="medium",
    )


def _plain_prompt_spec() -> PromptSpec:
    return PromptSpec(
        body='{"request":"test"}',
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        temperature=0.7,
        response_format=None,
        system_message="테스트 시스템 메시지",
        max_tokens=1024,
        thinking=False,
        thinking_effort="medium",
    )


class ScriptedClient:
    """provider 순서와 응답 내용을 스크립트로 검증하는 테스트 더블."""

    def __init__(self, script: list[tuple[str, str | Exception]]) -> None:
        self._script = list(script)
        self.calls: list[dict] = []

    def chat_completion(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        if not self._script:
            raise AssertionError("No scripted response left for chat_completion call")

        expected_provider, payload = self._script.pop(0)
        assert kwargs["provider"] == expected_provider

        if isinstance(payload, Exception):
            raise payload

        if isinstance(payload, dict):
            content = payload.get("content", "{}")
            usage = payload.get("usage", {})
            return {
                "choices": [{"message": {"content": content}}],
                "usage": usage if isinstance(usage, dict) else {},
            }

        return {
            "choices": [{"message": {"content": payload}}],
            "usage": {},
        }


def _patch_prompt_and_client(monkeypatch: pytest.MonkeyPatch, spec: PromptSpec, client: ScriptedClient) -> None:
    monkeypatch.setattr("datapipeline.ai.llm_utils.load_prompt", lambda *args, **kwargs: spec)
    monkeypatch.setattr("datapipeline.ai.llm_utils.get_multi_provider_client", lambda: client)


@pytest.fixture(autouse=True)
def _reset_observability_and_cache() -> None:
    reset_llm_stats()
    reset_llm_cache()


def test_json_prompt_success_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("anthropic", '{"ok": true, "value": 1}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec(), client)

    result = call_llm_with_prompt("narrative_body", {"x": 1})

    assert result["ok"] is True
    assert len(client.calls) == 1
    assert client.calls[0]["response_format"] == {"type": "json_object"}
    assert "반드시 JSON object 하나만 반환" in client.calls[0]["messages"][0]["content"]


def test_anthropic_credit_error_falls_back_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("anthropic", RuntimeError("Error code: 400 - credit balance is too low")),
        ("openai", '{"ok": true, "fallback_used": true}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec(), client)

    result = call_llm_with_prompt("3_glossary", {"x": 1})

    assert result["ok"] is True
    assert result["fallback_used"] is True
    assert len(client.calls) == 2
    assert client.calls[0]["provider"] == "anthropic"
    assert client.calls[1]["provider"] == "openai"


def test_json_prompt_repair_success_on_second_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("anthropic", "BROKEN_JSON_OUTPUT"),
        ("anthropic", '{"broken": false, "fixed": true}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec(), client)

    result = call_llm_with_prompt("narrative_body", {"x": 1})

    assert result["fixed"] is True
    assert len(client.calls) == 2
    assert client.calls[1]["temperature"] == 0.0
    assert client.calls[1]["response_format"] == {"type": "json_object"}


def test_json_prompt_openai_fallback_on_third_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("anthropic", "BROKEN_JSON_OUTPUT_1"),
        ("anthropic", "BROKEN_JSON_OUTPUT_2"),
        ("openai", '{"fallback": true, "engine": "gpt-5.2"}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec(), client)

    result = call_llm_with_prompt("narrative_body", {"x": 1})

    assert result["fallback"] is True
    assert len(client.calls) == 3
    assert client.calls[2]["provider"] == "openai"
    assert client.calls[2]["model"] == "gpt-5.2"
    assert client.calls[2]["response_format"] == {"type": "json_object"}


def test_json_prompt_raises_after_all_retries_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("anthropic", "BROKEN_JSON_OUTPUT_1"),
        ("anthropic", "BROKEN_JSON_OUTPUT_2"),
        ("openai", "BROKEN_JSON_OUTPUT_3"),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec(), client)

    with pytest.raises(JSONResponseParseError) as exc_info:
        call_llm_with_prompt("narrative_body", {"x": 1})

    assert "모델 응답 JSON 불량" in str(exc_info.value)
    assert exc_info.value.prompt_name == "narrative_body"
    assert exc_info.value.provider == "anthropic"
    assert len(client.calls) == 3


def test_non_json_prompt_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("anthropic", '{"broken": true'),
    ])
    _patch_prompt_and_client(monkeypatch, _plain_prompt_spec(), client)

    with pytest.raises(Exception):
        call_llm_with_prompt("non_json_prompt", {"x": 1})

    assert len(client.calls) == 1


def test_openai_provider_retries_once_on_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("openai", RuntimeError("upstream timeout")),
        ("openai", '{"ok": true, "retried": true}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec_for("openai", "gpt-5.2"), client)

    result = call_llm_with_prompt("narrative_body", {"x": 1})

    assert result["ok"] is True
    assert result["retried"] is True
    assert len(client.calls) == 2
    assert client.calls[0]["provider"] == "openai"
    assert client.calls[1]["provider"] == "openai"
    assert client.calls[1]["model"] == "gpt-5.2"


def test_openai_provider_does_not_use_third_fallback_for_json_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedClient([
        ("openai", "BROKEN_JSON_OUTPUT_1"),
        ("openai", "BROKEN_JSON_OUTPUT_2"),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec_for("openai", "gpt-5.2"), client)

    with pytest.raises(JSONResponseParseError) as exc_info:
        call_llm_with_prompt("narrative_body", {"x": 1})

    assert "동일 OpenAI 모델로 재시도/복구까지 실패" in str(exc_info.value)
    assert exc_info.value.provider == "openai"
    assert exc_info.value.model == "gpt-5.2"
    assert len(client.calls) == 2


def test_narrative_body_node_marks_json_parse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from datapipeline.nodes.interface2 import run_narrative_body_node

    def _raise_json_parse(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise JSONResponseParseError(
            prompt_name="narrative_body",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            detail="테스트 JSON 파싱 실패",
        )

    monkeypatch.setattr("datapipeline.nodes.interface2.call_llm_with_prompt", _raise_json_parse)

    state = {
        "curated_context": {"theme": "test"},
        "page_purpose": {"theme": "t", "one_liner": "o", "concept": {}},
        "historical_case": {"historical_case": {"title": "t"}},
        "backend": "live",
        "metrics": {},
    }
    result = run_narrative_body_node(state)

    assert "error" in result
    assert "모델 응답 JSON 불량" in result["error"]
    assert "prompt=narrative_body" in result["error"]
    assert "provider=anthropic" in result["error"]


def test_cache_reuses_same_prompt_and_reduces_call_count(monkeypatch: pytest.MonkeyPatch) -> None:
    from datapipeline.ai.llm_observability import snapshot_llm_stats

    client = ScriptedClient([
        ("openai", '{"ok": true, "cached": false}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec_for("openai", "gpt-5.2"), client)

    first = call_llm_with_prompt("narrative_body", {"x": 1})
    second = call_llm_with_prompt("narrative_body", {"x": 1})
    stats = snapshot_llm_stats()
    prompt_stats = stats["by_prompt"]["narrative_body"]

    assert first["ok"] is True and second["ok"] is True
    assert len(client.calls) == 1
    assert prompt_stats["calls"] <= 1
    assert prompt_stats["events"].get("cache_hit", 0) >= 1


def test_retry_path_has_call_count_guardrail(monkeypatch: pytest.MonkeyPatch) -> None:
    from datapipeline.ai.llm_observability import snapshot_llm_stats

    client = ScriptedClient([
        ("openai", RuntimeError("upstream timeout")),
        ("openai", '{"ok": true, "retried": true}'),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec_for("openai", "gpt-5.2"), client)

    result = call_llm_with_prompt("3_theme", {"x": 1})
    stats = snapshot_llm_stats()
    prompt_stats = stats["by_prompt"]["3_theme"]

    assert result["retried"] is True
    assert 1 <= len(client.calls) <= 2
    assert 1 <= prompt_stats["calls"] <= 2


def test_token_budget_guardrail_for_single_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    from datapipeline.ai.llm_observability import snapshot_llm_stats

    client = ScriptedClient([
        ("openai", {
            "content": '{"ok": true, "value": 1}',
            "usage": {"prompt_tokens": 220, "completion_tokens": 140},
        }),
    ])
    _patch_prompt_and_client(monkeypatch, _json_prompt_spec_for("openai", "gpt-5-mini"), client)

    result = call_llm_with_prompt("page_purpose", {"x": 1})
    stats = snapshot_llm_stats()
    prompt_stats = stats["by_prompt"]["page_purpose"]

    assert result["ok"] is True
    assert prompt_stats["prompt_tokens"] <= 300
    assert prompt_stats["completion_tokens"] <= 200
