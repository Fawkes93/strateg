from datetime import date

from backtest.seasonality import (
    against_bias,
    bias_side,
    month_regime,
    normalize_seasonal_mode,
    seasonal_label,
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
