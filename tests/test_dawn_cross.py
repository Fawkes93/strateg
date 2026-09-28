"""Dawn Cross: 5m EMA cross in the Moldova dawn window, then a pullback fill."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backtest.candles import Candle
from backtest.dawn_cross import (
    DawnCrossParams,
    DawnCrossTrade,
    _summary,
    ema_series,
    in_window,
    run_dawn_cross,
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
