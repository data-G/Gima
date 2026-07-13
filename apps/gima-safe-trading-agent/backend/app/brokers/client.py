from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.trading import TradeOrder


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str
    status: str
    message: str


class BrokerClient(Protocol):
    def get_account_summary(self) -> dict:
        ...

    def get_positions(self) -> list[dict]:
        ...

    def get_market_data(self, symbol: str) -> dict:
        ...

    def place_paper_order(self, order: TradeOrder) -> BrokerOrderResult:
        ...

    def cancel_order(self, order_id: str) -> dict:
        ...

    def get_order_status(self, order_id: str) -> dict:
        ...
