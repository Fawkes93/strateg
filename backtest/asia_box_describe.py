"""Live setup copy for the Asia box tab. Interpolates current params."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backtest.asia_box import AsiaBoxParams, _FIB_SL_STEPS, _nth_step

SETUP_ORDER = (
    "continuation",
    "reverse_confirm",
    "reverse_ema",
    "shallow_ema",
    "shallow_confirm",
    "ema_retest",
)

_TITLES = {
    "continuation": "Continuation",
    "reverse_confirm": "Reverse Confirm",
    "reverse_ema": "Reverse EMA",
    "shallow_ema": "Shallow EMA",
    "shallow_confirm": "Shallow Confirm",
    "ema_retest": "EMA Retest",
}


def _hhmm(hour: int, minute: int = 0) -> str:
    return f"{int(hour):02d}:{int(minute):02d}"


def _fib_name(level: float) -> str:
    if abs(level) < 1e-9:
        return "Fib 0"
    text = f"{level:.3f}".rstrip("0").rstrip(".")
    if text.startswith("0."):
        return text[1:]
    return text


def _sl_step_level(pos: float, steps: int) -> float:
    return _nth_step(pos, _FIB_SL_STEPS, max(1, int(steps)), toward_higher=True)


def describe_setups(params: Optional[AsiaBoxParams] = None) -> List[Dict[str, Any]]:
    p = params or AsiaBoxParams()
    min_r = int(p.min_range_pts) if float(p.min_range_pts).is_integer() else p.min_range_pts
    box_open = _hhmm(p.box_start_hour)
    box_close = _hhmm(p.box_end_hour)
    shallow_at = _hhmm(p.shallow_hour, p.shallow_minute)
    ema_at = _hhmm(p.ema_retest_hour)
    cutoff = _hhmm(p.entry_cutoff_hour)
    flatten = _hhmm(p.flatten_hour, p.flatten_minute)
    ema_n = int(p.ema_period)
    near = p.shallow_ema_near_pts

    def lv(n: float) -> str:
        return f"Fib {n:g}"

    retest_steps = max(1, int(p.ema_retest_sl_steps or 1))
    through_lv = _fib_name(_sl_step_level(-0.01, retest_steps))
    inside_lv = _fib_name(_sl_step_level(0.10, retest_steps))
    second_fib = " This is the second fib behind the fill." if retest_steps == 2 else ""
    ema_levels = (
        f"Stop is {retest_steps} fib steps behind the fill, toward the other extreme. "
        f"Fib 0 counts as a step, so a fill through Fib 0 stops at {through_lv}. "
        f"A fill between Fib 0 and .236 stops at {inside_lv}.{second_fib} "
        f"Target is Fib 0 when that is still in front of the fill; if the fill is already "
        f"through Fib 0, target is the second extension beyond 0 (−.382)."
        if p.ema_retest_auto_levels
        else f"SL at {lv(p.ema_retest_sl_fib)}, TP at {lv(p.ema_retest_tp_fib)}. Auto steps are off."
    )
    trail_steps = max(1, int(p.continuation_trail_steps or 1))
    trail_through = _fib_name(_sl_step_level(-0.01, trail_steps))
    trail_inside = _fib_name(_sl_step_level(0.10, trail_steps))
    trail = (
        f" Once open, a new high (long) or new low (short) moves the stop "
        f"{trail_steps} fib steps behind that extreme, and only tightens "
        f"(through Fib 0 → {trail_through}; between Fib 0 and .236 → {trail_inside}). "
        f"The open trade keeps the fib from the fill."
        if p.continuation_trail
        else " The stop stays at that fib for the whole trade."
    )
    bodies = {
        "continuation": (
            f"With the box after a deep retrace. Box builds {box_open}–{box_close} local "
            f"and needs at least {min_r} pts. Fib 0 is the later extreme, Fib 1 the other. "
            f"A 5m must close in the box direction with the close still between .500 and .786. "
            f"A wick to .786 taints that candle — one extra clean confirm, or skip. "
            f"A close through .786 kills this door. SL at {lv(p.continuation_sl_fib)}, "
            f"TP at {lv(p.continuation_tp_fib)}.{trail} "
            f"Entries until {cutoff}; flatten {flatten}."
        ),
        "reverse_confirm": (
            f"Against the box after a 5m closes through .786 (a wick is not enough). "
            f"Then a 5m close in the reverse direction, until {cutoff}. "
            f"SL at {lv(p.reverse_confirm_sl_fib)}, TP at {lv(p.reverse_confirm_tp_fib)}."
        ),
        "reverse_ema": (
            f"Same reverse arm as Reverse Confirm. An opposing 5m (against the reverse "
            f"trade) tags the {ema_n}-period 5m EMA while price is still beyond .500. "
            f"SL at {lv(p.reverse_ema_sl_fib)}, TP at {lv(p.reverse_ema_tp_fib)}."
        ),
        "shallow_ema": (
            f"From {shallow_at}, only if .500 has never been tagged on this fib. "
            f"A 5m tags .382 and EMA{ema_n} is within {near:g} pts of that level. "
            f"With the box. SL at {lv(p.shallow_ema_sl_fib)}, TP at {lv(p.shallow_ema_tp_fib)}."
        ),
        "shallow_confirm": (
            f"From {shallow_at}, only if .500 has never been tagged. After a .382 touch, "
            f"a 5m closes in the box direction still between Fib 0 and .500. "
            f"SL at {lv(p.shallow_confirm_sl_fib)}, TP at {lv(p.shallow_confirm_tp_fib)}."
        ),
        "ema_retest": (
            f"{ema_at}–{cutoff}, still flat (or trade 2 after a fill that died before "
            f"{box_close}). Direction is the last Asia leg: 06:00 close vs box midpoint "
            f"(below mid → only shorts from below EMA; above mid → only longs from above). "
            f"Not the later-extreme label used by Continuation. Opposing 5m tags EMA{ema_n}. "
            f"Dead if reverse is armed. {ema_levels}"
        ),
    }
    return [
        {"id": sid, "title": _TITLES[sid], "body": bodies[sid], "enabled": _enabled(p, sid)}
        for sid in SETUP_ORDER
    ]


def describe_rules(params: Optional[AsiaBoxParams] = None) -> List[Dict[str, Any]]:
    """Plain-language session gates. The Asia box tab prints these next to the inputs."""
    p = params or AsiaBoxParams()
    start = _hhmm(p.trade_start_hour, p.trade_start_minute)
    box_open = _hhmm(p.box_start_hour)
    shallow_at = _hhmm(p.shallow_hour, p.shallow_minute)
    ema_at = _hhmm(p.ema_retest_hour)
    steps = max(1, int(p.continuation_trail_steps or 1))
    through_lv = _fib_name(_sl_step_level(-0.01, steps))
    inside_lv = _fib_name(_sl_step_level(0.10, steps))
    pct = f"{p.impulse_freeze_frac * 100:g}"
    mins = int(p.impulse_freeze_minutes)
    if p.trade_start_enabled:
        trade_body = (
            f"No new entry before {start} local. From {box_open} the box high and low, "
            f"the fibs, and the arm flags still update — a reverse can arm early and "
            f"confirm on the first valid close at or after {start}. Shallow still waits "
            f"until {shallow_at}, EMA retest until {ema_at}."
        )
    else:
        trade_body = (
            f"Earliest-entry clock is off. Continuation and reverse can fill as soon as "
            f"the box is wide enough, from {box_open}."
        )
    if p.continuation_trail:
        trail_body = (
            f"Continuation starts at Fib {p.continuation_sl_fib:g}. After a new high (long) "
            f"or new low (short), the stop moves to {steps} fib steps behind that extreme — "
            f"only tighter, never wider. Through Fib 0 that is {through_lv}; between Fib 0 "
            f"and .236 that is {inside_lv}. This trade keeps the fib from the fill. A later "
            f"box high does not move its target."
        )
    else:
        trail_body = (
            f"Continuation trail is off. The stop stays at Fib {p.continuation_sl_fib:g} "
            f"for the whole trade."
        )
    if p.impulse_freeze:
        freeze_body = (
            f"If the 5m that would fill is wider than {pct}% of the Asia box, skip it and "
            f"block every setup for {mins} minutes after that candle closes. The box keeps "
            f"extending during the wait, and a new high or low still redraws the fib. "
            f"This is the Run #14 reverse longs: 2026-03-16 02:00 (2678 pts, 46% of the box, "
            f"stopped −2528) and 2026-04-06 05:15 (2893 pts, 45%, stopped −2998)."
        )
    else:
        freeze_body = (
            "Huge-candle freeze is off. A single 5m can be most of the box and still fill."
        )
    return [
        {
            "id": "trade_start",
            "title": "Watch first",
            "body": trade_body,
            "enabled": bool(p.trade_start_enabled),
        },
        {
            "id": "continuation_trail",
            "title": "Continuation stop",
            "body": trail_body,
            "enabled": bool(p.continuation_trail),
        },
        {
            "id": "impulse_freeze",
            "title": "Huge candle",
            "body": freeze_body,
            "enabled": bool(p.impulse_freeze),
        },
    ]


def _enabled(p: AsiaBoxParams, sid: str) -> bool:
    return bool(
        {
            "continuation": p.enable_continuation,
            "reverse_confirm": p.enable_reverse_confirm,
            "reverse_ema": p.enable_reverse_ema,
            "shallow_ema": p.enable_shallow_ema,
            "shallow_confirm": p.enable_shallow_confirm,
            "ema_retest": p.enable_ema_retest,
        }[sid]
    )
