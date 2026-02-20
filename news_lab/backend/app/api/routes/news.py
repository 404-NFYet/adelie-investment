from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.models import AnalyzeRequest, AnalyzeResponse, Market, TermExplainResponse, VisualizeRequest
from app.services.analyzer import AnalyzeError, analyze_url
from app.services.rss_service import fetch_headlines
from app.services.source_catalog import get_sources
from app.services.upstream_client import UpstreamError, upstream_client
from app.services.url_guard import UrlValidationError, validate_public_article_url


router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "news-lab"}


@router.get("/sources")
async def sources(market: Market = Query("KR")) -> dict:
    items = get_sources(market)
    return {"market": market, "sources": [item.model_dump() for item in items]}


@router.get("/headlines")
async def headlines(
    market: Market = Query("KR"),
    source_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, warnings = fetch_headlines(market=market, source_id=source_id, limit=limit)
    return {
        "market": market,
        "source_id": source_id,
        "headlines": [item.model_dump(mode="json") for item in items],
        "warnings": [{"source_id": w.source_id, "message": w.message} for w in warnings],
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        clean_url = validate_public_article_url(str(payload.url))
    except UrlValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = await analyze_url(clean_url, payload.difficulty, payload.market)
    except AnalyzeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AnalyzeResponse.model_validate(result)


@router.post("/visualize")
async def visualize(payload: VisualizeRequest) -> dict:
    try:
        result = await upstream_client.visualize(payload.description, payload.data_context)
    except UpstreamError as exc:
        raise HTTPException(status_code=502, detail=f"Visualization upstream failed: {exc}") from exc

    return result


@router.get("/explain-term", response_model=TermExplainResponse)
async def explain_term(
    term: str = Query(..., min_length=1),
    difficulty: str = Query("beginner"),
) -> TermExplainResponse:
    safe_difficulty = difficulty if difficulty in {"beginner", "elementary", "intermediate"} else "beginner"

    try:
        result = await upstream_client.explain_term(term, safe_difficulty)
        explanation = str(result.get("explanation", "")).strip() or "설명을 가져오지 못했습니다."
        source = result.get("source")
    except UpstreamError:
        explanation = f"{term} 관련 설명을 가져오지 못했습니다. 잠시 후 다시 시도해주세요."
        source = "fallback"

    return TermExplainResponse(
        term=term,
        difficulty=safe_difficulty,
        explanation=explanation,
        source=source,
    )
