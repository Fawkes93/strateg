"""Background job for the CRT tab. One thread, 5-minute candles."""

from __future__ import annotations

import json
import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backtest.candle_packs import load_candles_range
from backtest.crt import CrtParams, normalize_params, run_crt_on_candles, summarize_crt
from backtest.crt_store import insert_run as insert_crt_run
from backtest.dukascopy import reaktor_symbol
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, _parse_range, unique_result_path


@dataclass
class CrtJobParams(CrtParams):
    symbol: str = "XAUUSD"
    date_from: str = "2025-03-01"
    date_to: str = "2025-04-01"
    force_download: bool = False


@dataclass
class CrtProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    ticks: int = 0
    trades: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class CrtJobState:
    params: CrtJobParams = field(default_factory=CrtJobParams)
    progress: CrtProgress = field(default_factory=CrtProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = CrtJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()


def is_crt_running() -> bool:
    with _lock:
        return _state.running


def get_crt_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
            "cancel_requested": _cancel.is_set(),
        }


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    with _lock:
        if _state.running:
            return {"ok": False, "error": "CRT is running — stop it first"}
        _cancel.clear()
        _state.result = retain_result(result)
        _state.progress = CrtProgress(
            phase="done",
            message=f"Loaded {name}" if name else "Loaded saved run",
            pct=100.0,
            trades=int(result.get("trades") or 0),
            finished_at=result.get("finished_at"),
        )
    return {"ok": True}


def _set_progress(**kwargs: Any) -> None:
    with _lock:
        for key, value in kwargs.items():
            if hasattr(_state.progress, key):
                setattr(_state.progress, key, value)


def _busy() -> Optional[str]:
    from backtest.batch import is_batch_running
    from backtest.overnight_jobs import is_overnight_running

    if is_batch_running():
        return "Sweep is running"
    if is_overnight_running():
        return "Overnight break is running"
    return None


def start_crt_job(params: CrtJobParams) -> Dict[str, Any]:
    global _thread
    try:
        normalize_params(params)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        start, end = _parse_range(params.date_from, params.date_to)
    except Exception:
        return {"ok": False, "error": "date_from and date_to must be YYYY-MM-DD"}
    if end <= start:
        return {"ok": False, "error": "date_to must be after date_from"}
    with _lock:
        if _state.running:
            return {"ok": False, "error": "CRT is already running"}
        busy = _busy()
        if busy:
            return {"ok": False, "error": busy}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = CrtProgress(
            phase="download",
            message="Starting…",
            pct=1.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True}


def stop_crt() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "CRT is not running"}
        _cancel.set()
    _set_progress(phase="cancelling", message="Stopping…")
    return {"ok": True, "message": "Stop sent"}


def _run(params: CrtJobParams) -> None:
    try:
        normalize_params(params)
        start, end = _parse_range(params.date_from, params.date_to)
        lookback = start - timedelta(days=3, minutes=params.structure_bars * params.htf_min)

        def on_load(**kwargs: Any) -> None:
            _set_progress(
                phase=str(kwargs.get("phase") or "download"),
                message=str(kwargs.get("message") or "Loading 5m candles"),
                pct=8.0,
            )

        _set_progress(phase="download", message="Loading 5m candles…", pct=5.0)
        candles = load_candles_range(
            params.symbol,
            lookback,
            end,
            tf_min=5,
            tick_cache=DEFAULT_CACHE,
            force=bool(params.force_download),
            progress=on_load,
        )
        if _cancel.is_set():
            _finish_cancelled(params, candles_n=len(candles))
            return

        def on_scan(done: int, total: int) -> None:
            pct = 15.0 if total <= 0 else 15.0 + 80.0 * min(done, total) / total
            _set_progress(
                phase="replay",
                message=f"CRT {done}/{total} higher-timeframe bars",
                pct=round(pct, 1),
                ticks=len(candles),
            )

        raw = run_crt_on_candles(
            candles,
            symbol=params.symbol,
            params=params,
            date_from=params.date_from,
            date_to=params.date_to,
            progress=on_scan,
            stop=_cancel.is_set,
        )
        _save(params, raw, ticks=len(candles))
    except Exception as exc:
        _set_progress(
            phase="error",
            message=str(exc),
            error=traceback.format_exc(),
            pct=100.0,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        try:
            release_job_memory()
        except Exception:
            pass
        with _lock:
            slim_state_result_inplace(_state)
            _state.running = False


def _finish_cancelled(params: CrtJobParams, candles_n: int) -> None:
    raw = {"rows": [], "skips": [], "cancelled": True, "ticks": candles_n, "symbol": reaktor_symbol(params.symbol)}
    _save(params, raw, ticks=candles_n)


def _save(params: CrtJobParams, raw: Dict[str, Any], *, ticks: int) -> None:
    cancelled = bool(raw.get("cancelled") or _cancel.is_set())
    result = summarize_crt(
        raw,
        params,
        symbol=params.symbol,
        data_source="candles_5m",
        cancelled=cancelled,
    )
    result["date_from"] = params.date_from
    result["date_to"] = params.date_to
    result["params"] = asdict(params)
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["ticks"] = ticks
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    tag = f"crt_{params.symbol}_5m_{params.date_from}_{params.date_to}"
    path, run_id = unique_result_path(tag)
    result["run_id"] = run_id
    sqlite_id = insert_crt_run(
        None,
        date_from=params.date_from,
        date_to=params.date_to,
        result=result,
        status="cancelled" if cancelled else "complete",
    )
    result["sqlite_id"] = sqlite_id
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    result["saved_to"] = str(path)
    with _lock:
        _state.result = retain_result(result)
    catalog = f" · catalog #{sqlite_id}" if sqlite_id else ""
    if cancelled:
        _set_progress(
            phase="cancelled",
            message=f"Stopped · {result.get('trades') or 0} trades" + catalog,
            pct=100.0,
            ticks=ticks,
            trades=result.get("trades") or 0,
            finished_at=result["finished_at"],
        )
        return
    pf = result.get("profit_factor")
    _set_progress(
        phase="done",
        message=(
            f"Done · {result.get('trades')} trades · "
            f"PF {pf if pf is not None else '—'} · {result.get('sum_pts')} pts"
            + catalog
        ),
        pct=100.0,
        ticks=ticks,
        trades=result.get("trades") or 0,
        finished_at=result["finished_at"],
    )
