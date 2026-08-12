"""
Forward path analysis — same questions as Reaktor Performance / xau_forward.

After an alert at entry price + side:
  - Did favorable excursion reach T points within the next W hours?
  - Was adverse excursion ≤ adverse_limit *before or at* first touch of T?

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
) -> Dict[str, ForwardPath]:
    """
    One forward walk → stats for every T.

    Returns map threshold_key → ForwardPath.
    """
    thr_list = [float(t) for t in thresholds]
    ps = point_size(alert.symbol)

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
    max_adv_until = [0.0] * n_thr
    first_hit_sec: List[Optional[float]] = [None] * n_thr
    first_hit_ts: List[Optional[datetime]] = [None] * n_thr
    first_touch: List[Optional[str]] = [None] * n_thr
    n_hit = 0

    run_hi = entry
    run_lo = entry
    max_fav = 0.0
    max_adv = 0.0
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
        else:
            fav = (entry - run_lo) / ps
            adv = (run_hi - entry) / ps

        if fav > max_fav:
            max_fav = fav
        if adv > max_adv:
            max_adv = adv

        # Update every T that has not hit yet
        if n_hit < n_thr:
            for k in range(n_thr):
                if hit[k]:
                    continue
                if adv > max_adv_until[k]:
                    max_adv_until[k] = adv
                thr = thr_list[k]
                alim = adv_lims[k]
                fav_hit = fav + 1e-9 >= thr
                adv_hit = adv + 1e-9 >= alim
                if first_touch[k] is None:
                    if fav_hit and adv_hit:
                        first_touch[k] = "adv"
                    elif fav_hit:
                        first_touch[k] = "fav"
                    elif adv_hit:
                        first_touch[k] = "adv"
                if fav_hit:
                    hit[k] = True
                    first_hit_sec[k] = elapsed
                    first_hit_ts[k] = tick_ts
                    n_hit += 1

    out: Dict[str, ForwardPath] = {}
    for k, thr in enumerate(thr_list):
        key = str(int(thr) if thr == int(thr) else thr)
        h = hit[k]
        clean = h and (max_adv_until[k] <= adv_lims[k] + 1e-9)
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
