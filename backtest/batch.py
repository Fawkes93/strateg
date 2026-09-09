"""
Overnight parameter sweep: date ranges × experiment rows per alert type.

Speed:
  - Group by date range → load ticks once, replay all param variants
  - Optional multi-process workers across date-range groups only
    (never split one date's variants — one tick load per month)
"""

from __future__ import annotations

import itertools
import json
import os
import queue
import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from multiprocessing import Manager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backtest.config import _base_for_symbol
from backtest.dukascopy import drop_cached_pack, normalize_duka_symbol, parse_ymd, reaktor_symbol
from backtest.runner import (
    DEFAULT_RESULTS,
    _parse_range,
    load_ticks,
    research_from_ticks,
    top_ts_by_clean,
    unique_result_path,
)
from backtest.job_memory import release_job_memory
from backtest.seasonality import lookback_from

# Short UI names → full config keys
RANGE_SHORT = {
    "mult": "range_mult",
    "min_dir": "min_directed_points",
    "min_body": "min_body_points",
    "hold": "hold_sec",
    "struct": "structure_break_lookback",
    "buf": "breakout_buffer_points",
    "cd": "cooldown_min",
    "lb": "lookback",
}
SPIKE_SHORT = {
    "min": "min_points",
    "win": "window_sec",
    "cd": "cooldown_min",
    "rel": "relative_mult",
    "rel_n": "relative_lookback",
    "rel_on": "relative_enabled",
    "en": "enabled",
    "pt": "point_size",
}
SPIKE_NEO_SHORT = {
    "en": "enabled",
    "comp_n": "compression_lookback",
    "comp_swing": "compression_swing_max_points",
    "comp_size": "compression_size_max_ratio",
    "exp_n": "expansion_lookback",
    "exp_mult": "expansion_mult",
    "exp_dyn": "expansion_dynamic",
    "exp_ctx": "expansion_context_lookback",
    "exp_min": "expansion_mult_min",
    "exp_max": "expansion_mult_max",
    "min_form": "min_forming_points",
    "struct_n": "structure_lookback",
    "break": "break_min_points",
    "hold": "hold_sec",
    "cd": "cooldown_min",
    "body": "require_body_direction",
}
IMPULSE_RETRACE_SHORT = {
    "en": "enabled",
    "look": "impulse_lookback",
    "min_imp": "min_impulse_points",
    "ext_n": "extreme_recent_bars",
    "fracs": "retrace_fractions",
    "min_pull": "min_pullback_points",
    "max_depth": "max_retrace_depth",
    "max_age": "max_retrace_age_sec",
    "hold": "hold_sec",
    "cd": "cooldown_min",
    "quiet": "require_quiet",
    "quiet_n": "quiet_lookback",
    "quiet_sw": "quiet_swing_max_points",
}
RANGE_WICK_SHORT = {
    "mult": "range_mult",
    "min_dir": "min_directed_points",
    "min_body": "min_body_points",
    "hold": "hold_sec",
    "struct": "structure_break_lookback",
    "buf": "breakout_buffer_points",
    "cd": "cooldown_min",
    "lb": "lookback",
}


@dataclass
class BatchProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    run_index: int = 0
    run_total: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    # nested single-run progress
    sub_phase: str = ""
    sub_message: str = ""
    sub_pct: float = 0.0


@dataclass
class BatchState:
    running: bool = False
    progress: BatchProgress = field(default_factory=BatchProgress)
    report: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


_lock = threading.Lock()
_state = BatchState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
# Active process pool (if any) so Stop can hard-kill workers mid-replay
_active_pool: Optional[ProcessPoolExecutor] = None
_active_pool_lock = threading.Lock()


def get_batch_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "progress": asdict(_state.progress),
            "report": _state.report,
            "config": _state.config,
            "cancel_requested": _cancel.is_set(),
        }


def is_batch_running() -> bool:
    with _lock:
        return _state.running


def _set_prog(**kwargs: Any) -> None:
    with _lock:
        for k, v in kwargs.items():
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


def _force_kill_pool() -> int:
    """
    Terminate ProcessPoolExecutor worker processes immediately.
    Returns how many processes we tried to kill.
    """
    global _active_pool
    killed = 0
    with _active_pool_lock:
        pool = _active_pool
        if pool is None:
            return 0
        # Cancel not-yet-started futures
        try:
            # Private API, but needed for true stop mid-replay
            procs = getattr(pool, "_processes", None) or {}
            for p in list(procs.values()):
                try:
                    if p.is_alive():
                        p.terminate()
                        killed += 1
                except Exception:
                    pass
            # Brief wait then kill -9 leftovers
            time.sleep(0.3)
            for p in list(procs.values()):
                try:
                    if p.is_alive():
                        p.kill()
                        killed += 1
                except Exception:
                    pass
        except Exception:
            pass
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            try:
                pool.shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass
        _active_pool = None
    return killed


def stop_batch() -> Dict[str, Any]:
    """
    Stop the sweep now: set cancel flag and hard-kill worker processes
    so RAM is freed (not just 'stop requested' while workers keep replaying).
    """
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "No batch running"}
        _cancel.set()
        _set_prog(
            phase="cancelling",
            message="Stopping… killing workers to free RAM",
        )
    n = _force_kill_pool()
    return {
        "ok": True,
        "message": f"Stop sent · terminated {n} worker process(es)",
        "workers_killed": n,
    }


