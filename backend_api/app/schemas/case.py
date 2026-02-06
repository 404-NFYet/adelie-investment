"""Historical case related schemas."""

from typing import Literal, Optional

from pydantic import BaseModel


class CaseSearchRequest(BaseModel):
    """Request for case search."""
    
    query: str
    recency: Literal["year", "month", "week"] = "year"
    limit: int = 5


class HistoricalCase(BaseModel):
    """Historical case summary."""
    
    id: int
    title: str
    event_year: int
    summary: str
    keywords: list[str]
    similarity_score: float
    citations: list[str] = []


class CaseSearchResponse(BaseModel):
    """Response for case search."""
    
    query: str
    cases: list[HistoricalCase]
    search_source: str = "perplexity"


class StoryResponse(BaseModel):
    """Story content response."""
    
    case_id: int
    title: str
    difficulty: str
    content: str  # Markdown format
    glossary_terms: list[str]
    reading_time_minutes: int
    thinking_point: str = ""  # 생각해볼 포인트


class ComparisonPoint(BaseModel):
    """Single comparison point between past and present."""
    
    aspect: str  # "시장 상황", "정책 대응" 등
    past: str
    present: str
    similarity: Literal["유사", "상이", "부분 유사"]


class ComparisonResponse(BaseModel):
    """Past-present comparison response."""
    
    case_id: int
    past_event: dict
    current_situation: dict
    comparison_points: list[ComparisonPoint]
    lessons: list[str]
    # 실 비교 데이터 (JSONB comparison 필드에서 추출)
    comparison_title: str = ""
    past_metric: Optional[dict] = None
    present_metric: Optional[dict] = None
    analysis: list[str] = []
    poll_question: str = ""
    summary: str = ""


class RelatedCompany(BaseModel):
    """Related company information."""
    
    stock_code: str
    stock_name: str
    relation_type: str  # leader, equipment, potential, main_subject, affected, supply_chain 등
    relation_detail: str
    hops: int = 1  # Graph distance


class CompanyGraphResponse(BaseModel):
    """Company graph response."""
    
    case_id: int
    center_company: str
    related_companies: list[RelatedCompany]
    graph_data: Optional[dict] = None  # For visualization
