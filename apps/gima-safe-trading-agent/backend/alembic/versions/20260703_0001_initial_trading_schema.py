"""initial trading schema

Revision ID: 20260703_0001
Revises:
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260703_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_snapshots_symbol", "market_snapshots", ["symbol"])
    op.create_index("ix_market_snapshots_timeframe", "market_snapshots", ["timeframe"])
    op.create_index("ix_market_snapshots_timestamp", "market_snapshots", ["timestamp"])

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("signal_type", sa.String(length=8), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("raw_features_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signals_symbol", "signals", ["symbol"])
    op.create_index("ix_signals_signal_type", "signals", ["signal_type"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "symbol", "exchange", name="uq_watchlist_user_symbol_exchange"),
    )
    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"])
    op.create_index("ix_watchlist_items_symbol", "watchlist_items", ["symbol"])

    op.create_table(
        "risk_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("max_risk_per_trade_percent", sa.Float(), nullable=False),
        sa.Column("max_daily_loss_percent", sa.Float(), nullable=False),
        sa.Column("max_weekly_loss_percent", sa.Float(), nullable=False),
        sa.Column("max_position_concentration_percent", sa.Float(), nullable=False),
        sa.Column("live_trading_enabled", sa.Boolean(), nullable=False),
        sa.Column("kill_switch_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_settings_user_id", "risk_settings", ["user_id"], unique=True)

    op.create_table(
        "risk_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("account_equity", sa.Float(), nullable=False),
        sa.Column("proposed_position_size", sa.Integer(), nullable=False),
        sa.Column("risk_amount", sa.Float(), nullable=False),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("max_loss_percent", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_checks_signal_id", "risk_checks", ["signal_id"])
    op.create_index("ix_risk_checks_status", "risk_checks", ["status"])

    op.create_table(
        "trade_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("stop_loss", sa.Float(), nullable=False),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("is_live_trade", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trade_orders_user_id", "trade_orders", ["user_id"])
    op.create_index("ix_trade_orders_signal_id", "trade_orders", ["signal_id"])
    op.create_index("ix_trade_orders_symbol", "trade_orders", ["symbol"])
    op.create_index("ix_trade_orders_status", "trade_orders", ["status"])

    op.create_table(
        "trade_journal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("trade_orders.id"), nullable=True),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=False),
        sa.Column("pnl_percent", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trade_journal_order_id", "trade_journal", ["order_id"])
    op.create_index("ix_trade_journal_symbol", "trade_journal", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_trade_journal_symbol", table_name="trade_journal")
    op.drop_index("ix_trade_journal_order_id", table_name="trade_journal")
    op.drop_table("trade_journal")
    op.drop_index("ix_trade_orders_status", table_name="trade_orders")
    op.drop_index("ix_trade_orders_symbol", table_name="trade_orders")
    op.drop_index("ix_trade_orders_signal_id", table_name="trade_orders")
    op.drop_index("ix_trade_orders_user_id", table_name="trade_orders")
    op.drop_table("trade_orders")
    op.drop_index("ix_risk_checks_status", table_name="risk_checks")
    op.drop_index("ix_risk_checks_signal_id", table_name="risk_checks")
    op.drop_table("risk_checks")
    op.drop_index("ix_risk_settings_user_id", table_name="risk_settings")
    op.drop_table("risk_settings")
    op.drop_index("ix_watchlist_items_symbol", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_user_id", table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_index("ix_signals_signal_type", table_name="signals")
    op.drop_index("ix_signals_symbol", table_name="signals")
    op.drop_table("signals")
    op.drop_index("ix_market_snapshots_timestamp", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_timeframe", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_symbol", table_name="market_snapshots")
    op.drop_table("market_snapshots")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
