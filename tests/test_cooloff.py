"""Trend cool-off: reverse >30% in 2–3 bars, join <30% + HH/LL reclaim."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backtest.candles import Candle
from backtest.cooloff import (
    CoolOffParams,
    extract_run,
    run_cooloff,
    run_levels,
)
from backtest.dukascopy import Tick


T0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
TF = timedelta(minutes=15)


def _tick(ts, px):
    return Tick(ts=ts, bid=px, ask=px)


def _bar_ticks(i, o, h, l, c):
    t0 = T0 + TF * i
    return [
        _tick(t0 + timedelta(seconds=1), o),
        _tick(t0 + timedelta(seconds=20), h),
        _tick(t0 + timedelta(seconds=40), l),
        _tick(t0 + timedelta(minutes=14, seconds=50), c),
    ]


def _up_run_ticks():
    """5 bull 15m bars. first open 3300, run high 3350, range 50 → 30% at 3335."""
    out = []
    out += _bar_ticks(0, 3300, 3310, 3299, 3308)
    out += _bar_ticks(1, 3310, 3320, 3309, 3318)
    out += _bar_ticks(2, 3320, 3330, 3319, 3328)
    out += _bar_ticks(3, 3330, 3340, 3329, 3338)
    out += _bar_ticks(4, 3340, 3350, 3339, 3348)
    return out


def _down_run_ticks():
    """5 bear 15m bars. first open 3350, run low 3300, range 50 → 30% at 3315."""
    out = []
    out += _bar_ticks(0, 3350, 3351, 3340, 3342)
    out += _bar_ticks(1, 3340, 3341, 3330, 3332)
    out += _bar_ticks(2, 3330, 3331, 3320, 3322)
    out += _bar_ticks(3, 3320, 3321, 3310, 3312)
    out += _bar_ticks(4, 3310, 3311, 3300, 3302)
    return out


def _params(**kw):
    p = CoolOffParams(
        invert=False,
        min_run=5,
        max_tolerance=2,
        reverse_frac=0.30,
        reverse_min_bars=2,
        reverse_max_bars=3,
        join_min_bars=2,
        join_max_bars=4,
        tp_pts=200,
        sl_pts=200,
        max_hold_hours=4,
        skip_ignored=False,
        weekend_blackout_min=0,
        cooldown_sec=0,
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def _follow_through(start_bar, px0, step, n=40):
    """Ticks after the signal so TP/SL can print."""
    t0 = T0 + TF * start_bar + timedelta(minutes=2)
    out = []
    px = px0
    for i in range(n):
        px = px + step
        out.append(_tick(t0 + timedelta(seconds=5 * i), px))
    return out


def test_extract_run_needs_five_bull_bars():
    bars = []
    for i in range(5):
        t0 = T0 + TF * i
        o = 3300 + i * 10
        bars.append(
            Candle(t0, t0 + TF, o, o + 10, o - 1, o + 8, True)
        )
    hit = extract_run(bars, bull=True, min_run=5, max_tolerance=2)
    assert hit is not None
    run, _ = hit
    lv = run_levels(run, bull=True, reverse_frac=0.30)
    assert lv is not None
    assert abs(lv["run_high"] - 3350) < 1e-9
    assert abs(lv["reverse_px"] - (lv["run_high"] - 0.30 * lv["run_range"])) < 1e-9
    assert extract_run(bars[:4], bull=True, min_run=5, max_tolerance=2) is None


def test_reverse_on_bar2_when_pullback_exceeds_30pct():
    """5 UP bars, pause 1 shallow, pause 2 tags 30% → short."""
    ticks = _up_run_ticks()
    # pause 1 (bar 5): dip 20% to 3340
    ticks += _bar_ticks(5, 3348, 3349, 3340, 3342)
    # pause 2 (bar 6): dump through 3335
    t6 = T0 + TF * 6
    ticks += [
        _tick(t6 + timedelta(seconds=1), 3342),
        _tick(t6 + timedelta(seconds=8), 3338),
        _tick(t6 + timedelta(seconds=16), 3334),  # 32% of the 50-pt rise
    ]
    ticks += _follow_through(6, 3334, -0.08)
    res = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["kind"] == "reverse"
    assert t["side"] == "DOWN"
    assert t["run_dir"] == "UP"
    assert t["pause_bars"] == 2
    assert t["retrace"] >= 0.30
    assert t["exit_reason"] == "tp"
    assert t["pts"] == 200


def test_join_on_forming_bar_when_shallow_pullback_reclaims_hh():
    """<30% dip, then pause bar 2 forming tags the run high → long immediately."""
    ticks = _up_run_ticks()
    ticks += _bar_ticks(5, 3348, 3349, 3342, 3344)  # 8/50 = 16%
    t6 = T0 + TF * 6
    ticks += [
        _tick(t6 + timedelta(seconds=1), 3344),
        _tick(t6 + timedelta(seconds=5), 3346),
        _tick(t6 + timedelta(seconds=10), 3350.02),  # reclaim HH
    ]
    ticks += _follow_through(6, 3350.02, 0.08)
    res = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["kind"] == "join"
    assert t["side"] == "UP"
    assert t["run_dir"] == "UP"
    assert t["pause_bars"] == 2
    assert t["retrace"] < 0.30
    assert t["exit_reason"] == "tp"
    assert t["max_fav_price"] >= t["entry"]
    assert t["max_adv_price"] <= t["entry"]
    assert t["max_fav_pts"] > 0
    assert t["max_adv_pts"] >= 0


def test_full_high_low_run_range_filter_limits_entries():
    """Range bounds use the run's lowest low and highest high, in points."""
    ticks = _up_run_ticks()
    ticks += _bar_ticks(5, 3348, 3349, 3342, 3344)
    t6 = T0 + TF * 6
    ticks += [_tick(t6 + timedelta(seconds=1), 3344), _tick(t6 + timedelta(seconds=10), 3350.02)]
    ticks += _follow_through(6, 3350.02, 0.08)

    # The test run spans 3299 to 3350 = 5,100 XAU/USD points.
    assert run_cooloff(ticks, symbol="XAU/USD", params=_params(min_run_range_pts=5100, max_run_range_pts=5100))["trades"] == 1
    assert run_cooloff(ticks, symbol="XAU/USD", params=_params(min_run_range_pts=5101))["trades"] == 0
    assert run_cooloff(ticks, symbol="XAU/USD", params=_params(max_run_range_pts=5099))["trades"] == 0


