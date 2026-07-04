from __future__ import annotations

import pandas as pd

from app.agents.types import SignalDecision


class StrategyAgent:
    """Moving-average, RSI, and volume-confirmed strategy agent."""

    def create_signal_from_ohlcv(self, symbol: str, ohlcv: pd.DataFrame) -> SignalDecision:
        if len(ohlcv) < 50:
            latest_close = float(ohlcv["close"].iloc[-1])
            return SignalDecision(
                symbol=symbol.upper(),
                action="WAIT",
                confidence=0.0,
                explanation="At least 50 bars are required for the 20/50 moving-average strategy.",
                entry_price=latest_close,
                stop_loss=None,
            )

        frame = ohlcv.copy()
        frame["sma20"] = frame["close"].rolling(20).mean()
        frame["sma50"] = frame["close"].rolling(50).mean()
        frame["rsi14"] = self._rsi(frame["close"])
        frame["volume20"] = frame["volume"].rolling(20).mean()

        latest = frame.iloc[-1]
        previous = frame.iloc[-2]
        price = float(latest["close"])
        sma20 = float(latest["sma20"])
        sma50 = float(latest["sma50"])
        rsi = float(latest["rsi14"])
        volume = float(latest["volume"])
        avg_volume = float(latest["volume20"])

        bullish_trend = sma20 > sma50 and float(previous["sma20"]) <= float(previous["sma50"])
        bearish_trend = sma20 < sma50 and float(previous["sma20"]) >= float(previous["sma50"])
        sustained_bullish = sma20 > sma50 and price > sma20
        sustained_bearish = sma20 < sma50 and price < sma20
        volume_confirmed = volume >= avg_volume * 1.05
        buy_rsi_ok = 45 <= rsi <= 72
        sell_rsi_ok = rsi <= 55

        confidence = 0.45
        explanation_parts = [
            f"SMA20={sma20:.2f}",
            f"SMA50={sma50:.2f}",
            f"RSI14={rsi:.1f}",
            f"volume={volume:.0f}",
            f"avgVolume20={avg_volume:.0f}",
        ]

        if (bullish_trend or sustained_bullish) and buy_rsi_ok and volume_confirmed:
            action = "BUY"
            confidence += 0.20 if bullish_trend else 0.14
            confidence += 0.12
            confidence += 0.08
            reason = "BUY: bullish 20/50 moving-average setup, RSI filter passed, and volume confirmed."
            stop_loss = round(price * 0.97, 2)
        elif (bearish_trend or sustained_bearish) and sell_rsi_ok and volume_confirmed:
            action = "SELL"
            confidence += 0.20 if bearish_trend else 0.14
            confidence += 0.10
            confidence += 0.08
            reason = "SELL: bearish 20/50 moving-average setup, RSI filter passed, and volume confirmed."
            stop_loss = round(price * 1.03, 2)
        else:
            action = "WAIT"
            confidence = 0.40
            reason = "WAIT: moving average, RSI, and volume confirmation are not aligned."
            stop_loss = None

        explanation = f"{reason} {'; '.join(explanation_parts)}."
        return SignalDecision(
            symbol=symbol.upper(),
            action=action,
            confidence=round(min(confidence, 0.92), 2),
            explanation=explanation,
            entry_price=price,
            stop_loss=stop_loss,
            indicators={
                "sma20": sma20,
                "sma50": sma50,
                "rsi14": rsi,
                "volume": volume,
                "volume20": avg_volume,
            },
        )

    def create_signal(self, snapshot: dict) -> dict:
        price = snapshot["price"]
        previous_close = snapshot["previous_close"]
        change = (price - previous_close) / previous_close

        if change > 0.012:
            decision = SignalDecision(snapshot["symbol"], "BUY", min(0.84, 0.62 + abs(change) * 4), "Positive short-term momentum with price above previous close.", price, round(price * 0.97, 2))
        elif change < -0.018:
            decision = SignalDecision(snapshot["symbol"], "SELL", min(0.78, 0.60 + abs(change) * 3), "Negative momentum detected; paper signal is defensive.", price, round(price * 1.03, 2))
        else:
            decision = SignalDecision(snapshot["symbol"], "WAIT", 0.55, "Price movement is not strong enough for a trade.", price, None)
        return self.to_dict(decision)

    def to_dict(self, decision: SignalDecision) -> dict:
        return {
            "symbol": decision.symbol,
            "action": decision.action,
            "confidence": round(decision.confidence, 2),
            "reason": decision.explanation,
            "entry_price": decision.entry_price,
            "stop_loss": decision.stop_loss or 0.0,
            "indicators": decision.indicators,
        }

    def _rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)
        avg_gain = gains.rolling(period).mean()
        avg_loss = losses.rolling(period).mean().replace(0, 0.000001)
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
