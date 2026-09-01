"""Background job for the Trend Cool-Off tab."""

from __future__ import annotations

import gc
import json
import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from queue import Empty
from typing import Any, Dict, List, Optional, Sequence

from backtest.batch import is_batch_running
from backtest.cooloff import CoolOffParams, CoolOffTrade, run_cooloff, summarize_cooloff
from backtest.dukascopy import (
    drop_cached_pack,
    fetch_hours_parallel,
    hour_range,
    normalize_duka_symbol,
    parse_ymd,
    reaktor_symbol,
)
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, _parse_range, load_ticks
from backtest.spike_fade_jobs import (
    _assign_slot,
    _idle_lane,
    _job_index,
    _lane_dict,
    _lanes_snapshot,
    _month_chunks,
    _release_slot,
)

_CHUNK_LOOKBACK = timedelta(days=2)


@dataclass
class CoolOffProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    ticks: int = 0
    trades: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    months_done: int = 0
    months_total: int = 0
    lanes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CoolOffJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2026-06-01"
    date_to: str = "2026-07-01"
    invert: bool = False
    min_run: int = 5
    max_tolerance: int = 2
    reverse_frac: float = 0.30
    reverse_min_bars: int = 2
    reverse_max_bars: int = 3
    join_min_bars: int = 2
    join_max_bars: int = 4
    tp_pts: float = 500.0
    sl_pts: float = 500.0
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0
    max_hold_hours: float = 4.0
    cooldown_sec: float = 0.0
    weekend_blackout_min: float = 10.0
    workers: int = 2
    force_download: bool = False


@dataclass
class CoolOffJobState:
    params: CoolOffJobParams = field(default_factory=CoolOffJobParams)
    progress: CoolOffProgress = field(default_factory=CoolOffProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = CoolOffJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
_active_pool: Optional[ProcessPoolExecutor] = None


def get_cooloff_state(*, include_rows: bool = False, row_limit: int = 400) -> Dict[str, Any]:
    with _lock:
        running = _state.running
        params = asdict(_state.params)
        progress = asdict(_state.progress)
        raw = _state.result
        cancel_requested = _cancel.is_set()
    if not raw:
        return {
            "running": running,
            "params": params,
            "progress": progress,
            "result": None,
            "cancel_requested": cancel_requested,
        }
    result = {k: v for k, v in raw.items() if k != "rows"}
    rows = raw.get("rows") or []
    result["row_count"] = len(rows)
    if include_rows:
        result["rows"] = rows[: max(0, int(row_limit))]
        result["rows_truncated"] = len(rows) > len(result["rows"])
    else:
        result["rows"] = []
        result["rows_truncated"] = bool(rows)
    return {
        "running": running,
        "params": params,
        "progress": progress,
        "result": result,
        "cancel_requested": cancel_requested,
    }


def is_cooloff_running() -> bool:
    with _lock:
        return _state.running


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    """Show a saved cool-off JSON in the UI without re-running."""
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Cool-off is running — stop it first"}
        _cancel.clear()
        _state.result = result
        _state.progress = CoolOffProgress(
            phase="done",
            message=f"Loaded {name}" if name else "Loaded saved run",
            pct=100.0,
            ticks=int(result.get("ticks") or 0),
            trades=int(result.get("trades") or 0),
            finished_at=result.get("finished_at"),
            lanes=[],
        )
    return {"ok": True}


def _set_progress(**kwargs: Any) -> None:
    result = kwargs.pop("result", None)
    with _lock:
        for k, v in kwargs.items():
            if v is None:
                continue
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)
        if result is not None:
            _state.result = result


def _busy_others() -> Optional[str]:
    from backtest.jobs import is_job_running
    from backtest.session_jobs import is_session_running
    from backtest.spike_fade_jobs import is_spike_fade_running
    from backtest.overnight_jobs import is_overnight_running
    from backtest.micro_momentum_jobs import is_micro_running

    if is_job_running():
        return "Research job is running"
    if is_batch_running():
        return "Sweep is running"
    if is_session_running():
        return "Session clock is running"
    if is_spike_fade_running():
        return "Spike fade is running"
    if is_overnight_running():
        return "Overnight break is running"
    if is_micro_running():
        return "Micro fade is running"
    return None


