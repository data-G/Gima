from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.models.trading import (
    MarketSnapshot,
    BacktestResult,
    BacktestTrade,
    AuditLog,
    RiskCheck,
    RiskSettings,
    Signal,
    TradeJournal,
    TradeOrder,
    User,
    WatchlistItem,
)
from app.schemas.trading import (
    MarketSnapshotCreate,
    RiskCheckCreate,
    RiskSettingsCreate,
    RiskSettingsUpdate,
    SignalCreate,
    TradeJournalCreate,
    TradeOrderCreate,
    TradeOrderUpdate,
    UserCreate,
    UserUpdate,
    WatchlistCreate,
    WatchlistUpdate,
    BacktestResultCreate,
    AuditLogCreate,
)

ModelT = TypeVar("ModelT")


def _apply_updates(model: ModelT, updates: dict[str, Any]) -> ModelT:
    for key, value in updates.items():
        if value is not None:
            setattr(model, key, value)
    return model


class UserRepository:
    def create(self, db: Session, payload: UserCreate) -> User:
        user = User(**payload.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get(self, db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def list(self, db: Session, limit: int = 100) -> list[User]:
        return db.query(User).order_by(User.created_at.desc()).limit(limit).all()

    def update(self, db: Session, user: User, payload: UserUpdate) -> User:
        _apply_updates(user, payload.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(user)
        return user


class WatchlistRepository:
    def create(self, db: Session, payload: WatchlistCreate) -> WatchlistItem:
        data = payload.model_dump()
        data["symbol"] = payload.symbol.upper()
        item = WatchlistItem(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def get(self, db: Session, item_id: int) -> WatchlistItem | None:
        return db.get(WatchlistItem, item_id)

    def list(self, db: Session, user_id: int | None = None, active: bool | None = None) -> list[WatchlistItem]:
        query = db.query(WatchlistItem)
        if user_id is not None:
            query = query.filter(WatchlistItem.user_id == user_id)
        if active is not None:
            query = query.filter(WatchlistItem.active == active)
        return query.order_by(WatchlistItem.symbol).all()

    def update(self, db: Session, item: WatchlistItem, payload: WatchlistUpdate) -> WatchlistItem:
        _apply_updates(item, payload.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, item: WatchlistItem) -> None:
        db.delete(item)
        db.commit()


class MarketSnapshotRepository:
    def create(self, db: Session, payload: MarketSnapshotCreate) -> MarketSnapshot:
        data = payload.model_dump()
        data["symbol"] = payload.symbol.upper()
        snapshot = MarketSnapshot(**data)
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    def list(self, db: Session, symbol: str | None = None, limit: int = 500) -> list[MarketSnapshot]:
        query = db.query(MarketSnapshot)
        if symbol:
            query = query.filter(MarketSnapshot.symbol == symbol.upper())
        return query.order_by(MarketSnapshot.timestamp.desc()).limit(limit).all()


class SignalRepository:
    def create(self, db: Session, payload: SignalCreate) -> Signal:
        data = payload.model_dump()
        data["symbol"] = payload.symbol.upper()
        signal = Signal(**data)
        db.add(signal)
        db.commit()
        db.refresh(signal)
        return signal

    def get(self, db: Session, signal_id: int) -> Signal | None:
        return db.get(Signal, signal_id)

    def list(self, db: Session, symbol: str | None = None, limit: int = 100) -> list[Signal]:
        query = db.query(Signal)
        if symbol:
            query = query.filter(Signal.symbol == symbol.upper())
        return query.order_by(Signal.created_at.desc()).limit(limit).all()


class RiskCheckRepository:
    def create(self, db: Session, payload: RiskCheckCreate) -> RiskCheck:
        risk_check = RiskCheck(**payload.model_dump())
        db.add(risk_check)
        db.commit()
        db.refresh(risk_check)
        return risk_check

    def list(self, db: Session, signal_id: int | None = None, limit: int = 100) -> list[RiskCheck]:
        query = db.query(RiskCheck)
        if signal_id:
            query = query.filter(RiskCheck.signal_id == signal_id)
        return query.order_by(RiskCheck.created_at.desc()).limit(limit).all()


class TradeOrderRepository:
    def create(self, db: Session, payload: TradeOrderCreate) -> TradeOrder:
        data = payload.model_dump()
        data["symbol"] = payload.symbol.upper()
        order = TradeOrder(**data)
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    def get(self, db: Session, order_id: int) -> TradeOrder | None:
        return db.get(TradeOrder, order_id)

    def get_for_update(self, db: Session, order_id: int) -> TradeOrder | None:
        return db.query(TradeOrder).filter(TradeOrder.id == order_id).with_for_update().one_or_none()

    def list(self, db: Session, user_id: int | None = None, status: str | None = None, limit: int = 100) -> list[TradeOrder]:
        query = db.query(TradeOrder)
        if user_id:
            query = query.filter(TradeOrder.user_id == user_id)
        if status:
            query = query.filter(TradeOrder.status == status)
        return query.order_by(TradeOrder.created_at.desc()).limit(limit).all()

    def update(self, db: Session, order: TradeOrder, payload: TradeOrderUpdate) -> TradeOrder:
        _apply_updates(order, payload.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(order)
        return order


class TradeJournalRepository:
    def create(self, db: Session, payload: TradeJournalCreate) -> TradeJournal:
        data = payload.model_dump()
        data["symbol"] = payload.symbol.upper()
        entry = TradeJournal(**data)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def list(self, db: Session, symbol: str | None = None, order_id: int | None = None, limit: int = 200) -> list[TradeJournal]:
        query = db.query(TradeJournal)
        if symbol:
            query = query.filter(TradeJournal.symbol == symbol.upper())
        if order_id:
            query = query.filter(TradeJournal.order_id == order_id)
        return query.order_by(TradeJournal.created_at.desc()).limit(limit).all()


class RiskSettingsRepository:
    def create(self, db: Session, payload: RiskSettingsCreate) -> RiskSettings:
        settings = RiskSettings(**payload.model_dump())
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings

    def get_for_user(self, db: Session, user_id: int) -> RiskSettings | None:
        return db.query(RiskSettings).filter(RiskSettings.user_id == user_id).first()

    def upsert_for_user(self, db: Session, user_id: int, payload: RiskSettingsUpdate | RiskSettingsCreate) -> RiskSettings:
        settings = self.get_for_user(db, user_id)
        if not settings:
            data = payload.model_dump(exclude_unset=True)
            data["user_id"] = user_id
            return self.create(db, RiskSettingsCreate(**data))
        _apply_updates(settings, payload.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(settings)
        return settings


class BacktestRepository:
    def create(self, db: Session, payload: BacktestResultCreate) -> BacktestResult:
        data = payload.model_dump()
        trade_rows = data.pop("trades", [])
        data["symbol"] = payload.symbol.upper()
        result = BacktestResult(**data)
        db.add(result)
        db.flush()
        for trade in trade_rows:
            db.add(BacktestTrade(backtest_id=result.id, **trade))
        db.commit()
        db.refresh(result)
        return result

    def get(self, db: Session, backtest_id: int) -> BacktestResult | None:
        return db.get(BacktestResult, backtest_id)

    def list(self, db: Session, symbol: str | None = None, strategy_name: str | None = None, limit: int = 100) -> list[BacktestResult]:
        query = db.query(BacktestResult)
        if symbol:
            query = query.filter(BacktestResult.symbol == symbol.upper())
        if strategy_name:
            query = query.filter(BacktestResult.strategy_name == strategy_name)
        return query.order_by(BacktestResult.created_at.desc()).limit(limit).all()


class AuditLogRepository:
    def create(self, db: Session, payload: AuditLogCreate) -> AuditLog:
        entry = AuditLog(**payload.model_dump())
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def list(self, db: Session, user_id: int | None = None, entity_type: str | None = None, limit: int = 200) -> list[AuditLog]:
        query = db.query(AuditLog)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
