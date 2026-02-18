"""LLM 호출 관측/집계 유틸.

파이프라인 1회 실행 단위로 호출 수/토큰/지연/이벤트를 누적 집계한다.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from threading import Lock
from typing import Any

_LOCK = Lock()

_STATS: dict[str, Any] = {
    "totals": {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "elapsed_s": 0.0,
    },
    "by_prompt": defaultdict(
        lambda: {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elapsed_s": 0.0,
            "events": defaultdict(int),
            "providers": defaultdict(int),
            "models": defaultdict(int),
        }
    ),
}


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def reset_llm_stats() -> None:
    """누적 통계를 초기화한다."""
    with _LOCK:
        _STATS["totals"] = {
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elapsed_s": 0.0,
        }
        _STATS["by_prompt"].clear()


def record_llm_call(
    *,
    prompt_name: str,
    provider: str,
    model: str,
    usage: dict[str, Any] | None,
    elapsed_s: float,
) -> None:
    """LLM 1회 호출 결과를 기록한다."""
    prompt_tokens = _to_int((usage or {}).get("prompt_tokens"))
    completion_tokens = _to_int((usage or {}).get("completion_tokens"))
    elapsed = _to_float(elapsed_s)
    name = str(prompt_name or "unknown")
    provider_name = str(provider or "unknown")
    model_name = str(model or "unknown")

    with _LOCK:
        totals = _STATS["totals"]
        totals["calls"] += 1
        totals["prompt_tokens"] += prompt_tokens
        totals["completion_tokens"] += completion_tokens
        totals["elapsed_s"] += elapsed

        bucket = _STATS["by_prompt"][name]
        bucket["calls"] += 1
        bucket["prompt_tokens"] += prompt_tokens
        bucket["completion_tokens"] += completion_tokens
        bucket["elapsed_s"] += elapsed
        bucket["providers"][provider_name] += 1
        bucket["models"][model_name] += 1


def record_llm_event(*, prompt_name: str, event: str) -> None:
    """재시도/폴백/파싱실패 등 이벤트를 기록한다."""
    name = str(prompt_name or "unknown")
    event_name = str(event or "unknown")
    with _LOCK:
        bucket = _STATS["by_prompt"][name]
        bucket["events"][event_name] += 1


def snapshot_llm_stats() -> dict[str, Any]:
    """현재 통계 스냅샷을 반환한다."""
    with _LOCK:
        payload = {
            "totals": deepcopy(_STATS["totals"]),
            "by_prompt": {},
        }
        for prompt, values in _STATS["by_prompt"].items():
            payload["by_prompt"][prompt] = {
                "calls": values["calls"],
                "prompt_tokens": values["prompt_tokens"],
                "completion_tokens": values["completion_tokens"],
                "elapsed_s": round(values["elapsed_s"], 4),
                "events": dict(values["events"]),
                "providers": dict(values["providers"]),
                "models": dict(values["models"]),
            }
        payload["totals"]["elapsed_s"] = round(payload["totals"]["elapsed_s"], 4)
        return payload
