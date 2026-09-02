"""configuration: read/update versioned screener, risk, execution-mode, and
provider configuration; live-mode changes use a separate protected action
(requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from trading_app.config import Settings, get_settings

router = APIRouter(prefix="/configuration", tags=["configuration"])

REQUIRED_CONFIRMATION = "I understand the risk of live trading"


class SafetyConfigResponse(BaseModel):
    default_execution_mode: str
    live_trading_enabled: bool
    human_approval_enabled: bool
    kill_switch_engaged: bool


class LiveModeChangeRequest(BaseModel):
    enable: bool
    confirmation_phrase: str
    target_broker_account_alias: str


class LiveModeChangeResponse(BaseModel):
    live_trading_enabled: bool


@router.get("/safety", response_model=SafetyConfigResponse)
async def get_safety_config(settings: Settings = Depends(get_settings)) -> SafetyConfigResponse:
    return SafetyConfigResponse(
        default_execution_mode=settings.safety.default_execution_mode.value,
        live_trading_enabled=settings.safety.live_trading_enabled,
        human_approval_enabled=settings.safety.human_approval_enabled,
        kill_switch_engaged=settings.safety.kill_switch_engaged,
    )


@router.post("/safety/live-mode", response_model=LiveModeChangeResponse)
async def change_live_mode(
    payload: LiveModeChangeRequest, settings: Settings = Depends(get_settings)
) -> LiveModeChangeResponse:
    """Separately protected action to enable/disable LIVE mode
    (requirements.md sections 4.6, 11). This skeleton only enforces the
    explicit confirmation phrase in-memory; wire in real
    authentication/authorization, persistence, and an audit write before
    Phase 4."""
    if payload.enable and payload.confirmation_phrase != REQUIRED_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmation_phrase does not match the required live-trading confirmation.",
        )
    # TODO(Phase 4): persist this change, require authenticated admin action,
    # write an audit record, and verify the target broker adapter/account.
    settings.safety.live_trading_enabled = payload.enable
    return LiveModeChangeResponse(live_trading_enabled=settings.safety.live_trading_enabled)
