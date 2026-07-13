from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.types import RiskDecision, SignalDecision
from app.core.config import Settings
from app.models.trading import RiskSettings, TradeJournal


class RiskManagerAgent:
    def __init__(self, settings: Settings):
        self.settings = settings

    def evaluate_signal(self, db: Session, signal: SignalDecision, market_as_of: datetime, volatility: float = 0.0, user_id: int | None = None) -> RiskDecision:
        reasons: list[str] = []
        equity = self.settings.account_equity
        metrics: dict[str, float] = {"account_equity": equity, "volatility": volatility}

        risk_query = db.query(RiskSettings)
        if user_id is not None:
            risk_query = risk_query.filter(RiskSettings.user_id == user_id)
        risk_settings = risk_query.order_by(RiskSettings.id).first()
        if risk_settings and risk_settings.kill_switch_enabled:
            reasons.append("Kill switch is active.")
        max_risk_per_trade = min(self.settings.max_risk_per_trade, (risk_settings.max_risk_per_trade_percent / 100) if risk_settings else self.settings.max_risk_per_trade)
        max_daily_loss = min(self.settings.max_daily_loss, (risk_settings.max_daily_loss_percent / 100) if risk_settings else self.settings.max_daily_loss)
        max_weekly_loss = min(self.settings.max_weekly_loss, (risk_settings.max_weekly_loss_percent / 100) if risk_settings else self.settings.max_weekly_loss)
        max_position_concentration = min(
            self.settings.max_position_concentration,
            (risk_settings.max_position_concentration_percent / 100) if risk_settings else self.settings.max_position_concentration,
        )
        metrics["max_risk_per_trade"] = max_risk_per_trade
        metrics["max_daily_loss"] = max_daily_loss
        metrics["max_weekly_loss"] = max_weekly_loss
        metrics["max_position_concentration"] = max_position_concentration

        if equity <= 0:
            reasons.append("Account equity must be positive.")

        if signal.action == "WAIT":
            reasons.append("Strategy selected WAIT; no order should be created.")

        if signal.confidence < self.settings.min_confidence:
            reasons.append("Confidence is below the configured minimum.")

        if volatility > self.settings.max_volatility:
            reasons.append("Volatility is too high for v1 risk limits.")

        age_seconds = (datetime.now(timezone.utc) - market_as_of).total_seconds()
        metrics["market_data_age_seconds"] = age_seconds
        if age_seconds > self.settings.stale_data_seconds:
            reasons.append("Market data is stale.")

        if signal.stop_loss is None or signal.stop_loss <= 0 or signal.stop_loss == signal.entry_price:
            reasons.append("Every trade must include a valid stop-loss.")

        daily_pl = self._realized_pl_since(db, datetime.now(timezone.utc) - timedelta(days=1))
        weekly_pl = self._realized_pl_since(db, datetime.now(timezone.utc) - timedelta(days=7))
        metrics["daily_realized_pl"] = daily_pl
        metrics["weekly_realized_pl"] = weekly_pl
        if daily_pl <= -(equity * max_daily_loss):
            reasons.append("Daily loss limit has been reached.")
        if weekly_pl <= -(equity * max_weekly_loss):
            reasons.append("Weekly loss limit has been reached.")

        quantity = self._position_size(signal, max_risk_per_trade, max_position_concentration)
        concentration = (quantity * signal.entry_price) / equity if equity else 0
        risk_amount = quantity * abs(signal.entry_price - (signal.stop_loss or signal.entry_price))
        metrics["quantity"] = float(quantity)
        metrics["position_concentration"] = concentration
        metrics["risk_amount"] = risk_amount
        metrics["max_risk_amount"] = equity * max_risk_per_trade
        if signal.action != "WAIT" and quantity <= 0:
            reasons.append("Position size is zero under max risk per trade.")
        if concentration > max_position_concentration:
            reasons.append("Position concentration would exceed 10% per symbol.")
        if risk_amount > equity * max_risk_per_trade:
            reasons.append("Trade risk exceeds max risk per trade.")

        if not self.settings.require_human_approval:
            reasons.append("Human approval must remain enabled for v1.")

        if self.settings.trading_mode != "paper":
            reasons.append("Only paper trading is supported in v1.")

        approved = len(reasons) == 0
        return RiskDecision(
            status="APPROVED" if approved else "BLOCKED",
            approved=approved,
            reason="Approved for paper approval queue." if approved else " ".join(reasons),
            quantity=quantity if approved else 0,
            metrics=metrics,
        )

    def evaluate(self, db: Session, signal: dict, snapshot: dict) -> dict:
        decision = SignalDecision(
            symbol=signal["symbol"],
            action=signal["action"],
            confidence=signal["confidence"],
            explanation=signal.get("reason", ""),
            entry_price=signal["entry_price"],
            stop_loss=signal.get("stop_loss") or None,
            indicators=signal.get("indicators", {}),
        )
        risk = self.evaluate_signal(db, decision, snapshot["as_of"], snapshot.get("volatility", 0.0))
        return {
            "allowed": risk.approved,
            "status": risk.status,
            "reason": risk.reason,
            "quantity": risk.quantity,
            "metrics": risk.metrics,
        }

    def _position_size(self, signal: SignalDecision, max_risk_per_trade: float | None = None, max_position_concentration: float | None = None) -> int:
        risk_limit = self.settings.max_risk_per_trade if max_risk_per_trade is None else max_risk_per_trade
        concentration_limit = self.settings.max_position_concentration if max_position_concentration is None else max_position_concentration
        risk_budget = self.settings.account_equity * risk_limit
        if signal.stop_loss is None:
            return 0
        per_share_risk = abs(signal.entry_price - signal.stop_loss)
        if per_share_risk <= 0:
            return 0
        risk_quantity = int(risk_budget // per_share_risk)
        concentration_quantity = int((self.settings.account_equity * concentration_limit) // signal.entry_price)
        return max(0, min(risk_quantity, concentration_quantity))

    def _realized_pl_since(self, db: Session, since: datetime) -> float:
        value = db.query(func.coalesce(func.sum(TradeJournal.pnl), 0.0)).filter(
            TradeJournal.created_at >= since
        ).scalar()
        return float(value or 0.0)
