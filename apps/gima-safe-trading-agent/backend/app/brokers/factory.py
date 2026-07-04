from __future__ import annotations

from app.brokers.client import BrokerClient
from app.brokers.mock import MockBrokerClient
from app.core.config import Settings


def create_broker_client(settings: Settings) -> BrokerClient:
    if settings.broker_backend != "mock":
        raise ValueError("Only the mock broker is enabled in this paper-trading milestone.")
    return MockBrokerClient()
