"""candidates: current/historical screener results (requirements.md
section 9)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from trading_app.api.deps import get_db
from trading_app.config import Settings, get_settings
from trading_app.db.repositories.screener import (
    get_candidates_for_run,
    get_latest_candidates,
    list_recent_runs,
    save_screen_result,
)
from trading_app.models.screener import CandidateSymbolRecord, ScreenerRunRecord
from trading_app.schemas.candidates import CandidateSymbol
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.market_data.factory import get_market_data_provider
from trading_app.services.screener.service import ScreenResult, run_screen
from trading_app.services.universe.factory import get_universe_provider

router = APIRouter(prefix="/candidates", tags=["candidates"])


class ScreenerRunSummary(BaseModel):
    run_id: str
    started_at: str
    completed_at: str
    universe_size: int
    candidate_count: int
    market_data_provider: str


def _record_to_schema(record: CandidateSymbolRecord) -> CandidateSymbol:
    return CandidateSymbol(
        symbol=record.symbol,
        score=record.score,
        reasons=record.reasons or [],
        as_of=record.as_of,
        source_freshness=DataFreshness(record.source_freshness),
        run_id=record.run_id,
        correlation_id=UUID(record.correlation_id),
    )


def _run_to_summary(run: ScreenerRunRecord) -> ScreenerRunSummary:
    return ScreenerRunSummary(
        run_id=run.id,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat(),
        universe_size=run.universe_size,
        candidate_count=run.candidate_count,
        market_data_provider=run.market_data_provider,
    )


def _result_to_summary(result: ScreenResult) -> ScreenerRunSummary:
    return ScreenerRunSummary(
        run_id=result.run_id,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat(),
        universe_size=result.universe_size,
        candidate_count=len(result.candidates),
        market_data_provider=result.market_data_provider,
    )


@router.get("", response_model=list[CandidateSymbol])
async def list_candidates(
    run_id: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[CandidateSymbol]:
    """Defaults to the most recent screening run; pass `run_id` (from
    `GET /candidates/runs`) for a historical one."""
    records = (
        await get_candidates_for_run(db, run_id) if run_id else await get_latest_candidates(db)
    )
    return [_record_to_schema(r) for r in records]


@router.get("/runs", response_model=list[ScreenerRunSummary])
async def list_runs(
    limit: int = 20, db: AsyncSession = Depends(get_db)
) -> list[ScreenerRunSummary]:
    runs = await list_recent_runs(db, limit=limit)
    return [_run_to_summary(r) for r in runs]


@router.post("/run", response_model=ScreenerRunSummary)
async def trigger_screen(
    settings: Settings = Depends(get_settings), db: AsyncSession = Depends(get_db)
) -> ScreenerRunSummary:
    """Force an immediate screening run outside the normal background
    cadence (`workers.screener_worker`) — useful for testing/ops. Runs
    inline (blocking this request on real Schwab HTTP calls when
    MARKET_DATA__PROVIDER=schwab); move this to an enqueue-and-report-status
    pattern if that latency becomes a problem (requirements.md section 9)."""
    market_data_provider = get_market_data_provider(settings)
    universe_provider = get_universe_provider(settings)
    result = await run_screen(
        settings.screener,
        market_data_provider,
        universe_provider,
        provider_name=settings.market_data.provider,
        always_include=settings.universe.always_include,
    )
    await save_screen_result(db, result)
    return _result_to_summary(result)
