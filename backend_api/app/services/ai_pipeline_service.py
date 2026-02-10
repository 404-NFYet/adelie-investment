"""AI Pipeline Service - OpenAI/Perplexity/Anthropic 직접 API 호출.

각 LLM 프로바이더를 httpx로 직접 호출하여 내러티브 파이프라인을 실행한다.
- OpenAI (gpt-5-mini): 키워드 추출, 플래너, 리뷰어, 용어집, 톤 교정, 마커
- Perplexity (sonar): 맥락 리서치, 시뮬레이션 리서치
- Anthropic (claude-sonnet-4.5): 스토리 생성
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

LOGGER = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

# 프롬프트 디렉토리 (backend_api/app/pipeline/prompts/)
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "pipeline" / "prompts"

# 7단계 내러티브 섹션
NARRATIVE_SECTIONS = [
    "background",
    "mirroring",
    "simulation",
    "result",
    "difference",
    "devils_advocate",
    "action",
]

# <mark class='term'> 태그 패턴
MARK_PATTERN = re.compile(r"<mark class=['\"]term['\"]>(.*?)</mark>")

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

# 모델 키 → 실제 모델명 매핑
MODEL_NAMES: dict[str, str] = {
    "keyword_model": "gpt-5-mini",
    "research_model": "sonar",
    "planner_model": "gpt-5-mini",
    "story_model": "claude-sonnet-4-5-20250514",
    "reviewer_model": "gpt-5-mini",
    "glossary_model": "gpt-5-mini",
    "tone_model": "gpt-5-mini",
}

# 재시도 가능한 HTTP 상태 코드
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# API 엔드포인트
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


# ──────────────────────────────────────────────
# 데이터 타입
# ──────────────────────────────────────────────


@dataclass
class KeywordPlan:
    """키워드 추출 결과."""

    category: str
    keyword: str
    title: str
    context: str
    domain: str = "macro"
    mirroring_hint: str = ""


@dataclass
class PromptSpec:
    """프롬프트 템플릿 파싱 결과."""

    body: str
    model_key: str = ""
    temperature: float = 0.7
    response_format: str | None = None
    role: str = ""
    system_message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
# 프롬프트 로더
# ──────────────────────────────────────────────

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")
_INCLUDE_PATTERN = re.compile(r"\{\{include:(\w+)\}\}")
_FM_DELIM = "---"


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """프론트매터(YAML-like key: value) 파싱."""
    lines = raw.split("\n")
    if not lines or lines[0].strip() != _FM_DELIM:
        return {}, raw

    meta_lines: list[str] = []
    body_start = 1
    found_end = False
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == _FM_DELIM:
            body_start = idx + 1
            found_end = True
            break
        meta_lines.append(line)

    if not found_end:
        return {}, raw

    meta: dict[str, str] = {}
    current_key = ""
    current_value = ""
    for mline in meta_lines:
        stripped = mline.strip()
        if not stripped:
            continue
        if ":" in stripped and not stripped.startswith(" "):
            if current_key:
                meta[current_key] = current_value.strip()
            key, _, value = stripped.partition(":")
            current_key = key.strip()
            current_value = value.strip()
            if current_value == ">":
                current_value = ""
        elif current_key:
            current_value += " " + stripped
    if current_key:
        meta[current_key] = current_value.strip()

    body = "\n".join(lines[body_start:])
    return meta, body


def _resolve_includes(body: str, prompts_dir: Path) -> str:
    """{{include:filename}} 디렉티브를 실제 파일 내용으로 치환."""

    def _replacer(match: re.Match[str]) -> str:
        name = match.group(1)
        include_path = prompts_dir / f"{name}.md"
        if not include_path.exists():
            LOGGER.warning("Include file not found: %s", include_path)
            return ""
        return include_path.read_text(encoding="utf-8").strip()

    return _INCLUDE_PATTERN.sub(_replacer, body)


def _substitute_vars(body: str, variables: dict[str, str]) -> str:
    """{{variable}} 플레이스홀더를 제공된 값으로 치환."""

    def _replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return variables[key]
        LOGGER.debug("Unresolved variable: {{%s}}", key)
        return ""

    return _VAR_PATTERN.sub(_replacer, body)


def load_prompt(
    name: str,
    prompts_dir: Path | None = None,
    **kwargs: str,
) -> PromptSpec:
    """프롬프트 템플릿 로드, include 해석, 변수 치환.

    Args:
        name: 프롬프트 파일명 (확장자 제외, 예: "planner")
        prompts_dir: 프롬프트 디렉토리 (기본: pipeline/prompts/)
        **kwargs: 템플릿 내 {{변수}} 치환용 값

    Returns:
        렌더링된 PromptSpec
    """
    directory = prompts_dir or _PROMPTS_DIR
    filepath = directory / f"{name}.md"

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt template not found: {filepath}")

    raw = filepath.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    body = _resolve_includes(body, directory)
    str_kwargs = {k: str(v) for k, v in kwargs.items()}
    body = _substitute_vars(body, str_kwargs)

    response_format = meta.get("response_format")
    try:
        temperature = float(meta.get("temperature", "0.7"))
    except (TypeError, ValueError):
        temperature = 0.7

    return PromptSpec(
        body=body.strip(),
        model_key=meta.get("model_key", ""),
        temperature=temperature,
        response_format=response_format if response_format else None,
        role=meta.get("role", ""),
        system_message=meta.get("system_message", ""),
        extra={
            k: v
            for k, v in meta.items()
            if k not in ("model_key", "temperature", "response_format", "role", "system_message")
        },
    )


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
# AI Pipeline Service
# ──────────────────────────────────────────────


# 섹터별 구체적 mirroring 힌트 매핑
_SECTOR_MIRRORING_HINTS: dict[str, str] = {
    "반도체": "2018년 메모리 다운사이클: 삼성전자·SK하이닉스 주가 40%+ 하락 후 2019년 반등",
    "2차전지": "2021년 배터리주 급등락: LG에너지솔루션 IPO 전후 에코프로·엘앤에프 300%+ 상승 후 2022년 50% 조정",
    "자동차": "2020년 현대차 전기차 전략 발표: 주가 2배 상승 후 2021년 조정, 아이오닉5 출시 효과",
    "바이오": "2020년 셀트리온·삼성바이오로직스 코로나 수혜 급등, 2021년 임상 실패 리스크로 30% 조정",
    "건설": "2015년 해외건설 수주 급감: 대우건설·현대건설 주가 30% 하락, 부동산 PF 리스크 부각",
    "금융": "2008년 글로벌 금융위기: KB금융·신한지주 50% 급락 후 2009년 정부 지원으로 80% 반등",
    "엔터": "2023년 하이브·SM·JYP K-pop 글로벌 확장: 위버스 구독자 급증, 주가 2배 후 조정",
    "조선": "2021년 친환경 선박 수주 사이클: HD한국조선해양·삼성중공업 수주 잔고 3년치 확보, 주가 100%+",
    "에너지": "2022년 러시아-우크라이나 전쟁: 유가 배럴당 $130 돌파, S-Oil·SK이노베이션 60% 급등",
    "통신": "2019년 5G 상용화: SKT·KT·LGU+ 5G 투자 확대, 에릭슨·삼성전자 네트워크 수혜",
    "유통": "2020년 코로나 언택트 소비: 쿠팡·네이버쇼핑 거래액 100% 증가, 오프라인 유통 30% 하락",
    "게임": "2021년 메타버스 테마: 위메이드·컴투스 300% 급등, 2022년 P2E 규제로 80% 급락",
    "AI": "2023년 ChatGPT 등장: 네이버·카카오 AI 투자 확대, 솔트룩스·코난테크놀로지 300%+ 급등 후 조정",
    "철강": "2021년 포스코·현대제철 철강 슈퍼사이클: 열연코일 톤당 150만원 돌파, 주가 80% 상승",
    "화학": "2021년 LG화학·SKC 배터리 소재 호황: 양극재·음극재 가격 2배, 에코프로비엠 급등",
}


def _get_sector_mirroring_hint(keyword: str) -> str:
    """키워드에서 섹터를 추론하여 구체적 mirroring 힌트 반환."""
    keyword_lower = keyword.lower()
    for sector, hint in _SECTOR_MIRRORING_HINTS.items():
        if sector.lower() in keyword_lower:
            return hint
    # 매칭 안 되면 구체적 기본값
    return "과거 한국 주식시장의 구체적 사례 (종목명, 연도, 주가 변동폭 포함)"


class AIPipelineService:
    """OpenAI/Perplexity/Anthropic 직접 API 호출 기반 AI 파이프라인 서비스.

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

    # ──────────────────────────────────────────
    # 저수준 API 호출 메서드
    # ──────────────────────────────────────────

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
            payload["search_domain_filter"] = search_domain_filter
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
        """Anthropic Messages API 직접 호출 (재시도 포함).

        system 메시지는 messages에서 자동 분리하여 별도 필드로 전달한다.
        """
        # Anthropic은 system 메시지를 messages 밖에서 전달
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
        """HTTP POST + 지수 백오프 재시도.

        - 429/5xx 에러 시 자동 재시도
        - 400/401/403 등 클라이언트 에러는 즉시 실패
        """
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

    # ──────────────────────────────────────────
    # 프롬프트 기반 호출 (프로바이더 자동 라우팅)
    # ──────────────────────────────────────────

    async def _call_prompt(self, name: str, **kwargs: str) -> tuple[dict[str, Any], str]:
        """프롬프트 로드 -> model_key로 프로바이더 결정 -> API 호출.

        Returns:
            (raw_response_dict, extracted_text_content)
        """
        spec = load_prompt(name, **kwargs)
        model_key = spec.model_key or "keyword_model"
        provider = MODEL_PROVIDERS.get(model_key, "openai")
        model_name = MODEL_NAMES.get(model_key, "gpt-5-mini")

        messages: list[dict[str, str]] = []
        if spec.system_message:
            messages.append({"role": "system", "content": spec.system_message})
        messages.append({"role": "user", "content": spec.body})

        if provider == "anthropic":
            result = await self.call_anthropic(
                messages=messages,
                model=model_name,
                temperature=spec.temperature,
                system=spec.system_message,
            )
            text = extract_anthropic_content(result, "")
            return result, text

        elif provider == "perplexity":
            result = await self.call_perplexity(
                messages=messages,
                model=model_name,
                temperature=spec.temperature,
            )
            text = extract_openai_content(result, "")
            return result, text

        else:  # openai
            response_format = None
            if spec.response_format:
                response_format = {"type": spec.response_format}
            result = await self.call_openai(
                messages=messages,
                model=model_name,
                temperature=spec.temperature,
                response_format=response_format,
            )
            text = extract_openai_content(result, "")
            return result, text

    # ──────────────────────────────────────────
    # 키워드 추출
    # ──────────────────────────────────────────

    async def extract_top_keywords(
        self,
        rss_text: str,
        candidate_count: int = 8,
        avoid_keywords: list[str] | None = None,
        avoid_categories: list[str] | None = None,
        avoid_mirroring_hints: list[str] | None = None,
    ) -> list[KeywordPlan]:
        """RSS 뉴스 텍스트에서 투자 키워드 후보 추출 (gpt-5-mini).

        다양성 제약(avoid_*)을 지정하면 해당 키워드/카테고리/힌트를 피한다.
        """
        avoid_keywords = avoid_keywords or []
        avoid_categories = avoid_categories or []
        avoid_mirroring_hints = avoid_mirroring_hints or []

        avoid_lines = []
        if avoid_keywords:
            avoid_lines.append("- 금지 Keyword: " + ", ".join(avoid_keywords))
        if avoid_categories:
            avoid_lines.append("- 금지 Category: " + ", ".join(avoid_categories))
        if avoid_mirroring_hints:
            avoid_lines.append("- 금지 Mirroring Hint: " + ", ".join(avoid_mirroring_hints))
        avoid_guideline = "\n".join(avoid_lines)
        avoid_section = (
            "[재생성 제약 - 반드시 준수]\n" + avoid_guideline if avoid_guideline else ""
        )

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
            category = str(item.get("category", "Market trend")).strip() or "Market trend"
            domain = (
                str(item.get("domain", "macro")).strip().lower().replace(" ", "_") or "macro"
            )
            keyword = str(item.get("keyword", "")).strip()
            title = str(item.get("title", "")).strip()
            context = str(item.get("context", "")).strip()
            hint = str(item.get("mirroringHint", "")).strip()

            if not keyword or not context:
                continue
            if not title or len(title) < 8 or title.upper() == "AI":
                title = "[" + keyword + "] 시장이 주목하는 핵심 포인트"
            title = re.sub(r"^\[.*?\]\s*", "", title).strip()

            output.append(
                KeywordPlan(
                    category=category,
                    domain=domain,
                    keyword=keyword,
                    title=title,
                    context=context,
                    mirroring_hint=hint,
                )
            )

        LOGGER.info("[KEYWORDS] Extracted %d keyword plans from RSS text", len(output))
        return output

    # ──────────────────────────────────────────
    # 리서치 (2단계: context + simulation)
    # ──────────────────────────────────────────

    async def research_context(
        self,
        keyword: str,
        mirroring_hint: str = "",
    ) -> tuple[str, list[dict[str, str]]]:
        """맥락 리서치 (sonar): 배경, 과거 유사 사례, 차이점, 반대 시나리오.

        Returns:
            (리서치 텍스트, 인용 목록)
        """
        hint = mirroring_hint or _get_sector_mirroring_hint(keyword)
        result, text = await self._call_prompt(
            "research_context",
            keyword=keyword,
            mirroring_hint=hint,
        )
        citations = extract_citations(result)
        LOGGER.info(
            "[RESEARCH-CTX] keyword=%s citations=%d chars=%d",
            keyword, len(citations), len(text),
        )
        return text, citations

    async def research_simulation(
        self,
        keyword: str,
        mirroring_hint: str = "",
    ) -> tuple[str, list[dict[str, str]]]:
        """시뮬레이션 리서치 (sonar): 과거 가격 데이터, 모의 투자 시나리오.

        Returns:
            (리서치 텍스트, 인용 목록)
        """
        hint = mirroring_hint or _get_sector_mirroring_hint(keyword)
        result, text = await self._call_prompt(
            "research_simulation",
            keyword=keyword,
            mirroring_hint=hint,
        )
        citations = extract_citations(result)
        LOGGER.info(
            "[RESEARCH-SIM] keyword=%s citations=%d chars=%d",
            keyword, len(citations), len(text),
        )
        return text, citations

    # ──────────────────────────────────────────
    # 스토리 생성 파이프라인
    # ──────────────────────────────────────────

    async def generate_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        mirroring_hint: str = "",
    ) -> dict[str, Any]:
        """전체 스토리 생성 파이프라인.

        plan(gpt-5-mini) -> write(claude-sonnet-4.5) -> review(gpt-5-mini)
        -> tone(gpt-5-mini) -> mark(gpt-5-mini) -> post-process
        """
        LOGGER.info("[STORY] Starting pipeline for theme=%s", theme)
        started = time.perf_counter()

        plan = await self._plan_story(
            theme, context_research, simulation_research, mirroring_hint,
        )
        draft = await self._write_story(
            theme, context_research, simulation_research, plan, mirroring_hint,
        )
        reviewed = await self._review_story(theme, draft)
        tone_corrected = await self._correct_tone(reviewed)
        marked = await self._enrich_marks(tone_corrected)
        result = self._ensure_narrative_shape(marked, theme)

        # 품질 메트릭 로깅
        self._log_quality_metrics(result, theme)

        elapsed = time.perf_counter() - started
        LOGGER.info("[STORY] Pipeline complete for theme=%s elapsed=%.2fs", theme, elapsed)
        return result

    async def _plan_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        mirroring_hint: str,
    ) -> dict[str, Any]:
        """스토리 아웃라인 플래닝 (gpt-5-mini)."""
        _, content = await self._call_prompt(
            "planner",
            theme=theme,
            mirroring_hint=mirroring_hint,
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        raw = extract_json_fragment(content, "{", "}")
        parsed = safe_load_json(raw, {})
        return parsed if isinstance(parsed, dict) else {}

    async def _write_story(
        self,
        theme: str,
        context_research: str,
        simulation_research: str,
        plan: dict[str, Any],
        mirroring_hint: str,
    ) -> dict[str, Any]:
        """스토리 초안 작성 (claude-sonnet-4.5)."""
        _, content = await self._call_prompt(
            "writer",
            theme=theme,
            mirroring_hint=mirroring_hint,
            plan=str(plan),
            context_research=context_research[:5000],
            simulation_research=simulation_research[:3000],
        )
        raw = extract_json_fragment(content, "{", "}")
        parsed = safe_load_json(raw, {})
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Story draft is invalid for theme: {theme}")
        return parsed

    async def _review_story(self, theme: str, draft: dict[str, Any]) -> dict[str, Any]:
        """스토리 품질 리뷰 (gpt-5-mini)."""
        _, content = await self._call_prompt("reviewer", draft=str(draft))
        raw = extract_json_fragment(content, "{", "}")
        parsed = safe_load_json(raw, {})
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Story review is invalid for theme: {theme}")
        return parsed

    async def _correct_tone(self, narrative: dict[str, Any]) -> dict[str, Any]:
        """아델리 톤 교정 (gpt-5-mini).

        각 섹션의 content를 아델리 브랜드 말투로 보정한다.
        실패 시 원본을 그대로 반환한다.
        """
        contents_to_fix: list[tuple[str, str]] = []
        for section in NARRATIVE_SECTIONS:
            sec_data = narrative.get(section)
            if isinstance(sec_data, dict):
                text = sec_data.get("content", "")
                if text:
                    contents_to_fix.append((section, text))

        if not contents_to_fix:
            return narrative

        sections_text = "\n".join(
            "[" + section + "]: " + text for section, text in contents_to_fix
        )

        try:
            _, content = await self._call_prompt(
                "tone_corrector", sections_text=sections_text,
            )
            raw = extract_json_fragment(content, "{", "}")
            parsed = safe_load_json(raw, {})

            if isinstance(parsed, dict):
                for section, corrected in parsed.items():
                    if (
                        section in narrative
                        and isinstance(narrative[section], dict)
                        and isinstance(corrected, str)
                    ):
                        narrative[section]["content"] = corrected
                LOGGER.info("[TONE] Successfully corrected %d sections", len(parsed))
            return narrative
        except Exception as exc:
            LOGGER.warning("[TONE] Correction failed, using original: %s", exc)
            return narrative

    async def _enrich_marks(self, narrative: dict[str, Any]) -> dict[str, Any]:
        """용어 마킹 보강 (gpt-5-mini).

        각 섹션의 content/bullets에서 투자 용어를 찾아 <mark> 태그로 감싼다.
        실패 시 원본을 그대로 반환한다.
        """
        slim: dict[str, Any] = {}
        for section in NARRATIVE_SECTIONS:
            sec_data = narrative.get(section)
            if isinstance(sec_data, dict):
                slim[section] = {
                    "content": sec_data.get("content", ""),
                    "bullets": sec_data.get("bullets", []),
                }

        if not slim:
            return narrative

        try:
            _, content = await self._call_prompt(
                "marker",
                narrative_json=json.dumps(slim, ensure_ascii=False),
            )
            raw = extract_json_fragment(content, "{", "}")
            parsed = safe_load_json(raw, {})

            if isinstance(parsed, dict):
                applied = 0
                for section in NARRATIVE_SECTIONS:
                    enriched = parsed.get(section)
                    if not isinstance(enriched, dict):
                        continue
                    original = narrative.get(section)
                    if not isinstance(original, dict):
                        continue
                    enriched_content = enriched.get("content")
                    if isinstance(enriched_content, str) and enriched_content.strip():
                        original["content"] = enriched_content
                    enriched_bullets = enriched.get("bullets")
                    if isinstance(enriched_bullets, list) and enriched_bullets:
                        original["bullets"] = enriched_bullets
                    applied += 1
                LOGGER.info("[MARKER] Enriched marks for %d sections", applied)
            return narrative
        except Exception as exc:
            LOGGER.warning("[MARKER] Enrichment failed, using original: %s", exc)
            return narrative

    # ──────────────────────────────────────────
    # 용어집 생성
    # ──────────────────────────────────────────

    async def generate_batch_definitions(self, terms: list[str]) -> dict[str, str]:
        """용어 일괄 정의 생성 (gpt-5-mini).

        <mark class='term'>으로 감싸진 용어들의 쉬운 한글 설명을 생성한다.
        """
        if not terms:
            return {}

        try:
            _, content = await self._call_prompt("glossary", terms=", ".join(terms))
            raw = extract_json_fragment(content, "{", "}")
            parsed = safe_load_json(raw, {})
            if isinstance(parsed, dict) and parsed:
                return {str(key): str(value) for key, value in parsed.items()}
        except Exception as exc:
            LOGGER.warning("[GLOSSARY] Generation failed: %s", exc)

        # 폴백: 기본 설명 생성
        fallback_terms = terms[:5]
        return {
            term: term + "은(는) 시장을 볼 때 꼭 체크할 핵심 개념이에요."
            for term in fallback_terms
        }

    # ──────────────────────────────────────────
    # 후처리 유틸리티
    # ──────────────────────────────────────────

    def _ensure_narrative_shape(
        self, narrative: dict[str, Any], theme: str,
    ) -> dict[str, Any]:
        """7단계 내러티브 구조 보장 및 정규화.

        누락된 섹션은 폴백으로 채우고, 차트/퀴즈 구조를 검증한다.
        """
        output: dict[str, Any] = {}

        for idx, section in enumerate(NARRATIVE_SECTIONS, start=1):
            raw = narrative.get(section)
            data = raw if isinstance(raw, dict) else {}
            content = str(
                data.get("content") or (theme + " 관련 핵심 내용을 쉽게 정리했어요.")
            ).strip()

            raw_bullets = data.get("bullets")
            bullets_source: list[Any] = (
                raw_bullets if isinstance(raw_bullets, list) else []
            )
            bullets = [str(b).strip() for b in bullets_source if str(b).strip()]

            if section == "devils_advocate":
                bullets = bullets[:3]
                while len(bullets) < 3:
                    bullets.append(theme + " 관련 반대 시나리오")
            else:
                bullets = bullets[:2]
                if not bullets:
                    bullets = [theme + " 핵심 흐름", theme + " 체크 포인트"]

            raw_chart = data.get("chart")
            chart: dict[str, Any] = raw_chart if isinstance(raw_chart, dict) else {}

            section_output: dict[str, Any] = {
                "content": self._ensure_mark_presence(
                    self._to_friendly_tone(self._shorten_content(content)),
                    theme,
                ),
                "bullets": bullets,
                "chart": self._ensure_chart(chart, section, idx),
            }

            # simulation 섹션에 퀴즈 필수
            if section == "simulation":
                raw_quiz = data.get("quiz")
                quiz = (
                    self._ensure_quiz(raw_quiz, theme)
                    if isinstance(raw_quiz, dict)
                    else self._fallback_quiz(theme)
                )
                section_output["quiz"] = quiz

            output[section] = section_output

        return output

    @staticmethod
    def _shorten_content(content: str) -> str:
        """콘텐츠를 최대 3문장으로 축약."""
        normalized = re.sub(r"\s+", " ", content).strip()
        if not normalized:
            return "핵심만 쉽게 정리해드릴게요."
        sentences = re.split(r"(?<=[.!?다요죠])\s+", normalized)
        filtered = [s.strip() for s in sentences if s.strip()]
        return " ".join(filtered[:3])

    @staticmethod
    def _ensure_mark_presence(content: str, theme: str) -> str:
        """최소 1개 <mark> 태그 존재 보장."""
        if MARK_PATTERN.search(content):
            return content
        candidates = [
            token for token in re.split(r"[\s\-_/]+", theme) if len(token.strip()) >= 2
        ]
        if not candidates:
            return content
        term = candidates[0].strip()
        return f"<mark class='term'>{term}</mark> " + content

    @staticmethod
    def _to_friendly_tone(content: str) -> str:
        """하십시오체 -> 해요체 변환 (규칙 기반)."""
        replacements = {
            "합니다.": "해요.",
            "있습니다.": "있어요.",
            "됩니다.": "돼요.",
            "보입니다.": "보여요.",
            "필요합니다.": "필요해요.",
            "중요합니다.": "중요해요.",
            "의미합니다.": "의미해요.",
            "나타납니다.": "나타나요.",
            "예상됩니다.": "예상돼요.",
            "전망됩니다.": "전망이에요.",
            "분석됩니다.": "분석돼요.",
        }
        updated = content
        for source, target in replacements.items():
            updated = updated.replace(source, target)
        return updated

    @staticmethod
    def _ensure_quiz(raw_quiz: dict[str, Any], theme: str) -> dict[str, Any]:
        """퀴즈 데이터 검증 및 정규화."""
        context = str(
            raw_quiz.get("context") or theme + " 관련 과거 사례가 있었어요."
        ).strip()
        question = str(
            raw_quiz.get("question") or "이 상황에서 시장은 어떻게 움직였을까요?"
        ).strip()
        correct_answer = str(raw_quiz.get("correct_answer", "up")).strip()
        actual_result = str(
            raw_quiz.get("actual_result") or "구체적 결과 데이터를 확인할 수 없었어요."
        ).strip()
        lesson = str(
            raw_quiz.get("lesson")
            or "과거 사례와 현재 상황을 함께 고려하며 투자 결정을 내려야 해요."
        ).strip()

        if correct_answer not in ("up", "down", "sideways"):
            correct_answer = "up"

        raw_options = raw_quiz.get("options")
        default_options = [
            {
                "id": "up",
                "label": "올랐어요",
                "explanation": theme + " 이슈로 시장이 상승했을 거예요.",
            },
            {
                "id": "down",
                "label": "내렸어요",
                "explanation": theme + " 이슈로 시장이 하락했을 거예요.",
            },
            {
                "id": "sideways",
                "label": "횡보했어요",
                "explanation": theme + " 이슈에도 시장은 큰 변동이 없었을 거예요.",
            },
        ]

        if isinstance(raw_options, list) and len(raw_options) >= 3:
            options = []
            for opt in raw_options[:3]:
                if isinstance(opt, dict):
                    idx = len(options)
                    options.append({
                        "id": str(opt.get("id", "")).strip()
                        or default_options[idx]["id"],
                        "label": str(opt.get("label", "")).strip()
                        or default_options[idx]["label"],
                        "explanation": str(opt.get("explanation", "")).strip()
                        or default_options[idx]["explanation"],
                    })
                else:
                    options.append(default_options[len(options)])
        else:
            options = default_options

        return {
            "context": context,
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "actual_result": actual_result,
            "lesson": lesson,
        }

    @staticmethod
    def _fallback_quiz(theme: str) -> dict[str, Any]:
        """AI가 퀴즈를 생성하지 못했을 때의 폴백."""
        return {
            "context": theme + "과(와) 유사한 상황이 과거에도 있었어요.",
            "question": "이 상황에서 시장은 어떻게 움직였을까요?",
            "options": [
                {
                    "id": "up",
                    "label": "올랐어요",
                    "explanation": "긍정적 요인이 더 크게 작용해서 시장이 상승했을 거예요.",
                },
                {
                    "id": "down",
                    "label": "내렸어요",
                    "explanation": "불확실성이 커지며 시장이 하락했을 거예요.",
                },
                {
                    "id": "sideways",
                    "label": "횡보했어요",
                    "explanation": "상승과 하락 요인이 팽팽해서 큰 변동이 없었을 거예요.",
                },
            ],
            "correct_answer": "up",
            "actual_result": "실제로는 단기 변동 후 점차 안정을 찾아갔어요.",
            "lesson": "과거 사례가 항상 반복되지는 않아요. "
            "현재 상황만의 고유한 요인을 함께 고려해야 해요.",
        }

    # 섹션별 기대 차트 타입 매핑
    _SECTION_CHART_TYPES: dict[str, str] = {
        "background": "scatter",
        "mirroring": "scatter",
        "simulation": "scatter",  # 첫 trace가 scatter, 두 번째가 bar
        "result": "bar",
        "difference": "bar",
        "devils_advocate": "bar",
        "action": "bar",
    }

    _SECTION_TITLES: dict[str, str] = {
        "background": "현재 시장 배경",
        "mirroring": "과거 유사 사례",
        "simulation": "모의 투자 시뮬레이션",
        "result": "시뮬레이션 결과",
        "difference": "과거 vs 현재",
        "devils_advocate": "반대 시나리오 분석",
        "action": "투자 액션 플랜",
    }

    @classmethod
    def _ensure_chart(
        cls, chart: dict[str, Any], section: str, seed: int,
    ) -> dict[str, Any]:
        """차트 데이터 검증 및 섹션별 적절한 폴백 생성."""
        raw_data = chart.get("data")
        data: list[Any] = raw_data if isinstance(raw_data, list) else []
        raw_layout = chart.get("layout")
        layout: dict[str, Any] = raw_layout if isinstance(raw_layout, dict) else {}

        valid_trace = False
        if data:
            for trace in data:
                if not isinstance(trace, dict):
                    continue
                x_values = trace.get("x")
                y_values = trace.get("y")
                if not isinstance(x_values, list) or not isinstance(y_values, list):
                    continue
                if len(x_values) == 0 or len(x_values) != len(y_values):
                    continue
                # y값이 실제 숫자인지 검증
                if not all(isinstance(v, (int, float)) for v in y_values):
                    continue
                # 모든 y가 0인 경우 거부
                if all(v == 0 for v in y_values):
                    continue
                valid_trace = True
                break

        if not valid_trace:
            data = cls._generate_fallback_chart_data(section, seed)

        # layout에 title 없으면 섹션별 기본 title 주입
        if "title" not in layout:
            layout = {
                **layout,
                "title": cls._SECTION_TITLES.get(section, section.title() + " Insight"),
            }

        return {"data": data, "layout": layout}

    @classmethod
    def _generate_fallback_chart_data(cls, section: str, seed: int) -> list[dict[str, Any]]:
        """섹션별 적절한 타입의 fallback 차트 데이터 생성."""
        expected_type = cls._SECTION_CHART_TYPES.get(section, "scatter")

        if section == "background":
            return [{
                "x": ["2020", "2021", "2022", "2023", "2024"],
                "y": [seed + 8, seed + 10, seed + 9, seed + 12, seed + 13],
                "type": "scatter", "mode": "lines+markers",
                "name": "추세", "line": {"width": 3},
            }]
        elif section == "mirroring":
            return [
                {"x": ["T-4", "T-3", "T-2", "T-1", "T"],
                 "y": [100, 95, 85, 80, 90],
                 "type": "scatter", "mode": "lines+markers",
                 "name": "과거", "line": {"width": 2}},
                {"x": ["T-4", "T-3", "T-2", "T-1", "T"],
                 "y": [100, 97, 88, 82, 92],
                 "type": "scatter", "mode": "lines+markers",
                 "name": "현재", "line": {"width": 2}},
            ]
        elif section == "simulation":
            return [
                {"x": ["1개월", "3개월", "6개월", "12개월"],
                 "y": [1000, 1050, 1020, 1100],
                 "type": "scatter", "mode": "lines+markers",
                 "name": "자산 변화 (만원)", "line": {"width": 3}},
                {"x": ["낙관", "중립", "비관"],
                 "y": [15, 5, -8],
                 "type": "bar", "name": "수익률 (%)",
                 "text": ["+15%", "+5%", "-8%"], "textposition": "outside"},
            ]
        elif section == "result":
            return [{
                "x": ["최적", "평균", "최악"],
                "y": [seed + 15, seed + 5, -(seed + 3)],
                "type": "bar", "name": "수익률 (%)",
                "marker": {"color": ["#4CAF50", "#2196F3", "#F44336"]},
            }]
        elif section == "difference":
            return [
                {"x": ["지표A", "지표B", "지표C"],
                 "y": [seed + 5, seed + 8, seed + 3],
                 "type": "bar", "name": "과거"},
                {"x": ["지표A", "지표B", "지표C"],
                 "y": [seed + 7, seed + 6, seed + 9],
                 "type": "bar", "name": "현재"},
            ]
        elif section == "devils_advocate":
            return [{
                "x": ["시나리오 1", "시나리오 2", "시나리오 3"],
                "y": [-(seed + 5), -(seed + 10), -(seed + 15)],
                "type": "bar", "name": "예상 하락률 (%)",
                "text": [f"-{seed+5}%", f"-{seed+10}%", f"-{seed+15}%"],
                "textposition": "outside",
            }]
        elif section == "action":
            return [{
                "x": ["주식", "채권", "현금"],
                "y": [50, 30, 20],
                "type": "bar", "name": "포트폴리오 비중 (%)",
            }]
        else:
            return [{
                "x": ["2020", "2021", "2022", "2023", "2024"],
                "y": [seed + 8, seed + 10, seed + 9, seed + 12, seed + 13],
                "type": expected_type, "name": section.title(),
            }]

    @staticmethod
    def _log_quality_metrics(narrative: dict[str, Any], theme: str) -> None:
        """생성된 내러티브의 품질 지표를 로깅."""
        sections_with_chart = 0
        chart_types: dict[str, int] = {}
        total_content_len = 0
        mark_count = 0
        has_quiz = False

        for key in NARRATIVE_SECTIONS:
            section = narrative.get(key, {})
            if not isinstance(section, dict):
                continue

            content = str(section.get("content", ""))
            total_content_len += len(content)
            mark_count += len(MARK_PATTERN.findall(content))

            chart = section.get("chart", {})
            if isinstance(chart, dict):
                data = chart.get("data", [])
                if isinstance(data, list) and len(data) > 0:
                    sections_with_chart += 1
                    first_trace = data[0]
                    if isinstance(first_trace, dict):
                        ct = first_trace.get("type", "unknown")
                        chart_types[ct] = chart_types.get(ct, 0) + 1

            if key == "simulation" and isinstance(section.get("quiz"), dict):
                has_quiz = True

        avg_content_len = total_content_len / max(len(NARRATIVE_SECTIONS), 1)
        LOGGER.info(
            "[QUALITY] theme=%s charts=%d/7 chart_types=%s quiz=%s "
            "avg_content=%.0f marks=%d",
            theme, sections_with_chart, chart_types, has_quiz,
            avg_content_len, mark_count,
        )

    @staticmethod
    def calculate_similarity() -> dict[str, str | int]:
        """유사도 점수 계산 (현재 랜덤 스텁, 추후 임베딩 기반으로 대체)."""
        return {
            "score": random.randint(65, 85),
            "reasoning_log": "현재 시장의 추세와 과거의 특정 지점이 높은 유사성을 보이고 있어요.",
        }


# ──────────────────────────────────────────────
# 싱글톤 인스턴스
# ──────────────────────────────────────────────

_instance: AIPipelineService | None = None


def get_ai_pipeline_service() -> AIPipelineService:
    """싱글톤 AI 파이프라인 서비스 인스턴스 반환."""
    global _instance
    if _instance is None:
        _instance = AIPipelineService()
    return _instance
