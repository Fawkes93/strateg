"""Background job for the Overnight Break tab."""

from __future__ import annotations

import json
import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backtest.batch import is_batch_running
from backtest.dukascopy import (
    DEFAULT_DOWNLOAD_WORKERS,
    fetch_hours_parallel,
    hour_range,
    parse_ymd,
    reaktor_symbol,
)
from backtest.overnight_break import OvernightParams, OvernightSkip, OvernightTrade, run_overnight, summarize_overnight
from backtest.runner import DEFAULT_CACHE, DEFAULT_RESULTS


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
    # Pullback
    pullback_mode: str = "required"  # off | required | preferred
    ema_period: int = 21
    max_wait_candles: int = 8
    timeout_action: str = "skip"
    use_higher_close: bool = True
    # Risk
    sl_mode: str = "asia_opposite"
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    tp_mode: str = "range_mult"
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.5
    tp_r_mult: float = 2.0
    trail_arm_pts: float = 400.0
    trail_pts: float = 250.0
    max_hold_hours: float = 10.0
    flatten_hour: int = 18
    one_trade_per_day: bool = True
    side_filter: str = "both"
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


def get_overnight_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
        }


def is_overnight_running() -> bool:
    with _lock:
        return _state.running


def _set_progress(**kwargs: Any) -> None:
    with _lock:
        for k, v in kwargs.items():
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


def _run(params: OvernightJobParams) -> None:
    try:
        start = parse_ymd(params.date_from)
        end = parse_ymd(params.date_to)
        hours = hour_range(start, end)
        _set_progress(
            phase="download",
            message=f"Load {len(hours)} hours…",
            pct=5.0,
        )

        def dl_prog(**kwargs: Any) -> None:
            done = int(kwargs.get("hours_done") or 0)
            total = int(kwargs.get("hours_total") or max(len(hours), 1))
            pct = 5.0 + 55.0 * (done / max(total, 1))
            _set_progress(
                pct=round(min(60.0, pct), 1),
                ticks=int(kwargs.get("ticks") or 0),
                message=str(
                    kwargs.get("message") or f"Hour {done}/{total}"
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
            message=f"Build 15m + walk {len(ticks):,} ticks…",
            ticks=len(ticks),
            pct=65.0,
        )

        op = OvernightParams(
            timezone="Europe/Bucharest",
            asia_start_hour=int(params.asia_start_hour),
            asia_end_hour=int(params.asia_end_hour),
            min_asia_range_pts=float(params.min_asia_range_pts),
            min_break_pts_above=float(params.min_break_pts_above),
            min_break_pts_below=float(params.min_break_pts_below),
            max_break_candles_after=int(params.max_break_candles_after),
            pullback_mode=str(params.pullback_mode or "required"),
            ema_period=int(params.ema_period),
            max_wait_candles=int(params.max_wait_candles),
            timeout_action=str(params.timeout_action or "skip"),
            use_higher_close=bool(params.use_higher_close),
            sl_mode=str(params.sl_mode or "asia_opposite"),
            sl_fixed_pts=float(params.sl_fixed_pts),
            sl_range_mult=float(params.sl_range_mult),
            tp_mode=str(params.tp_mode or "range_mult"),
            tp_fixed_pts=float(params.tp_fixed_pts),
            tp_range_mult=float(params.tp_range_mult),
            tp_r_mult=float(params.tp_r_mult),
            trail_arm_pts=float(params.trail_arm_pts),
            trail_pts=float(params.trail_pts),
            max_hold_hours=float(params.max_hold_hours),
            flatten_hour=int(params.flatten_hour),
            one_trade_per_day=bool(params.one_trade_per_day),
            side_filter=str(params.side_filter or "both"),
        )
        raw = run_overnight(ticks, symbol=params.symbol, params=op)

        d0, d1 = params.date_from, params.date_to
        trade_rows = [
            r for r in (raw.get("rows") or []) if d0 <= r["local_date"] < d1
        ]
        skip_rows = [
            r for r in (raw.get("skips") or []) if d0 <= r["local_date"] < d1
        ]
        trades = [OvernightTrade(**{k: r[k] for k in OvernightTrade.__dataclass_fields__ if k in r}) for r in trade_rows]
        skips = [OvernightSkip(**r) for r in skip_rows]
        result = summarize_overnight(
            trades,
            skips,
            op,
            symbol=reaktor_symbol(params.symbol),
            ticks=len(ticks),
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["finished_at"] = datetime.now(timezone.utc).isoformat()

        DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
        tag = f"overnight_{params.symbol}_{params.date_from}_{params.date_to}"
        path = DEFAULT_RESULTS / f"{tag}.json"
        path.write_text(json.dumps(result, indent=2, default=str))
        result["saved_to"] = str(path)

        with _lock:
            _state.result = result
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
        with _lock:
            _state.running = False
