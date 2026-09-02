"""Aggregates every required API group into a single router
(requirements.md section 9)."""
from __future__ import annotations

from fastapi import APIRouter

from trading_app.api.routers import (
    approval,
    audit,
    candidates,
    configuration,
    features,
    health,
    insights,
    orders,
    paper,
    trade_intents,
)

api_router = APIRouter()

for _module in (
    health,
    configuration,
    candidates,
    features,
    insights,
    trade_intents,
    orders,
    paper,
    approval,
    audit,
):
    api_router.include_router(_module.router)
