# Gima Safe Trading Agent

Production-ready skeleton for an agent-based trading assistant with strict v1 safety limits.

Gima Safe Trading Agent is risk-controlled decision support for paper trading. Trading involves risk, human approval is required, and past performance does not guarantee future results. Capital protection first.

The first version is paper trading only. Real-money trading is disabled by default and the backend refuses non-paper order submission in v1.

## Stack

- Frontend: Next.js 16, React, TypeScript, Tailwind CSS
- Backend: Python FastAPI
- Database: PostgreSQL with SQLAlchemy
- Broker integration: safe mock broker for local paper trading
- AI/agent system: modular Python agents
- Notifications: mock WhatsApp adapter locally, optional WhatsApp Cloud API sender later
- Deployment: Docker and Docker Compose

## Safety Defaults

- `TRADING_MODE=paper`
- `REAL_TRADING_ENABLED=false`
- `REQUIRE_HUMAN_APPROVAL=true`
- Stocks and ETFs only in v1
- Margin and leverage features are out of scope and disabled in v1
- Crypto, forex, options, and CFDs are out of scope and disabled in v1
- Every created order is a paper order and starts as `pending_approval`

Risk rules implemented in `backend/app/agents/risk_manager.py`:

- Max risk per trade: 0.5% of account equity
- Max daily loss: 2%
- Max weekly loss: 5%
- Max position concentration: 10% per symbol
- Stop-loss required
- High volatility blocks trades
- Stale data blocks trades
- Low confidence blocks trades
- Kill switch blocks all trades

## Folder Structure

```text
gima-safe-trading-agent/
  backend/
    app/
      agents/          Market data, strategy, risk, backtesting
      api/             FastAPI routes
      core/            Settings and env handling
      db/              SQLAlchemy session/base
      models/          Database models
      schemas/         Pydantic request/response models
      services/        Paper trading, approvals, reports, safety
    Dockerfile
    requirements.txt
  frontend/
    app/               Next.js app routes
    components/        Shared UI
    lib/               API client
    types/             TypeScript API types
    Dockerfile
  docker-compose.yml
```

## Docker Setup

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

The backend container runs Alembic migrations and seed data on startup by default. The seeded local account uses mock broker data and does not require broker credentials.

Useful Docker commands:

```bash
docker compose up --build
docker compose down
docker compose down -v
docker compose logs -f backend
```

## Local Setup Guide

### 1. Install Dependencies

Backend:

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent/frontend
npm install
```

### 2. Start PostgreSQL

For local development without running the full app stack:

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent
cp .env.example .env
docker compose up -d postgres redis
```

The default local database URL is:

```text
postgresql+psycopg://gima:gima@localhost:5432/gima_safe_trading
```

### 3. Run Migrations

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent/backend
source .venv/bin/activate
DATABASE_URL=postgresql+psycopg://gima:gima@localhost:5432/gima_safe_trading alembic upgrade head
DATABASE_URL=postgresql+psycopg://gima:gima@localhost:5432/gima_safe_trading python -m app.db.seed
```

When using `docker compose up --build`, this step is handled automatically by the backend container.

### 4. Start Backend

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent/backend
source .venv/bin/activate
cp ../.env.example .env
uvicorn app.main:app --reload
```

Backend API docs will be available at `http://localhost:8000/docs`.

### 5. Start Frontend

```bash
cd /Users/gimhangunarathne/Documents/Gima/apps/gima-safe-trading-agent/frontend
cp ../.env.example .env.local
npm run dev
```

Frontend will be available at `http://localhost:3000`.

### 6. Use Mock Broker

Mock broker mode is the default local setup:

```env
BROKER_BACKEND=mock
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
REAL_TRADING_ENABLED=false
REQUIRE_HUMAN_APPROVAL=true
```

This mode returns safe local account, position, and market data responses so the app can run without external broker credentials.

### 7. Connect IBKR Paper Trading Later

IBKR paper trading is intentionally not enabled in this milestone. After the local mock-broker app is stable, add IBKR paper connectivity as a separate change with TWS or IB Gateway paper mode, dedicated tests, and the same human approval, risk checks, and kill switch controls.

### 8. WhatsApp Paper-Trade Notifications

WhatsApp is notification-only. WhatsApp messages cannot approve orders, reject orders, place orders, or execute trades.

Local mock notification mode:

```env
NOTIFICATIONS_ENABLED=true
WHATSAPP_MODE=mock
```

Send a safe test notification:

```bash
curl -X POST http://localhost:8000/api/notifications/test \
  -H 'Content-Type: application/json' \
  -d '{"message":"Paper order notification test."}'
```

To connect WhatsApp Cloud API later, create a Meta app with WhatsApp, generate a system-user access token, configure the phone number ID, and set:

```env
NOTIFICATIONS_ENABLED=true
WHATSAPP_MODE=cloud
WHATSAPP_GRAPH_VERSION=v23.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_system_user_token
WHATSAPP_DEFAULT_RECIPIENT=your_test_recipient_number
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token
```

Webhook endpoints:

- `GET /api/webhooks/whatsapp` for Meta verification
- `POST /api/webhooks/whatsapp` for inbound events and delivery status logging

Inbound WhatsApp messages are stored in audit logs with `trade_action=ignored`.

### 9. Safety Limitations

Gima Safe Trading Agent is risk-controlled decision support for paper trading. Trading involves risk, human approval is required, and past performance does not guarantee future results. Capital protection first.

v1 safety boundaries:

- Paper trading only by default
- Stocks and ETFs only
- Margin and leverage features are out of scope and disabled in v1
- Crypto, forex, options, and CFDs are out of scope and disabled in v1
- Every order must pass backend risk checks
- Every order requires human approval before execution
- Kill switch blocks order execution

## Broker Notes

Prompt 1 uses `BROKER_BACKEND=mock` only. Order submission is paper-only, and live routing is blocked at configuration, API, risk, and execution layers.

## API Highlights

- `POST /api/watchlist`
- `GET /api/watchlist`
- `GET /api/market/{symbol}`
- `POST /api/signals`
- `GET /api/decisions`
- `GET /api/orders`
- `POST /api/orders/{order_id}/approval`
- `GET /api/journal`
- `GET /api/reports/daily-pl`
- `GET /api/safety`
- `POST /api/safety/kill-switch`

## Production TODOs

- Add authentication and role-based permissions before deployment outside localhost.
- Add Alembic migrations and migration CI.
- Add encrypted secrets management.
- Add IBKR paper order placement later as a separate milestone after manual review.
- Add quote data provider redundancy.
- Add comprehensive unit and integration tests for every risk rule.
- Add audit export and immutable log storage.
