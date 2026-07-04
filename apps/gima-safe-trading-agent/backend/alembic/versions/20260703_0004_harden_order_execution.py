"""harden order execution

Revision ID: 20260703_0004
Revises: 20260703_0003
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "20260703_0004"
down_revision = "20260703_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("uq_trade_orders_broker_order_id", "trade_orders", ["broker_order_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_trade_orders_broker_order_id", table_name="trade_orders")
