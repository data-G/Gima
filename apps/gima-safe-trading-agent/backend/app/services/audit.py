from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.trading import TradeOrder
from app.repositories.trading import AuditLogRepository
from app.schemas.trading import AuditLogCreate


def order_snapshot(order: TradeOrder | None) -> dict[str, Any] | None:
    if order is None:
        return None
    return {
        "id": order.id,
        "user_id": order.user_id,
        "signal_id": order.signal_id,
        "symbol": order.symbol,
        "side": order.side,
        "quantity": order.quantity,
        "entry_price": order.entry_price,
        "stop_loss": order.stop_loss,
        "status": order.status,
        "broker_order_id": order.broker_order_id,
        "is_live_trade": order.is_live_trade,
    }


class AuditLogger:
    def log(
        self,
        db: Session,
        *,
        user_id: int | None,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        before_json: dict[str, Any] | None = None,
        after_json: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        AuditLogRepository().create(
            db,
            AuditLogCreate(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_json=before_json,
                after_json=after_json,
                ip_address=ip_address,
            ),
        )
