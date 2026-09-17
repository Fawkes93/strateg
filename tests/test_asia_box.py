from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backtest.asia_box import (
    AsiaBoxParams,
    close_through_786,
    fib_anchors,
    fib_px,
    in_continuation_band,
    run_asia_box_on_candles,
    wick_786,
)
from backtest.asia_box_describe import SETUP_ORDER, describe_setups
from backtest.candles import Candle


TZ = ZoneInfo("UTC")


def _bar(h, m, o, high, low, close):
    t0 = datetime(2026, 7, 10, h, m, tzinfo=TZ)
    return Candle(
        open_time=t0,
        close_time=t0 + timedelta(minutes=5),
        open=o,
        high=high,
        low=low,
        close=close,
        is_closed=True,
    )


def test_fib_px_up_box_puts_zero_on_high():
    # 3000-pt box: 3330 high / 3300 low. Later high → UP, fib0=high.
    side, fib0, fib1 = fib_anchors(
        high=3330.0,
        low=3300.0,
        high_ts=datetime(2026, 7, 10, 2, 0, tzinfo=TZ),
        low_ts=datetime(2026, 7, 10, 1, 0, tzinfo=TZ),
    )
    assert side == "UP"
    assert fib0 == 3330.0
    assert fib1 == 3300.0
    assert fib_px(fib0, fib1, 0.0) == 3330.0
    assert fib_px(fib0, fib1, 1.0) == 3300.0
    assert abs(fib_px(fib0, fib1, 0.5) - 3315.0) < 1e-9
    assert abs(fib_px(fib0, fib1, 0.786) - (3330.0 + (3300.0 - 3330.0) * 0.786)) < 1e-9


def test_fib_px_down_box_puts_zero_on_low():
    side, fib0, fib1 = fib_anchors(
        high=3330.0,
        low=3300.0,
        high_ts=datetime(2026, 7, 10, 1, 0, tzinfo=TZ),
        low_ts=datetime(2026, 7, 10, 2, 0, tzinfo=TZ),
    )
    assert side == "DOWN"
    assert fib0 == 3300.0
    assert fib1 == 3330.0
    assert fib_px(fib0, fib1, 0.0) == 3300.0
    assert fib_px(fib0, fib1, 1.0) == 3330.0


def test_later_extreme_tie_prefers_high():
    ts = datetime(2026, 7, 10, 2, 0, tzinfo=TZ)
    side, fib0, fib1 = fib_anchors(3330.0, 3300.0, ts, ts)
    assert side == "UP"
    assert fib0 == 3330.0


def test_close_through_786_is_not_a_wick():
    fib0, fib1 = 3330.0, 3300.0
    p786 = fib_px(fib0, fib1, 0.786)
    wick = _bar(4, 0, 3315.0, 3316.0, p786 - 0.1, 3314.0)
    through = _bar(4, 5, 3314.0, 3315.0, p786 - 0.5, p786 - 0.2)
    assert wick_786("UP", wick, fib0, fib1)
    assert not close_through_786("UP", wick, fib0, fib1)
    assert close_through_786("UP", through, fib0, fib1)


def test_continuation_band_is_between_500_and_786():
    fib0, fib1 = 3330.0, 3300.0
    p500 = fib_px(fib0, fib1, 0.5)
    p786 = fib_px(fib0, fib1, 0.786)
    assert in_continuation_band("UP", (p500 + p786) / 2.0, fib0, fib1)
    assert in_continuation_band("UP", p500, fib0, fib1)
    assert in_continuation_band("UP", p786, fib0, fib1)
    assert not in_continuation_band("UP", p500 + 0.5, fib0, fib1)
    assert not in_continuation_band("UP", p786 - 0.5, fib0, fib1)