def start_cooloff_job(params: CoolOffJobParams) -> Dict[str, Any]:
    global _thread
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Cool-off is already running"}
        err = _busy_others()
        if err:
            return {"ok": False, "error": err}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = CoolOffProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Cool-off started"}


def _force_kill_pool() -> int:
    global _active_pool
    pool = _active_pool
    killed = 0
    if pool is None:
        return 0
    try:
        procs = getattr(pool, "_processes", None) or {}
        for p in list(procs.values()):
            try:
                if p.is_alive():
                    p.terminate()
                    killed += 1
            except Exception:
                pass
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


def stop_cooloff() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "No cool-off running"}
        _cancel.set()
        _set_progress(phase="cancelling", message="Stopping… killing workers")
    n = _force_kill_pool()
    return {
        "ok": True,
        "message": f"Stop sent · terminated {n} worker process(es)",
        "killed": n,
    }


def _params_to_engine(params: CoolOffJobParams) -> CoolOffParams:
    return CoolOffParams(
        invert=bool(params.invert),
        min_run=int(params.min_run),
        max_tolerance=int(params.max_tolerance),
        reverse_frac=float(params.reverse_frac),
        reverse_min_bars=int(params.reverse_min_bars),
        reverse_max_bars=int(params.reverse_max_bars),
        join_min_bars=int(params.join_min_bars),
        join_max_bars=int(params.join_max_bars),
        tp_pts=float(params.tp_pts),
        sl_pts=float(params.sl_pts),
        trail_pts=float(params.trail_pts or 0.0),
        trail_arm_pts=float(params.trail_arm_pts or 0.0),
        max_hold_hours=float(params.max_hold_hours),
        cooldown_sec=float(params.cooldown_sec or 0.0),
        weekend_blackout_min=float(params.weekend_blackout_min or 0.0),
        skip_ignored=True,
    )


def _rows_to_trades(rows: Sequence[dict]) -> List[CoolOffTrade]:
    fields = CoolOffTrade.__dataclass_fields__
    out: List[CoolOffTrade] = []
    for r in rows:
        try:
            out.append(CoolOffTrade(**{k: r[k] for k in fields if k in r}))
        except Exception:
            continue
    return out


def _live_result(
    params: CoolOffJobParams,
    fp: CoolOffParams,
    rows: Sequence[dict],
    total_ticks: int,
    n_m: int,
    *,
    partial: bool,
) -> Dict[str, Any]:
    result = summarize_cooloff(
        _rows_to_trades(rows),
        fp,
        symbol=reaktor_symbol(params.symbol),
        ticks=total_ticks,
        partial=partial,
    )
    result["date_from"] = params.date_from
    result["date_to"] = params.date_to
    result["months"] = n_m
    return result


def _prepend_lookback(ticks: List, date_from: str, symbol: str, force: bool, progress) -> List:
    utc_from = parse_ymd(date_from)
    start = utc_from - _CHUNK_LOOKBACK
    if start >= utc_from:
        return ticks
    hours = hour_range(start, utc_from)
    if not hours:
        return ticks
    prefix = fetch_hours_parallel(
        symbol,
        hours,
        cache_dir=DEFAULT_CACHE,
        force=force,
        progress=progress,
    )
    prefix = [t for t in prefix if t.ts < utc_from]
    prefix.sort(key=lambda t: t.ts)
    if not prefix:
        return ticks
    return prefix + list(ticks)


def _in_entry_window(row: dict, a: str, b: str) -> bool:
    ts = str(row.get("entry_ts") or "")
    if len(ts) < 10:
        return False
    day = ts[:10]
    return a <= day < b


