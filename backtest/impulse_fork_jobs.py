"""Background job for the Impulse fork tab."""

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
from typing import Any, Dict, List, Optional, Tuple

from backtest.batch import is_batch_running
from backtest.dukascopy import (
    drop_cached_pack,
    fetch_hours_parallel,
    hour_range,
    normalize_duka_symbol,
    parse_ymd,
    reaktor_symbol,
)
from backtest.impulse_fork import ForkParams, ForkSkip, ForkTrade, run_impulse_fork, summarize_fork
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, _parse_range, load_ticks, unique_result_path

_CHUNK_LOOKBACK = timedelta(hours=2)


@dataclass
class ForkProgress:
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
class ForkJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2026-06-01"
    date_to: str = "2026-07-01"
    window_sec: float = 3.0
    min_blast_pts: float = 1100.0
    snap_pts: float = 300.0
    snap_sec: float = 10.0
    join_retrace: float = 0.50
    join_wait_sec: float = 90.0
    chase_ext: float = 0.50
    fade_lag_sec: float = 1.0
    fade_sl_pct: float = 100.0
    fade_sl_cap_pts: float = 1500.0
    fade_tp_pct: float = 200.0
    fade_tp_cap_pts: float = 3000.0
    fade_trail_pts: float = 600.0
    fade_trail_arm_pts: float = 750.0
    fade_hold_sec: float = 250.0
    join_stop_beyond: float = 0.15
    join_tp1_r: float = 1.0
    join_tp2_r: float = 1.5
    join_be_r: float = 0.1
    join_hold_sec: float = 1200.0
    cooldown_sec: float = 30.0
    weekend_blackout_min: float = 10.0
    stand_aside_n: int = 3
    skip_london_utc: bool = True
    london_start_hour: int = 7
    london_end_hour: int = 10
    fade_enabled: bool = True
    join_enabled: bool = True
    stand_aside_enabled: bool = True
    risk_pct: float = 0.5
    start_equity: float = 1_000.0
    daily_halt_r: float = 1.5
    weekly_halt_r: float = 4.0
    workers: int = 3
    force_download: bool = False


@dataclass
class ForkJobState:
    params: ForkJobParams = field(default_factory=ForkJobParams)
    progress: ForkProgress = field(default_factory=ForkProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = ForkJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
_active_pool: Optional[ProcessPoolExecutor] = None


def get_fork_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
            "cancel_requested": _cancel.is_set(),
        }


def is_fork_running() -> bool:
    with _lock:
        return _state.running


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Impulse fork is running — stop it first"}
        _cancel.clear()
        _state.result = retain_result(result)
        _state.progress = ForkProgress(
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
    with _lock:
        for k, v in kwargs.items():
            if v is None:
                continue
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


def _busy_others() -> Optional[str]:
    from backtest.jobs import is_job_running
    from backtest.session_jobs import is_session_running
    from backtest.spike_fade_jobs import is_spike_fade_running
    from backtest.overnight_jobs import is_overnight_running
    from backtest.micro_momentum_jobs import is_micro_running
    from backtest.cooloff_jobs import is_cooloff_running
    from backtest.fvg_jobs import is_fvg_running
    from backtest.asia_liquidity_jobs import is_asia_liq_running

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
    if is_cooloff_running():
        return "Cool-off is running"
    if is_fvg_running():
        return "IFVG is running"
    if is_asia_liq_running():
        return "Asia liquidity is running"
    return None


def start_fork_job(params: ForkJobParams) -> Dict[str, Any]:
    global _thread
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Impulse fork is already running"}
        err = _busy_others()
        if err:
            return {"ok": False, "error": err}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = ForkProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Impulse fork started"}


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


def stop_fork() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "No Impulse fork run"}
        _cancel.set()
        _set_progress(phase="cancelling", message="Stopping… killing workers")
    n = _force_kill_pool()
    return {"ok": True, "message": f"Stop sent · terminated {n} worker process(es)", "killed": n}


def params_to_engine(params: ForkJobParams) -> ForkParams:
    raw = asdict(params)
    fields = ForkParams.__dataclass_fields__
    return ForkParams(**{k: raw[k] for k in fields if k in raw})


def _month_chunks(date_from: str, date_to: str) -> List[Tuple[str, str]]:
    d0 = datetime.strptime(date_from, "%Y-%m-%d").date()
    d1 = datetime.strptime(date_to, "%Y-%m-%d").date()
    out: List[Tuple[str, str]] = []
    cur = d0
    while cur < d1:
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1, day=1)
        else:
            nxt = cur.replace(month=cur.month + 1, day=1)
        if nxt > d1:
            nxt = d1
        out.append((cur.isoformat(), nxt.isoformat()))
        cur = nxt
    return out


