"""Background job for the Spike fade tab."""

from __future__ import annotations

import gc
import json
import threading
import time
import traceback
from queue import Empty
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backtest.batch import is_batch_running
from backtest.dukascopy import drop_cached_pack, normalize_duka_symbol, reaktor_symbol
from backtest.runner import DEFAULT_RESULTS, _parse_range, load_ticks
from backtest.spike_fade import FadeParams, FadeTrade, run_spike_fade, summarize_fade


@dataclass
class SpikeFadeProgress:
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
class SpikeFadeJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-06-01"
    window_sec: float = 3.0
    min_spike_pts: float = 2000.0
    tp_pts: float = 2000.0
    sl_pts: float = 2000.0
    tp_pct: float = 100.0
    sl_pct: float = 100.0
    trail_pts: float = 1000.0
    max_hold_sec: float = 120.0
    cooldown_sec: float = 30.0
    weekend_blackout_min: float = 10.0
    lag_sec: float = 0.0
    workers: int = 3
    force_download: bool = False


@dataclass
class SpikeFadeJobState:
    params: SpikeFadeJobParams = field(default_factory=SpikeFadeJobParams)
    progress: SpikeFadeProgress = field(default_factory=SpikeFadeProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = SpikeFadeJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
_active_pool: Optional[ProcessPoolExecutor] = None


def get_spike_fade_state(*, include_rows: bool = False, row_limit: int = 300) -> Dict[str, Any]:
    """Status payload. Full trade list is huge — omit unless asked."""
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


def is_spike_fade_running() -> bool:
    with _lock:
        return _state.running


def _set_progress(**kwargs: Any) -> None:
    with _lock:
        for k, v in kwargs.items():
            if v is None:
                continue
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


def start_spike_fade_job(params: SpikeFadeJobParams) -> Dict[str, Any]:
    global _thread
    from backtest.jobs import is_job_running
    from backtest.session_jobs import is_session_running

    with _lock:
        if _state.running:
            return {"ok": False, "error": "Spike fade is already running"}
        if is_job_running():
            return {"ok": False, "error": "Research job is running"}
        if is_batch_running():
            return {"ok": False, "error": "Sweep is running"}
        if is_session_running():
            return {"ok": False, "error": "Session clock is running"}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = SpikeFadeProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Spike fade started"}


def _force_kill_pool() -> int:
    """Hard-kill month workers so RAM is freed immediately."""
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


def stop_spike_fade() -> Dict[str, Any]:
    """Stop now: set cancel flag and kill worker processes."""
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "No spike fade running"}
        _cancel.set()
        _set_progress(
            phase="cancelling",
            message="Stopping… killing workers",
        )
    n = _force_kill_pool()
    return {
        "ok": True,
        "message": f"Stop sent · terminated {n} worker process(es)",
        "killed": n,
    }


def _month_chunks(date_from: str, date_to: str) -> List[Tuple[str, str]]:
    """Split [from, to) into calendar months so we never hold a year of ticks."""
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


def _job_index(d: Dict[str, Any], default: int = -1) -> int:
    """Month index. 0 is valid — never use `value or default`."""
    if "index" not in d or d["index"] is None:
        return default
    return int(d["index"])


def _assign_slot(month_i: int, n_workers: int, slot_of: Dict[int, int]) -> int:
    """Keep a month on the same visual worker lane until it finishes."""
    if month_i in slot_of:
        return slot_of[month_i]
    used = set(slot_of.values())
    for s in range(max(1, n_workers)):
        if s not in used:
            slot_of[month_i] = s
            return s
    slot_of[month_i] = month_i % max(1, n_workers)
    return slot_of[month_i]


def _release_slot(month_i: int, slot_of: Dict[int, int]) -> None:
    slot_of.pop(month_i, None)


