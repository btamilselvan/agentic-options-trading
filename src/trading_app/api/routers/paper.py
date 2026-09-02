"""paper: paper account balance, positions, orders, fills, P&L, reset/replay
controls, and simulator assumptions (requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter

from trading_app.schemas.execution import FillRecord, OrderRecord, PaperAccount

router = APIRouter(prefix="/paper", tags=["paper"])


@router.get("/account", response_model=PaperAccount)
async def get_paper_account() -> PaperAccount:
    # TODO(Phase 3): backed by the internal paper-simulation engine.
    return PaperAccount(starting_cash=0.0, effective_cash=0.0, buying_power=0.0)


@router.get("/orders", response_model=list[OrderRecord])
async def list_paper_orders() -> list[OrderRecord]:
    return []


@router.get("/fills", response_model=list[FillRecord])
async def list_paper_fills() -> list[FillRecord]:
    return []