def _date_key(row: Dict[str, Any]) -> str:
    s = str(row.get("entry_ts") or row.get("ts") or "")
    return s[:10]


def _rows_to_trades(rows: List[Dict[str, Any]]) -> List[ForkTrade]:
    fields = ForkTrade.__dataclass_fields__
    out: List[ForkTrade] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            out.append(ForkTrade(**{k: r[k] for k in fields if k in r}))
        except TypeError:
            continue
    return out


def _rows_to_skips(rows: List[Dict[str, Any]]) -> List[ForkSkip]:
    fields = ForkSkip.__dataclass_fields__
    out: List[ForkSkip] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            out.append(ForkSkip(**{k: r[k] for k in fields if k in r}))
        except TypeError:
            continue
    return out


def _job_index(d: Dict[str, Any], default: int = -1) -> int:
    if "index" not in d or d["index"] is None:
        return default
    return int(d["index"])


def _prepend_lookback(ticks: List, params: ForkJobParams, progress) -> List:
    utc_from = parse_ymd(params.date_from)
    start = utc_from - _CHUNK_LOOKBACK
    if start >= utc_from:
        return ticks
    hours = hour_range(start, utc_from)
    if not hours:
        return ticks
    prefix = fetch_hours_parallel(
        params.symbol,
        hours,
        cache_dir=DEFAULT_CACHE,
        force=params.force_download,
        progress=progress,
    )
    prefix = [t for t in prefix if t.ts < utc_from]
    prefix.sort(key=lambda t: t.ts)
    return (prefix + list(ticks)) if prefix else ticks


def _run_month_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    op = ForkParams(**payload["op"])
    q = payload.get("progress_q")
    idx = _job_index(payload, 0)

    def emit(event: str, **kw: Any) -> None:
        if q is None:
            return
        try:
            ev = {"event": event, "index": idx, "date_from": a, "date_to": b}
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
            message=str(kw.get("message") or "scan"),
        )

    try:
        emit("load", message="load pack…")
        ticks = load_ticks(
            symbol=symbol, date_from=a, date_to=b, force_download=force, progress=load_prog
        )
        chunk = ForkJobParams(symbol=symbol, date_from=a, date_to=b, force_download=force)
        ticks = _prepend_lookback(ticks, chunk, load_prog)
        raw = run_impulse_fork(ticks, symbol=symbol, params=op, progress=walk_prog)
        n_ticks = len(ticks)
        trade_rows = [r for r in (raw.get("rows") or []) if a <= _date_key(r) < b]
        skip_rows = [r for r in (raw.get("skips") or []) if a <= _date_key(r) < b]
        del ticks
        del raw
        gc.collect()
        start, end = _parse_range(a, b)
        drop_cached_pack(normalize_duka_symbol(symbol), start, end)
        return {
            "ok": True,
            "index": idx,
            "date_from": a,
            "date_to": b,
            "ticks": n_ticks,
            "rows": trade_rows,
            "skips": skip_rows,
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
            "skips": [],
            "error": f"{a}→{b}: {e}",
        }


class _CallbackQueue:
    def __init__(self, cb):
        self._cb = cb

    def put(self, item, block=True, timeout=None):
        try:
            self._cb(item)
        except Exception:
            pass


