from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backtest.candles import Candle
from backtest.dukascopy import Tick
from backtest.overnight_break import (
    OvernightParams,
    OvernightSkip,
    OvernightTrade,
    _asia_extensions,
    _compute_sl_tp,
    _decision_line,
    _excursion_from,
    _mk_skip,
    asia_window_start_utc,
    entry_label,
    late_short_blocked,
    run_overnight,
    timeout_quality_blocked,
    summarize_overnight,
    trail_arm_for_range,
    trail_setup,
    _simulate_from_entry,
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
    )
    assert round(fav, 1) == 200.0
    assert round(adv, 1) == 500.0
    assert best == 3302.0
    assert worst == 3295.0


def test_trade_max_fav_adv_run_until_flatten_past_sl():
    """Short hits a tight SL on 07:15, then 09:00 prints a deeper adverse high and a larger fav low."""
    quiet = (3296.0, 3298.0, 3294.0, 3296.0)
    ticks = _utc_down_break_ticks(
        (3301.0, 3302.0, 3300.4, 3301.0),
        quiet,
        quiet,
        quiet,
        quiet,
        quiet,
        quiet,
        (3296.0, 3315.0, 3280.0, 3290.0),
    )
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="off",
        sl_mode="fixed",
        sl_fixed_pts=50.0,
        tp_mode="fixed",
        tp_fixed_pts=100000.0,
        trail_arm_mode="off",
        trail_arm_pts=0.0,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        flatten_hour=18,
        max_hold_hours=0.5,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["side"] == "DOWN"
    assert row["exit_reason"] == "sl"
    assert abs(row["max_adv_price"] - 3315.0) < 1e-6
    assert abs(row["max_fav_price"] - 3280.0) < 1e-6
    assert row["max_adv_pts"] > row["sl_pts"] * 10
    assert row["max_fav_pts"] > 1500.0


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


def test_empty_run_error_does_not_look_like_success():
    from backtest.overnight_jobs import _empty_run_error, _rows_to_trades
    from backtest.job_memory import retain_result

    assert "No ticks loaded" in _empty_run_error([], total_ticks=0, n_months=3)
    boom = _empty_run_error(
        ["2026-08-01→2026-09-01: No time zone found"],
        total_ticks=12,
        n_months=1,
    )
    assert "No time zone found" in boom
    assert "no Asia session days" in _empty_run_error([], total_ticks=99, n_months=1)
    assert _rows_to_trades([{"not": "a trade"}, "bad"]) == []

    slim = retain_result(
        {
            "kind": "overnight_break",
            "trades": 14,
            "skipped": 52,
            "ticks": 1000,
            "rows": [{"local_date": "2026-08-05", "pts": 1.0}] * 14,
            "skips": [{"local_date": "2026-08-06", "reason": "no_break"}] * 52,
        }
    )
    assert slim["trades"] == 14
    assert slim["skipped"] == 52
    assert len(slim["rows"]) == 14
    assert slim["rows_truncated"] is False


def test_require_zone_names_tzdata():
    from backtest.overnight_break import require_zone

    tz = require_zone("Europe/Bucharest")
    assert str(tz) == "Europe/Bucharest"
    try:
        require_zone("Not/AZone")
        raise AssertionError("expected missing zone to raise")
    except RuntimeError as e:
        assert "tzdata" in str(e).lower()


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


