"""Background job for the Asia pullback tab. Own state, month-chunk pool."""

from __future__ import annotations

import gc
import json
import threading
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backtest.asia_pullback import (
    AsiaPullbackParams,
    normalize_params,
    run_asia_pullback,
    run_asia_pullback_on_candles,
    summarize_asia_pullback,
)
from backtest.candle_packs import load_candles_range
from backtest.dukascopy import (
    drop_cached_pack,
    fetch_hours_parallel,
    hour_range,
    normalize_duka_symbol,
    parse_ymd,
    reaktor_symbol,
)
from backtest.asia_pullback_store import insert_run as insert_pullback_run
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.overnight_break import require_zone
from backtest.runner import (
    DEFAULT_CACHE,
    DEFAULT_RESULTS,
    _parse_range,
    load_ticks,
    unique_result_path,
)

_LOOKBACK = timedelta(days=5)


@dataclass
class AsiaPullbackJobParams(AsiaPullbackParams):
    symbol: str = "XAUUSD"
    date_from: str = "2025-03-01"
    date_to: str = "2025-06-01"
    workers: int = 2
    force_download: bool = False
    data_source: str = "candles_5m"  # candles_5m | ticks


@dataclass
class AsiaPullbackProgress:
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


@dataclass
class AsiaPullbackJobState:
    params: AsiaPullbackJobParams = field(default_factory=AsiaPullbackJobParams)
    progress: AsiaPullbackProgress = field(default_factory=AsiaPullbackProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = AsiaPullbackJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()
_active_pool: Optional[ProcessPoolExecutor] = None


def is_asia_pullback_running() -> bool:
    with _lock:
        return _state.running


def get_asia_pullback_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
            "cancel_requested": _cancel.is_set(),
        }


def _set_progress(**kw: Any) -> None:
    with _lock:
        for k, v in kw.items():
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


def _busy() -> Optional[str]:
    from backtest.batch import is_batch_running
    from backtest.overnight_jobs import is_overnight_running

    if is_batch_running():
        return "Sweep is running"
    if is_overnight_running():
        return "Overnight break is running"
    return None


def start_asia_pullback_job(params: AsiaPullbackJobParams) -> Dict[str, Any]:
    global _thread
    try:
        normalize_params(params)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    src = str(params.data_source or "candles_5m").strip().lower()
    if src not in ("candles_5m", "ticks"):
        return {"ok": False, "error": "data_source must be candles_5m or ticks"}
    params.data_source = src
    params.workers = max(1, min(6, int(params.workers or 1)))
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Asia pullback is already running"}
        busy = _busy()
        if busy:
            return {"ok": False, "error": busy}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = AsiaPullbackProgress(
            phase="download",
            message="Starting…",
            pct=1.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True}


def stop_asia_pullback() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "Asia pullback is not running"}
        _cancel.set()
        _set_progress(phase="cancelling", message="Stopping… killing workers")
    n = _force_kill_pool()
    return {"ok": True, "message": f"Stop sent · terminated {n} worker process(es)", "killed": n}


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


def _lookback_start(date_from: str, tz_name: str, sr_days: int = 5) -> datetime:
    day = datetime.strptime(date_from, "%Y-%m-%d").date()
    tz = require_zone(tz_name)
    local_open = datetime.combine(day, dt_time(0, 0), tzinfo=tz).astimezone(timezone.utc)
    extra = max(_LOOKBACK, timedelta(days=max(1, int(sr_days)) + 2))
    ema = parse_ymd(date_from) - extra
    return min(local_open, ema)


def _run_month_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """One month in a worker process. Top-level so the pool can pickle it."""
    a = payload["date_from"]
    b = payload["date_to"]
    try:
        out = _scan_range(payload)
        out["ok"] = True
        out["error"] = None
        return out
    except Exception as e:
        return {
            "ok": False,
            "index": payload.get("index"),
            "date_from": a,
            "date_to": b,
            "ticks": 0,
            "rows": [],
            "skips": [],
            "cancelled": False,
            "error": f"{a}→{b}: {e}",
        }


