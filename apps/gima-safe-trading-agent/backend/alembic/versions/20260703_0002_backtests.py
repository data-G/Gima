"""add backtest tables

Revision ID: 20260703_0002
Revises: 20260703_0001
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260703_0002"
down_revision = "20260703_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initial_capital", sa.Float(), nullable=False),
        sa.Column("final_equity", sa.Float(), nullable=False),
        sa.Column("total_return_percent", sa.Float(), nullable=False),
        sa.Column("max_drawdown_percent", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("loss_rate", sa.Float(), nullable=False),
        sa.Column("profit_factor", sa.Float(), nullable=False),
        sa.Column("sharpe_ratio", sa.Float(), nullable=False),
        sa.Column("number_of_trades", sa.Integer(), nullable=False),
        sa.Column("average_win", sa.Float(), nullable=False),
        sa.Column("average_loss", sa.Float(), nullable=False),
        sa.Column("fees_percent", sa.Float(), nullable=False),
        sa.Column("slippage_percent", sa.Float(), nullable=False),
        sa.Column("stop_loss_percent", sa.Float(), nullable=False),
        sa.Column("position_size_percent", sa.Float(), nullable=False),
        sa.Column("max_allowed_drawdown_percent", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("warning", sa.Text(), nullable=False),
        sa.Column("equity_curve_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_backtest_results_symbol", "backtest_results", ["symbol"])
    op.create_index("ix_backtest_results_strategy_name", "backtest_results", ["strategy_name"])

    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("backtest_id", sa.Integer(), sa.ForeignKey("backtest_results.id"), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=False),
        sa.Column("pnl", sa.Float(), nullable=False),
        sa.Column("pnl_percent", sa.Float(), nullable=False),
        sa.Column("exit_reason", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_backtest_trades_backtest_id", "backtest_trades", ["backtest_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_trades_backtest_id", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_index("ix_backtest_results_strategy_name", table_name="backtest_results")
    op.drop_index("ix_backtest_results_symbol", table_name="backtest_results")
    op.drop_table("backtest_results")