def _utc_down_break_ticks(*wait_ohlcs, asia_high=3320.0):
    start = datetime(2025, 5, 6, 0, 0, tzinfo=timezone.utc)
    wait1 = wait_ohlcs[0] if wait_ohlcs else (3296.0, 3298.0, 3294.0, 3296.0)
    overrides = {
        datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc): (
            3310.0,
            asia_high,
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


def test_wick_break_when_close_is_still_inside():
    """Min-break can use the wick: high/low vs Asia, even if the 15m closes back inside."""
    start = datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
    lookback_low = datetime(2026, 3, 31, 22, 30, tzinfo=timezone.utc)
    asia_high_bar = datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc)
    break_bar = datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc)
    ticks = _ohlc_ticks(
        start,
        44,
        overrides={
            lookback_low: (3310.0, 3312.0, 3290.0, 3308.0),
            asia_high_bar: (3310.0, 3320.0, 3308.0, 3315.0),
            # wick +400 pts above Asia high 3320; close 3316 still inside
            break_bar: (3315.0, 3324.0, 3314.0, 3316.0),
        },
    )
    close_only = run_overnight(
        ticks, symbol="XAU/USD", params=_apr1_params(require_close_outside=True)
    )
    assert close_only["trades"] == 0
    assert any(s.get("reason") == "no_break" for s in close_only["skips"])

    wick = run_overnight(
        ticks, symbol="XAU/USD", params=_apr1_params(break_on_wick=True)
    )
    assert wick["trades"] == 1
    row = wick["rows"][0]
    assert row["side"] == "UP"
    assert row["break_pts"] >= 200.0
    assert round(row["break_pts"], 0) == 400.0


def test_trail_arm_for_range_caps_asia_size():
    fixed = OvernightParams(trail_arm_mode="fixed", trail_arm_pts=400.0)
    assert trail_arm_for_range(fixed, 1500.0) == 400.0
    asia = OvernightParams(trail_arm_mode="asia", trail_arm_cap_pts=2000.0)
    assert trail_arm_for_range(asia, 1500.0) == 1500.0
    assert trail_arm_for_range(asia, 4000.0) == 2000.0
    uncapped = OvernightParams(trail_arm_mode="asia", trail_arm_cap_pts=0.0)
    assert trail_arm_for_range(uncapped, 4000.0) == 4000.0
    off = OvernightParams(trail_arm_mode="off", trail_pts=400.0)
    assert trail_setup(off, 2500.0, sl_pts=2000.0) == (0.0, 0.0, False)
    from_fill = OvernightParams(trail_arm_mode="from_fill", trail_pts=0.0)
    assert trail_arm_for_range(from_fill, 2500.0) == 0.0
    arm, dist, immediate = trail_setup(from_fill, 2500.0, sl_pts=2000.0)
    assert immediate is True and arm == 0.0 and dist == 2000.0
    custom = OvernightParams(trail_arm_mode="from_fill", trail_pts=1000.0)
    _arm, dist2, _im = trail_setup(custom, 2500.0, sl_pts=2000.0)
    assert dist2 == 1000.0


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


def test_from_fill_trail_tightens_one_for_one():
    tz = ZoneInfo("UTC")
    start = datetime(2025, 5, 6, 8, 0, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 3300.0),
        _tick(start + timedelta(seconds=1), 3301.0),
        _tick(start + timedelta(seconds=2), 3281.0),
    ]
    params = OvernightParams(
        trail_arm_mode="from_fill",
        trail_pts=0.0,
        flatten_hour=23,
        max_hold_hours=10.0,
    )
    reason, _ts, px, pts, armed, _fav, _adv, best, _worst = _simulate_from_entry(
        ticks,
        0,
        side="UP",
        entry=3300.0,
        sl=3280.0,
        tp=3400.0,
        params=params,
        ps=0.01,
        tz=tz,
        flatten_local=datetime(2025, 5, 6, 23, 0, tzinfo=tz),
        trail_arm_pts=0.0,
        trail_dist_pts=2000.0,
        trail_from_fill=True,
    )
    assert armed is True
    assert reason == "trail"
    assert best == 3301.0
    assert abs(px - 3281.0) < 1e-9
    assert round(pts, 0) == -1900.0


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


