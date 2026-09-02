"""features: snapshots and feature events (requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter

from trading_app.schemas.features import FeatureEvent, FeatureSnapshot

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/snapshots", response_model=list[FeatureSnapshot])
async def list_snapshots(symbol: str | None = None) -> list[FeatureSnapshot]:
    # TODO(Phase 1): backed by the quantitative engine's persisted snapshots.
    return []


@router.get("/events", response_model=list[FeatureEvent])
async def list_events(symbol: str | None = None) -> list[FeatureEvent]:
    # TODO(Phase 1): backed by the state/change-detection layer.
    return []
