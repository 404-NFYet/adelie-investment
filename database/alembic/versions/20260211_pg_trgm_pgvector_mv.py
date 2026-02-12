"""pg_trgm GIN 인덱스 + pgvector embedding 컬럼 + 키워드 빈도 Materialized View

Revision ID: 20260211_optimization
Revises: 20260209_indexes
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger(__name__)

revision = '20260211_optimization'
down_revision = '20260209_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # ── 1. pg_trgm 확장 활성화 ──
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    except Exception as e:
        logger.warning(f"pg_trgm 확장 생성 실패 (이미 존재하거나 권한 부족): {e}")

    # ── 2. pgvector 확장 활성화 ──
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    except Exception as e:
        logger.warning(f"vector 확장 생성 실패 (이미 존재하거나 권한 부족): {e}")

    # ── 3. pg_trgm GIN 인덱스 (한글 퍼지 검색용) ──
    if 'glossary' in existing_tables:
        try:
            op.execute("""
                CREATE INDEX IF NOT EXISTS ix_glossary_term_trgm
                    ON glossary USING gin (term gin_trgm_ops);
            """)
        except Exception as e:
            logger.warning(f"ix_glossary_term_trgm 인덱스 생성 실패: {e}")

        try:
            op.execute("""
                CREATE INDEX IF NOT EXISTS ix_glossary_def_trgm
                    ON glossary USING gin (definition_short gin_trgm_ops);
            """)
        except Exception as e:
            logger.warning(f"ix_glossary_def_trgm 인덱스 생성 실패: {e}")

    if 'historical_cases' in existing_tables:
        try:
            op.execute("""
                CREATE INDEX IF NOT EXISTS ix_historical_cases_title_trgm
                    ON historical_cases USING gin (title gin_trgm_ops);
            """)
        except Exception as e:
            logger.warning(f"ix_historical_cases_title_trgm 인덱스 생성 실패: {e}")

        try:
            op.execute("""
                CREATE INDEX IF NOT EXISTS ix_historical_cases_summary_trgm
                    ON historical_cases USING gin (summary gin_trgm_ops);
            """)
        except Exception as e:
            logger.warning(f"ix_historical_cases_summary_trgm 인덱스 생성 실패: {e}")

    # ── 4. pgvector embedding 컬럼 추가 (historical_cases) ──
    if 'historical_cases' in existing_tables:
        try:
            op.execute("""
                ALTER TABLE historical_cases
                    ADD COLUMN IF NOT EXISTS embedding vector(1536);
            """)
        except Exception as e:
            logger.warning(f"embedding 컬럼 추가 실패: {e}")

        # ivfflat 인덱스는 테이블에 행이 있어야 생성 가능
        try:
            op.execute("""
                CREATE INDEX IF NOT EXISTS ix_historical_cases_embedding
                    ON historical_cases USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
            """)
        except Exception as e:
            logger.warning(
                f"ix_historical_cases_embedding ivfflat 인덱스 생성 실패 "
                f"(테이블에 행이 없으면 정상): {e}"
            )

    # ── 5. Materialized View: 키워드 빈도 집계 ──
    if 'daily_briefings' in existing_tables:
        try:
            op.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_keyword_frequency AS
                SELECT
                    kw->>'title' AS keyword,
                    COUNT(*) AS frequency,
                    MAX(b.briefing_date) AS last_seen
                FROM daily_briefings b,
                     jsonb_array_elements(b.top_keywords->'keywords') AS kw
                WHERE b.top_keywords IS NOT NULL
                GROUP BY kw->>'title'
                ORDER BY frequency DESC;
            """)
        except Exception as e:
            logger.warning(f"mv_keyword_frequency Materialized View 생성 실패: {e}")

        try:
            op.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_keyword_frequency_keyword
                    ON mv_keyword_frequency(keyword);
            """)
        except Exception as e:
            logger.warning(f"ix_mv_keyword_frequency_keyword 인덱스 생성 실패: {e}")


def downgrade() -> None:
    # ── Materialized View 삭제 ──
    try:
        op.execute("DROP INDEX IF EXISTS ix_mv_keyword_frequency_keyword;")
    except Exception as e:
        logger.warning(f"ix_mv_keyword_frequency_keyword 인덱스 삭제 실패: {e}")

    try:
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_keyword_frequency;")
    except Exception as e:
        logger.warning(f"mv_keyword_frequency Materialized View 삭제 실패: {e}")

    # ── embedding 컬럼 및 인덱스 삭제 ──
    try:
        op.execute("DROP INDEX IF EXISTS ix_historical_cases_embedding;")
    except Exception as e:
        logger.warning(f"ix_historical_cases_embedding 인덱스 삭제 실패: {e}")

    try:
        op.execute("ALTER TABLE historical_cases DROP COLUMN IF EXISTS embedding;")
    except Exception as e:
        logger.warning(f"embedding 컬럼 삭제 실패: {e}")

    # ── pg_trgm GIN 인덱스 삭제 ──
    try:
        op.execute("DROP INDEX IF EXISTS ix_historical_cases_summary_trgm;")
    except Exception as e:
        logger.warning(f"ix_historical_cases_summary_trgm 인덱스 삭제 실패: {e}")

    try:
        op.execute("DROP INDEX IF EXISTS ix_historical_cases_title_trgm;")
    except Exception as e:
        logger.warning(f"ix_historical_cases_title_trgm 인덱스 삭제 실패: {e}")

    try:
        op.execute("DROP INDEX IF EXISTS ix_glossary_def_trgm;")
    except Exception as e:
        logger.warning(f"ix_glossary_def_trgm 인덱스 삭제 실패: {e}")

    try:
        op.execute("DROP INDEX IF EXISTS ix_glossary_term_trgm;")
    except Exception as e:
        logger.warning(f"ix_glossary_term_trgm 인덱스 삭제 실패: {e}")
