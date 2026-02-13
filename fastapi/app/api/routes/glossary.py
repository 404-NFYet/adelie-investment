"""Glossary API - 동적 LLM 기반 용어 설명 생성 + Redis 캐싱.

정적 DB 조회 대신 LLM이 동적으로 용어를 설명하고, 결과를 Redis에 24시간 캐싱한다.
기존 DB에 데이터가 있으면 우선 사용하고, 없으면 LLM으로 생성한다.
"""

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/glossary", tags=["glossary"])

# 캐시 TTL (24시간)
GLOSSARY_CACHE_TTL = 60 * 60 * 24


async def _generate_term_definition(term: str) -> dict:
    """LLM으로 투자 용어 설명을 동적 생성한다."""
    try:
        from openai import AsyncOpenAI
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise HTTPException(status_code=503, detail="용어 설명 서비스를 사용할 수 없습니다 (API key 미설정)")

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"'{term}' 투자 용어를 초보자에게 쉽게 설명해주세요.\n"
                    "아래 JSON 형식으로 응답하세요:\n"
                    '{"term": "용어", "definition_short": "1문장 쉬운 설명", '
                    '"definition_full": "2-3문장 상세 설명", "example": "실제 예시"}'
                ),
            }],
            response_format={"type": "json_object"},
            max_tokens=500,
            temperature=0.5,
        )
        result = json.loads(response.choices[0].message.content)
        result["term"] = term  # 원래 용어 보존
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM 용어 생성 실패 ({term}): {e}")
        raise HTTPException(status_code=502, detail=f"용어 설명 생성 실패: {e}")


async def _get_or_generate_term(term: str, db: AsyncSession) -> dict:
    """Redis 캐시 -> DB -> LLM 순서로 용어 설명을 가져온다."""
    cache_key = f"glossary:term:{term}"

    # 1. Redis 캐시 확인
    cache = await get_redis_cache()
    if cache.client:
        try:
            cached = await cache.client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # 2. DB 확인 (기존 glossary 테이블이 있으면)
    try:
        result = await db.execute(
            text("SELECT term, definition_short, definition_full, example FROM glossary WHERE term ILIKE :t LIMIT 1"),
            {"t": f"%{term}%"},
        )
        row = result.fetchone()
        if row:
            data = {
                "term": row[0],
                "definition_short": row[1] or "",
                "definition_full": row[2] or "",
                "example": row[3] or "",
            }
            # 캐싱
            if cache.client:
                await cache.client.setex(cache_key, GLOSSARY_CACHE_TTL, json.dumps(data, ensure_ascii=False))
            return data
    except Exception:
        pass  # 테이블이 없으면 무시

    # 3. LLM 동적 생성
    data = await _generate_term_definition(term)

    # 캐싱
    if cache.client:
        try:
            await cache.client.setex(cache_key, GLOSSARY_CACHE_TTL, json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

    return data


@router.get("")
async def get_glossary(
    search: Optional[str] = Query(None, description="검색어"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """용어 사전 조회 (기존 DB 호환 + 동적 LLM 생성)."""
    try:
        # 기존 DB 테이블이 있으면 사용
        query = "SELECT id, term, definition_short, difficulty, category FROM glossary"
        params = {}

        if search:
            query += " WHERE term ILIKE :search OR definition_short ILIKE :search"
            params["search"] = f"%{search}%"

        query += " ORDER BY term LIMIT :limit OFFSET :offset"
        params["limit"] = per_page
        params["offset"] = (page - 1) * per_page

        result = await db.execute(text(query), params)
        items = [
            {"id": r[0], "term": r[1], "definition_short": r[2], "difficulty": r[3], "category": r[4]}
            for r in result.fetchall()
        ]

        count_query = "SELECT COUNT(*) FROM glossary"
        if search:
            count_query += " WHERE term ILIKE :search OR definition_short ILIKE :search"
        count_result = await db.execute(text(count_query), {"search": f"%{search}%"} if search else {})
        total = count_result.scalar() or 0

        return {"items": items, "total": total, "page": page, "per_page": per_page}
    except Exception:
        # 테이블 없으면 빈 응답
        return {"items": [], "total": 0, "page": page, "per_page": per_page}


@router.get("/search/{term}")
async def search_glossary_term(term: str, db: AsyncSession = Depends(get_db)):
    """용어 검색 - DB에 없으면 LLM으로 동적 생성."""
    result = await _get_or_generate_term(term, db)
    return result


@router.get("/{term_id}")
async def get_glossary_by_id(term_id: int, db: AsyncSession = Depends(get_db)):
    """ID로 용어 조회 (기존 호환)."""
    try:
        result = await db.execute(
            text("SELECT id, term, definition_short, definition_full, example, difficulty, category FROM glossary WHERE id = :id"),
            {"id": term_id},
        )
        row = result.fetchone()
        if row:
            return {
                "id": row[0], "term": row[1], "definition_short": row[2],
                "definition_full": row[3], "example": row[4],
                "difficulty": row[5], "category": row[6],
            }
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="용어를 찾을 수 없습니다")
