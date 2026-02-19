"""user_portfolios.user_id에 UNIQUE 인덱스 재생성

기존 ix_user_portfolios_user_id 인덱스를 DROP 후 UNIQUE로 재생성.
사전에 중복 데이터 정리 필요 (Phase 0 SQL 참조).

Revision ID: 20260218_unique_portfolio
Revises: 20260217_rewards
Create Date: 2026-02-18
"""
from alembic import op

revision = "20260218_unique_portfolio"
down_revision = "20260217_rewards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_user_portfolios_user_id", table_name="user_portfolios")
    op.create_index(
        "ix_user_portfolios_user_id",
        "user_portfolios",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_portfolios_user_id", table_name="user_portfolios")
    op.create_index(
        "ix_user_portfolios_user_id",
        "user_portfolios",
        ["user_id"],
        unique=False,
    )
