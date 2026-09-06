"""Background job for the Overnight Break tab."""

from __future__ import annotations

import gc
import json
import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
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
from backtest.overnight_break import (
    OvernightParams,
    OvernightSkip,
    OvernightTrade,
    asia_window_start_utc,
    run_overnight,
    summarize_overnight,
)
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, _parse_range, load_ticks, unique_result_path
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.seasonality import TREND_LOOKBACK_DAYS

# Extra hours before each month pack so EMA / Asia DST still work in a worker
# that does not see the previous month's ticks.
_CHUNK_LOOKBACK = timedelta(days=5)


@dataclass
class OvernightJobProgress:
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
class OvernightJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    # Asia
    asia_start_hour: int = 0
    asia_end_hour: int = 7
    min_asia_range_pts: float = 300.0
    min_break_pts_above: float = 200.0
    min_break_pts_below: float = 200.0
    max_break_candles_after: int = 8
    break_on_wick: bool = False
    # Pullback
    pullback_mode: str = "required"  # off | required | preferred
    ema_period: int = 21
    max_wait_candles: int = 8
    wait_from_break: bool = False
    timeout_action: str = "skip"
    use_higher_close: bool = True
    resume_closes: int = 1
    skip_late_short_wait: int = 7
    skip_late_short_asia_pts: float = 3000.0
    # Risk
    sl_mode: str = "asia_opposite"
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    tp_mode: str = "range_mult"
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.5
    tp_r_mult: float = 2.0
    trail_arm_mode: str = "fixed"  # fixed | asia
    trail_arm_pts: float = 400.0
    trail_arm_cap_pts: float = 2000.0
    trail_pts: float = 250.0
    max_hold_hours: float = 10.0
    flatten_hour: int = 18
    one_trade_per_day: bool = True
    side_filter: str = "both"
    seasonal_mode: str = "off"  # off | tag | filter
    seasonal_join: bool = False
    week2_trend: bool = False
    trend_flat_pts: float = 1500.0
    trend_sessions: int = 10
    news_mode: str = "off"  # off | tag | filter
    news_set: str = "scheduled"  # scheduled | all
    workers: int = 3
    force_download: bool = False


@dataclass
class OvernightJobState:
    params: OvernightJobParams = field(default_factory=OvernightJobParams)
    progress: OvernightJobProgress = field(default_factory=OvernightJobProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = OvernightJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
_active_pool: Optional[ProcessPoolExecutor] = None


def get_overnight_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
            "cancel_requested": _cancel.is_set(),
        }


def is_overnight_running() -> bool:
    with _lock:
        return _state.running


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    """Show a saved overnight-break JSON in the UI without re-running."""
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Overnight break is running — stop it first"}
        _cancel.clear()
        _state.result = retain_result(result)
        _state.progress = OvernightJobProgress(
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


def start_overnight_job(params: OvernightJobParams) -> Dict[str, Any]:
    global _thread
    from backtest.jobs import is_job_running
    from backtest.session_jobs import is_session_running
    from backtest.spike_fade_jobs import is_spike_fade_running

    with _lock:
        if _state.running:
            return {"ok": False, "error": "Overnight break is already running"}
        if is_job_running():
            return {"ok": False, "error": "Research job is running"}
        if is_batch_running():
            return {"ok": False, "error": "Sweep is running"}
        if is_session_running():
            return {"ok": False, "error": "Session clock is running"}
        if is_spike_fade_running():
            return {"ok": False, "error": "Spike fade is running"}
        from backtest.micro_momentum_jobs import is_micro_running

        if is_micro_running():
            return {"ok": False, "error": "Micro fade is running"}
        from backtest.cooloff_jobs import is_cooloff_running

        if is_cooloff_running():
            return {"ok": False, "error": "Cool-off is running"}

        from backtest.fvg_jobs import is_fvg_running

        if is_fvg_running():
            return {"ok": False, "error": "IFVG is running"}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = OvernightJobProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Overnight break started"}


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


def stop_overnight() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "No overnight break running"}
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


def _prepend_asia_lookback(
    ticks: List,
    params: OvernightJobParams,
    op: OvernightParams,
    progress,
) -> List:
    """Prefix hours from local Asia open to UTC date_from so the first day is complete.

    Leaves the month tick pack key unchanged; extra hours come from .bi5 cache.
    """
    utc_from = parse_ymd(params.date_from)
    asia_start = asia_window_start_utc(
        date.fromisoformat(params.date_from),
        op.timezone,
        op.asia_start_hour,
        op.asia_end_hour,
    )
    if asia_start >= utc_from:
        return ticks
    hours = hour_range(asia_start, utc_from)
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
    if not prefix:
        return ticks
    return prefix + list(ticks)


def _chunk_lookback_start(date_from: str, op: OvernightParams) -> datetime:
    day = date.fromisoformat(date_from)
    asia = asia_window_start_utc(
        day, op.timezone, op.asia_start_hour, op.asia_end_hour
    )
    ema = parse_ymd(date_from) - _CHUNK_LOOKBACK
    if getattr(op, "week2_trend", False):
        ema = min(ema, parse_ymd(date_from) - timedelta(days=TREND_LOOKBACK_DAYS))
    return min(asia, ema)


