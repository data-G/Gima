from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.types import RiskDecision, SignalDecision
from app.models.trading import TradeJournal


class JournalAgent:
    """Persists every trading decision event with reasons and risk metrics."""

    def log_signal(self, db: Session, signal: SignalDecision, risk: RiskDecision | None = None) -> TradeJournal:
        message = signal.explanation
        if risk:
            message = f"{message} Risk={risk.status}: {risk.reason}. Metrics={risk.metrics}"
        return self._log(db, signal.symbol, "signal", message)

    def log_rejected_trade(self, db: Session, symbol: str, reason: str, metrics: dict[str, float] | None = None) -> TradeJournal:
        return self._log(db, symbol, "trade_blocked", f"{reason}. Metrics={metrics or {}}")

    def log_approved_trade(self, db: Session, symbol: str, reason: str, metrics: dict[str, float] | None = None) -> TradeJournal:
        return self._log(db, symbol, "trade_approved", f"{reason}. Metrics={metrics or {}}")

    def log_attempted_order(self, db: Session, symbol: str, message: str) -> TradeJournal:
        return self._log(db, symbol, "order_attempted", message)

    def log_executed_paper_trade(self, db: Session, symbol: str, message: str) -> TradeJournal:
        return self._log(db, symbol, "paper_trade_executed", message)

    def log_final_result(self, db: Session, symbol: str, message: str, realized_pl: float = 0.0) -> TradeJournal:
        return self._log(db, symbol, "final_result", message, realized_pl)

    def _log(self, db: Session, symbol: str, event_type: str, message: str, realized_pl: float = 0.0) -> TradeJournal:
        entry = TradeJournal(symbol=symbol.upper(), notes=f"{event_type}: {message}", pnl=realized_pl)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
