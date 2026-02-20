from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Adelie News Lab API"
    app_version: str = "0.1.0"

    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    redis_url: str = ""
    cache_ttl_seconds: int = 600

    upstream_api_base: str = "http://localhost:8082/api/v1"
    request_timeout_seconds: int = 20
    ytdlp_binary: str = "yt-dlp"
    ytdlp_timeout_seconds: int = 20
    youtube_cookies_file: str = ""

    max_article_chars: int = 12000
    min_article_chars: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
