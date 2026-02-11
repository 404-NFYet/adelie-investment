"""Phase 1: Add trend and catalyst fields to briefing_stocks

Revision ID: 20260209_phase1
Revises: 72a5a3b425a4
Create Date: 2026-02-09 20:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260209_phase1'
down_revision = '72a5a3b425a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add trend and catalyst metadata fields to briefing_stocks."""
    # Phase 1: 멀티데이 트렌드 메타데이터
    op.add_column('briefing_stocks',
        sa.Column('trend_days', sa.Integer(), nullable=True, comment='연속 트렌드 일수 (3, 4, 5...)')
    )
    op.add_column('briefing_stocks',
        sa.Column('trend_type', sa.String(20), nullable=True,
                  comment='consecutive_rise, consecutive_fall, volume_surge')
    )

    # Phase 3: 뉴스 카탈리스트 정보
    op.add_column('briefing_stocks',
        sa.Column('catalyst', sa.Text(), nullable=True,
                  comment='RSS 뉴스에서 추출한 카탈리스트 제목')
    )
    op.add_column('briefing_stocks',
        sa.Column('catalyst_url', sa.Text(), nullable=True,
                  comment='카탈리스트 뉴스 원문 링크')
    )
    op.add_column('briefing_stocks',
        sa.Column('catalyst_published_at', sa.DateTime(), nullable=True,
                  comment='뉴스 발행 시각')
    )
    op.add_column('briefing_stocks',
        sa.Column('catalyst_source', sa.String(50), nullable=True,
                  comment='뉴스 출처 (네이버, 조선경제 등)')
    )


def downgrade() -> None:
    """Remove trend and catalyst fields."""
    op.drop_column('briefing_stocks', 'catalyst_source')
    op.drop_column('briefing_stocks', 'catalyst_published_at')
    op.drop_column('briefing_stocks', 'catalyst_url')
    op.drop_column('briefing_stocks', 'catalyst')
    op.drop_column('briefing_stocks', 'trend_type')
    op.drop_column('briefing_stocks', 'trend_days')
