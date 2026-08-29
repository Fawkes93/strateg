from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backtest.candles import Candle
from backtest.dukascopy import Tick
from backtest.overnight_break import (
    OvernightParams,
    OvernightSkip,
    OvernightTrade,
    _asia_extensions,
    _decision_line,
    _excursion_from,
    _mk_skip,
    asia_window_start_utc,
    entry_label,
    run_overnight,
    summarize_overnight,
    trail_arm_for_range,
)


def _tick(ts, mid, spread=0.2):
    half = spread / 2.0
    return Tick(ts=ts, bid=mid - half, ask=mid + half)


def test_entry_and_decision_labels():
    assert entry_label("ema_touch") == "EMA touch"
    assert entry_label("higher_close") == "Higher close resume"
    assert entry_label("lower_close") == "Lower close resume"
    line = _decision_line(
        reason="ema_touch",
        side="UP",
        wait_i=2,
        wait_n=8,
        ema=3312.4,
        prev_close=3310.0,
        signal_close=3311.0,
        entry=3312.38,
        break_pts=280.0,
        entry_vs_ema_pts=-2.0,
        close_vs_prev_pts=100.0,
        same_bar_ema=False,
        pullback_mode="required",
    )
    assert "EMA touch" in line
    assert "wait 2/8" in line
    assert "break +280 pts" in line
    resume = _decision_line(
        reason="higher_close",
        side="UP",
        wait_i=1,
        wait_n=8,
        ema=3312.4,
        prev_close=3315.0,
        signal_close=3318.2,
        entry=3318.2,
        break_pts=200.0,
        entry_vs_ema_pts=None,
        close_vs_prev_pts=320.0,
        same_bar_ema=True,
        pullback_mode="required",
    )
    assert "Higher close resume" in resume
    assert "EMA also touched this bar (close wins)" in resume


def test_asia_extensions_and_skip_fields():
    tz = ZoneInfo("UTC")
    t0 = datetime(2025, 5, 6, 7, 0, tzinfo=tz)
    candles = [
        Candle(
            open_time=t0,
            close_time=t0 + timedelta(minutes=15),
            open=3300.0,
            high=3310.0,
            low=3280.0,
            close=3305.0,
            is_closed=True,
        )
    ]
    above, below = _asia_extensions(candles, asia_high=3300.0, asia_low=3290.0, ps=0.01)
    assert above == 1000.0
    assert below == 1000.0
    s = _mk_skip(
        t0.date(),
        "no_pullback",
        side="UP",
        asia_range_pts=500.0,
        break_price=3305.0,
        max_adv_pts=220.0,
        max_adv_price=3302.8,
        max_above_asia_pts=above,
        max_below_asia_pts=below,
    )
    assert s.reason == "no_pullback"
    assert s.max_adv_price == 3302.8


def test_excursion_tracks_opposite_peak():
    tz = ZoneInfo("UTC")
    start = datetime(2025, 5, 6, 8, 0, tzinfo=timezone.utc)
    ticks = []
    px = 3300.0
    # go +2 then -5 then +1 (pts at 0.01 → 200 / 500 / 100)
    path = [3300.0, 3302.0, 3295.0, 3301.0]
    for i, p in enumerate(path):
        ticks.append(_tick(start + timedelta(seconds=i), p))
    flatten = datetime(2025, 5, 6, 18, 0, tzinfo=tz)
    fav, adv, best, worst = _excursion_from(
        ticks,
        0,
        side="UP",
        entry=3300.0,
        ps=0.01,
        tz=tz,
        flatten_local=flatten,
        max_hold_hours=10.0,
    )
    assert round(fav, 1) == 200.0
    assert round(adv, 1) == 500.0
    assert best == 3302.0
    assert worst == 3295.0


def test_run_overnight_records_skip_reason():
    # Enough 15m closes for a local day, but too few Asia bars → thin_asia skip
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    ticks = [
        _tick(start + timedelta(minutes=15 * i + s), 3300.0 + i * 0.01)
        for i in range(8)
        for s in (0, 1)
    ]
    out = run_overnight(ticks, symbol="XAU/USD", params=OvernightParams())
    assert out["trades"] == 0
    assert out["skipped"] >= 1
    assert out["skips"]
    assert out["skips"][0]["reason"] in ("thin_asia", "no_candles", "no_break", "asia_too_small")


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


def test_chunk_lookback_starts_five_days_before_month():
    from backtest.overnight_jobs import _chunk_lookback_start

    summer = _chunk_lookback_start("2026-04-01", OvernightParams())
    assert summer == datetime(2026, 3, 27, 0, 0, tzinfo=timezone.utc)
    winter = _chunk_lookback_start("2026-01-01", OvernightParams())
    assert winter == datetime(2025, 12, 27, 0, 0, tzinfo=timezone.utc)


