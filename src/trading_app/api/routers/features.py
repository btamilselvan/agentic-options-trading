"""features: snapshots and feature events (requirements.md section 9).
`/snapshots` is backed by the quantitative engine (component 2);
`/events` remains a stub for the state/change-detection layer
(component 3) — not this component's responsibility."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trading_app.api.deps import get_db
from trading_app.config import Settings, get_settings
from trading_app.db.repositories.features import (
    get_latest_snapshots_for_symbols,
    get_snapshot_history,
    save_feature_snapshot,
)
from trading_app.db.repositories.screener import get_latest_candidates
from trading_app.models.features import FeatureSnapshotRecord
from trading_app.schemas.features import FeatureEvent, FeatureSnapshot
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.factory import get_market_data_provider
from trading_app.services.quant.service import compute_snapshots_for_candidates

router = APIRouter(prefix="/features", tags=["features"])


def _record_to_schema(record: FeatureSnapshotRecord) -> FeatureSnapshot:
    return FeatureSnapshot(
        symbol=record.symbol,
        as_of=record.as_of,
        feature_definition_version=record.feature_definition_version,
        features=record.features or {},
        market_context=record.market_context or {},
        data_quality=DataFreshness(record.data_quality),
        correlation_id=UUID(record.correlation_id),
    )


@router.get("/snapshots", response_model=list[FeatureSnapshot])
async def list_snapshots(
    symbol: str | None = None, limit: int = 50, db: AsyncSession = Depends(get_db)
) -> list[FeatureSnapshot]:
    """Without `symbol`: the latest snapshot per symbol that has one.
    With `symbol`: up to `limit` most recent snapshots for that symbol."""
    records = (
        await get_snapshot_history(db, symbol, limit=limit)
        if symbol
        else await get_latest_snapshots_for_symbols(db)
    )
    return [_record_to_schema(r) for r in records]


@router.get("/events", response_model=list[FeatureEvent])
async def list_events(symbol: str | None = None) -> list[FeatureEvent]:
    # TODO(Phase 1): backed by the state/change-detection layer.
    return []


@router.post("/compute", response_model=list[FeatureSnapshot])
async def trigger_compute(
    settings: Settings = Depends(get_settings), db: AsyncSession = Depends(get_db)
) -> list[FeatureSnapshot]:
    """Force immediate feature computation for the current screener
    candidates, outside the normal background cadence
    (`workers.quant_worker`) — useful for testing/ops. Runs inline
    (blocking this request on real Schwab HTTP calls, one quote+bar
    fetch per candidate plus benchmarks, when MARKET_DATA__PROVIDER=schwab);
    move this to an enqueue-and-report-status pattern if that latency
    becomes a problem (requirements.md section 9)."""
    candidate_records = await get_latest_candidates(db)
    candidates = [(record.symbol, UUID(record.correlation_id)) for record in candidate_records]
    if not candidates:
        return []

    provider = get_market_data_provider(settings)
    snapshots = await compute_snapshots_for_candidates(candidates, provider, settings.quant_engine)
    for snapshot in snapshots:
        await save_feature_snapshot(db, snapshot)
    return snapshots
