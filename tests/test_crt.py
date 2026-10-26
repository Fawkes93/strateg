"""CRT trend model: sweep back inside, then a lower-timeframe gap."""

from datetime import datetime, timedelta, timezone

import pytest

from backtest.candles import Candle
from backtest.crt import (
    CrtParams,
    cap_open,
    mark_drawdown,
    normalize_params,
    rules_for,
    run_crt_on_candles,
    summarize_crt,
    trade_charges,
    trend_of,
)
from backtest.crt_api import CrtRunRequest, _params_from_body


def _bar(minute_offset: int, o, h, l, c) -> Candle:
    start = datetime(2025, 3, 3, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=minute_offset)
    return Candle(
        open_time=start,
        close_time=start + timedelta(minutes=5),
        open=float(o),
        high=float(h),
        low=float(l),
        close=float(c),
        is_closed=True,
    )


def _pack(legs):
    return [_bar(i * 5, *leg) for i, leg in enumerate(legs)]


# 15m bars from 08:00. Four-bar up impulse, bearish discount range, sweep, then the rally.
_UP = [
    # 08:00 low of the dealing range
    (2000, 2001, 1995, 1998),
    (1998, 1999, 1990, 1992),
    (1992, 1994, 1991, 1992),
    # 08:15
    (1992, 2000, 1991, 1999),
    (1999, 2010, 1998, 2008),
    (2008, 2009, 2006, 2008),
    # 08:30
    (2008, 2015, 2007, 2014),
    (2014, 2020, 2013, 2018),
    (2018, 2019, 2016, 2018),
    # 08:45 impulse high 2030
    (2018, 2024, 2017, 2023),
    (2023, 2030, 2022, 2028),
    (2028, 2029, 2026, 2028),
    # 09:00 bearish range, close 2006 is below equilibrium 2010. CRL 2004, CRH 2025.
    (2024, 2025, 2018, 2020),
    (2020, 2021, 2010, 2012),
    (2012, 2013, 2004, 2006),
    # 09:15 sweep under 2004 and close 2012 back inside. Bullish gap 2007–2010.
    (2006, 2007, 2000, 2005),
    (2005, 2012, 2004, 2011),
    (2011, 2014, 2010, 2012),
    # 09:30 fill the proximal edge at 2010. Stop is the gap bottom 2007.
    (2012, 2012.5, 2009, 2011),
    # 09:35 1:1 at 2013
    (2011, 2016, 2010.5, 2015),
    # 09:40 runner, the dealing-range high 2030
    (2015, 2032, 2014, 2030),
]


def _params(**overrides) -> CrtParams:
    base = dict(
        timezone="Europe/Bucharest",
        htf_min=15,
        ltf_min=5,
        structure_bars=4,
        pd_filter=True,
        equilibrium=0.5,
        entry_mode="fvg",
        fvg_select="first",
        fvg_entry="proximal",
        max_fvgs=2,
        fvg_wait_htf=3,
        sl_mode="beyond_fvg",
        sl_buffer_pts=0,
        partial_frac=0.5,
        partial_rr=1,
        runner_mode="swing",
        runner_rr=2,
        max_hold_htf=12,
        max_concurrent=0,
        session_enabled=False,
        skip_news=False,
        direction="both",
        cost_pts=0,
    )
    base.update(overrides)
    return normalize_params(CrtParams(**base))


def _run(legs, **overrides):
    return run_crt_on_candles(
        _pack(legs),
        symbol="XAUUSD",
        params=_params(**overrides),
        date_from="2025-03-01",
        date_to="2025-03-10",
    )


def test_beyond_sweep_normal_fill_keeps_the_wick_stop():
    raw = _run(_UP, sl_mode="beyond_sweep")
    assert len(raw["rows"]) == 1
    row = raw["rows"][0]
    assert row["entry"] == 2010
    assert row["sl"] == 2000
    assert row["exit_reason"] == "tp"
    assert row["exit"] == 2030
    assert row["pts"] == 1500
    assert raw["skip_reasons"].get("invalidated_before_fill", 0) == 0


def test_beyond_sweep_break_before_fill_is_skipped():
    # Same morning impulse and bearish range as _UP. The sweep wick is 2000 and
    # the close is back inside, but no gap exists yet. The next bar trades
    # through 2000. A later gap would have filled at 2010; that order is cancelled.
    legs = list(_UP[:15]) + [
        (2006, 2008, 2000, 2004),
        (2004, 2007, 2003, 2006),
        (2006, 2009, 2005, 2008),
        (2008, 2009, 1994, 1996),
        (1996, 2002, 1995, 2001),
        (2001, 2012, 2000, 2011),
        (2011, 2016, 2010, 2014),
        (2014, 2015, 2009, 2012),
    ]
    raw = _run(legs, sl_mode="beyond_sweep")
    assert raw["rows"] == []
    assert raw["skip_reasons"].get("invalidated_before_fill") == 1