def _lane_dict(slot: int, ev: Dict[str, Any]) -> Dict[str, Any]:
    kind = ev.get("event") or "load"
    tot = int(ev.get("ticks_total") or 0)
    done = int(ev.get("ticks_done") or 0)
    trades = int(ev.get("trades") or 0)
    if kind == "load":
        p = ev.get("pct")
        if p is not None:
            pct = max(3.0, min(38.0, float(p) * 0.76))
        elif done:
            pct = 16.0
        else:
            pct = 6.0
        msg = str(ev.get("message") or "load pack")
        if "Unpack" in msg and done:
            detail = f"unpack {done // 1000}k"
        elif done:
            detail = f"load {done // 1000}k"
        else:
            detail = "loading pack"
        phase = "load"
    else:
        pct = 40.0 + 60.0 * (done / tot) if tot > 0 else 42.0
        detail = f"{done // 1000}k / {tot // 1000}k" if tot > 0 else "scanning…"
        phase = "scan"
    return {
        "slot": slot,
        "index": _job_index(ev, -1),
        "month": ev.get("date_from"),
        "to": ev.get("date_to"),
        "phase": phase,
        "pct": round(min(99.0, float(pct)), 1),
        "ticks_done": done,
        "ticks_total": tot,
        "trades": trades,
        "detail": detail,
    }


def _idle_lane(slot: int) -> Dict[str, Any]:
    return {
        "slot": slot,
        "index": None,
        "month": None,
        "to": None,
        "phase": "idle",
        "pct": 0.0,
        "ticks_done": 0,
        "ticks_total": 0,
        "trades": 0,
        "detail": "waiting",
    }


def _lanes_snapshot(
    n_workers: int,
    live: Dict[int, Dict[str, Any]],
    slot_of: Dict[int, int],
) -> List[Dict[str, Any]]:
    n = max(1, int(n_workers))
    by_slot: Dict[int, Dict[str, Any]] = {}
    for mi, ev in live.items():
        s = _assign_slot(int(mi), n, slot_of)
        by_slot[s] = _lane_dict(s, ev)
    return [by_slot[s] if s in by_slot else _idle_lane(s) for s in range(n)]


def _run_month_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker process: load one month pack and scan it.
    Must stay top-level so ProcessPoolExecutor can pickle it.
    """
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    fp = FadeParams(**payload["fade_params"])
    q = payload.get("progress_q")
    idx = _job_index(payload, 0)

    def emit(event: str, **kw: Any) -> None:
        if q is None:
            return
        try:
            payload_ev: Dict[str, Any] = {
                "event": event,
                "index": idx,
                "date_from": a,
                "date_to": b,
            }
            payload_ev.update(kw)
            q.put(payload_ev)
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
        part = run_spike_fade(ticks, symbol=symbol, params=fp, progress=walk_prog)
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


def _run(params: SpikeFadeJobParams) -> None:
    global _active_pool
    try:
        chunks = _month_chunks(params.date_from, params.date_to)
        if not chunks:
            raise RuntimeError("Empty date range")
        n_m = len(chunks)
        fp = FadeParams(
            window_sec=float(params.window_sec),
            min_spike_pts=float(params.min_spike_pts),
            tp_pts=float(params.tp_pts),
            sl_pts=float(params.sl_pts),
            tp_pct=float(params.tp_pct if params.tp_pct is not None else 100.0),
            sl_pct=float(params.sl_pct if params.sl_pct is not None else 100.0),
            trail_pts=float(params.trail_pts),
            max_hold_sec=float(params.max_hold_sec),
            cooldown_sec=float(params.cooldown_sec),
            weekend_blackout_min=float(params.weekend_blackout_min),
            lag_sec=float(params.lag_sec or 0.0),
        )
        all_rows: List[dict] = []
        total_ticks = 0
        completed = 0
        workers = max(1, min(6, int(params.workers or 1)))
        fade_params = asdict(fp)
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
                    month_n=month_n,
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
                                    "trades": int(kw.get("trades") or 0),
                                },
                            )
                        ],
                    )

                part = run_spike_fade(
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
                        "fade_params": fade_params,
                        "progress_q": progress_q,
                    }
                )
            live: Dict[int, Dict[str, Any]] = {}
            finished: set = set()
            slot_of: Dict[int, int] = {}
            completed = 0
            errors: List[str] = []

            # First N months start immediately; seed so the log isn't 0k/0k
            # while a worker is still unpacking the pack.
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

        fields = FadeTrade.__dataclass_fields__
        trades = [
            FadeTrade(**{k: r[k] for k in fields if k in r}) for r in all_rows
        ]
        result = summarize_fade(
            trades,
            fp,
            symbol=reaktor_symbol(params.symbol),
            ticks=total_ticks,
        )
        cancelled = _cancel.is_set()
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["months"] = n_m
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
        )
        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        tag = f"spikefade_{params.symbol}_{params.date_from}_{params.date_to}"
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
