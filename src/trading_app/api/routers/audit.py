"""audit: filtered, read-only correlation timeline for a candidate, setup,
intent, order, or fill (requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_app.api.deps import get_db
from trading_app.models.audit import AuditRecord

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    correlation_id: str
    stage: str
    summary: str
    detail: dict | None = None


@router.get("", response_model=list[AuditRecordResponse])
async def get_audit_trail(
    correlation_id: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[AuditRecord]:
    stmt = select(AuditRecord).order_by(AuditRecord.created_at.desc()).limit(200)
    if correlation_id:
        stmt = stmt.where(AuditRecord.correlation_id == correlation_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
