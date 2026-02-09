"""Prompt loader: reads .md prompt templates with frontmatter and variable substitution.

Each prompt file lives under ``pipeline/prompts/`` and follows this format::

    ---
    model_key: planner_model
    temperature: 0.7
    response_format: json_object
    role: system                   # optional
    system_message: You are ...    # optional
    ---
    Prompt body with {{variable}} placeholders.
    {{include:_tone_guide}} will inline another .md file.

``load_prompt`` returns a ``PromptSpec`` dataclass with the rendered body
and metadata extracted from the frontmatter.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

# Default prompts directory (sibling to this file)
_DEFAULT_DIR = Path(__file__).resolve().parent / "prompts"

# Pattern for {{variable}} placeholders
_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")

# Pattern for {{include:filename}} directives
_INCLUDE_PATTERN = re.compile(r"\{\{include:(\w+)\}\}")

# Frontmatter delimiter
_FM_DELIM = "---"


@dataclass
class PromptSpec:
    """Parsed prompt template with metadata."""

    body: str
    model_key: str = ""
    temperature: float = 0.7
    response_format: str | None = None  # "json_object" or None
    role: str = ""                       # "system" if system_message present
    system_message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Split frontmatter (YAML-like key: value) from body."""
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
            # Save previous key
            if current_key:
                meta[current_key] = current_value.strip()
            key, _, value = stripped.partition(":")
            current_key = key.strip()
            current_value = value.strip()
            # Handle YAML multiline indicator >
            if current_value == ">":
                current_value = ""
        elif current_key:
            # Continuation line for multiline values
            current_value += " " + stripped
    if current_key:
        meta[current_key] = current_value.strip()

    body = "\n".join(lines[body_start:])
    return meta, body


def _resolve_includes(body: str, prompts_dir: Path) -> str:
    """Replace {{include:filename}} with contents of the referenced file."""

    def _replacer(match: re.Match[str]) -> str:
        name = match.group(1)
        include_path = prompts_dir / f"{name}.md"
        if not include_path.exists():
            LOGGER.warning("Include file not found: %s", include_path)
            return ""
        return include_path.read_text(encoding="utf-8").strip()

    return _INCLUDE_PATTERN.sub(_replacer, body)


def _substitute_vars(body: str, variables: dict[str, str]) -> str:
    """Replace {{variable}} placeholders with provided values."""

    def _replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return variables[key]
        # Leave unresolved placeholders as empty string
        LOGGER.debug("Unresolved variable: {{%s}}", key)
        return ""

    return _VAR_PATTERN.sub(_replacer, body)


def load_prompt(
    name: str,
    prompts_dir: str | Path | None = None,
    **kwargs: str,
) -> PromptSpec:
    """Load a prompt template by name, resolve includes, substitute variables.

    Args:
        name: Prompt file name without extension (e.g. ``"planner"``).
        prompts_dir: Override directory. Defaults to ``pipeline/prompts/``.
        **kwargs: Variables to substitute in the template.

    Returns:
        PromptSpec with rendered body and metadata.
    """
    directory = Path(prompts_dir) if prompts_dir else _DEFAULT_DIR
    filepath = directory / f"{name}.md"

    if not filepath.exists():
        raise FileNotFoundError(f"Prompt template not found: {filepath}")

    raw = filepath.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)

    # Resolve includes first
    body = _resolve_includes(body, directory)

    # Substitute variables
    str_kwargs = {k: str(v) for k, v in kwargs.items()}
    body = _substitute_vars(body, str_kwargs)

    # Build PromptSpec
    response_format = meta.get("response_format")
    temperature_str = meta.get("temperature", "0.7")
    try:
        temperature = float(temperature_str)
    except (TypeError, ValueError):
        temperature = 0.7

    return PromptSpec(
        body=body.strip(),
        model_key=meta.get("model_key", ""),
        temperature=temperature,
        response_format=response_format if response_format else None,
        role=meta.get("role", ""),
        system_message=meta.get("system_message", ""),
        extra={k: v for k, v in meta.items()
               if k not in ("model_key", "temperature", "response_format", "role", "system_message")},
    )