def load_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Load a saved/re-ranked batch report into UI state (no re-run)."""
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Batch is running — stop it first"}
        _state.report = report
        _state.progress = BatchProgress(
            phase="done",
            message=report.get("rerank_note")
            or report.get("message")
            or f"Loaded report · {report.get('run_count') or len(report.get('rows') or [])} runs",
            pct=100.0,
            run_index=int(report.get("run_count") or 0),
            run_total=int(report.get("run_total") or report.get("run_count") or 0),
            finished_at=report.get("finished_at"),
        )
    return {"ok": True, "run_count": report.get("run_count")}


# Keys that are list-valued (comma/pipe separates list items, not cartesian expand)
_LIST_CELL_KEYS = {"fracs", "retrace_fractions"}


def expand_row_values(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Each cell can be a single value or a list (or comma-separated string).
    Cartesian product across multi-valued keys.
    Exception: fracs / retrace_fractions stay one value (list of fractions).
    """
    keys = list(row.keys())
    value_lists: List[List[Any]] = []
    for k in keys:
        v = row[k]
        if v is None or (isinstance(v, str) and v.strip() == ""):
            value_lists.append([None])
            continue
        if k in _LIST_CELL_KEYS:
            value_lists.append([v])
            continue
        if isinstance(v, list):
            value_lists.append(v if v else [None])
        elif isinstance(v, str) and "," in v:
            parts = [p.strip() for p in v.split(",") if p.strip() != ""]
            value_lists.append(parts if parts else [v])
        else:
            value_lists.append([v])

    out = []
    for combo in itertools.product(*value_lists):
        d = {}
        for k, val in zip(keys, combo):
            if val is None or (isinstance(val, str) and val.strip() == ""):
                continue
            d[k] = val
        out.append(d)
    return out if out else [{}]


def short_to_full(short_map: Dict[str, str], row: Dict[str, Any]) -> Dict[str, Any]:
    full = {}
    for k, v in row.items():
        key = short_map.get(k, k)
        if key == "retrace_fractions" or k in _LIST_CELL_KEYS:
            if isinstance(v, (list, tuple)):
                full[key] = [float(x) for x in v]
            elif isinstance(v, str):
                parts = [
                    p.strip()
                    for p in v.replace(";", ",").replace("|", ",").split(",")
                    if p.strip()
                ]
                fracs = []
                for p in parts:
                    try:
                        f = float(p)
                    except ValueError:
                        continue
                    if 0.0 < f < 1.0:
                        fracs.append(f)
                full[key] = fracs if fracs else [0.5, 0.75]
            else:
                try:
                    full[key] = [float(v)]
                except (TypeError, ValueError):
                    full[key] = [0.5, 0.75]
            continue
        if isinstance(v, str) and v.lower() in ("true", "false"):
            full[key] = v.lower() == "true"
        else:
            try:
                if isinstance(v, str) and "." in v:
                    full[key] = float(v)
                else:
                    full[key] = int(v) if isinstance(v, str) and v.lstrip("-").isdigit() else v
                    if isinstance(v, str) and not v.lstrip("-").isdigit():
                        try:
                            full[key] = float(v)
                        except ValueError:
                            full[key] = v
            except (TypeError, ValueError):
                full[key] = v
    return full


def label_params(prefix: str, params: Dict[str, Any]) -> str:
    if not params:
        return f"{prefix}=defaults"
    parts = [f"{k}={v}" for k, v in sorted(params.items())]
    return f"{prefix}[" + ",".join(parts) + "]"


def label_experiment(
    engines: List[str],
    range_p: Dict[str, Any],
    spike_p: Dict[str, Any],
    neo_p: Optional[Dict[str, Any]] = None,
    ir_p: Optional[Dict[str, Any]] = None,
    wick_p: Optional[Dict[str, Any]] = None,
) -> str:
    bits = []
    if "candle" in engines:
        bits.append(label_params("range", range_p))
    if "spike" in engines:
        bits.append(label_params("spike", spike_p))
    if "spike_neo" in engines:
        bits.append(label_params("neo", neo_p or {}))
    if "impulse_retrace" in engines:
        bits.append(label_params("impulse", ir_p or {}))
    if "candle_wick" in engines or "range_wick" in engines:
        bits.append(label_params("wick", wick_p or {}))
    return " + ".join(bits) if bits else "defaults"


