"""Agent UX v7: execution realism + tutor session meta columns

Revision ID: 20260222_agent_v7
Revises: 20260209_phase1, 20260218_unique_portfolio, 20260211_optimization
Create Date: 2026-02-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260222_agent_v7"
down_revision = ("20260209_phase1", "20260218_unique_portfolio", "20260211_optimization")
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [column["name"] for column in inspector.get_columns(table_name)]
    return column_name in columns


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    # portfolio_holdings
    _add_column_if_missing(
        "portfolio_holdings",
        sa.Column("position_side", sa.String(length=10), nullable=False, server_default="long", comment="long | short"),
    )
    _add_column_if_missing(
        "portfolio_holdings",
        sa.Column("leverage", sa.Numeric(6, 2), nullable=False, server_default="1.0", comment="레버리지 배수"),
    )
    _add_column_if_missing(
        "portfolio_holdings",
        sa.Column("borrow_rate_bps", sa.Integer(), nullable=False, server_default="0", comment="공매도 차입수수료 (bps/일)"),
    )
    _add_column_if_missing(
        "portfolio_holdings",
        sa.Column("last_funding_at", sa.DateTime(), nullable=True, comment="차입수수료 마지막 정산 시각"),
    )

    # simulation_trades
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("filled_quantity", sa.Integer(), nullable=False, server_default="0", comment="실제 체결 수량"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("requested_price", sa.Numeric(15, 2), nullable=True, comment="요청 가격"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("executed_price", sa.Numeric(15, 2), nullable=True, comment="실제 체결 가격"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("slippage_bps", sa.Numeric(10, 2), nullable=True, comment="슬리피지 (bps)"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("fee_amount", sa.Numeric(15, 2), nullable=True, comment="수수료"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("order_kind", sa.String(length=10), nullable=False, server_default="market", comment="market | limit"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("order_status", sa.String(length=20), nullable=False, server_default="filled", comment="pending | partial | filled | cancelled"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("position_side", sa.String(length=10), nullable=False, server_default="long", comment="long | short"),
    )
    _add_column_if_missing(
        "simulation_trades",
        sa.Column("leverage", sa.Numeric(6, 2), nullable=False, server_default="1.0", comment="레버리지 배수"),
    )

    # tutor_sessions
    _add_column_if_missing(
        "tutor_sessions",
        sa.Column("cover_icon_key", sa.String(length=80), nullable=True, comment="세션 커버 아이콘 키"),
    )
    _add_column_if_missing(
        "tutor_sessions",
        sa.Column("summary_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="세션 요약 키워드"),
    )
    _add_column_if_missing(
        "tutor_sessions",
        sa.Column("summary_snippet", sa.Text(), nullable=True, comment="세션 요약 스니펫"),
    )
    _add_column_if_missing(
        "tutor_sessions",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false(), comment="홈 고정 여부"),
    )
    _add_column_if_missing(
        "tutor_sessions",
        sa.Column("pinned_at", sa.DateTime(), nullable=True, comment="고정 시각"),
    )


def downgrade() -> None:
    _drop_column_if_exists("tutor_sessions", "pinned_at")
    _drop_column_if_exists("tutor_sessions", "is_pinned")
    _drop_column_if_exists("tutor_sessions", "summary_snippet")
    _drop_column_if_exists("tutor_sessions", "summary_keywords")
    _drop_column_if_exists("tutor_sessions", "cover_icon_key")

    _drop_column_if_exists("simulation_trades", "leverage")
    _drop_column_if_exists("simulation_trades", "position_side")
    _drop_column_if_exists("simulation_trades", "order_status")
    _drop_column_if_exists("simulation_trades", "order_kind")
    _drop_column_if_exists("simulation_trades", "fee_amount")
    _drop_column_if_exists("simulation_trades", "slippage_bps")
    _drop_column_if_exists("simulation_trades", "executed_price")
    _drop_column_if_exists("simulation_trades", "requested_price")
    _drop_column_if_exists("simulation_trades", "filled_quantity")

    _drop_column_if_exists("portfolio_holdings", "last_funding_at")
    _drop_column_if_exists("portfolio_holdings", "borrow_rate_bps")
    _drop_column_if_exists("portfolio_holdings", "leverage")
    _drop_column_if_exists("portfolio_holdings", "position_side")
