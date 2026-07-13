from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.journal import JournalAgent
from app.models.trading import OrderStatus, RiskStatus, TradeOrder
from app.services.audit import AuditLogger, order_snapshot
from app.services.paper_trading import PaperTradingEngine


class HumanApprovalWorkflow:
    def __init__(self, paper_engine: PaperTradingEngine):
        self.paper_engine = paper_engine
        self.journal = JournalAgent()
        self.audit = AuditLogger()

    def decide(self, db: Session, order: TradeOrder, approved: bool, note: str, ip_address: str | None = None) -> TradeOrder:
        if order.status != OrderStatus.pending_approval.value:
            raise ValueError("Only pending paper orders can be approved or rejected.")

        before = order_snapshot(order)
        if not approved:
            order.status = OrderStatus.rejected.value
            self.journal.log_rejected_trade(db, order.symbol, note or "Human rejected the order.")
            db.commit()
            db.refresh(order)
            self.audit.log(db, user_id=order.user_id, action="ORDER_REJECTED", entity_type="trade_order", entity_id=order.id, before_json=before, after_json=order_snapshot(order), ip_address=ip_address)
            return order

        risk_check = self.paper_engine.recheck_risk_before_execution(db, order)
        if risk_check.status != RiskStatus.approved.value:
            self.journal.log_rejected_trade(db, order.symbol, risk_check.reason)
            self.audit.log(db, user_id=order.user_id, action="ORDER_APPROVAL_BLOCKED_BY_RISK", entity_type="trade_order", entity_id=order.id, before_json=before, after_json=order_snapshot(order), ip_address=ip_address)
            raise ValueError(risk_check.reason)

        order.status = OrderStatus.approved.value
        self.journal.log_approved_trade(db, order.symbol, note or "Human approved the paper order.")
        db.commit()
        db.refresh(order)
        self.audit.log(db, user_id=order.user_id, action="ORDER_APPROVED", entity_type="trade_order", entity_id=order.id, before_json=before, after_json=order_snapshot(order), ip_address=ip_address)
        try:
            executed = self.paper_engine.submit_after_approval(db, order)
        except Exception as exc:
            failed_before = order_snapshot(order)
            order.status = OrderStatus.cancelled.value
            db.commit()
            db.refresh(order)
            self.journal.log_rejected_trade(db, order.symbol, f"Paper execution failed after approval: {exc}")
            self.audit.log(db, user_id=order.user_id, action="ORDER_PAPER_EXECUTION_FAILED", entity_type="trade_order", entity_id=order.id, before_json=failed_before, after_json=order_snapshot(order), ip_address=ip_address)
            raise
        self.audit.log(db, user_id=order.user_id, action="ORDER_PAPER_EXECUTED", entity_type="trade_order", entity_id=order.id, before_json=before, after_json=order_snapshot(executed), ip_address=ip_address)
        return executed
