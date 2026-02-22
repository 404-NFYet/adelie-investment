"""merge agent_v7 and feedback_surveys heads

Revision ID: 20260223_merge
Revises: 20260222_agent_v7, 20260223_surveys
Create Date: 2026-02-23
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision = "20260223_merge"
down_revision = ("20260222_agent_v7", "20260223_surveys")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
