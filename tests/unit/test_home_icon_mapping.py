"""Unit tests for home icon mapping and keyset consistency."""

from pathlib import Path
import re

from datapipeline.constants.home_icons import (
    DEFAULT_HOME_ICON_KEY,
    HOME_ICON_KEYS,
    backfill_top_keywords_icon_keys,
    is_valid_icon_key,
    normalize_icon_key,
    resolve_icon_key,
)


def test_resolve_icon_key_semantic_first_overrides_existing_icon():
    result = resolve_icon_key(
        title="금융시장 상승세",
        description="시장 지수 강세",
        category="ATTENTION",
        trend_type="consecutive_rise",
        icon_key="lock-dynamic-color",
    )
    assert result == "chart-dynamic-color"


def test_resolve_icon_key_uses_existing_when_semantic_is_ambiguous():
    result = resolve_icon_key(
        title="중립 코멘트",
        description="특정 섹터 언급 없음",
        category="GENERAL",
        trend_type="",
        icon_key="file-text-dynamic-color",
    )
    assert result == "file-text-dynamic-color"


def test_resolve_icon_key_defaults_when_invalid():
    result = resolve_icon_key(
        title="무작위 키워드",
        description="",
        category="",
        trend_type="",
        icon_key="invalid-icon",
    )
    assert result == DEFAULT_HOME_ICON_KEY


def test_normalize_alias_and_validity():
    assert normalize_icon_key("shield-dynamic-color") == "sheild-dynamic-color"
    assert is_valid_icon_key("shield-dynamic-color")


def test_backfill_top_keywords_icon_keys_updates_only_missing_or_invalid():
    payload = {
        "keywords": [
            {"title": "금융시장 상승세", "description": "시장 강세", "category": "GENERAL", "trend_type": "", "icon_key": None},
            {"title": "일반 공시 요약", "description": "실적 발표", "category": "GENERAL", "trend_type": "", "icon_key": "file-text-dynamic-color"},
            {"title": "임의 데이터", "description": "", "category": "", "trend_type": "", "icon_key": "unknown"},
        ]
    }

    patched, changed = backfill_top_keywords_icon_keys(payload)

    assert changed == 2
    assert patched["keywords"][0]["icon_key"] == "chart-dynamic-color"
    assert patched["keywords"][1]["icon_key"] == "file-text-dynamic-color"
    assert patched["keywords"][2]["icon_key"] == DEFAULT_HOME_ICON_KEY


def test_frontend_catalog_keys_match_backend_keys():
    catalog_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "homeIconCatalog.js"
    content = catalog_path.read_text(encoding="utf-8")
    frontend_keys = set(re.findall(r"key:\s*'([^']+)'", content))
    assert frontend_keys == HOME_ICON_KEYS
