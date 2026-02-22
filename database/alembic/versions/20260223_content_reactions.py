"""content_reactions 테이블 생성

콘텐츠별 좋아요/싫어요 반응 저장용 테이블.

Revision ID: 20260223_reactions
Revises: 20260218_unique_portfolio
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260223_reactions"
down_revision = "20260218_unique_portfolio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_reactions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("content_id", sa.String(100), nullable=False),
        sa.Column("reaction", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "content_type", "content_id", name="uq_user_content_reaction"),
    )
    op.create_index("ix_content_reactions_content", "content_reactions", ["content_type", "content_id"])
    op.create_index("ix_content_reactions_user_id", "content_reactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_content_reactions_user_id", table_name="content_reactions")
    op.drop_index("ix_content_reactions_content", table_name="content_reactions")
    op.drop_table("content_reactions")
