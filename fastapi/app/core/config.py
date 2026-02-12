"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/narrative_investment"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT (반드시 .env에서 설정 필요)
    JWT_SECRET: str = "narrative-invest-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # API Keys (반드시 .env에서 설정 필요)
    OPENAI_API_KEY: str = ""
    PERPLEXITY_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Pipeline 설정
    TARGET_SCENARIO_COUNT: int = 3

    # CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Application
    DEBUG: bool = False
    APP_NAME: str = "Narrative Investment API"
    APP_VERSION: str = "0.1.0"

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS_ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
