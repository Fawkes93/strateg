"""Inverse FVG helpers and saved-result kind."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backtest.candles import Candle
from backtest.fvg import (
    IfvgParams,
    _bearish_fvg,
    _bullish_fvg,
    _is_swing_high,
    _is_swing_low,
    build_tf_candles,
)
from backtest.dukascopy import Tick
from backtest import saved_results as sr


def _bar(i, o, h, l, c, start=None):
    start = start or datetime(2025, 5, 1, 10, 0, tzinfo=timezone.utc)
    ot = start + timedelta(minutes=15 * i)
    return Candle(
        open_time=ot,
        close_time=ot + timedelta(minutes=15),
        open=float(o),
        high=float(h),
        low=float(l),
        close=float(c),
        is_closed=True,
        tick_count=10,
    )


def test_swing_low_high():
    # flat then a clear pivot
    bars = [
        _bar(0, 100, 101, 99, 100),
        _bar(1, 100, 101, 98, 99),
        _bar(2, 99, 100, 95, 96),  # swing low candidate
        _bar(3, 96, 97, 96, 97),
        _bar(4, 97, 99, 96.5, 98),
        _bar(5, 98, 100, 97, 99),
        _bar(6, 99, 105, 98, 104),  # swing high area
        _bar(7, 104, 104.5, 102, 103),
        _bar(8, 103, 103.5, 101, 102),
    ]
    assert _is_swing_low(bars, 2, 2) is True
    assert _is_swing_high(bars, 6, 2) is True


def test_fvg_geometry():
    c1 = _bar(0, 110, 111, 108, 109)
    c2 = _bar(1, 109, 109.5, 100, 101)
    c3 = _bar(2, 101, 102, 99, 100)
    bear = _bearish_fvg(c1, c3)
    assert bear is not None
    p, distal, ce = bear
    assert p == 108
    assert distal == 102
    assert abs(ce - 105.0) < 1e-9

    b1 = _bar(0, 90, 92, 89, 91)
    b3 = _bar(2, 100, 105, 99, 104)
    bull = _bullish_fvg(b1, b3)
    assert bull is not None
    assert bull[0] == 92


def test_build_tf_aggregates_60():
    start = datetime(2025, 5, 5, 8, 0, tzinfo=timezone.utc)
    ticks = []
    # 4 hours of ticks every minute — enough for a few 15m then 1h
    px = 2000.0
    for m in range(0, 240):
        ts = start + timedelta(minutes=m)
        ticks.append(Tick(ts=ts, bid=px, ask=px))
        px += 0.1
    bars15 = build_tf_candles(ticks, timeframe_min=15, skip_ignored=False)
    bars60 = build_tf_candles(ticks, timeframe_min=60, skip_ignored=False)
    assert len(bars15) >= 8
    assert len(bars60) >= 2
    assert bars60[0].close_time - bars60[0].open_time == timedelta(minutes=60)


def test_stop_when_idle():
    from backtest.fvg_jobs import stop_fvg

    out = stop_fvg()
    assert out["ok"] is False
    assert "running" in (out.get("error") or "").lower()


def test_classify_ifvg_filename():
    assert sr.classify_filename("ifvg_XAUUSD_2025-05-01_2025-06-01.json") == "fvg"
