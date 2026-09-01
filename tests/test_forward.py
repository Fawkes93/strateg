"""Forward walk: realized pts flatten dirty hits at the opposite stop."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backtest.dukascopy import Tick
from backtest.forward import summarize_forward, walk_forward_multi
from backtest.trades import AlertSignal

T0 = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def ticks(prices):
    return [
        Tick(ts=T0 + timedelta(seconds=i), bid=px, ask=px)
        for i, px in enumerate(prices)
    ]


def alert(price=2000.0, side="UP"):
    return AlertSignal(
        kind="impulse_retrace",
        symbol="XAU/USD",
        side=side,
        ts=T0,
        price=price,
    )


def path_at(prices, T=500.0, adverse_mult=1.5, sl_manage="off"):
    out = walk_forward_multi(
        alert(),
        ticks(prices),
        0,
        thresholds=[T],
        window_sec=60.0,
        adverse_mult=adverse_mult,
        sl_manage=sl_manage,
    )
    return out["500"]


def test_clean_hit_is_plus_T():
    # +510 pts, never against. T=500, SL=750.
    p = path_at([2000.0, 2002.0, 2005.1])
    assert p.hit is True
    assert p.clean is True
    assert p.realized_pts == 500.0
    assert p.exit == "target"


def test_dirty_hit_is_minus_SL_not_plus_T():
    # Tag −760 (past 1.5×T=750) then still reach +510. Path-analysis hit, not clean.
    p = path_at([2000.0, 1992.4, 2005.1])
    assert p.hit is True
    assert p.clean is False
    assert p.first_touch == "adv"
    assert p.realized_pts == -750.0
    assert p.exit == "init_sl"


def test_sl_miss_is_minus_SL():
    p = path_at([2000.0, 1992.4, 1992.0])
    assert p.hit is False
    assert p.clean is False
    assert p.realized_pts == -750.0
    assert p.exit == "init_sl"


def test_timeout_without_sl_is_mark_to_market():
    p = path_at([2000.0, 2001.0, 2001.0])
    assert p.hit is False
    assert p.clean is False
    assert p.exit == "timeout"
    # +100 pts still open at window end
    assert p.realized_pts == 100.0


def test_summary_sum_does_not_credit_dirty_hits():
    clean = path_at([2000.0, 2005.1])
    dirty = path_at([2000.0, 1992.4, 2005.1])
    miss = path_at([2000.0, 1992.4])
    s = summarize_forward([clean, dirty, miss])
    assert s["n"] == 3
    assert s["hits"] == 2
    assert s["cleans"] == 1
    assert s["realized_mode"] == "hard_sl"
    # +500 + −750 + −750
    assert s["sum_realized_pts"] == -1000.0
    assert s["avg_realized_pts"] == round(-1000.0 / 3, 1)


def test_managed_stop_still_flattens_at_init_sl():
    p = path_at([2000.0, 1992.4, 2005.1], sl_manage="be")
    assert p.hit is False
    assert p.clean is False
    assert p.exit == "init_sl"
    assert p.realized_pts == -750.0
