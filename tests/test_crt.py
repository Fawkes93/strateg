"""CRT trend model: sweep back inside, then a lower-timeframe gap."""

from datetime import datetime, timedelta, timezone

import pytest

from backtest.candles import Candle
from backtest.crt import (
    CrtParams,
    cap_open,
    normalize_params,
    rules_for,
    run_crt_on_candles,
    trend_of,
)


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
        side_filter="both",
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
