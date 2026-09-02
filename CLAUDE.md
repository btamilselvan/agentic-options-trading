# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Phase 0 (foundation) is scaffolded: a FastAPI skeleton, typed shared contracts, config/secrets scaffolding, an async DB layer, and a placeholder background-worker loop per component. No screener, indicator, LLM, risk, or broker logic is implemented yet — see the phased plan below for what's still ahead.

Treat `requirements.md` as the authoritative spec. Any implementation work in this repo should conform to it; if a requested change conflicts with it, flag the conflict rather than silently diverging.

## Commands

Managed with [uv](https://docs.astral.sh/uv/); everything runs through `uv run` against the `.venv` uv manages.

```bash
uv sync --extra dev                 # install/update deps (reads pyproject.toml + uv.lock)
uv run uvicorn trading_app.main:app --reload   # run the dev server (docs at /docs)
uv run pytest                       # run the test suite
uv run pytest tests/test_health.py::test_liveness   # run a single test
uv run ruff check .                 # lint
uv run ruff check . --fix           # lint, auto-fixing what's safe
uv run mypy src                     # type-check
```

Source lives under `src/trading_app` (src-layout, installed editable); tests under `tests/`, using `pytest-asyncio` (`asyncio_mode = "auto"`) and an `httpx.AsyncClient` against the app via `ASGITransport` — see `tests/conftest.py`.

**Gotcha:** `get_settings()` is a process-wide `lru_cache` singleton, and the live-mode endpoint mutates it in place (see below). Tests that touch it must call `get_settings.cache_clear()` before building the app, or state leaks across test files run in the same process — the `client` fixture in `conftest.py` already does this.

## What this system is

A **personal-use, intraday options-trading decision-support application**. It screens for candidates, computes market/options features deterministically, asks an LLM to recognize a setup (advisory only), and — only after a separate deterministic risk layer approves — routes an order through a broker adapter (Schwab / Robinhood) or an internal paper-trading simulator.

Critical boundary to preserve in any implementation: **the LLM never places, modifies, or cancels an order.** It only emits a schema-validated advisory JSON opinion. A deterministic risk/validation layer is the sole gate between advisory output and an executable order intent, and only `APPROVED` intents may reach order management.

## Architecture (from requirements.md §4)

Four components in a strict one-way pipeline, plus shared safety/platform services:

```
Screener → Data collection & quantitative engine → State/change detection → LLM insights → Deterministic risk/validation → Order management
```

1. **Screener** — deterministic filters (price, RVOL, % move, spread, options availability) produce a ranked `CandidateSymbol` watchlist on a configurable cadence. No indicators, no LLM.
2. **Data collection & quantitative engine** — the *canonical* source of all numerical indicators. Schwab Trader API is the primary market-data source (subject to validation); Robinhood is for broker/order functionality only, not core quant data, unless explicitly validated as a fallback. All provider data is normalized into provider-neutral contracts before any feature is calculated. Computes VWAP, EMA 9/20/50 (+slopes/alignment), RSI(14), ROC, RVOL, volume acceleration, ATR(14), key levels (prior day H/L/C, premarket H/L, opening range, session H/L), SPY/QQQ/sector context, and options Greeks/IV where available. Every feature definition is versioned.
3. **State/change detection** — turns frequent feature snapshots into a small stream of material `FeatureEvent`s (VWAP cross/reclaim, EMA structure change, level touch/break, volume regime, market regime, data-quality state) with per-symbol cooldown/dedup. Only eligible events trigger an LLM call — this is the throttle that keeps LLM usage bounded.
4. **LLM insights** — pluggable `InsightProvider` interface (first implementation: Gemini Flash — app code must depend on the interface, never a hardcoded provider/model). Input is a compact, bounded context package (never raw unbounded candle streams, never credentials/account identifiers, no order-execution tool). Output must validate against a strict JSON schema (`setup_available`, `setup_type`, `direction`, `confidence`, `evidence`, `risks`, `invalidation_conditions`, `requires_human_review`, ...). Schema failure ⇒ evaluation is treated as unavailable, never as a fallback executable path.
5. **Deterministic risk/validation** — independent of both the LLM and order management. Validates data freshness, setup validity/expiry, symbol/contract eligibility, option liquidity (spread/volume/OI), position/loss/concentration/frequency limits, duplicate-intent detection, buying power, and human-approval status. Produces an immutable `RiskDecision` (`APPROVED` / `REJECTED` / `REVIEW_REQUIRED`) with every rule and reason code recorded.
6. **Order management** — `OrderBroker` adapter interface behind which Schwab and Robinhood adapters live; adapters do no indicator math and make no LLM calls. Two mutually exclusive, explicitly persisted **execution modes**:
   - `PAPER` — runs the full pipeline identically to `LIVE` but never calls a broker order API; fills are simulated internally from versioned, configurable assumptions (quote staleness, spread/slippage, fees, partial fills). Default: refuse a fill rather than invent a price when the quote is stale/missing.
   - `LIVE` — submits only approved, unexpired intents to the verified broker adapter (initial target: the user's authorized Robinhood agentic account). Disabled by default; enabling it requires explicit authenticated confirmation and shows the target broker/account alias. A kill switch blocks new live submissions without interrupting paper-mode/monitoring/reconciliation.
   Normalized order lifecycle: `CREATED → PENDING_SUBMISSION → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED/FILLED → ...`, plus `CANCEL_PENDING`, `CANCELLED`, `REJECTED`, `EXPIRED`, `UNKNOWN`. Never retry a potentially-accepted order without idempotency/reconciliation safeguards.

A correlation ID must be threaded from candidate → snapshot → event → LLM evaluation → risk decision → intent → order/fill, including rejected and suppressed paths, so any outcome (including "nothing happened") is auditable.

## Non-negotiable invariants when implementing any part of this system

- **Fail closed.** Missing/stale data, invalid LLM JSON, schema failures, ambiguous broker responses, reconciliation mismatches, or Telegram approval failures must all block execution, never proceed with a best guess. Never substitute missing numerical data with `0` — use `null` plus a quality/availability flag.
- **Execution mode is explicit, persisted, and immutable per intent** — never inferred from whether broker credentials happen to be present. `PAPER` must work with zero broker credentials.
- **Human approval (Telegram), when enabled**, gates both `PAPER` and `LIVE` identically: `RiskDecision` stays `REVIEW_REQUIRED` until an authenticated, idempotent, non-expired approval is recorded from an authorized chat/user ID.
- **Broker-specific behavior is validation-required.** Don't assume undocumented Schwab/Robinhood API capabilities (order types, streaming, rate limits, options support). Unverified operations must fail closed with a clear reason, and each adapter must isolate its provider's conventions from the rest of the app.
- **FastAPI is the only request-handling surface**; it must never block on market-data loops, LLM calls, or broker reconciliation — that work runs in durable background workers, with the API enqueuing/reporting status. All request/response/event contracts are typed (Pydantic), versioned, UTC-timestamped, and carry a source/provider field.
- Indicator definitions (VWAP session boundary, RVOL lookback, opening-range duration, timezone = `America/New_York` by default) must be explicit, versioned, and unit-tested against fixed fixtures — not implicit in code.

## Code layout (`src/trading_app/`)

- `main.py` — FastAPI app factory; `lifespan` calls `db.base.init_models()` then starts `workers.manager.WorkerManager` so request handlers never touch background work directly.
- `config.py` — `Settings` (env-backed via `pydantic-settings`, nested delimiter `__`), `ExecutionMode`, `SafetySettings` (live disabled by default).
- `schemas/` — one module per contract family from §5 (`common.py` has the shared `VersionedModel` base every contract inherits: schema version, correlation ID, UTC timestamp).
- `api/routers/` — one module per required API group from §9 (`health`, `configuration`, `candidates`, `features`, `insights`, `trade_intents`, `orders`, `paper`, `approval`, `audit`), aggregated in `api/routers/__init__.py`. Most bodies are still `TODO(Phase N)` stubs returning empty lists — `audit.py` is the one router already reading real state (SQLite via `db/base.py`).
- `workers/manager.py` — a placeholder asyncio loop per background component named in §9 (`collection`, `indicators`, `event_detection`, `llm_evaluation`, `paper_fills`, `reconciliation`, `notifications`); swap for a durable task queue before Phase 1 relies on real scheduling.
- `security/secrets.py` — `SecretsProvider` abstraction; only an env-var-backed dev implementation exists so far.

When implementing a spec component, extend the matching module above rather than introducing a parallel structure.

## Shared data contracts (requirements.md §5)

`Candle`, `Quote`, `OptionContract`, `FeatureSnapshot`, `FeatureEvent`, `SetupEvaluationRequest`/`Response`, `RiskDecision`, `ExecutionMode`, `ApprovedOrderIntent`, `OrderRecord`/`FillRecord`, `PaperAccount` — see §5 for required fields before adding or changing any of these.

## Phased delivery order (requirements.md §14)

Work is expected to land in this order; don't jump ahead of validated capabilities:

0. Validate Schwab/Robinhood capabilities; scaffold contracts, FastAPI skeleton, config, secrets, DB schema, audit log, paper-sim shell. *No implementation may depend on an unverified broker behavior.*
1. Read-only quant pipeline: screener + Schwab-backed OHLCV/benchmarks + features + state detection + activity log. No LLM, no orders yet.
2. LLM advisory insights (`InsightProvider`, Gemini Flash, schema validation, Telegram approval workflow). No order can result from LLM output alone.
3. Deterministic risk layer + internal paper-trading simulator + historical replay.
4. Verified live broker adapters, reconciliation, kill switch, constrained live sizing.
5. Hardening: threshold tuning from replay, streaming, dashboards, fallbacks.

When starting implementation, check which phase's exit criteria (§14) are already met before adding capability from a later phase.
