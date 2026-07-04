from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SignalDecision:
    symbol: str
    action: str
    confidence: float
    explanation: str
    entry_price: float
    stop_loss: Optional[float]
    indicators: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDecision:
    status: str
    approved: bool
    reason: str
    quantity: int
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    quantity: int
    entry_price: float
    stop_loss: float
    decision_id: Optional[int] = None
    human_approved: bool = False


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    broker_order_id: Optional[str]
    message: str
    submitted_at: Optional[datetime] = None


class MarketDataRejected(ValueError):
    pass
