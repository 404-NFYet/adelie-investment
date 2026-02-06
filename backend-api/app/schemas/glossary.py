"""Glossary related schemas."""

from typing import Optional

from pydantic import BaseModel


class GlossaryItem(BaseModel):
    """Single glossary item."""
    
    id: int
    term: str
    term_en: Optional[str] = None
    abbreviation: Optional[str] = None
    difficulty: str
    category: str
    definition_short: str
    definition_full: Optional[str] = None
    example: Optional[str] = None
    formula: Optional[str] = None
    related_terms: Optional[str] = None


class GlossaryResponse(BaseModel):
    """Response for glossary list."""
    
    items: list[GlossaryItem]
    total: int
    page: int = 1
    per_page: int = 20