def test_late_short_blocked_helper():
    p = OvernightParams(skip_late_short_wait=7, skip_late_short_asia_pts=3000.0)
    assert late_short_blocked(p, "DOWN", 7, 1500.0)
    assert late_short_blocked(p, "DOWN", 8, 2999.0)
    assert not late_short_blocked(p, "DOWN", 6, 1500.0)
    assert not late_short_blocked(p, "UP", 8, 1500.0)
    assert not late_short_blocked(p, "DOWN", 7, 3000.0)
    off = OvernightParams(skip_late_short_wait=0, skip_late_short_asia_pts=3000.0)
    assert not late_short_blocked(off, "DOWN", 8, 500.0)
    any_asia = OvernightParams(skip_late_short_wait=7, skip_late_short_asia_pts=0.0)
    assert late_short_blocked(any_asia, "DOWN", 7, 9000.0)


def _wait7_ema_down_ticks(asia_high=3320.0):
    quiet = (3296.0, 3298.0, 3294.0, 3296.0)
    touch = (3296.0, 3320.0, 3294.0, 3308.0)
    return _utc_down_break_ticks(
        quiet, quiet, quiet, quiet, quiet, quiet, touch, asia_high=asia_high
    )


def test_late_short_skips_wait7_on_small_asia():
    ticks = _wait7_ema_down_ticks(asia_high=3320.0)
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        skip_late_short_wait=7,
        skip_late_short_asia_pts=3000.0,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "late_short"


def test_late_short_still_enters_on_large_asia():
    ticks = _wait7_ema_down_ticks(asia_high=3355.0)
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        skip_late_short_wait=7,
        skip_late_short_asia_pts=3000.0,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 1
    assert out["rows"][0]["side"] == "DOWN"
    assert out["rows"][0]["entry_reason"] == "ema_touch"
    assert out["rows"][0]["wait_i"] == 7
    assert out["rows"][0]["asia_range_pts"] >= 3000.0


