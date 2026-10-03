"""SL multiple, both-level race, rolling fib, and the extra moving averages."""

from datetime import datetime, timedelta, timezone

from backtest.dukascopy import Tick
from backtest.overnight_break import (
    OvernightParams,
    _Fill,
    _compute_sl_tp,
    _first_level_fill,
    _hma_series,
    _kama_series,
    _normalize_params,
    _zlema_series,
    entry_label,
    run_overnight,
)


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


def _params(**kwargs):
    base = dict(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        sl_mode="fixed",
        sl_fixed_pts=1000.0,
        tp_mode="fixed",
        tp_fixed_pts=5000.0,
        near_box_bars=0,
        skip_late_short_wait=0,
    )
    base.update(kwargs)
    return OvernightParams(**base)


def test_sl_mult_matches_the_old_r_multiple():
    legacy = _normalize_params(
        OvernightParams(
            tp_mode="r_mult",
            tp_r_mult=3.0,
            tp_sl_mult=None,
            sl_mode="fixed",
            sl_fixed_pts=1000.0,
        )
    )
    assert legacy.tp_mode == "sl_mult"
    assert legacy.tp_sl_mult == 3.0
    assert legacy.tp_r_mult == 3.0
    _sl, _tp, sl_pts, tp_pts = _compute_sl_tp(
        "UP", 3300.0, 3320.0, 3300.0, legacy, 0.01
    )
    assert sl_pts == 1000.0
    assert tp_pts == 3000.0

    direct = OvernightParams(
        tp_mode="sl_mult",
        tp_sl_mult=2.5,
        tp_r_mult=9.0,
        sl_mode="fixed",
        sl_fixed_pts=1000.0,
    )
    _sl, _tp, sl_pts, tp_pts = _compute_sl_tp(
        "DOWN", 3300.0, 3320.0, 3300.0, direct, 0.01
    )
    assert sl_pts == 1000.0
    assert tp_pts == 2500.0


def test_fixed_cap_keeps_the_ceiling_when_the_stop_is_wide():
    # Asia range 5000 pts, so the stop is 5000. 2R is 10000, above the ceiling.
    p = _normalize_params(
        OvernightParams(
            tp_mode="fixed_r",
            tp_fixed_pts=4000.0,
            tp_sl_mult=2.0,
            sl_mode="range",
            sl_range_mult=1.0,
        )
    )
    assert p.tp_mode == "fixed_cap"
    _sl, tp, sl_pts, tp_pts = _compute_sl_tp("UP", 3300.0, 3350.0, 3300.0, p, 0.01)
    assert sl_pts == 5000.0
    assert tp_pts == 4000.0
    assert tp == 3300.0 + 40.0


def test_fixed_cap_shrinks_a_small_stop_to_the_multiple():
    # Asia range 1000 pts. 2R is 2000, under the 4000 ceiling.
    p = OvernightParams(
        tp_mode="fixed_cap",
        tp_fixed_pts=4000.0,
        tp_sl_mult=2.0,
        sl_mode="range",
        sl_range_mult=1.0,
    )
    _sl, tp, sl_pts, tp_pts = _compute_sl_tp("DOWN", 3300.0, 3310.0, 3300.0, p, 0.01)
    assert sl_pts == 1000.0
    assert tp_pts == 2000.0
    assert tp == 3300.0 - 20.0


def test_same_timestamp_takes_the_level_reached_first():
    t0 = datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc)
    ma = _Fill(1, t0, 3310.0)
    fib = _Fill(2, t0, 3315.0)
    # A long pullback comes down, so the higher price is first.
    fill, which = _first_level_fill("UP", ma, fib, 3310.0, 3315.0)
    assert which == "fib"
    assert fill is fib
    fill, which = _first_level_fill("DOWN", ma, fib, 3310.0, 3315.0)
    assert which == "ma"
    assert fill is ma
    later = _Fill(3, t0 + timedelta(seconds=5), 3300.0)
    fill, which = _first_level_fill("UP", ma, later, 3310.0, 3300.0)
    assert which == "ma"


def test_both_takes_the_fib_when_the_average_is_still_below_it():
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        40,
        default=3302.0,
        overrides={
            datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (3302.0, 3320.0, 3301.0, 3302.0),
            datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (3302.0, 3303.0, 3300.0, 3302.0),
            datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3318.0, 3326.0, 3316.0, 3324.0),
            # Fib 0.5 of 3300–3320 is 3310. EMA(21) after the 3324 close is 3304.
            datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc): (3324.0, 3325.0, 3308.0, 3312.0),
        },
    )
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_params(pullback_ref="both", pullback_fib=0.5, ema_period=21),
    )
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "fib_touch"
    assert row["entry_label"] == "Fib touch"


