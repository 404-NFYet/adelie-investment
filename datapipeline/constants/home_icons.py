"""Home keyword title-to-icon mapping constants."""

from __future__ import annotations

DEFAULT_HOME_ICON_KEY = "chart-dynamic-color"

HOME_ICON_CANDIDATES: list[dict[str, str]] = [
    {"key": "chart-dynamic-color", "label": "주가/시장 흐름"},
    {"key": "money-dynamic-color", "label": "현금/유동성"},
    {"key": "money-bag-dynamic-color", "label": "이익/자금"},
    {"key": "wallet-dynamic-color", "label": "소비/자산 보관"},
    {"key": "card-dynamic-color", "label": "결제/신용"},
    {"key": "dollar-dollar-color", "label": "달러 강세/약세"},
    {"key": "euro-dynamic-color", "label": "유럽 통화"},
    {"key": "pound-dynamic-color", "label": "영국 통화"},
    {"key": "yuan-dynamic-color", "label": "중국 통화"},
    {"key": "rupee-dynamic-color", "label": "신흥국 통화"},
    {"key": "3d-coin-dynamic-color", "label": "코인/디지털 자산"},
    {"key": "calculator-dynamic-color", "label": "실적 계산/지표"},
    {"key": "bulb-dynamic-color", "label": "핵심 인사이트"},
    {"key": "rocket-dynamic-color", "label": "급성장/상승"},
    {"key": "target-dynamic-color", "label": "목표가/전략"},
    {"key": "bookmark-dynamic-color", "label": "핵심 포인트"},
    {"key": "file-text-dynamic-color", "label": "리포트/공시"},
    {"key": "medal-dynamic-color", "label": "우수 업종/종목"},
    {"key": "sheild-dynamic-color", "label": "방어/리스크 관리"},
    {"key": "lock-dynamic-color", "label": "규제/보안 이슈"},
]

HOME_ICON_KEYS = {item["key"] for item in HOME_ICON_CANDIDATES}

