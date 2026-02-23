"""add flashcards table

Revision ID: c1d4e8f92b3a
Revises: 72a5a3b425a4
Create Date: 2026-02-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c1d4e8f92b3a'
down_revision: Union[str, Sequence[str], None] = '20260223_merge'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'flashcards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False, comment='카드 제목'),
        sa.Column('content_html', sa.Text(), nullable=False, comment='복습카드 HTML 전체'),
        sa.Column('source_session_id', sa.Integer(), nullable=True, comment='출처 튜터 세션'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_session_id'], ['tutor_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_flashcards_user_id', 'flashcards', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_flashcards_user_id', table_name='flashcards')
    op.drop_table('flashcards')
