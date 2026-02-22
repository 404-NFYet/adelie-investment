"""SQLAlchemy DB 조회 유틸리티 — SELECT 전용"""

import re

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from config import DB_CONFIG

# 캐시 TTL 상수 (초 단위)
CACHE_TTL = {
    "meta":     300,   # 테이블 목록, 스키마
    "metrics":   60,   # 비즈니스 메트릭
    "health":    30,   # 서버 헬스 상태
    "pipeline": 120,   # 파이프라인 이력
}

# 위험한 SQL 키워드 차단
_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

_engine = None


def get_engine():
    """SQLAlchemy 엔진 (싱글턴)"""
    global _engine
    if _engine is None:
        url = (
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
        )
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def execute_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """SELECT 쿼리 실행 → DataFrame 반환. 비-SELECT 쿼리는 차단."""
    if _DANGEROUS_PATTERN.search(sql):
        raise ValueError("SELECT 쿼리만 허용됩니다. 수정/삭제 쿼리는 실행할 수 없습니다.")

    with get_engine().connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)


@st.cache_data(ttl=CACHE_TTL["meta"])
def get_tables() -> pd.DataFrame:
    """전체 테이블 목록 + 행 수 (5분 캐시)"""
    sql = """
    SELECT
        t.table_name,
        COALESCE(s.n_live_tup, 0) AS row_count
    FROM information_schema.tables t
    LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname
    WHERE t.table_schema = 'public'
      AND t.table_type = 'BASE TABLE'
    ORDER BY t.table_name
    """
    return execute_query(sql)


def get_table_schema(table_name: str) -> pd.DataFrame:
    """테이블 컬럼 정보"""
    sql = """
    SELECT
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = :table_name
    ORDER BY ordinal_position
    """
    return execute_query(sql, {"table_name": table_name})


def get_table_preview(table_name: str, limit: int = 50) -> pd.DataFrame:
    """테이블 최근 N행 미리보기"""
    # 테이블명 검증 (SQL injection 방지)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        raise ValueError(f"유효하지 않은 테이블명: {table_name}")
    limit = min(limit, 500)  # 최대 500행
    sql = f'SELECT * FROM "{table_name}" ORDER BY 1 DESC LIMIT {limit}'
    return execute_query(sql)
