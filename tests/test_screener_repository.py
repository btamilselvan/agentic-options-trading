"""Regression test for a real bug: ScreenerRunRecord/CandidateSymbolRecord
have no ORM relationship() between them (only a raw FK column), so
without an explicit flush the unit-of-work isn't guaranteed to insert the
parent run row before its children — SQLite silently allowed this (no FK
enforcement by default), Postgres correctly rejected it with a
ForeignKeyViolationError. `db/base.py` now turns SQLite FK enforcement on
so this is reproducible here without a real Postgres database.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio

from trading_app.db.base import get_session_factory, init_models
from trading_app.db.repositories.screener import get_candidates_for_run, save_screen_result
from trading_app.schemas.candidates import CandidateSymbol
from trading_app.schemas.market_data import DataFreshness
from trading_app.services.screener.service import ScreenResult


@pytest_asyncio.fixture
async def db_ready():
    await init_models()


async def test_save_screen_result_persists_candidates_with_valid_run_fk(db_ready):
    now = datetime.now(UTC)
    run_id = "regression-test-run"
    result = ScreenResult(
        run_id=run_id,
        started_at=now,
        completed_at=now,
        universe_size=1,
        market_data_provider="fake",
        candidates=[
            CandidateSymbol(
                symbol="REGRESSION",
                score=1.0,
                reasons=["x"],
                as_of=now,
                source_freshness=DataFreshness.FRESH,
                run_id=run_id,
            )
        ],
    )

    async with get_session_factory()() as session:
        await save_screen_result(session, result)

    async with get_session_factory()() as session:
        records = await get_candidates_for_run(session, run_id)

    assert len(records) == 1
    assert records[0].symbol == "REGRESSION"
