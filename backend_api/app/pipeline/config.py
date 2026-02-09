"""Pipeline configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv


DEFAULT_FEEDS = [
    "https://www.hankyung.com/feed/economy",
    "https://www.mk.co.kr/rss/30100041/",
    "https://www.yonhapnewseconomytv.com/rss/allArticle.xml",
    "https://data.bis.org/feed.xml",
    "http://feeds.bbci.co.uk/news/business/rss.xml",
]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class PipelineConfig:
    """Pipeline configuration."""
    # API Keys
    openai_api_key: str
    perplexity_api_key: str
    anthropic_api_key: str
    
    # Database
    database_url: str
    
    # Model names
    keyword_model: str
    research_model: str
    planner_model: str
    story_model: str
    reviewer_model: str
    glossary_model: str
    tone_model: str
    
    # Pipeline settings
    target_scenario_count: int
    rss_feeds: list[str]
    prompts_dir: str
    
    # Flags
    dry_run: bool
    force_generate: bool
    
    # Default related companies
    default_related_companies: list[dict[str, str]]


def load_config() -> PipelineConfig:
    """Load pipeline configuration from environment variables."""
    load_dotenv()
    
    dry_run = _env_bool("PIPELINE_DRY_RUN", False)
    force_generate = _env_bool("FORCE_GENERATE", False)
    
    # API Keys
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY", "")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Database
    database_url = os.getenv("DATABASE_URL", "postgresql://narative:password@postgres:5432/narrative_invest")
    
    if not dry_run:
        missing = []
        if not openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not perplexity_api_key:
            missing.append("PERPLEXITY_API_KEY")
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Prompts directory
    prompts_dir = os.getenv("PIPELINE_PROMPTS_DIR", "")
    if not prompts_dir:
        # Default to the prompts folder in the same directory as this module
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
    
    related_default = [
        {
            "name": "삼성전자",
            "code": "005930",
            "reason": "시장 대표주",
            "latest_disclosure": "분기보고서",
            "disclosure_url": "#",
        }
    ]
    
    return PipelineConfig(
        openai_api_key=openai_api_key,
        perplexity_api_key=perplexity_api_key,
        anthropic_api_key=anthropic_api_key,
        database_url=database_url,
        keyword_model=os.getenv("KEYWORD_MODEL", "gpt-4o-mini"),
        research_model=os.getenv("RESEARCH_MODEL", "sonar"),
        planner_model=os.getenv("PLANNER_MODEL", "gpt-4o-mini"),
        story_model=os.getenv("STORY_MODEL", "claude-sonnet-4-20250514"),
        reviewer_model=os.getenv("REVIEWER_MODEL", "gpt-4o-mini"),
        glossary_model=os.getenv("GLOSSARY_MODEL", "gpt-4o-mini"),
        tone_model=os.getenv("TONE_MODEL", "gpt-4o-mini"),
        target_scenario_count=_env_int("TARGET_SCENARIO_COUNT", 5),
        rss_feeds=_env_list("RSS_FEEDS", DEFAULT_FEEDS),
        prompts_dir=prompts_dir,
        dry_run=dry_run,
        force_generate=force_generate,
        default_related_companies=related_default,
    )
