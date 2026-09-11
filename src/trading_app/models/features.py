"""Feature-snapshot persistence (requirements.md section 4.2) — one row
per computed snapshot. Deliberately no FK to `ot_candidate_symbols`: the
relationship is logical/audit-only via `correlation_id`, and snapshots
should be able to outlive pruned candidate rows — avoids repeating the
FK-ordering bug fixed in the screener tables.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from trading_app.db.base import Base


class FeatureSnapshotRecord(Base):
    __tablename__ = "ot_feature_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_definition_version: Mapped[str] = mapped_column(String(16))
    features: Mapped[dict] = mapped_column(JSON)
    market_context: Mapped[dict] = mapped_column(JSON)
    data_quality: Mapped[str] = mapped_column(String(16))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
