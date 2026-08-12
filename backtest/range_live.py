"""
Live range-expansion signal (standalone copy of Reaktor range_expansion).

Hold timer is applied by the replay engine using simulated tick time.
Hot path is optimized for multi-million tick replays.
"""

from __future__ import annotations

from statistics import mean, median
from typing import Any, Dict, Optional, Tuple

from backtest import config
from backtest.config import point_size as mt_point_size


def candle_range_pct(candle) -> float:
    if candle is None or candle.open <= 0:
        return 0.0
    return ((candle.high - candle.low) / candle.open) * 100


def directed_excursion_price(candle) -> float:
    if candle is None:
        return 0.0
    up = candle.high - candle.open
    down = candle.open - candle.low
    return max(up, down, 0.0)


def directed_side(candle) -> str:
    if candle is None:
        return "UP"
    up = candle.high - candle.open
    down = candle.open - candle.low
    if up > down:
        return "UP"
    if down > up:
        return "DOWN"
    if candle.close >= candle.open:
        return "UP"
    return "DOWN"


def price_to_points_delta(delta: float, symbol: str) -> float:
    ps = mt_point_size(symbol)
    if ps <= 0:
        return 0.0
    return delta / ps


class RangeBaselineCache:
    """
    Completed-bar stats change only when a candle closes.
    Cache baseline + structure so each live tick is O(1).
    """

    __slots__ = ("_key", "baseline_dir_price", "avg_hl", "prior_high", "prior_low",
                 "history_ok", "history_required", "prev_close", "n_completed")

    def __init__(self) -> None:
        self._key: Optional[Tuple] = None
        self.baseline_dir_price = 0.0
        self.avg_hl = 0.0
        self.prior_high: Optional[float] = None
        self.prior_low: Optional[float] = None
        self.history_ok = False
        self.history_required = 1
        self.prev_close = 0.0
        self.n_completed = 0

    def update(self, builder: Any, lookback: int, n_struct: int) -> None:
        completed = builder.completed_candles
        n = len(completed)
        # Key: length + last open_time (identity of newest closed bar)
        last_ot = completed[-1].open_time if n else None
        key = (n, last_ot, lookback, n_struct)
        if key == self._key:
            return
        self._key = key
        self.n_completed = n
        if n < 1:
            self.history_ok = False
            return

        recent = completed[-lookback:] if lookback > 0 else completed
        required = max(lookback, n_struct) if n_struct > 0 else max(lookback, 1)
        self.history_required = required
        self.history_ok = n >= required

        hl_ranges = [candle_range_pct(c) for c in recent]
        self.avg_hl = mean(hl_ranges) if hl_ranges else 0.0
        dir_prices = [directed_excursion_price(c) for c in recent]
        self.baseline_dir_price = median(dir_prices) if dir_prices else 0.0
        self.prev_close = float(completed[-1].close)

        if n_struct > 0:
            struct_bars = completed[-n_struct:]
            if len(struct_bars) >= n_struct:
                self.prior_high = max(b.high for b in struct_bars)
                self.prior_low = min(b.low for b in struct_bars)
            else:
                self.prior_high = None
                self.prior_low = None
        else:
            self.prior_high = None
            self.prior_low = None


