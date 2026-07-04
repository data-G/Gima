from __future__ import annotations

from datetime import datetime, timezone

from app.brokers.client import BrokerOrderResult
from app.models.trading import TradeOrder


class MockBrokerClient:
    """Safe local broker: deterministic data and paper-only fake order IDs."""

    def __init__(self) -> None:
        self.orders: dict[str, dict] = {}

    def get_account_summary(self) -> dict:
        return {
            "account_type": "MOCK_PAPER",
            "net_liquidation": 100_000.0,
            "available_funds": 100_000.0,
            "currency": "USD",
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def get_positions(self) -> list[dict]:
        return []

    def get_market_data(self, symbol: str) -> dict:
        return {
            "symbol": symbol.upper(),
            "bid": 100.0,
            "ask": 100.05,
            "last": 100.02,
            "source": "mock",
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def place_paper_order(self, order: TradeOrder) -> BrokerOrderResult:
        broker_order_id = f"MOCK-PAPER-{order.id}"
        self.orders[broker_order_id] = {
            "order_id": broker_order_id,
            "status": "Filled",
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "is_live_trade": False,
        }
        return BrokerOrderResult(broker_order_id=broker_order_id, status="Filled", message="Mock paper order filled.")

    def cancel_order(self, order_id: str) -> dict:
        order = self.orders.setdefault(order_id, {"order_id": order_id})
        order["status"] = "Cancelled"
        return order

    def get_order_status(self, order_id: str) -> dict:
        return self.orders.get(order_id, {"order_id": order_id, "status": "Unknown"})
