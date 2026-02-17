"""멀티 프로바이더 AI 클라이언트.

datapipeline/ai/multi_provider_client.py에서 복제.
config 의존을 제거하고 환경변수를 직접 참조한다.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from openai import OpenAI

from ..config import OPENAI_API_KEY, PERPLEXITY_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY

LOGGER = logging.getLogger(__name__)
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180"))
PERPLEXITY_TIMEOUT_SECONDS = float(os.getenv("PERPLEXITY_TIMEOUT_SECONDS", "60"))


class MultiProviderClient:
    """OpenAI, Perplexity, Anthropic, Google을 통합 관리하는 AI 클라이언트."""

    def __init__(
        self,
        openai_key: str = "",
        perplexity_key: str = "",
        anthropic_key: str = "",
        google_key: str = "",
    ) -> None:
        openai_key = openai_key or OPENAI_API_KEY
        perplexity_key = perplexity_key or PERPLEXITY_API_KEY
        anthropic_key = anthropic_key or ANTHROPIC_API_KEY
        google_key = google_key or GOOGLE_API_KEY

        self.providers: dict[str, Any] = {}

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

        # Google Gemini (선택적)
        if google_key:
            try:
                from google import genai
                self._google_client = genai.Client(api_key=google_key)
                self.providers["google"] = self._google_client
                LOGGER.info("Google Gemini provider initialized")
            except ImportError:
                LOGGER.warning("google-genai 패키지 미설치 - pip install google-genai")

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
        """프로바이더별 chat completion 호출 (최대 3회 재시도)."""
        # "gemini"는 "google"의 별칭
        if provider == "gemini":
            provider = "google"

        if provider not in self.providers:
            raise ValueError(
                f"프로바이더 '{provider}'가 초기화되지 않았습니다. "
                f"사용 가능: {list(self.providers.keys())}"
            )

        max_retries = 3
        last_exc = None

        for attempt in range(max_retries):
            started = time.perf_counter()
            LOGGER.info(
                "[%s] start model=%s messages=%d thinking=%s (attempt %d/%d)",
                provider.upper(), model, len(messages), thinking, attempt + 1, max_retries,
            )

            try:
                if provider == "anthropic":
                    result = self._call_anthropic(model, messages, temperature, max_tokens)
                elif provider == "google":
                    result = self._call_google(model, messages, temperature, max_tokens)
                else:
                    result = self._call_openai_compatible(
                        provider, model, messages, thinking, thinking_effort,
                        temperature, max_tokens, response_format, **kwargs,
                    )
                elapsed = time.perf_counter() - started
                LOGGER.info("[%s] done model=%s elapsed=%.2fs", provider.upper(), model, elapsed)
                return result
            except (TimeoutError, ConnectionError) as exc:
                elapsed = time.perf_counter() - started
                last_exc = exc
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    LOGGER.warning(
                        "[%s] 재시도 가능 에러 (attempt %d/%d, %.1fs 후 재시도): %s",
                        provider.upper(), attempt + 1, max_retries, wait, exc,
                    )
                    time.sleep(wait)
                else:
                    LOGGER.error(
                        "[%s] 최대 재시도 초과 model=%s elapsed=%.2fs: %s",
                        provider.upper(), model, elapsed, exc,
                    )
            except Exception as exc:
                elapsed = time.perf_counter() - started
                LOGGER.error(
                    "[%s] error model=%s elapsed=%.2fs: %s",
                    provider.upper(), model, elapsed, exc,
                )
                raise

        raise last_exc

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
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        response_format: Optional[dict[str, Any]] = None,
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

        # Anthropic SDK의 strict JSON mode 지원 여부가 모델/버전별로 달라
        # 현재는 프롬프트 강제와 상위 파서 재시도 로직에 의존한다.
        _ = response_format

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

    def _call_google(
        self, model: str, messages: list[dict], temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        """Google Gemini API 호출.

        OpenAI 메시지 형식을 Gemini 형식으로 변환한다:
        - system → system_instruction 파라미터
        - user → role: "user"
        - assistant → role: "model"
        """
        from google.genai import types

        client = self._google_client

        # system 메시지 분리 + 나머지 메시지 role 변환
        system_parts: list[str] = []
        contents: list[types.Content] = []

        for msg in messages:
            role = msg["role"]
            text = msg["content"]

            if role == "system":
                system_parts.append(text)
            elif role == "assistant":
                # Gemini는 assistant 대신 "model" role 사용
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)],
                ))
            else:
                # user (및 기타)
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=text)],
                ))

        # 메시지가 비어 있으면 기본 user 메시지 추가
        if not contents:
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text="위 지시사항을 수행해주세요.")],
            ))

        # GenerateContentConfig 구성
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # system instruction 설정
        if system_parts:
            config.system_instruction = "\n".join(system_parts)

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        # 응답 텍스트 추출
        content_text = response.text or ""

        # 사용량 정보 추출
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

        return {
            "choices": [
                {
                    "message": {
                        "content": content_text,
                        "role": "assistant",
                    }
                }
            ],
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
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
