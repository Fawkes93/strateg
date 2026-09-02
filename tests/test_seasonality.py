from datetime import date

from backtest.seasonality import (
    DailyClose,
    against_bias,
    bias_side,
    combine_sides,
    month_regime,
    normalize_seasonal_mode,
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
