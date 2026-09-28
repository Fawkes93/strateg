"""Fib pullback uses the Asia box. Second trade only follows a stop."""

from datetime import datetime, timedelta, timezone

from backtest.dukascopy import Tick
from backtest.overnight_break import OvernightParams, entry_label, run_overnight, trade_fib_px


def _tick(ts, mid):
    return Tick(ts=ts, bid=mid - 0.05, ask=mid + 0.05)


def _ohlc_ticks(start, n_bars, default=3310.0, overrides=None):
    overrides = overrides or {}
    ticks = []
    t = start
    last_c = default
    for _ in range(n_bars):
        o, h, l, c = overrides.get(t, (default, default + 0.5, default - 0.5, default))
        ticks.extend(
            [
                _tick(t, o),
                _tick(t + timedelta(seconds=1), h),
                _tick(t + timedelta(seconds=2), l),
                _tick(t + timedelta(minutes=14, seconds=50), c),
            ]
        )
        last_c = c
        t += timedelta(minutes=15)
    ticks.append(_tick(t, last_c))
    return ticks


def test_fib_zero_is_the_edge_in_the_trade_direction():
    # Asia high 3320, low 3305. Long: 0.5 is halfway back down. Short: halfway back up.
    assert abs(trade_fib_px(3320.0, 3305.0, "UP", 0.5) - 3312.5) < 1e-9
    assert abs(trade_fib_px(3320.0, 3305.0, "DOWN", 0.5) - 3312.5) < 1e-9
    assert trade_fib_px(3320.0, 3305.0, "UP", 0.618) < 3312.5
    assert trade_fib_px(3320.0, 3305.0, "DOWN", 0.618) > 3312.5
    assert entry_label("fib_touch") == "Fib touch"
    assert entry_label("reentry") == "Second trade"


def test_fib_touch_enters_without_a_higher_close():
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        40,
        overrides={
            datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (3310.0, 3320.0, 3308.0, 3315.0),
            datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (3312.0, 3315.0, 3305.0, 3308.0),
            datetime(2025, 5, 6, 6, 45, tzinfo=timezone.utc): (3310.0, 3312.0, 3308.0, 3310.0),
            datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3310.0, 3311.0, 3299.0, 3300.0),
            # Fib 0.5 of 3305–3320 is 3312.5. This bar trades up to it. Close is not a lower close.
            datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc): (3300.0, 3313.0, 3299.0, 3308.0),
        },
    )
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=OvernightParams(
            timezone="UTC",
            pullback_mode="required",
            pullback_ref="fib",
            pullback_fib=0.5,
            use_higher_close=False,
            min_asia_range_pts=300.0,
            min_break_pts_below=200.0,
            min_break_pts_above=200.0,
            sl_mode="fixed",
            sl_fixed_pts=1000.0,
            tp_mode="fixed",
            tp_fixed_pts=5000.0,
        ),
    )
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "fib_touch"
    assert "Fib 0.5" in out["rows"][0]["decision"]


def test_second_trade_only_after_a_stop_and_two_closes():
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        40,
        overrides={
            datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (3310.0, 3320.0, 3308.0, 3315.0),
            datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (3312.0, 3315.0, 3305.0, 3308.0),
            datetime(2025, 5, 6, 6, 45, tzinfo=timezone.utc): (3310.0, 3312.0, 3308.0, 3310.0),
            datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3310.0, 3311.0, 3299.0, 3300.0),
            # Stop for a short from ~3300 is 10 price points higher.
            datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc): (3300.0, 3312.0, 3300.0, 3308.0),
            datetime(2025, 5, 6, 7, 30, tzinfo=timezone.utc): (3308.0, 3309.0, 3304.0, 3306.0),
            datetime(2025, 5, 6, 7, 45, tzinfo=timezone.utc): (3306.0, 3307.0, 3297.0, 3298.0),
            datetime(2025, 5, 6, 8, 0, tzinfo=timezone.utc): (3298.0, 3299.0, 3290.0, 3292.0),
        },
    )
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="off",
        reentry_enabled=True,
        reentry_closes=2,
        reentry_sl_pts=500.0,
        reentry_tp_pts=200.0,
        sl_mode="fixed",
        sl_fixed_pts=1000.0,
        tp_mode="fixed",
        tp_fixed_pts=5000.0,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    reasons = [r["entry_reason"] for r in out["rows"]]
    assert reasons[0] == "break_close"
    assert out["rows"][0]["exit_reason"] == "sl"
    assert "reentry" in reasons
    second = next(r for r in out["rows"] if r["entry_reason"] == "reentry")
    assert second["sl_pts"] == 500.0
    assert second["tp_pts"] == 200.0
    assert out["reentry"]["trades"] == 1

    off = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=OvernightParams(
            timezone="UTC",
            pullback_mode="off",
            reentry_enabled=False,
            sl_mode="fixed",
            sl_fixed_pts=1000.0,
            tp_mode="fixed",
            tp_fixed_pts=5000.0,
            min_asia_range_pts=300.0,
            min_break_pts_below=200.0,
            min_break_pts_above=200.0,
        ),
    )
    assert all(r["entry_reason"] != "reentry" for r in off["rows"])