def test_long_fvg_runs_to_the_dealing_high():
    raw = _run(_UP)
    assert len(raw["rows"]) == 1
    row = raw["rows"][0]
    assert row["side"] == "UP"
    assert row["entry_reason"] == "fvg"
    assert row["entry"] == 2010
    assert row["sl"] == 2007
    assert row["partial_px"] == 2013
    assert row["tp"] == 2030
    assert row["exit_reason"] == "tp"
    assert row["exit"] == 2030
    assert row["pts"] == 1150
    assert row["crh"] == 2025
    assert row["crl"] == 2004
    assert row["fvg_bottom"] == 2007
    assert row["fvg_top"] == 2010
    assert "discount" in row["story"]
    assert "closed back inside" in row["story"]


def test_partial_then_stop_is_a_scratch():
    legs = list(_UP)
    legs[-1] = (2015, 2016, 2006, 2008)
    raw = _run(legs)
    assert len(raw["rows"]) == 1
    row = raw["rows"][0]
    assert row["exit_reason"] == "partial_sl"
    assert row["pts"] == 0
    assert row["partial_hit"] is True


def test_close_through_is_not_a_trade():
    legs = list(_UP)
    legs[17] = (2011, 2014, 2001, 2002)
    raw = _run(legs)
    assert raw["rows"] == []
    assert raw["skips"][0]["reason"] == "close_through"


def test_bullish_candle_in_an_uptrend_is_ignored():
    legs = list(_UP)
    legs[12] = (2004, 2010, 2003, 2008)
    legs[13] = (2008, 2016, 2007, 2015)
    legs[14] = (2015, 2022, 2014, 2020)
    raw = _run(legs)
    assert raw["rows"] == []


def test_premium_close_blocks_the_long_until_the_filter_is_off():
    legs = list(_UP)
    legs[14] = (2012, 2020, 2004, 2020)
    assert _run(legs)["rows"] == []
    raw = _run(legs, pd_filter=False)
    assert len(raw["rows"]) == 1
    assert raw["rows"][0]["side"] == "UP"


def test_sweep_close_enters_at_the_higher_timeframe_close():
    raw = _run(_UP, entry_mode="sweep_close", sl_mode="beyond_sweep")
    row = raw["rows"][0]
    assert row["entry_reason"] == "sweep_close"
    assert row["entry"] == 2012
    assert row["sl"] == 2000
    assert row["exit_reason"] == "tp"
    assert row["pts"] == 1500


def test_short_fvg_in_premium():
    # High prints first, then the low. Bullish range closes in premium. Sweep of CRH.
    legs = [
        (2020, 2030, 2018, 2028),
        (2028, 2029, 2024, 2026),
        (2026, 2027, 2025, 2026),
        (2026, 2027, 2015, 2016),
        (2016, 2017, 2010, 2012),
        (2012, 2013, 2011, 2012),
        (2012, 2013, 2005, 2006),
        (2006, 2007, 2000, 2002),
        (2002, 2003, 2001, 2002),
        (2002, 2003, 1995, 1996),
        (1996, 1997, 1990, 1992),
        (1992, 1993, 1991, 1992),
        # Bullish range. CRH 2018, close 2016 is above equilibrium 2010.
        (1994, 2008, 1993, 2006),
        (2006, 2014, 2005, 2012),
        (2012, 2018, 2011, 2016),
        # Sweep above 2018, close 2010 back inside. Bearish gap 2014–2015.
        (2016, 2022, 2015, 2020),
        (2020, 2021, 2012, 2013),
        (2013, 2014, 2008, 2010),
        # Rally into the proximal edge 2014. Stop above the gap at 2015.
        (2010, 2014.5, 2013.2, 2013.5),
        # Runner is the dealing-range low 1990.
        (2013.5, 2013.6, 1988, 1992),
    ]
    raw = _run(legs)
    assert len(raw["rows"]) == 1
    row = raw["rows"][0]
    assert row["side"] == "DOWN"
    assert row["entry"] == 2014
    assert row["sl"] == 2015
    assert row["fvg_bottom"] == 2014
    assert row["fvg_top"] == 2015
    assert row["tp"] == 1990
    assert row["exit_reason"] == "tp"
    assert row["exit"] == 1990
    assert "premium" in row["story"]


