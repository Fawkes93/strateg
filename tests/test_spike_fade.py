"""Spike fade: 3s/2000 detect, fade entry, TP/SL/trail/timeout, weekend skip."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backtest.dukascopy import Tick
from backtest.spike_fade import FadeParams, run_spike_fade, target_pts, weekend_reopen_blackout


def ticks_from(start: datetime, pairs):
    """pairs: (seconds_offset, mid)."""
    return [
        Tick(ts=start + timedelta(seconds=s), bid=px, ask=px) for s, px in pairs
    ]


def test_stop_when_idle():
    from backtest.spike_fade_jobs import stop_spike_fade

    out = stop_spike_fade()
    assert out["ok"] is False
    assert "running" in (out.get("error") or "").lower()


def test_month_chunks_year():
    from backtest.spike_fade_jobs import _month_chunks

    ch = _month_chunks("2025-05-01", "2026-05-01")
    assert len(ch) == 12
    assert ch[0] == ("2025-05-01", "2025-06-01")
    assert ch[-1] == ("2026-04-01", "2026-05-01")


def test_job_index_zero_is_valid():
    """Month 1 is index 0 — `0 or -1` would leave it stuck in the live log."""
    from backtest.spike_fade_jobs import _job_index

    assert _job_index({"index": 0}) == 0
    assert _job_index({"index": 0}, -1) == 0
    assert _job_index({}, -1) == -1
    assert _job_index({"index": None}, -1) == -1
    assert _job_index({"index": 3}) == 3


def test_worker_lanes_keep_slot_and_zero_index():
    from backtest.spike_fade_jobs import (
        _assign_slot,
        _lanes_snapshot,
        _release_slot,
    )

    slot_of = {}
    live = {
        0: {
            "event": "scan",
            "index": 0,
            "date_from": "2025-05-01",
            "ticks_done": 500_000,
            "ticks_total": 1_000_000,
            "trades": 2,
        },
        1: {
            "event": "load",
            "index": 1,
            "date_from": "2025-06-01",
            "message": "Unpack pack 200,000/2,000,000",
            "ticks_done": 200_000,
            "ticks_total": 0,
        },
    }
    _assign_slot(0, 4, slot_of)
    _assign_slot(1, 4, slot_of)
    lanes = _lanes_snapshot(4, live, slot_of)
    assert len(lanes) == 4
    assert lanes[0]["month"] == "2025-05-01"
    assert lanes[0]["phase"] == "scan"
    assert lanes[0]["pct"] > 40
    assert lanes[1]["phase"] == "load"
    assert "unpack" in lanes[1]["detail"]
    assert lanes[2]["phase"] == "idle"
    assert lanes[3]["phase"] == "idle"

    _release_slot(0, slot_of)
    live.pop(0)
    live[4] = {
        "event": "load",
        "index": 4,
        "date_from": "2025-09-01",
        "message": "starting…",
    }
    lanes = _lanes_snapshot(4, live, slot_of)
    assert lanes[0]["month"] == "2025-09-01"
    assert lanes[1]["month"] == "2025-06-01"


def test_weekend_blackout_sunday_2200():
    t0 = datetime(2026, 5, 3, 22, 0, 0, tzinfo=timezone.utc)  # Sunday
    assert weekend_reopen_blackout(t0, 10) is True
    assert weekend_reopen_blackout(t0 + timedelta(minutes=9, seconds=50), 10) is True
    assert weekend_reopen_blackout(t0 + timedelta(minutes=10), 10) is False
    mon = datetime(2026, 5, 4, 8, 0, tzinfo=timezone.utc)
    assert weekend_reopen_blackout(mon, 10) is False


def test_ignore_1000pt_move():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    # 10$ = 1000 pts in 1s — below 2000
    seq = [(0, 3300.0), (0.5, 3295.0), (1.0, 3290.0), (5.0, 3290.0)]
    res = run_spike_fade(ticks_from(t0, seq), symbol="XAU/USD")
    assert res["trades"] == 0


def test_dump_2000pts_fades_long_then_tp():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    # 20$ dump in 2s = 2000 pts → long at 3280, TP 3300
    seq = [(0, 3300.0), (1.0, 3290.0), (2.0, 3280.0)]
    # retrace to TP
    for i in range(1, 25):
        seq.append((2.0 + i * 0.2, 3280.0 + i))
    res = run_spike_fade(ticks_from(t0, seq), symbol="XAU/USD")
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "UP"
    assert t["spike_dir"] == "DOWN"
    assert t["spike_pts"] >= 2000
    assert t["exit_reason"] == "tp"
    assert t["pts"] == 2000


def test_hard_sl():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (2.0, 3280.0)]  # dump 2000, long 3280, SL 3260
    seq.append((3.0, 3259.0))
    res = run_spike_fade(ticks_from(t0, seq), symbol="XAU/USD")
    assert res["trades"] == 1
    assert res["rows"][0]["exit_reason"] == "sl"
    assert res["rows"][0]["pts"] == -2000


def test_trail_after_plus_1000():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (2.0, 3280.0)]  # long 3280
    seq.append((4.0, 3290.0))  # +1000 → trail at BE 3280
    seq.append((5.0, 3295.0))  # +1500 → trail at 3285
    seq.append((6.0, 3284.0))  # through trail
    res = run_spike_fade(ticks_from(t0, seq), symbol="XAU/USD")
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "trail"
    assert t["pts"] > 0


def test_timeout_2min():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (2.0, 3280.0)]
    seq.append((2.0 + 121, 3281.0))  # still near entry after 2 min
    res = run_spike_fade(
        ticks_from(t0, seq),
        symbol="XAU/USD",
        params=FadeParams(max_hold_sec=120, cooldown_sec=0),
    )
    assert res["trades"] == 1
    assert res["rows"][0]["exit_reason"] == "timeout"


def test_lag_fills_later_price():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    # Detect dump at t=2 (3280). Lag 2s → fill at t=4 (3275), not 3280.
    seq = [(0, 3300.0), (2.0, 3280.0), (4.0, 3275.0), (6.0, 3275.0 + 20.0)]
    res = run_spike_fade(
        ticks_from(t0, seq),
        symbol="XAU/USD",
        params=FadeParams(lag_sec=2.0, cooldown_sec=0, max_hold_sec=120),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert abs(t["entry"] - 3275.0) < 1e-6
    assert abs((t.get("detect_px") or 0) - 3280.0) < 1e-6
    assert t["lag_sec"] == 2.0
    assert t["exit_reason"] == "tp"


def test_target_pts_percent_and_fixed():
    assert target_pts(100, 2500, 2000) == 2500
    assert target_pts(50, 2000, 2000) == 1000
    assert target_pts(0, 3000, 2000) == 2000
    assert target_pts(200, 2000, 2000) == 4000


def test_tp_sl_percent_of_this_spike():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    # 3000 pt dump → long 3270. TP 50% = 1500 → 3285. SL 100% = 3000 → 3240.
    seq = [(0, 3300.0), (2.0, 3270.0), (3.0, 3285.0)]
    res = run_spike_fade(
        ticks_from(t0, seq),
        symbol="XAU/USD",
        params=FadeParams(
            min_spike_pts=2000,
            tp_pct=50,
            sl_pct=100,
            cooldown_sec=0,
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "tp"
    assert abs(t["pts"] - 1500) < 1.0
    assert abs(t["tp_pts"] - 1500) < 1.0
    assert abs(t["sl_pts"] - 3000) < 1.0


def test_sl_percent_tighter_than_fixed():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    # 2000 dump → long 3280. SL 50% = 1000 → 3270. Price 3269 hits %.
    seq = [(0, 3300.0), (2.0, 3280.0), (3.0, 3269.0)]
    res = run_spike_fade(
        ticks_from(t0, seq),
        symbol="XAU/USD",
        params=FadeParams(tp_pct=100, sl_pct=50, cooldown_sec=0),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "sl"
    assert abs(t["pts"] + 1000) < 1.0


def test_zero_pct_keeps_fixed_pts():
    t0 = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    # 3000 dump → long 3270. % = 0 so TP stays 2000 pts → 3290.
    seq = [(0, 3300.0), (2.0, 3270.0), (3.0, 3290.0)]
    res = run_spike_fade(
        ticks_from(t0, seq),
        symbol="XAU/USD",
        params=FadeParams(
            tp_pct=0,
            sl_pct=0,
            tp_pts=2000,
            sl_pts=2000,
            cooldown_sec=0,
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "tp"
    assert abs(t["pts"] - 2000) < 1.0
    assert abs(t["tp_pts"] - 2000) < 1.0


def test_skip_sunday_reopen():
    t0 = datetime(2026, 5, 3, 22, 0, 1, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (2.0, 3280.0), (5.0, 3300.0)]
    res = run_spike_fade(ticks_from(t0, seq), symbol="XAU/USD")
    assert res["trades"] == 0
