"""Glossary API routes with Redis caching."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.glossary import Glossary
from app.schemas.glossary import GlossaryItem, GlossaryResponse
from app.services import get_redis_cache

router = APIRouter(prefix="/glossary", tags=["Glossary"])


@router.get("", response_model=GlossaryResponse)
async def get_glossary(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: beginner, elementary, intermediate"),
    category: Optional[str] = Query(None, description="Filter by category: basic, market, indicator, technical, product, strategy"),
    search: Optional[str] = Query(None, description="Search term"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> GlossaryResponse:
    """
    Get glossary terms with optional filtering and pagination.
    
    - **difficulty**: Filter by difficulty level
    - **category**: Filter by category
    - **search**: Search in term, term_en, and definition_short
    """
    # Build query
    query = select(Glossary)
    count_query = select(func.count(Glossary.id))
    
    # Apply filters
    filters = []
    
    if difficulty:
        filters.append(Glossary.difficulty == difficulty)
    
    if category:
        filters.append(Glossary.category == category)
    
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                Glossary.term.ilike(search_pattern),
                Glossary.term_en.ilike(search_pattern),
                Glossary.definition_short.ilike(search_pattern),
                Glossary.abbreviation.ilike(search_pattern),
            )
        )
    
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Glossary.term).offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    glossary_items = result.scalars().all()
    
    # Convert to response
    items = [
        GlossaryItem(
            id=item.id,
            term=item.term,
            term_en=item.term_en,
            abbreviation=item.abbreviation,
            difficulty=item.difficulty,
            category=item.category,
            definition_short=item.definition_short,
            definition_full=item.definition_full,
            example=item.example,
            formula=item.formula,
            related_terms=item.related_terms,
        )
        for item in glossary_items
    ]
    
    return GlossaryResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{term_id}", response_model=GlossaryItem)
async def get_glossary_term(
    term_id: int,
    db: AsyncSession = Depends(get_db),
) -> GlossaryItem:
    """Get a specific glossary term by ID with Redis caching."""
    # Check cache first
    cache = await get_redis_cache()
    cached = await cache.get_glossary(term_id)
    if cached:
        return GlossaryItem(**cached)
    
    # Query database
    result = await db.execute(
        select(Glossary).where(Glossary.id == term_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Term not found")
    
    glossary_item = GlossaryItem(
        id=item.id,
        term=item.term,
        term_en=item.term_en,
        abbreviation=item.abbreviation,
        difficulty=item.difficulty,
        category=item.category,
        definition_short=item.definition_short,
        definition_full=item.definition_full,
        example=item.example,
        formula=item.formula,
        related_terms=item.related_terms,
    )
    
    # Cache the result
    await cache.set_glossary(term_id, glossary_item.model_dump())
    
    return glossary_item


@router.get("/search/{term}", response_model=GlossaryItem)
async def search_glossary_by_term(
    term: str,
    db: AsyncSession = Depends(get_db),
) -> GlossaryItem:
    """Search for a glossary term by exact term name with Redis caching."""
    # Check cache first
    cache = await get_redis_cache()
    cached = await cache.get_glossary_by_term(term)
    if cached:
        return GlossaryItem(**cached)
    
    # Query database
    result = await db.execute(
        select(Glossary).where(Glossary.term == term)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found")
    
    glossary_item = GlossaryItem(
        id=item.id,
        term=item.term,
        term_en=item.term_en,
        abbreviation=item.abbreviation,
        difficulty=item.difficulty,
        category=item.category,
        definition_short=item.definition_short,
        definition_full=item.definition_full,
        example=item.example,
        formula=item.formula,
        related_terms=item.related_terms,
    )
    
    # Cache the result
    await cache.set_glossary_by_term(term, glossary_item.model_dump())
    
    return glossary_item
