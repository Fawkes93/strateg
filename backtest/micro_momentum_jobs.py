"""Background job for the Micro fade tab (month-chunked, live summaries)."""

from __future__ import annotations

import gc
import json
import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from queue import Empty
from typing import Any, Dict, List, Optional, Sequence

from backtest.batch import is_batch_running
from backtest.dukascopy import drop_cached_pack, normalize_duka_symbol, reaktor_symbol
from backtest.micro_momentum import BurstParams, BurstTrade, run_micro_momentum, summarize_burst
from backtest.runner import DEFAULT_RESULTS, _parse_range, load_ticks, unique_result_path
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.spike_fade_jobs import (
    _assign_slot,
    _idle_lane,
    _job_index,
    _lane_dict,
    _lanes_snapshot,
    _month_chunks,
    _release_slot,
)


@dataclass
class MicroProgress:
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
class MicroJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2026-03-02"
    date_to: str = "2026-03-09"
    window_sec: float = 4.0
    min_burst_pts: float = 100.0
    max_burst_pts: float = 400.0
    persist_frac: float = 0.35
    use_1m: bool = True
    min_1m_body: float = 40.0
    tp_pts: float = 100.0
    sl_pts: float = 80.0
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0
    max_hold_sec: float = 45.0
    cooldown_sec: float = 15.0
    weekend_blackout_min: float = 10.0
    lag_sec: float = 0.5
    session: str = "all"
    max_spread_pts: float = 50.0
    mode: str = "with"
    confirm_pts: float = 0.0
    confirm_timeout_sec: float = 3.0
    pause_sec: float = 1.0
    pause_give_up_sec: float = 8.0
    tp_frac: float = 0.0
    tp_cap_pts: float = 0.0
    sl_extra_pts: float = 0.0
    rr_one_to_one: bool = False
    sl_mult: float = 1.0
    trail_frac: float = 0.0
    max_spread_vs_tp: float = 0.4
    be_asap: bool = False
    be_asap_pts: float = 1.0
    workers: int = 2
    force_download: bool = False


