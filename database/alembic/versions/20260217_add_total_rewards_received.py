"""user_portfolios에 total_rewards_received 컬럼 추가 + 기존 데이터 backfill

Revision ID: 20260217_rewards
Revises: 20260216_unique_cases
Create Date: 2026-02-17
"""
import sqlalchemy as sa
from alembic import op

revision = "20260217_rewards"
down_revision = "20260216_unique_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_portfolios",
        sa.Column(
            "total_rewards_received",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
            comment="누적 보상 수령액 (수익률 계산에서 제외용)",
        ),
    )

    # 기존 데이터 backfill: briefing_rewards + dwell_rewards 합산
    op.execute("""
        UPDATE user_portfolios p
        SET total_rewards_received = (
            COALESCE(
                (SELECT SUM(final_reward) FROM briefing_rewards WHERE portfolio_id = p.id),
                0
            )
            + COALESCE(
                (SELECT SUM(reward_amount) FROM dwell_rewards WHERE portfolio_id = p.id),
                0
            )
        )
    """)


def downgrade() -> None:
    op.drop_column("user_portfolios", "total_rewards_received")
