# Personal Intraday Agentic Options-Trading Application

## 1. Purpose and boundaries

Build a personal-use application that finds liquid intraday options opportunities, computes market features deterministically, recognizes potential setups with an LLM, and manages orders through supported brokers.

The application is **decision support plus controlled execution infrastructure**. The LLM is advisory only: it may identify and explain a setup, but it must never place, modify, or cancel an order directly. A deterministic validation and risk layer must approve every proposed trade before the independent order-management component can act.

This specification deliberately does not assume undocumented Schwab or Robinhood API behavior. Any broker capability marked **validation required** must be verified against the currently authorized API, documentation, account permissions, and applicable terms before implementation depends on it.

The implementation language is Python. The application must expose its service interfaces through FastAPI endpoints; FastAPI's generated OpenAPI schema must describe request/response models and authentication requirements. Background market-data, analysis, scheduling, and reconciliation work must run outside request handlers.

## 2. Goals

- Screen a defined equity/ETF universe for intraday candidates.
- Calculate technical, volume, market-context, and options features outside the LLM from raw data.
- Detect meaningful feature/state changes so LLM calls occur only when useful.
- Ask an LLM whether a defined setup is currently present and receive machine-valid structured output with concise reasoning.
- Apply deterministic risk, liquidity, account, and order validation before execution.
- Keep market analysis, LLM analysis, risk approval, and broker order management independently testable and replaceable.
- Support Schwab and Robinhood order-management adapters without making one broker's conventions leak through the rest of the application.
- Provide two explicit, mutually exclusive execution modes: internal paper trading and live trading.
- Route live Robinhood trading through the user's authorized Robinhood agentic account once its order capabilities are validated.

## 3. Non-goals for the first release

- LLM-generated order parameters or direct broker access.
- A large library of chart indicators or predictive ML models.
- Reliance on Robinhood data as the canonical feed for quantitative analysis.
- Multi-user accounts, social trading, or public signal distribution.
- A claim that any signal is profitable or suitable for a particular user.

## 4. Architecture

The system consists of four major components plus shared safety and platform services.

```text
                    ┌────────────────────┐
                    │  1. Screener       │
                    │ candidate symbols  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ 2. Data collection │
                    │ + quantitative     │
                    │ engine             │
                    └─────────┬──────────┘
                              │ feature snapshots
                    ┌─────────▼──────────┐
                    │ State/change       │
                    │ detection          │
                    └─────────┬──────────┘
                              │ only material events
                    ┌─────────▼──────────┐
                    │ 3. LLM insights    │
                    │ advisory JSON only │
                    └─────────┬──────────┘
                              │ setup proposal
                    ┌─────────▼──────────┐
                    │ Deterministic risk │
                    │ and validation     │
                    └─────────┬──────────┘
                              │ approved intent only
                    ┌─────────▼──────────┐
                    │ 4. Order management│
                    │ Schwab / Robinhood │
                    └────────────────────┘
```

### 4.1 Component 1: Screener

**Responsibility:** produce a bounded, ranked watchlist of underlying symbols eligible for deeper collection and analysis.

The screener must:

- Operate over a configurable universe (initially liquid equities and ETFs).
- Use deterministic filters such as price, intraday volume, relative volume, percentage move, spread/liquidity proxies, options availability, and configurable exclusion lists.
- Publish a `CandidateSymbol` record with symbol, score, reasons, timestamp, and source-data freshness.
- Refresh on a configurable cadence during market hours; initial default: every 1–5 minutes.
- Persist each screening run for later audit and backtesting.

Initial screener ranking should favor liquid symbols with active options and meaningful intraday movement. Exact thresholds must be configuration, not code constants.

### 4.2 Component 2: Data collection and quantitative engine

**Responsibility:** collect raw data and calculate all numerical indicators and derived features. It is the canonical source of quantitative analysis.

#### Data-source policy

- Prefer the Schwab production Trader API as the primary source for market data, subject to validation of entitlement, coverage, rate limits, history depth, and timestamp semantics.
- Robinhood MCP tools and the unofficial Robinhood API are available primarily for broker and order functionality. Do not make them the core quantitative market-data source unless a validated fallback policy explicitly permits it.
- Normalize data from every source into provider-neutral contracts before indicators are calculated.
- Store source, received timestamp, market timestamp, and a freshness status with all externally sourced records.

#### Required initial raw-data scope

