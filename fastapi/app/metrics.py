"""Prometheus custom metrics."""

from prometheus_client import Counter

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

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
