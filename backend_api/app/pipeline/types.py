"""Data types for the pipeline."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KeywordPlan:
    """Keyword extraction result."""
    category: str
    keyword: str
    title: str
    context: str
    domain: str = "macro"
    mirroring_hint: str = ""