def _scan_range(payload: Dict[str, Any]) -> Dict[str, Any]:
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    data_source = str(payload.get("data_source") or "candles_5m")
    params = AsiaPullbackJobParams(**payload["params"])
    normalize_params(params)
    lookback = _lookback_start(a, params.timezone, int(getattr(params, "sr_days", 5) or 5))
    _start, end = _parse_range(a, b)
    if data_source == "ticks":
        ticks = load_ticks(
            symbol=symbol,
            date_from=a,
            date_to=b,
            force_download=force,
        )
        ticks = _prepend_ticks(ticks, symbol, a, lookback, force)
        raw = run_asia_pullback(
            ticks,
            symbol=symbol,
            params=params,
            date_from=a,
            date_to=b,
        )
        n = len(ticks)
        del ticks
        gc.collect()
        drop_cached_pack(normalize_duka_symbol(symbol), _start, end)
    else:
        candles = load_candles_range(
            symbol,
            lookback,
            end,
            tf_min=5,
            tick_cache=DEFAULT_CACHE,
            force=force,
        )
        raw = run_asia_pullback_on_candles(
            candles,
            symbol=symbol,
            params=params,
            date_from=a,
            date_to=b,
        )
        n = len(candles)
        del candles
        gc.collect()
    return {
        "index": payload.get("index"),
        "date_from": a,
        "date_to": b,
        "ticks": n,
        "rows": raw.get("rows") or [],
        "skips": raw.get("skips") or [],
        "cancelled": bool(raw.get("cancelled")),
    }


def _prepend_ticks(ticks: List[Any], symbol: str, date_from: str, lookback: datetime, force: bool) -> List[Any]:
    utc_from = parse_ymd(date_from)
    if lookback >= utc_from:
        return ticks
    hours = hour_range(lookback, utc_from)
    if not hours:
        return ticks
    prefix = fetch_hours_parallel(
        symbol,
        hours,
        cache_dir=DEFAULT_CACHE,
        force=force,
    )
    prefix = [t for t in prefix if t.ts < utc_from]
    prefix.sort(key=lambda t: t.ts)
    if not prefix:
        return ticks
    return prefix + list(ticks)


