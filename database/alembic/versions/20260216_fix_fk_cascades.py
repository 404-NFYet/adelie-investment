"""FK CASCADE 규칙 보강 — rewards, limit_orders, watchlists

Revision ID: 20260216_fk_cascade
Revises: 20260214_missing
Create Date: 2026-02-16
"""
from alembic import op

# revision identifiers
revision = "20260216_fk_cascade"
down_revision = "20260214_missing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # briefing_rewards: user_id FK
    op.drop_constraint("briefing_rewards_user_id_fkey", "briefing_rewards", type_="foreignkey")
    op.create_foreign_key(
        "briefing_rewards_user_id_fkey", "briefing_rewards", "users",
        ["user_id"], ["id"], ondelete="CASCADE"
    )
    # briefing_rewards: portfolio_id FK
    try:
        op.drop_constraint("briefing_rewards_portfolio_id_fkey", "briefing_rewards", type_="foreignkey")
        op.create_foreign_key(
            "briefing_rewards_portfolio_id_fkey", "briefing_rewards", "user_portfolios",
            ["portfolio_id"], ["id"], ondelete="CASCADE"
        )
    except Exception:
        pass

    # dwell_rewards: user_id FK
    try:
        op.drop_constraint("dwell_rewards_user_id_fkey", "dwell_rewards", type_="foreignkey")
        op.create_foreign_key(
            "dwell_rewards_user_id_fkey", "dwell_rewards", "users",
            ["user_id"], ["id"], ondelete="CASCADE"
        )
    except Exception:
        pass

    # limit_orders: user_id FK
    try:
        op.drop_constraint("limit_orders_user_id_fkey", "limit_orders", type_="foreignkey")
        op.create_foreign_key(
            "limit_orders_user_id_fkey", "limit_orders", "users",
            ["user_id"], ["id"], ondelete="CASCADE"
        )
    except Exception:
        pass

    # watchlists: user_id FK
    try:
        op.drop_constraint("watchlists_user_id_fkey", "watchlists", type_="foreignkey")
        op.create_foreign_key(
            "watchlists_user_id_fkey", "watchlists", "users",
            ["user_id"], ["id"], ondelete="CASCADE"
        )
    except Exception:
        pass


def downgrade() -> None:
    for table, col, ref_table in [
        ("briefing_rewards", "user_id", "users"),
        ("briefing_rewards", "portfolio_id", "user_portfolios"),
        ("dwell_rewards", "user_id", "users"),
        ("limit_orders", "user_id", "users"),
        ("watchlists", "user_id", "users"),
    ]:
        fk_name = f"{table}_{col}_fkey"
        try:
            op.drop_constraint(fk_name, table, type_="foreignkey")
            op.create_foreign_key(fk_name, table, ref_table, [col], ["id"])
        except Exception:
            pass
