"""Persistence for screener runs and their candidates (requirements.md
section 4.1: "Persist each screening run for later audit and
backtesting")."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_app.models.screener import CandidateSymbolRecord, ScreenerRunRecord
from trading_app.services.screener.service import ScreenResult


async def save_screen_result(session: AsyncSession, result: ScreenResult) -> None:
    session.add(
        ScreenerRunRecord(
            id=result.run_id,
            started_at=result.started_at,
            completed_at=result.completed_at,
            universe_size=result.universe_size,
            candidate_count=len(result.candidates),
            market_data_provider=result.market_data_provider,
        )
    )
    # ScreenerRunRecord/CandidateSymbolRecord have no ORM relationship()
    # between them (just a raw FK column), so the unit-of-work has no
    # dependency processor to order their inserts automatically — flush
    # the parent row explicitly before adding children that reference it,
    # or a strict-FK backend (Postgres) can insert them out of order.
    # SQLite doesn't enforce FK constraints by default, which is exactly
    # why this went unnoticed until a real Postgres database hit it.
    await session.flush()
    for candidate in result.candidates:
        session.add(
            CandidateSymbolRecord(
                run_id=result.run_id,
                symbol=candidate.symbol,
                score=candidate.score,
                reasons=candidate.reasons,
                as_of=candidate.as_of,
                source_freshness=candidate.source_freshness.value,
                correlation_id=str(candidate.correlation_id),
            )
        )
    await session.commit()


async def get_latest_run_id(session: AsyncSession) -> str | None:
    stmt = select(ScreenerRunRecord.id).order_by(ScreenerRunRecord.started_at.desc()).limit(1)
    return (await session.execute(stmt)).scalars().first()


async def get_candidates_for_run(
    session: AsyncSession, run_id: str
) -> list[CandidateSymbolRecord]:
    stmt = (
        select(CandidateSymbolRecord)
        .where(CandidateSymbolRecord.run_id == run_id)
        .order_by(CandidateSymbolRecord.score.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_latest_candidates(session: AsyncSession) -> list[CandidateSymbolRecord]:
    latest_run_id = await get_latest_run_id(session)
    if latest_run_id is None:
        return []
    return await get_candidates_for_run(session, latest_run_id)


async def list_recent_runs(session: AsyncSession, limit: int = 20) -> list[ScreenerRunRecord]:
    stmt = select(ScreenerRunRecord).order_by(ScreenerRunRecord.started_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