def test_both_takes_the_selected_average_when_it_is_tagged_first():
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        40,
        default=3302.0,
        overrides={
            datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (3302.0, 3320.0, 3301.0, 3302.0),
            datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (3302.0, 3303.0, 3300.0, 3302.0),
            datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3318.0, 3326.0, 3316.0, 3324.0),
            # Period-1 EMA is the previous close, 3324. Fib 0.9 is 3302, still below this bar.
            datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc): (3324.0, 3325.0, 3308.0, 3312.0),
        },
    )
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_params(
            pullback_ref="both",
            pullback_fib=0.9,
            ma_type="ema",
            ema_period=1,
        ),
    )
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "ema_touch"
    assert row["entry_label"] == "EMA touch"


def test_kama_touch_uses_the_selected_average():
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        40,
        default=3302.0,
        overrides={
            datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (3302.0, 3320.0, 3301.0, 3302.0),
            datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (3302.0, 3303.0, 3300.0, 3302.0),
            datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3318.0, 3326.0, 3316.0, 3324.0),
            datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc): (3324.0, 3325.0, 3308.0, 3312.0),
        },
    )
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_params(
            pullback_ref="ema",
            ma_type="kama",
            kama_er=1,
            kama_fast=2,
            kama_slow=2,
        ),
    )
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "ema_touch"
    assert row["entry_label"] == "KAMA touch"
    assert entry_label("ema_touch", "hma") == "HMA touch"
    assert entry_label("ema_touch", "zlema") == "ZLEMA touch"


def _roll_day(extra=None):
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    overrides = {
        datetime(2025, 5, 6, 2, 0, tzinfo=timezone.utc): (3310.0, 3320.0, 3309.0, 3312.0),
        datetime(2025, 5, 6, 3, 0, tzinfo=timezone.utc): (3312.0, 3314.0, 3300.0, 3308.0),
        # Extends the window, close stays inside the 200 pt break (3322).
        datetime(2025, 5, 6, 6, 0, tzinfo=timezone.utc): (3316.0, 3325.0, 3314.0, 3321.0),
        # Breaks and extends. Window slides to 01:30–06:30, fib 0.5 = 3315.
        datetime(2025, 5, 6, 6, 15, tzinfo=timezone.utc): (3321.0, 3330.0, 3320.0, 3324.0),
    }
    if extra:
        overrides.update(extra)
    return _ohlc_ticks(start, 40, overrides=overrides)


def test_rolling_fib_locks_the_shifted_window():
    ticks = _roll_day(
        {
            # Does not extend 3330. Tags 3315 and misses the original Asia fib at 3310.
            datetime(2025, 5, 6, 6, 30, tzinfo=timezone.utc): (3324.0, 3328.0, 3314.0, 3320.0),
        }
    )
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_params(
            asia_start_hour=1,
            asia_end_hour=6,
            pullback_ref="fib",
            pullback_fib=0.5,
            fib_anchor="roll",
        ),
    )
    assert out["trades"] == 1, out["skips"]
    row = out["rows"][0]
    assert row["entry_reason"] == "fib_touch"
    assert row["fib_high"] == 3330.0
    assert row["fib_low"] == 3300.0
    assert row["fib_level"] == 3315.0
    assert row["asia_high"] == 3320.0


def test_rolling_fib_with_no_retrace_uses_the_timeout_action():
    ticks = _roll_day(
        {
            # Would be a new high, but the drag cap is two bars, so it is not in the fib.
            datetime(2025, 5, 6, 6, 30, tzinfo=timezone.utc): (3328.0, 3340.0, 3326.0, 3332.0),
            datetime(2025, 5, 6, 6, 45, tzinfo=timezone.utc): (3332.0, 3334.0, 3324.0, 3328.0),
            # The level scan includes the next bar's open tick. Keep that above 3315 too.
            datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (3328.0, 3330.0, 3322.0, 3326.0),
        }
    )
    common = dict(
        asia_start_hour=1,
        asia_end_hour=6,
        pullback_ref="fib",
        pullback_fib=0.5,
        fib_anchor="roll",
        max_break_candles_after=2,
        max_wait_candles=2,
    )
    preferred = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_params(pullback_mode="preferred", timeout_action="market", **common),
    )
    assert preferred["trades"] == 1, preferred["skips"]
    row = preferred["rows"][0]
    assert row["entry_reason"] == "timeout_market"
    assert row["fib_high"] == 3330.0
    assert row["fib_low"] == 3300.0

    required = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_params(pullback_mode="required", **common),
    )
    assert required["trades"] == 0
    assert any(s["reason"] == "no_pullback" for s in required["skips"])


def test_moving_average_hand_values():
    kama = _kama_series([10, 11, 12, 13, 14], 3, 2, 30)
    assert kama[4] is not None
    assert abs(kama[4] - 13.1358024691) < 1e-9

    hma = _hma_series([1, 2, 3, 4, 5, 6, 7, 8], 4)
    assert hma[4] == 5

    zlema = _zlema_series([1, 2, 3, 4, 5], 3)
    assert zlema[3] == 4.25
    assert zlema[4] == 5.125
