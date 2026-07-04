from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gima_safe_trading_test.db")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("REAL_TRADING_ENABLED", "false")
os.environ.setdefault("REQUIRE_HUMAN_APPROVAL", "true")
os.environ.setdefault("BROKER_BACKEND", "mock")

from app.brokers.mock import MockBrokerClient
from app.core.config import Settings
from app.db.session import Base, SessionLocal, engine
from app.models.trading import MarketSnapshot, OrderStatus, RiskCheck, RiskSettings, RiskStatus, Signal, TradeOrder, User
from app.services.paper_trading import PaperTradingEngine


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def settings(**overrides) -> Settings:
    defaults = {
        "database_url": "sqlite:////tmp/gima_safe_trading_test.db",
        "trading_mode": "paper",
        "live_trading_enabled": False,
        "real_trading_enabled": False,
        "broker_backend": "mock",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def make_order(
    *,
    order_status: str = OrderStatus.approved.value,
    risk_status: str = RiskStatus.approved.value,
    kill_switch: bool = False,
    user_live_enabled: bool = False,
    is_live_trade: bool = False,
) -> int:
    db = SessionLocal()
    try:
        user = User(email="trader@example.com", name="Trader", role="trader")
        db.add(user)
        db.commit()
        db.refresh(user)

        db.add(RiskSettings(user_id=user.id, kill_switch_enabled=kill_switch, live_trading_enabled=user_live_enabled))
        signal = Signal(
            symbol="SPY",
            signal_type="BUY",
            confidence=0.8,
            strategy_name="test",
            explanation="test signal",
            raw_features_json={},
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)

        db.add(
            RiskCheck(
                signal_id=signal.id,
                status=risk_status,
                reason="test risk",
                account_equity=100_000,
                proposed_position_size=10,
                risk_amount=100,
                stop_loss=95,
                max_loss_percent=0.5,
            )
        )
        db.add(
            MarketSnapshot(
                symbol="SPY",
                timeframe="1d",
                open=100,
                high=101,
                low=99,
                close=100,
                volume=1_000_000,
                timestamp=datetime.now(timezone.utc),
            )
        )
        order = TradeOrder(
            user_id=user.id,
            signal_id=signal.id,
            symbol="SPY",
            side="BUY",
            quantity=10,
            order_type="MARKET",
            entry_price=100,
            stop_loss=95,
            status=order_status,
            is_live_trade=is_live_trade,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order.id
    finally:
        db.close()


def execute_order(order_id: int, engine_settings: Settings | None = None) -> TradeOrder:
    db = SessionLocal()
    try:
        order = db.get(TradeOrder, order_id)
        assert order is not None
        return PaperTradingEngine(engine_settings or settings(), broker=MockBrokerClient()).submit_after_approval(db, order)
    finally:
        db.close()


def test_live_orders_are_blocked_by_default() -> None:
    order_id = make_order(is_live_trade=True)
    with pytest.raises(ValueError, match="LIVE_TRADING_ENABLED is false"):
        execute_order(order_id)


def test_kill_switch_blocks_orders() -> None:
    order_id = make_order(kill_switch=True)
    with pytest.raises(ValueError, match="Kill switch is active"):
        execute_order(order_id)


def test_unapproved_orders_cannot_execute() -> None:
    order_id = make_order(order_status=OrderStatus.pending_approval.value)
    with pytest.raises(ValueError, match="manually approved"):
        execute_order(order_id)


def test_blocked_risk_checks_cannot_execute() -> None:
    order_id = make_order(risk_status=RiskStatus.blocked.value)
    with pytest.raises(ValueError, match="risk check must be APPROVED"):
        execute_order(order_id)


def test_paper_order_can_execute_after_approval() -> None:
    order_id = make_order()
    order = execute_order(order_id)
    assert order.status == OrderStatus.paper_executed.value
    assert order.broker_order_id == f"MOCK-PAPER-{order.id}"
    assert order.is_live_trade is False


def test_duplicate_paper_execution_is_blocked() -> None:
    order_id = make_order()
    execute_order(order_id)
    with pytest.raises(ValueError, match="already been executed"):
        execute_order(order_id)


def test_stale_market_snapshot_blocks_execution() -> None:
    order_id = make_order()
    db = SessionLocal()
    try:
        snapshot = db.query(MarketSnapshot).filter(MarketSnapshot.symbol == "SPY").first()
        assert snapshot is not None
        snapshot.timestamp = datetime.now(timezone.utc) - timedelta(seconds=600)
        db.commit()
    finally:
        db.close()
    with pytest.raises(ValueError, match="stale"):
        execute_order(order_id, settings(stale_data_seconds=60))