def test_session_filter_uses_the_local_clock():
    # 09:15 UTC is 11:15 in Bucharest on 3 Mar 2025 (UTC+2).
    assert _run(_UP, session_enabled=True, session_start_hour=0, session_end_hour=1)["rows"] == []
    raw = _run(_UP, session_enabled=True, session_start_hour=11, session_end_hour=12)
    assert len(raw["rows"]) == 1


def test_news_day_is_skipped(monkeypatch):
    monkeypatch.setattr("backtest.crt.is_news_day", lambda day, **kwargs: True)
    raw = _run(_UP, skip_news=True)
    assert raw["rows"] == []
    assert raw["skips"][0]["reason"] == "news"


def test_trend_of_needs_the_extremes_on_different_bars():
    same = [
        Candle(datetime(2025, 3, 3, tzinfo=timezone.utc), datetime(2025, 3, 3, 0, 15, tzinfo=timezone.utc), 1, 3, 0, 2),
        Candle(datetime(2025, 3, 3, 0, 15, tzinfo=timezone.utc), datetime(2025, 3, 3, 0, 30, tzinfo=timezone.utc), 2, 2.5, 1, 2),
    ]
    # The high and the low are both on the first bar.
    assert trend_of(same) is None
    up = [
        Candle(datetime(2025, 3, 3, tzinfo=timezone.utc), datetime(2025, 3, 3, 0, 15, tzinfo=timezone.utc), 1, 2, 0, 1.5),
        Candle(datetime(2025, 3, 3, 0, 15, tzinfo=timezone.utc), datetime(2025, 3, 3, 0, 30, tzinfo=timezone.utc), 1.5, 4, 1.2, 3),
    ]
    assert trend_of(up) == "up"


def test_cap_open_keeps_the_earlier_fill():
    rows = [
        {"entry_ts": "2025-03-03T09:30:00+00:00", "exit_ts": "2025-03-03T12:00:00+00:00", "_seq": 1},
        {"entry_ts": "2025-03-03T10:00:00+00:00", "exit_ts": "2025-03-03T11:00:00+00:00", "_seq": 2},
    ]
    kept, skipped = cap_open(rows, 1)
    assert len(kept) == 1 and kept[0]["_seq"] == 1
    assert len(skipped) == 1
    kept, skipped = cap_open(rows, 0)
    assert len(kept) == 2 and skipped == []


def test_rules_name_the_sweep_and_the_partial():
    rules = {row["id"]: row["body"] for row in rules_for(_params())}
    assert "closes back inside" in rules["sweep"]
    assert "0.5" in rules["partial"]
    assert "1 R" in rules["partial"]
    assert "no cap" in rules["hold"]
    assert "ny_open" in rules["mode"]
    ny = {row["id"]: row["body"] for row in rules_for(_params(mode="ny_open"))}
    assert "One attempt per day" in ny["mode"]
    assert "08:00" in ny["mode"]
    assert "America/New_York" in ny["mode"]


def _ny_bars():
    """15m candle closing 08:00 New York on 3 Mar 2025 (13:00 UTC), then the sweep hour."""
    start = datetime(2025, 3, 3, 12, 45, tzinfo=timezone.utc)
    legs = [
        (2010, 2020, 2005, 2015),
        (2015, 2016, 2000, 2012),
        (2012, 2014, 2008, 2011),
        (2011, 2012, 1990, 2005),
        (2005, 2008, 2002, 2006),
        (2006, 2010, 2004, 2010),
        (2010, 2011, 2005, 2008),
    ]
    out = []
    for i, (o, h, l, c) in enumerate(legs):
        opened = start + timedelta(minutes=5 * i)
        out.append(
            Candle(
                open_time=opened,
                close_time=opened + timedelta(minutes=5),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                is_closed=True,
            )
        )
    return out


def test_ny_open_takes_one_attempt_and_ignores_the_morning_trend():
    candles = _pack(_UP) + _ny_bars()
    raw = run_crt_on_candles(
        candles,
        symbol="XAUUSD",
        params=_params(mode="ny_open", entry_mode="sweep_close", sl_mode="beyond_sweep"),
        date_from="2025-03-01",
        date_to="2025-03-10",
    )
    assert len(raw["rows"]) == 1
    row = raw["rows"][0]
    assert row["side"] == "UP"
    assert row["entry"] == 2010
    assert row["sl"] == 1990
    assert row["crh"] == 2020
    assert row["crl"] == 2000
    assert "New York open" in row["story"]
    assert "one" not in row["story"].lower() or "only range" in row["story"]


