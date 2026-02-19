"""LLM 응답 캐시.

동일 프롬프트/모델/메시지 요청을 TTL 범위 내에서 재사용한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from typing import Any

_LOCK = Lock()
_CACHE: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()

_CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", "900"))
_CACHE_MAX_ENTRIES = int(os.getenv("LLM_CACHE_MAX_ENTRIES", "512"))


def is_cache_enabled() -> bool:
    return _CACHE_ENABLED and _CACHE_TTL_SECONDS > 0 and _CACHE_MAX_ENTRIES > 0


def _now() -> float:
    return time.time()


def _prune_expired(now_ts: float) -> None:
    expired: list[str] = []
    for key, (created_at, _) in _CACHE.items():
        if now_ts - created_at > _CACHE_TTL_SECONDS:
            expired.append(key)
        else:
            break
    for key in expired:
        _CACHE.pop(key, None)


def _prune_oversize() -> None:
    while len(_CACHE) > _CACHE_MAX_ENTRIES:
        _CACHE.popitem(last=False)


def build_cache_key(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_cached_response(cache_key: str) -> dict[str, Any] | None:
    if not is_cache_enabled():
        return None
    now_ts = _now()
    with _LOCK:
        _prune_expired(now_ts)
        entry = _CACHE.get(cache_key)
        if entry is None:
            return None
        created_at, value = entry
        if now_ts - created_at > _CACHE_TTL_SECONDS:
            _CACHE.pop(cache_key, None)
            return None
        _CACHE.move_to_end(cache_key)
        return deepcopy(value)


def set_cached_response(cache_key: str, value: dict[str, Any]) -> None:
    if not is_cache_enabled():
        return
    now_ts = _now()
    with _LOCK:
        _prune_expired(now_ts)
        _CACHE[cache_key] = (now_ts, deepcopy(value))
        _CACHE.move_to_end(cache_key)
        _prune_oversize()


def reset_llm_cache() -> None:
    """테스트/런 경계에서 캐시를 비운다."""
    with _LOCK:
        _CACHE.clear()
