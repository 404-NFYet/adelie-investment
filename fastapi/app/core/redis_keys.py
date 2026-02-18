"""Redis 키 스키마 — 네임스페이스: {env}:{service}:{module}:..."""

import os

ENV = os.getenv("ENV", "dev")


def key_term_explanation(difficulty: str, term: str) -> str:
    return f"{ENV}:api:tutor:term:{difficulty}:{term.lower()}"


def key_glossary_by_id(term_id: int) -> str:
    return f"{ENV}:api:glossary:id:{term_id}"


def key_glossary_by_name(term_name: str) -> str:
    return f"{ENV}:api:glossary:name:{term_name.lower()}"


def key_keywords_today(date_str: str) -> str:
    return f"{ENV}:api:keywords:today:{date_str}"


def key_rate_limit(scope: str, identifier: str) -> str:
    return f"{ENV}:rl:{scope}:{identifier}"


def key_user_settings(user_id: int) -> str:
    return f"{ENV}:api:user:settings:{user_id}"


def key_portfolio_summary(user_id: int) -> str:
    return f"{ENV}:api:portfolio:summary:{user_id}"


# TTL 상수 (초 단위)
TTL_SHORT = 60       # 1분 (rate limit window)
TTL_MEDIUM = 300     # 5분 (keywords, portfolio summary)
TTL_LONG = 3600      # 1시간
TTL_DAY = 86400      # 24시간 (term/glossary)
