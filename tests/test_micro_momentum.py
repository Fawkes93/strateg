"""Micro-burst scalp: with-momentum, spread fills, session, persist, size cap."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backtest.dukascopy import Tick
from backtest.micro_momentum import (
    BurstParams,
    in_session,
    run_micro_momentum,
)


def ticks_mid(start: datetime, pairs, spread=0.0):
    """pairs: (seconds_offset, mid). Optional symmetric spread in price."""
    half = float(spread) / 2.0
    return [
        Tick(ts=start + timedelta(seconds=s), bid=px - half, ask=px + half)
        for s, px in pairs
    ]


def test_in_session_windows():
    asia = datetime(2026, 3, 4, 3, 0, tzinfo=timezone.utc)
    london = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    ny = datetime(2026, 3, 4, 18, 0, tzinfo=timezone.utc)
    assert in_session(asia, "all")
    assert in_session(asia, "asia")
    assert in_session(asia, "asia_london")
    assert not in_session(asia, "london_ny")
    assert in_session(london, "asia_london")
    assert in_session(london, "london_ny")
    assert not in_session(london, "asia")
    assert in_session(ny, "all")
    assert in_session(ny, "london_ny")
    assert not in_session(ny, "asia")
    assert not in_session(ny, "asia_london")


def test_one_way_burst_goes_long_and_tps():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)  # London
    # +120 pts in 3s, almost no pullback, then to TP 100
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    for i in range(1, 30):
        seq.append((3.0 + i * 0.2, 3301.20 + i * 0.08))
    res = run_micro_momentum(
        ticks_mid(t0, seq, spread=0.0),
        symbol="XAU/USD",
        params=BurstParams(
            window_sec=4,
            min_burst_pts=100,
            max_burst_pts=400,
            persist_frac=0.35,
            use_1m=False,
            tp_pts=100,
            sl_pts=80,
            lag_sec=0,
            session="all",
            max_spread_pts=80,
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "UP"
    assert t["burst_pts"] >= 100
    assert t["exit_reason"] == "tp"
    assert t["pts"] == 100


def test_persist_fail_no_trade():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    # net +120 but dipped 80 pts first (adverse/burst = 80/120 > 0.35)
    seq = [(0, 3300.0), (1.0, 3299.20), (2.5, 3300.40), (4.0, 3301.20)]
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(use_1m=False, lag_sec=0, persist_frac=0.35),
    )
    assert res["trades"] == 0


def test_max_burst_skips_fade_territory():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (2.0, 3325.00)]  # +2500 pts
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(use_1m=False, lag_sec=0, max_burst_pts=400),
    )
    assert res["trades"] == 0


def test_spread_fill_long_entry_is_ask():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    spread = 0.30  # 30 pts
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    for i in range(1, 40):
        seq.append((3.0 + i * 0.2, 3301.20 + i * 0.08))
    res = run_micro_momentum(
        ticks_mid(t0, seq, spread=spread),
        symbol="XAU/USD",
        params=BurstParams(
            use_1m=False,
            lag_sec=0,
            tp_pts=100,
            sl_pts=80,
            max_spread_pts=80,
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "UP"
    # ask = mid + 0.15 at fill (~3301.20)
    assert t["entry"] > 3301.20
    assert abs(t["spread_pts"] - 30.0) < 0.6
    if t["exit_reason"] == "tp":
        assert t["pts"] == 100


def test_tp_cannot_win_if_target_inside_spread():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    spread = 0.40  # 40 pts
    seq = [(0, 3300.0), (1.0, 3300.70), (2.0, 3301.10), (3.0, 3301.20)]
    # only grind +20 pts of mid after entry — not enough to cover TP 100 after spread
    for i in range(1, 15):
        seq.append((3.0 + i * 0.3, 3301.20 + 0.20))
    res = run_micro_momentum(
        ticks_mid(t0, seq, spread=spread),
        symbol="XAU/USD",
        params=BurstParams(
            use_1m=False,
            lag_sec=0,
            tp_pts=100,
            sl_pts=80,
            max_hold_sec=8,
            max_spread_pts=80,
        ),
    )
    assert res["trades"] >= 1
    t = res["rows"][0]
    assert t["exit_reason"] != "tp"


def test_session_asia_skips_london_hour():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)  # 10:00 UTC London
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    for i in range(1, 20):
        seq.append((3.0 + i * 0.2, 3301.20 + i * 0.05))
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(use_1m=False, lag_sec=0, session="asia"),
    )
    assert res["trades"] == 0


def test_weekend_blackout():
    t0 = datetime(2026, 5, 3, 22, 1, 0, tzinfo=timezone.utc)  # Sunday 22:01
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(use_1m=False, lag_sec=0, session="all"),
    )
    assert res["trades"] == 0


def test_trail_after_arm():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    seq.append((5.0, 3301.70))  # +50 from entry ~3301.20 → arm
    seq.append((6.0, 3302.00))  # +80 → trail at +40
    seq.append((7.0, 3301.55))  # through trail
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(
            use_1m=False,
            lag_sec=0,
            tp_pts=300,
            sl_pts=200,
            trail_pts=40,
            trail_arm_pts=50,
            max_hold_sec=30,
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["exit_reason"] == "trail"
    assert t["pts"] > 0
    assert res["trail_n"] == 1


def test_trail_off_does_not_trail():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    seq.append((5.0, 3301.70))
    seq.append((6.0, 3301.50))
    seq.append((8.0, 3301.25))  # still open → timeout
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(
            use_1m=False,
            lag_sec=0,
            tp_pts=300,
            sl_pts=200,
            trail_pts=0,
            trail_arm_pts=0,
            max_hold_sec=5,
        ),
    )
    assert res["trades"] == 1
    assert res["rows"][0]["exit_reason"] == "timeout"


def test_spread_wider_than_sl_is_not_a_trade():
    """Gold spread ~30 pts vs a 20-pt SL must not open (was instant SL, 5% WR)."""
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (0.8, 3300.40), (1.6, 3300.80)]
    seq.append((2.0, 3300.90))
    seq.append((2.5, 3300.50))
    res = run_micro_momentum(
        ticks_mid(t0, seq, spread=0.30),
        symbol="XAU/USD",
        params=BurstParams(
            window_sec=2,
            min_burst_pts=50,
            max_burst_pts=100,
            use_1m=False,
            lag_sec=0,
            tp_pts=20,
            sl_pts=20,
            max_spread_pts=80,
            session="all",
        ),
    )
    assert res["trades"] == 0


def test_spread_does_not_instant_stop():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (0.8, 3300.40), (1.6, 3300.80)]
    # hold mid flat for a bit — must not SL from the spread alone
    for i in range(1, 8):
        seq.append((1.6 + i * 0.2, 3300.80))
    seq.append((4.0, 3301.20))  # +40 mid → TP 20 on bid from entry bid
    res = run_micro_momentum(
        ticks_mid(t0, seq, spread=0.10),  # 10 pts < SL 20
        symbol="XAU/USD",
        params=BurstParams(
            window_sec=2,
            min_burst_pts=50,
            max_burst_pts=100,
            use_1m=False,
            lag_sec=0,
            tp_pts=20,
            sl_pts=20,
            max_hold_sec=15,
            max_spread_pts=80,
            session="all",
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["hold_sec"] is None or t["hold_sec"] >= 0.3
    assert t["exit_reason"] != "sl" or t["hold_sec"] >= 0.3


def test_be_asap_closes_at_entry():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (0.8, 3300.40), (1.6, 3300.80)]  # +80 in 1.6s
    seq.append((2.2, 3300.90))  # in favor
    seq.append((2.8, 3300.80))  # back to fill → BE
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(
            window_sec=2,
            min_burst_pts=50,
            max_burst_pts=100,
            use_1m=False,
            lag_sec=0,
            tp_pts=20,
            sl_pts=30,
            be_asap=True,
            be_asap_pts=1,
            max_hold_sec=15,
            session="all",
        ),
    )
    assert res["trades"] == 1
    t = res["rows"][0]
    assert t["side"] == "UP"
    assert t["exit_reason"] == "be"
    assert t["pts"] >= 0


def test_hard_sl():
    t0 = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
    seq = [(0, 3300.0), (1.0, 3300.60), (2.0, 3300.90), (3.0, 3301.20)]
    seq.append((4.0, 3299.00))  # through SL
    res = run_micro_momentum(
        ticks_mid(t0, seq),
        symbol="XAU/USD",
        params=BurstParams(use_1m=False, lag_sec=0, tp_pts=100, sl_pts=80),
    )
    assert res["trades"] == 1
    assert res["rows"][0]["exit_reason"] == "sl"
    assert res["rows"][0]["pts"] == -80
