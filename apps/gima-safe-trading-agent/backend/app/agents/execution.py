from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.journal import JournalAgent
from app.agents.types import ExecutionResult, OrderRequest
from app.brokers.client import BrokerClient
from app.brokers.factory import create_broker_client
from app.core.config import Settings
from app.models.trading import OrderStatus, Signal, TradeOrder


class ExecutionAgent:
    """Executes orders through the v1 paper-only, human-approved workflow."""

    def __init__(self, settings: Settings, journal: JournalAgent | None = None, broker: BrokerClient | None = None):
        self.settings = settings
        self.journal = journal or JournalAgent()
        self.broker = broker or create_broker_client(settings)

    def queue_paper_order(self, db: Session, decision: Signal, user_id: int = 1, quantity: int = 0, entry_price: float = 0.0, stop_loss: float = 0.0) -> TradeOrder:
        self.journal.log_attempted_order(
            db,
            decision.symbol,
            f"Queue requested for {decision.signal_type} {quantity} shares. Human approval required.",
        )
        order = TradeOrder(
            user_id=user_id,
            signal_id=decision.id,
            symbol=decision.symbol,
            side=decision.signal_type,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            status=OrderStatus.pending_approval.value,
            is_live_trade=False,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    def execute(self, db: Session, order: OrderRequest) -> ExecutionResult:
        self.journal.log_attempted_order(
            db,
            order.symbol,
            f"Execution attempt: side={order.side}, quantity={order.quantity}, human_approved={order.human_approved}.",
        )

        if self.settings.trading_mode != "paper":
            return ExecutionResult("BLOCKED", None, "Only paper trading is supported in v1.")
        if self.settings.is_live_trading_allowed:
            return ExecutionResult("BLOCKED", None, "Live order routing is not implemented in v1.")
        if not self.settings.real_trading_enabled and self.settings.trading_mode == "live":
            return ExecutionResult("BLOCKED", None, "LIVE_TRADING_ENABLED must be true before live routing can be considered.")
        if self.settings.require_human_approval and not order.human_approved:
            return ExecutionResult("PENDING_APPROVAL", None, "Human approval is required before paper execution.")
        if order.quantity <= 0:
            return ExecutionResult("BLOCKED", None, "Quantity must be positive.")

        submitted_at = datetime.now(timezone.utc)
        broker_order_id = f"PAPER-{int(submitted_at.timestamp())}"
        self.journal.log_executed_paper_trade(
            db,
            order.symbol,
            f"Executed paper {order.side} order for {order.quantity} shares at reference price {order.entry_price}.",
        )
        return ExecutionResult("EXECUTED_PAPER", broker_order_id, "Paper order executed.", submitted_at)