def test_wait_from_break_not_clipped_by_max_break_window():
    """Late break: default wait dies with leftover post_asia; wait_from_break still counts 3 bars."""
    ticks = _utc_down_break_ticks(
        (3300.0, 3302.0, 3299.0, 3301.0),
        (3301.0, 3302.0, 3299.0, 3301.5),
        (3301.5, 3302.0, 3294.0, 3295.0),
    )
    clipped = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=True,
        ema_period=100,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        max_break_candles_after=2,
        wait_from_break=False,
    )
    from_break = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=True,
        ema_period=100,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        max_break_candles_after=2,
        wait_from_break=True,
    )
    off = run_overnight(ticks, symbol="XAU/USD", params=clipped)
    assert off["trades"] == 0
    skips = [s for s in off["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback"

    on = run_overnight(ticks, symbol="XAU/USD", params=from_break)
    assert on["trades"] == 1
    assert on["rows"][0]["side"] == "DOWN"
    assert on["rows"][0]["wait_i"] == 3
    assert on["rows"][0]["entry_reason"] == "lower_close"


def test_late_short_off_enters_wait7():
    ticks = _wait7_ema_down_ticks(asia_high=3320.0)
    params = OvernightParams(
        timezone="UTC",
        pullback_mode="required",
        use_higher_close=False,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        skip_late_short_wait=0,
        skip_late_short_asia_pts=3000.0,
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=params)
    assert out["trades"] == 1
    assert out["rows"][0]["wait_i"] == 7
    assert out["rows"][0]["entry_reason"] == "ema_touch"


def _timeout_params(**kwargs):
    base = dict(
        timezone="UTC",
        pullback_mode="preferred",
        timeout_action="market",
        use_higher_close=False,
        ema_period=21,
        min_asia_range_pts=300.0,
        min_break_pts_below=200.0,
        min_break_pts_above=200.0,
        max_wait_candles=8,
        max_break_candles_after=8,
        flatten_hour=23,
        max_hold_hours=14.0,
        skip_late_short_wait=0,
    )
    base.update(kwargs)
    return OvernightParams(**base)


def test_sl_asia_opposite_cap_pulls_in():
    p = OvernightParams(sl_mode="asia_opposite", sl_cap_pts=1800.0)
    sl, _tp, sl_pts, _tp_pts = _compute_sl_tp(
        "UP", 3325.0, 3320.0, 3300.0, p, 0.01
    )
    assert round(sl_pts, 1) == 1800.0
    assert abs(sl - (3325.0 - 18.0)) < 1e-9


def test_sl_asia_opposite_no_cap_uses_box():
    p = OvernightParams(sl_mode="asia_opposite", sl_cap_pts=0.0)
    sl, _tp, sl_pts, _tp_pts = _compute_sl_tp(
        "UP", 3325.0, 3320.0, 3300.0, p, 0.01
    )
    assert sl == 3300.0
    assert round(sl_pts, 1) == 2500.0


def test_sl_range_is_asia_width():
    p = OvernightParams(sl_mode="range", sl_range_mult=1.0, sl_cap_pts=0.0)
    sl, _tp, sl_pts, _tp_pts = _compute_sl_tp(
        "UP", 3325.0, 3320.0, 3300.0, p, 0.01
    )
    assert round(sl_pts, 1) == 2000.0
    assert abs(sl - 3305.0) < 1e-9


def test_sl_range_with_cap():
    p = OvernightParams(sl_mode="range", sl_range_mult=1.0, sl_cap_pts=1500.0)
    sl, _tp, sl_pts, _tp_pts = _compute_sl_tp(
        "DOWN", 3290.0, 3320.0, 3300.0, p, 0.01
    )
    assert round(sl_pts, 1) == 1500.0
    assert abs(sl - (3290.0 + 15.0)) < 1e-9


def test_sl_range_mult_alias_uncapped():
    p = OvernightParams(sl_mode="range_width", sl_range_mult=1.5, sl_cap_pts=0.0)
    _sl, _tp, sl_pts, _tp_pts = _compute_sl_tp(
        "UP", 3325.0, 3320.0, 3300.0, p, 0.01
    )
    assert round(sl_pts, 1) == 3000.0


def test_sl_fixed_ignores_cap():
    p = OvernightParams(sl_mode="fixed", sl_fixed_pts=500.0, sl_cap_pts=100.0)
    _sl, _tp, sl_pts, _tp_pts = _compute_sl_tp(
        "UP", 3325.0, 3320.0, 3300.0, p, 0.01
    )
    assert round(sl_pts, 1) == 500.0


def test_timeout_quality_blocked_helper():
    off = OvernightParams(timeout_max_ema_dist_pts=0.0, timeout_min_break_pts=0.0)
    assert not timeout_quality_blocked(off, closest_ema_pts=None, break_pts=200.0)
    assert not timeout_quality_blocked(off, closest_ema_pts=900.0, break_pts=200.0)
    dist = OvernightParams(timeout_max_ema_dist_pts=300.0, timeout_min_break_pts=0.0)
    assert timeout_quality_blocked(dist, closest_ema_pts=None, break_pts=500.0)
    assert timeout_quality_blocked(dist, closest_ema_pts=301.0, break_pts=500.0)
    assert not timeout_quality_blocked(dist, closest_ema_pts=300.0, break_pts=500.0)
    brk = OvernightParams(timeout_max_ema_dist_pts=0.0, timeout_min_break_pts=300.0)
    assert timeout_quality_blocked(brk, closest_ema_pts=None, break_pts=299.0)
    assert not timeout_quality_blocked(brk, closest_ema_pts=None, break_pts=300.0)
    pb = OvernightParams(timeout_min_pullback_pts=200.0)
    assert timeout_quality_blocked(pb, closest_ema_pts=0.0, break_pts=500.0, last_wait_pullback_pts=None)
    assert timeout_quality_blocked(pb, closest_ema_pts=0.0, break_pts=500.0, last_wait_pullback_pts=199.0)
    assert not timeout_quality_blocked(pb, closest_ema_pts=0.0, break_pts=500.0, last_wait_pullback_pts=200.0)


def test_timeout_market_ungated_still_fills():
    ticks = _utc_down_break_ticks()
    out = run_overnight(ticks, symbol="XAU/USD", params=_timeout_params())
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "timeout_market"
    assert row["side"] == "DOWN"
    assert row.get("closest_ema_pts") is not None
    assert row["closest_ema_pts"] > 0
    # Default leftover wait is 7 bars; last default wait close is 3296.
    assert abs(row["entry"] - 3296.0) < 1e-6
    assert row["wait_i"] == 7
    assert "08:59:50" in row["entry_ts"]


def test_timeout_market_fills_last_wait_close_not_break():
    ticks = _utc_down_break_ticks((3302.0, 3304.0, 3301.0, 3304.0))
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(max_wait_candles=1, use_higher_close=False),
    )
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "timeout_market"
    assert abs(row["entry"] - 3304.0) < 1e-6
    assert abs(row["break_candle_close"] - 3300.0) < 1e-6
    assert row["wait_i"] == 1
    assert "07:29:50" in row["entry_ts"]


def test_timeout_legacy_worst_is_market_at_last_wait():
    ticks = _utc_down_break_ticks((3302.0, 3304.0, 3301.0, 3304.0))
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(
            timeout_action="worst",
            max_wait_candles=1,
            use_higher_close=False,
        ),
    )
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "timeout_market"
    assert abs(row["entry"] - 3304.0) < 1e-6


