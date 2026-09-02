from datetime import date

from backtest.news_calendar import (
    events_on,
    is_news_day,
    kinds_for_set,
    load_events,
    news_dates,
    normalize_news_mode,
    normalize_news_set,
)


def test_calendar_covers_2023_to_2026():
    events = load_events()
    assert events[0].date >= date(2023, 1, 1)
    assert events[-1].date.year == 2026
    kinds = {e.kind for e in events}
    assert kinds == {"fomc", "cpi", "nfp", "jackson_hole", "shock"}


def test_known_prints():
    assert is_news_day("2023-01-06", kinds={"nfp"})
    nfp = events_on("2023-01-06", kinds={"nfp"})
    assert nfp and "NFP" in nfp[0].title
    fomc = events_on("2026-01-28", kinds={"fomc"})
    assert fomc and fomc[0].time_et == "14:00"
    cpi = events_on("2025-10-24", kinds={"cpi"})
    assert cpi  # delayed September 2025 CPI after shutdown
    assert not is_news_day("2025-10-15", kinds={"cpi"})  # original slot, not published


def test_sets_exclude_shocks_by_default():
    yen = date(2024, 8, 5)
    assert is_news_day(yen, kinds=kinds_for_set("all"))
    assert not is_news_day(yen, kinds=kinds_for_set("scheduled"))
    assert is_news_day("2024-08-02", kinds=kinds_for_set("scheduled"))  # NFP


def test_svb_day_is_nfp_and_shock():
    hits = events_on("2023-03-10")
    assert {e.kind for e in hits} == {"nfp", "shock"}


def test_normalize():
    assert normalize_news_mode("FILTER") == "filter"
    assert normalize_news_mode("nope") == "off"
    assert normalize_news_set("ALL") == "all"
    assert normalize_news_set("macro") == "scheduled"


def test_news_dates_are_unique_per_kind_set():
    sched = news_dates(kinds=kinds_for_set("scheduled"))
    assert date(2023, 2, 1) in sched  # FOMC
    assert date(2024, 8, 5) not in sched
    assert date(2024, 8, 5) in news_dates(kinds=kinds_for_set("all"))
