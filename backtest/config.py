"""
Signal thresholds for offline backtest.

Defaults from Reaktor `reaktor/config.py` (live range + spike + filters).
Jobs may override in-process without touching the live bot.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Global / session filters
# ---------------------------------------------------------------------------

DISPLAY_TZ = "Europe/Bucharest"
CANDLE_TIMEFRAME_MIN = 15
CANDLE_LOOKBACK = 30

# Skip 15m bars whose open is in local hour window (DISPLAY_TZ)
CANDLE_IGNORE = {
    "enabled": True,
    "local_hour_start": 0,
    "local_hour_end": 1,
}

# Forex/gold session UTC (Reaktor is_market_open)
FOREX_OPEN_SUNDAY_UTC_HOUR = 22
FOREX_CLOSE_FRIDAY_UTC_HOUR = 22

# Market-open blackout — from Factor (factor/rules/filter.py + config).
# Ignore alerts in the first N minutes after local open. Default: Monday only,
# ~01:05 Europe/Bucharest (XAU weekly reopen), 15 minutes.
MARKET_OPEN_BLACKOUT = {
    "enabled": True,
    "open_time": "01:05",  # HH:MM in open_tz
    "open_tz": "Europe/Bucharest",
    "minutes": 15,
    "weekdays": [0],  # 0=Mon … 6=Sun; empty = every day
}

# ---------------------------------------------------------------------------
# Factory defaults (immutable templates)
# ---------------------------------------------------------------------------

DEFAULT_RANGE_XAU = {
    "range_mult": 1.8,
    "min_directed_points": 500,
    "min_body_points": 280,
    "hold_sec": 30,
    "structure_break_lookback": 10,
    "breakout_buffer_points": 0,
    "cooldown_min": 60,
    "lookback": 30,
}

DEFAULT_SPIKE_XAU = {
    "enabled": True,
    "point_size": 0.01,
    "min_points": 650,
    "window_sec": 60,
    "cooldown_min": 60,
    "relative_enabled": True,
    "relative_lookback": 2,
    "relative_mult": 2.0,
}

# Spike Neo — compression → expansion → structure (Reaktor SPIKE_NEO_CONFIG)
DEFAULT_SPIKE_NEO_XAU = {
    "enabled": True,
    "compression_lookback": 10,
    "compression_swing_max_points": 1200,
    "compression_size_max_ratio": 2.5,
    "expansion_lookback": 3,
    "expansion_mult": 2.0,
    "expansion_dynamic": True,
    "expansion_context_lookback": 15,
    "expansion_mult_min": 1.5,
    "expansion_mult_max": 2.5,
    "expansion_tight_relative_swing": 3.0,
    "expansion_loose_relative_swing": 10.0,
    "min_forming_points": 200,
    "structure_lookback": 20,
    "break_min_points": 100,
    "hold_sec": 2,
    "cooldown_min": 45,
    "require_body_direction": True,
}

DEFAULT_SPIKE_NEO_EUR = {
    "enabled": True,
    "compression_lookback": 10,
    "compression_swing_max_points": 80,
    "compression_size_max_ratio": 2.5,
    "expansion_lookback": 3,
    "expansion_mult": 2.0,
    "expansion_dynamic": True,
    "expansion_context_lookback": 15,
    "expansion_mult_min": 1.5,
    "expansion_mult_max": 2.5,
    "expansion_tight_relative_swing": 3.0,
    "expansion_loose_relative_swing": 10.0,
    "min_forming_points": 25,
    "structure_lookback": 20,
    "break_min_points": 15,
    "hold_sec": 2,
    "cooldown_min": 45,
    "require_body_direction": True,
}

# Impulse retrace — after blast, fire at pullback fractions (continuation bias)
DEFAULT_IMPULSE_RETRACE_XAU = {
    "enabled": True,
    "impulse_lookback": 16,
    "min_impulse_points": 500,
    "extreme_recent_bars": 4,
    "retrace_fractions": [0.50, 0.75],
    "min_pullback_points": 30,
    "max_retrace_depth": 0.85,  # no alert if pullback deeper than this
    # Fire only if a level is reached within this many seconds of the blast
    # extreme (clock starts / resets when impulse_key first seen or extreme extends).
    "max_retrace_age_sec": 120,  # 2 minutes
    "hold_sec": 2,
    "cooldown_min": 30,
    "require_quiet": False,
    "quiet_lookback": 10,
    "quiet_swing_max_points": 1200,
}

DEFAULT_IMPULSE_RETRACE_EUR = {
    "enabled": True,
    "impulse_lookback": 16,
    "min_impulse_points": 50,
    "extreme_recent_bars": 4,
    "retrace_fractions": [0.50, 0.75],
    "min_pullback_points": 5,
    "max_retrace_depth": 0.85,
    "max_retrace_age_sec": 120,
    "hold_sec": 2,
    "cooldown_min": 30,
    "require_quiet": False,
    "quiet_lookback": 10,
    "quiet_swing_max_points": 80,
}

# Legacy range wick (candle_wick) — directed via forming H/L, independent of live range
DEFAULT_RANGE_WICK_XAU = {
    "range_mult": 2.0,
    "min_directed_points": 500,
    "min_body_points": 280,
    "hold_sec": 30,
    "structure_break_lookback": 10,
    "breakout_buffer_points": 0,
    "cooldown_min": 60,
    "lookback": 30,
}

DEFAULT_RANGE_WICK_EUR = {
    "range_mult": 1.5,
    "min_directed_points": 55,
    "min_body_points": 35,
    "hold_sec": 30,
    "structure_break_lookback": 10,
    "breakout_buffer_points": 0,
    "cooldown_min": 60,
    "lookback": 30,
}

DEFAULT_RANGE_EUR = {
    "range_mult": 1.5,
    "min_directed_points": 55,
    "min_body_points": 35,
    "hold_sec": 30,
    "structure_break_lookback": 10,
    "breakout_buffer_points": 0,
    "cooldown_min": 60,
    "lookback": 30,
}

DEFAULT_SPIKE_EUR = {
    "enabled": True,
    "point_size": 0.00001,
    "min_points": 55,
    "window_sec": 60,
    "cooldown_min": 60,
    "relative_enabled": True,
    "relative_lookback": 3,
    "relative_mult": 2.0,
}

THRESHOLDS: Dict[str, dict] = {
    "XAU/USD": copy.deepcopy(DEFAULT_RANGE_XAU),
    "EUR/USD": copy.deepcopy(DEFAULT_RANGE_EUR),
}

SPIKE_CONFIG: Dict[str, dict] = {
    "XAU/USD": copy.deepcopy(DEFAULT_SPIKE_XAU),
    "EUR/USD": copy.deepcopy(DEFAULT_SPIKE_EUR),
}

SPIKE_NEO_CONFIG: Dict[str, dict] = {
    "XAU/USD": copy.deepcopy(DEFAULT_SPIKE_NEO_XAU),
    "EUR/USD": copy.deepcopy(DEFAULT_SPIKE_NEO_EUR),
}

IMPULSE_RETRACE_CONFIG: Dict[str, dict] = {
    "XAU/USD": copy.deepcopy(DEFAULT_IMPULSE_RETRACE_XAU),
    "EUR/USD": copy.deepcopy(DEFAULT_IMPULSE_RETRACE_EUR),
}

RANGE_WICK_THRESHOLDS: Dict[str, dict] = {
    "XAU/USD": copy.deepcopy(DEFAULT_RANGE_WICK_XAU),
    "EUR/USD": copy.deepcopy(DEFAULT_RANGE_WICK_EUR),
}


def point_size(symbol: str) -> float:
    cfg = SPIKE_CONFIG.get(symbol) or {}
    if cfg.get("point_size"):
        return float(cfg["point_size"])
    if "XAU" in symbol or "GOLD" in symbol:
        return 0.01
    if "BTC" in symbol:
        # Same as XAU: 1 pt = $0.01. A $100 BTC rip = 10_000 pts.
        return 0.01
    return 0.00001


def _base_for_symbol(symbol: str):
    if "EUR" in symbol:
        return (
            copy.deepcopy(DEFAULT_RANGE_EUR),
            copy.deepcopy(DEFAULT_SPIKE_EUR),
            copy.deepcopy(DEFAULT_SPIKE_NEO_EUR),
            copy.deepcopy(DEFAULT_IMPULSE_RETRACE_EUR),
            copy.deepcopy(DEFAULT_RANGE_WICK_EUR),
        )
    return (
        copy.deepcopy(DEFAULT_RANGE_XAU),
        copy.deepcopy(DEFAULT_SPIKE_XAU),
        copy.deepcopy(DEFAULT_SPIKE_NEO_XAU),
        copy.deepcopy(DEFAULT_IMPULSE_RETRACE_XAU),
        copy.deepcopy(DEFAULT_RANGE_WICK_XAU),
    )


def defaults_snapshot(symbol: str = "XAU/USD") -> Dict[str, Any]:
    """JSON-friendly defaults + docs for the UI."""
    r, s, n, ir, rw = _base_for_symbol(symbol)
    return {
        "symbol": symbol,
        "docs": {
            "range": {
                "range_mult": "Live directed move from open ≥ mult × median one-sided completed-bar excursion",
                "min_directed_points": "Absolute directed-move floor (MT points; XAU 1pt = $0.01)",
                "min_body_points": "Absolute |live − open| floor",
                "hold_sec": "Seconds conditions must stay true before fire",
                "structure_break_lookback": "Break high/low of last N completed 15m bars",
                "breakout_buffer_points": "Extra points beyond structure high/low",
                "cooldown_min": "Minutes before another range alert (same symbol)",
                "lookback": "Completed 15m bars for median baseline / history gate",
            },
            "spike": {
                "enabled": "Master switch",
                "min_points": "Absolute MT-point floor in the rolling window",
                "window_sec": "Rolling window length (seconds)",
                "cooldown_min": "Minutes before another spike",
                "relative_enabled": "effective = max(min_points, relative_mult × median H−L of last N completed 15m bars)",
                "relative_lookback": "N = last N fully closed 15m candles only (not forming bar); XAU default 2",
                "relative_mult": "× median H−L of those last N closed 15m bars; spike needs max(min_points, that)",
                "point_size": "Price per MT point (XAU 0.01)",
            },
            "spike_neo": {
                "enabled": "Master switch for Spike Neo",
                "compression_lookback": "Last N completed 15m bars for coil check",
                "compression_swing_max_points": "Max overall swing (pts) of the coil window",
                "compression_size_max_ratio": "max(bar HL) / median(bar HL) — similar sizes",
                "expansion_lookback": "Recent bars whose max HL sets expansion need",
                "expansion_mult": "Fixed mult if expansion_dynamic is off",
                "expansion_dynamic": "Soft/hard mult from recent context (quiet coil → softer)",
                "expansion_context_lookback": "Bars driving dynamic mult",
                "expansion_mult_min": "Softest expansion mult (quiet coil)",
                "expansion_mult_max": "Strictest expansion mult (choppy)",
                "min_forming_points": "Absolute floor on forming bar H−L",
                "structure_lookback": "Prior high/low from last K completed bars",
                "break_min_points": "Points beyond prior high/low to count as break",
                "hold_sec": "Seconds live must hold beyond structure",
                "cooldown_min": "Minutes between Spike Neo alerts",
                "require_body_direction": "Live must be on correct side of bar open",
            },
            "impulse_retrace": {
                "enabled": "Master switch for Impulse Retrace",
                "impulse_lookback": "Bars (completed+forming) to find the blast swing",
                "min_impulse_points": "Minimum H−L of the impulse leg (pts)",
                "extreme_recent_bars": "Extreme must fall in last N bars of the window",
                "retrace_fractions": "Pullback depths to alert (e.g. 0.5, 0.75)",
                "min_pullback_points": "Ignore micro noise off the extreme",
                "max_retrace_depth": "No alert if pullback deeper than this fraction (default 0.85)",
                "max_retrace_age_sec": "Pullback must hit a level within this many seconds of the blast extreme (0=off)",
                "hold_sec": "Seconds at the retrace level before fire",
                "cooldown_min": "Minutes between any impulse-retrace alerts",
                "require_quiet": "Optional: pre-blast window must be a tight coil",
                "quiet_lookback": "Bars before extreme for quiet check",
                "quiet_swing_max_points": "Max pre-blast swing if require_quiet",
            },
            "range_wick": {
                "range_mult": "Wick range: directed wick excursion ≥ mult × median completed",
                "min_directed_points": "Wick: absolute directed floor (uses forming H/L)",
                "min_body_points": "Wick: |close−open| floor on forming bar",
                "hold_sec": "Wick: seconds conditions stay true before fire",
                "structure_break_lookback": "Wick: break prior high/low of last N completed",
                "breakout_buffer_points": "Wick: extra pts beyond structure",
                "cooldown_min": "Wick: minutes between candle_wick alerts",
                "lookback": "Wick: completed bars for median baseline",
            },
            "filters": {
                "candle_ignore": "Skip 15m bars whose open is in local hour window (DISPLAY_TZ)",
                "market_open_blackout": "Factor rule: skip alerts for N min after local open (default Mon 01:05 Bucharest)",
                "market_hours": "No processing when forex closed (weekend)",
            },
            "suggestions": [
                "Lower min_directed / min_body → more range alerts",
                "Raise range_mult or structure lookback → fewer, stronger moves",
                "Shorter hold_sec → earlier fires, more noise",
                "Spike: raise min_points or relative_mult to cut thin spikes",
                "Spike Neo: raise compression_swing_max or lower expansion_mult_min for more coils",
                "Impulse retrace: lower min_impulse_points or add more retrace_fractions for more signals",
                "Range wick: older wick-latched range (A/B vs live range); higher mult = fewer",
                "Market-open blackout 15–30m for Monday reopen (matches Factor)",
                "candle_ignore 0–1 local keeps Asia open quiet",
            ],
        },
        "range": r,
        "spike": s,
        "spike_neo": n,
        "impulse_retrace": ir,
        "range_wick": rw,
        "filters": {
            "display_tz": DISPLAY_TZ,
            "candle_timeframe_min": CANDLE_TIMEFRAME_MIN,
            "candle_lookback": CANDLE_LOOKBACK,
            "candle_ignore_enabled": True,
            "candle_ignore_local_hour_start": 0,
            "candle_ignore_local_hour_end": 1,
            "market_open_blackout_enabled": True,
            "market_open_time": "01:05",
            "market_open_tz": "Europe/Bucharest",
            "market_open_blackout_minutes": 15,
            "market_open_weekdays": "0",  # Monday only; comma list 0-6
            "forex_open_sunday_utc_hour": FOREX_OPEN_SUNDAY_UTC_HOUR,
            "forex_close_friday_utc_hour": FOREX_CLOSE_FRIDAY_UTC_HOUR,
        },
    }


def _num(v: Any, *, as_float: bool = False):
    if v is None:
        return None
    try:
        if isinstance(v, str) and not str(v).strip():
            return None
        x = float(v)
        if x != x:  # NaN
            return None
        return x if as_float else int(x)
    except (TypeError, ValueError):
        return None


def apply_overrides(
    symbol: str,
    *,
    range_cfg: Optional[Dict[str, Any]] = None,
    spike_cfg: Optional[Dict[str, Any]] = None,
    spike_neo_cfg: Optional[Dict[str, Any]] = None,
    impulse_retrace_cfg: Optional[Dict[str, Any]] = None,
    range_wick_cfg: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge overrides into live signal configs / filters for one job."""
    global CANDLE_LOOKBACK, DISPLAY_TZ

    base_r, base_s, base_n, base_ir, base_rw = _base_for_symbol(symbol)
    range_cfg = dict(range_cfg or {})
    spike_cfg = dict(spike_cfg or {})
    spike_neo_cfg = dict(spike_neo_cfg or {})
    impulse_retrace_cfg = dict(impulse_retrace_cfg or {})
    range_wick_cfg = dict(range_wick_cfg or {})
    filters = dict(filters or {})

    # 1) Global filters first (does NOT own range.lookback)
    if filters.get("candle_lookback") is not None:
        lb = _num(filters["candle_lookback"])
        if lb is not None:
            CANDLE_LOOKBACK = int(lb)
    if filters.get("display_tz"):
        DISPLAY_TZ = str(filters["display_tz"])
    if "candle_ignore_enabled" in filters and filters["candle_ignore_enabled"] is not None:
        CANDLE_IGNORE["enabled"] = bool(filters["candle_ignore_enabled"])
    if filters.get("candle_ignore_local_hour_start") is not None:
        CANDLE_IGNORE["local_hour_start"] = int(
            filters["candle_ignore_local_hour_start"]
        )
    if filters.get("candle_ignore_local_hour_end") is not None:
        CANDLE_IGNORE["local_hour_end"] = int(filters["candle_ignore_local_hour_end"])
    if "market_open_blackout_enabled" in filters and filters["market_open_blackout_enabled"] is not None:
        MARKET_OPEN_BLACKOUT["enabled"] = bool(filters["market_open_blackout_enabled"])
    if "session_open_skip_enabled" in filters and filters["session_open_skip_enabled"] is not None:
        MARKET_OPEN_BLACKOUT["enabled"] = bool(filters["session_open_skip_enabled"])
    if filters.get("market_open_blackout_minutes") is not None:
        MARKET_OPEN_BLACKOUT["minutes"] = int(filters["market_open_blackout_minutes"])
    if filters.get("session_open_skip_minutes") is not None:
        MARKET_OPEN_BLACKOUT["minutes"] = int(filters["session_open_skip_minutes"])
    if filters.get("market_open_time"):
        MARKET_OPEN_BLACKOUT["open_time"] = str(filters["market_open_time"]).strip()
    if filters.get("market_open_tz"):
        MARKET_OPEN_BLACKOUT["open_tz"] = str(filters["market_open_tz"]).strip()
    if filters.get("market_open_weekdays") is not None:
        raw = filters["market_open_weekdays"]
        if isinstance(raw, str):
            MARKET_OPEN_BLACKOUT["weekdays"] = [
                int(x) for x in raw.replace(" ", "").split(",") if x != ""
            ]
        elif isinstance(raw, list):
            MARKET_OPEN_BLACKOUT["weekdays"] = [int(x) for x in raw]

    # 2) Range / spike (range.lookback is independent of filters.candle_lookback)
    for k, v in range_cfg.items():
        if k not in base_r or v is None:
            continue
        if k == "range_mult":
            nv = _num(v, as_float=True)
        else:
            nv = _num(v, as_float=False)
        if nv is not None:
            base_r[k] = nv

    for k, v in spike_cfg.items():
        if k not in base_s or v is None:
            continue
        if k in ("enabled", "relative_enabled"):
            if isinstance(v, str):
                base_s[k] = v.strip().lower() in ("1", "true", "yes", "on")
            else:
                base_s[k] = bool(v)
        elif k in ("point_size", "relative_mult"):
            nv = _num(v, as_float=True)
            if nv is not None:
                base_s[k] = nv
        else:
            nv = _num(v, as_float=False)
            if nv is not None:
                base_s[k] = nv

    # Final coerce
    base_r["range_mult"] = float(base_r["range_mult"])
    for k in (
        "min_directed_points",
        "min_body_points",
        "hold_sec",
        "structure_break_lookback",
        "breakout_buffer_points",
        "cooldown_min",
        "lookback",
    ):
        base_r[k] = int(float(base_r[k]))

    base_s["enabled"] = bool(base_s.get("enabled", True))
    base_s["relative_enabled"] = bool(base_s.get("relative_enabled", True))
    base_s["point_size"] = float(base_s["point_size"])
    base_s["relative_mult"] = float(base_s["relative_mult"])
    for k in ("min_points", "window_sec", "cooldown_min", "relative_lookback"):
        base_s[k] = int(float(base_s[k]))

    # Spike Neo
    bool_neo = ("enabled", "expansion_dynamic", "require_body_direction")
    float_neo = (
        "compression_size_max_ratio",
        "expansion_mult",
        "expansion_mult_min",
        "expansion_mult_max",
        "expansion_tight_relative_swing",
        "expansion_loose_relative_swing",
    )
    for k, v in spike_neo_cfg.items():
        if k not in base_n or v is None:
            continue
        if k in bool_neo:
            if isinstance(v, str):
                base_n[k] = v.strip().lower() in ("1", "true", "yes", "on")
            else:
                base_n[k] = bool(v)
        elif k in float_neo:
            nv = _num(v, as_float=True)
            if nv is not None:
                base_n[k] = nv
        else:
            nv = _num(v, as_float=False)
            if nv is not None:
                base_n[k] = nv

    base_n["enabled"] = bool(base_n.get("enabled", True))
    base_n["expansion_dynamic"] = bool(base_n.get("expansion_dynamic", True))
    base_n["require_body_direction"] = bool(base_n.get("require_body_direction", True))
    for k in float_neo:
        if k in base_n:
            base_n[k] = float(base_n[k])
    for k in (
        "compression_lookback",
        "compression_swing_max_points",
        "expansion_lookback",
        "expansion_context_lookback",
        "min_forming_points",
        "structure_lookback",
        "break_min_points",
        "hold_sec",
        "cooldown_min",
    ):
        if k in base_n:
            base_n[k] = int(float(base_n[k]))

    # Impulse retrace
    bool_ir = ("enabled", "require_quiet")
    float_ir = ("max_retrace_depth",)
    for k, v in impulse_retrace_cfg.items():
        if k not in base_ir or v is None:
            continue
        if k == "retrace_fractions":
            if isinstance(v, str):
                parts = [p.strip() for p in v.replace(";", ",").split(",") if p.strip()]
                fracs = []
                for p in parts:
                    try:
                        f = float(p)
                    except ValueError:
                        continue
                    if 0.0 < f < 1.0:
                        fracs.append(f)
                if fracs:
                    base_ir[k] = sorted(set(fracs))
            elif isinstance(v, (list, tuple)):
                fracs = []
                for p in v:
                    try:
                        f = float(p)
                    except (TypeError, ValueError):
                        continue
                    if 0.0 < f < 1.0:
                        fracs.append(f)
                if fracs:
                    base_ir[k] = sorted(set(fracs))
            continue
        if k in bool_ir:
            if isinstance(v, str):
                base_ir[k] = v.strip().lower() in ("1", "true", "yes", "on")
            else:
                base_ir[k] = bool(v)
        elif k in float_ir:
            nv = _num(v, as_float=True)
            if nv is not None:
                base_ir[k] = nv
        else:
            nv = _num(v, as_float=False)
            if nv is not None:
                base_ir[k] = nv

    base_ir["enabled"] = bool(base_ir.get("enabled", True))
    base_ir["require_quiet"] = bool(base_ir.get("require_quiet", False))
    base_ir["max_retrace_depth"] = float(base_ir.get("max_retrace_depth") or 0.85)
    base_ir["max_retrace_age_sec"] = int(float(base_ir.get("max_retrace_age_sec") or 0))
    if not isinstance(base_ir.get("retrace_fractions"), list):
        base_ir["retrace_fractions"] = [0.50, 0.75]
    for k in (
        "impulse_lookback",
        "min_impulse_points",
        "extreme_recent_bars",
        "min_pullback_points",
        "max_retrace_age_sec",
        "hold_sec",
        "cooldown_min",
        "quiet_lookback",
        "quiet_swing_max_points",
    ):
        if k in base_ir:
            base_ir[k] = int(float(base_ir[k]))

    # Range wick (same shape as live range params)
    for k, v in range_wick_cfg.items():
        if k not in base_rw or v is None:
            continue
        if k == "range_mult":
            nv = _num(v, as_float=True)
        else:
            nv = _num(v, as_float=False)
        if nv is not None:
            base_rw[k] = nv
    base_rw["range_mult"] = float(base_rw["range_mult"])
    for k in (
        "min_directed_points",
        "min_body_points",
        "hold_sec",
        "structure_break_lookback",
        "breakout_buffer_points",
        "cooldown_min",
        "lookback",
    ):
        if k in base_rw:
            base_rw[k] = int(float(base_rw[k]))

    THRESHOLDS[symbol] = base_r
    SPIKE_CONFIG[symbol] = base_s
    SPIKE_NEO_CONFIG[symbol] = base_n
    IMPULSE_RETRACE_CONFIG[symbol] = base_ir
    RANGE_WICK_THRESHOLDS[symbol] = base_rw

    snap = defaults_snapshot(symbol)
    snap["range"] = copy.deepcopy(THRESHOLDS[symbol])
    snap["spike"] = copy.deepcopy(SPIKE_CONFIG[symbol])
    snap["spike_neo"] = copy.deepcopy(SPIKE_NEO_CONFIG[symbol])
    snap["impulse_retrace"] = copy.deepcopy(IMPULSE_RETRACE_CONFIG[symbol])
    snap["range_wick"] = copy.deepcopy(RANGE_WICK_THRESHOLDS[symbol])
    wd = MARKET_OPEN_BLACKOUT.get("weekdays") or []
    snap["filters"] = {
        "display_tz": DISPLAY_TZ,
        "candle_timeframe_min": CANDLE_TIMEFRAME_MIN,
        "candle_lookback": CANDLE_LOOKBACK,
        "candle_ignore_enabled": bool(CANDLE_IGNORE.get("enabled", True)),
        "candle_ignore_local_hour_start": int(CANDLE_IGNORE.get("local_hour_start", 0)),
        "candle_ignore_local_hour_end": int(CANDLE_IGNORE.get("local_hour_end", 1)),
        "market_open_blackout_enabled": bool(MARKET_OPEN_BLACKOUT.get("enabled", True)),
        "market_open_time": str(MARKET_OPEN_BLACKOUT.get("open_time") or "01:05"),
        "market_open_tz": str(MARKET_OPEN_BLACKOUT.get("open_tz") or "Europe/Bucharest"),
        "market_open_blackout_minutes": int(MARKET_OPEN_BLACKOUT.get("minutes") or 15),
        "market_open_weekdays": ",".join(str(x) for x in wd),
        "forex_open_sunday_utc_hour": FOREX_OPEN_SUNDAY_UTC_HOUR,
        "forex_close_friday_utc_hour": FOREX_CLOSE_FRIDAY_UTC_HOUR,
    }
    return snap
