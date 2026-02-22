"""feedback_surveys 테이블 생성

피드백 설문 (1~5점 평가 + 자유 의견) 저장용.

Revision ID: 20260223_surveys
Revises: 20260223_reactions
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260223_surveys"
down_revision = "20260223_reactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_surveys",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ui_rating", sa.SmallInteger, nullable=False),
        sa.Column("feature_rating", sa.SmallInteger, nullable=False),
        sa.Column("content_rating", sa.SmallInteger, nullable=False),
        sa.Column("speed_rating", sa.SmallInteger, nullable=False),
        sa.Column("overall_rating", sa.SmallInteger, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("screenshot_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_feedback_surveys_created_at", "feedback_surveys", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_surveys_created_at", table_name="feedback_surveys")
    op.drop_table("feedback_surveys")
