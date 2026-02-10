"""AI Pipeline Service - 실험용 (OpenAI/Perplexity/Anthropic 직접 호출).

프로덕션 코드(backend_api/app/services/ai_pipeline_service.py)의
경량 독립 버전. DB 의존성 없이 순수 API 호출만 수행한다.
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

from pipeline.config import PipelineConfig
from pipeline.prompt_loader import load_prompt
from pipeline.types import KeywordPlan

LOGGER = logging.getLogger(__name__)

# API 엔드포인트
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# 모델 키 → 프로바이더 매핑
MODEL_PROVIDERS: dict[str, str] = {
    "keyword_model": "openai",
    "research_model": "perplexity",
    "planner_model": "openai",
    "story_model": "anthropic",
    "reviewer_model": "openai",
    "glossary_model": "openai",
    "tone_model": "openai",
}

# 7단계 내러티브 섹션
NARRATIVE_SECTIONS = [
    "background", "mirroring", "difference", "devils_advocate",
    "simulation", "result", "action",
]

# 재시도 가능한 HTTP 상태 코드
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ── JSON / 응답 파싱 유틸리티 ──


def extract_json_fragment(raw: str, start_char: str, end_char: str) -> str:
    """문자열에서 JSON 프래그먼트 추출."""
    start = raw.find(start_char)
    end = raw.rfind(end_char)
    if start != -1 and end != -1 and start <= end:
        return raw[start : end + 1]
    return raw


def safe_load_json(raw: str, default: Any) -> Any:
    """안전한 JSON 파싱."""
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def extract_openai_content(result: dict[str, Any], fallback: str = "") -> str:
    """OpenAI 호환 응답에서 텍스트 추출."""
    try:
        content = result["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content or fallback
        if isinstance(content, list):
            parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            return "\n".join(parts).strip() or fallback
        return fallback
    except (KeyError, IndexError, TypeError):
        return fallback


def extract_anthropic_content(result: dict[str, Any], fallback: str = "") -> str:
    """Anthropic 응답에서 텍스트 추출."""
    try:
        content_blocks = result.get("content", [])
        parts = [
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(parts).strip() or fallback
    except (KeyError, IndexError, TypeError):
        return fallback


def extract_citations(result: dict[str, Any]) -> list[dict[str, str]]:
    """Perplexity 응답에서 인용 URL 추출."""
    citations: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    raw_citations = result.get("citations")
    if isinstance(raw_citations, list):
        for item in raw_citations:
            url = str(item).strip() if item else ""
            if url and url not in seen_urls:
                seen_urls.add(url)
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                citations.append({"name": domain, "url": url})

    return citations[:5]


# ── AI Pipeline Service ──


class AIPipelineService:
    """OpenAI/Perplexity/Anthropic 직접 API 호출 기반 AI 서비스 (실험용)."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        cfg = config or PipelineConfig()
        self.openai_key = cfg.openai_api_key
        self.perplexity_key = cfg.perplexity_api_key
        self.anthropic_key = cfg.anthropic_api_key
        self.model_names = {
            "keyword_model": cfg.keyword_model,
            "research_model": cfg.research_model,
            "planner_model": cfg.keyword_model,  # planner도 같은 경량 모델
            "story_model": cfg.story_model,
            "reviewer_model": cfg.keyword_model,
            "glossary_model": cfg.keyword_model,
            "tone_model": cfg.keyword_model,
        }
        self.timeout = timeout
        self.max_retries = max_retries

    # ── 저수준 API 호출 ──

    async def call_openai(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """OpenAI Chat Completions API 호출."""
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
            url=OPENAI_API_URL, headers=headers,
            payload=payload, provider="OpenAI", model=model,
        )

    async def call_perplexity(
        self,
        messages: list[dict[str, str]],
        model: str = "sonar",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Perplexity API 호출."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }
        return await self._request_with_retry(
            url=PERPLEXITY_API_URL, headers=headers,
            payload=payload, provider="Perplexity", model=model,
        )

    async def call_anthropic(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-5-20250514",
        temperature: float = 0.7,
        system: str = "",
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Anthropic Messages API 호출."""
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
            url=ANTHROPIC_API_URL, headers=headers,
            payload=payload, provider="Anthropic", model=model,
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
                        "[%s] request model=%s attempt=%d/%d",
                        provider, model, attempt + 1, self.max_retries,
                    )
                    response = await client.post(url, headers=headers, json=payload)
                    elapsed = time.perf_counter() - started

                if response.status_code >= 400:
                    LOGGER.warning(
                        "[%s] error status=%d elapsed=%.2fs",
                        provider, response.status_code, elapsed,
                    )
                    if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries - 1:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(wait)
                        continue
                    raise httpx.HTTPStatusError(
                        f"{provider} API error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                LOGGER.info("[%s] done model=%s elapsed=%.2fs", provider, model, elapsed)
                return response.json()

            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue
                raise

            except httpx.HTTPStatusError:
                raise

            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue
                raise

        raise last_error or RuntimeError(f"{provider} failed after {self.max_retries} retries")

    # ── 프롬프트 기반 호출 ──

    async def _call_prompt(self, name: str, **kwargs: str) -> tuple[dict[str, Any], str]:
        """프롬프트 로드 -> model_key로 프로바이더 결정 -> API 호출."""
        spec = load_prompt(name, **kwargs)
        model_key = spec.model_key or "keyword_model"
        provider = MODEL_PROVIDERS.get(model_key, "openai")
        model_name = self.model_names.get(model_key, "gpt-4o-mini")

        messages: list[dict[str, str]] = []
        if spec.system_message:
            messages.append({"role": "system", "content": spec.system_message})
        messages.append({"role": "user", "content": spec.body})

        if provider == "anthropic":
            result = await self.call_anthropic(
                messages=messages, model=model_name,
                temperature=spec.temperature, system=spec.system_message,
            )
            return result, extract_anthropic_content(result, "")

        elif provider == "perplexity":
            result = await self.call_perplexity(
                messages=messages, model=model_name, temperature=spec.temperature,
            )
            return result, extract_openai_content(result, "")

        else:
            response_format = {"type": spec.response_format} if spec.response_format else None
            result = await self.call_openai(
                messages=messages, model=model_name,
                temperature=spec.temperature, response_format=response_format,
            )
            return result, extract_openai_content(result, "")

    # ── 키워드 추출 ──

    async def extract_top_keywords(
        self,
        rss_text: str,
        candidate_count: int = 8,
        avoid_keywords: list[str] | None = None,
    ) -> list[KeywordPlan]:
        """RSS 뉴스에서 투자 키워드 후보 추출."""
        avoid_section = ""
        if avoid_keywords:
            avoid_section = "[금지 키워드]\n- " + "\n- ".join(avoid_keywords)

        _, content = await self._call_prompt(
            "keyword_extraction",
            count=str(max(6, min(12, candidate_count))),
            avoid_section=avoid_section,
            rss_text=rss_text[:8000],
        )

        json_text = extract_json_fragment(content, "[", "]")
        parsed = safe_load_json(json_text, [])
        if not isinstance(parsed, list):
            parsed = [parsed]

        output: list[KeywordPlan] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            keyword = str(item.get("keyword", "")).strip()
            context = str(item.get("context", "")).strip()
            if not keyword or not context:
                continue

            title = str(item.get("title", "")).strip()
            if not title or len(title) < 8:
                title = f"[{keyword}] 시장이 주목하는 핵심 포인트"

            output.append(KeywordPlan(
                category=str(item.get("category", "Market trend")).strip(),
                domain=str(item.get("domain", "macro")).strip().lower().replace(" ", "_"),
                keyword=keyword,
                title=re.sub(r"^\[.*?\]\s*", "", title).strip(),
                context=context,
                mirroring_hint=str(item.get("mirroringHint", "")).strip(),
            ))

        LOGGER.info("[KEYWORDS] Extracted %d keyword plans", len(output))
        return output

    # ── 리서치 ──

    async def research_context(
        self, keyword: str, mirroring_hint: str = "",
    ) -> tuple[str, list[dict[str, str]]]:
        """맥락 리서치 (Perplexity sonar)."""
        result, text = await self._call_prompt(
            "research_context",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        return text, extract_citations(result)

    async def research_simulation(
        self, keyword: str, mirroring_hint: str = "",
    ) -> tuple[str, list[dict[str, str]]]:
        """시뮬레이션 리서치 (Perplexity sonar)."""
        result, text = await self._call_prompt(
            "research_simulation",
            keyword=keyword,
            mirroring_hint=mirroring_hint or "과거 금융 사례",
        )
        return text, extract_citations(result)

    # ── 스토리 생성 파이프라인 ──

    async def generate_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        mirroring_hint: str = "",
    ) -> dict[str, Any]:
        """전체 스토리 생성: plan -> write -> review."""
        LOGGER.info("[STORY] Starting for theme=%s", theme)
        started = time.perf_counter()

        # 플래닝
        _, plan_content = await self._call_prompt(
            "planner",
            theme=theme, mirroring_hint=mirroring_hint,
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        plan = safe_load_json(extract_json_fragment(plan_content, "{", "}"), {})

        # 스토리 작성
        _, draft_content = await self._call_prompt(
            "writer",
            theme=theme, mirroring_hint=mirroring_hint,
            plan=str(plan),
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        draft = safe_load_json(extract_json_fragment(draft_content, "{", "}"), {})

        # 리뷰
        _, review_content = await self._call_prompt("reviewer", draft=str(draft))
        reviewed = safe_load_json(extract_json_fragment(review_content, "{", "}"), draft)

        elapsed = time.perf_counter() - started
        LOGGER.info("[STORY] Complete for theme=%s elapsed=%.2fs", theme, elapsed)
        return reviewed if isinstance(reviewed, dict) else draft

    # ── 용어집 생성 ──

    async def generate_glossary(self, terms: list[str]) -> dict[str, str]:
        """용어 일괄 정의 생성."""
        if not terms:
            return {}
        try:
            _, content = await self._call_prompt("glossary", terms=", ".join(terms))
            parsed = safe_load_json(extract_json_fragment(content, "{", "}"), {})
            if isinstance(parsed, dict) and parsed:
                return {str(k): str(v) for k, v in parsed.items()}
        except Exception as exc:
            LOGGER.warning("[GLOSSARY] Failed: %s", exc)

        return {term: f"{term}은(는) 투자할 때 꼭 알아야 할 핵심 개념이에요." for term in terms[:5]}
