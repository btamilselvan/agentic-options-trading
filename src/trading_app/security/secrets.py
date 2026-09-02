"""Secret resolution abstraction.

Never read credentials directly from environment variables scattered
throughout the codebase, and never persist them in a plain database column
(requirements.md section 11). Route all secret access through a
`SecretsProvider` so the env-backed default here can be swapped for an OS
keychain or managed secrets store without touching call sites.
"""
from __future__ import annotations

import os
from typing import Protocol


class SecretsProvider(Protocol):
    def get(self, key: str) -> str | None: ...


class EnvSecretsProvider:
    """Default, development-only backend. Reads from the process environment."""

    def get(self, key: str) -> str | None:
        return os.environ.get(key)


def get_secrets_provider() -> SecretsProvider:
    # `secrets_backend` selects the concrete provider; only "env" exists
    # until a validated OS-backed/secrets-manager integration is added.
    return EnvSecretsProvider()