def test_ny_open_close_through_does_not_fall_back_to_another_candle():
    bars = _ny_bars()
    # Last 5m of the sweep hour closes through the range low.
    bars[5] = Candle(
        open_time=bars[5].open_time,
        close_time=bars[5].close_time,
        open=2006,
        high=2010,
        low=1992,
        close=1995,
        is_closed=True,
    )
    raw = run_crt_on_candles(
        _pack(_UP) + bars,
        symbol="XAUUSD",
        params=_params(mode="ny_open", entry_mode="sweep_close"),
        date_from="2025-03-01",
        date_to="2025-03-10",
    )
    assert raw["rows"] == []
    assert raw["skips"][0]["reason"] == "close_through"


def test_normalize_rejects_a_timeframe_the_engine_cannot_build():
    normalize_params(CrtParams(htf_min=60, ltf_min=30))
    with pytest.raises(ValueError):
        normalize_params(CrtParams(htf_min=15, ltf_min=15))
    with pytest.raises(ValueError):
        normalize_params(CrtParams(htf_min=30, ltf_min=60))


def test_min_sl_skips_a_tighter_stop_and_keeps_the_boundary():
    # beyond_fvg stop on the standard long is 300 points (2010 to 2007).
    kept = _run(_UP, min_sl_pts=290)
    assert len(kept["rows"]) == 1
    assert kept["rows"][0]["pts"] == 1150
    skipped = _run(_UP, min_sl_pts=310)
    assert skipped["rows"] == []
    assert skipped["skip_reasons"].get("min_sl") == 1


def test_spread_is_once_and_commission_is_per_fill():
    assert trade_charges(True, 0.5, 10, 4) == 10 + 4 * 3
    assert trade_charges(False, 0.5, 10, 4) == 10 + 4 * 2
    raw = _run(_UP, cost_pts=10, commission_pts=4)
    assert raw["rows"][0]["pts"] == 1150 - 22


def test_direction_keeps_one_side():
    assert _run(_UP, direction="short")["rows"] == []
    assert len(_run(_UP, direction="long")["rows"]) == 1
    params = _params_from_body(CrtRunRequest(side_filter="short"))
    assert params.direction == "short"
    assert _params_from_body(CrtRunRequest(direction="long")).direction == "long"


def test_ny_open_respects_min_leg():
    candles = _pack(_UP) + _ny_bars()
    params = dict(mode="ny_open", entry_mode="sweep_close", sl_mode="beyond_sweep")
    wide = run_crt_on_candles(
        candles,
        symbol="XAUUSD",
        params=_params(min_leg_pts=1000, **params),
        date_from="2025-03-01",
        date_to="2025-03-10",
    )
    tight = run_crt_on_candles(
        candles,
        symbol="XAUUSD",
        params=_params(min_leg_pts=100000, **params),
        date_from="2025-03-01",
        date_to="2025-03-10",
    )
    assert len(wide["rows"]) == 1
    assert tight["rows"] == []


def test_mark_to_market_drawdown_sees_the_open_dip():
    start = datetime(2025, 3, 3, 10, 0, tzinfo=timezone.utc)
    bars = []
    closes = [100.0, 90.0, 110.0]
    for i, close in enumerate(closes):
        opened = start + timedelta(minutes=5 * i)
        bars.append(
            Candle(
                open_time=opened,
                close_time=opened + timedelta(minutes=5),
                open=close,
                high=close,
                low=close,
                close=close,
                is_closed=True,
            )
        )
    # 1000 pts up from 100 to 110 at 0.01. The middle close is 1000 pts under water.
    trade = {
        "side": "UP",
        "entry": 100.0,
        "partial_px": 110.0,
        "pts": 1000.0,
        "partial_hit": False,
        "entry_ts": bars[0].open_time.isoformat(),
        "exit_ts": bars[2].open_time.isoformat(),
        "partial_ts": None,
    }
    dd = mark_drawdown([trade], bars, _params(cost_pts=0, commission_pts=0), 0.01)
    assert dd["max_dd_closed_pts"] == 0
    assert dd["max_dd_pts"] == 1000