def _run_month_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    fp = CoolOffParams(**payload["cooloff_params"])
    q = payload.get("progress_q")
    idx = _job_index(payload, 0)

    def emit(event: str, **kw: Any) -> None:
        if q is None:
            return
        try:
            ev: Dict[str, Any] = {
                "event": event,
                "index": idx,
                "date_from": a,
                "date_to": b,
            }
            ev.update(kw)
            q.put(ev)
        except Exception:
            pass

    def load_prog(**kw: Any) -> None:
        emit(
            "load",
            message=str(kw.get("message") or "load pack"),
            ticks_done=int(kw.get("ticks") or 0),
            ticks_total=0,
            pct=kw.get("pct"),
        )

    def walk_prog(**kw: Any) -> None:
        emit(
            "scan",
            ticks_done=int(kw.get("ticks_done") or 0),
            ticks_total=int(kw.get("ticks_total") or 0),
            trades=int(kw.get("trades") or 0),
        )

    try:
        emit("load", message="load pack…")
        ticks = load_ticks(
            symbol=symbol,
            date_from=a,
            date_to=b,
            force_download=force,
            progress=load_prog,
        )
        ticks = _prepend_lookback(ticks, a, symbol, force, load_prog)
        part = run_cooloff(
            ticks,
            symbol=symbol,
            params=fp,
            progress=walk_prog,
            entry_from=parse_ymd(a),
            entry_to=parse_ymd(b),
        )
        n_ticks = len(ticks)
        rows = [r for r in (part.get("rows") or []) if _in_entry_window(r, a, b)]
        del ticks
        gc.collect()
        start, end = _parse_range(a, b)
        drop_cached_pack(normalize_duka_symbol(symbol), start, end)
        return {
            "ok": True,
            "index": idx,
            "date_from": a,
            "date_to": b,
            "ticks": n_ticks,
            "rows": rows,
            "error": None,
        }
    except Exception as e:
        return {
            "ok": False,
            "index": idx,
            "date_from": a,
            "date_to": b,
            "ticks": 0,
            "rows": [],
            "error": f"{a}→{b}: {e}",
        }


