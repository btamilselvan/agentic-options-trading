"""Screener universe discovery (requirements.md section 4.1's
"configurable universe") — separate from `services.market_data`, which
fetches quotes for symbols already chosen. Provider selection is
`UNIVERSE__PROVIDER` config alone; see `factory.get_universe_provider`.
"""
