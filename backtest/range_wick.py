"""
Legacy 15m range-expansion signal (wick-latched) — Reaktor range_wick.

Parallel alert type (source=candle_wick) for A/B vs live range (candle).

Decision rules (wick):
  — side = larger wick excursion from open (high−open vs open−low)
  — directed distance = max(H−O, O−L) ≥ max(mult × median completed, min pts)
  — body floor vs |close−open| on the forming candle
  — structure: forming.high > prior high (UP) / forming.low < prior low (DOWN)
  — uses forming H/L for expansion + structure (wick-latched), close for body/side

Uses RANGE_WICK_THRESHOLDS only (independent of live THRESHOLDS).
"""

from __future__ import annotations

from statistics import mean, median
from typing import Any, Optional

from backtest import config
from backtest.range_live import (
    candle_range_pct,
    directed_excursion_price,
    directed_side,
    price_to_points_delta,
)

ALERT_KIND = "candle_wick"


def calculate_wick_metrics(
    builder: Any,
    current_price: float,
    lookback: int = None,
    symbol: str = "XAU/USD",
) -> Optional[dict]:
    """Metrics for wick-latched range (pre–live-hold semantics)."""
    cfg = (config.RANGE_WICK_THRESHOLDS or {}).get(symbol) or {}
    if lookback is None:
        lookback = int(cfg.get("lookback") or config.CANDLE_LOOKBACK)

    forming = builder.get_current_candle()
    if forming is None or forming.open <= 0:
        return None

    completed = builder.get_completed_candles(lookback)
    if len(completed) < 1:
        return None

    hl_ranges = [candle_range_pct(c) for c in completed]
    avg_hl = mean(hl_ranges) if hl_ranges else 0.0
    forming_hl = candle_range_pct(forming)

    dir_prices = [directed_excursion_price(c) for c in completed]
    baseline_dir_price = median(dir_prices) if dir_prices else 0.0
    forming_dir_price = directed_excursion_price(forming)
    side = directed_side(forming)
    dir_ratio = (
        (forming_dir_price / baseline_dir_price) if baseline_dir_price > 0 else 0.0
    )

    move_vs_open_pct = ((forming.close - forming.open) / forming.open) * 100
    prev = completed[-1]
    move_vs_prev_close_pct = (
        ((current_price - prev.close) / prev.close) * 100 if prev.close > 0 else 0.0
    )

    body_price = abs(forming.close - forming.open)

    n_struct = int(cfg.get("structure_break_lookback") or 0)
    struct_bars = completed[-n_struct:] if n_struct > 0 else []
    prior_high = max((b.high for b in struct_bars), default=None)
    prior_low = min((b.low for b in struct_bars), default=None)
    if n_struct <= 0 or not struct_bars or prior_high is None or prior_low is None:
        structure_break_ok = True
        structure_break_reason = "off"
    elif side == "UP":
        buf = float(cfg.get("breakout_buffer_points") or 0)
        ps = float(config.point_size(symbol))
        structure_break_ok = forming.high + 1e-12 >= prior_high + buf * ps
        structure_break_reason = "new_high" if structure_break_ok else "no_new_high"
    else:
        buf = float(cfg.get("breakout_buffer_points") or 0)
        ps = float(config.point_size(symbol))
        structure_break_ok = forming.low - 1e-12 <= prior_low - buf * ps
        structure_break_reason = "new_low" if structure_break_ok else "no_new_low"

    baseline_pct = (
        (baseline_dir_price / forming.open) * 100 if forming.open > 0 else 0.0
    )
    forming_activity_pct = (
        (forming_dir_price / forming.open) * 100 if forming.open > 0 else 0.0
    )

    return {
        "forming_range_pct": round(forming_hl, 4),
        "avg_completed_range_pct": round(avg_hl, 4),
        "range_ratio": round(dir_ratio, 3),
        "directed_side": side,
        "directed_price": round(forming_dir_price, 6),
        "directed_points": round(price_to_points_delta(forming_dir_price, symbol), 1),
        "baseline_directed_price": round(baseline_dir_price, 6),
        "baseline_directed_points": round(
            price_to_points_delta(baseline_dir_price, symbol), 1
        ),
        "directed_ratio": round(dir_ratio, 3),
        "forming_activity_pct": round(forming_activity_pct, 4),
        "baseline_activity_pct": round(baseline_pct, 4),
        "body_price": round(body_price, 6),
        "body_points": round(price_to_points_delta(body_price, symbol), 1),
        "move_vs_open_pct": round(move_vs_open_pct, 4),
        "move_vs_prev_close_pct": round(move_vs_prev_close_pct, 4),
        "completed_count": len(completed),
        "forming_open": forming.open,
        "forming_high": forming.high,
        "forming_low": forming.low,
        "forming_close": forming.close,
        "forming_open_time": forming.open_time.isoformat()
        if getattr(forming, "open_time", None)
        else None,
        "prev_close": prev.close,
        "structure_break_lookback": n_struct,
        "structure_break_ok": structure_break_ok,
        "structure_break_reason": structure_break_reason,
        "prior_structure_high": prior_high,
        "prior_structure_low": prior_low,
        "symbol": symbol,
        "range_variant": "wick",
        "side": side,
        "live_side": side,
    }


def conditions_met(symbol: str, candle_metrics: dict) -> bool:
    """Instant wick-latched range conditions (no hold timer)."""
    cfg = (config.RANGE_WICK_THRESHOLDS or {}).get(symbol) or {}
    mult = float(cfg.get("range_mult", 1.65))

    dir_ratio = float(candle_metrics.get("directed_ratio") or 0)
    dir_pts = float(candle_metrics.get("directed_points") or 0)
    body_pts = float(candle_metrics.get("body_points") or 0)
    min_dir = float(cfg.get("min_directed_points", 300))
    min_body = float(cfg.get("min_body_points", 150))
    side = candle_metrics.get("directed_side") or "UP"
    o = float(candle_metrics["forming_open"])
    c = float(candle_metrics["forming_close"])

    activity = dir_ratio >= mult and dir_pts >= min_dir
    body_ok = body_pts >= min_body
    if side == "UP":
        side_ok = c >= o
    else:
        side_ok = c <= o

    n_struct = int(cfg.get("structure_break_lookback") or 0)
    if n_struct <= 0:
        structure_ok = True
    elif "structure_break_ok" in candle_metrics:
        structure_ok = bool(candle_metrics.get("structure_break_ok"))
    else:
        structure_ok = True

    return activity and body_ok and side_ok and structure_ok
