"""Services module - LLM and database services."""

from .term_highlighter import (
    highlight_terms_in_content,
    extract_terms_from_highlighted,
    remove_highlighting,
    get_terms_for_difficulty,
    TERMS_BY_DIFFICULTY,
)

__all__ = [
    "highlight_terms_in_content",
    "extract_terms_from_highlighted",
    "remove_highlighting",
    "get_terms_for_difficulty",
    "TERMS_BY_DIFFICULTY",
]
