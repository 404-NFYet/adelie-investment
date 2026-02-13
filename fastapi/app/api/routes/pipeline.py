"""Pipeline API routes."""

import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Add datapipeline to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "datapipeline"))

from app.core.database import get_db
from app.schemas.pipeline import (
    PipelineTriggerRequest,
    PipelineResult,
    PipelineTriggerResponse,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/trigger", response_model=PipelineTriggerResponse)
async def trigger_pipeline(
    request: PipelineTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> PipelineTriggerResponse:
    """
    Trigger data pipeline tasks.
    
    Available tasks:
    - stock: Collect stock data (top movers, high volume)
    - report: Collect Naver finance research reports
    - vision: Extract data from PDFs using Vision API
    """
    job_id = str(uuid.uuid4())
    results = []
    total_start = time.time()
    
    # Get date
    date_str = request.date or datetime.now().strftime("%Y%m%d")
    
    for task in request.tasks:
        task_start = time.time()
        result = PipelineResult(task=task, status="pending", records_processed=0)
        
        try:
            if task == "stock":
                # Run stock collection
                from collectors.stock_collector import (
                    get_top_movers,
                    get_high_volume_stocks,
                    get_market_summary,
                )
                
                movers = get_top_movers(date_str, top_n=10)
                volume = get_high_volume_stocks(date_str, top_n=10)
                market = get_market_summary(date_str)
                
                records = len(movers.get("gainers", [])) + len(movers.get("losers", [])) + len(volume.get("high_volume", []))
                
                result.status = "success"
                result.records_processed = records
                
            elif task == "report":
                # Run report collection
                import asyncio
                from collectors.naver_report_crawler import collect_reports
                
                reports = await collect_reports(pages=1, download=False)
                
                result.status = "success"
                result.records_processed = len(reports)
                
            elif task == "vision":
                # Vision API extraction (requires MinIO and PDFs)
                result.status = "skipped"
                result.error = "Vision extraction requires MinIO and PDF files"
                
            else:
                result.status = "failed"
                result.error = f"Unknown task: {task}"
                
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
        
        result.duration_seconds = time.time() - task_start
        results.append(result)
    
    total_duration = time.time() - total_start

    # ── 후처리: 캐시 무효화 + MV 리프레시 ──
    try:
        from app.services.redis_cache import get_redis_cache
        cache = await get_redis_cache()
        await cache.invalidate_pipeline_caches()
    except Exception:
        pass  # 캐시 무효화 실패해도 응답은 정상 반환

    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text(
                "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_keyword_frequency"
            ))
            await session.commit()
    except Exception:
        pass

    return PipelineTriggerResponse(
        job_id=job_id,
        results=results,
        total_duration=total_duration,
    )


@router.get("/status/{job_id}")
async def get_pipeline_status(job_id: str) -> dict:
    """
    Get status of a pipeline job.
    
    Note: In production, this would track actual job status from a queue.
    """
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Pipeline jobs are executed synchronously in this version.",
    }