def test_describe_setups_uses_live_params():
    params = AsiaBoxParams(min_range_pts=3500.0, shallow_confirm_sl_fib=0.618, ema_period=21)
    cards = describe_setups(params)
    ids = [c["id"] for c in cards]
    assert ids == list(SETUP_ORDER)
    blob = " ".join(c["body"] for c in cards)
    assert "3500" in blob
    assert "0.618" in blob
    assert "21" in blob
    titles = {c["id"]: c["title"] for c in cards}
    assert titles["continuation"] == "Continuation"
    assert titles["reverse_confirm"] == "Reverse Confirm"
    rev_c = next(c["body"] for c in cards if c["id"] == "reverse_confirm")
    assert "1.5" in rev_c
    cont = next(c["body"] for c in cards if c["id"] == "continuation")
    assert "0.786" in cont or ".786" in cont
    assert titles["reverse_ema"] == "Reverse EMA"
    assert titles["shallow_ema"] == "Shallow EMA"
    assert titles["shallow_confirm"] == "Shallow Confirm"
    assert titles["ema_retest"] == "EMA Retest"
    ema_body = next(c["body"] for c in cards if c["id"] == "ema_retest")
    assert "second fib" in ema_body
    assert ".236" in ema_body and ".382" in ema_body
    assert "Moldova" not in blob


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
    """01:00 low 3300, 02:00 high 3330 → 3000-pt UP box. Fib0=3330, Fib1=3300."""
    return [
        _bar(1, 0, 3305.0, 3308.0, 3300.0, 3302.0),
        # Impulse must not wick into .382/.500 or shallow is dead on creation.
        _bar(2, 0, 3320.0, 3330.0, 3320.0, 3328.0),
    ]


def test_continuation_fills_in_band_and_takes_fib0():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),  # bullish, in band, no 786 wick
        _bar(3, 10, p500 - 0.4, 3330.0, p500 - 0.5, 3330.0),  # TP Fib 0
    ]
    out = _run(candles, enable_reverse_confirm=False)
    rows = out["rows"]
    assert len(rows) == 1
    t = rows[0]
    assert t["setup"] == "continuation"
    assert t["side"] == "UP"
    assert t["box_n"] == 1
    assert t["exit_reason"] == "tp"
    assert abs(t["tp"] - 3330.0) < 1e-9
    assert abs(t["sl"] - p786) < 1e-9
    assert abs(t["entry"] - (p500 - 0.4)) < 1e-9
    assert t["pts"] > 0


def test_continuation_tainted_confirm_needs_second_clean_close():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        # bullish in-band but wicks .786
        _bar(3, 5, mid, p500 - 0.1, p786 - 0.2, mid + 0.3),
        # second, clean
        _bar(3, 10, mid, p500 - 0.2, mid - 0.2, p500 - 0.3),
        _bar(3, 15, p500 - 0.3, 3330.0, p500 - 0.4, 3330.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert len(out["rows"]) == 1
    assert out["rows"][0]["setup"] == "continuation"
    assert abs(out["rows"][0]["entry"] - (p500 - 0.3)) < 1e-9


def test_two_tainted_confirms_skip_continuation():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.1, p786 - 0.2, mid + 0.3),
        _bar(3, 10, mid, p500 - 0.1, p786 - 0.3, mid + 0.2),
        _bar(3, 15, mid, p500 - 0.2, mid - 0.2, p500 - 0.3),
        _bar(3, 20, p500 - 0.3, 3330.0, p500 - 0.4, 3330.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert out["rows"] == []


def test_close_through_786_arms_reverse_and_kills_continuation():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        # close through .786 — no continuation
        _bar(3, 5, mid, mid + 0.2, p786 - 1.0, p786 - 0.4),
        # reverse confirm: bearish close
        _bar(3, 10, p786 - 0.4, p786 - 0.2, p786 - 0.8, p786 - 0.7),
        # TP Fib 1.5 = 3285
        _bar(3, 15, p786 - 0.7, p786 - 0.6, 3285.0, 3285.0),
    ]
    out = _run(candles)
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "reverse_confirm"
    assert t["side"] == "DOWN"
    assert t["exit_reason"] == "tp"
    assert abs(t["tp"] - fib_px(3330.0, 3300.0, 1.5)) < 1e-9
    assert abs(t["sl"] - p500) < 1e-9


