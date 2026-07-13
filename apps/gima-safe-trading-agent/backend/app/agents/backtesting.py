from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt

import pandas as pd

from app.schemas.trading import BacktestResultCreate, BacktestRunRequest


BACKTEST_WARNING = "Backtests are historical simulations. Past performance does not guarantee future results."


@dataclass
class OpenPosition:
    entry_time: datetime
    entry_price: float
    quantity: int
    stop_loss: float


class BacktestingEngine:
    """OHLCV backtesting engine with long-only strategies and explicit assumptions."""

    def run(self, ohlcv: pd.DataFrame, request: BacktestRunRequest) -> BacktestResultCreate:
        data = self._prepare_data(ohlcv, request)
        if len(data) < 30:
            raise ValueError("At least 30 OHLCV bars are required for backtesting.")

        cash = request.initial_capital
        equity = request.initial_capital
        peak_equity = request.initial_capital
        max_drawdown = 0.0
        position: OpenPosition | None = None
        equity_curve: list[dict] = []
        trades: list[dict] = []
        daily_returns: list[float] = []
        previous_equity = equity

        for index in range(1, len(data)):
            row = data.iloc[index]
            timestamp = row["timestamp"].to_pydatetime()
            close = float(row["close"])
            low = float(row["low"])
            signal = self._strategy_signal(data, index, request.strategy_name)

            if position:
                stop_hit = low <= position.stop_loss
                exit_signal = signal == "SELL"
                if stop_hit or exit_signal:
                    exit_price = position.stop_loss if stop_hit else close
                    exit_price = self._apply_slippage(exit_price, request.slippage_percent, "SELL")
                    trade = self._close_position(position, timestamp, exit_price, request.fees_percent, "STOP_LOSS" if stop_hit else "SIGNAL_EXIT")
                    cash += position.quantity * exit_price - self._fee(position.quantity * exit_price, request.fees_percent)
                    trades.append(trade)
                    position = None

            if not position and signal == "BUY":
                entry_price = self._apply_slippage(close, request.slippage_percent, "BUY")
                capital_to_deploy = cash * (request.position_size_percent / 100)
                quantity = int(capital_to_deploy // entry_price)
                if quantity > 0:
                    cost = quantity * entry_price
                    cash -= cost + self._fee(cost, request.fees_percent)
                    position = OpenPosition(
                        entry_time=timestamp,
                        entry_price=entry_price,
                        quantity=quantity,
                        stop_loss=entry_price * (1 - request.stop_loss_percent / 100),
                    )

            position_value = position.quantity * close if position else 0.0
            equity = cash + position_value
            daily_return = (equity - previous_equity) / previous_equity if previous_equity else 0.0
            daily_returns.append(daily_return)
            previous_equity = equity
            peak_equity = max(peak_equity, equity)
            drawdown = ((equity - peak_equity) / peak_equity) * 100 if peak_equity else 0.0
            max_drawdown = min(max_drawdown, drawdown)
            equity_curve.append({"timestamp": timestamp.isoformat(), "equity": round(equity, 2), "drawdown_percent": round(drawdown, 4)})

        if position:
            last = data.iloc[-1]
            exit_price = self._apply_slippage(float(last["close"]), request.slippage_percent, "SELL")
            timestamp = last["timestamp"].to_pydatetime()
            trade = self._close_position(position, timestamp, exit_price, request.fees_percent, "END_OF_TEST")
            cash += position.quantity * exit_price - self._fee(position.quantity * exit_price, request.fees_percent)
            trades.append(trade)
            equity = cash
            equity_curve.append({"timestamp": timestamp.isoformat(), "equity": round(equity, 2), "drawdown_percent": round(max_drawdown, 4)})

        metrics = self._metrics(request.initial_capital, equity, max_drawdown, trades, daily_returns)
        status = "REJECTED" if abs(metrics["max_drawdown_percent"]) > request.max_allowed_drawdown_percent else "ACCEPTED"
        rejection_reason = None
        if status == "REJECTED":
            rejection_reason = f"Max drawdown {abs(metrics['max_drawdown_percent']):.2f}% exceeds allowed limit {request.max_allowed_drawdown_percent:.2f}%."

        return BacktestResultCreate(
            symbol=request.symbol.upper(),
            strategy_name=request.strategy_name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            final_equity=round(equity, 2),
            total_return_percent=metrics["total_return_percent"],
            max_drawdown_percent=metrics["max_drawdown_percent"],
            win_rate=metrics["win_rate"],
            loss_rate=metrics["loss_rate"],
            profit_factor=metrics["profit_factor"],
            sharpe_ratio=metrics["sharpe_ratio"],
            number_of_trades=len(trades),
            average_win=metrics["average_win"],
            average_loss=metrics["average_loss"],
            fees_percent=request.fees_percent,
            slippage_percent=request.slippage_percent,
            stop_loss_percent=request.stop_loss_percent,
            position_size_percent=request.position_size_percent,
            max_allowed_drawdown_percent=request.max_allowed_drawdown_percent,
            status=status,
            rejection_reason=rejection_reason,
            warning=BACKTEST_WARNING,
            equity_curve_json=equity_curve,
            trades=trades,
        )

    def _prepare_data(self, ohlcv: pd.DataFrame, request: BacktestRunRequest) -> pd.DataFrame:
        data = ohlcv.copy()
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        start = pd.Timestamp(request.start_date).tz_convert("UTC") if pd.Timestamp(request.start_date).tzinfo else pd.Timestamp(request.start_date, tz="UTC")
        end = pd.Timestamp(request.end_date).tz_convert("UTC") if pd.Timestamp(request.end_date).tzinfo else pd.Timestamp(request.end_date, tz="UTC")
        data = data[(data["timestamp"] >= start) & (data["timestamp"] <= end)].sort_values("timestamp").reset_index(drop=True)
        data["sma20"] = data["close"].rolling(20).mean()
        data["sma50"] = data["close"].rolling(50).mean()
        data["rsi14"] = self._rsi(data["close"])
        data["high20"] = data["high"].rolling(20).max().shift(1)
        data["low10"] = data["low"].rolling(10).min().shift(1)
        return data.dropna().reset_index(drop=True)

    def _strategy_signal(self, data: pd.DataFrame, index: int, strategy_name: str) -> str:
        row = data.iloc[index]
        previous = data.iloc[index - 1]
        close = float(row["close"])
        if strategy_name == "moving_average_crossover":
            if float(row["sma20"]) > float(row["sma50"]) and float(previous["sma20"]) <= float(previous["sma50"]):
                return "BUY"
            if float(row["sma20"]) < float(row["sma50"]) and float(previous["sma20"]) >= float(previous["sma50"]):
                return "SELL"
        if strategy_name == "rsi_mean_reversion":
            if float(row["rsi14"]) < 35:
                return "BUY"
            if float(row["rsi14"]) > 60:
                return "SELL"
        if strategy_name == "breakout":
            if close > float(row["high20"]):
                return "BUY"
            if close < float(row["low10"]):
                return "SELL"
        return "WAIT"

    def _rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean().replace(0, 0.000001)
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _apply_slippage(self, price: float, slippage_percent: float, side: str) -> float:
        adjustment = slippage_percent / 100
        return price * (1 + adjustment) if side == "BUY" else price * (1 - adjustment)

    def _fee(self, notional: float, fees_percent: float) -> float:
        return notional * (fees_percent / 100)

    def _close_position(self, position: OpenPosition, exit_time: datetime, exit_price: float, fees_percent: float, exit_reason: str) -> dict:
        gross_pnl = (exit_price - position.entry_price) * position.quantity
        fees = self._fee(position.entry_price * position.quantity, fees_percent) + self._fee(exit_price * position.quantity, fees_percent)
        pnl = gross_pnl - fees
        basis = position.entry_price * position.quantity
        return {
            "entry_time": position.entry_time,
            "exit_time": exit_time,
            "side": "LONG",
            "quantity": position.quantity,
            "entry_price": round(position.entry_price, 4),
            "exit_price": round(exit_price, 4),
            "pnl": round(pnl, 2),
            "pnl_percent": round((pnl / basis) * 100, 4) if basis else 0.0,
            "exit_reason": exit_reason,
        }

    def _metrics(self, initial_capital: float, final_equity: float, max_drawdown: float, trades: list[dict], daily_returns: list[float]) -> dict:
        wins = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
        losses = [trade["pnl"] for trade in trades if trade["pnl"] < 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        variance = sum((value - avg_return) ** 2 for value in daily_returns) / len(daily_returns) if daily_returns else 0.0
        std_dev = sqrt(variance)
        return {
            "total_return_percent": round(((final_equity - initial_capital) / initial_capital) * 100, 4),
            "max_drawdown_percent": round(max_drawdown, 4),
            "win_rate": round((len(wins) / len(trades)) * 100, 2) if trades else 0.0,
            "loss_rate": round((len(losses) / len(trades)) * 100, 2) if trades else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (round(gross_profit, 4) if gross_profit else 0.0),
            "sharpe_ratio": round((avg_return / std_dev) * sqrt(252), 4) if std_dev else 0.0,
            "average_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
            "average_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
        }
