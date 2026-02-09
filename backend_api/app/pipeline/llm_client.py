"""LLM Client - Direct API calls to OpenAI, Perplexity, and Claude."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx


LOGGER = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client for OpenAI, Perplexity, and Claude APIs."""
    
    def __init__(
        self,
        openai_api_key: str,
        perplexity_api_key: str,
        anthropic_api_key: str = "",
        timeout_seconds: int = 120,
    ) -> None:
        self.openai_api_key = openai_api_key
        self.perplexity_api_key = perplexity_api_key
        self.anthropic_api_key = anthropic_api_key
        self.timeout_seconds = timeout_seconds
    
    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------
    
    def call_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Synchronous OpenAI API call."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=self.timeout_seconds) as client:
            started = time.perf_counter()
            LOGGER.info("[OPENAI] start model=%s messages=%d", model, len(messages))
            
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            elapsed = time.perf_counter() - started
        
        if response.status_code >= 400:
            LOGGER.error("OpenAI error (%s): %s", response.status_code, response.text)
            raise RuntimeError(f"OpenAI API error: {response.status_code}")
        
        LOGGER.info("[OPENAI] done model=%s elapsed=%.2fs", model, elapsed)
        return response.json()
    
    async def async_call_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Async OpenAI API call."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            started = time.perf_counter()
            LOGGER.info("[OPENAI-ASYNC] start model=%s messages=%d", model, len(messages))
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            elapsed = time.perf_counter() - started
        
        if response.status_code >= 400:
            LOGGER.error("OpenAI async error (%s): %s", response.status_code, response.text)
            raise RuntimeError(f"OpenAI API error: {response.status_code}")
        
        LOGGER.info("[OPENAI-ASYNC] done model=%s elapsed=%.2fs", model, elapsed)
        return response.json()
    
    # ------------------------------------------------------------------
    # Perplexity (Sonar)
    # ------------------------------------------------------------------
    
    def call_perplexity(
        self,
        messages: list[dict[str, str]],
        model: str = "sonar",
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Synchronous Perplexity API call."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=self.timeout_seconds) as client:
            started = time.perf_counter()
            LOGGER.info("[PERPLEXITY] start model=%s messages=%d", model, len(messages))
            
            response = client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
            )
            elapsed = time.perf_counter() - started
        
        if response.status_code >= 400:
            LOGGER.error("Perplexity error (%s): %s", response.status_code, response.text)
            raise RuntimeError(f"Perplexity API error: {response.status_code}")
        
        LOGGER.info("[PERPLEXITY] done model=%s elapsed=%.2fs", model, elapsed)
        return response.json()
    
    async def async_call_perplexity(
        self,
        messages: list[dict[str, str]],
        model: str = "sonar",
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Async Perplexity API call."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            started = time.perf_counter()
            LOGGER.info("[PERPLEXITY-ASYNC] start model=%s messages=%d", model, len(messages))
            
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
            )
            elapsed = time.perf_counter() - started
        
        if response.status_code >= 400:
            LOGGER.error("Perplexity async error (%s): %s", response.status_code, response.text)
            raise RuntimeError(f"Perplexity API error: {response.status_code}")
        
        LOGGER.info("[PERPLEXITY-ASYNC] done model=%s elapsed=%.2fs", model, elapsed)
        return response.json()
    
    # ------------------------------------------------------------------
    # Claude (Anthropic)
    # ------------------------------------------------------------------
    
    def call_claude(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Synchronous Claude API call."""
        # Convert OpenAI-style messages to Anthropic format
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_message:
            payload["system"] = system_message
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        with httpx.Client(timeout=self.timeout_seconds) as client:
            started = time.perf_counter()
            LOGGER.info("[CLAUDE] start model=%s messages=%d", model, len(anthropic_messages))
            
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            elapsed = time.perf_counter() - started
        
        if response.status_code >= 400:
            LOGGER.error("Claude error (%s): %s", response.status_code, response.text)
            raise RuntimeError(f"Claude API error: {response.status_code}")
        
        LOGGER.info("[CLAUDE] done model=%s elapsed=%.2fs", model, elapsed)
        
        # Convert Anthropic response to OpenAI-like format
        result = response.json()
        return self._convert_claude_response(result)
    
    async def async_call_claude(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Async Claude API call."""
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_message:
            payload["system"] = system_message
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            started = time.perf_counter()
            LOGGER.info("[CLAUDE-ASYNC] start model=%s messages=%d", model, len(anthropic_messages))
            
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            elapsed = time.perf_counter() - started
        
        if response.status_code >= 400:
            LOGGER.error("Claude async error (%s): %s", response.status_code, response.text)
            raise RuntimeError(f"Claude API error: {response.status_code}")
        
        LOGGER.info("[CLAUDE-ASYNC] done model=%s elapsed=%.2fs", model, elapsed)
        
        result = response.json()
        return self._convert_claude_response(result)
    
    @staticmethod
    def _convert_claude_response(result: dict[str, Any]) -> dict[str, Any]:
        """Convert Anthropic response to OpenAI-like format."""
        content = ""
        if "content" in result and isinstance(result["content"], list):
            for block in result["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    content += block.get("text", "")
        
        return {
            "choices": [
                {
                    "message": {
                        "content": content,
                        "role": "assistant",
                    }
                }
            ]
        }


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def extract_message_content(result: dict[str, Any], fallback: str = "") -> str:
    """Extract message content from API response."""
    try:
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content or fallback
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            joined = "\n".join(parts).strip()
            return joined or fallback
        return fallback
    except (KeyError, IndexError, TypeError):
        return fallback


def extract_citations(result: dict[str, Any]) -> list[dict[str, str]]:
    """Extract citation URLs from Perplexity Sonar responses."""
    citations: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    
    # Strategy 1: Perplexity structured citations field
    raw_citations = result.get("citations")
    if isinstance(raw_citations, list):
        for item in raw_citations:
            url = str(item).strip() if item else ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                citations.append({"name": domain, "url": url})
    
    # Strategy 2: Parse inline markdown links from content
    content = extract_message_content(result, "")
    if content:
        link_pattern = re.compile(r'\[(\d+)\]\((https?://[^\s)]+)\)')
        for match in link_pattern.finditer(content):
            url = match.group(2).strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                citations.append({"name": domain, "url": url})
    
    return citations[:5]


def extract_json_fragment(raw: str, start_char: str, end_char: str) -> str:
    """Extract JSON fragment from text."""
    start = raw.find(start_char)
    end = raw.rfind(end_char)
    if start != -1 and end != -1 and start <= end:
        return raw[start : end + 1]
    return raw


def safe_load_json(raw: str, default: Any) -> Any:
    """Safely load JSON with fallback."""
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default
