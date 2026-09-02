"""approval: pending and resolved approvals. Telegram callbacks/webhooks
must be authenticated and idempotent (requirements.md sections 9, 13)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/approval", tags=["approval"])


class PendingApproval(BaseModel):
    intent_id: str
    correlation_id: str
    summary: str


@router.get("/pending", response_model=list[PendingApproval])
async def list_pending_approvals() -> list[PendingApproval]:
    # TODO(Phase 2/3): backed by outstanding Telegram approval requests.
    return []


@router.post("/telegram/webhook", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def telegram_webhook() -> None:
    """Must authenticate the webhook, verify the chat/user is authorized,
    and be idempotent per callback before this can process a real decision
    (requirements.md sections 9, 13)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Telegram approval workflow lands in Phase 2/3.",
    )
