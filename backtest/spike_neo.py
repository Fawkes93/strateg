"""
Spike Neo — compression → expansion → structure hold (15m forming bar).

Faster, context-aware cousin of classic 1m Spike. Designed for the case where
price coils in a tight, similar-sized range then impulsively breaks structure.

Gates (all required):
  1. Compression — last N completed bars: overall swing tight + similar H−L sizes
  2. Expansion — forming bar range ≥ mult × max(H−L of last M completed)
     Mult can be dynamic from last ~15 bars (softer when coil is quiet/uniform)
  3. Structure hold — live price holds break_min_points beyond prior swing H/L
     of last K completed bars (hold_sec continuous in monitor)

Alert side = direction of structure break (UP / DOWN).
Source id: spike_neo
"""

from __future__ import annotations

from statistics import median
from typing import Any, Dict, List, Optional, Sequence

from backtest import config
from backtest.config import point_size as mt_point_size

ALERT_KIND = "spike_neo"


def _cfg(symbol: str) -> dict:
    return dict((config.SPIKE_NEO_CONFIG or {}).get(symbol) or {})


def _hl_points(candle, ps: float) -> float:
    if candle is None or ps <= 0:
        return 0.0
    return max(0.0, (float(candle.high) - float(candle.low)) / ps)


def _bar_window_stats(bars: Sequence, ps: float) -> Dict[str, float]:
    """Shared swing / size stats for a completed-bar window."""
    if not bars or ps <= 0:
        return {
            "swing_points": 0.0,
            "size_ratio": 0.0,
            "median_hl_points": 0.0,
            "max_hl_points": 0.0,
            "relative_swing": 0.0,
        }
    highs = [float(c.high) for c in bars]
    lows = [float(c.low) for c in bars]
    swing_pts = (max(highs) - min(lows)) / ps
    hls = [_hl_points(c, ps) for c in bars]
    med = float(median(hls)) if hls else 0.0
    mx = max(hls) if hls else 0.0
    if med <= 1e-9:
        size_ratio = 1.0 if mx <= 1e-9 else float("inf")
        relative_swing = 0.0 if swing_pts <= 1e-9 else float("inf")
    else:
        size_ratio = mx / med
        relative_swing = swing_pts / med
    return {
        "swing_points": swing_pts,
        "size_ratio": size_ratio,
        "median_hl_points": med,
        "max_hl_points": mx,
        "relative_swing": relative_swing,
    }


def _compression_ok(
    bars: Sequence,
    ps: float,
    *,
    swing_max_pts: float,
    size_max_ratio: float,
) -> Dict[str, Any]:
    """
    Swing of window (maxH−minL) and size similarity (max HL / median HL).
    """
    st = _bar_window_stats(bars, ps)
    if not bars or ps <= 0:
        return {
            "ok": False,
            "swing_points": 0.0,
            "size_ratio": 0.0,
            "median_hl_points": 0.0,
            "hl_points": [],
        }
    hls = [_hl_points(c, ps) for c in bars]
    size_ratio = st["size_ratio"]
    swing_pts = st["swing_points"]
    swing_ok = swing_pts <= float(swing_max_pts) + 1e-9
    size_ok = size_ratio <= float(size_max_ratio) + 1e-9
    return {
        "ok": swing_ok and size_ok,
        "swing_ok": swing_ok,
        "size_ok": size_ok,
        "swing_points": round(swing_pts, 1),
        "size_ratio": round(size_ratio, 3) if size_ratio != float("inf") else 999.0,
        "median_hl_points": round(st["median_hl_points"], 1),
        "max_hl_points": round(st["max_hl_points"], 1),
        "relative_swing": round(st["relative_swing"], 3)
        if st["relative_swing"] != float("inf")
        else 999.0,
        "hl_points": [round(x, 1) for x in hls],
        "swing_max_points": float(swing_max_pts),
        "size_max_ratio": float(size_max_ratio),
    }