def test_zero_tp_allows_the_trail_to_manage_the_exit():
    ticks = _up_run_ticks()
    ticks += _bar_ticks(5, 3348, 3349, 3342, 3344)
    t6 = T0 + TF * 6
    ticks += [
        _tick(t6 + timedelta(seconds=1), 3344),
        _tick(t6 + timedelta(seconds=10), 3350.02),  # join long
        _tick(t6 + timedelta(seconds=15), 3354.02),  # arm at +400 pts
        _tick(t6 + timedelta(seconds=20), 3355.02),  # trail rises to 3351.02
        _tick(t6 + timedelta(seconds=25), 3351.02),  # tag trailing stop
    ]
    res = run_cooloff(
        ticks,
        symbol="XAU/USD",
        params=_params(tp_pts=0, sl_pts=1000, trail_pts=400, trail_arm_pts=400),
    )
    assert res["trades"] == 1
    trade = res["rows"][0]
    assert trade["tp"] is None
    assert trade["exit_reason"] == "trail"
    assert trade["pts"] == 100


def test_invert_flips_reverse_fill():
    """Same UP-run dump: natural is short; invert fills long."""
    ticks = _up_run_ticks()
    ticks += _bar_ticks(5, 3348, 3349, 3340, 3342)
    t6 = T0 + TF * 6
    ticks += [
        _tick(t6 + timedelta(seconds=1), 3342),
        _tick(t6 + timedelta(seconds=16), 3334),
    ]
    ticks += _follow_through(6, 3334, -0.08)
    nat = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    inv = run_cooloff(ticks, symbol="XAU/USD", params=_params(invert=True))
    assert nat["trades"] == 1 and inv["trades"] == 1
    assert nat["rows"][0]["kind"] == "reverse"
    assert nat["rows"][0]["side"] == "DOWN"
    assert nat["rows"][0]["inverted"] is False
    assert inv["rows"][0]["kind"] == "reverse"
    assert inv["rows"][0]["side"] == "UP"
    assert inv["rows"][0]["inverted"] is True
    assert inv["rows"][0]["run_dir"] == "UP"


