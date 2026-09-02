# Agentic Options Trading

Personal intraday agentic options-trading decision-support application. The
full specification lives in [`requirements.md`](requirements.md); this
README covers only how to run what's currently implemented.

**Status:** Phase 0 (foundation) — FastAPI skeleton, typed shared contracts,
config/secrets scaffolding, an async DB layer, and a placeholder
background-worker scaffold. No screener, indicator, LLM, risk, or broker
logic yet.

## Setup

Managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
cp .env.example .env
```

## Run

```bash
uv run uvicorn trading_app.main:app --reload
# or, via the console script:
uv run trading-app
```

OpenAPI docs: http://localhost:8000/docs

## Test

```bash
uv run pytest
```

Run a single test: `uv run pytest tests/test_health.py::test_liveness`

## Lint / type-check

```bash
uv run ruff check .
uv run mypy src
```

## Project layout

```
src/trading_app/
  main.py          FastAPI app factory + lifespan (DB init, background workers)
  config.py        Env-backed Settings, ExecutionMode, live-trading safety posture
  correlation.py   Correlation-ID contextvar + ASGI middleware
  logging_config.py  Structured logging with correlation-id injection
  schemas/         Shared Pydantic contracts (requirements.md section 5)
  api/routers/     One module per required API group (requirements.md section 9)
  db/              Async SQLAlchemy engine/session (SQLite by default)
  models/          ORM models (audit trail so far; more land per component)
  workers/         Background worker scaffold — one placeholder loop per
                   component (collection, indicators, event detection, LLM
                   evaluation, paper fills, reconciliation, notifications)
  security/        Secret-resolution abstraction (env-backed by default)
tests/             pytest + httpx async-client tests
```

Live trading is disabled by default (`SAFETY__LIVE_TRADING_ENABLED=false`)
and can only be changed through the protected
`POST /api/v1/configuration/safety/live-mode` action — never inferred from
whether broker credentials happen to be present.

Schema migrations: table creation currently uses
`Base.metadata.create_all` at startup. Introduce Alembic once the schema
grows past the audit trail.
