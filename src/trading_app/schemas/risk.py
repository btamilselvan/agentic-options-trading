"""Deterministic risk/validation contract: RiskDecision
(requirements.md section 4.5).

RiskDecision is immutable and records every rule evaluated with its inputs
and reason code. Only an APPROVED outcome may reach order management.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from trading_app.schemas.common import VersionedModel


class RiskOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class RiskRuleResult(VersionedModel):
    rule_name: str
    passed: bool
    inputs: dict[str, float | str | bool | None] = Field(default_factory=dict)
    reason_code: str | None = None


class RiskDecision(VersionedModel):
    outcome: RiskOutcome
    rules_evaluated: list[RiskRuleResult] = Field(default_factory=list)
    setup_evaluation_request_id: str | None = None
