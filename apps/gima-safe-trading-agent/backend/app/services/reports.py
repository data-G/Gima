from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.trading import TradeJournal


class ReportingService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def daily_pl(self, db: Session) -> dict:
        start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
        realized = db.query(func.coalesce(func.sum(TradeJournal.pnl), 0.0)).filter(
            TradeJournal.created_at >= start
        ).scalar()
        return {
            "date": date.today().isoformat(),
            "realized_pl": float(realized or 0.0),
            "daily_loss_limit": -(self.settings.account_equity * self.settings.max_daily_loss),
            "weekly_loss_limit": -(self.settings.account_equity * self.settings.max_weekly_loss),
            "trading_mode": self.settings.trading_mode,
            "live_trading_enabled": self.settings.is_live_trading_allowed,
        }
