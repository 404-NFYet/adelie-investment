"""briefing_rewards, dwell_rewards 테이블 생성

Revision ID: 20260214_rewards
Revises: 20260213_trading
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa

revision = '20260214_rewards'
down_revision = '20260213_trading'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # briefing_rewards 테이블 (모델: app.models.reward.BriefingReward)
    op.execute("""
        CREATE TABLE IF NOT EXISTS briefing_rewards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) NOT NULL,
            portfolio_id INTEGER REFERENCES user_portfolios(id) NOT NULL,
            case_id INTEGER NOT NULL,
            base_reward BIGINT NOT NULL,
            multiplier FLOAT DEFAULT 1.0,
            final_reward BIGINT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            maturity_at TIMESTAMPTZ,
            quiz_correct BOOLEAN,
            applied_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_briefing_rewards_user_case UNIQUE (user_id, case_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_briefing_rewards_user_id ON briefing_rewards(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_briefing_rewards_status ON briefing_rewards(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_briefing_rewards_maturity ON briefing_rewards(maturity_at)")

    # dwell_rewards 테이블 (모델: app.models.reward.DwellReward)
    op.execute("""
        CREATE TABLE IF NOT EXISTS dwell_rewards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) NOT NULL,
            portfolio_id INTEGER REFERENCES user_portfolios(id) NOT NULL,
            page VARCHAR(50) NOT NULL,
            dwell_seconds INTEGER NOT NULL,
            reward_amount BIGINT DEFAULT 50000,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dwell_rewards_user_id ON dwell_rewards(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dwell_rewards_created_at ON dwell_rewards(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dwell_rewards")
    op.execute("DROP TABLE IF EXISTS briefing_rewards")