@dataclass
class MicroJobState:
    params: MicroJobParams = field(default_factory=MicroJobParams)
    progress: MicroProgress = field(default_factory=MicroProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = MicroJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
_active_pool: Optional[ProcessPoolExecutor] = None


def get_micro_state(*, include_rows: bool = False, row_limit: int = 400) -> Dict[str, Any]:
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
    result["row_count"] = int(raw.get("row_count") or len(rows))
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


def is_micro_running() -> bool:
    with _lock:
        return _state.running


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    """Show a saved micro fade/burst JSON in the UI without re-running."""
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Micro fade is running — stop it first"}
        _cancel.clear()
        _state.result = retain_result(result)
        _state.progress = MicroProgress(
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
    from backtest.cooloff_jobs import is_cooloff_running

    if is_cooloff_running():
        return "Cool-off is running"
    return None


def start_micro_job(params: MicroJobParams) -> Dict[str, Any]:
    global _thread
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Micro fade is already running"}
        err = _busy_others()
        if err:
            return {"ok": False, "error": err}

        from backtest.fvg_jobs import is_fvg_running

        if is_fvg_running():
            return {"ok": False, "error": "IFVG is running"}
        from backtest.asia_liquidity_jobs import is_asia_liq_running

        if is_asia_liq_running():
            return {"ok": False, "error": "Asia liquidity is running"}
        from backtest.impulse_fork_jobs import is_fork_running

        if is_fork_running():
            return {"ok": False, "error": "Impulse fork is running"}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = MicroProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Micro fade started"}


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


def stop_micro() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "No micro fade running"}
        _cancel.set()
        _set_progress(phase="cancelling", message="Stopping… killing workers")
    n = _force_kill_pool()
    return {
        "ok": True,
        "message": f"Stop sent · terminated {n} worker process(es)",
        "killed": n,
    }


def _params_to_burst(params: MicroJobParams) -> BurstParams:
    return BurstParams(
        window_sec=float(params.window_sec),
        min_burst_pts=float(params.min_burst_pts),
        max_burst_pts=float(params.max_burst_pts),
        persist_frac=float(params.persist_frac),
        use_1m=bool(params.use_1m),
        min_1m_body=float(params.min_1m_body),
        tp_pts=float(params.tp_pts),
        sl_pts=float(params.sl_pts),
        trail_pts=float(params.trail_pts or 0.0),
        trail_arm_pts=float(params.trail_arm_pts or 0.0),
        max_hold_sec=float(params.max_hold_sec),
        cooldown_sec=float(params.cooldown_sec),
        weekend_blackout_min=float(params.weekend_blackout_min),
        lag_sec=float(params.lag_sec or 0.0),
        session=str(params.session or "all"),
        max_spread_pts=float(params.max_spread_pts or 0.0),
        mode=str(params.mode or "with"),
        confirm_pts=float(params.confirm_pts or 0.0),
        confirm_timeout_sec=float(params.confirm_timeout_sec or 3.0),
        pause_sec=float(params.pause_sec or 0.0),
        pause_give_up_sec=float(params.pause_give_up_sec or 8.0),
        tp_frac=float(params.tp_frac or 0.0),
        tp_cap_pts=float(params.tp_cap_pts or 0.0),
        sl_extra_pts=float(params.sl_extra_pts or 0.0),
        rr_one_to_one=bool(params.rr_one_to_one),
        sl_mult=float(params.sl_mult or 1.0),
        trail_frac=float(params.trail_frac or 0.0),
        max_spread_vs_tp=float(params.max_spread_vs_tp or 0.0),
        be_asap=bool(params.be_asap),
        be_asap_pts=float(params.be_asap_pts or 0.0),
    )


def _rows_to_trades(rows: Sequence[dict]) -> List[BurstTrade]:
    fields = BurstTrade.__dataclass_fields__
    out: List[BurstTrade] = []
    for r in rows:
        try:
            out.append(BurstTrade(**{k: r[k] for k in fields if k in r}))
        except Exception:
            continue
    return out


def _live_result(
    params: MicroJobParams,
    fp: BurstParams,
    rows: Sequence[dict],
    total_ticks: int,
    n_m: int,
    *,
    partial: bool,
) -> Dict[str, Any]:
    result = summarize_burst(
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


def _run_month_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    fp = BurstParams(**payload["burst_params"])
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
        part = run_micro_momentum(ticks, symbol=symbol, params=fp, progress=walk_prog)
        n_ticks = len(ticks)
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
            "rows": part.get("rows") or [],
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


def _run(params: MicroJobParams) -> None:
    global _active_pool
    try:
        chunks = _month_chunks(params.date_from, params.date_to)
        if not chunks:
            raise RuntimeError("Empty date range")
        n_m = len(chunks)
        fp = _params_to_burst(params)
        all_rows: List[dict] = []
        total_ticks = 0
        completed = 0
        workers = max(1, min(6, int(params.workers or 1)))
        burst_params = asdict(fp)
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
                    month_rows = kw.get("rows") or []
                    live = all_rows + list(month_rows)
                    n_tr = len(live)
                    snap = _live_result(
                        params, fp, live, total_ticks - month_n + done, n_m, partial=True
                    )
                    _set_progress(
                        phase="replay",
                        message=(
                            f"{label} · scan {done:,}/{tot:,} · {n_tr} trades"
                        ),
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
                                    "trades": n_tr,
                                },
                            )
                        ],
                        result=snap,
                    )

                part = run_micro_momentum(
                    ticks, symbol=params.symbol, params=fp, progress=walk_prog
                )
                all_rows.extend(part.get("rows") or [])
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
                        "burst_params": burst_params,
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

        result = _live_result(
            params, fp, all_rows, total_ticks, n_m, partial=False
        )
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
        tag = f"micro_{params.symbol}_{params.date_from}_{params.date_to}"
        path, run_id = unique_result_path(tag)
        result["run_id"] = run_id
        path.write_text(json.dumps(result, default=str, separators=(",", ":")))
        result["saved_to"] = str(path)

        with _lock:
            _state.result = retain_result(result)
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
        try:
            release_job_memory()
        except Exception:
            pass
        with _lock:
            slim_state_result_inplace(_state)
            _state.running = False
