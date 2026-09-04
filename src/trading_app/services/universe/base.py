"""UniverseProvider interface.

Discovers which symbols the screener should evaluate on a given cycle —
as opposed to `MarketDataProvider`, which fetches quotes for symbols
already chosen. No call site should depend on a concrete provider
(requirements.md section 4.1); see
`trading_app.services.universe.factory`.
"""
from __future__ import annotations

from typing import Protocol


class UniverseProviderError(Exception):
    """Raised when discovery fails outright. Callers should fail closed —
    e.g. fall back to whatever `always_include` configures — never
    fabricate a symbol list."""


class UniverseProvider(Protocol):
    async def discover_symbols(self) -> list[str]: ...
