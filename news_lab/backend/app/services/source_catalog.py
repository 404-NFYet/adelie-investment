from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.core.models import SourceItem


@lru_cache(maxsize=1)
def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config" / "sources.yml"
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_sources(market: str) -> list[SourceItem]:
    config = _load_config()
    market_key = market.upper()
    entries = config.get("markets", {}).get(market_key, [])
    return [SourceItem.model_validate(entry) for entry in entries]


def get_source_by_id(market: str, source_id: str) -> SourceItem | None:
    for source in get_sources(market):
        if source.id == source_id:
            return source
    return None
