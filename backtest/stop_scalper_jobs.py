"""Background job for the Stop Scalper tab. One thread, 1m candles."""

from __future__ import annotations

import json
import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backtest.batch import is_batch_running
from backtest.candle_packs import load_candles_range
from backtest.dukascopy import parse_ymd
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, unique_result_path
from backtest.stop_scalper import StopScalperParams, run_stop_scalper, validate_params


ROW_LIMIT = 2000


@dataclass
class StopScalperJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-06-01"
    timezone: str = "Europe/Chisinau"
    entry_pts: float = 50.0
    sl_pts: float = 500.0
    trail_pts: float = 100.0
    trail_arm_pts: float = 200.0
    be_pts: float = 150.0
    lock_arm_pts: float = 0.0
    lock_pts: float = 0.0
    tp_pts: float = 0.0
    spread_pts: float = 0.0
    max_spread_pts: float = 0.0
    reverse: bool = True
    reverse_on: str = "close"
    force_download: bool = False


@dataclass
class StopScalperProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    trades: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class StopScalperJobState:
    params: StopScalperJobParams = field(default_factory=StopScalperJobParams)
    progress: StopScalperProgress = field(default_factory=StopScalperProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = StopScalperJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()


def is_scalper_running() -> bool:
    with _lock:
        return _state.running


def get_scalper_state(*, include_rows: bool = False, row_limit: int = ROW_LIMIT) -> Dict[str, Any]:
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
        result["rows_truncated"] = len(rows) > len(result["rows"]) or bool(raw.get("rows_truncated"))
    else:
        result["rows"] = []
        result["rows_truncated"] = bool(rows) or bool(raw.get("rows_truncated"))
    return {
        "running": running,
        "params": params,
        "progress": progress,
        "result": result,
        "cancel_requested": cancel_requested,
    }


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Stop Scalper is running — stop it first"}
        _cancel.clear()
        _state.result = retain_result(result, row_limit=ROW_LIMIT)
        _state.progress = StopScalperProgress(
            phase="done",
            message=f"Loaded {name}" if name else "Loaded saved run",
            pct=100.0,
            trades=int(result.get("trades") or 0),
            finished_at=result.get("finished_at"),
        )
    return {"ok": True}


def _set_progress(**kwargs: Any) -> None:
    result = kwargs.pop("result", None)
    with _lock:
        for k, v in kwargs.items():
            if v is None or not hasattr(_state.progress, k):
                continue
            setattr(_state.progress, k, v)
        if result is not None:
            _state.result = result


def _busy() -> Optional[str]:
    from backtest.jobs import is_job_running
    from backtest.session_jobs import is_session_running
    from backtest.spike_fade_jobs import is_spike_fade_running

    if is_job_running():
        return "Research job is running"
    if is_batch_running():
        return "Sweep is running"
    if is_session_running():
        return "Session clock is running"
    if is_spike_fade_running():
        return "Spike fade is running"
    from backtest.micro_momentum_jobs import is_micro_running

    if is_micro_running():
        return "Micro fade is running"
    from backtest.cooloff_jobs import is_cooloff_running

    if is_cooloff_running():
        return "Cool-off is running"
    from backtest.overnight_jobs import is_overnight_running

    if is_overnight_running():
        return "Overnight break is running"
    from backtest.fvg_jobs import is_fvg_running

    if is_fvg_running():
        return "IFVG is running"
    from backtest.asia_liquidity_jobs import is_asia_liq_running

    if is_asia_liq_running():
        return "Asia liquidity is running"
    from backtest.impulse_fork_jobs import is_fork_running

    if is_fork_running():
        return "Impulse fork is running"
    from backtest.asia_box_jobs import is_asia_box_running

    if is_asia_box_running():
        return "Asia box is running"
    from backtest.dawn_cross_jobs import is_dawn_running

    if is_dawn_running():
        return "Dawn Cross is running"
    return None


def start_scalper_job(params: StopScalperJobParams) -> Dict[str, Any]:
    global _thread
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Stop Scalper is already running"}
        busy = _busy()
        if busy:
            return {"ok": False, "error": busy}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.progress = StopScalperProgress(
            phase="load",
            message="Loading 1m candles…",
            pct=5.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _state.running = True
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True}


def stop_scalper() -> Dict[str, Any]:
    if not is_scalper_running():
        return {"ok": False, "error": "Stop Scalper is not running"}
    _cancel.set()
    return {"ok": True}


def _run(params: StopScalperJobParams) -> None:
    try:
        start = parse_ymd(params.date_from)
        end = parse_ymd(params.date_to)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if _cancel.is_set():
            _set_progress(
                phase="cancelled",
                message="Stopped",
                pct=100.0,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            return
        candles = load_candles_range(
            params.symbol,
            start,
            end,
            tf_min=1,
            tick_cache=DEFAULT_CACHE,
            force=bool(params.force_download),
        )
        if _cancel.is_set():
            _set_progress(
                phase="cancelled",
                message="Stopped",
                pct=100.0,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            return
        _set_progress(phase="scan", message=f"Scanning {len(candles)} bars…", pct=60.0)
        engine = StopScalperParams(
            timezone=params.timezone or "Europe/Chisinau",
            entry_pts=float(params.entry_pts),
            sl_pts=float(params.sl_pts),
            trail_pts=float(params.trail_pts),
            trail_arm_pts=float(params.trail_arm_pts),
            be_pts=float(params.be_pts),
            lock_arm_pts=float(params.lock_arm_pts),
            lock_pts=float(params.lock_pts),
            tp_pts=float(params.tp_pts),
            spread_pts=float(params.spread_pts),
            max_spread_pts=float(params.max_spread_pts),
            reverse=bool(params.reverse),
            reverse_on=str(params.reverse_on or "close"),
        )
        validate_params(engine)
        result = run_stop_scalper(
            candles,
            symbol=params.symbol,
            params=engine,
            date_from=start.date(),
            date_to=end.date(),
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        path, run_id = unique_result_path("stopscalp")
        result["run_id"] = run_id
        result["path"] = str(path)
        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result), encoding="utf-8")
        _set_progress(
            phase="done",
            message=f"Done · {result.get('trades')} trades · {result.get('sum_pts')} pts",
            pct=100.0,
            trades=int(result.get("trades") or 0),
            finished_at=result["finished_at"],
            result=retain_result(result, row_limit=ROW_LIMIT),
        )
    except Exception as e:
        _set_progress(
            phase="error",
            message=str(e),
            error=traceback.format_exc(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        try:
            release_job_memory()
        except Exception:
            pass
        with _lock:
            slim_state_result_inplace(_state, row_limit=ROW_LIMIT)
            _state.running = False
