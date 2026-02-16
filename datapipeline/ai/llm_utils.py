"""LLM 호출 헬퍼: prompt_loader 연동 + JSON 추출/복구."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from ..prompts.prompt_loader import load_prompt
from ..config import PROMPTS_DIR
from .multi_provider_client import get_multi_provider_client

LOGGER = logging.getLogger(__name__)

_JSON_ONLY_GUARDRAIL = (
    "반드시 JSON object 하나만 반환하세요. "
    "설명/문장/마크다운/코드블록/주석을 절대 포함하지 마세요."
)
_JSON_REPAIR_SYSTEM = (
    "당신은 깨진 JSON을 복구하는 도구입니다. "
    "반드시 유효한 JSON object 하나만 반환하세요."
)
_JSON_REPAIR_TEMPLATE = """다음 모델 응답은 JSON 파싱에 실패했습니다.
아래 텍스트를 의미를 유지한 채 유효한 JSON object로 복구하세요.

제약:
1) 반드시 JSON object만 반환
2) 코드블록/설명/추가 텍스트 금지
3) 값이 불명확하면 null 사용

원본 텍스트:
{raw_text}
"""


class JSONResponseParseError(RuntimeError):
    """JSON 전용 호출이 재시도/폴백까지 실패했을 때 발생."""

    def __init__(
        self,
        *,
        prompt_name: str,
        provider: str,
        model: str,
        detail: str,
    ) -> None:
        super().__init__(detail)
        self.prompt_name = prompt_name
        self.provider = provider
        self.model = model


def _mask_sensitive(text: str) -> str:
    """로그 스니펫에서 민감한 문자열을 마스킹한다."""
    masked = text
    masked = re.sub(
        r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        "***@***",
        masked,
    )
    masked = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s,]+)",
        r"\1=[REDACTED]",
        masked,
    )
    return masked


def _snippet_for_logs(text: str, max_len: int = 280) -> str:
    cleaned = _mask_sensitive(text.replace("\n", "\\n"))
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[:max_len]}...(truncated)"


def _json_error_details(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return (
            f"{exc.msg} (line={exc.lineno}, column={exc.colno}, char={exc.pos})"
        )
    match = re.search(r"line (\d+) column (\d+) \(char (\d+)\)", str(exc))
    if match:
        return (
            f"{exc} (line={match.group(1)}, column={match.group(2)}, "
            f"char={match.group(3)})"
        )
    return str(exc)


def _build_messages(
    *,
    system_message: str,
    user_body: str,
    enforce_json: bool,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    sys_msg = (system_message or "").strip()
    if enforce_json:
        sys_msg = f"{sys_msg}\n\n{_JSON_ONLY_GUARDRAIL}".strip()
    if sys_msg:
        messages.append({"role": "system", "content": sys_msg})

    user_msg = user_body
    if enforce_json:
        user_msg = f"{user_body}\n\n{_JSON_ONLY_GUARDRAIL}"
    messages.append({"role": "user", "content": user_msg})
    return messages


def _build_repair_messages(raw_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _JSON_REPAIR_SYSTEM},
        {"role": "user", "content": _JSON_REPAIR_TEMPLATE.format(raw_text=raw_text)},
    ]


def _invoke_chat_completion(
    *,
    client: Any,
    prompt_name: str,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    thinking: bool,
    thinking_effort: str,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, str] | None,
    attempt: int,
) -> tuple[dict[str, Any], str]:
    result = client.chat_completion(
        provider=provider,
        model=model,
        messages=messages,
        thinking=thinking,
        thinking_effort=thinking_effort,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )
    content = result["choices"][0]["message"]["content"]
    LOGGER.info(
        "LLM call done: prompt=%s provider=%s model=%s attempt=%d tokens=%s",
        prompt_name,
        provider,
        model,
        attempt,
        result.get("usage"),
    )
    return result, content


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """응답에서 JSON 객체 추출 (코드블록 처리 포함)."""
    text = raw_text.strip()

    # 코드블록 제거
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # 직접 파싱 시도
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("Model output JSON is not an object.")
    except json.JSONDecodeError:
        pass

    # { ... } 범위 추출
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in model output. (length={len(raw_text)})")

    candidate = text[start: end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Parsed JSON is not an object.")
    return parsed


def call_llm_with_prompt(
    prompt_name: str,
    variables: dict[str, Any],
    prompts_dir: str | Path | None = None,
) -> dict[str, Any]:
    """프롬프트 로드 -> LLM 호출 -> JSON 파싱.

    Args:
        prompt_name: 프롬프트 템플릿 이름 (확장자 없이).
        variables: 템플릿에 치환할 변수 (dict/list는 자동 JSON 직렬화).
        prompts_dir: 프롬프트 디렉토리 오버라이드.

    Returns:
        파싱된 JSON 딕셔너리.
    """
    # 변수를 문자열로 변환 (dict/list -> JSON string)
    str_vars: dict[str, str] = {}
    for k, v in variables.items():
        if isinstance(v, (dict, list)):
            str_vars[k] = json.dumps(v, ensure_ascii=False, indent=2)
        else:
            str_vars[k] = str(v)

    spec = load_prompt(prompt_name, prompts_dir=prompts_dir or PROMPTS_DIR, **str_vars)
    client = get_multi_provider_client()

    json_mode = spec.response_format == "json_object"
    response_format = {"type": "json_object"} if json_mode else None
    messages = _build_messages(
        system_message=spec.system_message,
        user_body=spec.body,
        enforce_json=json_mode,
    )

    _, first_content = _invoke_chat_completion(
        client=client,
        prompt_name=prompt_name,
        provider=spec.provider,
        model=spec.model,
        messages=messages,
        thinking=spec.thinking,
        thinking_effort=spec.thinking_effort,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        response_format=response_format,
        attempt=1,
    )

    try:
        return extract_json_object(first_content)
    except Exception as exc:
        if not json_mode:
            raise

        parse_detail = _json_error_details(exc)
        LOGGER.warning(
            "JSON_RETRY_ATTEMPT prompt=%s provider=%s model=%s attempt=2 reason=%s snippet=%s",
            prompt_name,
            spec.provider,
            spec.model,
            parse_detail,
            _snippet_for_logs(first_content),
        )

    # 2차: 동일 provider/model에 JSON 복구 요청
    repair_messages = _build_repair_messages(first_content)
    repaired_content = ""
    try:
        _, repaired_content = _invoke_chat_completion(
            client=client,
            prompt_name=prompt_name,
            provider=spec.provider,
            model=spec.model,
            messages=repair_messages,
            thinking=False,
            thinking_effort="low",
            temperature=0.0,
            max_tokens=spec.max_tokens,
            response_format=response_format,
            attempt=2,
        )
        repaired = extract_json_object(repaired_content)
        LOGGER.info(
            "JSON_REPAIR_SUCCESS prompt=%s provider=%s model=%s",
            prompt_name,
            spec.provider,
            spec.model,
        )
        return repaired
    except Exception as repair_exc:
        parse_detail = _json_error_details(repair_exc)
        snippet_source = repaired_content if repaired_content else str(repair_exc)
        LOGGER.warning(
            "JSON_RETRY_ATTEMPT prompt=%s provider=%s model=%s attempt=3 reason=%s snippet=%s",
            prompt_name,
            spec.provider,
            spec.model,
            parse_detail,
            _snippet_for_logs(snippet_source),
        )

    # 3차: OpenAI gpt-5-mini 폴백 1회
    fallback_content = ""
    try:
        _, fallback_content = _invoke_chat_completion(
            client=client,
            prompt_name=prompt_name,
            provider="openai",
            model="gpt-5-mini",
            messages=_build_repair_messages(first_content),
            thinking=False,
            thinking_effort="low",
            temperature=0.0,
            max_tokens=spec.max_tokens,
            response_format={"type": "json_object"},
            attempt=3,
        )
        fallback = extract_json_object(fallback_content)
        LOGGER.info(
            "JSON_FALLBACK_OPENAI_SUCCESS prompt=%s original_provider=%s original_model=%s fallback_model=gpt-5-mini",
            prompt_name,
            spec.provider,
            spec.model,
        )
        return fallback
    except Exception as fallback_exc:
        detail = _json_error_details(fallback_exc)
        snippet_source = fallback_content if fallback_content else str(fallback_exc)
        LOGGER.error(
            "JSON_PARSE_FAILURE prompt=%s provider=%s model=%s detail=%s snippet=%s",
            prompt_name,
            spec.provider,
            spec.model,
            detail,
            _snippet_for_logs(snippet_source),
        )
        raise JSONResponseParseError(
            prompt_name=prompt_name,
            provider=spec.provider,
            model=spec.model,
            detail=(
                "모델 응답 JSON 불량: 자동 복구/폴백까지 실패했습니다. "
                f"detail={detail}"
            ),
        ) from fallback_exc
