"""candidates: current/historical screener results (requirements.md
section 9)."""
from __future__ import annotations

from fastapi import APIRouter

from trading_app.schemas.common import VersionedModel

router = APIRouter(prefix="/candidates", tags=["candidates"])


class CandidateSymbol(VersionedModel):
    symbol: str
    score: float
    reasons: list[str] = []
    source_freshness: str = "unknown"


@router.get("", response_model=list[CandidateSymbol])
async def list_candidates() -> list[CandidateSymbol]:
    # TODO(Phase 1): backed by the screener's persisted run output.
    return []
