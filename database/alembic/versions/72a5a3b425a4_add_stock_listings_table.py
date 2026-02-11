"""add stock_listings table

Revision ID: 72a5a3b425a4
Revises: 20260209_indexes
Create Date: 2026-02-09 20:36:56.825420

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72a5a3b425a4'
down_revision: Union[str, Sequence[str], None] = 'bf2bf190408c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # stock_listings 테이블 생성
    op.create_table(
        'stock_listings',
        sa.Column('stock_code', sa.String(length=6), nullable=False, comment='종목 코드 (예: 005930)'),
        sa.Column('stock_name', sa.String(length=100), nullable=False, comment='종목명 (예: 삼성전자)'),
        sa.Column('market', sa.String(length=10), nullable=False, comment='시장 구분 (KOSPI/KOSDAQ)'),
        sa.Column('sector', sa.String(length=50), nullable=True, comment='섹터 (예: 반도체)'),
        sa.Column('industry', sa.String(length=100), nullable=True, comment='산업 분류 (예: 전자부품 제조업)'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='업데이트 시각'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='상장 여부 (False: 상장폐지)'),
        sa.PrimaryKeyConstraint('stock_code')
    )

    # 인덱스 생성
    op.create_index('ix_stock_listings_name', 'stock_listings', ['stock_name'])
    op.create_index('ix_stock_listings_market_sector', 'stock_listings', ['market', 'sector'])


def downgrade() -> None:
    """Downgrade schema."""
    # 인덱스 삭제
    op.drop_index('ix_stock_listings_market_sector', table_name='stock_listings')
    op.drop_index('ix_stock_listings_name', table_name='stock_listings')

    # 테이블 삭제
    op.drop_table('stock_listings')
