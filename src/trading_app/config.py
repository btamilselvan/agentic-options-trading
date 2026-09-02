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


class DatabaseSettings(BaseModel):
    url: str = "sqlite+aiosqlite:///./trading_app.db"
    echo: bool = False


class TelegramSettings(BaseModel):
    bot_token: str | None = None
    allowed_chat_ids: list[int] = Field(default_factory=list)
    webhook_secret: str | None = None


class LLMSettings(BaseModel):
    """Provider-neutral LLM configuration. Application code must depend on
    the `InsightProvider` interface, never on a concrete provider/model name
    (requirements.md section 4.4)."""

    provider: str = "gemini_flash"
    model_name: str = "gemini-flash"
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


class Settings(BaseSettings):
    """Root application settings, assembled from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "agentic-options-trading"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    secrets_backend: str = "env"

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor; use as a FastAPI dependency."""
    return Settings()
