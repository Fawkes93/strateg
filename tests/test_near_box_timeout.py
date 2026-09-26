"""Near-box timeout: required-mode recovery when wait closes hug the Asia edge."""

from datetime import datetime, timedelta, timezone

from backtest.candles import Candle
from backtest.overnight_break import (
    OvernightParams,
    _normalize_params,
    near_box_hug,
    run_overnight_on_candles,
)
from types import SimpleNamespace


def _c(h, l, c=None):
    return SimpleNamespace(high=h, low=l, close=c if c is not None else (h + l) / 2)


def test_near_box_off_when_bars_zero():
    p = OvernightParams(near_box_bars=0, near_box_pts=500)
    assert near_box_hug(p, "UP", [_c(2005, 2000)] * 5, 2000.0, 1900.0, 1.0) is False


def test_near_box_up_hug_passes():
    p = OvernightParams(near_box_bars=5, near_box_pts=500)
    bad = [_c(2500, 1500, c) for c in (2100, 1900, 2050, 2800, 2005)]
    assert near_box_hug(p, "UP", bad, 2000.0, 1000.0, 1.0) is False
    good = [_c(2500, 1500, c) for c in (2100, 1900, 2050, 1950, 2005)]
    assert near_box_hug(p, "UP", good, 2000.0, 1000.0, 1.0) is True


def test_near_box_up_fails_when_close_away():
    p = OvernightParams(near_box_bars=5, near_box_pts=500)
    candles = [_c(2200, 1800, 2000)] * 4 + [_c(3000, 2900, 2950)]
    assert near_box_hug(p, "UP", candles, 2000.0, 1000.0, 1.0) is False


def test_near_box_down_hug_passes():
    p = OvernightParams(near_box_bars=5, near_box_pts=500)
    candles = [_c(1600, 1400, 1550)] * 5
    assert near_box_hug(p, "DOWN", candles, 2000.0, 1500.0, 1.0) is True


def test_near_box_needs_enough_bars():
    p = OvernightParams(near_box_bars=5, near_box_pts=500)
    candles = [_c(2005, 1995, 2000)] * 4
    assert near_box_hug(p, "UP", candles, 2000.0, 1000.0, 1.0) is False


def test_near_box_trend_gates():
    # UP edge 2000. Tail closes 2050, 2100, 2150 — all within 500, stepping up,
    # net extension, and outside a 100-pt min break.
    tail = [_c(2200, 1900, c) for c in (2050, 2100, 2150)]
    base = dict(
        near_box_bars=3,
        near_box_pts=500,
        min_break_pts_above=100,
        min_break_pts_below=100,
    )
    assert near_box_hug(OvernightParams(near_box_trend="off", **base), "UP", tail, 2000.0, 1000.0, 1.0)
    assert near_box_hug(OvernightParams(near_box_trend="closes_dir", **base), "UP", tail, 2000.0, 1000.0, 1.0)
    assert near_box_hug(OvernightParams(near_box_trend="net_ext", **base), "UP", tail, 2000.0, 1000.0, 1.0)
    assert near_box_hug(OvernightParams(near_box_trend="outside", **base), "UP", tail, 2000.0, 1000.0, 1.0)
    assert near_box_hug(OvernightParams(near_box_trend="breakout", **base), "UP", tail, 2000.0, 1000.0, 1.0)

    faded = [_c(2200, 1900, c) for c in (2200, 2150, 2100)]
    assert not near_box_hug(
        OvernightParams(near_box_trend="closes_dir", **base), "UP", faded, 2000.0, 1000.0, 1.0
    )
    assert not near_box_hug(
        OvernightParams(near_box_trend="net_ext", **base), "UP", faded, 2000.0, 1000.0, 1.0
    )
    assert not near_box_hug(
        OvernightParams(near_box_trend="breakout", **base), "UP", faded, 2000.0, 1000.0, 1.0
    )
    # Last close is still 100 pts outside, so outside passes. Breakout does not.
    assert near_box_hug(
        OvernightParams(near_box_trend="outside", **base), "UP", faded, 2000.0, 1000.0, 1.0
    )

    inside = [_c(2200, 1900, c) for c in (2050, 2010, 2000)]
    assert not near_box_hug(
        OvernightParams(near_box_trend="outside", **base), "UP", inside, 2000.0, 1000.0, 1.0
    )
    norm = _normalize_params(OvernightParams(near_box_trend="nope", **base))
    assert norm.near_box_trend == "off"


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


def _down_day():
    """Asia low 3305, break close 3300, later 15m closes stay on 3300."""
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
        bars.append(_c5(t, o, h, l, c))
        t += timedelta(minutes=5)
    return bars


def _required(**kwargs):
    base = dict(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        ema_period=200,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=2,
        max_break_candles_after=8,
        timeout_action="skip",
        trail_arm_mode="off",
        sl_mode="fixed",
        sl_fixed_pts=500.0,
        tp_mode="fixed",
        tp_fixed_pts=100000.0,
    )
    base.update(kwargs)
    return OvernightParams(**base)


def test_required_timeout_fills_when_closes_hug_edge():
    out = run_overnight_on_candles(
        _down_day(),
        symbol="XAU/USD",
        params=_required(near_box_bars=2, near_box_pts=500.0, near_box_trend="off"),
    )
    assert out["trades"] == 1, out.get("skip_counts")
    row = out["rows"][0]
    assert row["entry_reason"] == "near_box_timeout"
    assert row["side"] == "DOWN"
    assert "hugged" in (row.get("decision") or "")


def test_required_timeout_still_skips_when_near_box_off():
    out = run_overnight_on_candles(_down_day(), symbol="XAU/USD", params=_required())
    assert out["trades"] == 0
    assert any(s.get("reason") == "no_pullback" for s in out["skips"])


def test_preferred_skip_ignores_near_box():
    out = run_overnight_on_candles(
        _down_day(),
        symbol="XAU/USD",
        params=_required(
            pullback_mode="preferred",
            timeout_action="skip",
            near_box_bars=2,
            near_box_pts=500.0,
        ),
    )
    assert out["trades"] == 0
    assert any(s.get("reason") == "no_pullback_timeout" for s in out["skips"])


def test_outside_trend_rejects_close_back_inside():
    # Every 5m bar after the break closes back inside, above Asia low 3305.
    bars = _down_day()
    cut = datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc)
    for i, bar in enumerate(bars):
        if bar.open_time >= cut:
            bars[i] = _c5(bar.open_time, 3310.0, 3312.0, 3308.0, 3310.0)
    out = run_overnight_on_candles(
        bars,
        symbol="XAU/USD",
        params=_required(near_box_bars=2, near_box_pts=800.0, near_box_trend="outside"),
    )
    assert out["trades"] == 0
    assert any(s.get("reason") == "no_pullback" for s in out["skips"])
