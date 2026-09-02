# Agentic Options Trading

Personal intraday agentic options-trading decision-support application. The
full specification lives in [`requirements.md`](requirements.md); this
README covers only how to run what's currently implemented.

**Status:** Phase 0 (foundation) — FastAPI skeleton, typed shared contracts,
config/secrets scaffolding, an Alembic-managed async DB layer, a pluggable
LLM insight-provider layer, and a placeholder background-worker scaffold.
No screener, indicator, risk, or broker logic yet.

## Local development

Managed with [uv](https://docs.astral.sh/uv/). The app itself runs on your
machine; the database can be local SQLite or a remote Postgres (e.g.
Supabase) — either way, schema is Alembic-managed, never created by the
app at runtime.

```bash
uv sync --extra dev
cp .env.example .env   # fill in DATABASE__URL (Supabase or sqlite), GEMINI_API_KEY, etc.
uv run alembic upgrade head
uv run uvicorn trading_app.main:app --reload
```

OpenAPI docs: http://localhost:8000/docs

To point at Supabase instead of the SQLite default, set in `.env`:

```bash
DATABASE__URL=postgresql+asyncpg://postgres.<project-ref>:<password>@<host>:5432/postgres
```

(Get the connection string from Supabase's Database Settings page — use
the asyncpg driver prefix as shown, not the raw `postgresql://` one.)
Nothing else in the app changes based on which database you point at.

## Production (containerized)

```bash
docker build -t agentic-options-trading .
docker run -d -p 8000:8000 --env-file .env agentic-options-trading
# or:
docker compose up --build
```

The container's entrypoint (`docker-entrypoint.sh`) runs
`alembic upgrade head` automatically before starting `uvicorn` — migrations
never need a manual step in production. Inject `DATABASE__URL`,
`GEMINI_API_KEY`, and any other secrets via your hosting platform's secrets
mechanism, not a committed `.env`; `docker-compose.yml` uses `env_file: .env`
purely as a local convenience for testing the container image itself.

Live trading is disabled by default in every environment
(`SAFETY__LIVE_TRADING_ENABLED=false`) and can only be changed through the
protected `POST /api/v1/configuration/safety/live-mode` action — never
inferred from whether broker credentials happen to be present.

## Database migrations

Schema is owned entirely by [Alembic](https://alembic.sqlalchemy.org/); the
app never calls `create_all` at runtime. `migrations/env.py` reads the DB
URL and target metadata straight from `trading_app.config`/`trading_app.db`,
so migrations always run against whatever `DATABASE__URL` you have
configured — no separate URL to keep in sync.

```bash
uv run alembic upgrade head                       # apply pending migrations
uv run alembic revision --autogenerate -m "..."   # generate a new migration from model changes
uv run alembic downgrade -1                       # roll back one migration
```

Every table this app creates — including Alembic's own version-tracking
table (`ot_alembic_version`) — is prefixed `ot_`, so this database can be
shared safely with other projects. Keep using that prefix for any new
model.

## LLM provider

Application code depends only on the `InsightProvider` interface
(`trading_app.services.insights`); the active implementation is selected
purely by `LLM__PROVIDER`, never hardcoded (requirements.md section 4.4).
Switch providers by changing env vars alone:

```bash
LLM__PROVIDER=gemini
LLM__MODEL_NAME=gemini-2.5-flash   # verify against currently available Gemini models
GEMINI_API_KEY=...
```

```bash
LLM__PROVIDER=ollama
LLM__MODEL_NAME=llama3.1           # any model you've pulled locally: `ollama pull llama3.1`
LLM__OLLAMA_BASE_URL=http://localhost:11434   # default; change if Ollama runs elsewhere
```

`GET /api/v1/configuration/llm` reports which provider/model is currently
active. Add a third provider by implementing `InsightProvider` under
`services/insights/` and registering it in `services/insights/factory.py`
— no other call site changes.

## Test

```bash
uv run pytest
```

Run a single test: `uv run pytest tests/test_health.py::test_liveness`

Tests always run against an isolated, throwaway SQLite file
(`tests/.test_trading_app.db`) created directly via `create_all`, regardless
of what `DATABASE__URL` your `.env` points at — they never touch a real
(Supabase/Postgres) database. See `tests/conftest.py`.

## Lint / type-check

```bash
uv run ruff check .
uv run mypy src
```

## Project layout

```
src/trading_app/
  main.py          FastAPI app factory + lifespan (background workers only —
                   schema is Alembic-managed, not created here)
  config.py        Env-backed Settings, ExecutionMode, live-trading safety posture
  correlation.py   Correlation-ID contextvar + ASGI middleware
  logging_config.py  Structured logging with correlation-id injection
  schemas/         Shared Pydantic contracts (requirements.md section 5)
  api/routers/     One module per required API group (requirements.md section 9)
  db/              Async SQLAlchemy engine/session (Postgres/Supabase or SQLite)
  models/          ORM models, all tables prefixed `ot_` (audit trail so far)
  services/insights/  Pluggable InsightProvider (Gemini / Ollama) + factory
  workers/         Background worker scaffold — one placeholder loop per
                   component (collection, indicators, event detection, LLM
                   evaluation, paper fills, reconciliation, notifications)
  security/        Secret-resolution abstraction (env-backed by default)
migrations/        Alembic environment + versioned migrations
tests/             pytest + httpx async-client tests
```