- OHLCV bars for 1-minute, 5-minute, and 15-minute intervals.
- Quote fields where available: last, bid, ask, cumulative/session volume, and timestamps.
- Daily bars sufficient to calculate previous-session levels and rolling volume baselines.
- Premarket data where available and permitted.
- Benchmark data for SPY and QQQ and a configurable sector ETF mapping.
- Options-chain/contract data where available: expiration, strike, call/put, bid, ask, last, volume, open interest, implied volatility, and Greeks.

#### Required calculated features

Compute and persist the following per symbol/timeframe as applicable:

| Family | Initial features |
|---|---|
| Trend | Session VWAP; EMA 9, 20, and 50; each EMA slope; price distance from VWAP/EMA20; EMA alignment and cross events |
| Momentum | RSI(14); rate of change (ROC), with periods configurable |
| Volume | Relative volume (RVOL); time-of-day volume comparison; volume acceleration; rolling average volume |
| Volatility | ATR(14); ATR percentage |
| Levels | Previous day high/low/close; premarket high/low; opening-range high/low; session high/low |
| Market context | SPY and QQQ trend/state; mapped sector ETF trend/state; relative movement versus benchmark where feasible |
| Options | IV, IV change, option volume, open interest, bid/ask spread, and delta/gamma/theta when available |

Definitions must be versioned and testable. For example, session VWAP needs an explicit session boundary and source-volume convention; RVOL must define its lookback and time-of-day alignment; opening range must define its duration and exchange timezone. Use America/New_York as the initial market-session timezone unless a validated instrument-specific calendar requires otherwise.

### 4.3 State and change-detection layer

**Responsibility:** convert frequent feature snapshots into a small stream of meaningful events and suppress redundant LLM calls.

The detector consumes current and previous feature snapshots and emits an event only when a configured material condition is met. It must keep per-symbol state and a cooldown/deduplication record.

Initial states and transitions:

| Domain | States/events |
|---|---|
| VWAP | `ABOVE`, `BELOW`, `CROSSING_UP`, `CROSSING_DOWN`, `RECLAIMED`, `REJECTED` |
| EMA structure | `BULLISH_ALIGNED`, `BEARISH_ALIGNED`, `MIXED`, fast/slow crossover events |
| Key levels | approaching, touched, broke above/below, reclaimed, rejected |
| Volume | normal, elevated, accelerating, climactic (thresholds configurable) |
| Market regime | trend, range, high-volatility, low-volatility, unknown |
| Data quality | fresh, stale, incomplete, invalid |

The detector must:

- Emit `FeatureEvent` records with symbol, event type, old state, new state, evidence, timestamp, feature-version, and severity.
- Trigger LLM evaluation only for eligible events, not on each data polling/streaming update.
- Apply configurable per-symbol/per-event cooldowns and coalesce duplicate events.
- Force re-evaluation when a previously identified setup becomes invalid, risk conditions change materially, or data freshness degrades.
- Record suppressed events and the suppression reason for observability.

### 4.4 Component 3: LLM insights

**Responsibility:** recognize whether an already-defined intraday setup appears to be available, explain the evidence and counter-evidence, and return structured advisory output.

The LLM receives a compact, normalized context package—not raw unbounded candle streams—and must never receive credentials, account identifiers, or a tool that can execute orders.

Use a pluggable provider interface. The first implementation may use Gemini Flash, but application code must depend on an interface such as `InsightProvider`, not a provider/model name. Provider selection, model name, timeout, retry policy, and spend limits must be configuration.

#### LLM input contract

`SetupEvaluationRequest` must include:

- Request ID, feature/event version, event timestamp, symbol, and source freshness.
- The triggering `FeatureEvent` and its evidence.
- Current feature snapshot and a bounded recent history for relevant changes.
- Market and sector context.
- A compact list of liquid candidate options contracts when options selection is in scope; otherwise state that contract selection is unavailable.
- A versioned catalog of permitted setup types and the JSON schema required for output.
- Explicit instruction that output is advisory and cannot issue an order.

#### Required LLM output contract

Validate output against a strict JSON schema. On schema failure, treat the evaluation as unavailable; do not attempt execution.

```json
{
  "request_id": "uuid",
  "setup_available": true,
  "setup_type": "vwap_reclaim | opening_range_breakout | trend_continuation | none",
  "direction": "bullish | bearish | neutral",
  "confidence": 0.0,
  "time_horizon_minutes": 0,
  "evidence": ["short, feature-grounded item"],
  "risks": ["short, feature-grounded item"],
  "invalidation_conditions": ["observable price or state condition"],
  "data_quality_concerns": ["optional concern"],
  "requires_human_review": true
}
```

