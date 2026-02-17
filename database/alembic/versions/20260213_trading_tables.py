"""limit_orders, watchlists 정식 마이그레이션 + briefing_rewards UNIQUE 제약

Revision ID: 20260213_trading
Revises: 20260212_merge
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa

revision = '20260213_trading'
down_revision = '20260212_merge'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # limit_orders 테이블 (CREATE IF NOT EXISTS로 안전하게)
    op.execute("""
        CREATE TABLE IF NOT EXISTS limit_orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) NOT NULL,
            stock_code VARCHAR(10) NOT NULL,
            stock_name VARCHAR(100) NOT NULL,
            order_type VARCHAR(4) NOT NULL,
            target_price INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            status VARCHAR(10) DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            filled_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_limit_orders_user_id ON limit_orders(user_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_limit_orders_status ON limit_orders(status)
    """)

    # watchlists 테이블
    op.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) NOT NULL,
            stock_code VARCHAR(10) NOT NULL,
            stock_name VARCHAR(100) NOT NULL,
            added_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, stock_code)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_watchlists_user_id ON watchlists(user_id)
    """)

    # briefing_rewards에 중복 방지 UNIQUE 제약 (테이블/제약 없으면 무시)
    op.execute("""
        DO $$
        BEGIN
            -- briefing_rewards 테이블이 존재하는지 먼저 확인
            IF to_regclass('public.briefing_rewards') IS NOT NULL THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_briefing_rewards_user_case'
                ) THEN
                    ALTER TABLE briefing_rewards
                    ADD CONSTRAINT uq_briefing_rewards_user_case UNIQUE (user_id, case_id);
                END IF;
            END IF;
        END $$;
    """)

    # current_cash 컬럼 NOT NULL + 기본값 설정
    op.execute("""
        UPDATE user_portfolios SET current_cash = 1000000 WHERE current_cash IS NULL
    """)
    op.execute("""
        ALTER TABLE user_portfolios ALTER COLUMN current_cash SET NOT NULL
    """)
    op.execute("""
        ALTER TABLE user_portfolios ALTER COLUMN current_cash SET DEFAULT 1000000
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE user_portfolios ALTER COLUMN current_cash DROP NOT NULL")
    op.execute("ALTER TABLE user_portfolios ALTER COLUMN current_cash DROP DEFAULT")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_briefing_rewards_user_case'
            ) THEN
                ALTER TABLE briefing_rewards DROP CONSTRAINT uq_briefing_rewards_user_case;
            END IF;
        END $$;
    """)
    op.execute("DROP TABLE IF EXISTS watchlists")
    op.execute("DROP TABLE IF EXISTS limit_orders")