def test_timeout_market_empty_wait_skips():
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(max_break_candles_after=1),
    )
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback_timeout"


def test_timeout_far_from_ema_skips():
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(timeout_max_ema_dist_pts=50.0),
    )
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback_timeout"
    assert skips[0].get("closest_ema_pts") is not None
    assert skips[0]["closest_ema_pts"] > 50.0


def test_timeout_wide_ema_cap_still_fills():
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(timeout_max_ema_dist_pts=20000.0),
    )
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "timeout_market"


def test_timeout_thin_break_skips():
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(timeout_min_break_pts=20000.0),
    )
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback_timeout"


def test_timeout_min_break_below_actual_still_fills():
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(timeout_min_break_pts=200.0),
    )
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "timeout_market"
    assert out["rows"][0]["break_pts"] >= 200.0


def test_timeout_no_wait_scan_fails_ema_dist_gate():
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(
            max_break_candles_after=1,
            timeout_max_ema_dist_pts=300.0,
        ),
    )
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback_timeout"
    assert skips[0].get("closest_ema_pts") is None


def test_timeout_min_pullback_skips_continuation():
    # Last wait close 3296 vs break close 3300 = continuation down, not a short pullback.
    ticks = _utc_down_break_ticks()
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(timeout_min_pullback_pts=50.0),
    )
    assert out["trades"] == 0
    skips = [s for s in out["skips"] if s.get("side") == "DOWN"]
    assert skips and skips[0]["reason"] == "no_pullback_timeout"
    assert skips[0].get("last_wait_pullback_pts") is not None
    assert skips[0]["last_wait_pullback_pts"] < 50.0


def test_timeout_min_pullback_fills_when_last_wait_retraces():
    # One wait bar: close 3304 vs break 3300 = +400 pts, high stays under EMA.
    ticks = _utc_down_break_ticks((3302.0, 3304.0, 3301.0, 3304.0))
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(timeout_min_pullback_pts=200.0, max_wait_candles=1),
    )
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["entry_reason"] == "timeout_market"
    assert row.get("last_wait_pullback_pts") is not None
    assert row["last_wait_pullback_pts"] >= 200.0
    assert abs(row["entry"] - 3304.0) < 1e-6


