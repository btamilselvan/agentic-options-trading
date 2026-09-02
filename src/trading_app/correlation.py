"""Correlation-ID propagation.

Every candidate through order/fill must preserve a correlation ID, including
rejected and suppressed paths (requirements.md section 6). This module
provides a contextvar-backed accessor plus ASGI middleware that assigns or
propagates one per request.
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Correlation-ID"

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def new_correlation_id() -> str:
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(HEADER_NAME) or new_correlation_id()
        token = _correlation_id.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            _correlation_id.reset(token)
        response.headers[HEADER_NAME] = correlation_id
        return response
