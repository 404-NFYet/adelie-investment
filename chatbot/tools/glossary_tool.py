"""Glossary lookup tool for the AI Tutor."""

import os
import sys
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

# Add paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "fastapi"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Get database connection."""
    from sqlalchemy import create_engine
    
    database_url = os.getenv("DATABASE_URL", "")
    if "+asyncpg" in database_url:
        database_url = database_url.replace("+asyncpg", "")
    
    return create_engine(database_url)


@tool
def get_glossary(
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
    import json
    
    engine = get_db_connection()
    
    query = """
        SELECT term, term_en, difficulty, category, definition_short
        FROM glossary
        WHERE difficulty = :difficulty
    """
    
    if category:
        query += " AND category = :category"
    
    query += " ORDER BY term LIMIT :limit"
    
    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            {"difficulty": difficulty, "category": category, "limit": limit}
        )
        
        terms = [
            {
                "term": row[0],
                "term_en": row[1],
                "difficulty": row[2],
                "category": row[3],
                "definition": row[4],
            }
            for row in result
        ]
    
    return json.dumps(terms, ensure_ascii=False, indent=2)


@tool
def lookup_term(term: str) -> str:
    """
    특정 주식 용어의 상세 정보를 조회합니다.
    
    Args:
        term: 조회할 용어 (예: PER, 배당률)
        
    Returns:
        용어 상세 정보 (JSON 형식)
    """
    from sqlalchemy import text
    import json
    
    engine = get_db_connection()
    
    query = """
        SELECT term, term_en, abbreviation, difficulty, category,
               definition_short, definition_full, example, formula, related_terms
        FROM glossary
        WHERE term ILIKE :term OR term_en ILIKE :term OR abbreviation ILIKE :term
        LIMIT 1
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query), {"term": f"%{term}%"})
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