def test_timeout_min_pullback_does_not_block_ema_touch():
    ticks = _utc_down_break_ticks((3300.0, 3320.0, 3299.0, 3308.0))
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(
            pullback_mode="required",
            timeout_min_pullback_pts=20000.0,
        ),
    )
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "ema_touch"


def test_timeout_gate_does_not_block_ema_touch():
    ticks = _utc_down_break_ticks((3300.0, 3320.0, 3299.0, 3308.0))
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_timeout_params(
            pullback_mode="required",
            timeout_max_ema_dist_pts=1.0,
            timeout_min_break_pts=20000.0,
        ),
    )
    assert out["trades"] == 1
    assert out["rows"][0]["entry_reason"] == "ema_touch"


def _season_day_ticks(start_utc, high_bar, low_bar, first_post, break_side=None):
    overrides = {
        high_bar: (3310.0, 3320.0, 3308.0, 3315.0),
        low_bar: (3312.0, 3315.0, 3290.0, 3308.0),
    }
    if break_side == "UP":
        overrides[first_post] = (3315.0, 3324.0, 3314.0, 3323.0)
    elif break_side == "DOWN":
        overrides[first_post] = (3310.0, 3311.0, 3287.0, 3288.0)
    return _ohlc_ticks(start_utc, 48, overrides=overrides)


def _season_params(**kwargs):
    base = dict(
        timezone="Europe/Bucharest",
        pullback_mode="off",
        min_asia_range_pts=300.0,
        min_break_pts_above=200.0,
        min_break_pts_below=200.0,
        max_break_candles_after=8,
        seasonal_mode="filter",
        seasonal_join=False,
    )
    base.update(kwargs)
    return OvernightParams(**base)


def test_january_up_break_passes_filter():
    ticks = _season_day_ticks(
        datetime(2025, 1, 5, 22, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 2, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 3, 30, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 5, 0, tzinfo=timezone.utc),
        break_side="UP",
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=_season_params())
    rows = [r for r in out["rows"] if r["local_date"] == "2025-01-06"]
    assert rows and rows[0]["side"] == "UP"
    assert rows[0]["seasonal_regime"] == "strong"


def test_january_down_break_skipped_by_filter():
    ticks = _season_day_ticks(
        datetime(2025, 1, 5, 22, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 2, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 3, 30, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 5, 0, tzinfo=timezone.utc),
        break_side="DOWN",
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=_season_params())
    assert not [r for r in out["rows"] if r["local_date"] == "2025-01-06"]
    skips = [s for s in out["skips"] if s["local_date"] == "2025-01-06"]
    assert skips and skips[0]["reason"] == "seasonal_bias"
    assert skips[0]["side"] == "DOWN"


def test_january_no_break_join_goes_long():
    ticks = _season_day_ticks(
        datetime(2025, 1, 5, 22, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 2, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 3, 30, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 5, 0, tzinfo=timezone.utc),
        break_side=None,
    )
    joined = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_season_params(seasonal_join=True),
    )
    rows = [r for r in joined["rows"] if r["local_date"] == "2025-01-06"]
    assert rows and rows[0]["side"] == "UP"
    assert rows[0]["entry_reason"] == "seasonal_join"

    skipped = run_overnight(ticks, symbol="XAU/USD", params=_season_params())
    skips = [s for s in skipped["skips"] if s["local_date"] == "2025-01-06"]
    assert skips and skips[0]["reason"] == "no_break"


