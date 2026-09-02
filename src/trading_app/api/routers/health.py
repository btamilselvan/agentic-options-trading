"""health: readiness, liveness, dependency/data-source status, and current
safety state (requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from trading_app.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: str = "ok"


class ReadinessResponse(BaseModel):
    status: str
    database: str


class SafetyStatusResponse(BaseModel):
    execution_mode: str
    live_trading_enabled: bool
    kill_switch_engaged: bool
    human_approval_enabled: bool


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    # TODO(Phase 1+): report real data-source freshness/dependency status.
    return ReadinessResponse(status="ok", database="unchecked")


@router.get("/status", response_model=SafetyStatusResponse)
async def safety_status(settings: Settings = Depends(get_settings)) -> SafetyStatusResponse:
    return SafetyStatusResponse(
        execution_mode=settings.safety.default_execution_mode.value,
        live_trading_enabled=settings.safety.live_trading_enabled,
        kill_switch_engaged=settings.safety.kill_switch_engaged,
        human_approval_enabled=settings.safety.human_approval_enabled,
    )
