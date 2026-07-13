from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="trader", pattern="^(admin|trader|viewer)$")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[str] = Field(default=None, pattern="^(admin|trader|viewer)$")


class UserRead(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    user_id: int = 1
    symbol: str = Field(min_length=1, max_length=24)
    asset_type: str = Field(default="stock", pattern="^(stock|etf)$")
    exchange: str = Field(default="SMART", max_length=32)


class WatchlistUpdate(BaseModel):
    asset_type: Optional[str] = Field(default=None, pattern="^(stock|etf)$")
    exchange: Optional[str] = Field(default=None, max_length=32)
    active: Optional[bool] = None


class WatchlistRead(BaseModel):
    id: int
    user_id: int
    symbol: str
    asset_type: str
    exchange: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketSnapshotCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    timeframe: str = "1d"
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    timestamp: datetime


class MarketSnapshotRead(MarketSnapshotCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalRequest(BaseModel):
    symbol: str


class SignalCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    signal_type: str = Field(pattern="^(BUY|SELL|WAIT)$")
    confidence: float = Field(ge=0, le=1)
    strategy_name: str = "ma20_ma50_rsi_volume"
    explanation: str
    raw_features_json: dict[str, Any] = Field(default_factory=dict)


class SignalRead(SignalCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskCheckCreate(BaseModel):
    signal_id: int
    status: str = Field(pattern="^(APPROVED|BLOCKED)$")
    reason: str
    account_equity: float = Field(gt=0)
    proposed_position_size: int = Field(ge=0)
    risk_amount: float = Field(ge=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    max_loss_percent: float = Field(ge=0)


class RiskCheckRead(RiskCheckCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeOrderCreate(BaseModel):
    user_id: int = 1
    signal_id: int
    symbol: str = Field(min_length=1, max_length=24)
    side: str = Field(pattern="^(BUY|SELL)$")
    quantity: int = Field(gt=0)
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$")
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    is_live_trade: bool = False


class TradeOrderUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    order_type: Optional[str] = Field(default=None, pattern="^(MARKET|LIMIT)$")
    entry_price: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    status: Optional[str] = Field(default=None, pattern="^(PENDING_APPROVAL|APPROVED|REJECTED|PAPER_EXECUTED|CANCELLED)$")
    broker_order_id: Optional[str] = None
    is_live_trade: Optional[bool] = None


class TradeOrderRead(BaseModel):
    id: int
    user_id: int
    signal_id: int
    symbol: str
    side: str
    quantity: int
    order_type: str
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    status: str
    broker_order_id: Optional[str]
    is_live_trade: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TradeJournalCreate(BaseModel):
    order_id: Optional[int] = None
    symbol: str = Field(min_length=1, max_length=24)
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    quantity: Optional[int] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    notes: str = ""


class TradeJournalRead(TradeJournalCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskSettingsCreate(BaseModel):
    user_id: int = 1
    max_risk_per_trade_percent: float = Field(default=0.5, gt=0, le=0.5)
    max_daily_loss_percent: float = Field(default=2.0, gt=0, le=2.0)
    max_weekly_loss_percent: float = Field(default=5.0, gt=0, le=5.0)
    max_position_concentration_percent: float = Field(default=10.0, gt=0, le=10.0)
    live_trading_enabled: bool = False
    kill_switch_enabled: bool = False


class RiskSettingsUpdate(BaseModel):
    max_risk_per_trade_percent: Optional[float] = Field(default=None, gt=0, le=0.5)
    max_daily_loss_percent: Optional[float] = Field(default=None, gt=0, le=2.0)
    max_weekly_loss_percent: Optional[float] = Field(default=None, gt=0, le=5.0)
    max_position_concentration_percent: Optional[float] = Field(default=None, gt=0, le=10.0)
    live_trading_enabled: Optional[bool] = None
    kill_switch_enabled: Optional[bool] = None


class RiskSettingsRead(RiskSettingsCreate):
    id: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalRequest(BaseModel):
    approved: bool
    note: str = ""


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = ""


class SafetyStateRead(BaseModel):
    kill_switch_active: bool
    reason: str


class NotificationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    recipient: Optional[str] = Field(default=None, max_length=32)


class NotificationRead(BaseModel):
    provider: str
    status: str
    message_id: Optional[str]
    detail: str


class ReportRead(BaseModel):
    date: str
    realized_pl: float
    daily_loss_limit: float
    weekly_loss_limit: float
    trading_mode: str
    live_trading_enabled: bool


class BacktestRunRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=24)
    start_date: datetime
    end_date: datetime
    strategy_name: str = Field(pattern="^(moving_average_crossover|rsi_mean_reversion|breakout)$")
    initial_capital: float = Field(gt=0)
    fees_percent: float = 0.05
    slippage_percent: float = 0.05
    stop_loss_percent: float = 3.0
    position_size_percent: float = 20.0
    max_allowed_drawdown_percent: float = 20.0


class BacktestTradeRead(BaseModel):
    id: int
    backtest_id: int
    entry_time: datetime
    exit_time: datetime
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    exit_reason: str

    model_config = {"from_attributes": True}


class BacktestResultCreate(BaseModel):
    symbol: str
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_equity: float
    total_return_percent: float
    max_drawdown_percent: float
    win_rate: float
    loss_rate: float
    profit_factor: float
    sharpe_ratio: float
    number_of_trades: int
    average_win: float
    average_loss: float
    fees_percent: float
    slippage_percent: float
    stop_loss_percent: float
    position_size_percent: float
    max_allowed_drawdown_percent: float
    status: str
    rejection_reason: Optional[str] = None
    warning: str
    equity_curve_json: list[dict[str, Any]]
    trades: list[dict[str, Any]] = Field(default_factory=list)


class BacktestResultRead(BaseModel):
    id: int
    symbol: str
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_equity: float
    total_return_percent: float
    max_drawdown_percent: float
    win_rate: float
    loss_rate: float
    profit_factor: float
    sharpe_ratio: float
    number_of_trades: int
    average_win: float
    average_loss: float
    fees_percent: float
    slippage_percent: float
    stop_loss_percent: float
    position_size_percent: float
    max_allowed_drawdown_percent: float
    status: str
    rejection_reason: Optional[str]
    warning: str
    equity_curve_json: list[dict[str, Any]]
    created_at: datetime
    trades: list[BacktestTradeRead] = []

    model_config = {"from_attributes": True}


class AuditLogCreate(BaseModel):
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    before_json: Optional[dict[str, Any]] = None
    after_json: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogRead(AuditLogCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