def test_april_down_break_neutral_still_trades():
    start = datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc)
    utc_midnight = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)
    lookback_low = datetime(2026, 3, 31, 22, 30, tzinfo=timezone.utc)
    trunc_low = datetime(2026, 4, 1, 2, 30, tzinfo=timezone.utc)
    asia_high_bar = datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc)
    break_bar = datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc)
    full = _ohlc_ticks(
        start,
        44,
        overrides={
            lookback_low: (3310.0, 3312.0, 3290.0, 3308.0),
            asia_high_bar: (3310.0, 3320.0, 3308.0, 3315.0),
            trunc_low: (3312.0, 3315.0, 3305.0, 3308.0),
            break_bar: (3310.0, 3311.0, 3299.0, 3300.0),
        },
    )
    truncated = full[next(i for i, t in enumerate(full) if t.ts >= utc_midnight) :]
    out = run_overnight(
        truncated,
        symbol="XAU/USD",
        params=_apr1_params(seasonal_mode="filter"),
    )
    assert out["trades"] == 1
    assert out["rows"][0]["side"] == "DOWN"
    assert out["rows"][0]["local_date"] == "2026-04-01"


def test_may_up_break_skipped_by_filter():
    ticks = _season_day_ticks(
        datetime(2025, 5, 5, 21, 0, tzinfo=timezone.utc),
        datetime(2025, 5, 6, 1, 0, tzinfo=timezone.utc),
        datetime(2025, 5, 6, 2, 30, tzinfo=timezone.utc),
        datetime(2025, 5, 6, 4, 0, tzinfo=timezone.utc),
        break_side="UP",
    )
    out = run_overnight(ticks, symbol="XAU/USD", params=_season_params())
    skips = [s for s in out["skips"] if s["local_date"] == "2025-05-06"]
    assert skips and skips[0]["reason"] == "seasonal_bias"
    assert skips[0]["side"] == "UP"


def _news_day_ticks(local_ymd, break_side="UP"):
    """Winter Bucharest (UTC+2): local midnight = 22:00 UTC previous evening."""
    y, m, d = (int(x) for x in local_ymd.split("-"))
    start = datetime(y, m, d, 0, 0, tzinfo=ZoneInfo("Europe/Bucharest")).astimezone(
        timezone.utc
    )
    high = start + timedelta(hours=4)
    low = start + timedelta(hours=5, minutes=30)
    post = start + timedelta(hours=7)
    return _season_day_ticks(start, high, low, post, break_side=break_side)


def test_news_filter_skips_nfp_day():
    ticks = _news_day_ticks("2023-02-03", break_side="UP")
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_season_params(seasonal_mode="off", news_mode="filter"),
    )
    assert not [r for r in out["rows"] if r["local_date"] == "2023-02-03"]
    skips = [s for s in out["skips"] if s["local_date"] == "2023-02-03"]
    assert skips and skips[0]["reason"] == "news_day"
    assert skips[0]["news_kind"] == "nfp"


def test_news_tag_still_trades():
    ticks = _news_day_ticks("2023-02-03", break_side="UP")
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_season_params(seasonal_mode="off", news_mode="tag"),
    )
    rows = [r for r in out["rows"] if r["local_date"] == "2023-02-03"]
    assert rows and rows[0]["side"] == "UP"
    assert rows[0]["news_kind"] == "nfp"
    assert "NFP" in (rows[0]["news_title"] or "")


def test_news_set_scheduled_ignores_shock_only_day():
    ticks = _news_day_ticks("2024-08-05", break_side="UP")  # yen unwind, not a print
    scheduled = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_season_params(
            seasonal_mode="off", news_mode="filter", news_set="scheduled"
        ),
    )
    assert [r for r in scheduled["rows"] if r["local_date"] == "2024-08-05"]
    all_set = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_season_params(seasonal_mode="off", news_mode="filter", news_set="all"),
    )
    skips = [s for s in all_set["skips"] if s["local_date"] == "2024-08-05"]
    assert skips and skips[0]["reason"] == "news_day"
    assert skips[0]["news_kind"] == "shock"


