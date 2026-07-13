from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gima_safe_trading_test.db")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("REAL_TRADING_ENABLED", "false")
os.environ.setdefault("REQUIRE_HUMAN_APPROVAL", "true")

from app.core.config import Settings, get_settings
from app.db.session import Base, engine
from app.main import app, create_tables


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    create_tables()
    get_settings.cache_clear()
    app.dependency_overrides.clear()


def test_mock_whatsapp_notification_can_be_sent_without_cloud_credentials() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite:////tmp/gima_safe_trading_test.db",
        notifications_enabled=True,
        whatsapp_mode="mock",
        broker_backend="mock",
    )
    response = client.post("/api/notifications/test", json={"message": "Paper order review test."})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock_whatsapp"
    assert body["status"] == "SENT"


def test_whatsapp_webhook_logs_inbound_payload_without_trade_action() -> None:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [{"text": {"body": "approve order"}}]}}]}],
    }
    response = client.post("/api/webhooks/whatsapp", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "received", "trade_action": "ignored"}
    audit_logs = client.get("/api/audit-logs?entity_type=notification").json()
    assert any(entry["action"] == "WHATSAPP_WEBHOOK_RECEIVED_NO_TRADE_ACTION" for entry in audit_logs)


def test_whatsapp_cloud_mode_requires_credentials_when_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite:////tmp/gima_safe_trading_test.db",
            notifications_enabled=True,
            whatsapp_mode="cloud",
            broker_backend="mock",
        )


def test_whatsapp_webhook_verification_requires_matching_token() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="sqlite:////tmp/gima_safe_trading_test.db",
        whatsapp_webhook_verify_token="verify-me",
        broker_backend="mock",
    )
    ok = client.get("/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=12345")
    assert ok.status_code == 200
    assert ok.text == "12345"

    blocked = client.get("/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=12345")
    assert blocked.status_code == 403