def _run(params: AsiaPullbackJobParams) -> None:
    global _active_pool
    try:
        chunks = _month_chunks(params.date_from, params.date_to)
        if not chunks:
            raise RuntimeError("Empty date range")
        n_m = len(chunks)
        workers = max(1, min(6, int(params.workers or 1)))
        param_dict = asdict(params)
        all_rows: List[Dict[str, Any]] = []
        all_skips: List[Dict[str, Any]] = []
        total_ticks = 0
        completed = 0
        errors: List[str] = []
        cancelled = False

        def ingest(out: Dict[str, Any]) -> None:
            nonlocal total_ticks, completed, cancelled
            completed += 1
            total_ticks += int(out.get("ticks") or 0)
            all_rows.extend(out.get("rows") or [])
            all_skips.extend(out.get("skips") or [])
            if out.get("cancelled"):
                cancelled = True
            if not out.get("ok", True) and out.get("error"):
                errors.append(str(out["error"]))

        def payload_for(i: int, a: str, b: str) -> Dict[str, Any]:
            return {
                "index": i,
                "date_from": a,
                "date_to": b,
                "symbol": params.symbol,
                "force_download": params.force_download,
                "data_source": params.data_source,
                "params": param_dict,
            }

        if workers <= 1 or n_m <= 1:
            for i, (a, b) in enumerate(chunks):
                if _cancel.is_set():
                    cancelled = True
                    break
                label = f"Month {i + 1}/{n_m}  {a} → {b}"
                base = 5.0 + 90.0 * i / n_m
                _set_progress(
                    phase="replay",
                    message=f"{label} · scanning",
                    pct=round(base, 1),
                    ticks=total_ticks,
                    trades=len(all_rows),
                    months_done=i,
                    months_total=n_m,
                )

                def on_prog(i=i, a=a, b=b, label=label, base=base, span=90.0 / n_m, **kw: Any) -> None:
                    tot = max(int(kw.get("days_total") or 1), 1)
                    done = int(kw.get("days_done") or 0)
                    frac = done / tot
                    _set_progress(
                        phase="replay",
                        message=f"{label} · {kw.get('message') or 'scan'}",
                        pct=round(min(94.0, base + span * frac), 1),
                        ticks=total_ticks,
                        trades=len(all_rows) + int(kw.get("trades") or 0),
                        months_done=i,
                        months_total=n_m,
                    )

                body = payload_for(i, a, b)
                out = _scan_one_with_progress(body, on_prog)
                ingest(out)
        else:
            import multiprocessing as mp

            ctx = mp.get_context("spawn")
            pool = ProcessPoolExecutor(max_workers=workers, mp_context=ctx)
            _active_pool = pool
            futures = []
            try:
                for i, (a, b) in enumerate(chunks):
                    if _cancel.is_set():
                        cancelled = True
                        break
                    futures.append(pool.submit(_run_month_job, payload_for(i, a, b)))
                pending = set(futures)
                while pending:
                    if _cancel.is_set():
                        cancelled = True
                        break
                    done, pending = wait(pending, timeout=0.4, return_when=FIRST_COMPLETED)
                    for fut in done:
                        try:
                            ingest(fut.result())
                        except (BrokenProcessPool, Exception) as e:
                            errors.append(str(e))
                    _set_progress(
                        phase="replay",
                        message=f"{workers} workers · {completed}/{n_m} months · {len(all_rows)} trades",
                        pct=round(100.0 * completed / n_m, 1),
                        ticks=total_ticks,
                        trades=len(all_rows),
                        months_done=completed,
                        months_total=n_m,
                    )
            finally:
                _force_kill_pool()

        if _cancel.is_set():
            cancelled = True
        all_rows.sort(key=lambda r: (str(r.get("local_date")), str(r.get("entry_ts"))))
        result = summarize_asia_pullback(
            all_rows,
            all_skips,
            params,
            symbol=reaktor_symbol(params.symbol),
            ticks=total_ticks,
            data_source=params.data_source,
            cancelled=cancelled,
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["months"] = n_m
        result["params"] = asdict(params)
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        if errors:
            result["month_errors"] = errors
        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        src_tag = "ticks" if params.data_source == "ticks" else "5m"
        tag = f"asiapullback_{params.symbol}_{src_tag}_{params.date_from}_{params.date_to}"
        path, run_id = unique_result_path(tag)
        result["run_id"] = run_id
        path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        result["saved_to"] = str(path)
        sqlite_id = insert_pullback_run(
            None,
            date_from=params.date_from,
            date_to=params.date_to,
            result=result,
            status="cancelled" if cancelled else "complete",
        )
        result["sqlite_id"] = sqlite_id
        catalog = f" · catalog #{sqlite_id}" if sqlite_id else ""
        with _lock:
            _state.result = retain_result(result)
        if cancelled:
            _set_progress(
                phase="cancelled",
                message=f"Stopped · {result.get('trades') or 0} trades" + catalog,
                ticks=total_ticks,
                trades=result.get("trades") or 0,
                finished_at=result["finished_at"],
            )
        elif errors and not all_rows and not all_skips:
            _set_progress(
                phase="error",
                message="; ".join(errors)[:500],
                error="; ".join(errors),
                pct=100.0,
                finished_at=result["finished_at"],
            )
        else:
            pf = result.get("profit_factor")
            _set_progress(
                phase="done",
                message=(
                    f"Done · {result.get('trades')} trades · "
                    f"PF {pf if pf is not None else '—'} · {result.get('sum_pts')} pts"
                    + catalog
                ),
                pct=100.0,
                ticks=total_ticks,
                trades=result.get("trades") or 0,
                finished_at=result["finished_at"],
            )
    except Exception as e:
        _set_progress(
            phase="error",
            message=str(e),
            error=traceback.format_exc(),
            pct=100.0,
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


def _scan_one_with_progress(payload: Dict[str, Any], progress: Any) -> Dict[str, Any]:
    """In-process month scan that can report day progress."""
    a = payload["date_from"]
    b = payload["date_to"]
    symbol = payload["symbol"]
    force = bool(payload.get("force_download"))
    params = AsiaPullbackJobParams(**payload["params"])
    normalize_params(params)
    lookback = _lookback_start(a, params.timezone, int(getattr(params, "sr_days", 5) or 5))
    _start, end = _parse_range(a, b)

    def stop() -> bool:
        return _cancel.is_set()

    if params.data_source == "ticks" or payload.get("data_source") == "ticks":
        ticks = load_ticks(symbol=symbol, date_from=a, date_to=b, force_download=force)
        ticks = _prepend_ticks(ticks, symbol, a, lookback, force)
        raw = run_asia_pullback(
            ticks,
            symbol=symbol,
            params=params,
            progress=progress,
            stop=stop,
            date_from=a,
            date_to=b,
        )
        n = len(ticks)
        del ticks
        gc.collect()
        drop_cached_pack(normalize_duka_symbol(symbol), _start, end)
    else:
        candles = load_candles_range(
            symbol, lookback, end, tf_min=5, tick_cache=DEFAULT_CACHE, force=force
        )
        raw = run_asia_pullback_on_candles(
            candles,
            symbol=symbol,
            params=params,
            progress=progress,
            stop=stop,
            date_from=a,
            date_to=b,
        )
        n = len(candles)
        del candles
        gc.collect()
    return {
        "ok": True,
        "index": payload.get("index"),
        "date_from": a,
        "date_to": b,
        "ticks": n,
        "rows": raw.get("rows") or [],
        "skips": raw.get("skips") or [],
        "cancelled": bool(raw.get("cancelled")) or _cancel.is_set(),
        "error": None,
    }
