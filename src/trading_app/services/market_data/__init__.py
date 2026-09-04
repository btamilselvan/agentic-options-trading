"""Provider-neutral market-data access, used by the screener today and
intended for the quantitative engine (component 2) later. Concrete
providers are selected purely by `MARKET_DATA__PROVIDER` config — see
`factory.get_market_data_provider`.
"""
