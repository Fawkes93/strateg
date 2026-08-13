"""
Single-run UI job wrapper around runner.run_research.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backtest.batch import is_batch_running
from backtest.runner import run_research


@dataclass
class JobProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    hours_done: int = 0
    hours_total: int = 0
    ticks: int = 0
    alerts: int = 0
    candles: int = 0
    replay_ticks_done: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class JobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2026-03-02"
    date_to: str = "2026-03-09"
    engines: List[str] = field(default_factory=lambda: ["candle", "spike"])
    hours: float = 6.0
    thresholds: List[float] = field(
        default_factory=lambda: [100, 200, 500, 800, 1000, 1200, 1500, 2000, 3000]
    )
    adverse_mult: float = 1.0
    signal_price: str = "mid"
    sl_manage: str = "off"
    sl_manage_at_frac: float = 0.5
    sl_manage_lock_pts: float = 100.0
    force_download: bool = False
    signal: Optional[Dict[str, Any]] = None


@dataclass
class JobState:
    params: JobParams = field(default_factory=JobParams)
    progress: JobProgress = field(default_factory=JobProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = JobState()
_thread: Optional[threading.Thread] = None


def get_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
        }


def is_job_running() -> bool:
    with _lock:
        return _state.running


def _set_progress(**kwargs: Any) -> None:
    with _lock:
        for k, v in kwargs.items():
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


def start_job(params: JobParams) -> Dict[str, Any]:
    global _thread
    with _lock:
        if _state.running:
            return {"ok": False, "error": "A job is already running"}
        if is_batch_running():
            return {"ok": False, "error": "Batch sweep is running — wait or use Sweep tab"}
        from backtest.session_jobs import is_session_running

        if is_session_running():
            return {"ok": False, "error": "Session clock is running"}
        from backtest.spike_fade_jobs import is_spike_fade_running

        if is_spike_fade_running():
            return {"ok": False, "error": "Spike fade is running"}
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = JobProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run_job, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Job started"}


def _run_job(params: JobParams) -> None:
    try:
        result = run_research(
            symbol=params.symbol,
            date_from=params.date_from,
            date_to=params.date_to,
            engines=params.engines,
            hours=params.hours,
            thresholds=params.thresholds,
            adverse_mult=params.adverse_mult,
            signal_price=params.signal_price,
            sl_manage=params.sl_manage,
            sl_manage_at_frac=params.sl_manage_at_frac,
            sl_manage_lock_pts=params.sl_manage_lock_pts,
            force_download=params.force_download,
            signal=params.signal,
            include_detail=True,
            save_json=True,
            progress=_set_progress,
        )
        with _lock:
            _state.result = result
        _set_progress(
            phase="done",
            message=f"Done · {result.get('alerts')} alerts · {result.get('ticks'):,} ticks",
            pct=100.0,
            alerts=result.get("alerts") or 0,
            ticks=result.get("ticks") or 0,
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
        with _lock:
            _state.running = False
