from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.agents.backtesting import BacktestingEngine
from app.agents.journal import JournalAgent
from app.agents.market_data import MarketDataAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.strategy import StrategyAgent
from app.agents.types import MarketDataRejected
from app.brokers.factory import create_broker_client
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.trading import OrderStatus, RiskStatus, TradeOrder
from app.repositories.trading import (
    AuditLogRepository,
    BacktestRepository,
    MarketSnapshotRepository,
    RiskCheckRepository,
    RiskSettingsRepository,
    SignalRepository,
    TradeJournalRepository,
    TradeOrderRepository,
    UserRepository,
    WatchlistRepository,
)
from app.schemas.trading import (
    ApprovalRequest,
    AuditLogRead,
    BacktestResultRead,
    BacktestRunRequest,
    KillSwitchRequest,
    MarketSnapshotCreate,
    MarketSnapshotRead,
    NotificationRead,
    NotificationRequest,
    ReportRead,
    RiskCheckCreate,
    RiskCheckRead,
    RiskSettingsCreate,
    RiskSettingsRead,
    RiskSettingsUpdate,
    SafetyStateRead,
    SignalCreate,
    SignalRead,
    SignalRequest,
    TradeJournalCreate,
    TradeJournalRead,
    TradeOrderCreate,
    TradeOrderRead,
    TradeOrderUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
    WatchlistCreate,
    WatchlistRead,
    WatchlistUpdate,
)
from app.services.approval import HumanApprovalWorkflow
from app.services.audit import AuditLogger, order_snapshot
from app.services.notifications import WhatsAppNotificationService, paper_order_message
from app.services.paper_trading import PaperTradingEngine
from app.services.reports import ReportingService
from app.services.safety import SafetyService

router = APIRouter()


def ensure_default_user(db: Session) -> UserRead:
    repo = UserRepository()
    user = repo.get(db, 1) or repo.get_by_email(db, "paper-trader@example.com")
    if not user:
        user = repo.create(db, UserCreate(email="paper-trader@example.com", name="Paper Trader", role="trader"))
    if not RiskSettingsRepository().get_for_user(db, user.id):
        RiskSettingsRepository().create(db, RiskSettingsCreate(user_id=user.id))
    return user


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "trading_mode": settings.trading_mode,
        "live_trading_enabled": settings.is_live_trading_allowed,
        "safety_notice": "Paper trading only in v1. Trading involves risk, and past performance does not guarantee future results.",
    }


@router.get("/broker/account-summary")
def broker_account_summary(settings: Settings = Depends(get_settings)) -> dict:
    return create_broker_client(settings).get_account_summary()


@router.get("/broker/positions")
def broker_positions(settings: Settings = Depends(get_settings)) -> list[dict]:
    return create_broker_client(settings).get_positions()


@router.get("/broker/market-data/{symbol}")
def broker_market_data(symbol: str, settings: Settings = Depends(get_settings)) -> dict:
    return create_broker_client(settings).get_market_data(symbol)


@router.get("/broker/orders/{broker_order_id}")
def broker_order_status(broker_order_id: str, settings: Settings = Depends(get_settings)) -> dict:
    return create_broker_client(settings).get_order_status(broker_order_id)


@router.post("/broker/orders/{broker_order_id}/cancel")
def broker_cancel_order(broker_order_id: str) -> dict:
    raise HTTPException(status_code=403, detail="Direct broker cancellation is disabled in v1. Use audited order workflows.")


