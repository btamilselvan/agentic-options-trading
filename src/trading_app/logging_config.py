"""Structured logging setup with correlation-id propagation.

requirements.md section 10 requires structured logs, metrics, and
correlation IDs; this wires the correlation ID from
`trading_app.correlation` into every log line emitted during a request.
"""
from __future__ import annotations

import json
import logging
import sys

from trading_app.correlation import get_correlation_id


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """One JSON object per line — machine-parseable for a log aggregator,
    used in staging/production (requirements.md section 10)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO", *, json_format: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(
        JSONFormatter()
        if json_format
        else logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