def test_same_bar_sl_beats_tp():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        # next bar tags both Fib 0 and SL
        _bar(3, 10, p500 - 0.4, 3330.0, p786 - 0.5, 3320.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert len(out["rows"]) == 1
    assert out["rows"][0]["exit_reason"] == "sl"


def test_fill_freezes_box_when_a_new_high_prints():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        # new high 3340 would have redrawn fib0, but trade is open — TP stays 3330
        _bar(3, 10, p500 - 0.4, 3340.0, p500 - 0.5, 3330.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    t = out["rows"][0]
    assert abs(t["fib0"] - 3330.0) < 1e-9
    assert abs(t["tp"] - 3330.0) < 1e-9
    assert t["exit_reason"] == "tp"


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


def test_flatten_at_1330():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        _bar(13, 30, p500 - 0.4, p500 - 0.2, p500 - 0.5, p500 - 0.3),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert len(out["rows"]) == 1
    assert out["rows"][0]["exit_reason"] == "flatten"


def test_shallow_confirm_from_530_until_500_tagged():
    p382 = fib_px(3330.0, 3300.0, 0.382)
    p500 = fib_px(3330.0, 3300.0, 0.5)
    candles = _up_box() + [
        _bar(5, 25, 3324.0, 3325.0, p382 + 0.2, 3323.0),
        _bar(5, 30, 3323.0, 3324.0, p382 - 0.1, 3322.0),
        _bar(5, 35, 3322.0, 3326.0, 3321.5, 3325.0),
        _bar(5, 40, 3325.0, 3330.0, 3324.0, 3330.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_shallow_confirm=True,
    )
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "shallow_confirm"
    assert abs(t["sl"] - p500) < 1e-9
    assert t["exit_reason"] == "tp"


def test_shallow_sl_fib_is_configurable():
    p382 = fib_px(3330.0, 3300.0, 0.382)
    p618 = fib_px(3330.0, 3300.0, 0.618)
    candles = _up_box() + [
        _bar(5, 30, 3323.0, 3324.0, p382 - 0.1, 3322.0),
        _bar(5, 35, 3322.0, 3326.0, 3321.5, 3325.0),
        _bar(5, 40, 3325.0, 3330.0, 3324.0, 3330.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_shallow_confirm=True,
        shallow_confirm_sl_fib=0.618,
    )
    assert abs(out["rows"][0]["sl"] - p618) < 1e-9


def test_tagging_500_kills_shallow_and_allows_continuation():
    p382 = fib_px(3330.0, 3300.0, 0.382)
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = _up_box() + [
        _bar(5, 30, 3323.0, 3324.0, p382 - 0.1, 3322.0),
        _bar(5, 35, 3322.0, 3323.0, mid, mid),
        _bar(5, 40, mid, p500 - 0.2, mid - 0.2, p500 - 0.3),
        _bar(5, 45, p500 - 0.3, 3330.0, p500 - 0.4, 3330.0),
    ]
    out = _run(
        candles,
        enable_reverse_confirm=False,
        enable_shallow_confirm=True,
    )
    assert len(out["rows"]) == 1
    assert out["rows"][0]["setup"] == "continuation"


def test_reverse_ema_fills_on_opposing_touch_beyond_500():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    ema_px = 3310.0
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, mid + 0.2, p786 - 1.0, p786 - 0.4),
        _bar(3, 10, ema_px - 2.0, ema_px + 3.0, ema_px - 2.5, ema_px - 1.0),
        _bar(3, 15, ema_px - 1.0, ema_px - 0.5, 3300.0, 3300.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_reverse_ema=True,
    )
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "reverse_ema"
    assert t["side"] == "DOWN"
    assert t["exit_reason"] == "tp"


def test_close_through_blocks_ema_retest():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    ema_px = 3312.0
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, mid + 0.2, p786 - 1.0, p786 - 0.4),
        _bar(7, 0, ema_px + 5.0, ema_px + 5.5, ema_px - 0.2, ema_px + 2.0),
        _bar(7, 5, ema_px + 2.0, 3330.0, ema_px + 1.0, 3330.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_reverse_ema=False,
        enable_ema_retest=True,
    )
    assert out["rows"] == []


def test_ema_retest_through_fib0_sl_is_236():
    """DOWN, entry below Fib 0: SL = .236, TP is an extension in front (not Fib 0)."""
    ema_px = 3295.0
    fib0, fib1 = 3300.0, 3330.0
    candles = _seed_ema(ema_px) + [
        _bar(1, 0, 3325.0, 3330.0, 3324.0, 3326.0),
        _bar(2, 0, 3310.0, 3311.0, 3300.0, 3302.0),
        _bar(7, 0, ema_px - 4.0, ema_px + 4.0, ema_px - 4.5, ema_px - 1.0),
        _bar(7, 5, ema_px - 1.0, ema_px, ema_px - 2.0, ema_px - 0.5),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "ema_retest"
    assert t["side"] == "DOWN"
    assert abs(t["sl"] - fib_px(fib0, fib1, 0.236)) < 1e-6
    assert t["tp"] < t["entry"]
    assert t["exit_reason"] != "tp" or t["pts"] > 0


def test_ema_retest_inside_0_236_sl_is_382():
    """UP, entry between Fib 0 and .236: SL = .382, TP = Fib 0."""
    fib0, fib1 = 3330.0, 3300.0
    ema_px = 3324.0  # just inside the box
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(7, 0, ema_px + 3.0, ema_px + 3.5, ema_px - 2.0, ema_px + 0.5),
        _bar(7, 5, ema_px + 0.5, 3330.0, ema_px, 3330.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "ema_retest"
    assert t["side"] == "UP"
    assert t["entry"] < fib0
    assert abs(t["sl"] - fib_px(fib0, fib1, 0.382)) < 1e-6
    assert abs(t["tp"] - fib0) < 1e-9


def test_ema_retest_does_not_buy_when_asia_closed_below_mid():
    """Later high (engine UP) but 06:00 close in the lower half → no longs."""
    ema_px = 3312.0
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(5, 55, 3312.0, 3313.0, 3308.0, 3309.0),  # below mid 3315, no new low
        _bar(7, 0, ema_px + 4.0, ema_px + 4.5, ema_px - 2.0, ema_px + 1.0),  # dip from above
        _bar(7, 5, ema_px + 1.0, 3330.0, ema_px, 3328.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    assert all(t["side"] != "UP" for t in out["rows"])
    assert all(t["setup"] != "ema_retest" or t["side"] == "DOWN" for t in out["rows"])


def test_ema_retest_shorts_from_below_when_asia_closed_lower():
    """Same box: bounce from below EMA is a short, not a buy."""
    ema_px = 3310.0
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(5, 55, 3312.0, 3313.0, 3308.0, 3309.0),
        _bar(7, 0, ema_px - 3.0, ema_px + 2.0, ema_px - 3.5, ema_px - 0.5),
        _bar(7, 5, ema_px - 0.5, ema_px, 3300.0, 3300.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "ema_retest"
    assert t["side"] == "DOWN"
    assert t["fib0"] == 3300.0  # Fib 0 is the low when last Asia leg is down
    assert t["exit_reason"] == "tp"


def test_ema_retest_as_first_trade_after_0700():
    ema_px = 3320.0
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(7, 0, ema_px + 4.0, ema_px + 4.5, ema_px - 2.0, ema_px + 1.0),
        _bar(7, 5, ema_px + 1.0, 3330.0, ema_px + 0.5, 3330.0),
    ]
    out = _run(
        candles,
        enable_continuation=False,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    assert len(out["rows"]) == 1
    assert out["rows"][0]["setup"] == "ema_retest"
    assert out["rows"][0]["side"] == "UP"
    assert out["rows"][0]["exit_reason"] == "tp"


def test_box2_after_early_exit_when_range_grows():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    fib0_b2, fib1_b2 = 3340.0, 3300.0
    p500_b2 = fib_px(fib0_b2, fib1_b2, 0.5)
    p786_b2 = fib_px(fib0_b2, fib1_b2, 0.786)
    mid2 = (p500_b2 + p786_b2) / 2.0
    candles = _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        _bar(3, 10, p500 - 0.4, 3330.0, p500 - 0.5, 3330.0),
        _bar(4, 0, 3330.0, 3340.0, 3329.0, 3338.0),
        _bar(4, 5, 3338.0, 3339.0, mid2, mid2),
        _bar(4, 10, mid2, p500_b2 - 0.2, mid2 - 0.3, p500_b2 - 0.4),
        _bar(4, 15, p500_b2 - 0.4, 3340.0, p500_b2 - 0.5, 3340.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert len(out["rows"]) == 2
    assert out["rows"][0]["box_n"] == 1
    assert out["rows"][1]["box_n"] == 2
    assert out["rows"][1]["setup"] == "continuation"
    assert abs(out["rows"][1]["fib0"] - 3340.0) < 1e-9


def test_continuation_down_box():
    # Later low → DOWN. Fib0=3300, Fib1=3330.
    candles = [
        _bar(1, 0, 3325.0, 3330.0, 3324.0, 3326.0),
        _bar(2, 0, 3310.0, 3311.0, 3300.0, 3302.0),
    ]
    p500 = fib_px(3300.0, 3330.0, 0.5)
    p786 = fib_px(3300.0, 3330.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles += [
        _bar(3, 0, 3310.0, mid, 3308.0, mid),
        _bar(3, 5, mid, mid + 0.2, p500 + 0.2, p500 + 0.3),  # bearish, in band
        _bar(3, 10, p500 + 0.3, p500 + 0.4, 3300.0, 3300.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert len(out["rows"]) == 1
    t = out["rows"][0]
    assert t["setup"] == "continuation"
    assert t["side"] == "DOWN"
    assert t["exit_reason"] == "tp"
    assert abs(t["tp"] - 3300.0) < 1e-9


def test_late_tp_does_not_unlock_trade_two():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    ema_px = 3320.0
    candles = _seed_ema(ema_px) + _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        _bar(8, 0, p500 - 0.4, 3330.0, p500 - 0.5, 3330.0),
        # valid opposing EMA retest after 07:00, but trade 1 died after 06:00
        _bar(8, 5, ema_px + 4.0, ema_px + 4.5, ema_px - 2.0, ema_px + 1.0),
    ]
    out = _run(
        candles,
        enable_reverse_confirm=False,
        enable_ema_retest=True,
    )
    assert len(out["rows"]) == 1
    assert out["rows"][0]["exit_reason"] == "tp"
    assert out["rows"][0]["setup"] == "continuation"


def test_box_ignores_bars_before_session_open():
    p500 = fib_px(3330.0, 3300.0, 0.5)
    p786 = fib_px(3330.0, 3300.0, 0.786)
    mid = (p500 + p786) / 2.0
    candles = [
        _bar(0, 30, 3390.0, 3400.0, 3388.0, 3392.0),
    ] + _up_box() + [
        _bar(3, 0, 3320.0, 3322.0, mid, mid),
        _bar(3, 5, mid, p500 - 0.2, mid - 0.4, p500 - 0.4),
        _bar(3, 10, p500 - 0.4, 3330.0, p500 - 0.5, 3330.0),
    ]
    out = _run(candles, enable_reverse_confirm=False)
    assert abs(out["rows"][0]["box_high"] - 3330.0) < 1e-9
    assert abs(out["rows"][0]["fib0"] - 3330.0) < 1e-9