@router.post("/users", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if UserRepository().get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already exists.")
    user = UserRepository().create(db, payload)
    RiskSettingsRepository().create(db, RiskSettingsCreate(user_id=user.id))
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return UserRepository().list(db)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = UserRepository().get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = UserRepository().get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserRepository().update(db, user, payload)


@router.post("/watchlist", response_model=WatchlistRead)
def create_watchlist_item(payload: WatchlistCreate, db: Session = Depends(get_db)):
    ensure_default_user(db)
    return WatchlistRepository().create(db, payload)


@router.get("/watchlist", response_model=list[WatchlistRead])
def list_watchlist(user_id: int | None = None, active: bool | None = None, db: Session = Depends(get_db)):
    return WatchlistRepository().list(db, user_id=user_id, active=active)


@router.patch("/watchlist/{item_id}", response_model=WatchlistRead)
def update_watchlist_item(item_id: int, payload: WatchlistUpdate, db: Session = Depends(get_db)):
    item = WatchlistRepository().get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found.")
    return WatchlistRepository().update(db, item, payload)


@router.delete("/watchlist/{item_id}")
def delete_watchlist_item(item_id: int, db: Session = Depends(get_db)) -> dict:
    item = WatchlistRepository().get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found.")
    WatchlistRepository().delete(db, item)
    return {"status": "deleted", "id": item_id}


@router.post("/market-snapshots", response_model=MarketSnapshotRead)
def create_market_snapshot(payload: MarketSnapshotCreate, db: Session = Depends(get_db)):
    return MarketSnapshotRepository().create(db, payload)


@router.get("/market-snapshots", response_model=list[MarketSnapshotRead])
def list_market_snapshots(symbol: str | None = None, limit: int = Query(default=500, le=1000), db: Session = Depends(get_db)):
    return MarketSnapshotRepository().list(db, symbol=symbol, limit=limit)


@router.get("/market/{symbol}", response_model=MarketSnapshotRead)
def fetch_and_store_market_snapshot(symbol: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        ohlcv = MarketDataAgent(settings).fetch_ohlcv(symbol)
    except MarketDataRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    last = ohlcv.iloc[-1]
    return MarketSnapshotRepository().create(
        db,
        MarketSnapshotCreate(
            symbol=symbol.upper(),
            timeframe="1d",
            open=float(last["open"]),
            high=float(last["high"]),
            low=float(last["low"]),
            close=float(last["close"]),
            volume=float(last["volume"]),
            timestamp=last["timestamp"].to_pydatetime(),
        ),
    )


@router.post("/signals", response_model=SignalRead)
def create_signal(payload: SignalCreate, db: Session = Depends(get_db)):
    return SignalRepository().create(db, payload)


@router.post("/signals/run", response_model=SignalRead)
def run_signal_agent(payload: SignalRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    user = ensure_default_user(db)
    market_agent = MarketDataAgent(settings)
    try:
        ohlcv = market_agent.fetch_ohlcv(payload.symbol)
    except MarketDataRejected as exc:
        JournalAgent().log_rejected_trade(db, payload.symbol, f"Market data rejected: {exc}")
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    last = ohlcv.iloc[-1]
    MarketSnapshotRepository().create(
        db,
        MarketSnapshotCreate(
            symbol=payload.symbol.upper(),
            timeframe="1d",
            open=float(last["open"]),
            high=float(last["high"]),
            low=float(last["low"]),
            close=float(last["close"]),
            volume=float(last["volume"]),
            timestamp=last["timestamp"].to_pydatetime(),
        ),
    )
    snapshot = market_agent.snapshot_from_ohlcv(payload.symbol, ohlcv)
    signal_decision = StrategyAgent().create_signal_from_ohlcv(payload.symbol, ohlcv)
    signal = SignalRepository().create(
        db,
        SignalCreate(
            symbol=signal_decision.symbol,
            signal_type=signal_decision.action,
            confidence=signal_decision.confidence,
            strategy_name="ma20_ma50_rsi_volume",
            explanation=signal_decision.explanation,
            raw_features_json=signal_decision.indicators,
        ),
    )
    risk = RiskManagerAgent(settings).evaluate_signal(db, signal_decision, snapshot["as_of"], snapshot.get("volatility", 0.0))
    RiskCheckRepository().create(
        db,
        RiskCheckCreate(
            signal_id=signal.id,
            status=risk.status,
            reason=risk.reason,
            account_equity=risk.metrics.get("account_equity", settings.account_equity),
            proposed_position_size=risk.quantity,
            risk_amount=risk.metrics.get("risk_amount", 0.0),
            stop_loss=signal_decision.stop_loss,
            max_loss_percent=risk.metrics.get("max_risk_per_trade", settings.max_risk_per_trade) * 100,
        ),
    )
    JournalAgent().log_signal(db, signal_decision, risk)
    return signal


@router.get("/signals", response_model=list[SignalRead])
def list_signals(symbol: str | None = None, limit: int = Query(default=100, le=500), db: Session = Depends(get_db)):
    return SignalRepository().list(db, symbol=symbol, limit=limit)


@router.post("/risk-checks", response_model=RiskCheckRead)
def create_risk_check(payload: RiskCheckCreate, db: Session = Depends(get_db)):
    if payload.status == RiskStatus.approved.value:
        raise HTTPException(status_code=403, detail="Manual APPROVED risk checks are disabled. Run the server-side risk agent.")
    return RiskCheckRepository().create(db, payload)


@router.get("/risk-checks", response_model=list[RiskCheckRead])
def list_risk_checks(signal_id: int | None = None, db: Session = Depends(get_db)):
    return RiskCheckRepository().list(db, signal_id=signal_id)


@router.post("/orders", response_model=TradeOrderRead)
def create_order(payload: TradeOrderCreate, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    ip_address = request.client.host if request.client else None
    if payload.is_live_trade:
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_LIVE", entity_type="trade_order", before_json=None, after_json=payload.model_dump(), ip_address=ip_address)
        raise HTTPException(status_code=403, detail="Live orders are disabled in v1.")
    signal = SignalRepository().get(db, payload.signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found.")
    if signal.signal_type == "WAIT":
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_WAIT_SIGNAL", entity_type="signal", entity_id=signal.id, after_json=payload.model_dump(), ip_address=ip_address)
        JournalAgent().log_rejected_trade(db, payload.symbol, "Order creation blocked because signal is WAIT.")
        raise HTTPException(status_code=400, detail="Cannot create an order from a WAIT signal.")
    if payload.symbol.upper() != signal.symbol.upper() or payload.side != signal.signal_type:
        reason = "Order symbol and side must match the approved signal."
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_SIGNAL_MISMATCH", entity_type="signal", entity_id=signal.id, after_json=payload.model_dump(), ip_address=ip_address)
        raise HTTPException(status_code=400, detail=reason)

    latest_risk = RiskCheckRepository().list(db, signal_id=payload.signal_id, limit=1)
    if not latest_risk or latest_risk[0].status != "APPROVED":
        reason = latest_risk[0].reason if latest_risk else "No approved risk check exists for this signal."
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_RISK", entity_type="signal", entity_id=signal.id, after_json={"payload": payload.model_dump(), "reason": reason}, ip_address=ip_address)
        JournalAgent().log_rejected_trade(db, payload.symbol, f"Order creation blocked: {reason}")
        raise HTTPException(status_code=400, detail=f"Cannot create order unless latest risk check is APPROVED. {reason}")
    risk_created_at = latest_risk[0].created_at
    if risk_created_at.tzinfo is None:
        risk_created_at = risk_created_at.replace(tzinfo=timezone.utc)
    risk_age_seconds = (datetime.now(timezone.utc) - risk_created_at).total_seconds()
    if risk_age_seconds > settings.stale_data_seconds:
        reason = "Approved risk check is stale. Run the signal and risk agents again."
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_STALE_RISK", entity_type="signal", entity_id=signal.id, after_json={"payload": payload.model_dump(), "risk_age_seconds": risk_age_seconds}, ip_address=ip_address)
        JournalAgent().log_rejected_trade(db, payload.symbol, reason)
        raise HTTPException(status_code=400, detail=reason)
    if payload.quantity > latest_risk[0].proposed_position_size:
        reason = "Requested quantity exceeds risk-approved position size."
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_SIZE", entity_type="signal", entity_id=signal.id, after_json={"payload": payload.model_dump(), "approved_quantity": latest_risk[0].proposed_position_size}, ip_address=ip_address)
        JournalAgent().log_rejected_trade(db, payload.symbol, reason)
        raise HTTPException(status_code=400, detail=reason)
    if payload.stop_loss != latest_risk[0].stop_loss:
        reason = "Order stop-loss must match the approved risk check."
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_STOP_MISMATCH", entity_type="signal", entity_id=signal.id, after_json={"payload": payload.model_dump(), "approved_stop_loss": latest_risk[0].stop_loss}, ip_address=ip_address)
        JournalAgent().log_rejected_trade(db, payload.symbol, reason)
        raise HTTPException(status_code=400, detail=reason)
    active_existing = [
        order for order in TradeOrderRepository().list(db, user_id=payload.user_id, limit=500)
        if order.signal_id == payload.signal_id and order.status in {OrderStatus.pending_approval.value, OrderStatus.approved.value, OrderStatus.paper_executed.value}
    ]
    if active_existing:
        reason = "An active or executed order already exists for this signal."
        AuditLogger().log(db, user_id=payload.user_id, action="ORDER_CREATE_BLOCKED_DUPLICATE_SIGNAL", entity_type="signal", entity_id=signal.id, after_json={"payload": payload.model_dump(), "existing_order_id": active_existing[0].id}, ip_address=ip_address)
        raise HTTPException(status_code=409, detail=reason)

    order = TradeOrderRepository().create(db, payload)
    JournalAgent().log_attempted_order(db, order.symbol, f"Pending paper order #{order.id} created and awaiting human approval.")
    AuditLogger().log(db, user_id=order.user_id, action="ORDER_CREATED_PENDING_APPROVAL", entity_type="trade_order", entity_id=order.id, before_json=None, after_json=order_snapshot(order), ip_address=ip_address)
    try:
        notification = WhatsAppNotificationService(settings).send_text(paper_order_message(order.id, order.symbol, order.side, order.quantity))
        AuditLogger().log(db, user_id=order.user_id, action="NOTIFICATION_PAPER_ORDER_REVIEW", entity_type="trade_order", entity_id=order.id, after_json=notification.__dict__, ip_address=ip_address)
    except Exception as exc:
        AuditLogger().log(db, user_id=order.user_id, action="NOTIFICATION_FAILED", entity_type="trade_order", entity_id=order.id, after_json={"error": str(exc)}, ip_address=ip_address)
    return order


@router.get("/orders", response_model=list[TradeOrderRead])
def list_orders(user_id: int | None = None, status: str | None = None, db: Session = Depends(get_db)):
    return TradeOrderRepository().list(db, user_id=user_id, status=status)


@router.patch("/orders/{order_id}", response_model=TradeOrderRead)
def update_order(order_id: int, payload: TradeOrderUpdate, request: Request, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    order = TradeOrderRepository().get(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if payload.is_live_trade:
        AuditLogger().log(db, user_id=order.user_id, action="ORDER_UPDATE_BLOCKED_LIVE", entity_type="trade_order", entity_id=order.id, before_json=order_snapshot(order), after_json=payload.model_dump(exclude_unset=True), ip_address=ip_address)
        raise HTTPException(status_code=403, detail="Live orders are disabled in v1.")
    updates = payload.model_dump(exclude_unset=True)
    allowed = {"status"}
    if set(updates) - allowed or updates.get("status") not in {OrderStatus.cancelled.value, OrderStatus.rejected.value}:
        AuditLogger().log(db, user_id=order.user_id, action="ORDER_UPDATE_BLOCKED_IMMUTABLE", entity_type="trade_order", entity_id=order.id, before_json=order_snapshot(order), after_json=updates, ip_address=ip_address)
        raise HTTPException(status_code=403, detail="Orders are immutable after creation except audited cancellation or rejection.")
    if order.status != OrderStatus.pending_approval.value:
        AuditLogger().log(db, user_id=order.user_id, action="ORDER_UPDATE_BLOCKED_STATUS", entity_type="trade_order", entity_id=order.id, before_json=order_snapshot(order), after_json=updates, ip_address=ip_address)
        raise HTTPException(status_code=400, detail="Only pending approval orders can be cancelled or rejected.")
    before = order_snapshot(order)
    updated = TradeOrderRepository().update(db, order, payload)
    AuditLogger().log(db, user_id=updated.user_id, action=f"ORDER_{updated.status}", entity_type="trade_order", entity_id=updated.id, before_json=before, after_json=order_snapshot(updated), ip_address=ip_address)
    return updated


@router.post("/orders/{order_id}/approval", response_model=TradeOrderRead)
def approve_order(order_id: int, payload: ApprovalRequest, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> TradeOrder:
    order = TradeOrderRepository().get_for_update(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    workflow = HumanApprovalWorkflow(PaperTradingEngine(settings))
    try:
        return workflow.decide(db, order, payload.approved, payload.note, ip_address=request.client.host if request.client else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(user_id: int | None = None, entity_type: str | None = None, limit: int = Query(default=200, le=500), db: Session = Depends(get_db)):
    return AuditLogRepository().list(db, user_id=user_id, entity_type=entity_type, limit=limit)


@router.post("/journal", response_model=TradeJournalRead)
def create_journal_entry(payload: TradeJournalCreate, db: Session = Depends(get_db)):
    return TradeJournalRepository().create(db, payload)


@router.get("/journal", response_model=list[TradeJournalRead])
def list_journal(symbol: str | None = None, order_id: int | None = None, db: Session = Depends(get_db)):
    return TradeJournalRepository().list(db, symbol=symbol, order_id=order_id)


@router.get("/risk-settings/{user_id}", response_model=RiskSettingsRead)
def get_risk_settings(user_id: int, db: Session = Depends(get_db)):
    settings = RiskSettingsRepository().get_for_user(db, user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Risk settings not found.")
    return settings


@router.put("/risk-settings/{user_id}", response_model=RiskSettingsRead)
def upsert_risk_settings(user_id: int, payload: RiskSettingsUpdate, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    ensure_default_user(db)
    if payload.live_trading_enabled:
        AuditLogger().log(db, user_id=user_id, action="RISK_SETTINGS_LIVE_FLAG_BLOCKED", entity_type="risk_settings", entity_id=user_id, after_json=payload.model_dump(exclude_unset=True), ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=403, detail="User live trading flag cannot be enabled in v1.")
    before = RiskSettingsRepository().get_for_user(db, user_id)
    updated = RiskSettingsRepository().upsert_for_user(db, user_id, payload)
    AuditLogger().log(db, user_id=user_id, action="RISK_SETTINGS_UPDATED", entity_type="risk_settings", entity_id=updated.id, before_json=None if before is None else {"kill_switch_enabled": before.kill_switch_enabled, "live_trading_enabled": before.live_trading_enabled}, after_json=payload.model_dump(exclude_unset=True), ip_address=request.client.host if request.client else None)
    return updated


@router.post("/backtests/run", response_model=BacktestResultRead)
def run_backtest(payload: BacktestRunRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    if payload.end_date <= payload.start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date.")
    lookback_days = max((payload.end_date - payload.start_date).days + 90, 120)
    try:
        ohlcv = MarketDataAgent(settings).fetch_ohlcv(payload.symbol, lookback_days=lookback_days)
        result = BacktestingEngine().run(ohlcv, payload)
    except (MarketDataRejected, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BacktestRepository().create(db, result)


@router.get("/backtests", response_model=list[BacktestResultRead])
def list_backtests(
    symbol: str | None = None,
    strategy_name: str | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    return BacktestRepository().list(db, symbol=symbol, strategy_name=strategy_name, limit=limit)


@router.get("/backtests/{backtest_id}", response_model=BacktestResultRead)
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    backtest = BacktestRepository().get(db, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found.")
    return backtest


@router.get("/reports/daily-pl", response_model=ReportRead)
def daily_report(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    return ReportingService(settings).daily_pl(db)


@router.get("/safety", response_model=SafetyStateRead)
def get_safety(db: Session = Depends(get_db)):
    return SafetyService().get_state(db)


@router.post("/notifications/test", response_model=NotificationRead)
def send_test_notification(payload: NotificationRequest, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    message = (
        "Gima Safe Trading Agent paper-trading notification.\n"
        f"{payload.message}\n"
        "This is decision support only. WhatsApp messages do not execute trades."
    )
    try:
        result = WhatsAppNotificationService(settings).send_text(message, payload.recipient)
    except Exception as exc:
        AuditLogger().log(db, user_id=1, action="NOTIFICATION_TEST_FAILED", entity_type="notification", after_json={"error": str(exc)}, ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditLogger().log(db, user_id=1, action="NOTIFICATION_TEST_SENT", entity_type="notification", after_json=result.__dict__, ip_address=request.client.host if request.client else None)
    return result


@router.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
):
    expected = settings.whatsapp_webhook_verify_token.get_secret_value() if settings.whatsapp_webhook_verify_token else ""
    if hub_mode == "subscribe" and expected and hub_verify_token == expected:
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed.")


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    AuditLogger().log(
        db,
        user_id=1,
        action="WHATSAPP_WEBHOOK_RECEIVED_NO_TRADE_ACTION",
        entity_type="notification",
        after_json=payload,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "received", "trade_action": "ignored"}


@router.post("/safety/kill-switch", response_model=SafetyStateRead)
def set_kill_switch(payload: KillSwitchRequest, request: Request, db: Session = Depends(get_db)):
    before = SafetyService().get_state(db)
    result = SafetyService().set_kill_switch(db, payload.active, payload.reason)
    AuditLogger().log(
        db,
        user_id=1,
        action="KILL_SWITCH_UPDATED",
        entity_type="risk_settings",
        entity_id=1,
        before_json=before,
        after_json=result,
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.get("/decisions", response_model=list[SignalRead])
def list_decisions(db: Session = Depends(get_db)):
    return SignalRepository().list(db)
