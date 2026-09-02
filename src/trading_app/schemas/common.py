"""Base types shared by every contract (requirements.md section 5)."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class VersionedModel(BaseModel):
    """Common fields required on every shared contract: a schema version, a
    UTC creation timestamp, and a correlation ID for end-to-end tracing
    (requirements.md section 6)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    correlation_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utcnow)
