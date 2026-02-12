"""
AI Module Configuration (shared)

환경 변수에서 AI 관련 설정을 로드합니다.
chatbot/datapipeline 공통 사용.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# .env 파일 경로 설정 (프로젝트 루트 기준 상대 경로)
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# 환경 변수 로드
load_dotenv(ENV_PATH)


@dataclass
class OpenAIConfig:
    """OpenAI API 설정."""

    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    default_model: str = field(default_factory=lambda: os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"))
    vision_model: str = field(default_factory=lambda: os.getenv("OPENAI_VISION_MODEL", "gpt-4o"))
    embedding_model: str = field(default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("OPENAI_MAX_TOKENS", "4096")))
    temperature: float = field(default_factory=lambda: float(os.getenv("OPENAI_TEMPERATURE", "0.7")))


@dataclass
class PerplexityConfig:
    """Perplexity API 설정."""

    api_key: str = field(default_factory=lambda: os.getenv("PERPLEXITY_API_KEY", ""))
    base_url: str = "https://api.perplexity.ai"
    model: str = field(default_factory=lambda: os.getenv("PERPLEXITY_MODEL", "sonar-pro"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("PERPLEXITY_MAX_TOKENS", "4096")))


@dataclass
class LangSmithConfig:
    """LangSmith 트레이싱 설정 (LANGCHAIN_* 환경변수 사용)."""

    api_key: str = field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY", ""))
    project_name: str = field(default_factory=lambda: os.getenv("LANGCHAIN_PROJECT", "adelie-pipeline"))
    tracing_enabled: bool = field(default_factory=lambda: os.getenv("LANGCHAIN_TRACING_V2", "true").lower() == "true")
    endpoint: str = field(default_factory=lambda: os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"))


@dataclass
class AISettings:
    """AI 모듈 통합 설정."""

    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    perplexity: PerplexityConfig = field(default_factory=PerplexityConfig)
    langsmith: LangSmithConfig = field(default_factory=LangSmithConfig)

    def validate(self) -> list[str]:
        """필수 설정 검증. 누락된 설정 목록 반환."""
        missing = []

        if not self.openai.api_key:
            missing.append("OPENAI_API_KEY")

        return missing


# 싱글톤 설정 인스턴스
settings = AISettings()


def get_settings() -> AISettings:
    """설정 인스턴스 반환."""
    return settings


def reload_settings() -> AISettings:
    """환경 변수 다시 로드 후 설정 반환."""
    global settings
    load_dotenv(ENV_PATH, override=True)
    settings = AISettings()
    return settings
