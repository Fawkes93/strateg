"""Session rules added on top of the Asia box setups.

The older tests/test_asia_box.py helper turns these gates off so the setup
geometry stays isolated. These tests turn the gates on.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backtest.asia_box import AsiaBoxParams, fib_px, run_asia_box_on_candles
from backtest.asia_box_describe import describe_rules, describe_setups
from backtest.candles import Candle


TZ = ZoneInfo("UTC")


def _bar(h, m, o, high, low, close, day=10):
    t0 = datetime(2026, 7, day, h, m, tzinfo=TZ)
    return Candle(
        open_time=t0,
        close_time=t0 + timedelta(minutes=5),
        open=o,
        high=high,
        low=low,
        close=close,
        is_closed=True,
    )


def _params(**kw):
    base = dict(
        timezone="UTC",
        min_range_pts=3000.0,
        enable_reverse_ema=False,
        enable_shallow_ema=False,
        enable_shallow_confirm=False,
        enable_ema_retest=False,
    )
    base.update(kw)
    return AsiaBoxParams(**base)


def _run(candles, **kw):
    return run_asia_box_on_candles(candles, symbol="XAUUSD", params=_params(**kw))


def _up_box():
    return [
        _bar(1, 0, 3305.0, 3308.0, 3300.0, 3302.0),
        _bar(2, 0, 3320.0, 3330.0, 3320.0, 3328.0),
    ]


def _seed_ema(px, n=32):
    bars = []
    t0 = datetime(2026, 7, 9, 20, 0, tzinfo=TZ)
    for i in range(n):
        ts = t0 + timedelta(minutes=5 * i)
        bars.append(
            Candle(
                open_time=ts,
                close_time=ts + timedelta(minutes=5),
                open=px,
                high=px + 0.05,
                low=px - 0.05,
                close=px,
                is_closed=True,
            )
        )
    return bars


def test_no_fill_before_0330_and_fill_at_0330():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    early = _up_box() + [
        _bar(2, 0, 3320.0, 3322.0, mid, mid),
        _bar(2, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        _bar(2, 10, p500 - 0.4, 3330.0, p500 - 0.3, 3330.0),
    ]
    blocked = _run(early, enable_reverse_confirm=False, continuation_trail=False)
    assert blocked["rows"] == []

    later = _up_box() + [
        _bar(3, 25, 3320.0, 3322.0, mid, mid),
        _bar(3, 30, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        _bar(3, 35, p500 - 0.4, 3330.0, 3320.0, 3330.0),
    ]
    out = _run(later, enable_reverse_confirm=False, continuation_trail=False)
    assert len(out["rows"]) == 1
    assert out["rows"][0]["setup"] == "continuation"
    assert "03:35" in out["rows"][0]["entry_ts"]


def test_reverse_arms_before_0330_and_confirms_after():
    p786 = fib_px(3330.0, 3300.0, 0.786)
    candles = _up_box() + [
        # Bearish close through .786 at 02:05. Arms reverse, cannot fill yet.
        _bar(2, 5, p786 + 1.0, p786 + 1.2, p786 - 0.8, p786 - 0.4),
        # Back inside the box, still bearish. Confirms only because 02:05 armed it.
        _bar(3, 30, p786 + 1.2, p786 + 1.3, p786 + 0.3, p786 + 0.5),
        _bar(3, 35, p786 + 0.5, p786 + 0.6, 3285.0, 3285.0),
    ]
    out = _run(candles, enable_continuation=False)
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "reverse_confirm"
    assert t["side"] == "DOWN"
    assert "03:35" in t["entry_ts"]


def test_continuation_trail_ratchets_to_382_and_keeps_initial():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    p382 = fib_px(3330.0, 3300.0, 0.382)
    high = fib_px(3330.0, 3300.0, 0.10)
    entry = p500 - 0.4
    candles = _up_box() + [
        _bar(3, 30, 3312.0, 3316.0, 3310.0, entry),
        _bar(3, 35, entry, high, p382 + 0.4, high - 0.2),
        _bar(3, 40, high - 0.2, high - 0.1, p382 - 0.1, p382),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "continuation"
    assert t["exit_reason"] == "sl"
    assert abs(t["sl"] - p382) < 1e-6
    assert abs(t["extras"]["sl_initial"] - p786) < 1e-6
    assert t["sl"] > t["extras"]["sl_initial"]


def test_continuation_straight_to_fib0_still_takes_target():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    entry = p500 - 0.4
    candles = _up_box() + [
        _bar(3, 30, 3312.0, 3316.0, 3310.0, entry),
        # Low stays above the trailed .382 stop while the high tags Fib 0.
        _bar(3, 35, entry, 3330.0, 3320.0, 3330.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    t = out["rows"][0]
    assert t["exit_reason"] == "tp"
    assert abs(t["tp"] - 3330.0) < 1e-9


def test_continuation_trail_does_not_widen_the_stop():
    p786 = fib_px(3330.0, 3300.0, 0.786)
    entry = p786 + 0.3
    candles = _up_box() + [
        _bar(3, 30, 3306.5, entry + 0.2, 3306.5, entry),
        _bar(3, 35, entry, entry + 0.5, entry - 0.05, entry + 0.2),
        _bar(3, 40, entry, entry + 0.1, p786 - 0.2, p786),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    t = out["rows"][0]
    assert t["exit_reason"] == "sl"
    assert abs(t["sl"] - p786) < 1e-6
    assert abs(t["extras"]["sl_initial"] - p786) < 1e-6


def test_candle_under_40_percent_fills():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    candles = _up_box() + [
        # Range 11 on a 30-wide box = 36.7%.
        _bar(3, 30, 3312.0, 3320.0, 3309.0, p500 - 0.4),
        _bar(3, 35, p500 - 0.4, 3330.0, 3320.0, 3330.0),
    ]
    out = _run(candles, enable_reverse_confirm=False, continuation_trail=False)
    assert len(out["rows"]) == 1
    assert out["freezes"] == []


def test_candle_over_40_percent_freezes_then_fills_on_expanded_box():
    candles = _up_box() + [
        # 18 wide on a 30 box (60%). Reverse confirm, skipped.
        _bar(3, 0, 3320.0, 3322.0, 3304.0, 3305.0),
        # New high while entries are frozen. Box becomes 3350–3300.
        _bar(3, 30, 3335.0, 3350.0, 3334.0, 3348.0),
        # 04:30 is still inside the 90 minutes. Would be a reverse confirm.
        _bar(4, 30, 3320.0, 3321.0, 3308.0, 3309.0),
        # 04:35 is 90 minutes after the 03:05 close. Fresh reverse on the new box.
        _bar(4, 35, 3312.0, 3313.0, 3308.0, 3309.0),
        _bar(4, 40, 3309.0, 3310.0, 3275.0, 3275.0),
    ]
    out = _run(candles, enable_continuation=False)
    assert len(out["freezes"]) == 1
    fz = out["freezes"][0]
    assert fz["setup"] == "reverse_confirm"
    assert fz["local_date"] == "2026-07-10"
    assert abs(fz["candle_pts"] - 1800.0) < 1e-6
    assert abs(fz["box_pts"] - 3000.0) < 1e-6
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "reverse_confirm"
    assert "04:40" in t["entry_ts"]
    assert abs(t["fib0"] - 3350.0) < 1e-9


def test_ema_retest_steps_default_two_and_three_is_wider():
    ema_px = 3295.0
    fib0, fib1 = 3300.0, 3330.0
    candles = _seed_ema(ema_px) + [
        _bar(1, 0, 3325.0, 3330.0, 3324.0, 3326.0),
        _bar(2, 0, 3310.0, 3311.0, 3300.0, 3302.0),
        _bar(7, 0, ema_px - 4.0, ema_px + 4.0, ema_px - 4.5, ema_px - 1.0),
        _bar(7, 5, ema_px - 1.0, ema_px, ema_px - 2.0, ema_px - 0.5),
    ]
    common = dict(
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    two = _run(candles, **common)
    assert len(two["rows"]) == 1
    assert abs(two["rows"][0]["sl"] - fib_px(fib0, fib1, 0.236)) < 1e-6
    three = _run(candles, ema_retest_sl_steps=3, **common)
    assert abs(three["rows"][0]["sl"] - fib_px(fib0, fib1, 0.382)) < 1e-6


def test_rule_copy_names_the_clock_the_freeze_and_the_ema_steps():
    rules = {r["id"]: r for r in describe_rules(AsiaBoxParams())}
    assert "03:30" in rules["trade_start"]["body"]
    assert "2026-03-16" in rules["impulse_freeze"]["body"]
    assert "2026-04-06" in rules["impulse_freeze"]["body"]
    assert "40%" in rules["impulse_freeze"]["body"]
    assert ".236" in rules["continuation_trail"]["body"]
    ema = next(c["body"] for c in describe_setups() if c["id"] == "ema_retest")
    assert ".236" in ema and ".382" in ema
    assert "second fib" in ema
    off = describe_rules(
        AsiaBoxParams(
            trade_start_enabled=False,
            continuation_trail=False,
            impulse_freeze=False,
        )
    )
    blob = " ".join(r["body"] for r in off).lower()
    assert blob.count("off") >= 3
    wider = AsiaBoxParams(impulse_freeze_frac=0.45, trade_start_hour=4, trade_start_minute=0)
    moved = {r["id"]: r for r in describe_rules(wider)}
    assert "04:00" in moved["trade_start"]["body"]
    assert "45%" in moved["impulse_freeze"]["body"]
