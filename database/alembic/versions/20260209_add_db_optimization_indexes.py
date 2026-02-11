"""DB 최적화: FK/GIN/복합/부분 인덱스 추가 및 company_relations 테이블 삭제

Revision ID: 20260209_indexes
Revises: 20260209_narrative
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260209_indexes'
down_revision = '20260209_narrative'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 테이블 존재 여부 확인
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # ── 1. FK 인덱스 추가 ──
    if 'case_matches' in existing_tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_case_matches_matched_case_id
                ON case_matches (matched_case_id);
        """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_case_matches_current_stock_code
                ON case_matches (current_stock_code);
        """)

    if 'briefing_rewards' in existing_tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_briefing_rewards_portfolio_id
                ON briefing_rewards (portfolio_id);
        """)

    if 'dwell_rewards' in existing_tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_dwell_rewards_portfolio_id
                ON dwell_rewards (portfolio_id);
        """)

    # ── 2. JSONB GIN 인덱스 추가 ──
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_daily_briefings_top_keywords
            ON daily_briefings USING gin (top_keywords);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_briefing_stocks_keywords
            ON briefing_stocks USING gin (keywords);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_narrative_scenarios_glossary
            ON narrative_scenarios USING gin (glossary);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_narrative_scenarios_sources
            ON narrative_scenarios USING gin (sources);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_narrative_scenarios_related_companies
            ON narrative_scenarios USING gin (related_companies);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_broker_reports_stock_codes
            ON broker_reports USING gin (stock_codes);
    """)

    # ── 3. market_daily_history 인덱스 추가 ──
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_market_daily_history_date
            ON market_daily_history (date);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_market_daily_history_index_code
            ON market_daily_history (index_code);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_market_daily_history_date_index
            ON market_daily_history (date, index_code);
    """)

    # ── 4. 복합 인덱스 추가 ──
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_notifications_user_created
            ON notifications (user_id, created_at);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_case_matches_keyword_matched
            ON case_matches (current_keyword, matched_at);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_simulation_trades_portfolio_traded
            ON simulation_trades (portfolio_id, traded_at);
    """)

    # ── 5. 부분(Partial) 인덱스 추가 ──
    if 'tutor_sessions' in existing_tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_tutor_sessions_active
                ON tutor_sessions (user_id) WHERE is_active = true;
        """)

    if 'notifications' in existing_tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_notifications_unread
                ON notifications (user_id, created_at) WHERE is_read = false;
        """)

    if 'briefing_rewards' in existing_tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_briefing_rewards_pending
                ON briefing_rewards (user_id, maturity_at) WHERE status = 'pending';
        """)

    # ── 6. company_relations 테이블 삭제 (Neo4j로 완전 이전) ──
    op.execute("DROP TABLE IF EXISTS company_relations;")


def downgrade() -> None:
    # ── company_relations 테이블 재생성 ──
    op.create_table(
        'company_relations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_stock_code', sa.String(length=10), nullable=False),
        sa.Column('target_stock_code', sa.String(length=10), nullable=False),
        sa.Column('relation_type', sa.String(length=50), nullable=False,
                  comment='supplier, customer, competitor, subsidiary'),
        sa.Column('relation_detail', sa.Text(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True,
                  comment='dart, news, manual'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='상세 그래프는 Neo4j에 저장, 이 테이블은 캐시/참조용'
    )
    op.create_index('ix_company_relations_source', 'company_relations',
                    ['source_stock_code'], unique=False)
    op.create_index('ix_company_relations_target', 'company_relations',
                    ['target_stock_code'], unique=False)
    op.create_index('ix_company_relations_type', 'company_relations',
                    ['relation_type'], unique=False)

    # ── 부분(Partial) 인덱스 삭제 ──
    op.execute("DROP INDEX IF EXISTS ix_briefing_rewards_pending;")
    op.execute("DROP INDEX IF EXISTS ix_notifications_unread;")
    op.execute("DROP INDEX IF EXISTS ix_tutor_sessions_active;")

    # ── 복합 인덱스 삭제 ──
    op.execute("DROP INDEX IF EXISTS ix_simulation_trades_portfolio_traded;")
    op.execute("DROP INDEX IF EXISTS ix_case_matches_keyword_matched;")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_created;")

    # ── market_daily_history 인덱스 삭제 ──
    op.execute("DROP INDEX IF EXISTS ix_market_daily_history_date_index;")
    op.execute("DROP INDEX IF EXISTS ix_market_daily_history_index_code;")
    op.execute("DROP INDEX IF EXISTS ix_market_daily_history_date;")

    # ── JSONB GIN 인덱스 삭제 ──
    op.execute("DROP INDEX IF EXISTS ix_broker_reports_stock_codes;")
    op.execute("DROP INDEX IF EXISTS ix_narrative_scenarios_related_companies;")
    op.execute("DROP INDEX IF EXISTS ix_narrative_scenarios_sources;")
    op.execute("DROP INDEX IF EXISTS ix_narrative_scenarios_glossary;")
    op.execute("DROP INDEX IF EXISTS ix_briefing_stocks_keywords;")
    op.execute("DROP INDEX IF EXISTS ix_daily_briefings_top_keywords;")

    # ── FK 인덱스 삭제 ──
    op.execute("DROP INDEX IF EXISTS ix_dwell_rewards_portfolio_id;")
    op.execute("DROP INDEX IF EXISTS ix_briefing_rewards_portfolio_id;")
    op.execute("DROP INDEX IF EXISTS ix_case_matches_current_stock_code;")
    op.execute("DROP INDEX IF EXISTS ix_case_matches_matched_case_id;")