def calculate_candle_metrics(
    builder: Any,
    current_price: float,
    lookback: int = None,
    symbol: str = "XAU/USD",
    *,
    cache: Optional[RangeBaselineCache] = None,
) -> Optional[dict]:
    cfg = config.THRESHOLDS.get(symbol) or {}
    if lookback is None:
        lookback = int(cfg.get("lookback") or config.CANDLE_LOOKBACK)

    forming = builder.get_current_candle()
    if forming is None or forming.open <= 0:
        return None

    n_struct = int(cfg.get("structure_break_lookback") or 0)
    if cache is None:
        cache = RangeBaselineCache()
    cache.update(builder, lookback, n_struct)

    if cache.n_completed < 1:
        return None

    baseline_dir_price = cache.baseline_dir_price
    history_ok = cache.history_ok
    required = cache.history_required
    prior_high = cache.prior_high
    prior_low = cache.prior_low
    avg_hl = cache.avg_hl
    prev_close = cache.prev_close

    forming_hl = candle_range_pct(forming)
    wick_dir_price = directed_excursion_price(forming)
    wick_side = directed_side(forming)
    wick_ratio = (
        (wick_dir_price / baseline_dir_price) if baseline_dir_price > 0 else 0.0
    )

    live = float(current_price)
    o = float(forming.open)
    signed = live - o
    if signed > 0:
        live_side = "UP"
    elif signed < 0:
        live_side = "DOWN"
    else:
        live_side = "UP" if forming.close >= o else "DOWN"

    live_move_price = abs(signed)
    live_ratio = (
        (live_move_price / baseline_dir_price) if baseline_dir_price > 0 else 0.0
    )
    live_pts = price_to_points_delta(live_move_price, symbol)
    body_pts = live_pts

    mult = float(cfg.get("range_mult", 1.65))
    min_dir_pts = float(cfg.get("min_directed_points", 300))
    ps = mt_point_size(symbol)
    min_dir_price = min_dir_pts * ps if ps > 0 else 0.0
    target_price = max(baseline_dir_price * mult, min_dir_price)

    buffer_pts = float(cfg.get("breakout_buffer_points") or 0)
    buffer_price = buffer_pts * ps if ps > 0 else 0.0

    if n_struct <= 0:
        structure_break_ok = True
        structure_break_reason = "off"
    elif prior_high is None or prior_low is None:
        structure_break_ok = False
        structure_break_reason = "insufficient_history"
    elif live_side == "UP":
        structure_break_ok = live >= prior_high + buffer_price
        structure_break_reason = (
            "live_above_prior_high" if structure_break_ok else "no_live_structure"
        )
    else:
        structure_break_ok = live <= prior_low - buffer_price
        structure_break_reason = (
            "live_below_prior_low" if structure_break_ok else "no_live_structure"
        )

    return {
        "forming_range_pct": round(forming_hl, 4),
        "avg_completed_range_pct": round(avg_hl, 4),
        "range_ratio": round(live_ratio, 3),
        "directed_side": live_side,
        "directed_points": round(live_pts, 1),
        "baseline_directed_points": round(
            price_to_points_delta(baseline_dir_price, symbol), 1
        ),
        "directed_ratio": round(live_ratio, 3),
        "body_points": round(body_pts, 1),
        "completed_count": cache.n_completed,
        "forming_open": o,
        "forming_high": forming.high,
        "forming_low": forming.low,
        "forming_close": live,
        "forming_open_time": forming.open_time.isoformat()
        if getattr(forming, "open_time", None)
        else None,
        "prev_close": prev_close,
        "structure_break_lookback": n_struct,
        "structure_break_ok": structure_break_ok,
        "structure_break_reason": structure_break_reason,
        "prior_structure_high": prior_high,
        "prior_structure_low": prior_low,
        "symbol": symbol,
        "live_side": live_side,
        "live_move_price": live_move_price,
        "live_ratio": live_ratio,
        "live_points": live_pts,
        "live_body_points": body_pts,
        "target_price": target_price,
        "target_points": price_to_points_delta(target_price, symbol),
        "baseline_dir_price_raw": baseline_dir_price,
        "history_ok": history_ok,
        "history_required": required,
        "breakout_buffer_points": buffer_pts,
        "wick_side": wick_side,
        "wick_directed_points": price_to_points_delta(wick_dir_price, symbol),
        "wick_ratio": wick_ratio,
    }


def conditions_met(symbol: str, candle_metrics: dict) -> bool:
    cfg = config.THRESHOLDS.get(symbol) or {}
    if not cfg:
        return False
    if not candle_metrics.get("history_ok", True):
        return False

    mult = float(cfg.get("range_mult", 1.65))
    min_dir = float(cfg.get("min_directed_points", 300))
    min_body = float(cfg.get("min_body_points", 150))

    live_ratio = float(
        candle_metrics["live_ratio"]
        if "live_ratio" in candle_metrics
        else candle_metrics.get("directed_ratio") or 0
    )
    live_pts = float(
        candle_metrics["live_points"]
        if "live_points" in candle_metrics
        else candle_metrics.get("directed_points") or 0
    )
    body_pts = float(
        candle_metrics["live_body_points"]
        if "live_body_points" in candle_metrics
        else candle_metrics.get("body_points") or 0
    )
    side = (
        candle_metrics.get("live_side")
        or candle_metrics.get("directed_side")
        or "UP"
    )
    o = float(candle_metrics["forming_open"])
    c = float(candle_metrics["forming_close"])

    activity = live_ratio >= mult and live_pts >= min_dir
    body_ok = body_pts >= min_body
    side_ok = c > o if side == "UP" else c < o

    n_struct = int(cfg.get("structure_break_lookback") or 0)
    if n_struct <= 0:
        structure_ok = True
    elif "structure_break_ok" not in candle_metrics:
        structure_ok = False
    else:
        structure_ok = bool(candle_metrics.get("structure_break_ok"))

    return activity and body_ok and side_ok and structure_ok
