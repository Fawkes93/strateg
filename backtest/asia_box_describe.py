"""Live setup copy for the Asia box tab. Interpolates current params."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backtest.asia_box import AsiaBoxParams

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

    ema_levels = (
        "SL is the second fib behind entry toward the other extreme "
        "(through Fib 0 → .236; between 0 and .236 → .382; and so on). "
        "TP is Fib 0 when that is still in front of entry; if entry is already "
        "through Fib 0, TP is the second extension beyond 0 (−.382)."
        if p.ema_retest_auto_levels
        else f"SL at {lv(p.ema_retest_sl_fib)}, TP at {lv(p.ema_retest_tp_fib)}."
    )
    bodies = {
        "continuation": (
            f"With the box after a deep retrace. Box builds {box_open}–{box_close} local "
            f"and needs at least {min_r} pts. Fib 0 is the later extreme, Fib 1 the other. "
            f"A 5m must close in the box direction with the close still between .500 and .786. "
            f"A wick to .786 taints that candle — one extra clean confirm, or skip. "
            f"A close through .786 kills this door. SL at {lv(p.continuation_sl_fib)}, "
            f"TP at {lv(p.continuation_tp_fib)}. "
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
