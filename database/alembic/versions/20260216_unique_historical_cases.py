"""historical_cases 유니크 제약 추가

Revision ID: 20260216_unique_cases
Revises: 20260216_fk_cascade
Create Date: 2026-02-16
"""
from alembic import op

revision = "20260216_unique_cases"
down_revision = "20260216_fk_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_historical_cases_title_year",
        "historical_cases",
        ["title", "event_year"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_historical_cases_title_year", "historical_cases", type_="unique")