def _prepend_chunk_lookback(
    ticks: List,
    params: OvernightJobParams,
    op: OvernightParams,
    progress,
) -> List:
    """Prefix Asia DST hours plus a few days of 15m EMA history."""
    utc_from = parse_ymd(params.date_from)
    start = _chunk_lookback_start(params.date_from, op)
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
    if not prefix:
        return ticks
    return prefix + list(ticks)


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


def _rows_to_trades(rows: List[Dict[str, Any]]) -> List[OvernightTrade]:
    fields = OvernightTrade.__dataclass_fields__
    return [OvernightTrade(**{k: r[k] for k in fields if k in r}) for r in rows]


def _rows_to_skips(rows: List[Dict[str, Any]]) -> List[OvernightSkip]:
    fields = OvernightSkip.__dataclass_fields__
    return [OvernightSkip(**{k: r[k] for k in fields if k in r}) for r in rows]


def _job_index(d: Dict[str, Any], default: int = -1) -> int:
    if "index" not in d or d["index"] is None:
        return default
    return int(d["index"])


def _assign_slot(month_i: int, n_workers: int, slot_of: Dict[int, int]) -> int:
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
        elif tot > 1000 and done:
            detail = f"load {done // 1000}k"
        elif done:
            detail = f"load {done:,}"
        else:
            detail = "loading pack"
        phase = "load"
    else:
        pct = 40.0 + 60.0 * (done / tot) if tot > 0 else 42.0
        if tot >= 1000:
            detail = f"{done // 1000}k / {tot // 1000}k"
        elif tot > 0:
            detail = f"{done}/{tot}"
        else:
            detail = "scanning…"
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
    Worker process: load one month pack (+ lookback hours) and scan it.
    Must stay top-level so ProcessPoolExecutor can pickle it.
    """
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    op = OvernightParams(**payload["op"])
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
        if kw.get("phase") == "candles":
            emit(
                "load",
                message=str(kw.get("message") or "15m candles"),
                ticks_done=int(kw.get("ticks_done") or 0),
                ticks_total=int(kw.get("ticks_total") or 0),
                pct=kw.get("pct") or 50.0,
            )
            return
        emit(
            "scan",
            ticks_done=int(kw.get("days_done") or kw.get("ticks_done") or 0),
            ticks_total=int(kw.get("days_total") or kw.get("ticks_total") or 0),
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
        chunk_job = OvernightJobParams(
            symbol=symbol,
            date_from=a,
            date_to=b,
            force_download=force,
        )
        ticks = _prepend_chunk_lookback(ticks, chunk_job, op, load_prog)
        raw = run_overnight(
            ticks, symbol=symbol, params=op, progress=walk_prog
        )
        n_ticks = len(ticks)
        trade_rows = [
            r for r in (raw.get("rows") or []) if a <= r["local_date"] < b
        ]
        skip_rows = [
            r for r in (raw.get("skips") or []) if a <= r["local_date"] < b
        ]
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
    """In-process stand-in for multiprocessing.Queue."""

    def __init__(self, cb):
        self._cb = cb

    def put(self, item, block=True, timeout=None):
        try:
            self._cb(item)
        except Exception:
            pass


def _run(params: OvernightJobParams) -> None:
    global _active_pool
    try:
        op = OvernightParams(
            timezone="Europe/Bucharest",
            asia_start_hour=int(params.asia_start_hour),
            asia_end_hour=int(params.asia_end_hour),
            min_asia_range_pts=float(params.min_asia_range_pts),
            min_break_pts_above=float(params.min_break_pts_above),
            min_break_pts_below=float(params.min_break_pts_below),
            max_break_candles_after=int(params.max_break_candles_after),
            break_on_wick=bool(params.break_on_wick),
            require_close_outside=not bool(params.break_on_wick),
            pullback_mode=str(params.pullback_mode or "required"),
            ema_period=int(params.ema_period),
            max_wait_candles=int(params.max_wait_candles),
            wait_from_break=bool(params.wait_from_break),
            timeout_action=str(params.timeout_action or "skip"),
            use_higher_close=bool(params.use_higher_close),
            resume_closes=max(1, int(params.resume_closes or 1)),
            skip_late_short_wait=max(0, int(params.skip_late_short_wait or 0)),
            skip_late_short_asia_pts=float(params.skip_late_short_asia_pts or 0.0),
            sl_mode=str(params.sl_mode or "asia_opposite"),
            sl_fixed_pts=float(params.sl_fixed_pts),
            sl_range_mult=float(params.sl_range_mult),
            tp_mode=str(params.tp_mode or "range_mult"),
            tp_fixed_pts=float(params.tp_fixed_pts),
            tp_range_mult=float(params.tp_range_mult),
            tp_r_mult=float(params.tp_r_mult),
            trail_arm_mode=str(params.trail_arm_mode or "fixed"),
            trail_arm_pts=float(params.trail_arm_pts),
            trail_arm_cap_pts=float(params.trail_arm_cap_pts),
            trail_pts=float(params.trail_pts),
            max_hold_hours=float(params.max_hold_hours),
            flatten_hour=int(params.flatten_hour),
            one_trade_per_day=bool(params.one_trade_per_day),
            side_filter=str(params.side_filter or "both"),
            seasonal_mode=str(params.seasonal_mode or "off"),
            seasonal_join=bool(params.seasonal_join),
            week2_trend=bool(params.week2_trend),
            trend_flat_pts=float(params.trend_flat_pts or 1500.0),
            trend_sessions=max(5, int(params.trend_sessions or 10)),
            news_mode=str(params.news_mode or "off"),
            news_set=str(params.news_set or "scheduled"),
        )
        chunks = _month_chunks(params.date_from, params.date_to)
        if not chunks:
            raise RuntimeError("Empty date range")
        n_m = len(chunks)
        workers = max(1, min(6, int(params.workers or 1)))
        op_dict = asdict(op)
        all_trades: List[OvernightTrade] = []
        all_skips: List[OvernightSkip] = []
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

                def on_put(ev, i=i, a=a, b=b, label=label, base=base, span=span):
                    kind = ev.get("event") or "load"
                    if kind == "load":
                        lp = float(ev.get("pct") or 0.0)
                        frac = 0.35 * min(lp, 50.0) / 50.0
                    else:
                        tot = max(int(ev.get("ticks_total") or 1), 1)
                        frac = 0.35 + 0.60 * int(ev.get("ticks_done") or 0) / tot
                    _set_progress(
                        phase="replay" if kind == "scan" else "download",
                        message=f"{label} · {ev.get('message') or kind}",
                        pct=round(min(94.0, base + span * frac), 1),
                        ticks=total_ticks + int(ev.get("ticks_done") or 0),
                        trades=len(all_trades) + int(ev.get("trades") or 0),
                        months_done=i,
                        months_total=n_m,
                        lanes=[_lane_dict(0, ev)],
                    )

                _set_progress(
                    phase="download",
                    message=f"{label} · load pack…",
                    pct=round(base, 1),
                    ticks=total_ticks,
                    trades=len(all_trades),
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
            payloads = []
            for i, (a, b) in enumerate(chunks):
                payloads.append(
                    {
                        "index": i,
                        "date_from": a,
                        "date_to": b,
                        "symbol": params.symbol,
                        "force_download": params.force_download,
                        "op": op_dict,
                        "progress_q": progress_q,
                    }
                )
            live: Dict[int, Dict[str, Any]] = {}
            finished: set = set()
            slot_of: Dict[int, int] = {}

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
                        in_frac += (
                            min(0.4, float(p) / 125.0) if p is not None else 0.05
                        )
                    else:
                        tot = max(int(ev.get("ticks_total") or 0), 1)
                        in_frac += min(1.0, int(ev.get("ticks_done") or 0) / tot)
                overall = 100.0 * (completed + in_frac) / n_m
                _set_progress(
                    phase="replay",
                    message=(
                        f"{workers} workers · {completed}/{n_m} months · "
                        f"{len(all_trades)} trades"
                    ),
                    pct=round(min(96.0, overall), 1),
                    ticks=total_ticks,
                    trades=len(all_trades),
                    months_done=completed,
                    months_total=n_m,
                    lanes=_lanes_snapshot(workers, live, slot_of),
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
                        ingest(out)
                        idx = _job_index(out, -1)
                        if idx >= 0:
                            finished.add(idx)
                            live.pop(idx, None)
                            _release_slot(idx, slot_of)
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

        all_trades.sort(key=lambda t: t.local_date)
        all_skips.sort(key=lambda s: (s.local_date or "", s.reason or ""))
        result = summarize_overnight(
            all_trades,
            all_skips,
            op,
            symbol=reaktor_symbol(params.symbol),
            ticks=total_ticks,
        )
        cancelled = _cancel.is_set()
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["months"] = n_m
        result["cancelled"] = cancelled
        result["finished_at"] = datetime.now(timezone.utc).isoformat()

        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        tag = f"overnight_{params.symbol}_{params.date_from}_{params.date_to}"
        path, run_id = unique_result_path(tag)
        result["run_id"] = run_id
        path.write_text(json.dumps(result, indent=2, default=str))
        result["saved_to"] = str(path)

        with _lock:
            _state.result = retain_result(result)
        if cancelled:
            _set_progress(
                phase="cancelled",
                message=(
                    f"Stopped · {result.get('trades') or 0} trades · "
                    f"{result.get('skipped') or 0} skipped"
                ),
                ticks=total_ticks,
                trades=result.get("trades") or 0,
                finished_at=datetime.now(timezone.utc).isoformat(),
                lanes=[],
            )
        else:
            _set_progress(
                phase="done",
                message=(
                    f"Done · {n_m} months · {result.get('trades')} trades · "
                    f"{result.get('skipped')} skipped"
                ),
                pct=100.0,
                ticks=total_ticks,
                trades=result.get("trades") or 0,
                finished_at=datetime.now(timezone.utc).isoformat(),
                lanes=[],
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
