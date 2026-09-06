"""Background job for the Session clock tab."""

from __future__ import annotations

import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backtest.batch import is_batch_running
from backtest.dukascopy import (
    DEFAULT_DOWNLOAD_WORKERS,
    fetch_hours_parallel,
    reaktor_symbol,
)
from backtest.h1 import utc_hours_for_local_window
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, unique_result_path
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.session_clock import SessionParams, SessionSkip, SessionTrade, run_session, summarize_session


@dataclass
class SessionJobProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    ticks: int = 0
    trades: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class SessionJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    timezone: str = "Europe/Chisinau"
    min_range_usd: float = 15.0
    min_body_pts: float = 200.0
    sl_floor_pts: float = 500.0
    flatten_hour: int = 12
    force_download: bool = False


@dataclass
class SessionJobState:
    params: SessionJobParams = field(default_factory=SessionJobParams)
    progress: SessionJobProgress = field(default_factory=SessionJobProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = SessionJobState()
_thread: Optional[threading.Thread] = None


def get_session_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
        }


def is_session_running() -> bool:
    with _lock:
        return _state.running


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    """Show a saved session-clock JSON in the UI without re-running."""
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Session clock is running — stop it first"}
        _state.result = retain_result(result)
        _state.progress = SessionJobProgress(
            phase="done",
            message=f"Loaded {name}" if name else "Loaded saved run",
            pct=100.0,
            ticks=int(result.get("ticks") or 0),
            trades=int(result.get("trades") or 0),
            finished_at=result.get("finished_at"),
        )
    return {"ok": True}


def _set_progress(**kwargs: Any) -> None:
    with _lock:
        for k, v in kwargs.items():
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


def start_session_job(params: SessionJobParams) -> Dict[str, Any]:
    global _thread
    from backtest.jobs import is_job_running

    with _lock:
        if _state.running:
            return {"ok": False, "error": "Session clock is already running"}
        if is_job_running():
            return {"ok": False, "error": "Research job is running"}
        if is_batch_running():
            return {"ok": False, "error": "Sweep is running"}
        from backtest.spike_fade_jobs import is_spike_fade_running

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
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = SessionJobProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True, "message": "Session clock started"}


def _run(params: SessionJobParams) -> None:
    try:
        # Only local 03:00–12:00 (plus 12h bar so noon flatten has a tick).
        # Does NOT load full-day tick packs.
        hours = utc_hours_for_local_window(
            params.date_from,
            params.date_to,
            params.timezone or "Europe/Chisinau",
            hour_from=3,
            hour_to=12,
        )
        _set_progress(
            phase="download",
            message=f"Load {len(hours)} session hours (3am–12pm local)…",
            pct=5.0,
        )

        def dl_prog(**kwargs: Any) -> None:
            done = int(kwargs.get("hours_done") or 0)
            total = int(kwargs.get("hours_total") or max(len(hours), 1))
            pct = 5.0 + 60.0 * (done / max(total, 1))
            _set_progress(
                pct=round(min(65.0, pct), 1),
                ticks=int(kwargs.get("ticks") or 0),
                message=str(
                    kwargs.get("message")
                    or f"Hour {done}/{total} · 3am–12pm only"
                ),
            )

        ticks = fetch_hours_parallel(
            params.symbol,
            hours,
            cache_dir=DEFAULT_CACHE,
            force=params.force_download,
            max_workers=DEFAULT_DOWNLOAD_WORKERS,
            progress=dl_prog,
        )
        ticks.sort(key=lambda t: t.ts)
        _set_progress(
            phase="replay",
            message=f"Build H1 + walk {len(ticks):,} ticks…",
            ticks=len(ticks),
            pct=70.0,
        )
        sp = SessionParams(
            timezone=params.timezone or "Europe/Chisinau",
            min_range_usd=float(params.min_range_usd),
            min_body_pts=float(params.min_body_pts),
            sl_floor_pts=float(params.sl_floor_pts),
            flatten_hour=int(params.flatten_hour),
        )
        raw = run_session(ticks, symbol=params.symbol, params=sp)

        # Keep only local dates in [date_from, date_to)
        d0, d1 = params.date_from, params.date_to
        trade_rows = [
            r for r in (raw.get("rows") or []) if d0 <= r["local_date"] < d1
        ]
        skip_rows = [
            r for r in (raw.get("skips") or []) if d0 <= r["local_date"] < d1
        ]
        trades = [SessionTrade(**r) for r in trade_rows]
        skips = [SessionSkip(**r) for r in skip_rows]
        result = summarize_session(
            trades,
            skips,
            sp,
            symbol=reaktor_symbol(params.symbol),
            ticks=len(ticks),
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["finished_at"] = datetime.now(timezone.utc).isoformat()

        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        tag = f"session_{params.symbol}_{params.date_from}_{params.date_to}"
        path, run_id = unique_result_path(tag)
        result["run_id"] = run_id
        import json

        path.write_text(json.dumps(result, indent=2, default=str))
        result["saved_to"] = str(path)

        with _lock:
            _state.result = retain_result(result)
        _set_progress(
            phase="done",
            message=(
                f"Done · {result.get('trades')} trades · "
                f"{result.get('skipped')} skipped"
            ),
            pct=100.0,
            ticks=len(ticks),
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
        try:
            release_job_memory()
        except Exception:
            pass
        with _lock:
            slim_state_result_inplace(_state)
            _state.running = False
