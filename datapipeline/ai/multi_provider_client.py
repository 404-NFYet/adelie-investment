"""멀티 프로바이더 AI 클라이언트.

OpenRouter를 대체하여 OpenAI, Perplexity, Anthropic을 직접 호출한다.
GPT-5 thinking 모드를 지원한다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from openai import OpenAI

from ..core.config import get_settings

LOGGER = logging.getLogger(__name__)


class MultiProviderClient:
    """OpenAI, Perplexity, Anthropic을 통합 관리하는 AI 클라이언트."""

    def __init__(
        self,
        openai_key: str = "",
        perplexity_key: str = "",
        anthropic_key: str = "",
    ) -> None:
        settings = get_settings()
        openai_key = openai_key or settings.openai.api_key
        perplexity_key = perplexity_key or settings.perplexity.api_key

        self.providers: dict[str, Any] = {}

        # OpenAI
        if openai_key:
            self.providers["openai"] = OpenAI(api_key=openai_key)
            LOGGER.info("OpenAI provider initialized")

        # Perplexity (OpenAI 호환 API)
        if perplexity_key:
            self.providers["perplexity"] = OpenAI(
                api_key=perplexity_key,
                base_url="https://api.perplexity.ai",
            )
            LOGGER.info("Perplexity provider initialized")

        # Anthropic (선택적)
        anthropic_key = anthropic_key or getattr(settings, 'claude_api_key', '') or ''
        if not anthropic_key:
            import os
            anthropic_key = os.getenv("CLAUDE_API_KEY", "")
        if anthropic_key:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic(api_key=anthropic_key)
                self.providers["anthropic"] = self._anthropic_client
                LOGGER.info("Anthropic provider initialized")
            except ImportError:
                LOGGER.warning("anthropic 패키지 미설치 - pip install anthropic")

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
        """프로바이더별 chat completion 호출.

        Args:
            provider: "openai", "perplexity", "anthropic"
            model: 실제 모델명
            messages: 대화 메시지 목록
            thinking: GPT-5 thinking 모드 활성화
            thinking_effort: thinking 강도 (low/medium/high)
            temperature: 온도 파라미터
            max_tokens: 최대 토큰 수
            response_format: JSON 응답 형식 강제
            **kwargs: 추가 파라미터

        Returns:
            응답 딕셔너리 (OpenAI 호환 형식)
        """
        if provider not in self.providers:
            raise ValueError(f"프로바이더 '{provider}'가 초기화되지 않았습니다. 사용 가능: {list(self.providers.keys())}")

        started = time.perf_counter()
        LOGGER.info(
            "[%s] start model=%s messages=%d thinking=%s",
            provider.upper(), model, len(messages), thinking,
        )

        try:
            if provider == "anthropic":
                result = self._call_anthropic(model, messages, temperature, max_tokens)
            else:
                result = self._call_openai_compatible(
                    provider, model, messages, thinking, thinking_effort,
                    temperature, max_tokens, response_format, **kwargs,
                )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            LOGGER.error("[%s] error model=%s elapsed=%.2fs: %s", provider.upper(), model, elapsed, exc)
            raise

        elapsed = time.perf_counter() - started
        LOGGER.info("[%s] done model=%s elapsed=%.2fs", provider.upper(), model, elapsed)
        return result

    def _call_openai_compatible(
        self, provider: str, model: str, messages: list[dict], thinking: bool,
        thinking_effort: str, temperature: float, max_tokens: int,
        response_format: Optional[dict], **kwargs: Any,
    ) -> dict[str, Any]:
        """OpenAI 호환 API 호출 (OpenAI, Perplexity)."""
        client = self.providers[provider]

        # gpt-5 계열: max_completion_tokens만 지원, temperature는 기본값(1)만 허용
        is_gpt5 = provider == "openai" and "gpt-5" in model

        call_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        if is_gpt5:
            call_kwargs["max_completion_tokens"] = max_tokens
            # gpt-5는 temperature 커스텀 불가 → 파라미터 생략 (기본값 1 적용)
        else:
            call_kwargs["max_tokens"] = max_tokens
            call_kwargs["temperature"] = temperature

        # GPT-5 thinking 모드
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

        # system 메시지 분리 (Anthropic API 형식)
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            else:
                user_messages.append(msg)

        # 최소 1개의 user 메시지 필요
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
