"""notifications, user_feedback, briefing_feedback, usage_events 테이블 생성

Revision ID: 20260214_missing
Revises: 20260214_rewards
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa

revision = '20260214_missing'
down_revision = '20260214_rewards'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- notifications ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) NOT NULL,
            type VARCHAR(20) NOT NULL,
            title VARCHAR(100) NOT NULL,
            message VARCHAR(500) NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            data JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(user_id, is_read)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_created ON notifications(user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_unread ON notifications(user_id, created_at) WHERE is_read = false")

    # --- user_feedback ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            page VARCHAR(50) NOT NULL,
            rating INTEGER CHECK (rating BETWEEN 1 AND 5),
            category VARCHAR(20),
            comment TEXT,
            device_info JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- briefing_feedback ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS briefing_feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            briefing_id INTEGER,
            scenario_keyword VARCHAR(100),
            overall_rating VARCHAR(10),
            favorite_section VARCHAR(30),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- usage_events ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            session_id VARCHAR(36),
            event_type VARCHAR(50),
            event_data JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_events")
    op.execute("DROP TABLE IF EXISTS briefing_feedback")
    op.execute("DROP TABLE IF EXISTS user_feedback")
    op.execute("DROP TABLE IF EXISTS notifications")
