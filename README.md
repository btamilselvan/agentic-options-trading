# Agentic Options Trading

Personal intraday agentic options-trading decision-support application. The
full specification lives in [`requirements.md`](requirements.md); this
README covers only how to run what's currently implemented.

**Status:** Phase 1 underway — the screener (component 1) is implemented;
FastAPI skeleton, typed shared contracts, config/secrets scaffolding, an
Alembic-managed async DB layer, and a pluggable LLM insight-provider layer
are all in place from Phase 0. No quantitative-features engine, state
detection, risk, or broker logic yet.

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

The image defaults `ENVIRONMENT=production` (override with
`-e ENVIRONMENT=development` if you need dev-mode behavior in a
container). This gates, independent of any trading behavior:

- interactive `/docs` and `/redoc` UI — disabled in production (the raw
  `/openapi.json` schema stays available in every environment, per
  requirements.md section 1)
- log format — JSON lines in production, plain-text in development
- FastAPI debug tracebacks and uvicorn autoreload — development only

`ENVIRONMENT=development` is `Settings`' own default, so plain `uv run
uvicorn ...` locally gets dev-mode behavior with no `.env` changes needed.

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

## Screener

The screener (requirements.md section 4.1) refreshes a bounded, ranked
watchlist of candidate symbols from deterministic filters — price, RVOL
proxy, percent move, spread, options availability — with every threshold
and ranking weight configurable via `ScreenerSettings`, never a code
constant. It runs automatically as a background loop (`workers.screener_worker`)
on `SCREENER__REFRESH_INTERVAL_SECONDS` (default 120s) during regular
market hours only (`SCREENER__MARKET_HOURS_ONLY=true`; a simple Mon-Fri
09:30-16:00 America/New_York check — full exchange-calendar handling for
holidays/early closes is a later refinement), and persists every run for
audit/backtesting.

```bash
GET  /api/v1/candidates             # latest run's ranked candidates
GET  /api/v1/candidates?run_id=...  # a specific historical run
GET  /api/v1/candidates/runs        # recent run metadata (audit/backtesting)
POST /api/v1/candidates/run         # force an immediate run (testing/ops)
```

Like the LLM layer, raw market data is fetched through a provider-neutral
`MarketDataProvider` interface (`trading_app.services.market_data`),
selected by `MARKET_DATA__PROVIDER`:

- `static` — a deterministic, synthetic dev fixture. Not real market data.
- `schwab` — the real Schwab Trader API (requirements.md sections 1, 4.2),
  via [schwab-py](https://schwab-py.readthedocs.io/). Field mapping is
  verified against a real, authenticated `/marketdata/v1/quotes` response
  (see `tests/test_schwab_client.py`), and `reference.optionable` gives
  options availability directly — no separate option-chain call needed.

Key `.env` knobs:

```bash
MARKET_DATA__PROVIDER=static
SCREENER__UNIVERSE=["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","SPY","QQQ"]
SCREENER__MAX_CANDIDATES=20
SCREENER__REFRESH_INTERVAL_SECONDS=120
```

### Universe: static list vs. dynamic discovery

Which symbols even get screened is itself pluggable — a separate
`UniverseProvider` interface (`trading_app.services.universe`), selected
by `UNIVERSE__PROVIDER`:

- `static` (default) — screens exactly `SCREENER__UNIVERSE`, unchanged.
- `schwab_movers` — dynamically discovers symbols every cycle from
  Schwab's real top-gainers/top-losers/most-active data
  (`GET /marketdata/v1/movers/{index}`; verified against a real response —
  see `tests/test_schwab_movers.py`). Each call returns only the top 10
  for one index/sort-order combination, so this combines every configured
  pair and dedupes to cover more of the market:

```bash
MARKET_DATA__PROVIDER=schwab
UNIVERSE__PROVIDER=schwab_movers
UNIVERSE__SCHWAB_MOVERS_INDICES=["equity_all"]
UNIVERSE__SCHWAB_MOVERS_SORT_ORDERS=["percent_change_up","percent_change_down","volume"]
UNIVERSE__MAX_DYNAMIC_SYMBOLS=60
UNIVERSE__ALWAYS_INCLUDE=["SPY","QQQ"]   # screened every cycle regardless of what's discovered
```

`ScreenerSettings.exclusions` still applies on top of whatever's
discovered — it's a universal blocklist, not tied to either provider.

### Using the Schwab provider

1. Register an app at [developer.schwab.com](https://developer.schwab.com)
   requesting Trader API access (approval typically takes 1-3 business
   days). Its callback URL must be HTTPS and match exactly what you set
   below.
2. Add to `.env`:
   ```bash
   MARKET_DATA__PROVIDER=schwab
   SCHWAB_CLIENT_ID=<your app key>
   SCHWAB_CLIENT_SECRET=<your app secret>
   SCHWAB_CALLBACK_URL=https://127.0.0.1:8182   # must match your app's registered callback
   SCHWAB_TOKEN_PATH=.secrets/schwab_token.json  # gitignored; never commit this file
   ```
3. One-time interactive browser consent — opens a browser, then writes the
   token to `SCHWAB_TOKEN_PATH`:
   ```bash
   uv run scripts/bootstrap_schwab_oauth.py
   ```
4. Schwab's refresh token lasts ~7 days; run this periodically (e.g. a
   daily cron) to keep the on-disk token from ever going stale — no
   browser needed:
   ```bash
   uv run scripts/refresh_schwab_token.py
   ```
   Once the refresh token itself expires, only step 3's interactive flow
   gets a new one — this script fails clearly when that's the case.

Quotes carry a freshness check (`MARKET_DATA__MAX_QUOTE_AGE_SECONDS`,
default 900s/15min): outside market hours Schwab returns the last
regular-session quote with its original timestamp, which this correctly
marks `STALE` and filters out — that's the fail-closed data-freshness
policy (requirements.md section 8) working as intended, not a bug.

## Quantitative engine

The data collection & quantitative engine (requirements.md section 4.2)
is the canonical, versioned source of technical/volume/volatility/
market-context features — no other component computes its own
indicators. Each cycle it reads the current screener candidates, fetches
their OHLCV bar history via `MarketDataProvider.get_candles` (the same
provider interface the screener uses, extended with a second method),
and persists a `FeatureSnapshot` per symbol:

```bash
GET  /api/v1/features/snapshots             # latest snapshot per symbol
GET  /api/v1/features/snapshots?symbol=...  # history for one symbol
POST /api/v1/features/compute               # force an immediate run (testing/ops)
```

Computed per symbol: session VWAP, EMA(9/20/50) + slopes + alignment,
RSI, ROC, ATR + ATR%, canonical time-of-day-aligned RVOL (distinct from
and more correct than the screener's cheap proxy), volume acceleration,
rolling average volume, previous-day/premarket/opening-range/session
levels, and market context (SPY/QQQ trend, mapped sector-ETF trend,
relative move vs each benchmark). Every definition is versioned
(`feature_definition_version`) and unit-tested against hand-checked
fixtures (`tests/test_quant_*.py`) per requirements.md section 13 — bump
the version string in `QuantEngineSettings` whenever a definition
changes (session boundary, lookback window, period, etc.).

Options features (IV/Greeks/OI) are explicitly out of scope for this
pass — deferred to Phase 2 per requirements.md's own phased plan.

Key `.env` knobs (`QUANT_ENGINE__*`): `PRIMARY_INTERVAL` (which timeframe
EMA/RSI/ATR compute on — VWAP/levels/RVOL always use 1-minute bars),
`EMA_PERIODS`, `RSI_PERIOD`/`ROC_PERIOD`/`ATR_PERIOD`,
`RVOL_LOOKBACK_DAYS` (bounds the minute-history payload size),
`OPENING_RANGE_MINUTES`, `SECTOR_ETF_MAP` (e.g. `{"AAPL":"XLK"}` — best-
effort, `null` sector trend when unmapped), `BENCHMARK_SYMBOLS`,
`REFRESH_INTERVAL_SECONDS`.

**Gotcha already hit once:** Schwab's daily-bar endpoint includes
*today's* still-open bar, whose `close` is just today's live price, not
a closed value — `SchwabMarketDataProvider.get_candles` explicitly
filters it out for `Interval.DAILY`. Without that filter, "previous day
close" silently becomes "today's current price," breaking every level
and relative-move calculation that depends on it.

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
  db/repositories/ Persistence functions, one module per aggregate (screener, features)
  models/          ORM models, all tables prefixed `ot_` (audit, screener, features)
  services/insights/     Pluggable InsightProvider (Gemini / Ollama) + factory
  services/market_data/  Pluggable MarketDataProvider (static fixture / real Schwab) + factory —
                         both current quotes (get_market_snapshots) and OHLCV bar history (get_candles)
  services/screener/     Filters, scoring, market-hours gate, and the run_screen entry point
  services/universe/     Pluggable UniverseProvider (static list / dynamic Schwab movers) + factory
  services/quant/        Indicator functions (vwap/ema/rsi/atr/volume/levels/market_context)
                         + engine.py (FeatureSnapshot assembly) + service.py (provider I/O orchestration)
  workers/         Background workers — `screener` and `indicators` run real logic; the rest
                   (collection, event detection, LLM evaluation, paper fills,
                   reconciliation, notifications) are still placeholders
  security/        Secret-resolution abstraction (env-backed by default)
migrations/        Alembic environment + versioned migrations
scripts/           One-off/periodic ops scripts (Schwab OAuth bootstrap + refresh)
tests/             pytest + httpx async-client tests
```
