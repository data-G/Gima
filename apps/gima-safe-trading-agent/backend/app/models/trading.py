from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    admin = "admin"
    trader = "trader"
    viewer = "viewer"


class AssetType(str, Enum):
    stock = "stock"
    etf = "etf"


class SignalType(str, Enum):
    buy = "BUY"
    sell = "SELL"
    wait = "WAIT"


class RiskStatus(str, Enum):
    approved = "APPROVED"
    blocked = "BLOCKED"


class OrderStatus(str, Enum):
    pending_approval = "PENDING_APPROVAL"
    approved = "APPROVED"
    rejected = "REJECTED"
    paper_executed = "PAPER_EXECUTED"
    cancelled = "CANCELLED"


class OrderSide(str, Enum):
    buy = "BUY"
    sell = "SELL"


class OrderType(str, Enum):
    market = "MARKET"
    limit = "LIMIT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.trader.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="user")
    trade_orders: Mapped[list["TradeOrder"]] = relationship(back_populates="user")
    risk_settings: Mapped[Optional["RiskSettings"]] = relationship(back_populates="user", uselist=False)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "symbol", "exchange", name="uq_watchlist_user_symbol_exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    asset_type: Mapped[str] = mapped_column(String(16), default=AssetType.stock.value)
    exchange: Mapped[str] = mapped_column(String(32), default="SMART")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship(back_populates="watchlist_items")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="1d", index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    signal_type: Mapped[str] = mapped_column(String(8), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    strategy_name: Mapped[str] = mapped_column(String(128), default="ma20_ma50_rsi_volume")
    explanation: Mapped[str] = mapped_column(Text)
    raw_features_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    risk_checks: Mapped[list["RiskCheck"]] = relationship(back_populates="signal")
    trade_orders: Mapped[list["TradeOrder"]] = relationship(back_populates="signal")


class RiskCheck(Base):
    __tablename__ = "risk_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str] = mapped_column(Text)
    account_equity: Mapped[float] = mapped_column(Float)
    proposed_position_size: Mapped[int] = mapped_column(Integer)
    risk_amount: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_loss_percent: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    signal: Mapped[Signal] = relationship(back_populates="risk_checks")


class TradeOrder(Base):
    __tablename__ = "trade_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer)
    order_type: Mapped[str] = mapped_column(String(16), default=OrderType.market.value)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.pending_approval.value, index=True)
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True)
    is_live_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped[User] = relationship(back_populates="trade_orders")
    signal: Mapped[Signal] = relationship(back_populates="trade_orders")
    journal_entries: Mapped[list["TradeJournal"]] = relationship(back_populates="order")


class TradeJournal(Base):
    __tablename__ = "trade_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trade_orders.id"), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_percent: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    order: Mapped[Optional[TradeOrder]] = relationship(back_populates="journal_entries")


class RiskSettings(Base):
    __tablename__ = "risk_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    max_risk_per_trade_percent: Mapped[float] = mapped_column(Float, default=0.5)
    max_daily_loss_percent: Mapped[float] = mapped_column(Float, default=2.0)
    max_weekly_loss_percent: Mapped[float] = mapped_column(Float, default=5.0)
    max_position_concentration_percent: Mapped[float] = mapped_column(Float, default=10.0)
    live_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_switch_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped[User] = relationship(back_populates="risk_settings")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    strategy_name: Mapped[str] = mapped_column(String(128), index=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    initial_capital: Mapped[float] = mapped_column(Float)
    final_equity: Mapped[float] = mapped_column(Float)
    total_return_percent: Mapped[float] = mapped_column(Float)
    max_drawdown_percent: Mapped[float] = mapped_column(Float)
    win_rate: Mapped[float] = mapped_column(Float)
    loss_rate: Mapped[float] = mapped_column(Float)
    profit_factor: Mapped[float] = mapped_column(Float)
    sharpe_ratio: Mapped[float] = mapped_column(Float)
    number_of_trades: Mapped[int] = mapped_column(Integer)
    average_win: Mapped[float] = mapped_column(Float)
    average_loss: Mapped[float] = mapped_column(Float)
    fees_percent: Mapped[float] = mapped_column(Float)
    slippage_percent: Mapped[float] = mapped_column(Float)
    stop_loss_percent: Mapped[float] = mapped_column(Float)
    position_size_percent: Mapped[float] = mapped_column(Float)
    max_allowed_drawdown_percent: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="ACCEPTED")
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warning: Mapped[str] = mapped_column(Text, default="Backtests are historical simulations. Past performance does not guarantee future results.")
    equity_curve_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    trades: Mapped[list["BacktestTrade"]] = relationship(back_populates="backtest", cascade="all, delete-orphan")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtest_results.id"), index=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    side: Mapped[str] = mapped_column(String(8), default="LONG")
    quantity: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float)
    pnl_percent: Mapped[float] = mapped_column(Float)
    exit_reason: Mapped[str] = mapped_column(String(64))

    backtest: Mapped[BacktestResult] = relationship(back_populates="trades")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    before_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