Human approval is a configurable risk-policy control. The initial configuration may run without human approval after deterministic risk approval; if enabled, an approval must be delivered and resolved through the configured Telegram channel before an intent is eligible for live submission. Any change to unattended live execution requires an explicit configuration change and independently tested risk policy.

The LLM must not provide broker-specific commands, make profitability claims, invent data, or override deterministic risk failures. Persist prompt version, model/provider identifier, response, validation result, latency, and estimated cost/token usage where available.

### 4.5 Deterministic risk and validation layer

**Responsibility:** decide whether an advisory setup may become an order intent. This is separate from both LLM insights and order management.

At minimum, validate:

- Feature data freshness and completeness.
- The setup is currently valid and has not expired.
- Symbol and contract eligibility (allowlists/blocklists, tradability, supported instrument type).
- Option contract liquidity: maximum configurable bid/ask spread, minimum volume/open interest where data exists, and valid quote.
- Position-size, premium-at-risk, daily-loss, open-position, concentration, and order-frequency limits.
- Duplicate/conflicting intent detection.
- Account/broker buying power and order constraints, once capability is validated.
- Human approval status when required.

The result must be an immutable `RiskDecision` of `APPROVED`, `REJECTED`, or `REVIEW_REQUIRED`, including every rule evaluated, its inputs, and reason codes. Only `APPROVED` intents may be sent to order management.

### 4.6 Component 4: Order management

**Responsibility:** independently route approved intents, track lifecycle state, reconcile broker state, and provide a broker-neutral audit trail.

Implement provider adapters behind an `OrderBroker` interface. Initial adapters are Schwab and Robinhood, enabled only after their required capabilities are validated. The component must not calculate indicators or ask the LLM for a decision.

### Execution modes

The selected execution mode is an explicit, persisted configuration value on every order intent and order record. It must never be inferred from the availability of credentials.

| Mode | Behavior |
|---|---|
| `PAPER` | Run the same screening, quantitative analysis, state detection, LLM advisory, deterministic risk validation, and configured human-approval workflow as `LIVE`. Do not submit any broker order or call a broker order endpoint. After approval (if enabled), use the application's internal simulation engine to simulate order lifecycle, fills, positions, cash/buying power, realized/unrealized P&L, fees, and slippage from recorded/current market data. |
| `LIVE` | Submit only an approved, unexpired intent to the explicitly selected, verified broker adapter. Initial intended live route is the user's authorized Robinhood agentic account. |

Neither Robinhood nor Schwab is assumed to provide paper trading. `PAPER` is therefore an internal broker-neutral simulator, not a broker sandbox. It differs from `LIVE` only at the final broker-submission boundary: all upstream analysis, risk, approval, and audit controls must be exercised in paper mode. Schwab and Robinhood adapters are live-routing integrations only unless a verified capability changes this policy.

Paper-fill assumptions must be versioned, configurable, and disclosed on each fill. At minimum configure fill pricing rules, maximum quote age, bid/ask spread treatment, slippage, commissions/fees, partial-fill behavior, and whether an order may fill when market data is unavailable. The default must fail a paper fill when its required quote is stale or missing rather than inventing a favorable price.

Mode changes require an authenticated administrative action and audit record. Live mode must be disabled by default; changing to `LIVE` must require an explicit confirmation and show the target broker/account alias. A kill switch must block new live submissions without interrupting paper-mode replay and monitoring.

Required behavior:

- Accept only validated `ApprovedOrderIntent` objects carrying an idempotency key and risk-decision reference.
- Implement internal paper-mode simulation without broker credentials or broker API calls.
- Validate broker capability and account state immediately before submission.
- Submit, cancel, replace, and query orders only where the selected, verified broker adapter supports each operation.
- Track normalized lifecycle states: `CREATED`, `PENDING_SUBMISSION`, `SUBMITTED`, `ACKNOWLEDGED`, `PARTIALLY_FILLED`, `FILLED`, `CANCEL_PENDING`, `CANCELLED`, `REJECTED`, `EXPIRED`, `UNKNOWN`.
- Reconcile broker-reported orders, fills, positions, and balances on a schedule and after state changes.
- Never retry a potentially accepted order without idempotency/reconciliation safeguards.

Broker-specific API details—including available order types, options support, streaming, quote coverage, authentication, rate limits, and order-status semantics—are **validation required**. Build adapters so unsupported operations fail closed with a clear reason.

## 5. Shared data contracts

