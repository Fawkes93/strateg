"""Dual-Mode Asia Liquidity Engine — closed-bar rules, box lock, A/B mutex."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backtest.candles import Candle
from backtest.dukascopy import Tick
from backtest.asia_liquidity import (
    AsiaLiqParams,
    lock_asia_box,
    moldova_lock_utc,
    mode_a_side,
    mode_a_targets,
    normalize_box_timezone,
    run_asia_liquidity,
    session_bounds,
    signal_from_candles,
    simulate_partial,
    wilder_atr,
)
from backtest.asia_liquidity_wf import walk_forward_folds
from live_signal import candles_from_rows, emit_signal


def _tick(ts, mid, spread=0.2):
    half = spread / 2.0
    return Tick(ts=ts, bid=mid - half, ask=mid + half)


def _ohlc_ticks(open_dt, o, h, l, c, spread=0.2):
    end = open_dt + timedelta(minutes=15)
    path = [
        (open_dt + timedelta(seconds=1), o),
        (open_dt + timedelta(seconds=25), h),
        (open_dt + timedelta(seconds=50), l),
        (end - timedelta(seconds=4), c),
    ]
    return [_tick(ts, px, spread) for ts, px in path]


def _bar(open_dt, o, h, l, c):
    return Candle(
        open_time=open_dt,
        close_time=open_dt + timedelta(minutes=15),
        open=o,
        high=h,
        low=l,
        close=c,
        is_closed=True,
        tick_count=4,
    )


def _fill_hours(start, hours, o=3305.0, rng=20.0):
    ticks = []
    t = start
    end = start + timedelta(hours=hours)
    while t < end:
        ticks.extend(_ohlc_ticks(t, o, o + rng / 2, o - rng / 2, o + 0.2))
        t += timedelta(minutes=15)
    return ticks


def _asia_session(day, high=3310.0, low=3300.0, mid=3305.0):
    """00:00–07:00 UTC Asia bars inside [low, high]."""
    ticks = []
    t = datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc)
    end = t + timedelta(hours=7)
    i = 0
    while t < end:
        if i == 0:
            ticks.extend(_ohlc_ticks(t, mid, high, mid - 0.5, mid + 0.2))
        elif i == 1:
            ticks.extend(_ohlc_ticks(t, mid, mid + 0.5, low, mid - 0.2))
        else:
            ticks.extend(_ohlc_ticks(t, mid, mid + 1.0, mid - 1.0, mid))
        i += 1
        t += timedelta(minutes=15)
    return ticks


def _research_params(**kw):
    p = AsiaLiqParams(
        timezone="UTC",
        exec_timezone="UTC",
        compression_lookback=0,
        htf_enabled=False,
        spread_filter=False,
        news_mode="off",
        london_wait_minutes=0,
        box_atr_min=0.05,
        box_atr_max=5.0,
        min_range_atr=0.0,
        body_frac=0.0,
        break_buffer_atr=0.0,
        sweep_buffer_atr=0.05,
        mode_b_confirm=True,
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_moldova_lock_follows_dst():
    winter = moldova_lock_utc(date(2026, 1, 15))
    summer = moldova_lock_utc(date(2026, 7, 15))
    assert winter.hour == 5  # EET UTC+2
    assert summer.hour == 4  # EEST UTC+3
    assert normalize_box_timezone("moldova") == "Europe/Chisinau"
    assert normalize_box_timezone("UTC") == "UTC"


def test_session_bounds_utc_and_moldova_exec_stays_utc():
    d = date(2026, 7, 15)
    utc = AsiaLiqParams(timezone="UTC", exec_timezone="UTC")
    _, lock, first, *_ = session_bounds(d, utc)
    assert lock == datetime(2026, 7, 15, 7, 0, tzinfo=timezone.utc)
    assert first == datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc)

    md = AsiaLiqParams(timezone="Europe/Chisinau", exec_timezone="UTC")
    asia_start, lock_m, first_m, _se, _mb, flat = session_bounds(d, md)
    assert lock_m == datetime(2026, 7, 15, 4, 0, tzinfo=timezone.utc)
    # London wait still from 07:00 UTC
    assert first_m == datetime(2026, 7, 15, 7, 30, tzinfo=timezone.utc)
    assert flat == datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
    assert asia_start.astimezone(timezone.utc) < lock_m


def test_box_frozen_after_lock():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    # Spike well above Asia after lock — must not lift the box
    after = _ohlc_ticks(t07, 3308.0, 3400.0, 3307.0, 3309.0)
    # no setup (close still inside) so we inspect skip box
    later = []
    t = t07 + timedelta(minutes=15)
    while t.hour < 12:
        later.extend(_ohlc_ticks(t, 3308.0, 3309.0, 3307.0, 3308.0))
        t += timedelta(minutes=15)
    ticks = warmup + asia + after + later
    out = run_asia_liquidity(ticks, symbol="XAU/USD", params=_research_params())
    rows = [
        r
        for r in (out["rows"] + out["skips"])
        if str(r.get("local_date") or "").startswith("2026-05-06")
    ]
    assert rows, out
    # locked high is 3310, not the 3400 post-lock spike
    highs = [r.get("asia_high") for r in rows if r.get("asia_high") is not None]
    assert highs
    assert max(highs) < 3311.0
    locked = lock_asia_box(
        [
            _bar(datetime(2026, 5, 6, h, m, tzinfo=timezone.utc), 3305, 3310, 3300, 3305)
            for h in range(0, 8)
            for m in (0, 15, 30, 45)
            if h < 7 or (h == 7 and m == 0)
        ],
        datetime(2026, 5, 6, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc),
    )
    assert locked[1] == 3310.0


def test_open_bar_cannot_fill():
    """signal_from_candles refuses the in-progress 15m."""
    start = datetime(2026, 5, 6, 0, 0, tzinfo=timezone.utc)
    candles = []
    t = start
    while t.hour < 8 or (t.hour == 8 and t.minute == 0):
        candles.append(_bar(t, 3305, 3310, 3300, 3305))
        t += timedelta(minutes=15)
    open_bar = Candle(
        open_time=datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc),
        close_time=datetime(2026, 5, 6, 8, 15, tzinfo=timezone.utc),
        open=3312,
        high=3320,
        low=3311,
        close=3318,
        is_closed=False,
    )
    sig = signal_from_candles(
        candles + [open_bar],
        symbol="XAUUSD",
        params=_research_params(),
        asof=datetime(2026, 5, 6, 8, 7, tzinfo=timezone.utc),
    )
    assert sig["mode"] is None
    assert sig["reason"] == "open_bar"


def test_mode_a_and_b_cannot_both_trade():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    # 07:00 bar: wick sweep high then close through (Mode A candidate)
    # close-through should win as Mode A; no Mode B the same day
    a_bar = _ohlc_ticks(t07, 3308.0, 3325.0, 3307.0, 3322.0)
    rest = []
    t = t07 + timedelta(minutes=15)
    while t.hour < 16:
        rest.extend(_ohlc_ticks(t, 3322.0, 3323.0, 3321.0, 3322.0))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + a_bar + rest,
        symbol="XAU/USD",
        params=_research_params(mode_a_enabled=True, mode_b_enabled=True),
    )
    modes = {r["mode"] for r in out["rows"]}
    assert len(out["rows"]) <= 1
    if out["rows"]:
        assert modes <= {"A", "B"}
        assert not ({"A", "B"} <= modes)


def test_mode_a_requires_htf():
    day = date(2026, 5, 6)
    # Down-close 4H history so HTF is short; Mode A long must not fire
    warmup = _fill_hours(
        datetime(2026, 5, 4, 0, 0, tzinfo=timezone.utc), 48, o=3400.0, rng=6.0
    )
    # drift down
    drift = _fill_hours(
        datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 24, o=3320.0, rng=6.0
    )
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    a_bar = _ohlc_ticks(t07, 3308.0, 3328.0, 3307.0, 3324.0)
    rest = []
    t = t07 + timedelta(minutes=15)
    while t.hour < 12:
        rest.extend(_ohlc_ticks(t, 3324.0, 3325.0, 3323.0, 3324.0))
        t += timedelta(minutes=15)
    params = _research_params(
        htf_enabled=True,
        htf_ema_period=3,
        mode_b_enabled=False,
    )
    out = run_asia_liquidity(
        warmup + drift + asia + a_bar + rest,
        symbol="XAU/USD",
        params=params,
    )
    longs = [r for r in out["rows"] if r["mode"] == "A" and r["side"] == "UP"]
    # With HTF on, a long continuation against a down 4H should not print
    assert longs == []


def test_mode_b_does_not_need_htf():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    # Sweep high, close back inside
    sweep = _ohlc_ticks(t07, 3308.0, 3316.0, 3306.0, 3308.0)
    # Confirm bar: no re-break of highs
    confirm = _ohlc_ticks(t07 + timedelta(minutes=15), 3308.0, 3309.5, 3304.0, 3306.0)
    rest = []
    t = t07 + timedelta(minutes=30)
    while t.hour < 16:
        rest.extend(_ohlc_ticks(t, 3306.0, 3307.0, 3304.0, 3305.5))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + sweep + confirm + rest,
        symbol="XAU/USD",
        params=_research_params(
            htf_enabled=True,
            htf_ema_period=3,
            mode_a_enabled=False,
            mode_b_enabled=True,
            mode_b_confirm=True,
        ),
    )
    b = [r for r in out["rows"] if r["mode"] == "B"]
    assert len(b) == 1, out["skip_reasons"]
    assert b[0]["side"] == "DOWN"


def test_flatten_at_16_utc():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    a_bar = _ohlc_ticks(t07, 3308.0, 3325.0, 3307.0, 3322.0)
    rest = []
    t = t07 + timedelta(minutes=15)
    while t < datetime(2026, 5, 6, 16, 5, tzinfo=timezone.utc):
        rest.extend(_ohlc_ticks(t, 3322.0, 3324.0, 3320.0, 3322.0))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + a_bar + rest,
        symbol="XAU/USD",
        params=_research_params(mode_b_enabled=False, flatten_hour=16),
    )
    assert out["rows"], out["skip_reasons"]
    assert out["rows"][0]["exit_reason"] == "flatten"
    exit_ts = datetime.fromisoformat(out["rows"][0]["exit_ts"])
    assert exit_ts.hour == 16


def test_partial_tp1_then_tp2_r_is_half_and_half():
    ticks = []
    t0 = datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc)
    # fill at 100, sl 90 (UP, 10 price = 1000 pts), tp1=110, tp2=118
    ticks.append(_tick(t0, 100.0))
    ticks.append(_tick(t0 + timedelta(minutes=1), 110.0))  # TP1
    ticks.append(_tick(t0 + timedelta(minutes=2), 118.0))  # TP2
    ticks.append(_tick(t0 + timedelta(hours=2), 118.0))
    reason, _, _, pts, tp1, trail, _, _ = simulate_partial(
        ticks,
        [x.ts for x in ticks],
        0,
        side="UP",
        entry=100.0,
        sl=90.0,
        tp1=110.0,
        tp2=118.0,
        flatten_utc=t0 + timedelta(hours=8),
        ps=0.01,
        trail_candles=[],
        trail_bars=3,
        use_trail=False,
        be_offset_px=1.0,
    )
    assert tp1 is True
    assert reason == "tp2"
    # 0.5 * 1000 pts + 0.5 * 1800 pts = 1400
    assert abs(pts - 1400.0) < 1e-6
    sl_pts = 1000.0
    assert abs((pts / sl_pts) - 1.4) < 1e-6


def test_box_width_and_compression_skips():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    # tiny Asia vs ATR → too tight
    asia = _asia_session(day, high=3305.2, low=3305.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    rest = []
    t = t07
    while t.hour < 12:
        rest.extend(_ohlc_ticks(t, 3305.1, 3305.3, 3305.0, 3305.1))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + rest,
        symbol="XAU/USD",
        params=_research_params(box_atr_min=0.25, box_atr_max=0.85),
    )
    assert out["rows"] == []
    assert (
        out["skip_reasons"].get("box_too_tight")
        or out["skip_reasons"].get("box_too_wide")
        or out["skip_reasons"].get("thin_asia")
    )


def test_sweep_without_reclaim_is_not_mode_b():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    # Sweep high, stay outside for >4 bars
    bars = []
    t = t07
    for _ in range(6):
        bars.extend(_ohlc_ticks(t, 3314.0, 3318.0, 3313.0, 3315.0))
        t += timedelta(minutes=15)
    while t.hour < 12:
        bars.extend(_ohlc_ticks(t, 3315.0, 3316.0, 3314.0, 3315.0))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + bars,
        symbol="XAU/USD",
        params=_research_params(mode_a_enabled=False, mode_b_enabled=True),
    )
    assert all(r["mode"] != "B" for r in out["rows"])


def test_reclaim_then_rebreak_skips_mode_b_when_confirm_on():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    sweep = _ohlc_ticks(t07, 3308.0, 3316.0, 3306.0, 3308.0)  # close inside
    rebreak = _ohlc_ticks(
        t07 + timedelta(minutes=15), 3308.0, 3314.0, 3307.0, 3312.0
    )
    rest = []
    t = t07 + timedelta(minutes=30)
    # Stay outside the box so a new reclaim cannot complete
    while t.hour < 12:
        rest.extend(_ohlc_ticks(t, 3312.0, 3313.0, 3311.2, 3312.2))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + sweep + rebreak + rest,
        symbol="XAU/USD",
        params=_research_params(
            mode_a_enabled=False, mode_b_enabled=True, mode_b_confirm=True
        ),
    )
    assert all(r["mode"] != "B" for r in out["rows"])


def test_no_second_mode_a_after_stop():
    day = date(2026, 5, 6)
    warmup = _fill_hours(datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    asia = _asia_session(day, high=3310.0, low=3300.0)
    t07 = datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc)
    a1 = _ohlc_ticks(t07, 3308.0, 3325.0, 3307.0, 3322.0)
    # stop through AsiaMid 3305 immediately
    stop = _ohlc_ticks(t07 + timedelta(minutes=15), 3320.0, 3321.0, 3300.0, 3302.0)
    a2 = _ohlc_ticks(t07 + timedelta(minutes=30), 3308.0, 3330.0, 3307.0, 3328.0)
    rest = []
    t = t07 + timedelta(minutes=45)
    while t.hour < 12:
        rest.extend(_ohlc_ticks(t, 3328.0, 3329.0, 3327.0, 3328.0))
        t += timedelta(minutes=15)
    out = run_asia_liquidity(
        warmup + asia + a1 + stop + a2 + rest,
        symbol="XAU/USD",
        params=_research_params(mode_b_enabled=False, one_trade_per_day=True),
    )
    a_rows = [r for r in out["rows"] if r["mode"] == "A"]
    assert len(a_rows) == 1


def test_weekly_halt_skips_later_days():
    params = _research_params(
        mode_b_enabled=False, weekly_halt_r=0.5, one_trade_per_day=True
    )
    ticks = _fill_hours(datetime(2026, 5, 4, 0, 0, tzinfo=timezone.utc), 20, rng=8.0)
    # Two weekdays: Wed 6 and Thu 7. First trade stops (negative R) beyond 0.5R
    for day in (date(2026, 5, 6), date(2026, 5, 7)):
        ticks += _asia_session(day, high=3310.0, low=3300.0)
        t07 = datetime(day.year, day.month, day.day, 7, 0, tzinfo=timezone.utc)
        ticks += _ohlc_ticks(t07, 3308.0, 3325.0, 3307.0, 3322.0)
        ticks += _ohlc_ticks(t07 + timedelta(minutes=15), 3320.0, 3321.0, 3295.0, 3298.0)
        t = t07 + timedelta(minutes=30)
        while t.hour < 16:
            ticks += _ohlc_ticks(t, 3298.0, 3299.0, 3297.0, 3298.0)
            t += timedelta(minutes=15)
    out = run_asia_liquidity(ticks, symbol="XAU/USD", params=params)
    # Second day should be weekly_halt if first loser was big enough
    reasons = out["skip_reasons"]
    assert reasons.get("weekly_halt") or len(out["rows"]) <= 1


def test_walk_forward_folds_abut_and_do_not_leak():
    folds = walk_forward_folds(date(2022, 1, 1), date(2024, 7, 1), train_months=18, test_months=6)
    assert folds
    for i, fold in enumerate(folds):
        assert fold["train_to"] == fold["test_from"]
        assert fold["train_from"] < fold["train_to"] <= fold["test_to"]
        if i:
            assert folds[i - 1]["test_from"] < fold["test_from"]
    # test window never overlaps its train
    for fold in folds:
        assert not (fold["test_from"] < fold["train_to"] and fold["train_from"] < fold["test_from"])


def test_live_signal_json_keys_and_open_bar():
    start = datetime(2026, 5, 6, 0, 0, tzinfo=timezone.utc)
    rows = []
    t = start
    while t < datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc):
        rows.append(
            {
                "open_time": t.isoformat(),
                "open": 3305,
                "high": 3310,
                "low": 3300,
                "close": 3305,
                "is_closed": True,
            }
        )
        t += timedelta(minutes=15)
    candles = candles_from_rows(rows)
    out = emit_signal(
        candles,
        symbol="XAUUSD",
        params=_research_params(),
        asof=datetime(2026, 5, 6, 7, 30, tzinfo=timezone.utc),
    )
    assert "symbol" in out and "mode" in out and "reason" in out
    open_rows = rows + [
        {
            "open_time": datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc).isoformat(),
            "open": 3312,
            "high": 3320,
            "low": 3311,
            "close": 3318,
            "is_closed": False,
        }
    ]
    refused = emit_signal(
        candles_from_rows(open_rows),
        symbol="XAUUSD",
        params=_research_params(),
        asof=datetime(2026, 5, 6, 8, 5, tzinfo=timezone.utc),
    )
    assert refused["mode"] is None
    assert refused["reason"] == "open_bar"


def test_mode_a_side_helper_and_tp2_nearer():
    c = _bar(
        datetime(2026, 5, 6, 7, 0, tzinfo=timezone.utc),
        3312,
        3320,
        3311,
        3319,
    )
    p = _research_params(break_buffer_atr=0.1, body_frac=0.5, min_range_atr=0.6)
    assert mode_a_side(c, asia_high=3310, asia_low=3300, atr=10.0, params=p) == "UP"
    tp1, tp2 = mode_a_targets("UP", 3320.0, 3305.0, 10.0, p)
    # R=15, 1.8R=27, box=10 → nearer is 10
    assert abs((tp2 - 3320.0) - 10.0) < 1e-9
    p.tp2_select = "farther"
    _, tp2f = mode_a_targets("UP", 3320.0, 3305.0, 10.0, p)
    assert abs((tp2f - 3320.0) - 27.0) < 1e-9


def test_wilder_atr_warmup():
    bars = [
        _bar(datetime(2026, 5, 6, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * i),
             10, 12, 9, 11)
        for i in range(20)
    ]
    atr = wilder_atr(bars, 14)
    assert all(x is None for x in atr[:13])
    assert atr[13] is not None
    assert atr[-1] is not None
