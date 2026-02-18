"""add suggested_questions column

Revision ID: 447d7d4dcd52
Revises: 20260217_rewards
Create Date: 2026-02-18 14:35:25.184745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '447d7d4dcd52'
down_revision: Union[str, Sequence[str], None] = '20260217_rewards'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add suggested_questions column to daily_briefings
    op.add_column('daily_briefings', sa.Column('suggested_questions', sa.JSON(), nullable=True))
    
    # Add suggested_questions column to historical_cases
    op.add_column('historical_cases', sa.Column('suggested_questions', sa.JSON(), nullable=True))
    
    # Add suggested_questions column to broker_reports
    op.add_column('broker_reports', sa.Column('suggested_questions', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove suggested_questions column from broker_reports
    op.drop_column('broker_reports', 'suggested_questions')
    
    # Remove suggested_questions column from historical_cases
    op.drop_column('historical_cases', 'suggested_questions')
    
    # Remove suggested_questions column from daily_briefings
    op.drop_column('daily_briefings', 'suggested_questions')