All contracts must use typed schemas (for example, JSON Schema plus generated/runtime types), version fields, UTC timestamps, a provider/source field, and correlation IDs.

Minimum entities:

- `Candle`: symbol, interval, open/high/low/close/volume, market timestamp, source.
- `Quote`: symbol or option contract ID, bid/ask/last, sizes if available, market timestamp, source, freshness.
- `OptionContract`: underlying, expiration, strike, right, contract identifier, quote, IV/Greeks/volume/OI availability flags.
- `FeatureSnapshot`: symbol, as-of timestamp, calculated features, market/sector context, data-quality status, feature-definition version.
- `FeatureEvent`: described in section 4.3.
- `SetupEvaluationRequest` and `SetupEvaluationResponse`: described in section 4.4.
- `RiskDecision`: described in section 4.5.
- `ExecutionMode`: `PAPER` or `LIVE`, recorded at intent creation and immutable thereafter.
- `ApprovedOrderIntent`: execution mode, broker target (required only for `LIVE`), contract, side, quantity, allowed order parameters, idempotency key, approval references, expiry.
- `OrderRecord` and `FillRecord`: normalized broker lifecycle records with raw provider payload retained securely for audit.
- `PaperAccount`: starting/effective cash, buying power, positions, realized/unrealized P&L, simulator-assumption version, and reset/replay provenance.

No contract may silently substitute missing numerical data with zero. Use `null` plus availability/quality metadata.

## 6. Event flow

1. Scheduler/stream consumer runs the screener and produces candidate symbols.
2. Data collector obtains normalized raw data for candidates, benchmarks, sector ETFs, and relevant options contracts.
3. Quantitative engine calculates and stores feature snapshots.
4. State detector compares snapshots, persists state, and emits only material `FeatureEvent`s.
5. Eligible events request an LLM setup evaluation.
6. Schema-validated advisory output is stored and sent to deterministic risk validation.
7. If human review is enabled, in either execution mode, send the setup, evidence, risks, and proposed intent to the configured Telegram channel and await an authenticated approve/reject decision; otherwise apply the configured policy.
8. Only an approved, unexpired intent reaches the selected order-management adapter.
9. Order management simulates the lifecycle in `PAPER` mode or submits/reconciles it with the selected live broker in `LIVE` mode, then publishes updates to the audit log and user interface.

Every step must preserve a correlation ID from candidate through order/fill, including rejected and suppressed paths.

## 7. Storage and retention

Use a durable relational database for configuration, entities, decisions, orders, fills, audit records, and feature snapshots. Use a time-series-friendly table/indexing strategy or a dedicated time-series store when volume warrants it. A lightweight queue/event bus is recommended for component boundaries; an in-process implementation is acceptable initially only if event records are durable and replayable.

Persist:

- Raw normalized data needed to reproduce feature calculations, subject to provider licensing/retention terms.
- Feature snapshots/events and feature-definition versions.
- Prompts, LLM responses, schema validation, risk decisions, approvals, and provider/model versions.
- Broker submission/reconciliation records and immutable audit history.
- Configuration versions and user actions.

Define retention windows by data class in configuration. Sensitive credentials and tokens must never be stored in application logs or plain database columns.

## 8. Scheduling, streaming, and freshness

- Design collection behind a common interface supporting polling first and streaming later.
- Initial cadence should be configurable by data type: e.g., bar completion, quote updates, screening refresh, and broker reconciliation.
- Align bar calculation to interval close; avoid evaluating incomplete bars as closed bars unless explicitly marked provisional.
- Define freshness thresholds for quotes, bars, options data, and account state. Stale or incomplete data must block risk approval and be visible to the user.
- Use an exchange calendar and handle premarket, regular session, after-hours, weekends, market holidays, early closes, and daylight-saving changes.
- Apply provider-specific rate limiting, exponential backoff with jitter, and circuit breakers.

## 9. API and application implementation requirements

Implement the backend in Python using FastAPI. Use Pydantic models (or the FastAPI-compatible equivalent) for every API input/output and shared event contract; reject invalid payloads with explicit validation errors.

Required API groups (exact paths may vary):

