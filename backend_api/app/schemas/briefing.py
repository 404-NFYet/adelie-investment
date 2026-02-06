"""Briefing related schemas."""

from typing import Literal, Optional

from pydantic import BaseModel


class BriefingStock(BaseModel):
    """Individual stock in briefing."""
    
    stock_code: str
    stock_name: str
    change_rate: float
    volume: int
    selection_reason: Literal["top_gainer", "top_loser", "high_volume"]
    keywords: list[str] = []


class BriefingResponse(BaseModel):
    """Daily briefing response."""
    
    date: str
    market_summary: str
    top_keywords: list[str]
    gainers: list[BriefingStock]
    losers: list[BriefingStock]
    high_volume: list[BriefingStock]
    kospi: Optional[dict] = None
    kosdaq: Optional[dict] = None
