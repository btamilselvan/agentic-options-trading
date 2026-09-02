"""trade-intents: create/read/cancel permitted intents. Creation must
enforce risk policy server-side and never trust a client-provided approval
value (requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from trading_app.schemas.execution import ApprovedOrderIntent

router = APIRouter(prefix="/trade-intents", tags=["trade-intents"])


@router.get("", response_model=list[ApprovedOrderIntent])
async def list_intents() -> list[ApprovedOrderIntent]:
    # TODO(Phase 3): backed by persisted, risk-approved intents.
    return []


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_intent() -> None:
    """Not wired up until the deterministic risk layer (Phase 3) exists —
    an intent must never be created without passing server-side risk
    validation."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Trade-intent creation requires the deterministic risk layer (Phase 3).",
    )
