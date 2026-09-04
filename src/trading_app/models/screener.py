"""Screener persistence — one row per run, one row per surviving candidate
(requirements.md section 4.1: "Persist each screening run for later audit
and backtesting")."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from trading_app.db.base import Base


class ScreenerRunRecord(Base):
    __tablename__ = "ot_screener_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    universe_size: Mapped[int] = mapped_column(Integer)
    candidate_count: Mapped[int] = mapped_column(Integer)
    market_data_provider: Mapped[str] = mapped_column(String(64))


class CandidateSymbolRecord(Base):
    __tablename__ = "ot_candidate_symbols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("ot_screener_runs.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list] = mapped_column(JSON)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_freshness: Mapped[str] = mapped_column(String(16))
    correlation_id: Mapped[str] = mapped_column(String(36))
