from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gima_safe_trading_test.db")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TRADING_MODE", "paper")

from app.agents.backtesting import BacktestingEngine
from app.db.session import Base, engine
from app.main import app, create_tables
from app.schemas.trading import BacktestRunRequest


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    create_tables()


def make_ohlcv(days: int = 180, drop: bool = False) -> pd.DataFrame:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = []
    price = 100.0
    for index in range(days):
        if drop and 55 < index < 80:
            price *= 1.02
        elif drop and index > 95:
            price *= 0.97
        else:
            price *= 1.004 if drop else (1.003 if index % 11 else 0.99)
        rows.append(
            {
                "timestamp": start + timedelta(days=index),
                "open": price * 0.995,
                "high": price * 1.015,
                "low": price * 0.985,
                "close": price,
                "volume": 1_000_000 + index,
            }
        )
    return pd.DataFrame(rows)


def request_for(strategy: str = "breakout", max_drawdown: float = 20.0) -> BacktestRunRequest:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=160)
    return BacktestRunRequest(
        symbol="SPY",
        start_date=start,
        end_date=end,
        strategy_name=strategy,
        initial_capital=100_000,
        max_allowed_drawdown_percent=max_drawdown,
    )


def test_backtest_engine_calculates_metrics() -> None:
    result = BacktestingEngine().run(make_ohlcv(), request_for("breakout"))
    assert result.symbol == "SPY"
    assert result.warning
    assert result.number_of_trades >= 0
    assert isinstance(result.equity_curve_json, list)
    assert "past performance does not guarantee future results" in result.warning.lower()


def test_backtest_rejects_excessive_drawdown() -> None:
    result = BacktestingEngine().run(make_ohlcv(drop=True), request_for("breakout", max_drawdown=0.0))
    assert result.status == "REJECTED"
    assert result.rejection_reason is not None


def test_backtest_api_persists_result(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.market_data.MarketDataAgent.fetch_ohlcv", lambda self, symbol, lookback_days=120: make_ohlcv())
    payload = request_for("moving_average_crossover").model_dump(mode="json")
    response = client.post("/api/backtests/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert body["strategy_name"] == "moving_average_crossover"

    list_response = client.get("/api/backtests")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(f"/api/backtests/{body['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["warning"]
