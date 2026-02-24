"""지정가 주문 만료 컬럼 추가

simulation_trades 테이블에 expires_at 컬럼 추가.
지정가 주문의 24시간 자동 만료를 위해 사용.

Revision ID: 20260223_expires
Revises: 20260223_review
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260223_expires"
down_revision = "20260223_review"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table_name, "col": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not _has_column("simulation_trades", "expires_at"):
        op.add_column(
            "simulation_trades",
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="지정가 주문 만료 시각",
            ),
        )


def downgrade() -> None:
    if _has_column("simulation_trades", "expires_at"):
        op.drop_column("simulation_trades", "expires_at")
