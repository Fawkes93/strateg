from datetime import date

from backtest.seasonality import (
    DailyClose,
    against_bias,
    bias_side,
    combine_sides,
    month_regime,
    normalize_seasonal_mode,
    normalize_week2_mode,
    seasonal_label,
    snapshot_bias,
    week2_trend,
)


def test_xau_month_table():
    assert month_regime(date(2025, 1, 6)) == "strong"
    assert month_regime(date(2025, 8, 15)) == "strong"
    assert month_regime(date(2025, 5, 6)) == "soft"
    assert month_regime(date(2025, 6, 3)) == "soft"
    assert month_regime(date(2026, 4, 1)) == "neutral"
    assert month_regime(date(2026, 9, 1)) == "neutral"


def test_bias_and_against():
    assert bias_side("strong") == "UP"
    assert bias_side("soft") == "DOWN"
    assert bias_side("neutral") is None
    assert against_bias("strong", "DOWN") is True
    assert against_bias("strong", "UP") is False
    assert against_bias("neutral", "DOWN") is False


def test_normalize_and_label():
    assert normalize_seasonal_mode("FILTER") == "filter"
    assert normalize_seasonal_mode("nope") == "off"
    assert "Jan" in seasonal_label("strong", date(2025, 1, 6))
    assert "long" in seasonal_label("strong")


def test_combine_sides_conflict_and_agree():
    side, conflict = combine_sides("UP", "DOWN")
    assert side is None and conflict is True
    side, conflict = combine_sides("UP", "UP")
    assert side == "UP" and conflict is False
    side, conflict = combine_sides("UP", None)
    assert side == "UP" and conflict is False
    side, conflict = combine_sides(None, "DOWN")
    assert side == "DOWN" and conflict is False
    side, conflict = combine_sides(None, None)
    assert side is None and conflict is False


def test_week2_trend_up_down_flat():
    asof = date(2025, 1, 20)
    rising = [
        DailyClose(date(2025, 1, i), 3300.0 + i * 3.0)
        for i in range(1, 16)
    ]
    up = week2_trend(rising, asof, sessions=10, flat_pts=1500.0, ps=0.01)
    assert up["state"] == "up"
    assert up["side"] == "UP"
    falling = [
        DailyClose(date(2025, 1, i), 3400.0 - i * 3.0)
        for i in range(1, 16)
    ]
    down = week2_trend(falling, asof, sessions=10, flat_pts=1500.0, ps=0.01)
    assert down["state"] == "down"
    assert down["side"] == "DOWN"
    assert up.get("efficiency") is not None and up["efficiency"] > 0.9
    flat = week2_trend(rising, asof, sessions=10, flat_pts=50000.0, ps=0.01)
    assert flat["state"] == "flat"
    assert flat["side"] is None


def test_snapshot_january_vs_down_trend_is_conflict():
    asof = date(2025, 1, 20)
    falling = [
        DailyClose(date(2025, 1, i), 3400.0 - i * 3.0)
        for i in range(1, 16)
    ]
    snap = snapshot_bias(
        asof,
        dailies=falling,
        use_season=True,
        use_week2=True,
        flat_pts=1500.0,
        sessions=10,
        ps=0.01,
    )
    assert snap.season_side == "UP"
    assert snap.trend_side == "DOWN"
    assert snap.conflict is True
    assert snap.filter_side is None


def test_normalize_week2_mode_legacy_checkbox():
    assert normalize_week2_mode("filter") == "filter"
    assert normalize_week2_mode("off") == "off"
    assert normalize_week2_mode("off", week2_trend=True, seasonal_mode="off") == "tag"
    assert normalize_week2_mode(None, week2_trend=True, seasonal_mode="off") == "tag"
    assert (
        normalize_week2_mode(None, week2_trend=True, seasonal_mode="filter")
        == "filter"
    )
    assert normalize_week2_mode(None, week2_trend=False) == "off"


def test_week2_chop_is_flat_even_with_large_net():
    asof = date(2025, 1, 20)
    px = 3300.0
    days = []
    # +20 / -15 … net +40 over 9 steps, efficiency 40/160 = 0.25
    deltas = [20, -15, 20, -15, 20, -15, 20, -15, 20]
    for i, dlt in enumerate(deltas, start=1):
        px += dlt
        days.append(DailyClose(date(2025, 1, i), px))
    chop = week2_trend(
        days, asof, sessions=10, flat_pts=1500.0, efficiency_min=0.35, ps=0.01
    )
    assert chop["state"] == "flat"
    assert chop["side"] is None
    assert chop["efficiency"] < 0.35
    assert abs(chop["net_pts"]) > 1500
    no_eff = week2_trend(
        days, asof, sessions=10, flat_pts=1500.0, efficiency_min=0.0, ps=0.01
    )
    assert no_eff["side"] in ("UP", "DOWN")


def test_week2_filter_without_season_uses_trend_side():
    asof = date(2026, 4, 1)
    falling = [
        DailyClose(date(2026, 3, i), 3400.0 - i * 3.0) for i in range(1, 16)
    ]
    snap = snapshot_bias(
        asof,
        dailies=falling,
        use_season=False,
        use_week2=True,
        season_filter=False,
        week2_filter=True,
        flat_pts=1500.0,
        sessions=10,
        efficiency_min=0.35,
        ps=0.01,
    )
    assert snap.season_side is None
    assert snap.trend_side == "DOWN"
    assert snap.filter_side == "DOWN"
    assert snap.conflict is False