def _expand_engine_rows(rows: List[Dict], short_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Expand research rows.
    - Empty {} is an explicit “defaults only” experiment (one config).
    - Missing/blank cells inside a non-empty row are ignored for that key.
    - Empty list → no configs (caller may pair partner defaults).
    """
    out: List[Dict[str, Any]] = []
    for raw in rows:
        if raw is None:
            continue
        if isinstance(raw, dict) and len(raw) == 0:
            # Explicit defaults-only row from UI
            out.append({})
            continue
        if isinstance(raw, dict) and not any(
            v is not None and str(v).strip() != "" for v in raw.values()
        ):
            continue
        for expanded in expand_row_values(raw):
            out.append(short_to_full(short_map, expanded))
    return out


def _is_default_only(cfgs: List[Dict[str, Any]]) -> bool:
    """True if list is empty or only empty dicts (all defaults)."""
    if not cfgs:
        return True
    return all(not c for c in cfgs)


def _zip_pad_many(
    *lists: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """
    Zip N config lists by index; cycle shorter ones.
    Returns list of N-tuples as lists: [[c0,c1,...], ...]
    """
    cleaned = [list(L) if L else [{}] for L in lists]
    n = max(len(L) for L in cleaned)
    out: List[List[Dict[str, Any]]] = []
    for i in range(n):
        out.append([dict(L[i % len(L)]) for L in cleaned])
    return out


def build_work_items(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build multi-engine runs (range / spike / spike_neo share one tick load when on).

    pairing (cfg["pairing"]):
      - "together" / "zip" (default): one run per slot in max(variants);
        shorter lists cycle. Example: 3 range + 2 spike + 1 neo → 3 runs.
      - "grid": full product of active engines' variant lists.
    """
    ranges = cfg.get("date_ranges") or []
    if not ranges:
        raise ValueError("Need at least one date range")

    test_range = bool(cfg.get("test_range", True))
    test_spike = bool(cfg.get("test_spike", True))
    test_neo = bool(cfg.get("test_spike_neo", False))
    test_ir = bool(cfg.get("test_impulse_retrace", False))
    test_wick = bool(cfg.get("test_range_wick", False) or cfg.get("test_candle_wick", False))
    if not any((test_range, test_spike, test_neo, test_ir, test_wick)):
        raise ValueError("Enable at least one engine")

    pairing = (cfg.get("pairing") or "together").strip().lower()
    if pairing in ("zip", "by_alert", "independent"):
        pairing = "together"
    if pairing not in ("together", "grid"):
        pairing = "together"

    range_rows = list(cfg.get("range_rows") or []) if test_range else []
    spike_rows = list(cfg.get("spike_rows") or []) if test_spike else []
    neo_rows = list(cfg.get("spike_neo_rows") or []) if test_neo else []
    ir_rows = list(cfg.get("impulse_retrace_rows") or []) if test_ir else []
    wick_rows = list(cfg.get("range_wick_rows") or cfg.get("candle_wick_rows") or []) if test_wick else []

    range_cfgs = _expand_engine_rows(range_rows, RANGE_SHORT) if test_range else []
    spike_cfgs = _expand_engine_rows(spike_rows, SPIKE_SHORT) if test_spike else []
    neo_cfgs = _expand_engine_rows(neo_rows, SPIKE_NEO_SHORT) if test_neo else []
    ir_cfgs = _expand_engine_rows(ir_rows, IMPULSE_RETRACE_SHORT) if test_ir else []
    wick_cfgs = _expand_engine_rows(wick_rows, RANGE_WICK_SHORT) if test_wick else []

    any_filled = bool(range_cfgs or spike_cfgs or neo_cfgs or ir_cfgs or wick_cfgs)
    if any_filled:
        if test_range and not range_cfgs:
            range_cfgs = [{}]
        if test_spike and not spike_cfgs:
            spike_cfgs = [{}]
        if test_neo and not neo_cfgs:
            neo_cfgs = [{}]
        if test_ir and not ir_cfgs:
            ir_cfgs = [{}]
        if test_wick and not wick_cfgs:
            wick_cfgs = [{}]

    if not any((range_cfgs, spike_cfgs, neo_cfgs, ir_cfgs, wick_cfgs)):
        raise ValueError(
            "No research rows: fill at least one param cell, or add “Defaults only”"
        )

    engines: List[str] = []
    if test_range:
        engines.append("candle")
    if test_spike:
        engines.append("spike")
    if test_neo:
        engines.append("spike_neo")
    if test_ir:
        engines.append("impulse_retrace")
    if test_wick:
        engines.append("candle_wick")

    r_list = range_cfgs if test_range else [{}]
    s_list = spike_cfgs if test_spike else [{}]
    n_list = neo_cfgs if test_neo else [{}]
    i_list = ir_cfgs if test_ir else [{}]
    w_list = wick_cfgs if test_wick else [{}]
    for flag, lst_name in (
        (test_range, "r_list"),
        (test_spike, "s_list"),
        (test_neo, "n_list"),
        (test_ir, "i_list"),
        (test_wick, "w_list"),
    ):
        pass
    if test_range and not r_list:
        r_list = [{}]
    if test_spike and not s_list:
        s_list = [{}]
    if test_neo and not n_list:
        n_list = [{}]
    if test_ir and not i_list:
        i_list = [{}]
    if test_wick and not w_list:
        w_list = [{}]

    combos: List[tuple] = []  # (range, spike, neo, ir, wick)

    if pairing == "grid":
        for rc in r_list:
            for sc in s_list:
                for nc in n_list:
                    for ic in i_list:
                        for wc in w_list:
                            combos.append(
                                (
                                    dict(rc) if test_range else {},
                                    dict(sc) if test_spike else {},
                                    dict(nc) if test_neo else {},
                                    dict(ic) if test_ir else {},
                                    dict(wc) if test_wick else {},
                                )
                            )
    else:
        zipped = _zip_pad_many(
            r_list if test_range else [{}],
            s_list if test_spike else [{}],
            n_list if test_neo else [{}],
            i_list if test_ir else [{}],
            w_list if test_wick else [{}],
        )
        for row in zipped:
            rc, sc, nc, ic, wc = row[0], row[1], row[2], row[3], row[4]
            combos.append(
                (
                    dict(rc) if test_range else {},
                    dict(sc) if test_spike else {},
                    dict(nc) if test_neo else {},
                    dict(ic) if test_ir else {},
                    dict(wc) if test_wick else {},
                )
            )

    items: List[Dict[str, Any]] = []
    for dr in ranges:
        d_from = dr.get("from") or dr.get("date_from")
        d_to = dr.get("to") or dr.get("date_to")
        if not d_from or not d_to:
            continue

        for rc, sc, nc, ic, wc in combos:
            items.append(
                {
                    "date_from": d_from,
                    "date_to": d_to,
                    "engines": list(engines),
                    "range": dict(rc) if test_range else {},
                    "spike": dict(sc) if test_spike else {},
                    "spike_neo": dict(nc) if test_neo else {},
                    "impulse_retrace": dict(ic) if test_ir else {},
                    "range_wick": dict(wc) if test_wick else {},
                    "label": label_experiment(
                        engines,
                        rc if test_range else {},
                        sc if test_spike else {},
                        nc if test_neo else {},
                        ic if test_ir else {},
                        wc if test_wick else {},
                    ),
                }
            )

    if not items:
        raise ValueError("No experiments to run (enable engines and add rows)")
    return items


def start_batch(cfg: Dict[str, Any]) -> Dict[str, Any]:
    global _thread
    from backtest.jobs import is_job_running

    with _lock:
        if _state.running:
            return {"ok": False, "error": "Batch already running"}
        if is_job_running():
            return {"ok": False, "error": "Single research is running — wait for it"}
        from backtest.session_jobs import is_session_running

        if is_session_running():
            return {"ok": False, "error": "Session clock is running"}
        from backtest.spike_fade_jobs import is_spike_fade_running

        if is_spike_fade_running():
            return {"ok": False, "error": "Spike fade is running"}
        from backtest.micro_momentum_jobs import is_micro_running

        if is_micro_running():
            return {"ok": False, "error": "Micro fade is running"}
        from backtest.cooloff_jobs import is_cooloff_running

        if is_cooloff_running():
            return {"ok": False, "error": "Cool-off is running"}
        items = build_work_items(cfg)
        _cancel.clear()
        _state.running = True
        _state.report = None
        _state.config = cfg
        _state.progress = BatchProgress(
            phase="run",
            message=f"Starting {len(items)} runs…",
            pct=0.0,
            run_index=0,
            run_total=len(items),
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        # Non-daemon so ProcessPoolExecutor workers are allowed and survive UI
        _thread = threading.Thread(
            target=_run_batch, args=(cfg, items), daemon=False, name="batch-sweep"
        )
        _thread.start()
    return {"ok": True, "runs": len(items)}


class BatchCancelled(Exception):
    """User requested stop between runs."""


def _run_batch(cfg: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
    try:
        report = _pipeline_batch(cfg, items)
        with _lock:
            # Keep full variant summary rows for Sweep UI; ticks already released in finally.
            _state.report = report
        cancelled = bool(report.get("cancelled")) or _cancel.is_set()
        done_n = int(report.get("run_count") or 0)
        total_n = int(report.get("run_total") or len(items))
        _set_prog(
            phase="done" if not cancelled else "cancelled",
            message=(
                f"Stopped · {done_n}/{total_n} runs completed"
                if cancelled
                else f"Batch done · {total_n} runs"
            ),
            pct=100.0 if not cancelled else round(100.0 * done_n / max(total_n, 1), 1),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except BatchCancelled:
        _set_prog(
            phase="cancelled",
            message="Sweep stopped",
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        _set_prog(
            phase="error",
            message=str(e),
            error=traceback.format_exc(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        _force_kill_pool()
        _cancel.clear()
        try:
            release_job_memory()
        except Exception:
            pass
        with _lock:
            _state.running = False


def _item_signal(
    item: Dict[str, Any],
    filters: Dict[str, Any],
    symbol: str = "XAUUSD",
) -> Dict[str, Any]:
    # Must seed the *selected* symbol. XAU point_size=0.01 on EURUSD
    # makes a 5-pip move look like 0.5 points → zero alerts.
    base_r, base_s, base_n, base_ir, base_rw = _base_for_symbol(
        reaktor_symbol(symbol)
    )
    signal = {
        "range": base_r,
        "spike": base_s,
        "spike_neo": base_n,
        "impulse_retrace": base_ir,
        "range_wick": base_rw,
        "filters": dict(filters or {}),
    }
    if item.get("range"):
        signal["range"].update(item["range"])
    if item.get("spike"):
        signal["spike"].update(item["spike"])
    if item.get("spike_neo"):
        signal["spike_neo"].update(item["spike_neo"])
    if item.get("impulse_retrace"):
        signal["impulse_retrace"].update(item["impulse_retrace"])
    if item.get("range_wick"):
        signal["range_wick"].update(item["range_wick"])
    return signal


def _params_for_engine(item: Dict[str, Any], engine: str) -> Dict[str, Any]:
    if engine == "candle":
        return dict(item.get("range") or {})
    if engine == "spike_neo":
        return dict(item.get("spike_neo") or {})
    if engine == "impulse_retrace":
        return dict(item.get("impulse_retrace") or {})
    if engine in ("candle_wick", "range_wick"):
        return dict(item.get("range_wick") or {})
    return dict(item.get("spike") or {})


def _rows_from_result(
    item: Dict[str, Any],
    res: Dict[str, Any],
    *,
    top_n: int,
) -> List[Dict[str, Any]]:
    engines = list(item.get("engines") or ["candle", "spike"])
    rows: List[Dict[str, Any]] = []
    by_eng = res.get("by_engine") or {}
    by_kind = res.get("alerts_by_kind") or {}

    def _append_row(engine: str, stats: Dict[str, Any], *, label_extra: str = "") -> None:
        top = top_ts_by_clean(stats, n=top_n, min_clean_rate_pct=50.0)
        params = _params_for_engine(item, engine.split("_")[0] if engine.startswith("impulse_retrace_") else engine)
        if engine.startswith("impulse_retrace_"):
            params = dict(_params_for_engine(item, "impulse_retrace"))
            try:
                pct = int(engine.rsplit("_", 1)[-1])
                params = {**params, "active_retrace_fraction": pct / 100.0}
            except ValueError:
                pass
        base_label = item.get("label") or ""
        label = (base_label + label_extra) if label_extra else base_label
        n_alerts = by_kind.get(engine)
        if n_alerts is None and engine == "impulse_retrace":
            n_alerts = by_kind.get("impulse_retrace") or res.get("alerts")
        rows.append(
            {
                "date_from": item["date_from"],
                "date_to": item["date_to"],
                "engine": engine,
                "label": label,
                "params": params,
                "alerts": n_alerts if n_alerts is not None else res.get("alerts"),
                "alerts_by_kind": by_kind,
                "ticks": res.get("ticks"),
                "top_ts": top,
                "all_ts": _compact_all_ts(stats),
                "ok": True,
                "error": None,
                "shared_run": True,
            }
        )

    for engine in engines:
        if engine == "impulse_retrace":
            # Prefer fraction breakouts when present; still emit combined total
            frac_keys = sorted(
                k
                for k in by_eng.keys()
                if isinstance(k, str) and k.startswith("impulse_retrace_")
            )
            if frac_keys:
                for fk in frac_keys:
                    stats = by_eng.get(fk) or {}
                    try:
                        pct = int(fk.rsplit("_", 1)[-1])
                        extra = f" · retrace {pct}%"
                    except ValueError:
                        extra = f" · {fk}"
                    _append_row(fk, stats, label_extra=extra)
                # Combined pool (all fractions) for overview
                stats_all = by_eng.get("impulse_retrace") or {}
                if stats_all:
                    _append_row(
                        "impulse_retrace",
                        stats_all,
                        label_extra=" · all fractions",
                    )
            else:
                stats = by_eng.get(engine) or {}
                if not stats and len(engines) == 1:
                    stats = res.get("overall") or {}
                _append_row(engine, stats)
            continue

        stats = by_eng.get(engine) or {}
        if not stats and len(engines) == 1:
            stats = res.get("overall") or {}
        _append_row(engine, stats)
    return rows


def _error_rows(item: Dict[str, Any], err: BaseException) -> List[Dict[str, Any]]:
    engines = list(item.get("engines") or ["candle", "spike"])
    rows = []
    for engine in engines:
        rows.append(
            {
                "date_from": item.get("date_from"),
                "date_to": item.get("date_to"),
                "engine": engine,
                "label": item.get("label"),
                "params": _params_for_engine(item, engine),
                "ok": False,
                "error": str(err),
                "top_ts": [],
                "all_ts": [],
            }
        )
    return rows


def _group_items_by_date(
    items: List[Dict[str, Any]],
) -> List[Tuple[str, str, List[Dict[str, Any]]]]:
    """Preserve order of first appearance of each date range."""
    order: List[Tuple[str, str]] = []
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for it in items:
        key = (str(it["date_from"]), str(it["date_to"]))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(it)
    return [(df, dt, groups[(df, dt)]) for df, dt in order]


def _split_for_workers(
    date_groups: List[Tuple[str, str, List[Dict[str, Any]]]],
    workers: int,
) -> List[Dict[str, Any]]:
    """
    One process job per date range. All variants for that range stay together
    so ticks load once. Workers only run *different months* in parallel.
    """
    return [
        {"date_from": df, "date_to": dt, "items": list(group_items)}
        for df, dt, group_items in date_groups
    ]


def _run_date_group_job(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Worker entrypoint (must be picklable top-level).
    Load ticks once for the date range, then replay every param variant.
    Emits progress events on job["progress_q"] when provided.
    """
    symbol = job["symbol"]
    date_from = job["date_from"]
    date_to = job["date_to"]
    hours = float(job["hours"])
    thresholds = job["thresholds"]
    adverse = float(job["adverse_mult"])
    sl_manage = job.get("sl_manage") or "off"
    sl_manage_at_frac = float(job.get("sl_manage_at_frac") or 0.5)
    sl_manage_lock_pts = float(job.get("sl_manage_lock_pts") or 100.0)
    top_n = int(job["top_n"])
    filters = job.get("filters") or {}
    items = job["items"]
    progress_q = job.get("progress_q")
    job_id = job.get("job_id", "?")

    def emit(event: str, **extra: Any) -> None:
        if progress_q is None:
            return
        try:
            payload = {
                "event": event,
                "job_id": job_id,
                "date_from": date_from,
                "date_to": date_to,
                **extra,
            }
            progress_q.put(payload)
        except Exception:
            pass

    rows: List[Dict[str, Any]] = []
    emit("load", message=f"Load {date_from}→{date_to} · {len(items)} variants")
    ticks = None
    lookback_ticks = None
    try:
        try:
            ticks = load_ticks(
                symbol=symbol,
                date_from=date_from,
                date_to=date_to,
                force_download=False,
                progress=None,
            )
        except Exception as e:
            for item in items:
                rows.extend(_error_rows(item, e))
                emit(
                    "item_done",
                    n=1,
                    ok=False,
                    label=str(item.get("label") or ""),
                    message=str(e)[:120],
                )
            return rows

        emit(
            "loaded",
            ticks=len(ticks),
            message=f"Pack {len(ticks):,} ticks · {date_from}→{date_to}",
        )

        _flt = job.get("filters") or {}
        if bool(_flt.get("week2_trend")) or str(_flt.get("week2_mode") or "off") != "off":
            try:
                prefix = load_ticks(
                    symbol=symbol,
                    date_from=lookback_from(date_from),
                    date_to=date_from,
                    force_download=False,
                    progress=None,
                )
                cutoff = parse_ymd(date_from)
                lookback_ticks = [t for t in prefix if t.ts < cutoff]
                del prefix
            except Exception:
                lookback_ticks = None

        for vi, item in enumerate(items):
            engines = list(item.get("engines") or ["candle", "spike"])
            signal = _item_signal(item, filters, symbol)
            label = str(item.get("label") or "")
            emit(
                "item_start",
                label=label,
                variant=vi + 1,
                variants=len(items),
                message=f"Replay {date_from}→{date_to} · {label}",
            )

            last_emit = [0.0]

            def sub_progress(label=label, **kwargs: Any) -> None:
                # throttle mid-replay heartbeats (~every 5% of overall research pct)
                pct = float(kwargs.get("pct") or 0)
                if pct - last_emit[0] < 5.0 and pct < 99.0:
                    return
                last_emit[0] = pct
                emit(
                    "item_tick",
                    label=label,
                    sub_pct=pct,
                    message=str(kwargs.get("message") or f"Replay {label}"),
                )

            try:
                res = research_from_ticks(
                    ticks,
                    symbol=symbol,
                    date_from=date_from,
                    date_to=date_to,
                    engines=engines,
                    hours=hours,
                    thresholds=thresholds,
                    adverse_mult=adverse,
                    sl_manage=sl_manage,
                    sl_manage_at_frac=sl_manage_at_frac,
                    sl_manage_lock_pts=sl_manage_lock_pts,
                    signal=signal,
                    include_detail=False,
                    save_json=False,
                    progress=sub_progress,
                    lookback_ticks=lookback_ticks,
                )
                rows.extend(_rows_from_result(item, res, top_n=top_n))
                emit("item_done", n=1, ok=True, label=label, message=label)
            except Exception as e:
                rows.extend(_error_rows(item, e))
                emit(
                    "item_done",
                    n=1,
                    ok=False,
                    label=label,
                    message=str(e)[:120],
                )
    finally:
        # Free tick arrays in this process (main for workers=1; child otherwise).
        ticks = None
        lookback_ticks = None
        try:
            start, end = _parse_range(date_from, date_to)
            drop_cached_pack(normalize_duka_symbol(symbol), start, end)
        except Exception:
            pass
        import gc as _gc

        _gc.collect()
    return rows


def _default_workers() -> int:
    n = os.cpu_count() or 2
    # Cap at 4 — each process copies the tick pack (tight on 8GB, but usable).
    return max(1, min(4, n))


def _pipeline_batch(cfg: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    global _active_pool
    symbol = cfg.get("symbol") or "XAUUSD"
    hours = float(cfg.get("hours") or 6)
    thresholds = cfg.get("thresholds") or [100, 200, 500, 800, 1000, 1200, 1500, 2000]
    adverse = float(cfg.get("adverse_mult") or 1.0)
    sl_manage = cfg.get("sl_manage") or "off"
    sl_manage_at_frac = float(cfg.get("sl_manage_at_frac") or 0.5)
    sl_manage_lock_pts = float(cfg.get("sl_manage_lock_pts") or 100.0)
    filters = cfg.get("filters") or {}
    top_n = int(cfg.get("top_n") or 3)
    workers = int(cfg.get("workers") if cfg.get("workers") is not None else _default_workers())
    workers = max(1, min(4, workers))

    results_rows: List[Dict[str, Any]] = []
    total = len(items)
    date_groups = _group_items_by_date(items)

    # --- Phase 1: warm tick packs for every unique date range (serial, download-safe)
    unique_ranges = [(df, dt) for df, dt, _ in date_groups]
    for ri, (df, dt) in enumerate(unique_ranges):
        if _cancel.is_set():
            break
        _set_prog(
            phase="pack",
            run_index=0,
            run_total=total,
            pct=round(5.0 * (ri / max(len(unique_ranges), 1)), 1),
            message=f"Warm pack {ri + 1}/{len(unique_ranges)} · {df}→{dt}",
            sub_phase="pack",
            sub_message="load ticks",
            sub_pct=0.0,
        )

        def pack_prog(ri=ri, df=df, dt=dt, **kwargs: Any) -> None:
            mapped: Dict[str, Any] = {}
            if "message" in kwargs:
                mapped["sub_message"] = kwargs["message"]
            if "pct" in kwargs:
                sub = float(kwargs["pct"])
                overall = 5.0 * (ri + sub / 100.0) / max(len(unique_ranges), 1)
                mapped["pct"] = round(min(8.0, overall), 1)
                mapped["sub_pct"] = sub
            if "phase" in kwargs:
                mapped["sub_phase"] = kwargs["phase"]
            mapped["message"] = (
                f"Warm pack {ri + 1}/{len(unique_ranges)} · {df}→{dt}"
                + (f" · {kwargs.get('message')}" if kwargs.get("message") else "")
            )
            _set_prog(**mapped)

        try:
            load_ticks(
                symbol=symbol,
                date_from=df,
                date_to=dt,
                force_download=False,
                progress=pack_prog,
            )
        except Exception as e:
            # Variants will record errors when they run
            _set_prog(
                sub_message=f"pack error: {e}",
                message=f"Pack failed {df}→{dt}: {e}",
            )

    if _cancel.is_set():
        release_job_memory()
        return _finalize_report(
            symbol, hours, thresholds, adverse, top_n, filters,
            results_rows, total, workers, cancelled=True,
            sl_manage=sl_manage,
            sl_manage_at_frac=sl_manage_at_frac,
            sl_manage_lock_pts=sl_manage_lock_pts,
        )

    # Warm phase only needed disk packs; multi-process workers reload from disk.
    # Drop main-process packs before spawning workers (or before single-thread replay
    # reloads the active group) so an 8GB laptop is not holding every month at once.
    from backtest.dukascopy import clear_mem_packs
    clear_mem_packs()

    # --- Phase 2: replay (group by date; optionally multi-process)
    jobs_meta = _split_for_workers(date_groups, workers)
    job_payloads: List[Dict[str, Any]] = []
    for ji, jm in enumerate(jobs_meta):
        job_payloads.append(
            {
                "job_id": f"j{ji}",
                "symbol": symbol,
                "date_from": jm["date_from"],
                "date_to": jm["date_to"],
                "hours": hours,
                "thresholds": list(thresholds),
                "adverse_mult": adverse,
                "sl_manage": sl_manage,
                "sl_manage_at_frac": sl_manage_at_frac,
                "sl_manage_lock_pts": sl_manage_lock_pts,
                "top_n": top_n,
                "filters": dict(filters or {}),
                "items": jm["items"],
            }
        )

    completed = 0
    # Fractional progress inside current in-flight variants (0..active_workers)
    in_flight_frac = 0.0

    def note_progress(extra: str = "", *, sub_pct: float = 0.0) -> None:
        frac = min(0.95, max(0.0, in_flight_frac))
        overall = 8.0 + 90.0 * ((completed + frac) / max(total, 1))
        _set_prog(
            phase="run",
            run_index=min(completed, total),
            run_total=total,
            pct=round(min(98.0, overall), 1),
            message=(
                f"Replay {completed}/{total}"
                + (f" · {workers} workers" if workers > 1 else " · 1 worker")
                + (f" · {extra}" if extra else "")
            ),
            sub_phase="replay",
            sub_message=extra,
            sub_pct=sub_pct,
        )

    if workers <= 1 or len(job_payloads) <= 1:
        # Single-process path: full progress detail + guaranteed tick reuse per group
        for jp in job_payloads:
            if _cancel.is_set():
                break
            df, dt = jp["date_from"], jp["date_to"]
            group_items = jp["items"]
            _set_prog(
                message=f"Load {df}→{dt} once · {len(group_items)} variants",
                sub_phase="load",
                sub_message=f"{df}→{dt}",
            )
            try:
                ticks = load_ticks(
                    symbol=symbol,
                    date_from=df,
                    date_to=dt,
                    force_download=False,
                    progress=None,
                )
            except Exception as e:
                for item in group_items:
                    results_rows.extend(_error_rows(item, e))
                    completed += 1
                    note_progress(str(item.get("label") or ""))
                continue

            for item in group_items:
                if _cancel.is_set():
                    break
                engines = list(item.get("engines") or ["candle", "spike"])
                signal = _item_signal(item, filters, symbol)
                label = item.get("label") or ""
                i_local = completed

                def sub_progress(i_local=i_local, label=label, **kwargs: Any) -> None:
                    mapped: Dict[str, Any] = {}
                    if "phase" in kwargs:
                        mapped["sub_phase"] = kwargs["phase"]
                    if "message" in kwargs:
                        mapped["sub_message"] = kwargs["message"]
                    if "pct" in kwargs:
                        sub = float(kwargs["pct"])
                        overall = 8.0 + 90.0 * (i_local + sub / 100.0) / max(total, 1)
                        mapped["pct"] = round(min(98.0, overall), 1)
                        mapped["sub_pct"] = sub
                    mapped["message"] = (
                        f"Run {i_local + 1}/{total} · {df}→{dt} · {label}"
                    )
                    mapped["run_index"] = i_local
                    mapped["run_total"] = total
                    _set_prog(**mapped)

                try:
                    res = research_from_ticks(
                        ticks,
                        symbol=symbol,
                        date_from=df,
                        date_to=dt,
                        engines=engines,
                        hours=hours,
                        thresholds=thresholds,
                        adverse_mult=adverse,
                        signal=signal,
                        include_detail=False,
                        save_json=False,
                        progress=sub_progress,
                    )
                    results_rows.extend(_rows_from_result(item, res, top_n=top_n))
                except Exception as e:
                    results_rows.extend(_error_rows(item, e))
                completed += 1
                note_progress(label)
    else:
        # Multi-process with live progress queue (item heartbeats)
        note_progress(f"starting {len(job_payloads)} jobs")
        job_frac: Dict[str, float] = {}
        manager = None
        pool: Optional[ProcessPoolExecutor] = None
        try:
            manager = Manager()
            progress_q = manager.Queue()
            for jp in job_payloads:
                jp["progress_q"] = progress_q

            pool = ProcessPoolExecutor(max_workers=workers)
            with _active_pool_lock:
                _active_pool = pool

            future_map = {
                pool.submit(_run_date_group_job, jp): jp for jp in job_payloads
            }
            pending = set(future_map.keys())

            def drain_queue() -> str:
                nonlocal completed, in_flight_frac
                last_extra = ""
                while True:
                    try:
                        msg = progress_q.get_nowait()
                    except queue.Empty:
                        break
                    except Exception:
                        break
                    ev = msg.get("event")
                    jid = str(msg.get("job_id") or "?")
                    df = msg.get("date_from") or ""
                    dt = msg.get("date_to") or ""
                    label = msg.get("label") or ""
                    if ev == "item_done":
                        n = int(msg.get("n") or 1)
                        completed += n
                        job_frac.pop(jid, None)
                        last_extra = f"{df}→{dt} · {label}"
                    elif ev == "item_start":
                        job_frac[jid] = 0.05
                        last_extra = f"{df}→{dt} · {label}"
                    elif ev == "item_tick":
                        sub = float(msg.get("sub_pct") or 0) / 100.0
                        job_frac[jid] = max(0.05, min(0.95, sub))
                        last_extra = str(msg.get("message") or label)
                    elif ev in ("load", "loaded"):
                        job_frac[jid] = 0.02
                        last_extra = str(msg.get("message") or f"{df}→{dt}")
                    in_flight_frac = sum(job_frac.values())
                    if last_extra:
                        note_progress(
                            last_extra,
                            sub_pct=round(100.0 * job_frac.get(jid, 0), 1),
                        )
                return last_extra

            while pending:
                if _cancel.is_set():
                    _set_prog(
                        phase="cancelling",
                        message="Stop: terminating worker processes…",
                    )
                    for f in pending:
                        try:
                            f.cancel()
                        except Exception:
                            pass
                    _force_kill_pool()
                    pool = None
                    break

                drain_queue()
                try:
                    done_set, pending = wait(
                        pending, timeout=0.8, return_when=FIRST_COMPLETED
                    )
                except Exception:
                    # Pool may have been killed under us
                    if _cancel.is_set():
                        break
                    raise
                drain_queue()

                for fut in done_set:
                    jp = future_map[fut]
                    jid = str(jp.get("job_id") or "?")
                    job_frac.pop(jid, None)
                    try:
                        if fut.cancelled():
                            continue
                        part = fut.result(timeout=0.1)
                        results_rows.extend(part or [])
                    except Exception as e:
                        # BrokenProcessPool / killed workers after stop
                        if _cancel.is_set():
                            continue
                        for item in jp.get("items") or []:
                            results_rows.extend(_error_rows(item, e))
                    in_flight_frac = sum(job_frac.values())
                    note_progress(
                        f"{jp.get('date_from')}→{jp.get('date_to')} job done"
                    )

            drain_queue()
            if completed > total:
                completed = total
            finished_items = len(
                {
                    (r.get("date_from"), r.get("date_to"), r.get("label"))
                    for r in results_rows
                }
            )
            if finished_items > completed:
                completed = finished_items
                note_progress("sync")
        except Exception as e:
            if _cancel.is_set():
                _set_prog(message=f"Stopped (workers killed) · {e}")
            else:
                _set_prog(
                    message=f"Workers failed ({e}); falling back to serial…",
                )
                _force_kill_pool()
                if manager is not None:
                    try:
                        manager.shutdown()
                    except Exception:
                        pass
                return _pipeline_batch({**cfg, "workers": 1}, items)
        finally:
            _force_kill_pool()
            if manager is not None:
                try:
                    manager.shutdown()
                except Exception:
                    pass

    return _finalize_report(
        symbol,
        hours,
        thresholds,
        adverse,
        top_n,
        filters,
        results_rows,
        total,
        workers,
        cancelled=_cancel.is_set(),
        sl_manage=sl_manage,
        sl_manage_at_frac=sl_manage_at_frac,
        sl_manage_lock_pts=sl_manage_lock_pts,
    )


def _finalize_report(
    symbol: str,
    hours: float,
    thresholds: List,
    adverse: float,
    top_n: int,
    filters: Dict[str, Any],
    results_rows: List[Dict[str, Any]],
    total: int,
    workers: int,
    *,
    cancelled: bool,
    sl_manage: str = "off",
    sl_manage_at_frac: float = 0.5,
    sl_manage_lock_pts: float = 100.0,
) -> Dict[str, Any]:
    results_rows.sort(
        key=lambda r: (
            r.get("date_from") or "",
            r.get("date_to") or "",
            r.get("engine") or "",
            r.get("label") or "",
        )
    )
    by_range: Dict[str, List[dict]] = {}
    for r in results_rows:
        key = f"{r.get('date_from')} → {r.get('date_to')}"
        by_range.setdefault(key, []).append(r)

    completed_items = len(
        {
            (r.get("date_from"), r.get("date_to"), r.get("label"))
            for r in results_rows
        }
    )
    report = {
        "kind": "batch_sweep",
        "symbol": symbol,
        "hours": hours,
        "thresholds": thresholds,
        "adverse_mult": adverse,
        "sl_manage": sl_manage,
        "sl_manage_at_frac": sl_manage_at_frac,
        "sl_manage_lock_pts": sl_manage_lock_pts,
        "top_n": top_n,
        "filters": filters,
        "workers": workers,
        "run_count": completed_items if cancelled else total,
        "run_total": total,
        "cancelled": cancelled,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "by_date_range": by_range,
        "rows": results_rows,
        "defaults_note": "Partial experiment rows merge onto Reaktor XAU defaults",
        "speed_note": (
            "Ticks loaded once per date range; "
            f"{workers} process worker(s) for parallel date groups (no variant split)"
        ),
    }

    path, run_id = unique_result_path(f"batch_{symbol}")
    report["run_id"] = run_id
    path.write_text(json.dumps(report, indent=2, default=str))
    report["saved_to"] = str(path)
    return report


def _compact_all_ts(stats_by_t: Dict[str, dict]) -> List[dict]:
    rows = []
    for t_key, s in sorted(
        (stats_by_t or {}).items(), key=lambda kv: float(kv[0])
    ):
        if not s:
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
                "hits": s.get("hits"),
                "cleans": s.get("cleans"),
                "avg_realized_pts": s.get("avg_realized_pts"),
                "sum_realized_pts": s.get("sum_realized_pts"),
                "realized_mode": s.get("realized_mode"),
            }
        )
    return rows


def batch_param_schema(symbol: str = "XAUUSD") -> Dict[str, Any]:
    """UI helper: short names + defaults for the selected symbol."""
    r, s, n, ir, rw = _base_for_symbol(reaktor_symbol(symbol))
    fracs = ir.get("retrace_fractions") or [0.5, 0.75]
    if isinstance(fracs, (list, tuple)):
        fracs_s = ",".join(str(x) for x in fracs)
    else:
        fracs_s = str(fracs)
    return {
        "symbol": reaktor_symbol(symbol),
        "range_fields": [
            {"short": "mult", "full": "range_mult", "default": r["range_mult"]},
            {"short": "min_dir", "full": "min_directed_points", "default": r["min_directed_points"]},
            {"short": "min_body", "full": "min_body_points", "default": r["min_body_points"]},
            {"short": "hold", "full": "hold_sec", "default": r["hold_sec"]},
            {"short": "struct", "full": "structure_break_lookback", "default": r["structure_break_lookback"]},
            {"short": "buf", "full": "breakout_buffer_points", "default": r["breakout_buffer_points"]},
            {"short": "cd", "full": "cooldown_min", "default": r["cooldown_min"]},
            {"short": "lb", "full": "lookback", "default": r["lookback"]},
        ],
        "spike_fields": [
            {"short": "min", "full": "min_points", "default": s["min_points"]},
            {"short": "win", "full": "window_sec", "default": s["window_sec"]},
            {"short": "cd", "full": "cooldown_min", "default": s["cooldown_min"]},
            {"short": "rel", "full": "relative_mult", "default": s["relative_mult"]},
            {"short": "rel_n", "full": "relative_lookback", "default": s["relative_lookback"]},
            {"short": "rel_on", "full": "relative_enabled", "default": s["relative_enabled"]},
        ],
        "spike_neo_fields": [
            {"short": "comp_n", "full": "compression_lookback", "default": n["compression_lookback"]},
            {"short": "comp_swing", "full": "compression_swing_max_points", "default": n["compression_swing_max_points"]},
            {"short": "comp_size", "full": "compression_size_max_ratio", "default": n["compression_size_max_ratio"]},
            {"short": "exp_n", "full": "expansion_lookback", "default": n["expansion_lookback"]},
            {"short": "exp_min", "full": "expansion_mult_min", "default": n["expansion_mult_min"]},
            {"short": "exp_max", "full": "expansion_mult_max", "default": n["expansion_mult_max"]},
            {"short": "min_form", "full": "min_forming_points", "default": n["min_forming_points"]},
            {"short": "struct_n", "full": "structure_lookback", "default": n["structure_lookback"]},
            {"short": "break", "full": "break_min_points", "default": n["break_min_points"]},
            {"short": "hold", "full": "hold_sec", "default": n["hold_sec"]},
            {"short": "cd", "full": "cooldown_min", "default": n["cooldown_min"]},
        ],
        "impulse_retrace_fields": [
            {"short": "look", "full": "impulse_lookback", "default": ir["impulse_lookback"]},
            {"short": "min_imp", "full": "min_impulse_points", "default": ir["min_impulse_points"]},
            {"short": "ext_n", "full": "extreme_recent_bars", "default": ir["extreme_recent_bars"]},
            {"short": "fracs", "full": "retrace_fractions", "default": fracs_s},
            {"short": "min_pull", "full": "min_pullback_points", "default": ir["min_pullback_points"]},
            {"short": "max_depth", "full": "max_retrace_depth", "default": ir["max_retrace_depth"]},
            {"short": "max_age", "full": "max_retrace_age_sec", "default": ir["max_retrace_age_sec"]},
            {"short": "hold", "full": "hold_sec", "default": ir["hold_sec"]},
            {"short": "cd", "full": "cooldown_min", "default": ir["cooldown_min"]},
            {"short": "quiet", "full": "require_quiet", "default": ir["require_quiet"]},
            {"short": "quiet_n", "full": "quiet_lookback", "default": ir["quiet_lookback"]},
            {"short": "quiet_sw", "full": "quiet_swing_max_points", "default": ir["quiet_swing_max_points"]},
        ],
        "range_wick_fields": [
            {"short": "mult", "full": "range_mult", "default": rw["range_mult"]},
            {"short": "min_dir", "full": "min_directed_points", "default": rw["min_directed_points"]},
            {"short": "min_body", "full": "min_body_points", "default": rw["min_body_points"]},
            {"short": "hold", "full": "hold_sec", "default": rw["hold_sec"]},
            {"short": "struct", "full": "structure_break_lookback", "default": rw["structure_break_lookback"]},
            {"short": "buf", "full": "breakout_buffer_points", "default": rw["breakout_buffer_points"]},
            {"short": "cd", "full": "cooldown_min", "default": rw["cooldown_min"]},
            {"short": "lb", "full": "lookback", "default": rw["lookback"]},
        ],
        "hint": "Comma-separate values to expand. Empty table = 0 runs. Wick = legacy wick-latched range (source candle_wick). EURUSD: 1 pt = 0.1 pip (T=50 is 5 pips).",
    }
