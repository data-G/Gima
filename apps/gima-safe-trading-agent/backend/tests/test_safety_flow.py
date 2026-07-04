import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gima_safe_trading_test.db")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("REAL_TRADING_ENABLED", "false")
os.environ.setdefault("REQUIRE_HUMAN_APPROVAL", "true")

from fastapi.testclient import TestClient
import pandas as pd

from app.db.session import Base, engine
from app.main import app, create_tables


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    create_tables()


def buy_ohlcv() -> pd.DataFrame:
    latest = datetime.now(timezone.utc)
    prices = [100 + (index * 0.03) for index in range(40)] + [101, 100.7, 101.4, 101.1, 101.9, 101.6, 102.3, 102.0, 102.7, 102.4, 103.0, 102.8, 103.5, 103.2, 103.9, 103.6, 104.3, 104.0, 104.8, 104.5]
    return pd.DataFrame(
        [
            {
                "timestamp": latest - timedelta(minutes=len(prices) - index - 1),
                "open": price * 0.995,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": 1_300_000 if index == len(prices) - 1 else 1_000_000,
            }
            for index, price in enumerate(prices)
        ]
    )


def test_signal_does_not_create_order_until_user_requests_paper_trade(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.market_data.MarketDataAgent.fetch_ohlcv", lambda self, symbol, lookback_days=90: buy_ohlcv())
    watchlist_response = client.post("/api/watchlist", json={"symbol": "SPY", "asset_type": "etf"})
    assert watchlist_response.status_code == 200

    signal_response = client.post("/api/signals/run", json={"symbol": "SPY"})
    assert signal_response.status_code == 200
    decision = signal_response.json()
    assert decision["signal_type"] == "BUY"
    assert decision["confidence"] >= 0.6

    orders = client.get("/api/orders").json()
    assert orders == []

    risk = client.get(f"/api/risk-checks?signal_id={decision['id']}").json()[0]
    order_response = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "signal_id": decision["id"],
            "symbol": decision["symbol"],
            "side": "BUY",
            "quantity": risk["proposed_position_size"],
            "entry_price": 104.5,
            "stop_loss": risk["stop_loss"],
        },
    )
    assert order_response.status_code == 200
    assert order_response.json()["status"] == "PENDING_APPROVAL"


def test_kill_switch_blocks_new_trade_decisions() -> None:
    kill_response = client.post("/api/safety/kill-switch", json={"active": True, "reason": "test stop"})
    assert kill_response.status_code == 200

    signal_response = client.post("/api/signals/run", json={"symbol": "AAPL"})
    assert signal_response.status_code == 200
    risk_checks = client.get("/api/risk-checks").json()
    assert risk_checks[0]["status"] == "BLOCKED"
    assert "Kill switch is active" in risk_checks[0]["reason"]


def test_blocked_risk_check_prevents_order_creation() -> None:
    client.post("/api/safety/kill-switch", json={"active": True, "reason": "test stop"})
    signal_response = client.post("/api/signals", json={"symbol": "SPY", "signal_type": "BUY", "confidence": 0.8, "strategy_name": "test", "explanation": "test", "raw_features_json": {}})
    assert signal_response.status_code == 200
    signal = signal_response.json()
    risk_response = client.post(
        "/api/risk-checks",
        json={
            "signal_id": signal["id"],
            "status": "BLOCKED",
            "reason": "test blocked",
            "account_equity": 100000,
            "proposed_position_size": 0,
            "risk_amount": 0,
            "stop_loss": 95,
            "max_loss_percent": 0.5,
        },
    )
    assert risk_response.status_code == 200
    order_response = client.post(
        "/api/orders",
        json={"user_id": 1, "signal_id": signal["id"], "symbol": "SPY", "side": "BUY", "quantity": 1, "entry_price": 100, "stop_loss": 95},
    )
    assert order_response.status_code == 400
    assert "latest risk check is APPROVED" in order_response.text


def test_manual_approved_risk_check_is_rejected() -> None:
    signal_response = client.post("/api/signals", json={"symbol": "SPY", "signal_type": "BUY", "confidence": 0.8, "strategy_name": "test", "explanation": "test", "raw_features_json": {}})
    assert signal_response.status_code == 200
    signal = signal_response.json()
    risk_response = client.post(
        "/api/risk-checks",
        json={
            "signal_id": signal["id"],
            "status": "APPROVED",
            "reason": "manual bypass attempt",
            "account_equity": 100000,
            "proposed_position_size": 10,
            "risk_amount": 100,
            "stop_loss": 95,
            "max_loss_percent": 0.5,
        },
    )
    assert risk_response.status_code == 403
    assert "server-side risk agent" in risk_response.text