def test_month_chunks_split_calendar_months():
    from backtest.overnight_jobs import _month_chunks

    assert _month_chunks("2025-01-01", "2025-01-01") == []
    assert _month_chunks("2025-01-15", "2025-03-01") == [
        ("2025-01-15", "2025-02-01"),
        ("2025-02-01", "2025-03-01"),
    ]
    assert _month_chunks("2025-12-01", "2026-02-01") == [
        ("2025-12-01", "2026-01-01"),
        ("2026-01-01", "2026-02-01"),
    ]


def test_prepend_asia_lookback_fetches_dst_prefix_hours():
    from backtest import overnight_jobs as jobs
    from backtest.overnight_jobs import OvernightJobParams, _prepend_asia_lookback

    seen = {}
    orig = jobs.fetch_hours_parallel

    def fake(symbol, hours, **kwargs):
        seen["hours"] = list(hours)
        return []

    jobs.fetch_hours_parallel = fake
    try:
        summer = OvernightJobParams(date_from="2026-04-01", date_to="2026-05-01")
        _prepend_asia_lookback([], summer, OvernightParams(), None)
        assert seen["hours"][0] == datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
        assert seen["hours"][-1] == datetime(2026, 3, 31, 23, 0, tzinfo=timezone.utc)
        assert len(seen["hours"]) == 3

        winter = OvernightJobParams(date_from="2026-01-01", date_to="2026-02-01")
        _prepend_asia_lookback([], winter, OvernightParams(), None)
        assert seen["hours"][0] == datetime(2025, 12, 31, 22, 0, tzinfo=timezone.utc)
        assert len(seen["hours"]) == 2
    finally:
        jobs.fetch_hours_parallel = orig


def test_asia_window_start_utc_follows_dst():
    summer = asia_window_start_utc(date(2026, 4, 1))
    assert summer == datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
    winter = asia_window_start_utc(date(2026, 1, 1))
    assert winter == datetime(2025, 12, 31, 22, 0, tzinfo=timezone.utc)
    wrap = asia_window_start_utc(
        date(2026, 4, 1), asia_start_hour=22, asia_end_hour=7
    )
    assert wrap == datetime(2026, 3, 31, 19, 0, tzinfo=timezone.utc)


def _apr1_params(**kwargs):
    base = dict(
        timezone="Europe/Bucharest",
        pullback_mode="off",
        min_asia_range_pts=300.0,
        min_break_pts_above=200.0,
        min_break_pts_below=200.0,
        max_break_candles_after=8,
    )
    base.update(kwargs)
    return OvernightParams(**base)


def test_full_asia_lookback_prevents_false_down_break():
    """2026-04-01 shape: true Asia low is before UTC midnight; 07:00 close is inside it."""
    start = datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
    utc_midnight = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    lookback_low = datetime(2026, 3, 31, 22, 30, tzinfo=timezone.utc)  # 01:30 Bucharest
    trunc_low = datetime(2026, 4, 1, 2, 30, tzinfo=timezone.utc)  # 05:30 Bucharest
    asia_high_bar = datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc)  # 04:00 Bucharest
    break_bar = datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc)  # 07:00 Bucharest
    overrides = {
        lookback_low: (3310.0, 3312.0, 3290.0, 3308.0),
        asia_high_bar: (3310.0, 3320.0, 3308.0, 3315.0),
        trunc_low: (3312.0, 3315.0, 3305.0, 3308.0),
        break_bar: (3310.0, 3311.0, 3299.0, 3300.0),
    }
    full = _ohlc_ticks(start, 44, overrides=overrides)
    utc_from_idx = next(i for i, t in enumerate(full) if t.ts >= utc_midnight)
    truncated = full[utc_from_idx:]
    params = _apr1_params()

    false_break = run_overnight(truncated, symbol="XAU/USD", params=params)
    assert false_break["trades"] == 1
    assert false_break["rows"][0]["side"] == "DOWN"
    assert false_break["rows"][0]["local_date"] == "2026-04-01"

    honest = run_overnight(full, symbol="XAU/USD", params=params)
    assert honest["trades"] == 0
    skips = [s for s in honest["skips"] if s["local_date"] == "2026-04-01"]
    assert skips and skips[0]["reason"] == "no_break"
    assert skips[0]["asia_low"] == 3290.0