def test_results_split_pf_by_year_and_direction():
    rows = [
        {"local_date": "2025-03-03", "side": "UP", "pts": 100.0, "exit_reason": "tp", "entry_reason": "fvg"},
        {"local_date": "2025-06-02", "side": "DOWN", "pts": -50.0, "exit_reason": "sl", "entry_reason": "fvg"},
        {"local_date": "2026-01-05", "side": "UP", "pts": 40.0, "exit_reason": "tp", "entry_reason": "fvg"},
    ]
    out = summarize_crt(
        {"rows": rows, "skips": [], "symbol": "XAU/USD", "point_size": 0.01, "ticks": 0},
        _params(),
        symbol="XAUUSD",
    )
    assert [row["year"] for row in out["by_year"]] == ["2025", "2026"]
    assert out["by_year"][0]["profit_factor"] == 2.0
    assert out["by_direction"]["long"]["trades"] == 2
    assert out["by_direction"]["long"]["sum_pts"] == 140
    assert out["by_direction"]["short"]["profit_factor"] == 0.0


def test_stdio_reconfigure_accepts_an_arrow():
    import io
    import sys

    from webapp import _configure_stdio

    raw = io.BytesIO()
    wrapper = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    sys.stdout = wrapper
    try:
        _configure_stdio()
        sys.stdout.write("→\n")
        sys.stdout.flush()
        assert "→" in raw.getvalue().decode("utf-8")
    finally:
        sys.stdout = sys.__stdout__


def _dedupe_row(seq, range_open, fvg_open, entry, side="UP"):
    return {"_seq": seq, "side": side, "range_open_ts": range_open, "fvg_open_ts": fvg_open, "entry": entry, "local_date": "2025-03-03", "weekday": "Mon"}


def test_dedupe_two_ranges_sharing_one_fvg_book_one_trade():
    from backtest.crt import dedupe_fvg_rows
    later = _dedupe_row(2, "2025-03-03T09:00:00Z", "2025-03-03T09:20:00Z", 2010.0)
    earlier = _dedupe_row(1, "2025-03-03T08:00:00Z", "2025-03-03T09:20:00Z", 2010.0)
    kept, dropped = dedupe_fvg_rows([later, earlier], "XAUUSD")
    assert [r["_seq"] for r in kept] == [1]
    assert [r["_seq"] for r in dropped] == [2]


def test_dedupe_keeps_two_different_fvgs_in_one_range():
    from backtest.crt import dedupe_fvg_rows
    a = _dedupe_row(1, "2025-03-03T09:00:00Z", "2025-03-03T09:20:00Z", 2010.0)
    b = _dedupe_row(2, "2025-03-03T09:00:00Z", "2025-03-03T09:35:00Z", 2016.0)
    kept, dropped = dedupe_fvg_rows([a, b], "XAUUSD")
    assert len(kept) == 2 and dropped == []


def test_dedupe_ignores_sweep_close_rows_and_other_sides():
    from backtest.crt import dedupe_fvg_rows
    a = _dedupe_row(1, "2025-03-03T08:00:00Z", None, 2010.0)
    b = _dedupe_row(2, "2025-03-03T09:00:00Z", None, 2010.0)
    c = _dedupe_row(3, "2025-03-03T09:00:00Z", "2025-03-03T09:20:00Z", 2010.0, side="DOWN")
    d = _dedupe_row(4, "2025-03-03T08:00:00Z", "2025-03-03T09:20:00Z", 2010.0)
    kept, _ = dedupe_fvg_rows([a, b, c, d], "XAUUSD")
    assert len(kept) == 4


def test_run_rows_carry_the_fvg_open_time_and_dedupe_is_on_by_default():
    raw = _run(_UP)
    assert raw["rows"][0]["fvg_open_ts"] == "2025-03-03T09:15:00+00:00"
    assert _params().dedupe_fvg_across_ranges is True
    assert len(_run(_UP, dedupe_fvg_across_ranges=False)["rows"]) == 1


# --- causal gap selection (no lookahead) -------------------------------------------------

def _walk(n=4000, seed=7):
    import random

    rnd = random.Random(seed)
    start = datetime(2025, 3, 3, 0, 0, tzinfo=timezone.utc)
    out, px = [], 2000.0
    for i in range(n):
        o = px
        c = o + rnd.gauss(0, 1.2) + (3.0 if rnd.random() < 0.03 else 0.0) * rnd.choice((-1, 1))
        h = max(o, c) + abs(rnd.gauss(0, 0.6))
        l = min(o, c) - abs(rnd.gauss(0, 0.6))
        t = start + timedelta(minutes=5 * i)
        out.append(Candle(open_time=t, close_time=t + timedelta(minutes=5), open=o, high=h, low=l, close=c, is_closed=True))
        px = c
    return out