def _clamp01(x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return float(x)


def dynamic_expansion_mult(
    context_bars: Sequence,
    ps: float,
    *,
    mult_min: float,
    mult_max: float,
    tight_relative_swing: float = 3.0,
    loose_relative_swing: float = 10.0,
    size_ratio_soft: float = 1.2,
    size_ratio_hard: float = 2.5,
) -> Dict[str, Any]:
    """
    Map last-N bar behaviour → expansion mult.

    Quiet, uniform coil (low relative swing, similar bar sizes) → mult near min
    (softer / earlier). Choppy or uneven recent bars → mult near max (stricter).

    relative_swing = window_swing_pts / median_bar_HL_pts
    """
    lo = float(mult_min)
    hi = float(mult_max)
    if hi < lo:
        lo, hi = hi, lo
    st = _bar_window_stats(context_bars, ps)
    rel = st["relative_swing"]
    size_r = st["size_ratio"]

    # 0 = tight coil, 1 = loose/choppy
    if rel == float("inf"):
        t_swing = 1.0
    else:
        span = max(1e-9, float(loose_relative_swing) - float(tight_relative_swing))
        t_swing = _clamp01(
            (float(rel) - float(tight_relative_swing)) / span
        )

    if size_r == float("inf"):
        t_size = 1.0
    else:
        span_s = max(1e-9, float(size_ratio_hard) - float(size_ratio_soft))
        t_size = _clamp01((float(size_r) - float(size_ratio_soft)) / span_s)

    # Uneven bars harden a bit even if swing is tight
    t = _clamp01(max(t_swing, 0.5 * t_size))
    mult = lo + t * (hi - lo)
    return {
        "mult": round(mult, 3),
        "t": round(t, 3),
        "t_swing": round(t_swing, 3),
        "t_size": round(t_size, 3),
        "relative_swing": round(rel, 3) if rel != float("inf") else 999.0,
        "size_ratio": round(size_r, 3) if size_r != float("inf") else 999.0,
        "swing_points": round(st["swing_points"], 1),
        "median_hl_points": round(st["median_hl_points"], 1),
        "mult_min": lo,
        "mult_max": hi,
        "context_count": len(context_bars) if context_bars else 0,
    }


def _expansion_ok(
    forming_hl_pts: float,
    recent: Sequence,
    ps: float,
    *,
    mult: float,
) -> Dict[str, Any]:
    """Forming H−L ≥ mult × max(H−L of recent completed)."""
    if not recent or ps <= 0:
        return {
            "ok": False,
            "forming_range_points": round(forming_hl_pts, 1),
            "max_recent_hl_points": 0.0,
            "need_points": 0.0,
            "ratio": 0.0,
            "expansion_mult": float(mult),
        }
    recent_hls = [_hl_points(c, ps) for c in recent]
    max_recent = max(recent_hls) if recent_hls else 0.0
    need = float(mult) * max_recent
    # Flat recent bars: still require some expansion (mult × 0 = 0) — use tiny epsilon
    # so a flat-to-move still needs positive forming range; absolute floor is separate.
    ok = forming_hl_pts + 1e-9 >= need and forming_hl_pts > 0
    ratio = (forming_hl_pts / max_recent) if max_recent > 1e-9 else (
        999.0 if forming_hl_pts > 0 else 0.0
    )
    return {
        "ok": ok,
        "forming_range_points": round(forming_hl_pts, 1),
        "max_recent_hl_points": round(max_recent, 1),
        "need_points": round(need, 1),
        "ratio": round(ratio, 3),
        "expansion_mult": float(mult),
        "recent_hl_points": [round(x, 1) for x in recent_hls],
    }


def evaluate_spike_neo(
    builder: Any,
    current_price: float,
    symbol: str = "XAU/USD",
) -> Optional[Dict[str, Any]]:
    """
    Snapshot for dashboard + conditions.
    Returns None only if builder missing; disabled/waiting are dict states.
    """
    cfg = _cfg(symbol)
    if not cfg.get("enabled", True):
        return {"enabled": False}

    ps = mt_point_size(symbol)
    if ps <= 0:
        return None

    forming = builder.get_current_candle()
    if forming is None:
        return None

    comp_n = int(cfg.get("compression_lookback") or 10)
    exp_n = int(cfg.get("expansion_lookback") or 3)
    struct_n = int(cfg.get("structure_lookback") or 20)
    dyn_on = bool(cfg.get("expansion_dynamic", True))
    ctx_n = int(cfg.get("expansion_context_lookback") or 15)
    need_n = max(comp_n, exp_n, struct_n, ctx_n if dyn_on else 1, 1)

    completed = builder.get_completed_candles(need_n)
    if len(completed) < need_n:
        return {
            "enabled": True,
            "waiting": True,
            "completed_count": len(completed),
            "need_completed": need_n,
        }

    live = float(current_price)
    h = float(forming.high)
    l = float(forming.low)
    o = float(forming.open)
    forming_hl_pts = max(0.0, (h - l) / ps)

    # --- 1) Compression (last comp_n of completed) ---
    comp_bars = completed[-comp_n:]
    compression = _compression_ok(
        comp_bars,
        ps,
        swing_max_pts=float(cfg.get("compression_swing_max_points") or 1200),
        size_max_ratio=float(cfg.get("compression_size_max_ratio") or 2.5),
    )

    # --- 2) Expansion vs last exp_n (mult may be dynamic from last ctx_n) ---
    exp_bars = completed[-exp_n:]
    fixed_mult = float(cfg.get("expansion_mult") or 2.0)
    dyn_blob: Optional[Dict[str, Any]] = None
    if dyn_on:
        ctx_bars = completed[-ctx_n:]
        dyn_blob = dynamic_expansion_mult(
            ctx_bars,
            ps,
            mult_min=float(cfg.get("expansion_mult_min") or 1.5),
            mult_max=float(cfg.get("expansion_mult_max") or 2.5),
            tight_relative_swing=float(
                cfg.get("expansion_tight_relative_swing") or 3.0
            ),
            loose_relative_swing=float(
                cfg.get("expansion_loose_relative_swing") or 10.0
            ),
            size_ratio_soft=float(cfg.get("expansion_size_ratio_soft") or 1.2),
            size_ratio_hard=float(
                cfg.get("expansion_size_ratio_hard")
                or cfg.get("compression_size_max_ratio")
                or 2.5
            ),
        )
        mult = float(dyn_blob["mult"])
    else:
        mult = fixed_mult

    expansion = _expansion_ok(
        forming_hl_pts,
        exp_bars,
        ps,
        mult=mult,
    )
    min_form = float(cfg.get("min_forming_points") or 0)
    expansion_abs_ok = forming_hl_pts + 1e-9 >= min_form if min_form > 0 else True
    expansion["abs_ok"] = expansion_abs_ok
    expansion["min_forming_points"] = min_form
    expansion["dynamic"] = dyn_on
    expansion["fixed_mult"] = fixed_mult
    if dyn_blob is not None:
        expansion["dynamic_detail"] = dyn_blob
    expansion["ok"] = bool(expansion.get("ok")) and expansion_abs_ok

    # --- 3) Structure break + live hold beyond ---
    struct_bars = completed[-struct_n:]
    prior_high = max(float(c.high) for c in struct_bars)
    prior_low = min(float(c.low) for c in struct_bars)
    break_pts = float(cfg.get("break_min_points") or 100)
    break_dist = break_pts * ps

    up_level = prior_high + break_dist
    down_level = prior_low - break_dist
    hold_up = live + 1e-12 >= up_level
    hold_down = live - 1e-12 <= down_level

    # Prefer side with larger excess beyond the break level if both (rare)
    excess_up = (live - up_level) / ps if hold_up else -1.0
    excess_down = (down_level - live) / ps if hold_down else -1.0

    side: Optional[str] = None
    if hold_up and hold_down:
        side = "UP" if excess_up >= excess_down else "DOWN"
    elif hold_up:
        side = "UP"
    elif hold_down:
        side = "DOWN"

    structure_ok = side is not None
    require_body = bool(cfg.get("require_body_direction", True))
    body_ok = True
    if structure_ok and require_body:
        if side == "UP":
            body_ok = live + 1e-12 >= o
        else:
            body_ok = live - 1e-12 <= o

    # Must have actually traded through (wick already beyond structure high/low)
    traded_through = True
    if side == "UP":
        traded_through = h + 1e-12 >= up_level
    elif side == "DOWN":
        traded_through = l - 1e-12 <= down_level

    beyond_pts = 0.0
    if side == "UP":
        beyond_pts = (live - prior_high) / ps
    elif side == "DOWN":
        beyond_pts = (prior_low - live) / ps

    conditions = (
        compression["ok"]
        and expansion["ok"]
        and structure_ok
        and body_ok
        and traded_through
    )

    open_time = getattr(forming, "open_time", None)
    return {
        "enabled": True,
        "waiting": False,
        "source": ALERT_KIND,
        "side": side,
        "directed_side": side,
        "conditions_met": conditions,
        "compression_ok": compression["ok"],
        "expansion_ok": expansion["ok"],
        "structure_ok": structure_ok and traded_through,
        "body_ok": body_ok,
        "require_body_direction": require_body,
        "beyond_points": round(beyond_pts, 1),
        "break_min_points": break_pts,
        "prior_high": prior_high,
        "prior_low": prior_low,
        "up_level": up_level,
        "down_level": down_level,
        "compression": compression,
        "expansion": expansion,
        "compression_lookback": comp_n,
        "expansion_lookback": exp_n,
        "structure_lookback": struct_n,
        "completed_count": len(completed),
        "forming_open": o,
        "forming_high": h,
        "forming_low": l,
        "forming_close": live,
        "forming_open_time": open_time.isoformat() if open_time is not None else None,
        "forming_range_points": round(forming_hl_pts, 1),
        "price": live,
        "hold_sec": float(cfg.get("hold_sec") or 0),
        "cooldown_min": float(cfg.get("cooldown_min") or 45),
        "levels": {
            "prior_high": round(prior_high, 6),
            "prior_low": round(prior_low, 6),
            "up_level": round(up_level, 6),
            "down_level": round(down_level, 6),
            "compression_high": round(max(float(c.high) for c in comp_bars), 6),
            "compression_low": round(min(float(c.low) for c in comp_bars), 6),
        },
    }


def conditions_met(snapshot: Optional[dict]) -> bool:
    if not snapshot or not snapshot.get("enabled", True):
        return False
    if snapshot.get("waiting"):
        return False
    return bool(snapshot.get("conditions_met"))
