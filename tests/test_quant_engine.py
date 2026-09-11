from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from trading_app.config import QuantEngineSettings
from trading_app.schemas.market_data import Candle, DataFreshness, Interval
from trading_app.services.quant.engine import compute_feature_snapshot
from trading_app.services.quant.vwap import MARKET_TZ

_SESSION_OPEN = datetime(2026, 9, 3, 9, 30, tzinfo=MARKET_TZ)


def _minute_bars(n: int, start_price: float = 100.0) -> list[Candle]:
    bars = []
    price = start_price
    for i in range(n):
        price += 0.1
        bars.append(
            Candle(
                symbol="TEST",
                interval=Interval.ONE_MIN,
                open=price,
                high=price + 0.05,
                low=price - 0.05,
                close=price,
                volume=1000.0,
                market_timestamp=_SESSION_OPEN + timedelta(minutes=i),
                source="test-fixture",
            )
        )
    return bars


def _daily_bars(n: int) -> list[Candle]:
    return [
        Candle(
            symbol="TEST",
            interval=Interval.DAILY,
            open=90.0,
            high=95.0,
            low=85.0,
            close=90.0 + d,
            volume=5_000_000.0,
            market_timestamp=datetime(2026, 8, 20 + d, 16, 0, tzinfo=MARKET_TZ),
            source="test-fixture",
        )
        for d in range(n)
    ]


def test_engine_assembles_a_full_snapshot():
    cfg = QuantEngineSettings()
    minute_bars = _minute_bars(60)
    daily_bars = _daily_bars(5)
    as_of = minute_bars[-1].market_timestamp
    correlation_id = uuid4()

    snapshot = compute_feature_snapshot(
        "TEST",
        minute_bars,
        daily_bars,
        benchmark_data={},
        cfg=cfg,
        as_of=as_of,
        correlation_id=correlation_id,
        data_quality=DataFreshness.FRESH,
    )

    assert snapshot.symbol == "TEST"
    assert snapshot.correlation_id == correlation_id
    assert snapshot.feature_definition_version == cfg.feature_definition_version
    assert snapshot.data_quality == DataFreshness.FRESH
    # Enough history for every configured EMA period (max 50) plus one.
    assert snapshot.features["ema_9"] is not None
    assert snapshot.features["ema_20"] is not None
    assert snapshot.features["ema_50"] is not None
    assert snapshot.features["vwap"] is not None
    assert snapshot.features["rsi"] is not None
    assert snapshot.features["atr"] is not None
    assert snapshot.features["prev_day_high"] == daily_bars[-1].high
    assert snapshot.features["prev_day_low"] == daily_bars[-1].low
    assert snapshot.features["prev_day_close"] == daily_bars[-1].close
    # A steadily-rising price series is bullish-aligned.
    assert snapshot.features["ema_alignment"] == 1.0


def test_engine_returns_none_features_on_insufficient_history_not_fabricated_zeros():
    cfg = QuantEngineSettings()
    minute_bars = _minute_bars(3)  # far short of any EMA/RSI/ATR period
    as_of = minute_bars[-1].market_timestamp

    snapshot = compute_feature_snapshot(
        "TEST", minute_bars, daily_bars=[], benchmark_data={}, cfg=cfg, as_of=as_of
    )

    assert snapshot.features["ema_50"] is None
    assert snapshot.features["rsi"] is None
    assert snapshot.features["prev_day_close"] is None
    assert snapshot.features["avg_daily_volume"] is None


def test_engine_populates_market_context_from_benchmarks():
    cfg = QuantEngineSettings(sector_etf_map={"TEST": "XLK"})
    minute_bars = _minute_bars(60)
    as_of = minute_bars[-1].market_timestamp
    benchmark_data = {
        "SPY": (_minute_bars(60, start_price=400.0), 395.0),
        "QQQ": (_minute_bars(60, start_price=350.0), 345.0),
        "XLK": (_minute_bars(60, start_price=200.0), 198.0),
    }

    snapshot = compute_feature_snapshot(
        "TEST", minute_bars, daily_bars=_daily_bars(5), benchmark_data=benchmark_data, cfg=cfg,
        as_of=as_of,
    )

    assert snapshot.market_context["spy_trend"] == "bullish"
    assert snapshot.market_context["qqq_trend"] == "bullish"
    assert snapshot.market_context["sector_etf_symbol"] == "XLK"
    assert snapshot.market_context["sector_trend"] == "bullish"
    assert snapshot.market_context["relative_move_vs_spy_pct"] is not None


def test_engine_correlation_id_defaults_when_not_provided():
    cfg = QuantEngineSettings()
    minute_bars = _minute_bars(10)
    snapshot = compute_feature_snapshot(
        "TEST", minute_bars, daily_bars=[], benchmark_data={}, cfg=cfg,
        as_of=minute_bars[-1].market_timestamp,
    )
    assert snapshot.correlation_id is not None
