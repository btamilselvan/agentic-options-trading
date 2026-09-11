from __future__ import annotations

from trading_app.services.quant.momentum import compute_roc, compute_rsi


def test_rsi_insufficient_history_returns_none():
    assert compute_rsi([10.0, 11.0], period=14) is None


def test_rsi_hand_computed():
    # period=3, closes=[10, 11, 12, 11, 13]
    # changes: +1, +1, -1, +2 -> gains=[1,1,0,2] losses=[0,0,1,0]
    # seed avg_gain = (1+1+0)/3 = 0.66667; avg_loss = (0+0+1)/3 = 0.33333
    # next (gain=2, loss=0): avg_gain = (0.66667*2 + 2)/3 = 1.11111
    #                        avg_loss = (0.33333*2 + 0)/3 = 0.22222
    # rs = 1.11111 / 0.22222 = 5.0 -> rsi = 100 - 100/6 = 83.3333
    closes = [10.0, 11.0, 12.0, 11.0, 13.0]
    rsi = compute_rsi(closes, period=3)
    assert rsi is not None
    assert abs(rsi - 83.3333) < 0.01


def test_rsi_100_when_no_losses():
    closes = [10.0, 11.0, 12.0, 13.0]
    assert compute_rsi(closes, period=3) == 100.0


def test_roc_hand_computed():
    # period=2: (closes[-1] - closes[-3]) / closes[-3] * 100
    closes = [100.0, 105.0, 110.0]
    assert compute_roc(closes, period=2) == 10.0


def test_roc_insufficient_history_returns_none():
    assert compute_roc([10.0, 11.0], period=5) is None


def test_roc_none_when_reference_is_zero():
    assert compute_roc([0.0, 10.0], period=1) is None
