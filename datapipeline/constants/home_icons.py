"""Home keyword title-to-icon mapping constants and helpers."""

from __future__ import annotations

from copy import deepcopy
import re

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

_ICON_KEY_ALIASES = {
    "shield-dynamic-color": "sheild-dynamic-color",
}

_SEMANTIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("dollar-dollar-color", ("달러", "usd", "dxy")),
    ("euro-dynamic-color", ("유로", "eur")),
    ("pound-dynamic-color", ("파운드", "gbp")),
    ("yuan-dynamic-color", ("위안", "위안화", "cny", "중국 통화")),
    ("rupee-dynamic-color", ("루피", "inr", "인도 통화")),
    ("3d-coin-dynamic-color", ("비트코인", "이더리움", "코인", "가상자산", "암호화폐", "crypto", "defi")),
    ("card-dynamic-color", ("결제", "신용카드", "체크카드", "카드사", "카드 수수료")),
    ("money-dynamic-color", ("유동성", "현금흐름", "현금 확보", "자금 조달", "자금 경색")),
    ("money-bag-dynamic-color", ("이익", "흑자", "수익성", "배당", "현금 창출")),
    ("calculator-dynamic-color", ("밸류에이션", "per", "pbr", "eps", "실적 추정", "지표 계산")),
    ("file-text-dynamic-color", ("공시", "사업보고서", "리포트", "보고서", "분기 실적 발표")),
    ("sheild-dynamic-color", ("방어", "리스크", "변동성", "헤지", "하방", "안전자산")),
    ("lock-dynamic-color", ("규제", "제재", "보안", "잠금", "봉쇄", "정책 리스크")),
    ("target-dynamic-color", ("목표", "전략", "포트폴리오 전략", "목표가")),
    ("medal-dynamic-color", ("1위", "우수", "최고", "수상", "선두")),
    ("bookmark-dynamic-color", ("핵심 포인트", "체크포인트", "요약", "노트")),
    ("bulb-dynamic-color", ("인사이트", "시사점", "통찰", "아이디어")),
    ("chart-dynamic-color", ("시장", "증시", "금융시장", "지수", "코스피", "코스닥")),
    ("rocket-dynamic-color", ("급등", "상승세", "상승", "랠리", "모멘텀", "성장세")),
]


def normalize_icon_key(icon_key: str | None) -> str | None:
    """Normalize icon key and legacy aliases."""
    if not icon_key:
        return None
    key = str(icon_key).strip()
    if not key:
        return None
    return _ICON_KEY_ALIASES.get(key, key)


def is_valid_icon_key(icon_key: str | None) -> bool:
    """Return whether icon key is valid after normalization."""
    normalized = normalize_icon_key(icon_key)
    return normalized in HOME_ICON_KEYS


def _semantic_text(title: str = "", description: str = "", category: str = "", trend_type: str = "") -> str:
    return " ".join(
        part.strip().lower()
        for part in (title, description, category, trend_type)
        if isinstance(part, str) and part.strip()
    )


def infer_icon_key_by_semantics(
    *,
    title: str = "",
    description: str = "",
    category: str = "",
    trend_type: str = "",
) -> str | None:
    """Infer icon key from semantic hints in title/category/trend_type."""
    text = _semantic_text(
        title=title,
        description=description,
        category=category,
        trend_type=trend_type,
    )
    if not text:
        return None

    for icon_key, keywords in _SEMANTIC_RULES:
        if any(keyword in text for keyword in keywords):
            return icon_key
    return None


def resolve_icon_key(
    *,
    title: str = "",
    description: str = "",
    category: str = "",
    trend_type: str = "",
    icon_key: str | None = None,
) -> str:
    """Resolve icon key with semantic-first policy."""
    semantic_key = infer_icon_key_by_semantics(
        title=title,
        description=description,
        category=category,
        trend_type=trend_type,
    )
    if semantic_key in HOME_ICON_KEYS:
        return semantic_key

    normalized = normalize_icon_key(icon_key)
    if normalized in HOME_ICON_KEYS:
        return normalized

    return DEFAULT_HOME_ICON_KEY


def normalize_title_for_match(title: str | None) -> str:
    """Normalize title text for dictionary match."""
    if not title:
        return ""
    return re.sub(r"[\s\-\–\—·:,'\"`()\[\]{}]+", "", str(title).lower()).strip()


def backfill_top_keywords_icon_keys(top_keywords: dict | None) -> tuple[dict, int]:
    """Return a copy of top_keywords with missing/invalid icon_key backfilled."""
    payload = deepcopy(top_keywords) if isinstance(top_keywords, dict) else {"keywords": []}
    keywords = payload.get("keywords")
    if not isinstance(keywords, list):
        payload["keywords"] = []
        return payload, 0

    updated = 0
    for kw in keywords:
        if not isinstance(kw, dict):
            continue

        current_icon = kw.get("icon_key")
        resolved = resolve_icon_key(
            title=kw.get("title", ""),
            description=kw.get("description", ""),
            category=kw.get("category", ""),
            trend_type=kw.get("trend_type", ""),
            icon_key=current_icon,
        )
        normalized_current = normalize_icon_key(current_icon)
        if normalized_current != resolved:
            kw["icon_key"] = resolved
            updated += 1

    return payload, updated
