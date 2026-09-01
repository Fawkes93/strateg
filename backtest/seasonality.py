"""Conservative XAU month regimes for Asia / overnight break.

Not a day-of-year scan. Only months that repeatedly show up in multi-year gold
work: January effect, summer doldrums, late-summer bid. September is not marked
soft — that story is sample-dependent.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

# Bucharest calendar month → regime. Missing months stay neutral.
XAU_MONTH_REGIMES = {
    1: "strong",  # January
    8: "strong",  # August
    5: "soft",  # May
    6: "soft",  # June
}

REGIME_LABELS = {
    "strong": "strong (long bias)",
    "soft": "soft (short bias)",
    "neutral": "neutral",
}


def month_regime(local_day: date) -> str:
    return XAU_MONTH_REGIMES.get(int(local_day.month), "neutral")


def bias_side(regime: str) -> Optional[str]:
    if regime == "strong":
        return "UP"
    if regime == "soft":
        return "DOWN"
    return None


def against_bias(regime: str, side: Optional[str]) -> bool:
    want = bias_side(regime)
    return want is not None and side is not None and side != want


def seasonal_label(regime: str, local_day: Optional[date] = None) -> str:
    body = REGIME_LABELS.get(regime, regime or "neutral")
    if local_day is None:
        return body
    return f"{local_day.strftime('%b')} {body}"


def normalize_seasonal_mode(mode: Optional[str]) -> str:
    m = (mode or "off").strip().lower()
    if m in ("off", "tag", "filter"):
        return m
    return "off"
