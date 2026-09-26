"""EURUSD and USDJPY point size for Asia box and overnight break."""

from datetime import datetime, timedelta, timezone

from backtest.candles import Candle
from backtest.config import point_size
from backtest.dukascopy import price_scale, reaktor_symbol
from backtest.overnight_break import OvernightParams, _fmt_px, run_overnight_on_candles


def test_symbol_maps_and_point_size():
    assert reaktor_symbol("EURUSD") == "EUR/USD"
    assert reaktor_symbol("USDJPY") == "USD/JPY"
    assert reaktor_symbol("USD/JPY") == "USD/JPY"
    assert price_scale("EURUSD") == 100000.0
    assert price_scale("USDJPY") == 1000.0
    assert price_scale("USD/JPY") == 1000.0
    assert point_size("EUR/USD") == 0.00001
    assert point_size("USD/JPY") == 0.001
    assert point_size("USDJPY") == 0.001
    assert point_size("XAU/USD") == 0.01
    assert _fmt_px(1.08543) == "1.08543"
    assert _fmt_px(149.123) == "149.123"
    assert _fmt_px(3312.4) == "3312.40"


def _c5(open_time, o, h, l, c):
    return Candle(
        open_time=open_time,
        close_time=open_time + timedelta(minutes=5),
        open=o,
        high=h,
        low=l,
        close=c,
        is_closed=True,
        tick_count=3,
    )


def _day(symbol):
    """Gold session shifted so one gold point is one point on this symbol."""
    ps = point_size(reaktor_symbol(symbol))
    anchor = {"EURUSD": 1.10000, "USDJPY": 150.000}[symbol]

    def px(gold):
        return anchor + (gold - 3300.0) * (ps / 0.01)

    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 5, 6, 12, 0, tzinfo=timezone.utc)
    specials = {
        datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (3310.0, 3320.0, 3308.0, 3315.0),
        datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (3312.0, 3315.0, 3305.0, 3308.0),
        datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3310.0, 3311.0, 3310.0, 3310.5),
        datetime(2025, 5, 6, 7, 5, tzinfo=timezone.utc): (3310.5, 3310.8, 3305.0, 3306.0),
        datetime(2025, 5, 6, 7, 10, tzinfo=timezone.utc): (3306.0, 3307.0, 3299.0, 3300.0),
    }
    bars = []
    level = 3310.0
    t = start
    while t < end:
        if t in specials:
            o, h, l, c = specials[t]
            level = c
        else:
            o = c = level
            h = level + 0.05
            l = level - 0.05
        bars.append(_c5(t, px(o), px(h), px(l), px(c)))
        t += timedelta(minutes=5)
    return bars


def test_overnight_break_points_follow_symbol():
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="off",
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        trail_arm_mode="off",
        sl_mode="fixed",
        sl_fixed_pts=500.0,
        tp_mode="fixed",
        tp_fixed_pts=100000.0,
    )
    expect_entry = {"EURUSD": 1.10000, "USDJPY": 150.000}
    for symbol, entry in expect_entry.items():
        out = run_overnight_on_candles(_day(symbol), symbol=symbol, params=params)
        assert out["trades"] == 1, (symbol, out.get("skip_counts"))
        row = out["rows"][0]
        assert row["side"] == "DOWN", symbol
        assert row["entry_reason"] == "break_close", symbol
        assert abs(row["entry"] - entry) < 1e-8, (symbol, row["entry"])
        assert abs(row["asia_range_pts"] - 1500.0) < 0.2, (symbol, row["asia_range_pts"])