def test_overnight_keeps_local_hour_zero_despite_candle_ignore():
    start = datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
    hour0_low = datetime(2026, 3, 31, 21, 15, tzinfo=timezone.utc)  # 00:15 Bucharest
    asia_high_bar = datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc)
    trunc_low = datetime(2026, 4, 1, 2, 30, tzinfo=timezone.utc)
    break_bar = datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        44,
        overrides={
            hour0_low: (3310.0, 3312.0, 3290.0, 3308.0),
            asia_high_bar: (3310.0, 3320.0, 3308.0, 3315.0),
            trunc_low: (3312.0, 3315.0, 3305.0, 3308.0),
            break_bar: (3310.0, 3311.0, 3299.0, 3300.0),
        },
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=_apr1_params())
    skips = [s for s in out["skips"] if s["local_date"] == "2026-04-01"]
    assert out["trades"] == 0
    assert skips and skips[0]["reason"] == "no_break"
    assert skips[0]["asia_low"] == 3290.0


def test_wait1_resume_uses_break_close_not_prior_bar():
    """Wait candle 1 must compare to the break close, not the last Asia close."""
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    last_asia = datetime(2025, 5, 6, 6, 45, tzinfo=timezone.utc)
    break_bar = datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc)
    wait1 = datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        32,
        overrides={
            datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (
                3310.0,
                3320.0,
                3308.0,
                3315.0,
            ),
            datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (
                3312.0,
                3315.0,
                3305.0,
                3308.0,
            ),
            last_asia: (3310.0, 3312.0, 3308.0, 3310.0),
            break_bar: (3310.0, 3311.0, 3299.0, 3300.0),
            # Between last Asia close (3310) and break close (3300):
            # old bug would fire lower-close; correct prev is 3300.
            wait1: (3300.0, 3308.0, 3299.5, 3307.0),
        },
    )
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=True,
        ema_period=100,  # no EMA yet; resume only
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        max_break_candles_after=8,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips
    assert skips[0]["reason"] == "no_pullback"


def _utc_down_break_ticks(*wait_ohlcs):
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    wait1 = wait_ohlcs[0] if wait_ohlcs else (3296.0, 3298.0, 3294.0, 3296.0)
    overrides = {
        datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (
            3310.0,
            3320.0,
            3308.0,
            3315.0,
        ),
        datetime(2025, 5, 6, 5, 30, tzinfo=timezone.utc): (
            3312.0,
            3315.0,
            3305.0,
            3308.0,
        ),
        datetime(2025, 5, 6, 6, 45, tzinfo=timezone.utc): (
            3310.0,
            3312.0,
            3308.0,
            3310.0,
        ),
        datetime(2025, 5, 6, 7, 0, tzinfo=timezone.utc): (
            3310.0,
            3311.0,
            3299.0,
            3300.0,
        ),
        datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc): wait1,
    }
    # Later wait bars stay below EMA so they cannot fake an EMA touch.
    for i in range(1, 8):
        t = datetime(2025, 5, 6, 7, 15, tzinfo=timezone.utc) + timedelta(minutes=15 * i)
        overrides[t] = (
            wait_ohlcs[i]
            if i < len(wait_ohlcs)
            else (3296.0, 3298.0, 3294.0, 3296.0)
        )
    return _ohlc_ticks(start, 40, overrides=overrides)


def test_resume_off_ignores_lower_close():
    ticks = _utc_down_break_ticks((3300.0, 3302.0, 3294.0, 3295.0))
    required = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=True,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
    )
    ema_only = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
    )
    with_resume = run_overnight(ticks, symbol="XAU/USD", params=required)
    assert with_resume["trades"] == 1
    assert with_resume["rows"][0]["entry_reason"] == "lower_close"

    out = run_overnight(ticks, symbol="XAU/USD", params=ema_only)
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback"
    assert "close resume off" in (skips[0].get("decision") or "")


def test_resume_off_enters_on_ema_touch():
    ticks = _utc_down_break_ticks((3300.0, 3320.0, 3299.0, 3308.0))
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "ema_touch"
    assert out["rows"][0]["side"] == "DOWN"


def test_legacy_ema_pullback_mode_aliases_resume_off():
    ticks = _utc_down_break_ticks((3300.0, 3302.0, 3294.0, 3295.0))
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="ema",
        use_higher_close=True,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback"


def test_trail_arm_for_range_caps_asia_size():
    fixed = OvernightParams(trail_arm_mode="fixed", trail_arm_pts=400.0)
    assert trail_arm_for_range(fixed, 1500.0) == 400.0
    asia = OvernightParams(trail_arm_mode="asia", trail_arm_cap_pts=2000.0)
    assert trail_arm_for_range(asia, 1500.0) == 1500.0
    assert trail_arm_for_range(asia, 4000.0) == 2000.0
    uncapped = OvernightParams(trail_arm_mode="asia", trail_arm_cap_pts=0.0)
    assert trail_arm_for_range(uncapped, 4000.0) == 4000.0


