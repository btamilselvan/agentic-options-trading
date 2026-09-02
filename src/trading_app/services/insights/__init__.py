"""Pluggable LLM advisory layer (requirements.md section 4.4).

Application code depends on `InsightProvider` only; `factory.get_insight_provider`
is the single place that maps `LLM__PROVIDER` to a concrete implementation.
"""
