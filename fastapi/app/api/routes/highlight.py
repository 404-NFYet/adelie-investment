"""Term highlighting API routes."""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add chatbot to path
_chatbot_path = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "chatbot")
if _chatbot_path not in sys.path:
    sys.path.insert(0, _chatbot_path)

try:
    from chatbot.services.term_highlighter import (
        highlight_terms_in_content,
        extract_terms_from_highlighted,
        get_terms_for_difficulty,
    )
except ImportError:
    # Docker 환경에서 chatbot이 별도 컨테이너인 경우 스텁 사용
    import logging
    logging.getLogger(__name__).warning("term_highlighter를 찾을 수 없어 스텁을 사용합니다")
    def highlight_terms_in_content(content, terms=None, difficulty=None):
        return content
    def extract_terms_from_highlighted(content):
        return []
    def get_terms_for_difficulty(difficulty="beginner"):
        return []

router = APIRouter(prefix="/highlight", tags=["Term Highlighting"])


class HighlightRequest(BaseModel):
    """Request model for content highlighting."""
    content: str
    difficulty: str = "beginner"
    custom_terms: Optional[list[str]] = None


class HighlightResponse(BaseModel):
    """Response model for highlighted content."""
    content: str
    highlighted_terms: list[dict]


class TermsResponse(BaseModel):
    """Response model for terms list."""
    difficulty: str
    terms: list[str]
    count: int


@router.post("", response_model=HighlightResponse)
async def highlight_content(request: HighlightRequest) -> HighlightResponse:
    """
    Highlight difficult terms in content based on user difficulty level.
    
    Terms are marked with [[term]] syntax for frontend parsing.
    
    - **content**: The content to highlight
    - **difficulty**: User's difficulty level (beginner, elementary, intermediate)
    - **custom_terms**: Additional terms to highlight
    """
    if not request.content:
        raise HTTPException(status_code=400, detail="Content is required")
    
    result = highlight_terms_in_content(
        content=request.content,
        user_difficulty=request.difficulty,
        custom_terms=request.custom_terms,
    )
    
    return HighlightResponse(
        content=result["content"],
        highlighted_terms=result["highlighted_terms"],
    )


@router.get("/terms/{difficulty}", response_model=TermsResponse)
async def get_highlight_terms(difficulty: str) -> TermsResponse:
    """
    Get list of terms that will be highlighted for a given difficulty level.
    
    - **difficulty**: User's difficulty level (beginner, elementary, intermediate)
    """
    if difficulty not in ["beginner", "elementary", "intermediate"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty. Must be: beginner, elementary, intermediate"
        )
    
    terms = get_terms_for_difficulty(difficulty)
    
    return TermsResponse(
        difficulty=difficulty,
        terms=terms,
        count=len(terms),
    )


@router.post("/extract")
async def extract_highlighted_terms(request: HighlightRequest) -> dict:
    """
    Extract list of highlighted terms from content.
    
    Useful for frontend to know which terms are clickable.
    """
    terms = extract_terms_from_highlighted(request.content)
    return {
        "terms": terms,
        "count": len(terms),
    }
