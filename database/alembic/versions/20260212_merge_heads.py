"""Merge two heads: optimization + phase1

Revision ID: 20260212_merge
Revises: 20260211_optimization, 20260209_phase1
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = '20260212_merge'
down_revision = ('20260211_optimization', '20260209_phase1')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
