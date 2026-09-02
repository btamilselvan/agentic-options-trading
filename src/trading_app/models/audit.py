"""Audit-trail ORM model (requirements.md section 10)."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from trading_app.db.base import Base
from trading_app.schemas.common import utcnow


class AuditRecord(Base):
    # All application tables are prefixed "ot_" (see CLAUDE.md) so this
    # database can be safely shared with other projects.
    __tablename__ = "ot_audit_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    stage: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(String(512))
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
