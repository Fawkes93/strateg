"""
Forward path analysis — same questions as Reaktor Performance / xau_forward.

After an alert at entry price + side:
  - Did favorable excursion reach T points within the next W hours?
  - Was adverse excursion ≤ adverse_limit *before or at* first touch of T?

Optional Factor-style SL manage (`sl_manage`):
  When fav first reaches `sl_manage_at_frac` × T (default ½T), move the stop to
  break-even (`be`) or lock in `sl_manage_lock_pts` (default 100). After that the
  walk for that T stops if the managed stop is touched — the trade would have
  been closed. Unmanaged (`off`) keeps the original path-analysis semantics.

Hot path optimized: one tick walk per alert covers all T values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backtest.config import point_size
from backtest.dukascopy import Tick
from backtest.trades import AlertSignal


@dataclass
class ForwardPath:
    alert: AlertSignal
    threshold_pts: float
    window_sec: float
    adverse_limit_pts: float
    max_fav_pts: float
    max_adv_pts: float
    max_adv_until_hit: float
    hit: bool
    clean: bool
    first_hit_ts: Optional[datetime]
    first_hit_sec: Optional[float]
    first_touch: Optional[str]  # "fav" | "adv" | None
    # Trade-sim extras (used when sl_manage != off; also filled for off)
    exit: str = "timeout"  # target | init_sl | manage_sl | timeout
    manage_armed: bool = False
    realized_pts: float = 0.0


def normalize_sl_manage(
    sl_manage: Optional[str] = None,
    sl_manage_at_frac: Optional[float] = 0.5,
    sl_manage_lock_pts: Optional[float] = 100.0,
) -> Tuple[str, float, float]:
    """Return (mode, trigger_frac, lock_pts). mode is off | be | lock."""
    mode = (sl_manage or "off").strip().lower()
    if mode in ("be", "breakeven", "break_even", "break-even"):
        mode = "be"
    elif mode in ("lock", "lock100", "plus100", "+100"):
        mode = "lock"
    else:
        mode = "off"
    try:
        frac = float(sl_manage_at_frac) if sl_manage_at_frac is not None else 0.5
    except (TypeError, ValueError):
        frac = 0.5
    if not (0.0 < frac < 1.0):
        frac = 0.5
    try:
        lock = float(sl_manage_lock_pts) if sl_manage_lock_pts is not None else 100.0
    except (TypeError, ValueError):
        lock = 100.0
    if lock < 0:
        lock = 0.0
    return mode, frac, lock


def _px(tick: Tick, price_field: str) -> float:
    if price_field == "bid":
        return tick.bid
    if price_field == "ask":
        return tick.ask
    return tick.mid


def prepare_price_arrays(
    ticks: Sequence[Tick],
    price_field: str = "mid",
) -> Tuple[List[float], List[float]]:
    """Precompute unix timestamps + prices once for many alert walks."""
    ts = [t.ts.timestamp() for t in ticks]
    if price_field == "bid":
        px = [t.bid for t in ticks]
    elif price_field == "ask":
        px = [t.ask for t in ticks]
    else:
        px = [t.mid for t in ticks]
    return ts, px


def walk_forward_ticks(
    alert: AlertSignal,
    ticks: Sequence[Tick],
    start_index: int,
    *,
    threshold_pts: float,
    window_sec: float,
    adverse_limit_pts: Optional[float] = None,
    price_field: str = "mid",
    ts_arr: Optional[Sequence[float]] = None,
    px_arr: Optional[Sequence[float]] = None,
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
) -> ForwardPath:
    """Single-T walk (used by CLI / thin paths). Prefer walk_forward_multi for UI."""
    paths = walk_forward_multi(
        alert,
        ticks,
        start_index,
        thresholds=[float(threshold_pts)],
        window_sec=window_sec,
        adverse_mult=(
            float(adverse_limit_pts) / float(threshold_pts)
            if adverse_limit_pts is not None and threshold_pts
            else 1.0
        ),
        price_field=price_field,
        ts_arr=ts_arr,
        px_arr=px_arr,
        sl_manage=sl_manage,
        sl_manage_at_frac=sl_manage_at_frac,
        sl_manage_lock_pts=sl_manage_lock_pts,
    )
    key = str(int(threshold_pts) if float(threshold_pts) == int(threshold_pts) else threshold_pts)
    # multi keys may be int-like strings
    if key not in paths:
        # try float key
        for k, v in paths.items():
            return v
        # empty
        adv = float(threshold_pts) if adverse_limit_pts is None else float(adverse_limit_pts)
        return ForwardPath(
            alert=alert,
            threshold_pts=float(threshold_pts),
            window_sec=window_sec,
            adverse_limit_pts=adv,
            max_fav_pts=0.0,
            max_adv_pts=0.0,
            max_adv_until_hit=0.0,
            hit=False,
            clean=False,
            first_hit_ts=None,
            first_hit_sec=None,
            first_touch=None,
        )
    return paths[key]


def walk_forward_multi(
    alert: AlertSignal,
    ticks: Sequence[Tick],
    start_index: int,
    *,
    thresholds: Sequence[float],
    window_sec: float,
    adverse_mult: float = 1.0,
    price_field: str = "mid",
    ts_arr: Optional[Sequence[float]] = None,
    px_arr: Optional[Sequence[float]] = None,
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
) -> Dict[str, ForwardPath]:
    """
    One forward walk → stats for every T.

    Returns map threshold_key → ForwardPath.
    """
    thr_list = [float(t) for t in thresholds]
    ps = point_size(alert.symbol)
    mode, arm_frac, lock_pts = normalize_sl_manage(
        sl_manage, sl_manage_at_frac, sl_manage_lock_pts
    )
    manage_on = mode != "off"

    def empty(t: float) -> ForwardPath:
        adv = t * float(adverse_mult)
        return ForwardPath(
            alert=alert,
            threshold_pts=t,
            window_sec=window_sec,
            adverse_limit_pts=adv,
            max_fav_pts=0.0,
            max_adv_pts=0.0,
            max_adv_until_hit=0.0,
            hit=False,
            clean=False,
            first_hit_ts=None,
            first_hit_sec=None,
            first_touch=None,
            exit="timeout",
            manage_armed=False,
            realized_pts=0.0,
        )

    if start_index >= len(ticks) or ps <= 0 or not thr_list:
        return {
            str(int(t) if t == int(t) else t): empty(t) for t in thr_list
        }

    if ts_arr is not None and px_arr is not None:
        t0 = float(ts_arr[start_index])
        entry = float(px_arr[start_index])
    else:
        entry_tick = ticks[start_index]
        t0 = entry_tick.ts.timestamp()
        entry = _px(entry_tick, price_field)

    if alert.price and alert.price > 0:
        entry = float(alert.price)

    side_up = alert.side == "UP"
    n_thr = len(thr_list)
    adv_lims = [t * float(adverse_mult) for t in thr_list]

    # Per-T state
    hit = [False] * n_thr
    done = [False] * n_thr  # trade closed (target or SL) when manage_on
    max_adv_until = [0.0] * n_thr
    first_hit_sec: List[Optional[float]] = [None] * n_thr
    first_hit_ts: List[Optional[datetime]] = [None] * n_thr
    first_touch: List[Optional[str]] = [None] * n_thr
    exit_kind = ["timeout"] * n_thr
    armed = [False] * n_thr
    realized = [0.0] * n_thr
    n_done = 0

    run_hi = entry
    run_lo = entry
    max_fav = 0.0
    max_adv = 0.0
    last_cur_fav = 0.0
    t_end = t0 + float(window_sec)

    use_arr = ts_arr is not None and px_arr is not None
    n_ticks = len(ticks)

    for i in range(start_index + 1, n_ticks):
        if use_arr:
            ts = float(ts_arr[i])  # type: ignore[index]
            if ts > t_end:
                break
            px = float(px_arr[i])  # type: ignore[index]
            elapsed = ts - t0
            tick_ts = ticks[i].ts
        else:
            t = ticks[i]
            elapsed = (t.ts - ticks[start_index].ts).total_seconds()
            if elapsed > window_sec:
                break
            px = _px(t, price_field)
            tick_ts = t.ts

        if px > run_hi:
            run_hi = px
        if px < run_lo:
            run_lo = px

        if side_up:
            fav = (run_hi - entry) / ps
            adv = (entry - run_lo) / ps
            cur_fav = (px - entry) / ps
            cur_adv = (entry - px) / ps
        else:
            fav = (entry - run_lo) / ps
            adv = (run_hi - entry) / ps
            cur_fav = (entry - px) / ps
            cur_adv = (px - entry) / ps

        if fav > max_fav:
            max_fav = fav
        if adv > max_adv:
            max_adv = adv
        last_cur_fav = cur_fav

        if n_done >= n_thr:
            continue

        for k in range(n_thr):
            if done[k] or (not manage_on and hit[k]):
                continue
            if adv > max_adv_until[k]:
                max_adv_until[k] = adv
            thr = thr_list[k]
            alim = adv_lims[k]
            fav_hit = fav + 1e-9 >= thr
            adv_hit = adv + 1e-9 >= alim

            if not manage_on:
                if first_touch[k] is None:
                    if fav_hit and adv_hit:
                        first_touch[k] = "adv"
                    elif fav_hit:
                        first_touch[k] = "fav"
                    elif adv_hit:
                        first_touch[k] = "adv"
                if fav_hit:
                    hit[k] = True
                    done[k] = True
                    first_hit_sec[k] = elapsed
                    first_hit_ts[k] = tick_ts
                    exit_kind[k] = "target"
                    realized[k] = thr
                    n_done += 1
                continue

            # --- managed trade sim ---
            # Arm when running fav first reaches half-T (or configured frac).
            # If this tick also hits T, take the target (½T is implied).
            if fav_hit:
                hit[k] = True
                done[k] = True
                first_touch[k] = "fav"
                first_hit_sec[k] = elapsed
                first_hit_ts[k] = tick_ts
                exit_kind[k] = "target"
                realized[k] = thr
                if fav + 1e-9 >= arm_frac * thr:
                    armed[k] = True
                n_done += 1
                continue

            if not armed[k] and fav + 1e-9 >= arm_frac * thr:
                armed[k] = True

            stopped = False
            if armed[k]:
                if mode == "be" and cur_fav <= 1e-9:
                    stopped = True
                    realized[k] = 0.0
                elif mode == "lock" and cur_fav <= lock_pts + 1e-9:
                    stopped = True
                    realized[k] = lock_pts
            else:
                if adv_hit:
                    stopped = True
                    realized[k] = -alim

            if stopped:
                done[k] = True
                first_touch[k] = "adv"
                first_hit_sec[k] = elapsed
                first_hit_ts[k] = tick_ts
                exit_kind[k] = "manage_sl" if armed[k] else "init_sl"
                n_done += 1

    out: Dict[str, ForwardPath] = {}
    for k, thr in enumerate(thr_list):
        key = str(int(thr) if thr == int(thr) else thr)
        h = hit[k]
        if manage_on:
            if exit_kind[k] == "timeout":
                realized[k] = last_cur_fav
            clean = h  # reached T without being stopped
        else:
            clean = h and (max_adv_until[k] <= adv_lims[k] + 1e-9)
            if h:
                realized[k] = thr
            elif first_touch[k] == "adv":
                # Unmanaged path-analysis: SL was touched but walk kept going.
                # Realized-if-flattened-at-SL for expectancy comparison.
                realized[k] = -adv_lims[k]
            else:
                realized[k] = last_cur_fav
                exit_kind[k] = "timeout"
        out[key] = ForwardPath(
            alert=alert,
            threshold_pts=thr,
            window_sec=window_sec,
            adverse_limit_pts=adv_lims[k],
            max_fav_pts=max_fav,
            max_adv_pts=max_adv,
            max_adv_until_hit=max_adv_until[k],
            hit=h,
            clean=clean,
            first_hit_ts=first_hit_ts[k],
            first_hit_sec=first_hit_sec[k],
            first_touch=first_touch[k],
            exit=exit_kind[k],
            manage_armed=armed[k],
            realized_pts=float(realized[k]),
        )
    return out


def summarize_forward(paths: Sequence[ForwardPath]) -> dict:
    n = len(paths)
    hits = sum(1 for p in paths if p.hit)
    cleans = sum(1 for p in paths if p.clean)
    race_fav = sum(1 for p in paths if p.first_touch == "fav")
    race_adv = sum(1 for p in paths if p.first_touch == "adv")
    # Time-to-T only among clean wins (hit + adverse budget ok)
    clean_hit_secs = [
        float(p.first_hit_sec)
        for p in paths
        if p.clean and p.first_hit_sec is not None
    ]

    def pct(a: int, b: int) -> Optional[float]:
        if b <= 0:
            return None
        return round(100.0 * a / b, 1)

    avg_clean_sec = (
        sum(clean_hit_secs) / len(clean_hit_secs) if clean_hit_secs else None
    )
    avg_clean_min = (
        round(avg_clean_sec / 60.0, 1) if avg_clean_sec is not None else None
    )

    armed_n = sum(1 for p in paths if p.manage_armed)
    init_sl_n = sum(1 for p in paths if p.exit == "init_sl")
    manage_sl_n = sum(1 for p in paths if p.exit == "manage_sl")
    timeout_n = sum(1 for p in paths if p.exit == "timeout")
    pts_sum = sum(float(p.realized_pts) for p in paths) if n else 0.0
    avg_real = round(pts_sum / n, 1) if n else 0.0

    return {
        "n": n,
        "hits": hits,
        "cleans": cleans,
        "hit_rate_pct": pct(hits, n),
        "clean_rate_pct": pct(cleans, n),
        "clean_given_hit_pct": pct(cleans, hits) if hits else None,
        "first_touch_fav": race_fav,
        "first_touch_adv": race_adv,
        "avg_max_fav": round(sum(p.max_fav_pts for p in paths) / n, 1) if n else 0.0,
        "avg_max_adv": round(sum(p.max_adv_pts for p in paths) / n, 1) if n else 0.0,
        "avg_max_adv_until_hit": (
            round(sum(p.max_adv_until_hit for p in paths if p.hit) / hits, 1)
            if hits
            else None
        ),
        "median_hit_sec": _median(
            [p.first_hit_sec for p in paths if p.first_hit_sec is not None]
        ),
        # Average time from alert → first T among *clean* hits only
        "avg_clean_hit_sec": (
            round(avg_clean_sec, 1) if avg_clean_sec is not None else None
        ),
        "avg_clean_hit_min": avg_clean_min,
        "manage_armed": armed_n,
        "manage_armed_pct": pct(armed_n, n),
        "stopped_init": init_sl_n,
        "stopped_init_pct": pct(init_sl_n, n),
        "stopped_manage": manage_sl_n,
        "stopped_manage_pct": pct(manage_sl_n, n),
        "timeout": timeout_n,
        "timeout_pct": pct(timeout_n, n),
        "avg_realized_pts": avg_real,
        "sum_realized_pts": round(pts_sum, 1),
    }


def _median(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    m = len(s) // 2
    if len(s) % 2:
        return round(s[m], 1)
    return round((s[m - 1] + s[m]) / 2.0, 1)


def score_all_alerts(
    alerts: Sequence[AlertSignal],
    alert_tick_index: Sequence[int],
    ticks: Sequence[Tick],
    *,
    thresholds: Sequence[float],
    window_sec: float,
    adverse_mult: float = 1.0,
    price_field: str = "mid",
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
    progress_cb=None,
) -> Dict[str, List[ForwardPath]]:
    """
    Score every alert once for all T.

    Returns {threshold_key: [ForwardPath per alert in order]}.
    """
    thr_list = [float(t) for t in thresholds]
    keys = [str(int(t) if t == int(t) else t) for t in thr_list]
    out: Dict[str, List[ForwardPath]] = {k: [] for k in keys}

    ts_arr, px_arr = prepare_price_arrays(ticks, price_field)
    n = len(alerts)
    for j, (a, idx) in enumerate(zip(alerts, alert_tick_index)):
        multi = walk_forward_multi(
            a,
            ticks,
            idx,
            thresholds=thr_list,
            window_sec=window_sec,
            adverse_mult=adverse_mult,
            price_field=price_field,
            ts_arr=ts_arr,
            px_arr=px_arr,
            sl_manage=sl_manage,
            sl_manage_at_frac=sl_manage_at_frac,
            sl_manage_lock_pts=sl_manage_lock_pts,
        )
        for k in keys:
            out[k].append(multi[k])
        if progress_cb and (j % 10 == 0 or j == n - 1):
            progress_cb(j + 1, n)

    return out


def multi_threshold_report(
    alerts: Sequence[AlertSignal],
    alert_tick_index: Sequence[int],
    ticks: Sequence[Tick],
    *,
    thresholds: Sequence[float],
    window_sec: float,
    adverse_mult: float = 1.0,
    price_field: str = "mid",
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
    scored: Optional[Dict[str, List[ForwardPath]]] = None,
) -> Dict[str, dict]:
    """
    For each T, hit/clean summary.

    Pass `scored` from score_all_alerts to avoid re-walking.
    """
    if scored is None:
        scored = score_all_alerts(
            alerts,
            alert_tick_index,
            ticks,
            thresholds=thresholds,
            window_sec=window_sec,
            adverse_mult=adverse_mult,
            price_field=price_field,
            sl_manage=sl_manage,
            sl_manage_at_frac=sl_manage_at_frac,
            sl_manage_lock_pts=sl_manage_lock_pts,
        )
    mode, arm_frac, lock_pts = normalize_sl_manage(
        sl_manage, sl_manage_at_frac, sl_manage_lock_pts
    )
    out: Dict[str, dict] = {}
    for t in thresholds:
        key = str(int(t) if float(t) == int(t) else t)
        paths = scored.get(key) or []
        # If scored was for a subset of alerts, paths already match
        s = summarize_forward(paths)
        s["threshold_pts"] = float(t)
        s["adverse_limit_pts"] = float(t) * float(adverse_mult)
        s["adverse_mult"] = adverse_mult
        s["window_sec"] = window_sec
        s["sl_manage"] = mode
        s["sl_manage_at_frac"] = arm_frac
        s["sl_manage_lock_pts"] = lock_pts
        out[key] = s
    return out


def paths_for_threshold(
    alerts: Sequence[AlertSignal],
    alert_tick_index: Sequence[int],
    ticks: Sequence[Tick],
    *,
    threshold_pts: float,
    window_sec: float,
    adverse_mult: float = 1.0,
    price_field: str = "mid",
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
    scored: Optional[Dict[str, List[ForwardPath]]] = None,
) -> List[ForwardPath]:
    key = str(
        int(threshold_pts) if float(threshold_pts) == int(threshold_pts) else threshold_pts
    )
    if scored is not None and key in scored:
        return scored[key]
    scored = score_all_alerts(
        alerts,
        alert_tick_index,
        ticks,
        thresholds=[float(threshold_pts)],
        window_sec=window_sec,
        adverse_mult=adverse_mult,
        price_field=price_field,
        sl_manage=sl_manage,
        sl_manage_at_frac=sl_manage_at_frac,
        sl_manage_lock_pts=sl_manage_lock_pts,
    )
    return scored[key]


def filter_scored_by_kind(
    scored: Dict[str, List[ForwardPath]],
    kind: str,
) -> Dict[str, List[ForwardPath]]:
    """Keep only paths whose alert.kind matches."""
    out: Dict[str, List[ForwardPath]] = {}
    for k, paths in scored.items():
        out[k] = [p for p in paths if p.alert.kind == kind]
    return out
