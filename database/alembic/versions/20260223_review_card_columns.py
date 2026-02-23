"""Add review card + context accumulation columns to tutor_sessions

복습 카드 메타데이터 컬럼: review_summary, review_key_points, review_topics
대화 컨텍스트 누적 컬럼: context_entities, conversation_summary

Revision ID: 20260223_review
Revises: 20260223_merge
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260223_review"
down_revision = "20260223_merge"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 복습 카드 컬럼
    if not _has_column("tutor_sessions", "review_summary"):
        op.add_column(
            "tutor_sessions",
            sa.Column("review_summary", sa.Text(), nullable=True, comment="복습 카드 3줄 요약"),
        )
    if not _has_column("tutor_sessions", "review_key_points"):
        op.add_column(
            "tutor_sessions",
            sa.Column("review_key_points", sa.JSON(), nullable=True, comment="복습 핵심 포인트 (list[str])"),
        )
    if not _has_column("tutor_sessions", "review_topics"):
        op.add_column(
            "tutor_sessions",
            sa.Column("review_topics", sa.JSON(), nullable=True, comment="복습 주제/종목 키워드 (list[str])"),
        )
    # 대화 컨텍스트 누적 컬럼
    if not _has_column("tutor_sessions", "context_entities"):
        op.add_column(
            "tutor_sessions",
            sa.Column("context_entities", sa.JSON(), nullable=True, comment="누적 컨텍스트 엔티티 (종목, 개념 등)"),
        )
    if not _has_column("tutor_sessions", "conversation_summary"):
        op.add_column(
            "tutor_sessions",
            sa.Column("conversation_summary", sa.Text(), nullable=True, comment="대화 요약 (10턴마다 갱신)"),
        )


def downgrade() -> None:
    if _has_column("tutor_sessions", "conversation_summary"):
        op.drop_column("tutor_sessions", "conversation_summary")
    if _has_column("tutor_sessions", "context_entities"):
        op.drop_column("tutor_sessions", "context_entities")
    if _has_column("tutor_sessions", "review_topics"):
        op.drop_column("tutor_sessions", "review_topics")
    if _has_column("tutor_sessions", "review_key_points"):
        op.drop_column("tutor_sessions", "review_key_points")
    if _has_column("tutor_sessions", "review_summary"):
        op.drop_column("tutor_sessions", "review_summary")
