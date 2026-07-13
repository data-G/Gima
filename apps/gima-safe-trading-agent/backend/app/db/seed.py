from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.trading import RiskSettingsRepository, UserRepository, WatchlistRepository
from app.schemas.trading import RiskSettingsCreate, UserCreate, WatchlistCreate


def seed_database(db: Session) -> None:
    users = UserRepository()
    risk_settings = RiskSettingsRepository()
    watchlist = WatchlistRepository()

    user = users.get_by_email(db, "paper-trader@example.com")
    if not user:
        user = users.create(db, UserCreate(email="paper-trader@example.com", name="Paper Trader", role="trader"))

    if not risk_settings.get_for_user(db, user.id):
        risk_settings.create(
            db,
            RiskSettingsCreate(
                user_id=user.id,
                max_risk_per_trade_percent=0.5,
                max_daily_loss_percent=2.0,
                max_weekly_loss_percent=5.0,
                max_position_concentration_percent=10.0,
                live_trading_enabled=False,
                kill_switch_enabled=False,
            ),
        )

    existing_symbols = {item.symbol for item in watchlist.list(db, user_id=user.id)}
    for symbol, asset_type in (("SPY", "etf"), ("VT", "etf"), ("AAPL", "stock")):
        if symbol not in existing_symbols:
            watchlist.create(db, WatchlistCreate(user_id=user.id, symbol=symbol, asset_type=asset_type, exchange="SMART"))


if __name__ == "__main__":
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        seed_database(session)
    finally:
        session.close()