def test_seasonal_mode_off_ignores_table():
    ticks = _season_day_ticks(
        datetime(2025, 1, 5, 22, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 2, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 3, 30, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 5, 0, tzinfo=timezone.utc),
        break_side="DOWN",
    )
    out = run_overnight(
        ticks,
        symbol="XAU/USD",
        params=_season_params(seasonal_mode="off", seasonal_join=True),
    )
    rows = [r for r in out["rows"] if r["local_date"] == "2025-01-06"]
    assert rows and rows[0]["side"] == "DOWN"
    assert rows[0].get("seasonal_regime") in (None, "neutral")
    assert rows[0]["entry_reason"] != "seasonal_join"


def test_january_down_agrees_with_down_trend_still_filtered():
    ticks = _season_day_ticks(
        datetime(2025, 1, 5, 22, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 2, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 3, 30, tzinfo=timezone.utc),
        datetime(2025, 1, 6, 5, 0, tzinfo=timezone.utc),
        break_side="DOWN",
    )
    # Prefix 12 sessions of falling gold so 2-week is down (agrees with... wait
    # January season is UP, down trend CONFLICTS → should NOT filter).
    from zoneinfo import ZoneInfo
    from datetime import time as dtime

    tz = ZoneInfo("Europe/Bucharest")
    prefix = []
    for i in range(12, 0, -1):
        d = date(2025, 1, 6) - timedelta(days=i)
        loc = datetime.combine(d, dtime(16, 0), tzinfo=tz)
        px = 3400.0 - (12 - i) * 2.0
        prefix.append(_tick(loc.astimezone(timezone.utc), px))
    out = run_overnight(
        prefix + ticks,
        symbol="XAU/USD",
        params=_season_params(week2_trend=True, trend_flat_pts=1500.0),
    )
    rows = [r for r in out["rows"] if r["local_date"] == "2025-01-06"]
    assert rows and rows[0]["side"] == "DOWN"
    assert rows[0]["bias_conflict"] is True


def _falling_prefix(asof, n=12, start_px=3400.0, step=2.0):
    from datetime import time as dtime

    tz = ZoneInfo("Europe/Bucharest")
    prefix = []
    for i in range(n, 0, -1):
        d = asof - timedelta(days=i)
        loc = datetime.combine(d, dtime(16, 0), tzinfo=tz)
        px = start_px - (n - i) * step
        prefix.append(_tick(loc.astimezone(timezone.utc), px))
    return prefix


def test_week2_filter_skips_against_side_without_season():
    ticks = _season_day_ticks(
        datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 2, 30, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc),
        break_side="UP",
    )
    out = run_overnight(
        _falling_prefix(date(2026, 4, 1)) + ticks,
        symbol="XAU/USD",
        params=_season_params(
            seasonal_mode="off",
            week2_mode="filter",
            trend_flat_pts=1500.0,
            trend_efficiency_min=0.35,
        ),
    )
    skips = [s for s in out["skips"] if s.get("local_date") == "2026-04-01"]
    assert skips and skips[0]["reason"] == "seasonal_bias"
    assert skips[0]["side"] == "UP"
    assert skips[0].get("trend_side") == "DOWN"


def test_week2_tag_without_season_still_takes_against_side():
    ticks = _season_day_ticks(
        datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 2, 30, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 4, 0, tzinfo=timezone.utc),
        break_side="UP",
    )
    out = run_overnight(
        _falling_prefix(date(2026, 4, 1)) + ticks,
        symbol="XAU/USD",
        params=_season_params(
            seasonal_mode="off",
            week2_mode="tag",
            trend_flat_pts=1500.0,
            trend_efficiency_min=0.35,
        ),
    )
    rows = [r for r in out["rows"] if r["local_date"] == "2026-04-01"]
    assert rows and rows[0]["side"] == "UP"
    assert rows[0].get("trend_side") == "DOWN"


def test_week2_lookback_extends_when_enabled():
    from backtest.overnight_jobs import _chunk_lookback_start

    off = _chunk_lookback_start("2026-04-01", OvernightParams())
    on = _chunk_lookback_start(
        "2026-04-01", OvernightParams(week2_trend=True)
    )
    assert on < off
