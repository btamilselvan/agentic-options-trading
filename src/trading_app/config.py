"""Application configuration.

Settings are loaded from environment variables (and an optional .env file for
local development), using `__` as the nested-field delimiter (e.g.
`SAFETY__LIVE_TRADING_ENABLED`). Nothing here ever holds a live secret value
directly — see `trading_app.security.secrets` for how credential material is
resolved.
"""
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionMode(StrEnum):
    """Mutually exclusive execution modes (requirements.md sections 4.6, 5)."""

    PAPER = "PAPER"
    LIVE = "LIVE"


class Environment(StrEnum):
    """Deployment environment. Gates dev-only conveniences that must never
    reach production: interactive API docs UI, verbose debug tracebacks,
    uvicorn autoreload, and log format (see main.py, logging_config.py).
    Independent of ExecutionMode/SafetySettings — this is about the
    deployment, not trading behavior."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseSettings(BaseModel):
    """Any SQLAlchemy-async-compatible URL works here — Supabase (or any
    other Postgres) via `postgresql+asyncpg://...`, or SQLite via
    `sqlite+aiosqlite:///...` for a zero-dependency local fallback. Schema
    is managed by Alembic (see migrations/), not by this application at
    runtime — run `alembic upgrade head` before starting the app. All
    tables use the `ot_` prefix so this database can be shared safely with
    other projects (requirements.md's storage guidance doesn't mandate a
    specific engine; Supabase is just Postgres underneath)."""

    url: str = "sqlite+aiosqlite:///./trading_app.db"
    echo: bool = False


class TelegramSettings(BaseModel):
    bot_token: str | None = None
    allowed_chat_ids: list[int] = Field(default_factory=list)
    webhook_secret: str | None = None


class LLMSettings(BaseModel):
    """Provider-neutral LLM configuration. Application code must depend on
    the `InsightProvider` interface (trading_app.services.insights), never
    on a concrete provider/model name (requirements.md section 4.4).

    Switch providers with `LLM__PROVIDER` alone — no code change required:

    - `LLM__PROVIDER=gemini`, `LLM__MODEL_NAME=gemini-2.5-flash` (verify the
      model name against the currently available Gemini API models); needs
      a `GEMINI_API_KEY` resolved via `trading_app.security.secrets`.
    - `LLM__PROVIDER=ollama`, `LLM__MODEL_NAME=<model you've pulled locally>`
      (e.g. `llama3.1`); talks to `LLM__OLLAMA_BASE_URL`, no API key needed.
    """

    provider: str = "gemini"
    model_name: str = "gemini-2.5-flash"
    ollama_base_url: str = "http://localhost:11434"
    timeout_seconds: float = 15.0
    max_retries: int = 2
    daily_spend_limit_usd: float = 5.0


class SafetySettings(BaseModel):
    """Live-trading safety posture. Live trading is disabled by default and
    must require an explicit, separately protected configuration change to
    enable (requirements.md sections 4.6, 11)."""

    default_execution_mode: ExecutionMode = ExecutionMode.PAPER
    live_trading_enabled: bool = False
    human_approval_enabled: bool = True
    kill_switch_engaged: bool = False


class MarketDataSettings(BaseModel):
    """Provider-neutral market-data configuration
    (trading_app.services.market_data). `static` is a deterministic,
    dev-only fixture; `schwab` calls the real Schwab Trader API
    (requirements.md sections 1, 4.2) using the OAuth token bootstrapped by
    `scripts/bootstrap_schwab_oauth.py`."""

    provider: str = "static"
    # Requirements.md section 8: "Define freshness thresholds for quotes,
    # bars, options data, and account state." A quote older than this is
    # STALE, not FRESH — applies to real providers (schwab); the static
    # fixture always stamps "now" so this never bites it.
    max_quote_age_seconds: float = 900.0


class UniverseSettings(BaseModel):
    """Screener universe *discovery* (requirements.md section 4.1's
    "configurable universe") — separate from ScreenerSettings, which owns
    filtering/scoring/cadence once a universe is in hand. Application code
    depends only on the `UniverseProvider` interface
    (trading_app.services.universe), never a concrete provider.

    - `UNIVERSE__PROVIDER=static` (default) — screens exactly
      `ScreenerSettings.universe`, unchanged from Phase 1's original
      fixed-list behavior.
    - `UNIVERSE__PROVIDER=schwab_movers` — dynamically discovers symbols
      each cycle from Schwab's real top-gainers/losers/most-active data
      (`GET /marketdata/v1/movers/{index}`, top 10 per index/sort
      combination — combine several to cover more of the market)."""

    provider: str = "static"
    schwab_movers_indices: list[str] = Field(default_factory=lambda: ["equity_all"])
    schwab_movers_sort_orders: list[str] = Field(
        default_factory=lambda: ["percent_change_up", "percent_change_down", "volume"]
    )
    max_dynamic_symbols: int = 60
    # Always screened in addition to whatever the provider discovers (e.g.
    # benchmarks that may not naturally show up as "movers"); empty by
    # default so `static` mode isn't surprised by symbols it didn't ask for.
    always_include: list[str] = Field(default_factory=list)


class ScreenerSettings(BaseModel):
    """Screener thresholds, weights, and cadence (requirements.md section
    4.1). Every value here is configuration, never a code constant —
    that's the point: retune without a deploy. `universe` is read only
    when `UNIVERSE__PROVIDER=static` (see UniverseSettings) — the dynamic
    provider ignores it."""

    universe: list[str] = Field(
        default_factory=lambda: [
            "AAPL",
            "MSFT",
            "NVDA",
            "AMZN",
            "GOOGL",
            "META",
            "TSLA",
            "AMD",
            "SPY",
            "QQQ",
        ]
    )
    exclusions: list[str] = Field(default_factory=list)

    # Deterministic filters (requirements.md section 4.1).
    min_price: float = 5.0
    max_price: float = 1000.0
    min_session_volume: float = 500_000.0
    min_rvol: float = 1.2
    min_abs_percent_move: float = 0.01
    max_spread_pct: float = 0.005
    require_options: bool = True

    # Ranking weights — favor liquid, actively-moving symbols with options.
    weight_rvol: float = 1.0
    weight_move: float = 1.0
    weight_spread: float = 0.5
    weight_options_bonus: float = 0.5

    max_candidates: int = 20
    refresh_interval_seconds: int = 1200
    market_hours_only: bool = True


class Settings(BaseSettings):
    """Root application settings, assembled from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "agentic-options-trading"
    environment: Environment = Environment.DEVELOPMENT
    api_prefix: str = "/api/v1"
    secrets_backend: str = "env"

    # Schwab OAuth (schwab-py). client_id/client_secret come from your
    # approved app at developer.schwab.com; callback_url must exactly
    # match the app's registered callback URL (HTTPS, per Schwab). See
    # scripts/bootstrap_schwab_oauth.py for the one-time interactive
    # consent flow that produces the token file at schwab_token_path, and
    # scripts/refresh_schwab_token.py for a no-browser refresh.
    schwab_client_id: str | None = None
    schwab_client_secret: str | None = None
    schwab_callback_url: str = "https://127.0.0.1:8182"
    schwab_token_path: str = ".secrets/schwab_token.json"

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    market_data: MarketDataSettings = Field(default_factory=MarketDataSettings)
    screener: ScreenerSettings = Field(default_factory=ScreenerSettings)
    universe: UniverseSettings = Field(default_factory=UniverseSettings)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor; use as a FastAPI dependency."""
    return Settings()
