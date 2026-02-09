"""Prompt templates loader - 프롬프트 템플릿 로더."""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache


PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """프롬프트 파일 로드 (frontmatter 제외)."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {name}")
    
    content = path.read_text(encoding="utf-8")
    
    # frontmatter (---로 감싸진 부분) 제거
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    
    return content


def load_prompt_with_meta(name: str) -> Dict[str, Any]:
    """프롬프트 파일과 메타데이터 함께 로드."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {name}")
    
    content = path.read_text(encoding="utf-8")
    meta = {}
    
    # frontmatter 파싱
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            content = parts[2].strip()
    
    return {"content": content, "meta": meta}


def render_prompt(template: str, **kwargs) -> str:
    """프롬프트 템플릿 렌더링.
    
    지원 문법:
    - {{variable}} - 변수 치환
    - {{include:filename}} - 다른 프롬프트 포함
    """
    # include 처리
    include_pattern = re.compile(r"\{\{include:([^}]+)\}\}")
    
    def replace_include(match):
        included_name = match.group(1).strip()
        try:
            return load_prompt(included_name)
        except FileNotFoundError:
            return f"[INCLUDE NOT FOUND: {included_name}]"
    
    result = include_pattern.sub(replace_include, template)
    
    # 변수 치환
    for key, value in kwargs.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    
    return result


@lru_cache(maxsize=32)
def get_prompt(name: str) -> str:
    """캐시된 프롬프트 로드."""
    return load_prompt(name)


# 프롬프트 이름 상수
KEYWORD_EXTRACTION = "keyword_extraction"
PLANNER = "planner"
WRITER = "writer"
GLOSSARY = "glossary"
DEEP_DIVE = "deep_dive"
RESEARCH_CONTEXT = "research_context"
RESEARCH_SIMULATION = "research_simulation"
REVIEWER = "reviewer"
TONE_CORRECTOR = "tone_corrector"
CHART_TEMPLATE = "chart_template"
MARKER = "marker"