def test_down_run_reverse_goes_long():
    ticks = _down_run_ticks()
    ticks += _bar_ticks(5, 3302, 3310, 3301, 3306)  # bounce 10/50 = 20%
    t6 = T0 + TF * 6
    ticks += [
        _tick(t6 + timedelta(seconds=1), 3306),
        _tick(t6 + timedelta(seconds=16), 3316),  # past 3315 (30%)
    ]
    ticks += _follow_through(6, 3316, 0.08)
    res = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["kind"] == "reverse"
    assert t["side"] == "UP"
    assert t["run_dir"] == "DOWN"
    assert t["pause_bars"] == 2
    assert t["inverted"] is False


def test_no_reverse_when_30pct_only_on_bar_4():
    """Deep dump on pause bar 4 is past the reverse window; join is dead too."""
    ticks = _up_run_ticks()
    ticks += _bar_ticks(5, 3348, 3349, 3342, 3344)
    ticks += _bar_ticks(6, 3344, 3346, 3341, 3343)
    ticks += _bar_ticks(7, 3343, 3345, 3340, 3342)
    t8 = T0 + TF * 8  # pause bar 4
    ticks += [
        _tick(t8 + timedelta(seconds=1), 3342),
        _tick(t8 + timedelta(seconds=20), 3320),  # 60% retrace, too late
    ]
    ticks += _follow_through(8, 3320, -0.08)
    res = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    assert res["trades"] == 0


def test_no_join_after_deep_pullback_even_if_hh_reclaimed():
    """Once retrace ≥ 30% the join is dead; we reverse instead (on bar 2)."""
    ticks = _up_run_ticks()
    ticks += _bar_ticks(5, 3348, 3349, 3340, 3342)
    t6 = T0 + TF * 6
    ticks += [
        _tick(t6 + timedelta(seconds=1), 3342),
        _tick(t6 + timedelta(seconds=8), 3334),  # reverse first
        _tick(t6 + timedelta(seconds=40), 3350.5),  # later reclaim must not join
    ]
    ticks += _follow_through(6, 3334, -0.08)
    res = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    assert res["trades"] == 1
    assert res["rows"][0]["kind"] == "reverse"
    assert res["rows"][0]["side"] == "DOWN"


def test_pause_bar1_reclaim_is_not_a_join():
    """HH reclaim on the first pause bar is run continuation, not a join."""
    ticks = _up_run_ticks()
    t5 = T0 + TF * 5
    ticks += [
        _tick(t5 + timedelta(seconds=1), 3348),
        _tick(t5 + timedelta(seconds=10), 3342),
        _tick(t5 + timedelta(seconds=20), 3350.5),
        _tick(t5 + timedelta(minutes=14, seconds=50), 3349),
    ]
    ticks += _follow_through(5, 3350.5, 0.08)
    res = run_cooloff(ticks, symbol="XAU/USD", params=_params())
    assert res["trades"] == 0


def test_stop_when_idle():
    from backtest.cooloff_jobs import stop_cooloff

    out = stop_cooloff()
    assert out["ok"] is False
    assert "running" in (out.get("error") or "").lower()
