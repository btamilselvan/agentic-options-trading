#!/bin/sh
# Production container entrypoint: apply pending Alembic migrations, then
# start the server. Locally, run these two steps yourself instead (see
# README.md) — this script only runs inside the container.
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn trading_app.main:app --host 0.0.0.0 --port 8000
