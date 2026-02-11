"""LLM API 호출 유틸리티.

OpenAI / Perplexity / Anthropic API를 httpx로 직접 호출하는 경량 클라이언트.
ai_pipeline_service.py에서 LLM 호출 로직만 추출.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from typing import Any

import httpx

from app.core.config import settings

LOGGER = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ──────────────────────────────────────────────
# JSON / 응답 파싱 유틸리티
# ──────────────────────────────────────────────


def extract_json_fragment(raw: str, start_char: str, end_char: str) -> str:
    """문자열에서 JSON 프래그먼트(시작~끝 문자) 추출."""
    start = raw.find(start_char)
    end = raw.rfind(end_char)
    if start != -1 and end != -1 and start <= end:
        return raw[start : end + 1]
    return raw


def safe_load_json(raw: str, default: Any) -> Any:
    """안전한 JSON 파싱 (실패 시 기본값 반환)."""
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def extract_openai_content(result: dict[str, Any], fallback: str = "") -> str:
    """OpenAI 호환 응답(Perplexity 포함)에서 메시지 텍스트 추출."""
    try:
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content or fallback
        if isinstance(content, list):
            parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            joined = "\n".join(parts).strip()
            return joined or fallback
        return fallback
    except (KeyError, IndexError, TypeError):
        return fallback


def extract_anthropic_content(result: dict[str, Any], fallback: str = "") -> str:
    """Anthropic 응답에서 텍스트 추출."""
    try:
        content_blocks = result.get("content", [])
        parts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        joined = "\n".join(parts).strip()
        return joined or fallback
    except (KeyError, IndexError, TypeError):
        return fallback


def extract_citations(result: dict[str, Any]) -> list[dict[str, str]]:
    """Perplexity 응답에서 인용 URL 추출.

    Perplexity는 두 가지 방식으로 인용을 제공:
    1) result["citations"] - URL 문자열 리스트
    2) 본문 내 마크다운 링크 [n](url)
    """
    citations: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    # 1) 구조화된 citations 필드
    raw_citations = result.get("citations")
    if isinstance(raw_citations, list):
        for item in raw_citations:
            url = str(item).strip() if item else ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                citations.append({"name": domain, "url": url})

    # 2) 본문 내 마크다운 링크 파싱
    content = extract_openai_content(result, "")
    if content:
        link_pattern = re.compile(r"\[(\d+)\]\((https?://[^\s)]+)\)")
        for match in link_pattern.finditer(content):
            url = match.group(2).strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                citations.append({"name": domain, "url": url})

    return citations[:5]


# ──────────────────────────────────────────────
# LLM Client
# ──────────────────────────────────────────────


class LLMClient:
    """OpenAI/Perplexity/Anthropic 직접 API 호출 클라이언트.

    모든 API 호출은 httpx.AsyncClient를 사용하며,
    지수 백오프 재시도 로직을 포함한다.
    """

    def __init__(
        self,
        openai_key: str = "",
        perplexity_key: str = "",
        anthropic_key: str = "",
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.openai_key = openai_key or settings.OPENAI_API_KEY
        self.perplexity_key = perplexity_key or settings.PERPLEXITY_API_KEY
        self.anthropic_key = anthropic_key or settings.ANTHROPIC_API_KEY
        self.timeout = timeout
        self.max_retries = max_retries

    async def call_openai(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-5-mini",
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """OpenAI Chat Completions API 직접 호출 (재시도 포함)."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        return await self._request_with_retry(
            url=OPENAI_API_URL,
            headers=headers,
            payload=payload,
            provider="OpenAI",
            model=model,
        )

    async def call_perplexity(
        self,
        messages: list[dict[str, str]],
        model: str = "sonar",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        search_domain_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perplexity Chat Completions API 직접 호출 (재시도 포함)."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if search_domain_filter:
            payload["web_search_options"] = {"search_domain_filter": search_domain_filter}
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }
        return await self._request_with_retry(
            url=PERPLEXITY_API_URL,
            headers=headers,
            payload=payload,
            provider="Perplexity",
            model=model,
        )

    async def call_anthropic(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-5-20250514",
        temperature: float = 0.7,
        system: str = "",
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Anthropic Messages API 직접 호출 (재시도 포함)."""
        filtered_messages = [m for m in messages if m.get("role") != "system"]
        if not system:
            for m in messages:
                if m.get("role") == "system":
                    system = m.get("content", "")
                    break

        payload: dict[str, Any] = {
            "model": model,
            "messages": filtered_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        return await self._request_with_retry(
            url=ANTHROPIC_API_URL,
            headers=headers,
            payload=payload,
            provider="Anthropic",
            model=model,
        )

    async def _request_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        provider: str,
        model: str,
    ) -> dict[str, Any]:
        """HTTP POST + 지수 백오프 재시도."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    started = time.perf_counter()
                    LOGGER.info(
                        "[%s] request start model=%s msgs=%d attempt=%d/%d",
                        provider,
                        model,
                        len(payload.get("messages", [])),
                        attempt + 1,
                        self.max_retries,
                    )
                    response = await client.post(url, headers=headers, json=payload)
                    elapsed = time.perf_counter() - started

                if response.status_code >= 400:
                    body_preview = response.text[:500]
                    LOGGER.warning(
                        "[%s] error status=%d model=%s elapsed=%.2fs body=%s",
                        provider,
                        response.status_code,
                        model,
                        elapsed,
                        body_preview,
                    )
                    if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries - 1:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                        LOGGER.info("[%s] retrying in %.1fs...", provider, wait)
                        await asyncio.sleep(wait)
                        continue
                    raise httpx.HTTPStatusError(
                        f"{provider} API error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                LOGGER.info(
                    "[%s] done model=%s status=%s elapsed=%.2fs",
                    provider,
                    model,
                    response.status_code,
                    elapsed,
                )
                return response.json()

            except httpx.TimeoutException as exc:
                last_error = exc
                LOGGER.warning(
                    "[%s] timeout model=%s attempt=%d/%d",
                    provider, model, attempt + 1, self.max_retries,
                )
                if attempt < self.max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    LOGGER.info("[%s] retrying in %.1fs...", provider, wait)
                    await asyncio.sleep(wait)
                    continue
                raise

            except httpx.HTTPStatusError:
                raise

            except Exception as exc:
                last_error = exc
                LOGGER.error("[%s] unexpected error: %s", provider, exc, exc_info=True)
                if attempt < self.max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait)
                    continue
                raise

        raise last_error or RuntimeError(
            f"{provider} API call failed after {self.max_retries} retries"
        )


# ──────────────────────────────────────────────
# 싱글톤 인스턴스
# ──────────────────────────────────────────────

_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """싱글톤 LLM 클라이언트 인스턴스 반환."""
    global _instance
    if _instance is None:
        _instance = LLMClient()
    return _instance
