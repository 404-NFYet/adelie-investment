"""Pipeline related schemas."""

from typing import Literal, Optional

from pydantic import BaseModel


class PipelineTriggerRequest(BaseModel):
    """Request to trigger pipeline."""
    
    tasks: list[Literal["stock", "report", "vision"]]
    date: Optional[str] = None  # Default: today


class PipelineResult(BaseModel):
    """Result for a single pipeline task."""
    
    task: str
    status: Literal["success", "failed", "skipped", "pending"]
    records_processed: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


class PipelineTriggerResponse(BaseModel):
    """Response for pipeline trigger."""
    
    job_id: str
    results: list[PipelineResult]
    total_duration: float
