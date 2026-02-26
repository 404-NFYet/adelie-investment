"""Prometheus custom metrics."""

from prometheus_client import Counter, Histogram

AUTH_LOGIN_TOTAL = Counter(
    "auth_login_total",
    "Login attempts",
    ["result"],
)

AUTH_REFRESH_TOTAL = Counter(
    "auth_refresh_total",
    "Refresh attempts",
    ["result"],
)

AUTH_REGISTER_TOTAL = Counter(
    "auth_register_total",
    "Register attempts",
    ["result"],
)

AUTH_LOGOUT_TOTAL = Counter(
    "auth_logout_total",
    "Logout attempts",
    ["result"],
)

PIPELINE_JOB_TOTAL = Counter(
    "pipeline_job_total",
    "Pipeline job attempts",
    ["type", "result"],
)

TRADING_ORDER_TOTAL = Counter(
    "trading_order_total",
    "Trading order attempts",
    ["side", "result"],
)

PORTFOLIO_REFRESH_TOTAL = Counter(
    "portfolio_refresh_total",
    "Portfolio refresh attempts",
    ["result"],
)

EXTERNAL_API_REQUEST_TOTAL = Counter(
    "external_api_request_total",
    "External API requests",
    ["provider", "result"],
)

EXTERNAL_API_LATENCY_SECONDS = Histogram(
    "external_api_latency_seconds",
    "External API latency in seconds",
    ["provider"],
)

CACHE_HIT_TOTAL = Counter(
    "cache_hit_total",
    "Cache hit/miss counts",
    ["cache", "hit"],
)

DB_QUERY_TOTAL = Counter(
    "db_query_total",
    "Database query counts",
    ["operation", "result"],
)

TUTOR_CHAT_TOTAL = Counter(
    "tutor_chat_total",
    "Tutor chat attempts",
    ["result"],
)

TUTOR_CHAT_TOKENS_TOTAL = Counter(
    "tutor_chat_tokens_total",
    "Tutor chat total tokens",
    ["model"],
)

BRIEFING_TODAY_TOTAL = Counter(
    "briefing_today_total",
    "Today briefing requests",
    ["result"],
)

QUIZ_REWARD_TOTAL = Counter(
    "quiz_reward_total",
    "Quiz reward attempts",
    ["result"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
