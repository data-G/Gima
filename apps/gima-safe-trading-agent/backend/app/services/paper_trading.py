from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.journal import JournalAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.types import SignalDecision
from app.brokers.client import BrokerClient
from app.brokers.factory import create_broker_client
from app.core.config import Settings
from app.models.trading import MarketSnapshot, OrderStatus, RiskCheck, RiskSettings, RiskStatus, TradeOrder
from app.schemas.trading import RiskCheckCreate
from app.repositories.trading import RiskCheckRepository


class PaperTradingEngine:
    def __init__(self, settings: Settings, broker: BrokerClient | None = None):
        self.settings = settings
        self.broker = broker or create_broker_client(settings)
        self.journal = JournalAgent()

    def submit_after_approval(self, db: Session, order: TradeOrder) -> TradeOrder:
        self._assert_can_execute(db, order)
        result = self.broker.place_paper_order(order)
        order.status = OrderStatus.paper_executed.value
        order.broker_order_id = result.broker_order_id
        order.updated_at = datetime.now(timezone.utc)
        self.journal.log_executed_paper_trade(db, order.symbol, f"{result.message} Submitted {order.side} order for {order.quantity} shares.")
        db.commit()
        db.refresh(order)
        return order

    def recheck_risk_before_execution(self, db: Session, order: TradeOrder) -> RiskCheck:
        signal = order.signal
        if signal is None:
            raise ValueError("Order signal not found.")
        latest_snapshot = (
            db.query(MarketSnapshot)
            .filter(MarketSnapshot.symbol == order.symbol.upper())
            .order_by(MarketSnapshot.timestamp.desc())
            .first()
        )
        if latest_snapshot is None:
            return RiskCheckRepository().create(
                db,
                RiskCheckCreate(
                    signal_id=order.signal_id,
                    status=RiskStatus.blocked.value,
                    reason="Immediate pre-execution risk check: No market snapshot exists for this symbol.",
                    account_equity=self.settings.account_equity,
                    proposed_position_size=0,
                    risk_amount=0.0,
                    stop_loss=order.stop_loss,
                    max_loss_percent=self.settings.max_risk_per_trade * 100,
                ),
            )
        snapshot_timestamp = latest_snapshot.timestamp
        if snapshot_timestamp.tzinfo is None:
            snapshot_timestamp = snapshot_timestamp.replace(tzinfo=timezone.utc)
        market_age_seconds = (datetime.now(timezone.utc) - snapshot_timestamp).total_seconds()
        if market_age_seconds > self.settings.stale_data_seconds:
            return RiskCheckRepository().create(
                db,
                RiskCheckCreate(
                    signal_id=order.signal_id,
                    status=RiskStatus.blocked.value,
                    reason=f"Immediate pre-execution risk check: Market data is stale ({market_age_seconds:.0f}s old).",
                    account_equity=self.settings.account_equity,
                    proposed_position_size=0,
                    risk_amount=0.0,
                    stop_loss=order.stop_loss,
                    max_loss_percent=self.settings.max_risk_per_trade * 100,
                ),
            )

        risk_decision = RiskManagerAgent(self.settings).evaluate_signal(
            db,
            SignalDecision(
                symbol=order.symbol,
                action=order.side,
                confidence=signal.confidence,
                explanation=signal.explanation,
                entry_price=order.entry_price,
                stop_loss=order.stop_loss,
                indicators=signal.raw_features_json or {},
            ),
            snapshot_timestamp,
            volatility=abs(latest_snapshot.close - latest_snapshot.open) / latest_snapshot.open,
            user_id=order.user_id,
        )
        order_risk_amount = order.quantity * abs(order.entry_price - order.stop_loss)
        max_risk_amount = self.settings.account_equity * self.settings.max_risk_per_trade
        if order_risk_amount > max_risk_amount:
            risk_decision = risk_decision.__class__(
                status="BLOCKED",
                approved=False,
                reason=f"Requested order risk {order_risk_amount:.2f} exceeds max risk amount {max_risk_amount:.2f}.",
                quantity=0,
                metrics={**risk_decision.metrics, "risk_amount": order_risk_amount, "max_risk_amount": max_risk_amount},
            )
        return RiskCheckRepository().create(
            db,
            RiskCheckCreate(
                signal_id=order.signal_id,
                status=risk_decision.status,
                reason=f"Immediate pre-execution risk check: {risk_decision.reason}",
                account_equity=risk_decision.metrics.get("account_equity", self.settings.account_equity),
                proposed_position_size=order.quantity if risk_decision.approved else 0,
                risk_amount=order_risk_amount,
                stop_loss=order.stop_loss,
                max_loss_percent=risk_decision.metrics.get("max_risk_per_trade", self.settings.max_risk_per_trade) * 100,
            ),
        )

    def _assert_can_execute(self, db: Session, order: TradeOrder) -> None:
        if order.status == OrderStatus.paper_executed.value or order.broker_order_id:
            raise ValueError("Order has already been executed. Duplicate execution blocked.")

        risk_settings = db.query(RiskSettings).filter(RiskSettings.user_id == order.user_id).first()
        if risk_settings and risk_settings.kill_switch_enabled:
            raise ValueError("Kill switch is active. Order execution blocked.")

        if order.status != OrderStatus.approved.value:
            raise ValueError("Order must be manually approved before execution.")

        risk_check = (
            db.query(RiskCheck)
            .filter(RiskCheck.signal_id == order.signal_id)
            .order_by(RiskCheck.created_at.desc())
            .first()
        )
        if not risk_check or risk_check.status != RiskStatus.approved.value:
            raise ValueError("Latest risk check must be APPROVED before execution.")

        latest_snapshot = (
            db.query(MarketSnapshot)
            .filter(MarketSnapshot.symbol == order.symbol.upper())
            .order_by(MarketSnapshot.timestamp.desc())
            .first()
        )
        if latest_snapshot is None:
            raise ValueError("Fresh market snapshot is required before execution.")
        snapshot_timestamp = latest_snapshot.timestamp
        if snapshot_timestamp.tzinfo is None:
            snapshot_timestamp = snapshot_timestamp.replace(tzinfo=timezone.utc)
        market_age_seconds = (datetime.now(timezone.utc) - snapshot_timestamp).total_seconds()
        if market_age_seconds > self.settings.stale_data_seconds:
            raise ValueError("Market data is stale. Order execution blocked.")

        if order.is_live_trade:
            env_allows_live = self.settings.is_live_trading_allowed or self.settings.live_trading_enabled
            user_allows_live = bool(risk_settings and risk_settings.live_trading_enabled)
            if not env_allows_live:
                raise ValueError("LIVE_TRADING_ENABLED is false. Live order blocked.")
            if not user_allows_live:
                raise ValueError("User risk_settings.live_trading_enabled is false. Live order blocked.")
            raise ValueError("Live broker routing is not implemented in v1. Paper orders only.")

        if self.settings.trading_mode != "paper":
            raise ValueError("Trading mode must be paper for v1 paper execution.")

        if order.quantity <= 0:
            raise ValueError("Quantity must be positive.")
