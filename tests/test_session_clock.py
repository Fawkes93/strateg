"""Session clock: defining bar fallback, 5am SL floor, 09:00 vs BE vs noon."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backtest.dukascopy import Tick
from backtest.h1 import build_h1, utc_hours_for_local_window
from backtest.session_clock import SessionParams, pick_defining_bar, run_session, sl_price
from backtest.h1 import index_h1

TZ = ZoneInfo("Europe/Chisinau")
# 2026-05-06 Wednesday, EEST = UTC+3
DAY = datetime(2026, 5, 6, tzinfo=TZ)


def utc_at(local_hour: int, minute: int = 0, second: int = 0) -> datetime:
    loc = DAY.replace(hour=local_hour, minute=minute, second=second, microsecond=0)
    return loc.astimezone(timezone.utc)


def tick(ts: datetime, mid: float) -> Tick:
    return Tick(ts=ts, bid=mid, ask=mid)


def hour_bar_ticks(hour: int, o: float, h: float, l: float, c: float) -> list:
    """A few ticks that form an H1 OHLC in local `hour`."""
    return [
        tick(utc_at(hour, 0, 1), o),
        tick(utc_at(hour, 10, 0), h),
        tick(utc_at(hour, 20, 0), l),
        tick(utc_at(hour, 59, 0), c),
    ]


def test_session_hours_are_morning_only():
    hours = utc_hours_for_local_window(
        "2026-05-04", "2026-05-09", "Europe/Chisinau", hour_from=3, hour_to=12
    )
    # Mon 4 May – Fri 8 May (9 is exclusive Sat) → 5 weekdays × 10 hours
    assert len(hours) == 5 * 10
    tz = ZoneInfo("Europe/Chisinau")
    for h in hours:
        loc = h.astimezone(tz)
        assert 3 <= loc.hour <= 12


def test_h1_local_hour():
    ticks = hour_bar_ticks(6, 3300, 3316, 3299, 3314)
    bars = build_h1(ticks, "Europe/Chisinau")
    assert len(bars) == 1
    assert bars[0].local_hour == 6
    assert bars[0].local_date.isoformat() == "2026-05-06"
    assert abs(bars[0].high - 3316) < 1e-9
    assert abs(bars[0].low - 3299) < 1e-9


def test_defining_fallback_skips_small_6am():
    ticks = []
    ticks += hour_bar_ticks(4, 3280, 3296, 3279, 3295)  # $16 up
    ticks += hour_bar_ticks(5, 3295, 3300, 3294, 3298)  # $6 — too small
    ticks += hour_bar_ticks(6, 3298, 3302, 3297, 3301)  # $5 — too small
    bars = index_h1(build_h1(ticks, "Europe/Chisinau"))
    p = SessionParams()
    d = pick_defining_bar(bars, DAY.date(), p, 0.01)
    assert d is not None
    assert d.local_hour == 4


def test_sl_floor_500pts():
    from backtest.h1 import H1Bar

    bar5 = H1Bar(
        open_time=utc_at(5),
        close_time=utc_at(6),
        local_date=DAY.date(),
        local_hour=5,
        open=3300,
        high=3301,
        low=3299.5,  # only $0.50 / 50 pts below a 3300 entry
        close=3300.2,
    )
    sl = sl_price("UP", 3300.0, bar5, sl_floor_pts=500, ps=0.01)
    assert abs(sl - 3295.0) < 1e-9  # entry - 500 pts


def _path(hours_px):
    """hours_px: list of (local_hour, minute, mid) plus required 4-6am bars."""
    ticks = []
    ticks += hour_bar_ticks(4, 3280, 3282, 3279, 3281)
    ticks += hour_bar_ticks(5, 3281, 3283, 3270, 3280)  # low 3270 for SL
    ticks += hour_bar_ticks(6, 3280, 3300, 3279, 3298)  # $21 up, defining
    for h, m, px in hours_px:
        ticks.append(tick(utc_at(h, m), px))
    ticks.sort(key=lambda t: t.ts)
    return run_session(ticks, symbol="XAU/USD", params=SessionParams())


def test_eval_flat_when_green_at_9am():
    # Entry ~3298 at 7:00, 9:00 still above
    res = _path(
        [
            (7, 0, 3298.0),
            (8, 0, 3302.0),
            (9, 0, 3305.0),
            (10, 0, 3310.0),
        ]
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "UP"
    assert t["defining_hour"] == 6
    assert t["exit_reason"] == "eval_flat"
    assert t["pts"] > 0


def test_be_after_red_9am():
    res = _path(
        [
            (7, 0, 3298.0),
            (8, 0, 3290.0),
            (9, 0, 3288.0),  # red at 9am
            (10, 0, 3298.0),  # back to entry
        ]
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "be"
    assert abs(t["pts"]) < 1e-6


def test_sl_before_9am():
    res = _path(
        [
            (7, 0, 3298.0),
            (7, 30, 3269.0),  # through 5am low 3270
            (9, 0, 3260.0),
        ]
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "sl"
    assert t["pts"] < 0


def test_noon_if_never_back_to_be():
    res = _path(
        [
            (7, 0, 3298.0),
            (9, 0, 3288.0),
            (11, 0, 3285.0),
            (12, 0, 3284.0),
        ]
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "noon_flat"
    assert t["pts"] < 0
