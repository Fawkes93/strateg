"""Stop scalper: OCO stops near the open, safety SL, BE, trail, one reversal."""

from datetime import datetime, timedelta, timezone

import pytest

from backtest.candles import Candle
from backtest.stop_scalper import (
    StopScalperParams,
    run_stop_scalper,
    validate_params,
)


UTC = timezone.utc
T0 = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)


def _bar(i, o, h, l, c):
    start = T0 + timedelta(minutes=i)
    return Candle(
        open_time=start,
        close_time=start + timedelta(minutes=1),
        open=o,
        high=h,
        low=l,
        close=c,
        is_closed=True,
        tick_count=4,
    )


def _run(bars, **kwargs):
    params = StopScalperParams(timezone="UTC", **kwargs)
    return run_stop_scalper(bars, symbol="XAUUSD", params=params)


def test_buy_stop_trails_and_the_reversal_trails():
    bars = [
        _bar(0, 2000, 2005, 1999.8, 2004),
        _bar(1, 2004, 2004.2, 2000, 2001.2),
    ]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=150, trail_pts=100, trail_arm_pts=200)
    assert out["trades"] == 2, out["rows"]
    first, second = out["rows"]
    assert first["origin"] == "stop" and first["side"] == "UP"
    assert first["entry"] == 2001
    assert first["exit_reason"] == "trail"
    assert first["exit"] == 2004
    assert first["pts"] == 300
    assert second["origin"] == "reverse" and second["side"] == "DOWN"
    assert second["entry"] == 2004
    assert second["exit_reason"] == "trail"
    assert second["exit"] == 2001
    assert second["pts"] == 300
    assert out["kind"] == "stop_scalper"
    assert out["data_source"] == "candles_1m"
    assert out["streaks"]["max_win"] == 2
    assert out["by_month"][0]["month"] == "2026-10"
    assert out["by_origin"][0]["origin"] == "stop"
    assert out["by_origin"][1]["trades"] == 1


def test_bullish_bar_hits_the_sell_stop_first_and_drops_the_buy():
    bars = [_bar(0, 2000, 2003, 1998, 2002)]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=0, trail_pts=0, reverse=False)
    assert out["trades"] == 1
    row = out["rows"][0]
    assert row["side"] == "DOWN"
    assert row["origin"] == "stop"
    assert row["entry"] == 1999
    assert row["exit_reason"] == "data_end"
    assert row["pts"] == -300


def test_safety_sl_is_500_points_then_one_reversal():
    bars = [
        _bar(0, 2000, 2001.2, 1999.9, 2001.05),
        _bar(1, 2001.05, 2001.1, 1990, 1992),
    ]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=0, trail_pts=0)
    assert out["trades"] == 2, out["rows"]
    stopped, reverse = out["rows"]
    assert stopped["side"] == "UP" and stopped["origin"] == "stop"
    assert stopped["exit_reason"] == "sl"
    assert stopped["exit"] == 1996
    assert stopped["pts"] == -500
    assert stopped["max_fav_pts"] == 20
    assert stopped["sl_init"] == 1996
    assert reverse["origin"] == "reverse" and reverse["side"] == "DOWN"
    assert reverse["entry"] == 1996
    assert reverse["exit_reason"] == "data_end"
    assert reverse["pts"] == 400


def test_break_even_scratch_does_not_chain_a_second_reversal():
    bars = [_bar(0, 2000, 2002.5, 1999.9, 2001)]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=100, trail_pts=0)
    assert out["trades"] == 2, out["rows"]
    scratch, reverse = out["rows"]
    assert scratch["exit_reason"] == "be"
    assert scratch["pts"] == 0
    assert scratch["exit"] == 2001
    assert reverse["origin"] == "reverse"
    assert reverse["entry"] == 2001
    assert reverse["exit_reason"] == "data_end"


def test_range_inside_the_stops_does_not_trade():
    bars = [_bar(0, 2000, 2000.4, 1999.6, 2000.1)]
    out = _run(bars, entry_pts=100, sl_pts=500)
    assert out["trades"] == 0


