"""Provider selection — the only place a provider name maps to a concrete
class. Everything else in the app depends on `InsightProvider`
(requirements.md section 4.4). Add a new provider by registering it in
`_PROVIDERS`; no other call site needs to change.
"""
from __future__ import annotations

from collections.abc import Callable

from trading_app.config import Settings
from trading_app.security.secrets import get_secrets_provider
from trading_app.services.insights.base import InsightProvider
from trading_app.services.insights.gemini_provider import GeminiInsightProvider
from trading_app.services.insights.ollama_provider import OllamaInsightProvider

_PROVIDERS: dict[str, Callable[[Settings], InsightProvider]] = {
    "gemini": lambda settings: GeminiInsightProvider(settings.llm, get_secrets_provider()),
    "ollama": lambda settings: OllamaInsightProvider(settings.llm),
}


def get_insight_provider(settings: Settings) -> InsightProvider:
    try:
        factory = _PROVIDERS[settings.llm.provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown LLM__PROVIDER={settings.llm.provider!r}; "
            f"expected one of {sorted(_PROVIDERS)}."
        ) from exc
    return factory(settings)
