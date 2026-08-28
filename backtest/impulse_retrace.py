"""
Impulse retrace — after a directional blast, alert on pullback depth.

Pattern:
  1. Quiet-or-any window produces a large directed swing (impulse)
  2. Price pulls back from the extreme toward the base
  3. Fire when retrace depth reaches configured fractions (e.g. 50%, 75%)
  4. Only if that level is reached within max_retrace_age_sec of the blast extreme
  5. Bias = direction of the blast (continuation entry)

UP:  base=swing low, extreme=swing high
     depth = (extreme − live) / (extreme − base)
DOWN: base=swing high, extreme=swing low
     depth = (live − extreme) / (base − extreme)

Source id: impulse_retrace

Age clock: replay/monitor stamps extreme_seen_at when impulse_key is first seen
or the extreme extends; evaluate rejects fires once (now − extreme_seen_at)
exceeds max_retrace_age_sec (default 120s).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from backtest import config
from backtest.config import point_size as mt_point_size

ALERT_KIND = "impulse_retrace"


def _cfg(symbol: str) -> dict:
    return dict((config.IMPULSE_RETRACE_CONFIG or {}).get(symbol) or {})


def _fractions(cfg: dict) -> List[float]:
    raw = cfg.get("retrace_fractions") or [0.50, 0.75]
    out: List[float] = []
    for x in raw:
        try:
            f = float(x)
        except (TypeError, ValueError):
            continue
        if 0.0 < f < 1.0:
            out.append(f)
    return sorted(set(out)) or [0.50, 0.75]


def _level_for_fraction(
    side: str, base: float, extreme: float, frac: float
) -> float:
    """Price level at `frac` retrace from extreme toward base."""
    r = abs(extreme - base)
    if side == "UP":
        return extreme - frac * r
    return extreme + frac * r  # DOWN: extreme is low, base is high


def _window_candles(builder: Any, max_bars: int) -> List[Any]:
    """Completed last max_bars + forming (if any), chronological."""
    completed = list(builder.get_completed_candles(max_bars) or [])
    forming = builder.get_current_candle()
    out = completed[-max_bars:] if completed else []
    if forming is not None:
        out = out + [forming]
    return out


def _find_impulse(
    candles: Sequence,
    ps: float,
    *,
    min_impulse_points: float,
    extreme_must_be_recent_bars: int,
) -> Optional[Dict[str, Any]]:
    """
    Dominant swing in window: low then high → UP; high then low → DOWN.
    Extreme must fall in the last `extreme_must_be_recent_bars` candles
    so we don't arm on an old blast mid-range.
    """
    if not candles or ps <= 0 or len(candles) < 2:
        return None

    lows = [float(c.low) for c in candles]
    highs = [float(c.high) for c in candles]
    i_lo = min(range(len(candles)), key=lambda i: lows[i])
    i_hi = max(range(len(candles)), key=lambda i: highs[i])
    lo = lows[i_lo]
    hi = highs[i_hi]
    rng_pts = (hi - lo) / ps
    if rng_pts + 1e-9 < float(min_impulse_points):
        return None

    n = len(candles)
    recent_from = max(0, n - max(1, int(extreme_must_be_recent_bars)))

    if i_hi > i_lo:
        # UP impulse: low first, then high
        if i_hi < recent_from:
            return None
        side = "UP"
        base, extreme = lo, hi
        base_i, extreme_i = i_lo, i_hi
    elif i_lo > i_hi:
        if i_lo < recent_from:
            return None
        side = "DOWN"
        base, extreme = hi, lo  # base = swing high, extreme = swing low
        base_i, extreme_i = i_hi, i_lo
    else:
        # Same bar holds both extremes (one fat impulse candle).
        # Side from that bar's body: close ≥ open → UP blast, else DOWN.
        if i_hi < recent_from:
            return None
        bar = candles[i_hi]
        o = float(getattr(bar, "open", lo))
        c = float(getattr(bar, "close", hi))
        if c + 1e-12 >= o:
            side = "UP"
            base, extreme = lo, hi
        else:
            side = "DOWN"
            base, extreme = hi, lo
        base_i = extreme_i = i_hi

    return {
        "side": side,
        "base": base,
        "extreme": extreme,
        "range_points": rng_pts,
        "base_index": base_i,
        "extreme_index": extreme_i,
        "window_count": n,
    }


def _quiet_ok(
    candles: Sequence,
    impulse: dict,
    ps: float,
    *,
    lookback: int,
    swing_max_points: float,
) -> Tuple[bool, Dict[str, Any]]:
    """Optional: bars *before* impulse extreme should be a tight swing."""
    ei = int(impulse.get("extreme_index") or 0)
    # Quiet window: up to `lookback` bars ending just before extreme bar
    end = max(0, ei)
    start = max(0, end - int(lookback))
    prior = list(candles[start:end])
    if len(prior) < 3:
        return True, {"ok": True, "skipped": True, "reason": "short_history"}
    ph = max(float(c.high) for c in prior)
    pl = min(float(c.low) for c in prior)
    swing_pts = (ph - pl) / ps if ps > 0 else 0.0
    ok = swing_pts <= float(swing_max_points) + 1e-9
    return ok, {
        "ok": ok,
        "skipped": False,
        "swing_points": round(swing_pts, 1),
        "swing_max_points": float(swing_max_points),
        "bar_count": len(prior),
    }


def evaluate_impulse_retrace(
    builder: Any,
    current_price: float,
    symbol: str = "XAU/USD",
    *,
    alerted_fractions: Optional[Set[float]] = None,
    extreme_seen_at: Optional[float] = None,
    now: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """
    Snapshot for dashboard + conditions.
    `alerted_fractions` = levels already fired for the current impulse (monitor).
    `extreme_seen_at` = epoch when this impulse extreme was stamped (replay clock).
    `now` = epoch for age gate (defaults to time.time()).
    """
    cfg = _cfg(symbol)
    if not cfg.get("enabled", True):
        return {"enabled": False}

    ps = mt_point_size(symbol)
    if ps <= 0:
        return None

    max_bars = int(cfg.get("impulse_lookback") or 16)
    min_imp = float(cfg.get("min_impulse_points") or 500)
    extreme_recent = int(cfg.get("extreme_recent_bars") or 4)
    fracs = _fractions(cfg)
    alerted = set(alerted_fractions or [])
    max_age = float(cfg.get("max_retrace_age_sec") or 0)
    now_ts = float(now) if now is not None else time.time()

    forming = builder.get_current_candle()
    if forming is None:
        return None

    candles = _window_candles(builder, max_bars)
    if len(candles) < 3:
        return {
            "enabled": True,
            "waiting": True,
            "completed_count": len(candles),
            "need_completed": 3,
        }

    imp = _find_impulse(
        candles,
        ps,
        min_impulse_points=min_imp,
        extreme_must_be_recent_bars=extreme_recent,
    )
    if imp is None:
        return {
            "enabled": True,
            "waiting": False,
            "idle": True,
            "impulse_ok": False,
            "conditions_met": False,
            "side": None,
            "message": "no_impulse",
            "min_impulse_points": min_imp,
            "retrace_fractions": fracs,
            "max_retrace_age_sec": max_age,
            "max_retrace_depth": float(cfg.get("max_retrace_depth") or 0.85),
            "forming_open_time": (
                forming.open_time.isoformat()
                if getattr(forming, "open_time", None) is not None
                else None
            ),
            "price": float(current_price),
            "hold_sec": float(cfg.get("hold_sec") or 0),
            "cooldown_min": float(cfg.get("cooldown_min") or 45),
            "levels": {},
        }

    side = imp["side"]
    base = float(imp["base"])
    extreme = float(imp["extreme"])
    r_price = abs(extreme - base)
    r_pts = r_price / ps
    live = float(current_price)

    quiet_blob: Dict[str, Any] = {"ok": True, "skipped": True}
    if bool(cfg.get("require_quiet", False)):
        q_ok, quiet_blob = _quiet_ok(
            candles,
            imp,
            ps,
            lookback=int(cfg.get("quiet_lookback") or 10),
            swing_max_points=float(cfg.get("quiet_swing_max_points") or 1200),
        )
        if not q_ok:
            return {
                "enabled": True,
                "waiting": False,
                "idle": True,
                "impulse_ok": False,
                "quiet_ok": False,
                "quiet": quiet_blob,
                "conditions_met": False,
                "side": side,
                "base": base,
                "extreme": extreme,
                "range_points": round(r_pts, 1),
                "message": "quiet_fail",
                "price": live,
                "hold_sec": float(cfg.get("hold_sec") or 0),
                "cooldown_min": float(cfg.get("cooldown_min") or 45),
                "levels": {},
            }

    # Retrace depth 0 = at extreme, 1 = fully back to base
    if side == "UP":
        if r_price <= 1e-12:
            depth = 0.0
        else:
            depth = (extreme - live) / r_price
        # Still above base; below extreme for a real pullback
        invalidated = live <= base + 1e-12
        pullback_started = live < extreme - 1e-12
    else:
        if r_price <= 1e-12:
            depth = 0.0
        else:
            depth = (live - extreme) / r_price
        invalidated = live >= base - 1e-12
        pullback_started = live > extreme + 1e-12

    depth = max(0.0, depth)

    # Levels map fraction → price
    level_map = {f: _level_for_fraction(side, base, extreme, f) for f in fracs}

    # Active fraction: deepest fraction whose threshold is reached, not yet alerted
    # Prefer firing the *next* unmet fraction (lowest f with depth >= f)
    active_frac: Optional[float] = None
    for f in fracs:
        if f in alerted:
            continue
        if depth + 1e-12 >= f:
            active_frac = f
            break  # fire shallowest unmet first (50 before 75)

    # Optional: only alert if not past "too deep" (default 0.85)
    max_depth = float(cfg.get("max_retrace_depth") or 0.85)
    depth_ok = depth <= max_depth + 1e-12

    min_pull_pts = float(cfg.get("min_pullback_points") or 0)
    if min_pull_pts > 0 and pullback_started:
        if side == "UP":
            pull_pts = (extreme - live) / ps
        else:
            pull_pts = (live - extreme) / ps
        pullback_enough = pull_pts + 1e-9 >= min_pull_pts
    else:
        pullback_enough = pullback_started

    # Age gate: level must be reached soon after the blast extreme was stamped.
    # max_retrace_age_sec <= 0 disables. Missing clock → fail closed when gate on.
    age_sec: Optional[float] = None
    if max_age > 0:
        if extreme_seen_at is None:
            age_ok = False
        else:
            age_sec = max(0.0, now_ts - float(extreme_seen_at))
            age_ok = age_sec <= max_age + 1e-9
    else:
        age_ok = True

    conditions = (
        not invalidated
        and pullback_enough
        and depth_ok
        and age_ok
        and active_frac is not None
        and bool(cfg.get("enabled", True))
    )

    # Impulse key in integer MT points (not price decimals).
    # round(extreme, 2) is fine for XAU ($0.01) but is 100 pips on EURUSD,
    # so the age clock never reset and max_retrace_age_sec killed every fire.
    scale = ps if ps > 0 else 1e-5
    impulse_key = (
        side,
        int(round(base / scale)),
        int(round(extreme / scale)),
    )

    open_time = getattr(forming, "open_time", None)
    return {
        "enabled": True,
        "waiting": False,
        "idle": False,
        "source": ALERT_KIND,
        "side": side,
        "directed_side": side,
        "impulse_ok": True,
        "quiet_ok": quiet_blob.get("ok", True),
        "quiet": quiet_blob,
        "base": base,
        "extreme": extreme,
        "range_points": round(r_pts, 1),
        "range_price": round(r_price, 6),
        "retrace_depth": round(depth, 4),
        "retrace_pct": round(depth * 100, 1),
        "active_fraction": active_frac,
        "active_level": (
            level_map[active_frac] if active_frac is not None else None
        ),
        "alerted_fractions": sorted(alerted),
        "retrace_fractions": fracs,
        "level_map": {str(f): round(level_map[f], 6) for f in fracs},
        "pullback_started": pullback_started,
        "invalidated": invalidated,
        "depth_ok": depth_ok,
        "max_retrace_depth": max_depth,
        "age_ok": age_ok,
        "extreme_age_sec": (
            round(age_sec, 1) if age_sec is not None else None
        ),
        "extreme_seen_at": extreme_seen_at,
        "max_retrace_age_sec": max_age,
        "conditions_met": conditions,
        "impulse_key": impulse_key,
        "min_impulse_points": min_imp,
        "impulse_lookback": max_bars,
        "forming_open": float(forming.open),
        "forming_high": float(forming.high),
        "forming_low": float(forming.low),
        "forming_close": live,
        "forming_open_time": (
            open_time.isoformat() if open_time is not None else None
        ),
        "price": live,
        "hold_sec": float(cfg.get("hold_sec") or 0),
        "cooldown_min": float(cfg.get("cooldown_min") or 45),
        "levels": {
            "base": round(base, 6),
            "extreme": round(extreme, 6),
            **{f"retrace_{int(f * 100)}": round(level_map[f], 6) for f in fracs},
        },
    }


def conditions_met(snapshot: Optional[dict]) -> bool:
    if not snapshot or not snapshot.get("enabled", True):
        return False
    if snapshot.get("waiting") or snapshot.get("idle"):
        return False
    return bool(snapshot.get("conditions_met"))