def _entries(bars, cut, **kw):
    p = CrtParams(htf_min=60, pd_filter=False, structure_bars=12, fvg_wait_htf=4, max_fvgs=2, cost_pts=0, **kw)
    rows = run_crt_on_candles(bars, symbol="XAUUSD", params=p)["rows"]
    return sorted(
        (r["range_open_ts"], r["fvg_open_ts"], round(float(r["entry"]), 6), r["entry_ts"])
        for r in rows
        if datetime.fromisoformat(str(r["entry_ts"]).replace("Z", "+00:00")) < cut
    )


@pytest.mark.parametrize("select", ["first", "extreme", "all", "extreme_at_close"])
def test_truncating_the_future_does_not_change_earlier_entries(select):
    bars = _walk()
    total = 0
    for k in (1500, 2300, 3100):
        cut = bars[k].open_time
        full = _entries(bars, cut, fvg_select=select)
        short = _entries(bars[:k], cut, fvg_select=select)
        assert full == short, (select, k)
        total += len(full)
    assert total > 0, "synthetic data should produce some fills"


def test_legacy_extreme_can_see_future_gaps():
    bars = _walk()
    leaked = False
    for k in range(1200, 3900, 50):
        cut = bars[k].open_time
        if _entries(bars, cut, fvg_select="all", lookahead_legacy=True) != _entries(bars[:k], cut, fvg_select="all", lookahead_legacy=True):
            leaked = True
            break
    if not leaked:
        pytest.skip("synthetic data did not expose the legacy lookahead")


def test_causal_caps_fills_per_setup():
    bars = _walk()
    for select, cap in (("first", 1), ("extreme", 1), ("extreme_at_close", 1), ("all", 2)):
        p = CrtParams(htf_min=60, pd_filter=False, structure_bars=12, fvg_wait_htf=4, max_fvgs=2, fvg_select=select, dedupe_fvg_across_ranges=False)
        rows = run_crt_on_candles(bars, symbol="XAUUSD", params=p)["rows"]
        per = {}
        for r in rows:
            per[r["range_open_ts"]] = per.get(r["range_open_ts"], 0) + 1
        assert not per or max(per.values()) <= cap, select


def test_extreme_at_close_needs_the_causal_engine():
    with pytest.raises(ValueError):
        normalize_params(CrtParams(fvg_select="extreme_at_close", lookahead_legacy=True))


@pytest.mark.parametrize(
    "extra",
    [
        dict(min_sweep_pts=50.0),
        dict(min_range_atr=0.5, max_range_atr=3.0),
        dict(bias_bars=48),
        dict(min_fvg_pts=30.0),
        dict(be_after_partial=True),
        dict(runner_mode="range"),
        dict(entry_mode="range_mid", sl_mode="beyond_sweep"),
        dict(entry_mode="sweep_close", sl_mode="beyond_sweep"),
        dict(ltf_min=15),
        dict(session_enabled=True, session_start_hour=9, session_end_hour=18),
    ],
)
def test_new_filters_do_not_read_the_future(extra):
    bars = _walk()
    for k in (1700, 2900):
        cut = bars[k].open_time
        assert _entries(bars, cut, fvg_select="extreme", **extra) == _entries(bars[:k], cut, fvg_select="extreme", **extra), (extra, k)


def test_new_params_default_to_the_causal_engine():
    bars = _walk()
    base = run_crt_on_candles(bars, symbol="XAUUSD", params=CrtParams(htf_min=60, pd_filter=False, structure_bars=12))["rows"]
    same = run_crt_on_candles(
        bars,
        symbol="XAUUSD",
        params=CrtParams(htf_min=60, pd_filter=False, structure_bars=12, min_sweep_pts=0, min_range_atr=0, max_range_atr=0, bias_bars=0, min_fvg_pts=0, be_after_partial=False),
    )["rows"]
    assert [r["pts"] for r in base] == [r["pts"] for r in same]


def test_breakeven_never_loses_more_than_costs_after_the_partial():
    bars = _walk()
    p = CrtParams(htf_min=60, pd_filter=False, structure_bars=12, be_after_partial=True, cost_pts=0)
    rows = run_crt_on_candles(bars, symbol="XAUUSD", params=p)["rows"]
    assert all(float(r["pts"]) >= -1e-6 for r in rows if r["exit_reason"] == "partial_sl")
