"""멀티 프로바이더 AI 클라이언트.

datapipeline/ai/multi_provider_client.py에서 복제.
config 의존을 제거하고 환경변수를 직접 참조한다.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from contextlib import contextmanager
from typing import Any, Optional

from openai import OpenAI

from ..config import OPENAI_API_KEY, PERPLEXITY_API_KEY, ANTHROPIC_API_KEY

LOGGER = logging.getLogger(__name__)

OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180"))
PERPLEXITY_TIMEOUT_SECONDS = float(os.getenv("PERPLEXITY_TIMEOUT_SECONDS", "60"))
LLM_MAX_CONCURRENCY = max(1, int(os.getenv("LLM_MAX_CONCURRENCY", "6")))
OPENAI_MAX_CONCURRENCY = max(1, int(os.getenv("OPENAI_MAX_CONCURRENCY", "4")))
PERPLEXITY_MAX_CONCURRENCY = max(1, int(os.getenv("PERPLEXITY_MAX_CONCURRENCY", "2")))
ANTHROPIC_MAX_CONCURRENCY = max(1, int(os.getenv("ANTHROPIC_MAX_CONCURRENCY", "2")))
PROVIDER_MAX_RETRIES = max(0, int(os.getenv("PROVIDER_MAX_RETRIES", "1")))
PROVIDER_BACKOFF_BASE_SECONDS = float(os.getenv("PROVIDER_BACKOFF_BASE_SECONDS", "1.0"))
PROVIDER_BACKOFF_MAX_SECONDS = float(os.getenv("PROVIDER_BACKOFF_MAX_SECONDS", "8.0"))
_RETRYABLE_ERROR_KEYWORDS = (
    "timeout",
    "timed out",
    "connection reset",
    "connection aborted",
    "temporarily unavailable",
    "service unavailable",
    "rate limit",
    "too many requests",
    "429",
    "502",
    "503",
    "504",
    "bad gateway",
)


class MultiProviderClient:
    """OpenAI, Perplexity, Anthropic을 통합 관리하는 AI 클라이언트."""

    def __init__(
        self,
        openai_key: str = "",
        perplexity_key: str = "",
        anthropic_key: str = "",
    ) -> None:
        openai_key = openai_key or OPENAI_API_KEY
        perplexity_key = perplexity_key or PERPLEXITY_API_KEY
        anthropic_key = anthropic_key or ANTHROPIC_API_KEY

        self.providers: dict[str, Any] = {}
        self._global_semaphore = threading.BoundedSemaphore(LLM_MAX_CONCURRENCY)
        self._provider_semaphores: dict[str, threading.BoundedSemaphore] = {
            "openai": threading.BoundedSemaphore(OPENAI_MAX_CONCURRENCY),
            "perplexity": threading.BoundedSemaphore(PERPLEXITY_MAX_CONCURRENCY),
            "anthropic": threading.BoundedSemaphore(ANTHROPIC_MAX_CONCURRENCY),
        }

        # OpenAI
        if openai_key:
            self.providers["openai"] = OpenAI(
                api_key=openai_key,
                timeout=OPENAI_TIMEOUT_SECONDS,
            )
            LOGGER.info("OpenAI provider initialized")

        # Perplexity (OpenAI 호환 API)
        if perplexity_key:
            self.providers["perplexity"] = OpenAI(
                api_key=perplexity_key,
                base_url="https://api.perplexity.ai",
                timeout=PERPLEXITY_TIMEOUT_SECONDS,
            )
            LOGGER.info("Perplexity provider initialized")

        # Anthropic (선택적)
        if anthropic_key:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic(api_key=anthropic_key)
                self.providers["anthropic"] = self._anthropic_client
                LOGGER.info("Anthropic provider initialized")
            except ImportError:
                LOGGER.warning("anthropic 패키지 미설치 - pip install anthropic")

    @contextmanager
    def _provider_slot(self, provider: str):
        provider_sem = self._provider_semaphores.get(provider)
        self._global_semaphore.acquire()
        if provider_sem is not None:
            provider_sem.acquire()
        try:
            yield
        finally:
            if provider_sem is not None:
                provider_sem.release()
            self._global_semaphore.release()

    def _is_retryable_error(self, exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return True
        lower = str(exc).lower()
        return any(keyword in lower for keyword in _RETRYABLE_ERROR_KEYWORDS)

    def _compute_backoff_seconds(self, attempt: int) -> float:
        base = max(0.1, PROVIDER_BACKOFF_BASE_SECONDS)
        cap = max(base, PROVIDER_BACKOFF_MAX_SECONDS)
        wait = min(cap, base * (2 ** max(0, attempt - 1)))
        return wait + random.uniform(0, min(0.5, wait * 0.2))

    def chat_completion(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        thinking: bool = False,
        thinking_effort: str = "medium",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """프로바이더별 chat completion 호출."""
        if provider not in self.providers:
            raise ValueError(
                f"프로바이더 '{provider}'가 초기화되지 않았습니다. "
                f"사용 가능: {list(self.providers.keys())}"
            )

        max_attempts = 1 + PROVIDER_MAX_RETRIES
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            started = time.perf_counter()
            LOGGER.info(
                "[%s] start model=%s messages=%d thinking=%s attempt=%d/%d",
                provider.upper(), model, len(messages), thinking, attempt, max_attempts,
            )
            try:
                with self._provider_slot(provider):
                    if provider == "anthropic":
                        result = self._call_anthropic(model, messages, temperature, max_tokens)
                    else:
                        result = self._call_openai_compatible(
                            provider, model, messages, thinking, thinking_effort,
                            temperature, max_tokens, response_format, **kwargs,
                        )
                elapsed = time.perf_counter() - started
                LOGGER.info("[%s] done model=%s elapsed=%.2fs", provider.upper(), model, elapsed)
                return result
            except Exception as exc:
                last_exc = exc
                elapsed = time.perf_counter() - started
                retryable = self._is_retryable_error(exc)
                if retryable and attempt < max_attempts:
                    wait_s = self._compute_backoff_seconds(attempt)
                    LOGGER.warning(
                        "[%s] retryable error model=%s elapsed=%.2fs attempt=%d/%d wait=%.2fs err=%s",
                        provider.upper(),
                        model,
                        elapsed,
                        attempt,
                        max_attempts,
                        wait_s,
                        exc,
                    )
                    time.sleep(wait_s)
                    continue
                LOGGER.error(
                    "[%s] error model=%s elapsed=%.2fs retryable=%s attempt=%d/%d: %s",
                    provider.upper(),
                    model,
                    elapsed,
                    retryable,
                    attempt,
                    max_attempts,
                    exc,
                )
                raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"Unknown provider error: provider={provider}, model={model}")

    def _call_openai_compatible(
        self, provider: str, model: str, messages: list[dict], thinking: bool,
        thinking_effort: str, temperature: float, max_tokens: int,
        response_format: Optional[dict], **kwargs: Any,
    ) -> dict[str, Any]:
        """OpenAI 호환 API 호출 (OpenAI, Perplexity)."""
        client = self.providers[provider]

        is_gpt5 = provider == "openai" and "gpt-5" in model

        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        if is_gpt5:
            call_kwargs["max_completion_tokens"] = max_tokens
        else:
            call_kwargs["max_tokens"] = max_tokens
            call_kwargs["temperature"] = temperature

        if thinking and is_gpt5:
            call_kwargs["reasoning_effort"] = thinking_effort

        if response_format:
            call_kwargs["response_format"] = response_format

        call_kwargs.update(kwargs)

        response = client.chat.completions.create(**call_kwargs)

        return {
            "choices": [
                {
                    "message": {
                        "content": response.choices[0].message.content,
                        "role": response.choices[0].message.role,
                    }
                }
            ],
            "model": response.model,
            "usage": {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
            },
        }

    def _call_anthropic(
        self, model: str, messages: list[dict], temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        """Anthropic Claude API 호출."""
        client = self._anthropic_client

        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            else:
                user_messages.append(msg)

        if not user_messages:
            user_messages = [{"role": "user", "content": "위 지시사항을 수행해주세요."}]

        call_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_msg.strip():
            call_kwargs["system"] = system_msg.strip()

        response = client.messages.create(**call_kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return {
            "choices": [
                {
                    "message": {
                        "content": content,
                        "role": "assistant",
                    }
                }
            ],
            "model": response.model,
            "usage": {
                "prompt_tokens": getattr(response.usage, 'input_tokens', 0),
                "completion_tokens": getattr(response.usage, 'output_tokens', 0),
            },
        }


# 싱글톤 인스턴스
_client: Optional[MultiProviderClient] = None


def get_multi_provider_client() -> MultiProviderClient:
    """멀티 프로바이더 클라이언트 싱글톤 반환."""
    global _client
    if _client is None:
        _client = MultiProviderClient()
    return _client