- `health`: readiness, liveness, dependency/data-source status, and current safety state.
- `configuration`: read/update versioned screener, risk, execution-mode, and provider configuration; live-mode changes must use a separate protected action.
- `candidates` and `features`: current/historical screener results, snapshots, and feature events.
- `insights`: LLM evaluations, schema-validation results, and decision trail.
- `trade-intents` and `orders`: create/read/cancel permitted intents and view normalized order/fill lifecycle. Create operations must enforce risk policy server-side, never trust a client-provided approval value.
- `paper`: paper account balance, positions, orders, fills, P&L, reset/replay controls, and simulator assumptions.
- `approval`: pending and resolved approvals. Telegram callbacks/webhooks, if used, must be authenticated and idempotent.
- `audit`: filtered, read-only correlation timeline for a candidate, setup, intent, order, or fill.

Run durable background workers for collection, indicator calculation, event detection, LLM evaluation, paper fills, broker reconciliation, and notifications. API request handlers may enqueue work and report status but must not block on market loops, LLM calls, or broker reconciliation. Use a configurable task queue/worker mechanism with durable retry records; the exact library may be selected during implementation.

### Telegram approval workflow

When `human_approval_enabled` is `true`, the risk result must be `REVIEW_REQUIRED` until a valid Telegram decision is recorded. The notification must contain the correlation ID, execution mode, symbol/contract, side/quantity, risk summary, setup evidence, invalidation conditions, expiry time, and approve/reject controls or equivalent commands.

Only configured Telegram chat IDs and authorized user IDs may approve/reject. Verify webhook authenticity where supported, protect any callback payload against tampering, and make each decision idempotent. Expired, ambiguous, unauthorized, or unavailable Telegram approvals must fail closed: no order submission or paper-fill simulation. Store the delivery status and the approver identity/time in the audit log. Paper mode must use the same approval configuration and workflow as live mode.

## 10. Observability and auditability

Provide structured logs, metrics, traces/correlation IDs, and a user-visible activity timeline.

Minimum metrics:

- Data freshness/lag and provider error/rate-limit counts.
- Screened candidates, emitted/suppressed events, and LLM-call rate.
- LLM latency, schema failures, provider failures, and token/cost estimates when available.
- Risk approvals/rejections by reason code.
- Order submission latency, rejections, fill lifecycle, reconciliation mismatches, and adapter health.
- Current execution mode, mode changes, paper-fill assumptions, Telegram approval delivery/response status, and blocked live submissions.

Alert or prominently surface stale data, broker reconciliation discrepancies, failed order actions, abnormal LLM error rates, and breached risk limits. Audit records must make it possible to reconstruct why no action, review, rejection, or order occurred.

## 11. Security and operational safety

- Use a secrets manager or OS-backed secret storage; never commit credentials.
- Apply least-privilege broker scopes; paper mode must operate without broker credentials, and live credentials/configuration must be separately protected.
- Encrypt sensitive data at rest and in transit as appropriate to the deployment environment.
- Require explicit confirmation and a clearly visible live-trading mode switch before live orders can be enabled.
- Make live execution disabled by default.
- Redact secrets, tokens, account identifiers, and sensitive provider payloads from logs and LLM prompts.
- Implement a kill switch that immediately prevents new submissions while preserving monitoring, reconciliation, cancellation (where supported), and audit access.

## 12. Failure handling

Fail closed for execution. Examples:

- Missing/stale market, options, or account data → no risk approval.
- Invalid LLM JSON, timeout, hallucinated/unrecognized setup, or provider outage → record failure; do not create executable intent.
- State-store or database outage → stop new analysis/execution and alert.
- Ambiguous broker submission result → mark `UNKNOWN`, reconcile before retrying.
- Rate limit/provider outage → back off; display degraded data-source status; use a validated fallback only if enabled.
- Reconciliation mismatch → block new orders for the affected broker/account according to policy and require review.
- Telegram approval delivery/callback failure while approval is enabled → retain/reject the intent on expiry; do not submit a live order.
- Paper simulator data gap → retain the order pending only if a configured expiry permits it; otherwise reject/expire it and record the reason.

All retries must be bounded, observable, and idempotent where an external side effect is possible.

## 13. Testing and backtesting

### Automated testing

- Unit-test every indicator against fixed, hand-checked fixtures, including session boundaries and missing data.
- Unit-test state transitions, cooldowns, deduplication, and invalidation events.
- Contract-test provider adapters against recorded/sandbox responses; never use live trading as an integration test.
- Validate all LLM output with JSON-schema tests, malformed output tests, and provider-timeout tests.
- Test every risk rule, including boundary values and fail-closed behavior.
- Test order idempotency, ambiguous-submit handling, lifecycle transitions, and reconciliation.
- Test paper-mode fills, P&L, partial fills, slippage/spread assumptions, stale-quote refusal, mode isolation, and prevention of broker calls in `PAPER` mode.
- Test Telegram authorization, webhook/callback authenticity, duplicate callback handling, expiry, and fail-closed approval behavior.

