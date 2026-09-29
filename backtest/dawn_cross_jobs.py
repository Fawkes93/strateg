"""Background job for the Dawn Cross tab. One thread, 5m candles."""

from __future__ import annotations

import json
import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backtest.batch import is_batch_running
from backtest.candle_packs import load_candles_range
from backtest.dawn_cross import DawnCrossParams, ma_line_spec, run_dawn_cross
from backtest.dukascopy import parse_ymd
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS, unique_result_path


@dataclass
class DawnCrossJobParams:
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    timezone: str = "Europe/Chisinau"
    window_start_hour: int = 2
    window_start_minute: int = 0
    window_end_hour: int = 6
    window_end_minute: int = 0
    fast_ma: str = "ema"
    fast_ema: int = 9
    fast_kama_fast: int = 2
    fast_kama_slow: int = 30
    slow_ma: str = "ema"
    slow_ema: int = 20
    slow_kama_fast: int = 2
    slow_kama_slow: int = 30
    pull_ma: str = "ema"
    pullback_ema: int = 9
    pull_kama_fast: int = 2
    pull_kama_slow: int = 30
    sl_pts: float = 400.0
    tp_pts: float = 800.0
    flatten_hour: int = 12
    one_trade_per_day: bool = True
    force_download: bool = False


@dataclass
class DawnProgress:
    phase: str = "idle"
    message: str = ""
    pct: float = 0.0
    trades: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class DawnJobState:
    params: DawnCrossJobParams = field(default_factory=DawnCrossJobParams)
    progress: DawnProgress = field(default_factory=DawnProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = DawnJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()


def is_dawn_running() -> bool:
    with _lock:
        return _state.running


def get_dawn_state(*, include_rows: bool = False, row_limit: int = 400) -> Dict[str, Any]:
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


def load_saved(result: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Dawn Cross is running — stop it first"}
        _cancel.clear()
        _state.result = retain_result(result)
        _state.progress = DawnProgress(
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
    return None


def start_dawn_job(params: DawnCrossJobParams) -> Dict[str, Any]:
    global _thread
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Dawn Cross is already running"}
        busy = _busy()
        if busy:
            return {"ok": False, "error": busy}
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.progress = DawnProgress(
            phase="load",
            message="Loading 5m candles…",
            pct=5.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        _state.running = True
        _thread = threading.Thread(target=_run, args=(params,), daemon=True)
        _thread.start()
    return {"ok": True}


def stop_dawn() -> Dict[str, Any]:
    if not is_dawn_running():
        return {"ok": False, "error": "Dawn Cross is not running"}
    _cancel.set()
    return {"ok": True}


def _run(params: DawnCrossJobParams) -> None:
    try:
        start = parse_ymd(params.date_from)
        end = parse_ymd(params.date_to)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        load_from = start - timedelta(days=3)
        if _cancel.is_set():
            _set_progress(phase="cancelled", message="Stopped", pct=100.0, finished_at=datetime.now(timezone.utc).isoformat())
            return
        candles = load_candles_range(
            params.symbol,
            load_from,
            end,
            tf_min=5,
            tick_cache=DEFAULT_CACHE,
            force=bool(params.force_download),
        )
        if _cancel.is_set():
            _set_progress(phase="cancelled", message="Stopped", pct=100.0, finished_at=datetime.now(timezone.utc).isoformat())
            return
        _set_progress(phase="scan", message=f"Scanning {len(candles)} bars…", pct=60.0)
        fast = ma_line_spec(
            params.fast_ma, params.fast_ema, params.fast_kama_fast, params.fast_kama_slow
        )
        slow = ma_line_spec(
            params.slow_ma, params.slow_ema, params.slow_kama_fast, params.slow_kama_slow
        )
        pull = ma_line_spec(
            params.pull_ma, params.pullback_ema, params.pull_kama_fast, params.pull_kama_slow
        )
        engine = DawnCrossParams(
            timezone=params.timezone,
            window_start_hour=int(params.window_start_hour),
            window_start_minute=int(params.window_start_minute),
            window_end_hour=int(params.window_end_hour),
            window_end_minute=int(params.window_end_minute),
            fast_ma=fast[0],
            fast_ema=fast[1],
            fast_kama_fast=fast[2],
            fast_kama_slow=fast[3],
            slow_ma=slow[0],
            slow_ema=slow[1],
            slow_kama_fast=slow[2],
            slow_kama_slow=slow[3],
            pull_ma=pull[0],
            pullback_ema=pull[1],
            pull_kama_fast=pull[2],
            pull_kama_slow=pull[3],
            sl_pts=float(params.sl_pts),
            tp_pts=float(params.tp_pts),
            flatten_hour=int(params.flatten_hour),
            one_trade_per_day=bool(params.one_trade_per_day),
        )
        result = run_dawn_cross(
            candles,
            symbol=params.symbol,
            params=engine,
            date_from=start.date(),
            date_to=end.date(),
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        path, run_id = unique_result_path("dawncross")
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
            result=retain_result(result),
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
