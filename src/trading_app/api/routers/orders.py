"""orders: view normalized order/fill lifecycle (requirements.md
section 9)."""
from __future__ import annotations

from fastapi import APIRouter

from trading_app.schemas.execution import OrderRecord

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderRecord])
async def list_orders() -> list[OrderRecord]:
    # TODO(Phase 3/4): backed by order management's normalized lifecycle
    # records.
    return []
