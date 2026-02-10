"""프롬프트 로더 - 실험용.

마크다운 프롬프트 파일을 로드하고, 프론트매터 파싱, include 해석,
변수 치환을 수행한다.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pipeline.types import PromptSpec

LOGGER = logging.getLogger(__name__)

# 프롬프트 디렉토리 (experiments/prompts/)
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

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
        prompts_dir: 프롬프트 디렉토리 (기본: experiments/prompts/)
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