def test_asia_trail_arm_recorded_on_trade():
    start = datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
    utc_midnight = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    trunc_low = datetime(2026, 4, 1, 2, 30, tzinfo=timezone.utc)
    asia_high_bar = datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc)
    break_bar = datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc)
    full = _ohlc_ticks(
        start,
        44,
        overrides={
            asia_high_bar: (3310.0, 3320.0, 3308.0, 3315.0),
            trunc_low: (3312.0, 3315.0, 3305.0, 3308.0),
            break_bar: (3310.0, 3311.0, 3299.0, 3300.0),
        },
    )
    utc_from_idx = next(i for i, t in enumerate(full) if t.ts >= utc_midnight)
    truncated = full[utc_from_idx:]
    params = _apr1_params(
        trail_arm_mode="asia",
        trail_arm_cap_pts=2000.0,
        trail_arm_pts=400.0,
    )
    out = run_overnight(truncated, symbol="XAU/USD", params=params)
    assert out["trades"] == 1
    row = out["rows"][0]
    expected = min(row["asia_range_pts"], 2000.0)
    assert row["trail_arm_used"] == expected
    assert expected != 400.0


def _resume_only_params(**kwargs):
    base = dict(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=True,
        ema_period=100,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        max_break_candles_after=8,
    )
    base.update(kwargs)
    return OvernightParams(**base)


def test_resume_closes_1_enters_on_first_opposite_close():
    ticks = _utc_down_break_ticks((3300.0, 3302.0, 3294.0, 3295.0))
    out = run_overnight(ticks, symbol="XAU/USD", params=_resume_only_params(resume_closes=1))
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "lower_close"
    assert out["rows"][0]["wait_i"] == 1


def test_resume_closes_2_skips_single_opposite_close():
    ticks = _utc_down_break_ticks((3300.0, 3302.0, 3294.0, 3295.0))
    out = run_overnight(ticks, symbol="XAU/USD", params=_resume_only_params(resume_closes=2))
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback"
    assert "need 2 consecutive closes" in (skips[0].get("decision") or "")


def test_resume_closes_2_enters_on_second_consecutive():
    ticks = _utc_down_break_ticks(
        (3300.0, 3302.0, 3294.0, 3295.0),
        (3295.0, 3296.0, 3288.0, 3290.0),
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=_resume_only_params(resume_closes=2))
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "lower_close"
    assert row["wait_i"] == 2
    assert "2 consecutive lower closes" in (row.get("decision") or "")


def test_resume_closes_2_resets_streak_on_inside_bar():
    ticks = _utc_down_break_ticks(
        (3300.0, 3302.0, 3294.0, 3295.0),  # lower vs 3300 → streak 1
        (3295.0, 3298.0, 3294.0, 3298.0),  # higher vs 3295 → reset
        (3298.0, 3299.0, 3288.0, 3290.0),  # lower vs 3298 → streak 1
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=_resume_only_params(resume_closes=2))
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback"


def _summary_trade(day, pts, trail_armed=False):
    return OvernightTrade(
        local_date=day,
        side="UP",
        asia_high=3320.0,
        asia_low=3300.0,
        asia_range_pts=2000.0,
        break_ts=day + "T07:00:00+00:00",
        break_price=3322.0,
        break_candle_open=3310.0,
        break_candle_close=3322.0,
        entry_ts=day + "T07:15:00+00:00",
        entry=3322.0,
        entry_reason="break_close",
        sl=3300.0,
        tp=3350.0,
        sl_pts=2200.0,
        tp_pts=2800.0,
        pts=pts,
        trail_armed=trail_armed,
    )


def test_summarize_overnight_by_month():
    trades = [
        _summary_trade("2025-05-06", 200.0, trail_armed=True),
        _summary_trade("2025-05-12", -80.0),
        _summary_trade("2025-06-03", 50.0),
    ]
    skips = [
        OvernightSkip(local_date="2025-05-07", reason="no_break"),
        OvernightSkip(local_date="2025-07-01", reason="thin_asia"),
    ]
    out = summarize_overnight(
        trades, skips, OvernightParams(), symbol="XAU/USD", ticks=10
    )
    months = {m["month"]: m for m in out["by_month"]}
    assert list(months) == ["2025-05", "2025-06", "2025-07"]
    may = months["2025-05"]
    assert may["trades"] == 2
    assert may["skipped"] == 1
    assert may["wins"] == 1
    assert may["losses"] == 1
    assert may["sum_pts"] == 120.0
    assert may["win_pct"] == 50.0
    assert may["trail_armed_n"] == 1
    assert months["2025-06"]["trades"] == 1
    assert months["2025-06"]["sum_pts"] == 50.0
    assert months["2025-06"]["skipped"] == 0
    assert months["2025-07"]["trades"] == 0
    assert months["2025-07"]["skipped"] == 1
    assert out["trades"] == 3
    assert out["sum_pts"] == 170.0