def _run(params: CoolOffJobParams) -> None:
    global _active_pool
    try:
        chunks = _month_chunks(params.date_from, params.date_to)
        if not chunks:
            raise RuntimeError("Empty date range")
        n_m = len(chunks)
        fp = _params_to_engine(params)
        all_rows: List[dict] = []
        total_ticks = 0
        completed = 0
        workers = max(1, min(6, int(params.workers or 1)))
        engine_params = asdict(fp)
        duka = normalize_duka_symbol(params.symbol)

        if workers <= 1 or n_m <= 1:
            for i, (a, b) in enumerate(chunks):
                if _cancel.is_set():
                    break
                base = 100.0 * i / n_m
                span = 100.0 / n_m
                label = f"Month {i + 1}/{n_m}  {a} → {b}"
                _set_progress(
                    phase="download",
                    message=f"{label} · load pack…",
                    pct=round(base, 1),
                    trades=len(all_rows),
                    ticks=total_ticks,
                    months_done=i,
                    months_total=n_m,
                    lanes=[
                        _lane_dict(
                            0,
                            {
                                "event": "load",
                                "index": i,
                                "date_from": a,
                                "date_to": b,
                                "message": "load pack…",
                            },
                        )
                    ],
                )

                def load_prog(label=label, base=base, span=span, a=a, b=b, i=i, **kw: Any) -> None:
                    lp = float(kw.get("pct") or 0.0)
                    _set_progress(
                        phase="download",
                        message=f"{label} · {kw.get('message') or 'load'}",
                        pct=round(base + span * 0.40 * min(lp, 50.0) / 50.0, 1),
                        ticks=int(kw.get("ticks") or 0) + total_ticks,
                        trades=len(all_rows),
                        months_done=i,
                        months_total=n_m,
                        lanes=[
                            _lane_dict(
                                0,
                                {
                                    "event": "load",
                                    "index": i,
                                    "date_from": a,
                                    "date_to": b,
                                    "message": kw.get("message") or "load pack",
                                    "ticks_done": int(kw.get("ticks") or 0),
                                    "pct": lp,
                                },
                            )
                        ],
                    )

                ticks = load_ticks(
                    symbol=params.symbol,
                    date_from=a,
                    date_to=b,
                    force_download=params.force_download,
                    progress=load_prog,
                )
                ticks = _prepend_lookback(
                    ticks, a, params.symbol, params.force_download, load_prog
                )
                month_n = len(ticks)
                total_ticks += month_n

                def walk_prog(
                    label=label,
                    base=base,
                    span=span,
                    a=a,
                    b=b,
                    i=i,
                    **kw: Any,
                ) -> None:
                    done = int(kw.get("ticks_done") or 0)
                    tot = max(int(kw.get("ticks_total") or 1), 1)
                    frac = done / tot
                    n_tr = len(all_rows) + int(kw.get("trades") or 0)
                    _set_progress(
                        phase="replay",
                        message=f"{label} · scan {done:,}/{tot:,} · {n_tr} trades",
                        pct=round(base + span * (0.40 + 0.55 * frac), 1),
                        ticks=total_ticks - month_n + done,
                        trades=n_tr,
                        months_done=i,
                        months_total=n_m,
                        lanes=[
                            _lane_dict(
                                0,
                                {
                                    "event": "scan",
                                    "index": i,
                                    "date_from": a,
                                    "date_to": b,
                                    "ticks_done": done,
                                    "ticks_total": tot,
                                    "trades": int(kw.get("trades") or 0),
                                },
                            )
                        ],
                    )

                part = run_cooloff(
                    ticks,
                    symbol=params.symbol,
                    params=fp,
                    progress=walk_prog,
                    entry_from=parse_ymd(a),
                    entry_to=parse_ymd(b),
                )
                all_rows.extend(
                    r for r in (part.get("rows") or []) if _in_entry_window(r, a, b)
                )
                completed += 1
                start, end = _parse_range(a, b)
                drop_cached_pack(duka, start, end)
                del ticks
                del part
                gc.collect()
        else:
            import multiprocessing as mp

            ctx = mp.get_context("spawn")
            manager = ctx.Manager()
            progress_q = manager.Queue()
            payloads = []
            for i, (a, b) in enumerate(chunks):
                payloads.append(
                    {
                        "index": i,
                        "date_from": a,
                        "date_to": b,
                        "symbol": params.symbol,
                        "force_download": params.force_download,
                        "cooloff_params": engine_params,
                        "progress_q": progress_q,
                    }
                )
            live: Dict[int, Dict[str, Any]] = {}
            finished: set = set()
            slot_of: Dict[int, int] = {}
            completed = 0
            errors: List[str] = []

            for i, (a, b) in enumerate(chunks[:workers]):
                live[i] = {
                    "event": "load",
                    "index": i,
                    "date_from": a,
                    "date_to": b,
                    "message": "starting…",
                    "ticks_done": 0,
                    "ticks_total": 0,
                }
                _assign_slot(i, workers, slot_of)

            def drain_q() -> None:
                while True:
                    try:
                        ev = progress_q.get_nowait()
                    except Empty:
                        break
                    except Exception:
                        break
                    if not ev or ev.get("event") not in ("scan", "load"):
                        continue
                    i = _job_index(ev, -1)
                    if i < 0 or i in finished:
                        continue
                    live[i] = ev

            def publish() -> None:
                in_frac = 0.0
                for ev in live.values():
                    if ev.get("event") == "load":
                        p = ev.get("pct")
                        in_frac += min(0.4, float(p) / 125.0) if p is not None else 0.05
                    else:
                        tot = max(int(ev.get("ticks_total") or 0), 1)
                        in_frac += min(1.0, int(ev.get("ticks_done") or 0) / tot)
                overall = 100.0 * (completed + in_frac) / n_m
                lanes = _lanes_snapshot(workers, live, slot_of)
                snap = _live_result(
                    params, fp, all_rows, total_ticks, n_m, partial=True
                )
                _set_progress(
                    phase="replay",
                    message=(
                        f"{workers} workers · {completed}/{n_m} months · "
                        f"{len(all_rows)} trades"
                    ),
                    pct=round(min(96.0, overall), 1),
                    ticks=total_ticks,
                    trades=len(all_rows),
                    months_done=completed,
                    months_total=n_m,
                    lanes=lanes,
                    result=snap,
                )

            _set_progress(
                phase="replay",
                message=f"{workers} workers · 0/{n_m} months…",
                pct=1.0,
                months_done=0,
                months_total=n_m,
                lanes=_lanes_snapshot(workers, live, slot_of),
            )
            pool = ProcessPoolExecutor(max_workers=workers, mp_context=ctx)
            _active_pool = pool
            try:
                futs = {pool.submit(_run_month_job, p): p for p in payloads}
                pending = set(futs)
                while pending:
                    if _cancel.is_set():
                        _set_progress(
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
                    drain_q()
                    publish()
                    try:
                        done, pending = wait(
                            pending, timeout=0.4, return_when=FIRST_COMPLETED
                        )
                    except Exception:
                        if _cancel.is_set():
                            break
                        raise
                    for fut in done:
                        if _cancel.is_set() or fut.cancelled():
                            continue
                        try:
                            out = fut.result(timeout=0.1)
                        except (BrokenProcessPool, Exception) as e:
                            if _cancel.is_set():
                                continue
                            errors.append(str(e))
                            continue
                        completed += 1
                        total_ticks += int(out.get("ticks") or 0)
                        all_rows.extend(out.get("rows") or [])
                        idx = _job_index(out, -1)
                        if idx >= 0:
                            finished.add(idx)
                            live.pop(idx, None)
                            _release_slot(idx, slot_of)
                        if not out.get("ok") and out.get("error"):
                            errors.append(str(out["error"]))
                    drain_q()
                    publish()
            except Exception as e:
                if not _cancel.is_set():
                    raise
                _set_progress(message=f"Stopped (workers killed) · {e}")
            finally:
                _force_kill_pool()
                try:
                    manager.shutdown()
                except Exception:
                    pass
            if errors and not _cancel.is_set():
                _set_progress(
                    phase="replay",
                    message="Some months failed: " + "; ".join(errors)[:240],
                )

        result = _live_result(params, fp, all_rows, total_ticks, n_m, partial=False)
        cancelled = _cancel.is_set()
        result["cancelled"] = cancelled
        result["finished_at"] = datetime.now(timezone.utc).isoformat()

        _set_progress(
            phase="save",
            message=f"Saving {result.get('trades') or 0} trades…",
            pct=98.0 if not cancelled else None,
            ticks=total_ticks,
            trades=result.get("trades") or 0,
            months_done=completed,
            months_total=n_m,
            lanes=[],
            result=result,
        )
        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        tag = f"cooloff_{params.symbol}_{params.date_from}_{params.date_to}"
        path = DEFAULT_RESULTS / f"{tag}.json"
        path.write_text(json.dumps(result, default=str, separators=(",", ":")))
        result["saved_to"] = str(path)

        with _lock:
            _state.result = result
        if cancelled:
            _set_progress(
                phase="cancelled",
                message=f"Stopped · {result.get('trades') or 0} trades",
                ticks=total_ticks,
                trades=result.get("trades") or 0,
                finished_at=datetime.now(timezone.utc).isoformat(),
                lanes=[],
            )
        else:
            _set_progress(
                phase="done",
                message=f"Done · {n_m} months · {result.get('trades')} trades",
                pct=100.0,
                ticks=total_ticks,
                trades=result.get("trades") or 0,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        if _cancel.is_set():
            _set_progress(
                phase="cancelled",
                message="Stopped",
                finished_at=datetime.now(timezone.utc).isoformat(),
                lanes=[],
            )
        else:
            _set_progress(
                phase="error",
                message=str(e),
                error=traceback.format_exc(),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
    finally:
        _force_kill_pool()
        with _lock:
            _state.running = False
