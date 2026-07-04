from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/gima_safe_trading_test.db")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("REAL_TRADING_ENABLED", "false")
os.environ.setdefault("REQUIRE_HUMAN_APPROVAL", "true")

from app.agents.market_data import MarketDataAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.strategy import StrategyAgent
from app.agents.types import MarketDataRejected, SignalDecision
from app.core.config import Settings
from app.db.session import Base, SessionLocal, engine
from app.models.trading import RiskSettings, TradeJournal


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def make_ohlcv(prices: list[float], volumes: list[float] | None = None, latest_age_seconds: int = 1) -> pd.DataFrame:
    latest = datetime.now(timezone.utc) - timedelta(seconds=latest_age_seconds)
    volumes = volumes or [1_000_000.0 for _ in prices]
    return pd.DataFrame(
        [
            {
                "timestamp": latest - timedelta(minutes=len(prices) - index - 1),
                "open": price * 0.995,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": volumes[index],
            }
            for index, price in enumerate(prices)
        ]
    )


def settings(**overrides) -> Settings:
    defaults = {
        "database_url": "sqlite:////tmp/gima_safe_trading_test.db",
        "stale_data_seconds": 300,
        "account_equity": 100_000,
        "max_risk_per_trade": 0.005,
        "max_daily_loss": 0.02,
        "max_weekly_loss": 0.05,
        "max_position_concentration": 0.10,
        "max_volatility": 0.06,
        "min_confidence": 0.60,
        "trading_mode": "paper",
        "real_trading_enabled": False,
        "require_human_approval": True,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_stale_market_data_rejection() -> None:
    stale = make_ohlcv([100.0 for _ in range(60)], latest_age_seconds=600)
    agent = MarketDataAgent(settings(stale_data_seconds=60), data_provider=lambda _symbol, _days: stale)

    try:
        agent.fetch_ohlcv("SPY")
    except MarketDataRejected as exc:
        assert "stale" in str(exc).lower()
    else:
        raise AssertionError("Expected stale market data to be rejected.")


def test_missing_values_are_detected() -> None:
    data = make_ohlcv([100.0 for _ in range(60)])
    data.loc[3, "close"] = None
    agent = MarketDataAgent(settings(), data_provider=lambda _symbol, _days: data)

    try:
        agent.fetch_ohlcv("SPY")
    except MarketDataRejected as exc:
        assert "missing values" in str(exc)
    else:
        raise AssertionError("Expected missing OHLCV values to be rejected.")


def test_high_risk_trade_rejection() -> None:
    db = SessionLocal()
    try:
        signal = SignalDecision("SPY", "BUY", 0.8, "test", 1_000.0, 3_000.0)
        risk = RiskManagerAgent(settings()).evaluate_signal(db, signal, datetime.now(timezone.utc), volatility=0.01)
        assert risk.status == "BLOCKED"
        assert "Position size is zero" in risk.reason
    finally:
        db.close()


def test_daily_loss_limit_rejection() -> None:
    db = SessionLocal()
    try:
        db.add(TradeJournal(symbol="SPY", notes="loss", pnl=-2_500.0))
        db.commit()
        signal = SignalDecision("SPY", "BUY", 0.8, "test", 100.0, 97.0)
        risk = RiskManagerAgent(settings()).evaluate_signal(db, signal, datetime.now(timezone.utc), volatility=0.01)
        assert risk.status == "BLOCKED"
        assert "Daily loss limit" in risk.reason
    finally:
        db.close()


def test_missing_stop_loss_rejection() -> None:
    db = SessionLocal()
    try:
        signal = SignalDecision("SPY", "BUY", 0.8, "test", 100.0, None)
        risk = RiskManagerAgent(settings()).evaluate_signal(db, signal, datetime.now(timezone.utc), volatility=0.01)
        assert risk.status == "BLOCKED"
        assert "stop-loss" in risk.reason
    finally:
        db.close()


def test_kill_switch_blocks_all_trades() -> None:
    db = SessionLocal()
    try:
        db.add(RiskSettings(user_id=1, kill_switch_enabled=True))
        db.commit()
        signal = SignalDecision("SPY", "BUY", 0.8, "test", 100.0, 97.0)
        risk = RiskManagerAgent(settings()).evaluate_signal(db, signal, datetime.now(timezone.utc), volatility=0.01)
        assert risk.status == "BLOCKED"
        assert "Kill switch is active" in risk.reason
    finally:
        db.close()


def test_user_risk_settings_tighten_position_size() -> None:
    db = SessionLocal()
    try:
        db.add(RiskSettings(user_id=1, max_risk_per_trade_percent=0.1, max_position_concentration_percent=1.0))
        db.commit()
        signal = SignalDecision("SPY", "BUY", 0.8, "test", 100.0, 99.0)
        risk = RiskManagerAgent(settings()).evaluate_signal(db, signal, datetime.now(timezone.utc), volatility=0.01, user_id=1)
        assert risk.status == "APPROVED"
        assert risk.quantity == 10
        assert risk.metrics["max_risk_per_trade"] == 0.001
        assert risk.metrics["max_position_concentration"] == 0.01
    finally:
        db.close()


def test_buy_sell_wait_signal_generation() -> None:
    strategy = StrategyAgent()
    volumes = [1_000_000.0 for _ in range(59)] + [1_300_000.0]

    buy_prices = [100 + (index * 0.03) for index in range(40)] + [101, 100.7, 101.4, 101.1, 101.9, 101.6, 102.3, 102.0, 102.7, 102.4, 103.0, 102.8, 103.5, 103.2, 103.9, 103.6, 104.3, 104.0, 104.8, 104.5]
    sell_prices = [110 - (index * 0.03) for index in range(40)] + [109, 109.2, 108.6, 108.9, 108.1, 108.4, 107.8, 108.0, 107.3, 107.6, 106.9, 107.1, 106.4, 106.7, 106.0, 106.2, 105.5, 105.8, 105.0, 105.2]
    wait_prices = [100.0 + ((index % 2) * 0.05) for index in range(60)]

    buy = strategy.create_signal_from_ohlcv("BUY", make_ohlcv(buy_prices, volumes))
    sell = strategy.create_signal_from_ohlcv("SELL", make_ohlcv(sell_prices, volumes))
    wait = strategy.create_signal_from_ohlcv("WAIT", make_ohlcv(wait_prices, volumes))

    assert buy.action == "BUY"
    assert buy.confidence >= 0.60
    assert sell.action == "SELL"
    assert sell.confidence >= 0.60
    assert wait.action == "WAIT"
