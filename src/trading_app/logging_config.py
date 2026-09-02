"""Structured logging setup with correlation-id propagation.

requirements.md section 10 requires structured logs, metrics, and
correlation IDs; this wires the correlation ID from
`trading_app.correlation` into every log line emitted during a request.
"""
from __future__ import annotations

import logging
import sys

from trading_app.correlation import get_correlation_id


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