def test_same_bar_stop_fills_and_safety_sl_reverses():
    bars = [_bar(0, 2000, 2001.5, 1990, 1992)]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=0, trail_pts=0)
    assert [r["origin"] for r in out["rows"]] == ["stop", "reverse"]
    assert out["rows"][0]["exit_reason"] == "sl"
    assert out["rows"][0]["pts"] == -500
    assert out["rows"][1]["side"] == "DOWN"
    assert out["rows"][1]["pts"] == 400


def test_next_bar_rearms_after_the_reversal_closes():
    bars = [
        _bar(0, 2000, 2002.5, 1999.9, 2001),
        _bar(1, 2001, 2006.5, 2000.9, 2006),
        _bar(2, 2006, 2007.2, 2005.5, 2007),
    ]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=100, trail_pts=0)
    assert [r["origin"] for r in out["rows"]] == ["stop", "reverse", "stop"]
    assert [r["side"] for r in out["rows"]] == ["UP", "DOWN", "UP"]
    assert [r["exit_reason"] for r in out["rows"]] == ["be", "sl", "data_end"]
    assert out["rows"][1]["pts"] == -500
    assert out["rows"][2]["entry"] == 2007


def test_trail_arm_of_zero_uses_the_trail_distance():
    # Profit must reach the 100-pt trail before the stop leaves the safety net.
    bars = [
        _bar(0, 2000, 2001.5, 1999.9, 2001.4),
        _bar(1, 2001.4, 2001.5, 1996, 1996.5),
    ]
    out = _run(bars, entry_pts=100, sl_pts=500, be_pts=0, trail_pts=100, trail_arm_pts=0)
    row = out["rows"][0]
    assert row["exit_reason"] == "sl"
    assert row["pts"] == -500


def test_profit_lock_exits_at_the_locked_stop_without_a_reversal():
    bars = [_bar(0, 2000, 2005, 1999.9, 2001.5)]
    out = _run(
        bars,
        entry_pts=100,
        sl_pts=500,
        be_pts=0,
        trail_pts=0,
        lock_arm_pts=300,
        lock_pts=100,
        reverse_on="sl",
    )
    assert len(out["rows"]) == 1
    row = out["rows"][0]
    assert row["exit_reason"] == "lock"
    assert row["exit"] == 2002
    assert row["pts"] == 100


def test_fixed_target_exits_at_the_target():
    bars = [_bar(0, 2000, 2005, 1999.9, 2004)]
    out = _run(
        bars,
        entry_pts=100,
        sl_pts=500,
        be_pts=0,
        trail_pts=0,
        tp_pts=200,
        reverse_on="sl",
    )
    assert len(out["rows"]) == 1
    assert out["rows"][0]["exit_reason"] == "tp"
    assert out["rows"][0]["exit"] == 2003
    assert out["rows"][0]["pts"] == 200


def test_reversal_only_after_the_safety_stop():
    stopped = [
        _bar(0, 2000, 2001.2, 1999.9, 2001.05),
        _bar(1, 2001.05, 2001.1, 1990, 1992),
    ]
    out = _run(stopped, entry_pts=100, sl_pts=500, be_pts=0, trail_pts=0, reverse_on="sl")
    assert [r["origin"] for r in out["rows"]] == ["stop", "reverse"]
    trailed = [_bar(0, 2000, 2005, 1999.8, 2004)]
    trail = _run(
        trailed,
        entry_pts=100,
        sl_pts=500,
        be_pts=150,
        trail_pts=100,
        trail_arm_pts=200,
        reverse_on="sl",
    )
    assert len(trail["rows"]) == 1
    assert trail["rows"][0]["exit_reason"] == "trail"


def test_spread_worsens_the_entry_and_a_wide_spread_blocks_entries():
    bars = [_bar(0, 2000, 2001.4, 1999.9, 2001.3)]
    paid = _run(bars, entry_pts=100, sl_pts=500, be_pts=0, trail_pts=0, spread_pts=20, reverse=False)
    assert paid["rows"][0]["entry"] == 2001.2
    blocked = _run(
        bars,
        entry_pts=100,
        sl_pts=500,
        spread_pts=30,
        max_spread_pts=20,
    )
    assert blocked["trades"] == 0


def test_rejects_a_non_positive_stop():
    with pytest.raises(ValueError, match="SL"):
        validate_params(StopScalperParams(sl_pts=0))
    with pytest.raises(ValueError, match="Entry"):
        validate_params(StopScalperParams(entry_pts=0))
