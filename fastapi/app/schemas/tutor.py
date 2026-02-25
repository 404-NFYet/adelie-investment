"""AI Tutor related schemas."""

from enum import Enum
from typing import Literal, Optional, Any, Dict, List

from pydantic import BaseModel, Field


class TutorChatRequest(BaseModel):
    """Request for AI Tutor chat."""
    
    session_id: Optional[str] = None
    message: str
    context_type: Optional[Literal["briefing", "case", "comparison", "glossary"]] = None
    context_id: Optional[int] = None
    context_text: Optional[str] = None
    difficulty: str = "beginner"


class TutorChatEvent(BaseModel):
    """SSE event for AI Tutor chat."""
    
    type: Literal["thinking", "tool_call", "text_delta", "done", "error", "action", "visualization"]
    content: Optional[str] = None
    tool: Optional[str] = None
    args: Optional[dict] = None
    session_id: Optional[str] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None
    action_type: Optional[str] = None

class TutorAction(BaseModel):
    """LLM intent classification Output Schema."""
    action: Literal["nav_portfolio", "nav_search", "open_narrative", "start_quiz", "none"]
    reasoning: Optional[str] = None


class ChartType(str, Enum):
    """11 Supported Chart Types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    CANDLESTICK = "candlestick"
    RADAR = "radar"
    BUBBLE = "bubble"
    COMBO_LINE_BAR = "combo_line_bar"
    FUNNEL = "funnel"
    UNSUPPORTED = "unsupported"  # Fallback for invalid requests


class ChartClassificationResult(BaseModel):
    """Step 1: Chart type classification result."""
    reasoning: str = Field(..., description="Reasoning for the selected chart type.")
    chart_type: ChartType = Field(..., description="The classified chart type from the 11 supported options or 'unsupported'.")


class ChartGenerationResult(BaseModel):
    """Step 2: Generated Plotly JSON chart configuration."""
    data: List[Dict[str, Any]] = Field(..., description="Plotly data array containing trace objects.")
    layout: Dict[str, Any] = Field(..., description="Plotly layout object configuring the chart appearance.")
