"""Micro fade: stall after a quiet-hour burst, then fade 1:1 with trail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backtest.dukascopy import Tick
from backtest.micro_momentum import BurstParams, in_session, run_micro_momentum


def ticks_mid(start: datetime, pairs, spread=0.0):
    half = float(spread) / 2.0
    return [
        Tick(ts=start + timedelta(seconds=s), bid=px - half, ask=px + half)
        for s, px in pairs
    ]


FADE = BurstParams(
    mode="fade",
    window_sec=4,
    min_burst_pts=100,
    max_burst_pts=300,
    persist_frac=0.35,
    use_1m=False,
    tp_frac=0.35,
    rr_one_to_one=True,
    trail_frac=0.5,
    pause_sec=1.0,
    pause_give_up_sec=8.0,
    lag_sec=0,
    session="all",
    max_spread_pts=80,
    max_hold_sec=20,
    cooldown_sec=20,
    trail_pts=0,
)


def test_quiet_includes_asia_and_late_chisinau():
    asia = datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc)
    # 20:30 Chisinau in August = 17:30 UTC (EEST, UTC+3)
    late_summer = datetime(2026, 8, 15, 17, 30, tzinfo=timezone.utc)
    # 20:30 Chisinau in January = 18:30 UTC (EET, UTC+2)
    late_winter = datetime(2026, 1, 15, 18, 30, tzinfo=timezone.utc)
    ny = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)
    assert in_session(asia, "quiet")
    assert in_session(late_summer, "quiet")
    assert in_session(late_summer, "late_chisinau")
    assert in_session(late_winter, "quiet")
    assert not in_session(ny, "quiet")
    assert not in_session(ny, "asia")
    assert not in_session(ny, "late_chisinau")


def test_stall_then_fade_hits_tp():
    t0 = datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]  # +120
    seq.append((3.5, 3301.20))
    seq.append((4.2, 3301.20))  # 1.2s stall
    seq.append((5.0, 3300.90))
    seq.append((6.0, 3300.70))  # TP 0.35*120 = 42 pts from 3301.20
    res = run_micro_momentum(ticks_mid(t0, seq), symbol="XAU/USD", params=FADE)
    assert res["kind"] == "micro_fade"
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "DOWN"
    assert t["exit_reason"] == "tp"
    assert abs(t["tp_pts"] - t["sl_pts"]) < 0.2
    assert t["pts"] > 0


def test_no_stall_skips_trade():
    t0 = datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    for i in range(1, 20):
        seq.append((3.0 + i * 0.2, 3301.20 + i * 0.01))  # new highs every 0.2s
    res = run_micro_momentum(ticks_mid(t0, seq), symbol="XAU/USD", params=FADE)
    assert res["trades"] == 0


def test_stall_then_continuation_hits_sl():
    t0 = datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    seq.append((4.2, 3301.20))
    seq.append((5.0, 3301.80))  # through 1:1 SL (42 pts)
    res = run_micro_momentum(ticks_mid(t0, seq), symbol="XAU/USD", params=FADE)
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "DOWN"
    assert t["exit_reason"] == "sl"
    assert t["pts"] < 0


def test_quiet_skips_ny_afternoon():
    t0 = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    seq.append((4.2, 3301.20))
    seq.append((6.0, 3300.70))
    p = BurstParams(**{**FADE.__dict__, "session": "quiet"})
    res = run_micro_momentum(ticks_mid(t0, seq), symbol="XAU/USD", params=p)
    assert res["trades"] == 0


def test_trail_to_be_after_half_r():
    t0 = datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc)
    # TP = 42, trail arm = 21, trail = 21 → BE after +½R
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    seq.append((4.2, 3301.20))  # stall → short ~3301.20
    seq.append((5.0, 3300.95))  # +25 pts fav, arms trail
    seq.append((6.0, 3301.21))  # back through BE trail
    res = run_micro_momentum(ticks_mid(t0, seq), symbol="XAU/USD", params=FADE)
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "trail"
    assert t["pts"] >= -1.0