def test_approval_executes_after_immediate_risk_recheck_and_logs(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.market_data.MarketDataAgent.fetch_ohlcv", lambda self, symbol, lookback_days=90: buy_ohlcv())
    signal = client.post("/api/signals/run", json={"symbol": "SPY"}).json()
    risk = client.get(f"/api/risk-checks?signal_id={signal['id']}").json()[0]
    order = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "signal_id": signal["id"],
            "symbol": signal["symbol"],
            "side": "BUY",
            "quantity": min(1, risk["proposed_position_size"]),
            "entry_price": 104.5,
            "stop_loss": risk["stop_loss"],
        },
    ).json()

    approved = client.post(f"/api/orders/{order['id']}/approval", json={"approved": True, "note": "manual test approval"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "PAPER_EXECUTED"

    audit_logs = client.get("/api/audit-logs?entity_type=trade_order").json()
    actions = {entry["action"] for entry in audit_logs}
    assert "ORDER_CREATED_PENDING_APPROVAL" in actions
    assert "ORDER_APPROVED" in actions
    assert "ORDER_PAPER_EXECUTED" in actions

    journal = client.get("/api/journal").json()
    notes = " ".join(entry["notes"] for entry in journal)
    assert "Pending paper order" in notes
    assert "paper_trade_executed" in notes


def test_approval_rechecks_risk_and_blocks_if_kill_switch_changes(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.market_data.MarketDataAgent.fetch_ohlcv", lambda self, symbol, lookback_days=90: buy_ohlcv())
    signal = client.post("/api/signals/run", json={"symbol": "SPY"}).json()
    risk = client.get(f"/api/risk-checks?signal_id={signal['id']}").json()[0]
    order = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "signal_id": signal["id"],
            "symbol": signal["symbol"],
            "side": "BUY",
            "quantity": min(1, risk["proposed_position_size"]),
            "entry_price": 104.5,
            "stop_loss": risk["stop_loss"],
        },
    ).json()
    client.post("/api/safety/kill-switch", json={"active": True, "reason": "changed before approval"})

    approval = client.post(f"/api/orders/{order['id']}/approval", json={"approved": True, "note": "should block"})
    assert approval.status_code == 400
    assert "Kill switch is active" in approval.text

    stored_order = client.get("/api/orders").json()[0]
    assert stored_order["status"] == "PENDING_APPROVAL"
    audit_logs = client.get("/api/audit-logs?entity_type=trade_order").json()
    assert any(entry["action"] == "ORDER_APPROVAL_BLOCKED_BY_RISK" for entry in audit_logs)


def test_duplicate_order_for_same_signal_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.market_data.MarketDataAgent.fetch_ohlcv", lambda self, symbol, lookback_days=90: buy_ohlcv())
    signal = client.post("/api/signals/run", json={"symbol": "SPY"}).json()
    risk = client.get(f"/api/risk-checks?signal_id={signal['id']}").json()[0]
    payload = {
        "user_id": 1,
        "signal_id": signal["id"],
        "symbol": signal["symbol"],
        "side": "BUY",
        "quantity": min(1, risk["proposed_position_size"]),
        "entry_price": 104.5,
        "stop_loss": risk["stop_loss"],
    }
    first = client.post("/api/orders", json=payload)
    second = client.post("/api/orders", json=payload)
    assert first.status_code == 200
    assert second.status_code == 409


def test_risk_settings_live_flag_is_blocked() -> None:
    response = client.put("/api/risk-settings/1", json={"live_trading_enabled": True})
    assert response.status_code == 403
    assert "cannot be enabled in v1" in response.text


def test_order_update_cannot_mutate_execution_fields(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.market_data.MarketDataAgent.fetch_ohlcv", lambda self, symbol, lookback_days=90: buy_ohlcv())
    signal = client.post("/api/signals/run", json={"symbol": "SPY"}).json()
    risk = client.get(f"/api/risk-checks?signal_id={signal['id']}").json()[0]
    order = client.post(
        "/api/orders",
        json={
            "user_id": 1,
            "signal_id": signal["id"],
            "symbol": signal["symbol"],
            "side": "BUY",
            "quantity": min(1, risk["proposed_position_size"]),
            "entry_price": 104.5,
            "stop_loss": risk["stop_loss"],
        },
    ).json()
    response = client.patch(f"/api/orders/{order['id']}", json={"quantity": 999})
    assert response.status_code == 403
    assert "immutable" in response.text
