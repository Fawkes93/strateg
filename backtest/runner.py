"""
Core research run: load ticks → replay → score.
Used by single UI jobs and overnight batch sweeps.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from backtest import config as signal_config
from backtest.dukascopy import (
    DEFAULT_DOWNLOAD_WORKERS,
    fetch_hours_parallel,
    get_cached_pack,
    hour_range,
    normalize_duka_symbol,
    parse_ymd,
    reaktor_symbol,
    store_cached_pack,
)
from backtest.forward import (
    filter_scored_by_kind,
    multi_threshold_report,
    normalize_sl_manage,
    score_all_alerts,
)
from backtest.replay import AlertReplay

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / "data" / "dukascopy"
DEFAULT_PACKS = ROOT / "data" / "tick_packs"
DEFAULT_RESULTS = ROOT / "results"

ProgressCb = Optional[Callable[..., None]]


def _parse_range(date_from: str, date_to: str):
    start = parse_ymd(date_from)
    end = parse_ymd(date_to)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)
    return start, end


def load_ticks(
    *,
    symbol: str = "XAUUSD",
    date_from: str,
    date_to: str,
    force_download: bool = False,
    progress: ProgressCb = None,
) -> List:
    """
    Load tick list for [date_from, date_to).
    Uses pack cache (memory + disk) when available.
    """

    def prog(**kwargs: Any) -> None:
        if progress:
            progress(**kwargs)

    symbol_duka = normalize_duka_symbol(symbol)
    start, end = _parse_range(date_from, date_to)
    hours_list = hour_range(start, end)
    n_hours = len(hours_list)
    pack_dir = DEFAULT_PACKS
    ticks: List = []

    if not force_download:
        prog(
            phase="download",
            message=f"Pack cache {symbol_duka} {date_from}→{date_to}…",
            hours_total=n_hours,
            hours_done=0,
            pct=2.0,
        )
        packed = get_cached_pack(symbol_duka, start, end, pack_dir)
        if packed is not None:
            ticks = packed
            prog(
                phase="download",
                message=f"Pack · {len(ticks):,} ticks",
                hours_done=n_hours,
                hours_total=n_hours,
                ticks=len(ticks),
                pct=50.0,
            )

    if not ticks:
        prog(
            phase="download",
            message=(
                f"Loading {n_hours}h {symbol_duka} "
                f"({DEFAULT_DOWNLOAD_WORKERS} parallel)…"
            ),
            hours_total=n_hours,
            hours_done=0,
            pct=3.0,
        )

        def dl_prog(**kwargs: Any) -> None:
            done = int(kwargs.get("hours_done") or 0)
            total = int(kwargs.get("hours_total") or n_hours)
            pct = 5.0 + 42.0 * (done / max(total, 1))
            prog(
                hours_done=done,
                hours_total=total,
                ticks=kwargs.get("ticks") or 0,
                pct=round(pct, 1),
                message=kwargs.get("message")
                or f"Hour {done}/{total} · parallel download",
            )

        all_ticks = fetch_hours_parallel(
            symbol_duka,
            hours_list,
            cache_dir=DEFAULT_CACHE,
            force=force_download,
            max_workers=DEFAULT_DOWNLOAD_WORKERS,
            progress=dl_prog,
        )

        ticks = [t for t in all_ticks if start <= t.ts < end]
        ticks.sort(key=lambda t: t.ts)
        if ticks and not force_download:
            try:
                store_cached_pack(symbol_duka, start, end, pack_dir, ticks)
            except Exception:
                pass
            prog(pct=50.0, ticks=len(ticks), message=f"Loaded {len(ticks):,} ticks")

    if not ticks:
        raise RuntimeError(f"No ticks for {date_from}→{date_to}")
    return ticks


def research_from_ticks(
    ticks: List,
    *,
    symbol: str = "XAUUSD",
    date_from: str,
    date_to: str,
    engines: Optional[List[str]] = None,
    hours: float = 6.0,
    thresholds: Optional[List[float]] = None,
    adverse_mult: float = 1.0,
    signal_price: str = "mid",
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
    signal: Optional[Dict[str, Any]] = None,
    include_detail: bool = True,
    save_json: bool = False,
    progress: ProgressCb = None,
) -> Dict[str, Any]:
    """
    Replay + score using an already-loaded tick list.
    Applies signal overrides for this run (mutates process-local config).
    """

    def prog(**kwargs: Any) -> None:
        if progress:
            progress(**kwargs)

    if not ticks:
        raise RuntimeError(f"No ticks for {date_from}→{date_to}")

    symbol_duka = normalize_duka_symbol(symbol)
    sym = reaktor_symbol(symbol_duka)
    start, end = _parse_range(date_from, date_to)
    eng_set: Set[str] = set(engines or ["candle", "spike"])
    thr_list = list(thresholds or [100, 200, 500, 800, 1000, 1200, 1500, 2000, 3000])
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)

    sig = signal or {}
    effective_cfg = signal_config.apply_overrides(
        sym,
        range_cfg=sig.get("range") if isinstance(sig, dict) else None,
        spike_cfg=sig.get("spike") if isinstance(sig, dict) else None,
        spike_neo_cfg=sig.get("spike_neo") if isinstance(sig, dict) else None,
        impulse_retrace_cfg=sig.get("impulse_retrace")
        if isinstance(sig, dict)
        else None,
        range_wick_cfg=sig.get("range_wick") if isinstance(sig, dict) else None,
        filters=sig.get("filters") if isinstance(sig, dict) else None,
    )

    prog(
        phase="replay",
        message=f"Replay {len(ticks):,} ticks…",
        ticks=len(ticks),
        pct=55.0,
        replay_ticks_done=0,
        alerts=0,
    )

    eng = AlertReplay(sym, engines=eng_set, price_field=signal_price)
    n = len(ticks)
    step = max(n // 40, 1)
    for i, t in enumerate(ticks):
        eng.on_tick(t, i)
        if i % step == 0 or i == n - 1:
            pct = 55.0 + 30.0 * ((i + 1) / n)
            prog(
                replay_ticks_done=i + 1,
                alerts=len(eng.alerts),
                candles=eng.candles_completed,
                pct=round(pct, 1),
                message=(f"Replay {i + 1:,}/{n:,} · {len(eng.alerts)} alerts"),
            )

    alerts = eng.alerts
    alert_idx = eng.alert_tick_index
    window_sec = float(hours) * 3600.0

    def _score_progress(done: int, total: int) -> None:
        pct = 88.0 + 10.0 * (done / max(total, 1))
        prog(
            phase="forward",
            message=f"Score {done}/{total} alerts…",
            alerts=len(alerts),
            pct=round(pct, 1),
        )

    prog(
        phase="forward",
        message=f"Score 0/{len(alerts)} alerts…",
        alerts=len(alerts),
        pct=88.0,
    )

    sl_mode, sl_frac, sl_lock = normalize_sl_manage(
        sl_manage, sl_manage_at_frac, sl_manage_lock_pts
    )

    scored = score_all_alerts(
        alerts,
        alert_idx,
        ticks,
        thresholds=thr_list,
        window_sec=window_sec,
        adverse_mult=adverse_mult,
        price_field=signal_price,
        sl_manage=sl_mode,
        sl_manage_at_frac=sl_frac,
        sl_manage_lock_pts=sl_lock,
        progress_cb=_score_progress,
    )

    overall = multi_threshold_report(
        alerts,
        alert_idx,
        ticks,
        thresholds=thr_list,
        window_sec=window_sec,
        adverse_mult=adverse_mult,
        price_field=signal_price,
        sl_manage=sl_mode,
        sl_manage_at_frac=sl_frac,
        sl_manage_lock_pts=sl_lock,
        scored=scored,
    )

    def _report_for_alerts(
        kind_alerts: List,
        kind_idx: List[int],
    ) -> Dict[str, Any]:
        if not kind_alerts:
            return {}
        # Rebuild scored subset by matching alert identity (kind+ts+side+price)
        # Prefer filtering from already-scored paths when available.
        return multi_threshold_report(
            kind_alerts,
            kind_idx,
            ticks,
            thresholds=thr_list,
            window_sec=window_sec,
            adverse_mult=adverse_mult,
            price_field=signal_price,
            sl_manage=sl_mode,
            sl_manage_at_frac=sl_frac,
            sl_manage_lock_pts=sl_lock,
            scored=None,  # recompute from subset (small n per engine)
        )

    by_engine: Dict[str, Any] = {}
    for kind in sorted(eng_set):
        kind_alerts = [a for a in alerts if a.kind == kind]
        kind_idx = [i for a, i in zip(alerts, alert_idx) if a.kind == kind]
        sub = filter_scored_by_kind(scored, kind)
        if not any(sub.values()) and not kind_alerts:
            by_engine[kind] = {}
            continue
        by_engine[kind] = multi_threshold_report(
            kind_alerts,
            kind_idx,
            ticks,
            thresholds=thr_list,
            window_sec=window_sec,
            adverse_mult=adverse_mult,
            price_field=signal_price,
            sl_manage=sl_mode,
            sl_manage_at_frac=sl_frac,
            sl_manage_lock_pts=sl_lock,
            scored=sub,
        )

        # Impulse retrace: also break out 50% / 75% (etc.) so the report is clear
        if kind == "impulse_retrace" and kind_alerts:
            by_frac: Dict[float, List[int]] = {}
            for j, a in enumerate(kind_alerts):
                frac = (a.meta or {}).get("retrace_fraction")
                if frac is None:
                    continue
                try:
                    f = float(frac)
                except (TypeError, ValueError):
                    continue
                by_frac.setdefault(f, []).append(j)
            for f, jlist in sorted(by_frac.items()):
                sub_alerts = [kind_alerts[j] for j in jlist]
                sub_idx = [kind_idx[j] for j in jlist]
                tag = f"impulse_retrace_{int(round(f * 100))}"
                by_engine[tag] = _report_for_alerts(sub_alerts, sub_idx)

    detail_by_t: Dict[str, List[dict]] = {}
    if include_detail:
        for t in thr_list:
            key = str(int(t) if float(t) == int(t) else t)
            paths = scored.get(key) or []
            detail_by_t[key] = [
                {
                    "kind": p.alert.kind,
                    "side": p.alert.side,
                    "alert_ts": p.alert.ts.isoformat(),
                    "entry": p.alert.price,
                    "hit": p.hit,
                    "clean": p.clean,
                    "first_touch": p.first_touch,
                    "exit": p.exit,
                    "manage_armed": p.manage_armed,
                    "realized_pts": round(p.realized_pts, 1),
                    "max_fav": round(p.max_fav_pts, 1),
                    "max_adv": round(p.max_adv_pts, 1),
                    "max_adv_until_hit": round(p.max_adv_until_hit, 1),
                    "first_hit_sec": p.first_hit_sec,
                    "meta": p.alert.meta,
                    "retrace_fraction": (p.alert.meta or {}).get("retrace_fraction"),
                }
                for p in paths
            ]

    by_kind_count: Dict[str, int] = {}
    for a in alerts:
        by_kind_count[a.kind] = by_kind_count.get(a.kind, 0) + 1
        if a.kind == "impulse_retrace":
            frac = (a.meta or {}).get("retrace_fraction")
            if frac is not None:
                try:
                    tag = f"impulse_retrace_{int(round(float(frac) * 100))}"
                    by_kind_count[tag] = by_kind_count.get(tag, 0) + 1
                except (TypeError, ValueError):
                    pass

    result: Dict[str, Any] = {
        "symbol": sym,
        "duka_symbol": symbol_duka,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "date_from": date_from,
        "date_to": date_to,
        "hours": hours,
        "window_sec": window_sec,
        "adverse_mult": adverse_mult,
        "sl_manage": sl_mode,
        "sl_manage_at_frac": sl_frac,
        "sl_manage_lock_pts": sl_lock,
        "thresholds": thr_list,
        "engines": sorted(eng_set),
        "ticks": len(ticks),
        "alerts": len(alerts),
        "alerts_by_kind": by_kind_count,
        "candles_completed": eng.candles_completed,
        "signal_config": effective_cfg,
        "overall": overall,
        "by_engine": by_engine,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    if include_detail:
        result["detail_by_threshold"] = detail_by_t

    if save_json:
        tag = f"{symbol_duka}_{date_from}_{date_to}_forward"
        out_path = DEFAULT_RESULTS / f"summary_{tag}.json"
        out_path.write_text(json.dumps(result, indent=2, default=str))
        result["saved_to"] = str(out_path)

    prog(
        phase="done",
        message=f"Done · {len(alerts)} alerts · {len(ticks):,} ticks",
        pct=100.0,
        alerts=len(alerts),
        ticks=len(ticks),
    )
    return result


def run_research(
    *,
    symbol: str = "XAUUSD",
    date_from: str,
    date_to: str,
    engines: Optional[List[str]] = None,
    hours: float = 6.0,
    thresholds: Optional[List[float]] = None,
    adverse_mult: float = 1.0,
    signal_price: str = "mid",
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
    force_download: bool = False,
    signal: Optional[Dict[str, Any]] = None,
    include_detail: bool = True,
    save_json: bool = False,
    progress: ProgressCb = None,
) -> Dict[str, Any]:
    """
    Run one research combo. `progress` is called with kwargs like jobs._set_progress.
    """
    ticks = load_ticks(
        symbol=symbol,
        date_from=date_from,
        date_to=date_to,
        force_download=force_download,
        progress=progress,
    )
    return research_from_ticks(
        ticks,
        symbol=symbol,
        date_from=date_from,
        date_to=date_to,
        engines=engines,
        hours=hours,
        thresholds=thresholds,
        adverse_mult=adverse_mult,
        signal_price=signal_price,
        sl_manage=sl_manage,
        sl_manage_at_frac=sl_manage_at_frac,
        sl_manage_lock_pts=sl_manage_lock_pts,
        signal=signal,
        include_detail=include_detail,
        save_json=save_json,
        progress=progress,
    )


def top_ts_by_clean(
    stats_by_t: Dict[str, dict],
    *,
    n: int = 3,
    min_alerts: int = 1,
    min_clean_rate_pct: float = 0.0,
) -> List[dict]:
    """Pick top N thresholds by clean_rate_pct (then hit_rate, then n)."""
    rows = []
    min_clean = float(min_clean_rate_pct or 0)
    for t_key, s in (stats_by_t or {}).items():
        if not s or int(s.get("n") or 0) < min_alerts:
            continue
        clean = s.get("clean_rate_pct")
        if clean is not None and float(clean) < min_clean:
            continue
        rows.append(
            {
                "T": float(t_key),
                "n": s.get("n"),
                "hit_rate_pct": s.get("hit_rate_pct"),
                "clean_rate_pct": s.get("clean_rate_pct"),
                "avg_clean_hit_min": s.get("avg_clean_hit_min"),
                "avg_max_fav": s.get("avg_max_fav"),
                "avg_max_adv": s.get("avg_max_adv"),
                "manage_armed_pct": s.get("manage_armed_pct"),
                "stopped_init_pct": s.get("stopped_init_pct"),
                "stopped_manage_pct": s.get("stopped_manage_pct"),
                "timeout_pct": s.get("timeout_pct"),
                "avg_realized_pts": s.get("avg_realized_pts"),
            }
        )
    rows.sort(
        key=lambda r: (
            r.get("clean_rate_pct") is None,
            -(r.get("clean_rate_pct") or -1),
            r.get("hit_rate_pct") is None,
            -(r.get("hit_rate_pct") or -1),
            -(r.get("n") or 0),
        )
    )
    return rows[:n]
