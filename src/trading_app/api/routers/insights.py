"""insights: LLM evaluations, schema-validation results, and decision trail
(requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter

from trading_app.schemas.insights import SetupEvaluationResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=list[SetupEvaluationResponse])
async def list_insights(symbol: str | None = None) -> list[SetupEvaluationResponse]:
    # TODO(Phase 2): backed by persisted LLM evaluations and their
    # schema-validation results.
    return []
