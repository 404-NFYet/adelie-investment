"""Add narrative tables and quiz_correct field

Revision ID: 20260209_narrative
Revises: 
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260209_narrative'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'daily_narratives',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('main_keywords', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('glossary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index('ix_daily_narratives_date', 'daily_narratives', ['date'])
    
    op.create_table(
        'narrative_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('narrative_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('related_companies', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mirroring_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('narrative_sections', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['narrative_id'], ['daily_narratives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_narrative_scenarios_narrative_id', 'narrative_scenarios', ['narrative_id'])
    op.create_index('ix_narrative_scenarios_sort_order', 'narrative_scenarios', ['sort_order'])
    
    op.add_column('briefing_rewards', 
        sa.Column('quiz_correct', sa.Boolean(), nullable=True, comment='퀴즈 정답 여부')
    )


def downgrade() -> None:
    op.drop_column('briefing_rewards', 'quiz_correct')
    op.drop_index('ix_narrative_scenarios_sort_order', table_name='narrative_scenarios')
    op.drop_index('ix_narrative_scenarios_narrative_id', table_name='narrative_scenarios')
    op.drop_table('narrative_scenarios')
    op.drop_index('ix_daily_narratives_date', table_name='daily_narratives')
    op.drop_table('daily_narratives')
