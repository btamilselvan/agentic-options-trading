"""Verifies LLM__PROVIDER alone controls which InsightProvider is used —
the actual mechanism behind "switch providers without a code change"
(requirements.md section 4.4)."""
from __future__ import annotations

import pytest

from trading_app.config import Settings
from trading_app.services.insights.factory import get_insight_provider
from trading_app.services.insights.gemini_provider import GeminiInsightProvider
from trading_app.services.insights.ollama_provider import OllamaInsightProvider


def test_factory_selects_gemini_provider(monkeypatch):
    monkeypatch.setenv("LLM__PROVIDER", "gemini")
    assert isinstance(get_insight_provider(Settings()), GeminiInsightProvider)


def test_factory_selects_ollama_provider(monkeypatch):
    monkeypatch.setenv("LLM__PROVIDER", "ollama")
    assert isinstance(get_insight_provider(Settings()), OllamaInsightProvider)


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM__PROVIDER", "not-a-real-provider")
    with pytest.raises(ValueError, match="LLM__PROVIDER"):
        get_insight_provider(Settings())
