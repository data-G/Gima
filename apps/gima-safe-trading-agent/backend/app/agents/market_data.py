from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from random import Random

import pandas as pd

from app.core.config import Settings
from app.agents.types import MarketDataRejected


class MarketDataAgent:
    """Fetches and validates OHLCV market data for paper-trading decisions."""

    required_columns = ("timestamp", "open", "high", "low", "close", "volume")

    def __init__(self, settings: Settings, data_provider: Callable[[str, int], pd.DataFrame] | None = None):
        self.settings = settings
        self.data_provider = data_provider

    def fetch_ohlcv(self, symbol: str, lookback_days: int = 90) -> pd.DataFrame:
        if self.data_provider:
            raw = self.data_provider(symbol.upper(), lookback_days)
        else:
            raw = self._simulated_ohlcv(symbol, lookback_days)
        return self.validate_ohlcv(raw)

    def validate_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        missing_columns = [column for column in self.required_columns if column not in df.columns]
        if missing_columns:
            raise MarketDataRejected(f"Missing OHLCV columns: {', '.join(missing_columns)}")

        clean = df.loc[:, self.required_columns].copy()
        clean["timestamp"] = pd.to_datetime(clean["timestamp"], utc=True)
        clean = clean.sort_values("timestamp").reset_index(drop=True)

        if clean.empty:
            raise MarketDataRejected("No OHLCV data returned.")
        if clean.isna().any().any():
            raise MarketDataRejected("OHLCV data contains missing values.")
        if (clean[["open", "high", "low", "close"]] <= 0).any().any():
            raise MarketDataRejected("OHLCV price data must be positive.")
        if (clean["volume"] < 0).any():
            raise MarketDataRejected("OHLCV volume cannot be negative.")

        latest = clean["timestamp"].iloc[-1].to_pydatetime()
        age_seconds = (datetime.now(timezone.utc) - latest).total_seconds()
        if age_seconds > self.settings.stale_data_seconds:
            raise MarketDataRejected("OHLCV data is stale.")

        return clean

    def snapshot(self, symbol: str) -> dict:
        df = self.fetch_ohlcv(symbol)
        return self.snapshot_from_ohlcv(symbol, df)

    def snapshot_from_ohlcv(self, symbol: str, df: pd.DataFrame) -> dict:
        last = df.iloc[-1]
        previous = df.iloc[-2] if len(df) > 1 else last
        returns = df["close"].pct_change().dropna().tail(20)
        volatility = float(returns.std() or 0.0)
        return {
            "symbol": symbol.upper(),
            "price": float(last["close"]),
            "previous_close": float(previous["close"]),
            "volatility": volatility,
            "source": "ohlcv",
            "as_of": last["timestamp"].to_pydatetime(),
        }

    def _simulated_snapshot(self, symbol: str) -> dict:
        rng = Random(symbol.upper())
        previous_close = round(rng.uniform(40, 380), 2)
        drift = rng.uniform(-0.025, 0.025)
        price = round(previous_close * (1 + drift), 2)
        volatility = round(abs(drift) + rng.uniform(0.005, 0.035), 4)
        return {
            "symbol": symbol.upper(),
            "price": price,
            "previous_close": previous_close,
            "volatility": volatility,
            "source": "simulated",
            "as_of": datetime.now(timezone.utc),
        }

    def _simulated_ohlcv(self, symbol: str, lookback_days: int) -> pd.DataFrame:
        rng = Random(symbol.upper())
        now = datetime.now(timezone.utc)
        price = rng.uniform(70, 220)
        rows = []
        for days_ago in range(lookback_days - 1, -1, -1):
            timestamp = now - timedelta(days=days_ago)
            drift = rng.uniform(-0.012, 0.014)
            open_price = price
            close = max(1.0, open_price * (1 + drift))
            high = max(open_price, close) * (1 + rng.uniform(0.001, 0.014))
            low = min(open_price, close) * (1 - rng.uniform(0.001, 0.014))
            volume = rng.randint(800_000, 4_000_000)
            rows.append(
                {
                    "timestamp": timestamp,
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": volume,
                }
            )
            price = close
        return pd.DataFrame(rows)
