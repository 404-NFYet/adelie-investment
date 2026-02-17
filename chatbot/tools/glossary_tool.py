"""Glossary lookup tool for the AI Tutor (async 지원)."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "fastapi"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

# --- async DB 연결 ---

_async_engine = None


async def _get_async_engine():
    """asyncpg 기반 비동기 엔진을 싱글톤으로 반환한다."""
    global _async_engine
    if _async_engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine

        database_url = os.getenv("DATABASE_URL", "")
        # asyncpg 드라이버 확보
        if "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        _async_engine = create_async_engine(
            database_url, pool_size=5, max_overflow=5, pool_pre_ping=True,
        )
    return _async_engine


# --- sync 폴백 (LangGraph ToolNode가 sync로 호출할 수 있으므로 유지) ---

def _get_sync_engine():
    """psycopg2 기반 동기 엔진을 반환한다 (폴백)."""
    from sqlalchemy import create_engine

    database_url = os.getenv("DATABASE_URL", "")
    if "+asyncpg" in database_url:
        database_url = database_url.replace("+asyncpg", "")
    return create_engine(database_url)


# --- 용어 목록 조회 ---

@tool
async def get_glossary(
    difficulty: str = "beginner",
    category: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    주식 용어 목록을 가져옵니다.

    Args:
        difficulty: 난이도 (beginner/elementary/intermediate)
        category: 카테고리 (basic/market/indicator/technical/product/strategy)
        limit: 최대 개수

    Returns:
        용어 목록 (JSON 형식)
    """
    from sqlalchemy import text

    query = """
        SELECT term, term_en, difficulty, category, definition_short
        FROM glossary
        WHERE difficulty = :difficulty
    """
    if category:
        query += " AND category = :category"
    query += " ORDER BY term LIMIT :limit"

    params = {"difficulty": difficulty, "category": category, "limit": limit}

    try:
        engine = await _get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            rows = result.fetchall()
    except Exception as e:
        logger.warning("async glossary 조회 실패, sync 폴백: %s", e)
        # sync 폴백
        engine = _get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()

    terms = [
        {
            "term": row[0],
            "term_en": row[1],
            "difficulty": row[2],
            "category": row[3],
            "definition": row[4],
        }
        for row in rows
    ]
    return json.dumps(terms, ensure_ascii=False, indent=2)


# --- 용어 상세 조회 ---

@tool
async def lookup_term(term: str) -> str:
    """
    특정 주식 용어의 상세 정보를 조회합니다.

    Args:
        term: 조회할 용어 (예: PER, 배당률)

    Returns:
        용어 상세 정보 (JSON 형식)
    """
    from sqlalchemy import text

    query = """
        SELECT term, term_en, abbreviation, difficulty, category,
               definition_short, definition_full, example, formula, related_terms
        FROM glossary
        WHERE term ILIKE :term OR term_en ILIKE :term OR abbreviation ILIKE :term
        LIMIT 1
    """
    params = {"term": f"%{term}%"}

    try:
        engine = await _get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            row = result.fetchone()
    except Exception as e:
        logger.warning("async lookup_term 실패, sync 폴백: %s", e)
        engine = _get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            row = result.fetchone()

    if not row:
        return json.dumps({"error": f"용어 '{term}'을 찾을 수 없습니다."}, ensure_ascii=False)

    term_info = {
        "term": row[0],
        "term_en": row[1],
        "abbreviation": row[2],
        "difficulty": row[3],
        "category": row[4],
        "definition_short": row[5],
        "definition_full": row[6],
        "example": row[7],
        "formula": row[8],
        "related_terms": row[9],
    }
    return json.dumps(term_info, ensure_ascii=False, indent=2)