### Historical replay/backtesting

Build a replay harness that feeds timestamped historical bars/quotes/options data through the same indicator and state-detection logic used in production. It must prevent look-ahead bias, record the feature/version configuration, model assumptions, estimated spreads/slippage/fees, and all risk-policy decisions.

Backtests must report both signal quality and operational behavior: event frequency, LLM-call volume, rejected intent reasons, fills under stated assumptions, maximum drawdown, and sensitivity to parameter changes. Historical options data availability and quality are **validation required**; do not present results as realistic if required options inputs are absent.

## 14. Phased delivery plan

### Phase 0 — capability validation and foundation

- Verify authorized Schwab and Robinhood capabilities, data entitlements, rate limits, authentication, account/order support, and terms applicable to intended use. Confirm Robinhood agentic-account order-routing capabilities before enabling `LIVE` mode.
- Document each verified capability and its source; mark unsupported capabilities explicitly.
- Create typed provider-neutral contracts, FastAPI application skeleton/OpenAPI contract, configuration system, secrets handling, database schema, audit log, and internal paper-simulation mode.

**Exit criteria:** no implementation decision relies on an unverified broker-specific behavior.

### Phase 1 — read-only quantitative pipeline

- Implement configurable universe/screener.
- Ingest Schwab-backed (if validated) 1m/5m/15m OHLCV and benchmark data.
- Calculate and persist initial non-options features, levels, context, and data-quality status.
- Implement state/change detection and an activity view/log; no LLM and no broker order actions.

**Exit criteria:** feature values and events pass fixtures and can be replayed deterministically.

### Phase 2 — LLM advisory insights

- Implement `InsightProvider` and Gemini Flash configuration as the initial provider option.
- Implement compact request construction, strict JSON validation, prompt/response audit, cost controls, and configurable Telegram human-approval workflow.
- Add options data and contract-liquidity context only after verified availability.

**Exit criteria:** LLM output is schema-valid or safely rejected; no code path can submit an order from LLM output alone.

### Phase 3 — deterministic risk and simulated execution

- Implement risk rules, approval workflow, expiration, duplicate controls, and internal paper-trading simulator.
- Replay historical and simulated real-time scenarios; measure data freshness, event volume, and risk decisions.

**Exit criteria:** every simulated order has an auditable feature event, advisory result, risk decision, approval state, and lifecycle.

### Phase 4 — verified live broker adapters

- Implement Schwab and/or Robinhood order adapters only for verified operations.
- Add reconciliation, kill switch, operational alerts, and limited live-mode controls.
- Begin with constrained sizing. Enable Telegram approval if configured; otherwise allow only the explicitly configured unattended policy to proceed after deterministic validation.

**Exit criteria:** broker lifecycle and account reconciliation behave correctly through failure/ambiguity scenarios in the supported environment.

### Phase 5 — hardening and iteration

- Tune screen/risk/state thresholds using replay results.
- Add validated streaming paths, resilience improvements, dashboards, and provider fallbacks.
- Consider reduced-human-intervention modes only after explicit policy decisions, tests, and operational review.

## 15. Acceptance criteria for the initial implementation

- A candidate symbol can be traced from screen result through feature snapshots and state events.
- VWAP, EMA 9/20/50, RSI, ROC, RVOL/time-of-day comparison, volume acceleration, ATR, key levels, and market context are calculated outside the LLM from versioned data inputs.
- The LLM is called only from eligible change events and returns validated JSON advisory output.
- Invalid/stale data and invalid LLM output cannot produce an executable order intent.
- Every proposed trade in either mode undergoes deterministic risk validation; human review follows the configured policy and, when enabled, must complete through an authorized Telegram approval before a paper fill or live submission can proceed.
- Paper mode never calls a broker order API and produces an auditable simulated order/fill/P&L lifecycle using versioned assumptions.
- Live mode is disabled by default, records an explicit mode selection, and can route only validated intents through a verified broker adapter; the initial intended target is the Robinhood agentic account.
- FastAPI exposes documented, typed endpoints while durable background workers perform collection, evaluation, simulated fills, notifications, and reconciliation.
- Schwab and Robinhood functionality is isolated behind adapters; every broker-dependent behavior is either verified or fails closed as unsupported.
- Logs/audit records reconstruct the full decision and order lifecycle using correlation IDs.
