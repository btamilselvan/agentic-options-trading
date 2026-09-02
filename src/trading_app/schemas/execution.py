"""Order-management contracts: ExecutionMode, ApprovedOrderIntent,
OrderRecord, FillRecord, PaperAccount (requirements.md sections 4.6, 5).

ExecutionMode is explicit and persisted on every intent/order — never
inferred from broker-credential availability.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from trading_app.config import ExecutionMode
from trading_app.schemas.common import VersionedModel

__all__ = [
    "ExecutionMode",
    "OrderSide",
    "OrderLifecycleState",
    "Broker",
    "ApprovedOrderIntent",
    "OrderRecord",
    "FillRecord",
    "PaperAccount",
]


class OrderSide(StrEnum):
    BUY_TO_OPEN = "BUY_TO_OPEN"
    SELL_TO_CLOSE = "SELL_TO_CLOSE"
    SELL_TO_OPEN = "SELL_TO_OPEN"
    BUY_TO_CLOSE = "BUY_TO_CLOSE"


class OrderLifecycleState(StrEnum):
    CREATED = "CREATED"
    PENDING_SUBMISSION = "PENDING_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class Broker(StrEnum):
    SCHWAB = "SCHWAB"
    ROBINHOOD = "ROBINHOOD"


class ApprovedOrderIntent(VersionedModel):
    execution_mode: ExecutionMode
    broker: Broker | None = None  # required only for LIVE
    contract_id: str
    side: OrderSide
    quantity: int = Field(gt=0)
    order_params: dict[str, float | str | None] = Field(default_factory=dict)
    idempotency_key: str
    risk_decision_id: str
    approval_reference: str | None = None
    expires_at: datetime


class OrderRecord(VersionedModel):
    intent_id: str
    execution_mode: ExecutionMode
    broker: Broker | None = None
    state: OrderLifecycleState = OrderLifecycleState.CREATED
    broker_order_id: str | None = None
    raw_provider_payload: dict | None = None


class FillRecord(VersionedModel):
    order_id: str
    quantity: float
    price: float
    fee: float = 0.0
    filled_at: datetime


class PaperAccount(VersionedModel):
    starting_cash: float
    effective_cash: float
    buying_power: float
    positions: dict[str, float] = Field(default_factory=dict)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    simulator_assumption_version: str = "1.0"
