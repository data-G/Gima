#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi

if [ "${SEED_DATABASE:-true}" = "true" ]; then
  python -m app.db.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
