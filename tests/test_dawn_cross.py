"""Dawn Cross: 5m EMA cross in the Moldova dawn window, then a pullback fill."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backtest.candles import Candle, to_utc
from backtest.dawn_cross import (
    DawnCrossParams,
    DawnCrossTrade,
    RV_BARS,
    _summary,
    ema_series,
    in_window,
    ma_line_series,
    ma_line_spec,
    relative_tick_volume,
    run_dawn_cross,
    same_average,
)


ZONE = ZoneInfo("Europe/Chisinau")


def _bar(local, price, *, low=None, high=None):
    if local.tzinfo is None:
        local = local.replace(tzinfo=ZONE)
    o = price
    h = price if high is None else high
    l = price if low is None else low
    c = price
    return Candle(
        open_time=local,
        close_time=local + timedelta(minutes=5),
        open=o,
        high=max(h, o, c),
        low=min(l, o, c),
        close=c,
        is_closed=True,
        tick_count=3,
    )


def _series(start_local, closes, wicks=None):
    bars = []
    t = start_local
    if t.tzinfo is None:
        t = t.replace(tzinfo=ZONE)
    for i, px in enumerate(closes):
        wick = (wicks or {}).get(i)
        if wick:
            bars.append(_bar(t, px, low=wick[0], high=wick[1]))
        else:
            bars.append(_bar(t, px))
        t += timedelta(minutes=5)
    return bars


def test_window_is_two_to_six_moldova():
    inside = datetime(2026, 9, 15, 2, 0, tzinfo=ZONE)
    edge = datetime(2026, 9, 15, 6, 0, tzinfo=ZONE)
    before = datetime(2026, 9, 15, 1, 55, tzinfo=ZONE)
    assert in_window(inside, ZONE, 2, 6)
    assert not in_window(edge, ZONE, 2, 6)
    assert not in_window(before, ZONE, 2, 6)


def test_window_respects_minutes():
    at_230 = datetime(2026, 9, 15, 2, 30, tzinfo=ZONE)
    at_225 = datetime(2026, 9, 15, 2, 25, tzinfo=ZONE)
    at_545 = datetime(2026, 9, 15, 5, 45, tzinfo=ZONE)
    at_550 = datetime(2026, 9, 15, 5, 50, tzinfo=ZONE)
    at_2345 = datetime(2026, 9, 15, 23, 45, tzinfo=ZONE)
    at_0010 = datetime(2026, 9, 16, 0, 10, tzinfo=ZONE)
    at_115 = datetime(2026, 9, 16, 1, 15, tzinfo=ZONE)
    assert in_window(at_230, ZONE, 2, 6, 30, 0)
    assert not in_window(at_225, ZONE, 2, 6, 30, 0)
    assert in_window(at_545, ZONE, 2, 5, 0, 50)
    assert not in_window(at_550, ZONE, 2, 5, 0, 50)
    assert in_window(at_2345, ZONE, 23, 1, 30, 15)
    assert in_window(at_0010, ZONE, 23, 1, 30, 15)
    assert not in_window(at_115, ZONE, 23, 1, 30, 15)


def test_up_cross_buys_on_pullback_to_fast_ema():
    start = datetime(2026, 9, 15, 0, 0, tzinfo=ZONE)
    closes = [100.0] * 30
    closes.extend(100 + i * 2.0 for i in range(1, 16))
    bars = _series(start, closes)
    fast = ema_series(closes, 9)
    slow = ema_series(closes, 20)
    cross_i = next(
        i
        for i in range(1, len(bars))
        if fast[i] is not None
        and slow[i] is not None
        and fast[i - 1] is not None
        and slow[i - 1] is not None
        and fast[i - 1] <= slow[i - 1]
        and fast[i] > slow[i]
        and in_window(bars[i].open_time, ZONE, 2, 6)
    )
    # Bars after the cross stay high, then one bar stabs the fast EMA.
    after = closes[cross_i]
    tail_start = start + timedelta(minutes=5 * (cross_i + 1))
    tail_closes = [after] * 4
    tail = _series(tail_start, tail_closes)
    pre = bars[: cross_i + 1] + tail
    ema_now = ema_series([b.close for b in pre] + [after], 9)
    tag = float(ema_now[-1])
    stab = _bar(
        tail_start + timedelta(minutes=5 * len(tail_closes)),
        after,
        low=min(tag, after) - 1.0,
        high=max(tag, after) + 0.5,
    )
    # Run to TP on the following bars.
    rally_start = stab.open_time + timedelta(minutes=5)
    rally = []
    px = after
    t = rally_start
    for _ in range(12):
        px += 3.0
        rally.append(_bar(t, px, low=px - 0.2, high=px + 0.2))
        t += timedelta(minutes=5)
    out = run_dawn_cross(
        pre + [stab] + rally,
        symbol="XAUUSD",
        params=DawnCrossParams(sl_pts=5000, tp_pts=200, flatten_hour=0),
    )
    assert out["trades"] == 1, out
    row = out["rows"][0]
    assert row["side"] == "UP"
    assert row["exit_reason"] == "TP"
    assert row["pts"] > 0
    assert " " in row["entry_local"]
    assert row["exit_local"]
    # Fill is not the cross bar.
    assert row["entry_ts"] != bars[cross_i].open_time.isoformat()


def test_cross_outside_the_window_does_not_arm():
    start = datetime(2026, 9, 15, 7, 0, tzinfo=ZONE)
    closes = [100.0] * 30
    closes.extend(100 + i * 2.0 for i in range(1, 20))
    bars = _series(start, closes)
    out = run_dawn_cross(
        bars,
        symbol="XAUUSD",
        params=DawnCrossParams(sl_pts=500, tp_pts=500, flatten_hour=0),
    )
    assert out["trades"] == 0


def test_down_cross_sells_and_stop_wins_if_both_print():
    start = datetime(2026, 9, 15, 0, 0, tzinfo=ZONE)
    closes = [200.0] * 30
    closes.extend(200 - i * 2.0 for i in range(1, 16))
    bars = _series(start, closes)
    fast = ema_series(closes, 9)
    slow = ema_series(closes, 20)
    cross_i = next(
        i
        for i in range(1, len(bars))
        if fast[i] is not None
        and slow[i] is not None
        and fast[i - 1] is not None
        and slow[i - 1] is not None
        and fast[i - 1] >= slow[i - 1]
        and fast[i] < slow[i]
        and in_window(bars[i].open_time, ZONE, 2, 6)
    )
    after = closes[cross_i]
    tail_start = start + timedelta(minutes=5 * (cross_i + 1))
    tail = _series(tail_start, [after] * 4)
    pre = bars[: cross_i + 1] + tail
    ema_now = ema_series([b.close for b in pre] + [after], 9)
    tag = float(ema_now[-1])
    stab = _bar(
        tail_start + timedelta(minutes=20),
        after,
        low=min(tag, after) - 0.5,
        high=max(tag, after) + 1.0,
    )
    # Next bar trades through both SL and TP. SL must win.
    entry_guess = tag
    ps = 0.01  # XAU
    sl = entry_guess + 50 * ps
    tp = entry_guess - 50 * ps
    nxt = _bar(
        stab.open_time + timedelta(minutes=5),
        after,
        low=min(tp, sl) - 1,
        high=max(tp, sl) + 1,
    )
    out = run_dawn_cross(
        pre + [stab, nxt],
        symbol="XAUUSD",
        params=DawnCrossParams(sl_pts=50, tp_pts=50, flatten_hour=0),
    )
    assert out["trades"] == 1, out
    row = out["rows"][0]
    assert row["side"] == "DOWN"
    assert row["exit_reason"] == "SL"
    assert row["pts"] < 0


def _up_cross_book():
    start = datetime(2026, 9, 15, 0, 0, tzinfo=ZONE)
    closes = [100.0] * 30
    closes.extend(100 + i * 2.0 for i in range(1, 16))
    bars = _series(start, closes)
    fast = ema_series(closes, 9)
    slow = ema_series(closes, 20)
    cross_i = next(
        i
        for i in range(1, len(bars))
        if fast[i] is not None
        and slow[i] is not None
        and fast[i - 1] is not None
        and slow[i - 1] is not None
        and fast[i - 1] <= slow[i - 1]
        and fast[i] > slow[i]
        and in_window(bars[i].open_time, ZONE, 2, 6)
    )
    after = closes[cross_i]
    tail_start = start + timedelta(minutes=5 * (cross_i + 1))
    tail = _series(tail_start, [after] * 4)
    pre = bars[: cross_i + 1] + tail
    ema_now = ema_series([b.close for b in pre] + [after], 9)
    tag = float(ema_now[-1])
    stab = _bar(
        tail_start + timedelta(minutes=20),
        after,
        low=min(tag, after) - 1.0,
        high=max(tag, after) + 0.5,
    )
    rally = []
    px = after
    t = stab.open_time + timedelta(minutes=5)
    for _ in range(12):
        px += 3.0
        rally.append(_bar(t, px, low=px - 0.2, high=px + 0.2))
        t += timedelta(minutes=5)
    return bars[cross_i], pre + [stab] + rally


def test_start_minute_drops_a_cross_before_the_window():
    cross_bar, book = _up_cross_book()
    cross_open = cross_bar.open_time.astimezone(ZONE)
    late_total = cross_open.hour * 60 + cross_open.minute + 5
    end_total = late_total + 5
    blocked = run_dawn_cross(
        book,
        symbol="XAUUSD",
        params=DawnCrossParams(
            window_start_hour=late_total // 60,
            window_start_minute=late_total % 60,
            window_end_hour=end_total // 60,
            window_end_minute=end_total % 60,
            sl_pts=5000,
            tp_pts=200,
            flatten_hour=0,
        ),
    )
    assert blocked["trades"] == 0, blocked
    opened = run_dawn_cross(
        book,
        symbol="XAUUSD",
        params=DawnCrossParams(
            window_start_hour=cross_open.hour,
            window_start_minute=cross_open.minute,
            window_end_hour=6,
            window_end_minute=0,
            sl_pts=5000,
            tp_pts=200,
            flatten_hour=0,
        ),
    )
    assert opened["trades"] == 1, opened
    row = opened["rows"][0]
    assert row["entry_local"].startswith("2026-09-15 ")
    assert len(row["entry_local"]) == 16
    assert row["exit_local"]


def _pts_trade(day: str, pts: float) -> DawnCrossTrade:
    stamp = day + "T02:00:00+00:00"
    return DawnCrossTrade(
        local_date=day,
        side="UP" if pts >= 0 else "DOWN",
        cross_ts=stamp,
        entry_ts=stamp,
        entry_local=day + " 04:00",
        entry=1.0,
        sl=1.0,
        tp=1.0,
        sl_pts=1.0,
        tp_pts=1.0,
        fast_ema=1.0,
        slow_ema=1.0,
        pullback_ema=1.0,
        exit_ts=stamp,
        exit_local=day + " 05:00",
        exit=1.0,
        exit_reason="TP" if pts > 0 else "SL",
        pts=pts,
    )


def test_one_trade_per_day_keeps_the_first_fill():
    start = datetime(2026, 9, 15, 0, 0, tzinfo=ZONE)
    closes = [100.0] * 30
    closes.extend(100 + i * 4 for i in range(1, 10))
    after = closes[-1]
    closes.extend([after] * 3)
    bars = _series(start, closes)
    tag = float(ema_series(closes + [after], 3)[-1])
    stab_t = start + timedelta(minutes=5 * len(closes))
    stab = _bar(stab_t, after, low=min(tag, after) - 1, high=max(tag, after) + 0.5)
    rally = []
    px = after
    t = stab_t + timedelta(minutes=5)
    for _ in range(6):
        px += 2
        rally.append(_bar(t, px, low=px - 0.2, high=px + 0.2))
        t += timedelta(minutes=5)
    fall_closes = [px - i * 6 for i in range(1, 12)]
    fall = _series(t, fall_closes)
    pre = bars + [stab] + rally + fall
    last = fall_closes[-1]
    tag2 = float(ema_series([b.close for b in pre] + [last], 3)[-1])
    stab2_t = t + timedelta(minutes=5 * len(fall_closes))
    stab2 = _bar(stab2_t, last, low=min(tag2, last) - 0.5, high=max(tag2, last) + 1)
    drop = []
    t2 = stab2_t + timedelta(minutes=5)
    for _ in range(8):
        last -= 2
        drop.append(_bar(t2, last, low=last - 0.2, high=last + 0.2))
        t2 += timedelta(minutes=5)
    book = pre + [stab2] + drop
    common = dict(fast_ema=3, slow_ema=8, pullback_ema=3, sl_pts=5000, tp_pts=50, flatten_hour=0)
    both = run_dawn_cross(
        book,
        symbol="XAUUSD",
        params=DawnCrossParams(one_trade_per_day=False, **common),
    )
    assert both["trades"] == 2, both
    assert both["rows"][0]["local_date"] == both["rows"][1]["local_date"] == "2026-09-15"
    assert both["rows"][0]["side"] == "UP"
    assert both["rows"][1]["side"] == "DOWN"
    first_only = run_dawn_cross(
        book,
        symbol="XAUUSD",
        params=DawnCrossParams(one_trade_per_day=True, **common),
    )
    assert first_only["trades"] == 1, first_only
    assert first_only["rows"][0]["entry_local"] == both["rows"][0]["entry_local"]
    assert first_only["params"]["one_trade_per_day"] is True


def test_streaks_and_months():
    trades = [
        _pts_trade("2026-01-06", 10),
        _pts_trade("2026-01-07", 10),
        _pts_trade("2026-01-08", -5),
        _pts_trade("2026-01-09", 0),
        _pts_trade("2026-02-02", -5),
        _pts_trade("2026-02-03", 10),
    ]
    out = _summary(trades, params=DawnCrossParams(), symbol="XAU/USD", n_bars=1)
    streaks = out["streaks"]
    assert streaks["max_win"] == 2
    assert streaks["max_loss"] == 1
    assert streaks["win_by_len"][2] == 1
    assert streaks["win_by_len"][1] == 1
    assert streaks["loss_by_len"][1] == 2
    assert streaks["current"] == {"side": "win", "len": 1}
    months = {m["month"]: m for m in out["by_month"]}
    assert set(months) == {"2026-01", "2026-02"}
    assert months["2026-01"]["trades"] == 4
    assert months["2026-01"]["wins"] == 2
    assert months["2026-01"]["sum_pts"] == 15
    assert months["2026-01"]["win_pct"] == 50.0
    assert months["2026-02"]["trades"] == 2
    assert months["2026-02"]["sum_pts"] == 5
    assert months["2026-02"]["avg_pts"] == 2.5


def test_same_average_matches_overnight_line_rules():
    ema = ma_line_spec("ema", 9, 2, 99)
    assert same_average(ema, ma_line_spec("EMA", 9, 5, 40))
    assert not same_average(ema, ma_line_spec("hma", 9))
    assert ma_line_spec("hma", 1) == ("hma", 2, 2, 30)
    assert not same_average(
        ma_line_spec("kama", 10, 2, 30),
        ma_line_spec("kama", 10, 2, 40),
    )
    assert same_average(
        ma_line_spec("kama", 10, 2, 30),
        ma_line_spec("kama", 10, 2, 30),
    )
    assert ma_line_spec("nope", 4)[0] == "ema"


def test_pullback_fill_uses_kama_hma_or_zlema():
    start = datetime(2026, 9, 15, 0, 0, tzinfo=ZONE)
    closes = [100.0] * 30
    closes.extend(100 + i * 2.0 for i in range(1, 16))
    bars = _series(start, closes)
    fast = ema_series(closes, 9)
    slow = ema_series(closes, 20)
    cross_i = next(
        i
        for i in range(1, len(bars))
        if fast[i] is not None
        and slow[i] is not None
        and fast[i - 1] is not None
        and slow[i - 1] is not None
        and fast[i - 1] <= slow[i - 1]
        and fast[i] > slow[i]
        and in_window(bars[i].open_time, ZONE, 2, 6)
    )
    after = closes[cross_i]
    tail_start = start + timedelta(minutes=5 * (cross_i + 1))
    pre = bars[: cross_i + 1] + _series(tail_start, [after] * 4)
    base = [b.close for b in pre] + [after]
    ema_level = float(ema_series(base, 9)[-1])
    for kind in ("kama", "hma", "zlema"):
        spec = ma_line_spec(kind, 9, 2, 30)
        level = ma_line_series(base, spec)[-1]
        assert level is not None, kind
        level = float(level)
        assert abs(level - ema_level) > 1e-6, kind
        stab = _bar(
            tail_start + timedelta(minutes=20),
            after,
            low=min(level, after) - 0.25,
            high=max(level, after) + 0.25,
        )
        rally = []
        px = after
        t = stab.open_time + timedelta(minutes=5)
        for _ in range(12):
            px += 3.0
            rally.append(_bar(t, px, low=px - 0.2, high=px + 0.2))
            t += timedelta(minutes=5)
        out = run_dawn_cross(
            pre + [stab] + rally,
            symbol="XAUUSD",
            params=DawnCrossParams(
                pull_ma=kind,
                pullback_ema=9,
                pull_kama_fast=2,
                pull_kama_slow=30,
                sl_pts=5000,
                tp_pts=200,
                flatten_hour=0,
            ),
        )
        assert out["trades"] == 1, (kind, out)
        row = out["rows"][0]
        assert row["side"] == "UP"
        assert abs(row["entry"] - level) < 1e-6
        assert abs(row["pullback_ema"] - level) < 1e-6
        assert out["params"]["pull_ma"] == kind
        assert out["params"]["fast_ma"] == "ema"


def test_relative_tick_volume_excludes_the_cross_bar():
    start = datetime(2026, 9, 15, 0, 0, tzinfo=ZONE)
    # 47 quiet bars, one heavy bar, then the cross bar, then the next bar.
    ticks = [1] * 47 + [49, 10, 4]
    bars = _series(start, [100.0] * len(ticks))
    for bar, tick in zip(bars, ticks):
        bar.tick_count = tick
    rv = relative_tick_volume(bars)
    assert RV_BARS == 48
    assert rv[47] is None
    # Prior 48 are 47 ones plus 49. The 10 on this bar stays out of the average.
    assert rv[48] == 10 / 2
    # The window then steps forward and drops the oldest 1.
    assert rv[49] == 4 / (105 / 48)
    zeros = _series(start, [100.0] * 49)
    for bar in zeros:
        bar.tick_count = 0
    zeros[-1].tick_count = 5
    assert relative_tick_volume(zeros)[48] is None


def _rv_params(**overrides):
    base = dict(
        fast_ema=3,
        slow_ema=8,
        pullback_ema=40,
        sl_pts=5000,
        tp_pts=5000,
        flatten_hour=0,
        rv_max=1,
    )
    base.update(overrides)
    return DawnCrossParams(**base)


def _rv_start():
    return datetime(2026, 9, 14, 12, 0, tzinfo=ZONE)


def _rv_rise():
    # 168 flat bars land on 02:00. The rise crosses up on that first bar.
    return [100.0] * 168 + [103, 108, 116, 128, 142, 155, 160, 160, 160, 160]


def _set_ticks(bars, tick):
    for bar in bars:
        bar.tick_count = tick


def _crosses(bars, fast_p=3, slow_p=8):
    closes = [bar.close for bar in bars]
    fast = ema_series(closes, fast_p)
    slow = ema_series(closes, slow_p)
    found = []
    for i in range(1, len(bars)):
        if None in (fast[i - 1], slow[i - 1], fast[i], slow[i]):
            continue
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
            found.append((i, "UP"))
        elif fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            found.append((i, "DOWN"))
    return found


def _tag_bar(bars, close):
    closes = [bar.close for bar in bars] + [close]
    level = float(ema_series(closes, 40)[-1])
    return _bar(
        bars[-1].open_time + timedelta(minutes=5),
        close,
        low=min(close, level) - 0.5,
        high=max(close, level) + 0.5,
    )


def _long_arm_book():
    bars = _series(_rv_start(), _rv_rise())
    tag = _tag_bar(bars, bars[-1].close)
    book = bars + [tag]
    _set_ticks(book, 10)
    return book


def test_rv_at_most_one_arms_and_a_busier_bar_does_not():
    book = _long_arm_book()
    up_i = next(i for i, side in _crosses(book) if side == "UP")
    assert up_i >= RV_BARS
    opened = run_dawn_cross(book, symbol="XAUUSD", params=_rv_params())
    assert opened["trades"] == 1, opened
    assert opened["rows"][0]["side"] == "UP"
    assert opened["params"]["rv_max"] == 1

    busy = _long_arm_book()
    busy_i = next(i for i, side in _crosses(busy) if side == "UP")
    busy[busy_i].tick_count = 11
    blocked = run_dawn_cross(busy, symbol="XAUUSD", params=_rv_params())
    assert blocked["trades"] == 0, blocked

    # Dropping the oldest of the 48 prior bars out of the average would hide this.
    shifted = _long_arm_book()
    shift_i = next(i for i, side in _crosses(shifted) if side == "UP")
    _set_ticks(shifted, 20)
    shifted[shift_i].tick_count = 20
    shifted[shift_i - RV_BARS].tick_count = 1
    assert run_dawn_cross(shifted, symbol="XAUUSD", params=_rv_params())["trades"] == 0


def test_rv_filter_blocks_a_cross_before_48_bars_exist():
    _cross_bar, book = _up_cross_book()
    opened = run_dawn_cross(
        book,
        symbol="XAUUSD",
        params=DawnCrossParams(sl_pts=5000, tp_pts=200, flatten_hour=0, rv_max=0),
    )
    assert opened["trades"] == 1, opened
    cross_ts = opened["rows"][0]["cross_ts"]
    idx = next(i for i, bar in enumerate(book) if to_utc(bar.close_time).isoformat() == cross_ts)
    assert idx < RV_BARS
    blocked = run_dawn_cross(
        book,
        symbol="XAUUSD",
        params=DawnCrossParams(sl_pts=5000, tp_pts=200, flatten_hour=0, rv_max=1),
    )
    assert blocked["trades"] == 0, blocked


def test_blocked_opposite_cross_disarms():
    rise = _series(_rv_start(), _rv_rise())
    dip = _series(rise[-1].open_time + timedelta(minutes=5), [156, 150, 142, 134, 126, 118, 112, 108, 104])
    held = rise + dip
    crosses = _crosses(held)
    assert [side for _i, side in crosses] == ["UP", "DOWN"], crosses
    up_i, down_i = crosses[0][0], crosses[1][0]
    pull = ema_series([bar.close for bar in held], 40)
    for i in range(up_i + 1, down_i + 1):
        level = float(pull[i])
        assert not (held[i].low <= level <= held[i].high)
    tag = _tag_bar(held, held[-1].close)
    book = held + [tag]
    _set_ticks(book, 10)

    still_long = run_dawn_cross(rise + [_tag_bar(rise, rise[-1].close)], symbol="XAUUSD", params=_rv_params())
    assert still_long["trades"] == 1, still_long
    assert still_long["rows"][0]["side"] == "UP"

    book[down_i].tick_count = 40
    blocked = run_dawn_cross(book, symbol="XAUUSD", params=_rv_params())
    assert blocked["trades"] == 0, blocked

    for bar in book:
        bar.tick_count = 10
    replaced = run_dawn_cross(book, symbol="XAUUSD", params=_rv_params())
    assert replaced["trades"] == 1, replaced
    assert replaced["rows"][0]["side"] == "DOWN"

    same_bars = held + [_tag_bar(held, held[-1].close)]
    _set_ticks(same_bars, 10)
    same_bars[_crosses(same_bars)[1][0]].tick_count = 40
    ignored = run_dawn_cross(same_bars, symbol="XAUUSD", params=_rv_params(rv_max=0))
    assert ignored["trades"] == 1, ignored
    assert ignored["rows"][0]["side"] == "DOWN"
