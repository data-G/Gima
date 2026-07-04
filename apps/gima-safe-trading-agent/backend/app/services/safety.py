from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.trading import RiskSettings
from app.repositories.trading import RiskSettingsRepository
from app.schemas.trading import RiskSettingsCreate, RiskSettingsUpdate


class SafetyService:
    def get_state(self, db: Session, user_id: int = 1) -> dict:
        settings = RiskSettingsRepository().get_for_user(db, user_id)
        if not settings:
            settings = RiskSettingsRepository().create(db, RiskSettingsCreate(user_id=user_id))
        return {"kill_switch_active": settings.kill_switch_enabled, "reason": "Stored in risk_settings.kill_switch_enabled"}

    def set_kill_switch(self, db: Session, active: bool, reason: str, user_id: int = 1) -> dict:
        RiskSettingsRepository().upsert_for_user(db, user_id, RiskSettingsUpdate(kill_switch_enabled=active))
        return {"kill_switch_active": active, "reason": reason or "Stored in risk_settings.kill_switch_enabled"}