def _run(params: ForkJobParams) -> None:
    global _active_pool
    try:
        op = params_to_engine(params)
        chunks = _month_chunks(params.date_from, params.date_to)
        if not chunks:
            raise RuntimeError("Empty date range")
        n_m = len(chunks)
        workers = max(1, min(6, int(params.workers or 1)))
        op_dict = asdict(op)
        all_trades: List[ForkTrade] = []
        all_skips: List[ForkSkip] = []
        total_ticks = 0
        completed = 0
        errors: List[str] = []

        def ingest(out: Dict[str, Any]) -> None:
            nonlocal total_ticks, completed
            completed += 1
            total_ticks += int(out.get("ticks") or 0)
            all_trades.extend(_rows_to_trades(out.get("rows") or []))
            all_skips.extend(_rows_to_skips(out.get("skips") or []))
            if not out.get("ok") and out.get("error"):
                errors.append(str(out["error"]))

        if workers <= 1 or n_m <= 1:
            for i, (a, b) in enumerate(chunks):
                if _cancel.is_set():
                    break
                label = f"Month {i + 1}/{n_m}  {a} → {b}"
                base = 5.0 + 90.0 * i / n_m
                span = 90.0 / n_m

                def on_put(ev, i=i, label=label, base=base, span=span):
                    kind = ev.get("event") or "load"
                    tot = max(int(ev.get("ticks_total") or 1), 1)
                    frac = 0.4 * min(float(ev.get("pct") or 0), 50) / 50.0 if kind == "load" else 0.4 + 0.55 * int(ev.get("ticks_done") or 0) / tot
                    _set_progress(
                        phase="replay" if kind == "scan" else "download",
                        message=f"{label} · {ev.get('message') or kind}",
                        pct=round(min(94.0, base + span * frac), 1),
                        ticks=total_ticks + int(ev.get("ticks_done") or 0),
                        trades=len(all_trades) + int(ev.get("trades") or 0),
                        months_done=i,
                        months_total=n_m,
                    )

                _set_progress(phase="download", message=f"{label} · load pack…", pct=round(base, 1))
                out = _run_month_job(
                    {
                        "index": i,
                        "date_from": a,
                        "date_to": b,
                        "symbol": params.symbol,
                        "force_download": params.force_download,
                        "op": op_dict,
                        "progress_q": _CallbackQueue(on_put),
                    }
                )
                ingest(out)
        else:
            import multiprocessing as mp

            ctx = mp.get_context("spawn")
            manager = ctx.Manager()
            progress_q = manager.Queue()
            payloads = [
                {
                    "index": i,
                    "date_from": a,
                    "date_to": b,
                    "symbol": params.symbol,
                    "force_download": params.force_download,
                    "op": op_dict,
                    "progress_q": progress_q,
                }
                for i, (a, b) in enumerate(chunks)
            ]
            pool = ProcessPoolExecutor(max_workers=workers, mp_context=ctx)
            _active_pool = pool
            try:
                futs = {pool.submit(_run_month_job, p): p for p in payloads}
                pending = set(futs)
                while pending:
                    if _cancel.is_set():
                        for f in pending:
                            try:
                                f.cancel()
                            except Exception:
                                pass
                        _force_kill_pool()
                        break
                    try:
                        done, pending = wait(pending, timeout=0.4, return_when=FIRST_COMPLETED)
                    except Exception:
                        if _cancel.is_set():
                            break
                        raise
                    while True:
                        try:
                            ev = progress_q.get_nowait()
                        except Empty:
                            break
                        except Exception:
                            break
                        _set_progress(
                            message=str(ev.get("message") or ""),
                            ticks=int(ev.get("ticks_done") or 0),
                            trades=len(all_trades) + int(ev.get("trades") or 0),
                            pct=round(min(96.0, 100.0 * completed / n_m), 1),
                            months_done=completed,
                            months_total=n_m,
                        )
                    for fut in done:
                        if _cancel.is_set() or fut.cancelled():
                            continue
                        try:
                            ingest(fut.result(timeout=0.1))
                        except (BrokenProcessPool, Exception) as e:
                            if not _cancel.is_set():
                                errors.append(str(e))
                                completed += 1
                    _set_progress(
                        phase="replay",
                        message=f"{workers} workers · {completed}/{n_m} months · {len(all_trades)} trades",
                        pct=round(min(96.0, 100.0 * completed / n_m), 1),
                        ticks=total_ticks,
                        trades=len(all_trades),
                        months_done=completed,
                        months_total=n_m,
                    )
            finally:
                _force_kill_pool()
                try:
                    manager.shutdown()
                except Exception:
                    pass

        cancelled = _cancel.is_set()
        all_trades.sort(key=lambda t: t.entry_ts)
        result = summarize_fork(
            all_trades, all_skips, op, symbol=reaktor_symbol(params.symbol), ticks=total_ticks
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["months"] = n_m
        result["cancelled"] = cancelled
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        if errors:
            result["month_errors"] = errors
        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        tag = f"fork_{params.symbol}_{params.date_from}_{params.date_to}"
        path, run_id = unique_result_path(tag)
        result["run_id"] = run_id
        path.write_text(json.dumps(result, indent=2, default=str))
        result["saved_to"] = str(path)
        with _lock:
            _state.result = retain_result(result)
        _set_progress(
            phase="cancelled" if cancelled else "done",
            message=(
                f"{'Stopped' if cancelled else 'Done'} · {result.get('trades')} trades · "
                f"{result.get('skipped')} skipped"
            ),
            pct=100.0 if not cancelled else None,
            ticks=total_ticks,
            trades=result.get("trades") or 0,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        _set_progress(
            phase="error",
            message=str(e),
            error=traceback.format_exc(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        _force_kill_pool()
        try:
            release_job_memory()
        except Exception:
            pass
        with _lock:
            slim_state_result_inplace(_state)
            _state.running = False
