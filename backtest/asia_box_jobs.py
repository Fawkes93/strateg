"""Background job for the Asia box tab."""

from __future__ import annotations

import threading
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backtest.asia_box import (
    AsiaBoxParams,
    AsiaBoxSkip,
    AsiaBoxTrade,
    run_asia_box,
    run_asia_box_on_candles,
    summarize_asia_box,
)
from backtest.asia_box_store import insert_run
from backtest.batch import is_batch_running
from backtest.candle_packs import load_candles_range
from backtest.dukascopy import reaktor_symbol
from backtest.job_memory import release_job_memory, retain_result, slim_state_result_inplace
from backtest.runner import _parse_range, load_ticks

_CHUNK_LOOKBACK = timedelta(days=2)


@dataclass
class AsiaBoxJobProgress:
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
    sqlite_id: Optional[int] = None


@dataclass
class AsiaBoxJobParams(AsiaBoxParams):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    workers: int = 1
    force_download: bool = False
    data_source: str = "candles_5m"


@dataclass
class AsiaBoxJobState:
    params: AsiaBoxJobParams = field(default_factory=AsiaBoxJobParams)
    progress: AsiaBoxJobProgress = field(default_factory=AsiaBoxJobProgress)
    result: Optional[Dict[str, Any]] = None
    running: bool = False


_lock = threading.Lock()
_state = AsiaBoxJobState()
_thread: Optional[threading.Thread] = None
_cancel = threading.Event()


def engine_params(job: AsiaBoxJobParams) -> AsiaBoxParams:
    fields = AsiaBoxParams.__dataclass_fields__
    return AsiaBoxParams(**{k: getattr(job, k) for k in fields})


def get_asia_box_state() -> Dict[str, Any]:
    with _lock:
        return {
            "running": _state.running,
            "params": asdict(_state.params),
            "progress": asdict(_state.progress),
            "result": _state.result,
            "cancel_requested": _cancel.is_set(),
        }


def is_asia_box_running() -> bool:
    with _lock:
        return _state.running


def _set_progress(**kwargs: Any) -> None:
    with _lock:
        for k, v in kwargs.items():
            if v is None:
                continue
            if hasattr(_state.progress, k):
                setattr(_state.progress, k, v)


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


def _rows_to_trades(rows: List[Dict[str, Any]]) -> List[AsiaBoxTrade]:
    fields = AsiaBoxTrade.__dataclass_fields__
    out: List[AsiaBoxTrade] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            kw = {k: r[k] for k in fields if k in r}
            if "extras" not in kw:
                kw["extras"] = r.get("extras") or {}
            out.append(AsiaBoxTrade(**kw))
        except TypeError:
            continue
    return out


def start_asia_box_job(params: AsiaBoxJobParams) -> Dict[str, Any]:
    if is_batch_running():
        return {"ok": False, "error": "A batch sweep is running"}
    with _lock:
        if _state.running:
            return {"ok": False, "error": "Asia box is already running"}
        _cancel.clear()
        _state.running = True
        _state.params = params
        _state.result = None
        _state.progress = AsiaBoxJobProgress(
            phase="starting",
            message="Starting…",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
    t = threading.Thread(target=_run, args=(params,), daemon=True)
    global _thread
    _thread = t
    t.start()
    return {"ok": True}


def stop_asia_box() -> Dict[str, Any]:
    with _lock:
        if not _state.running:
            return {"ok": False, "error": "not running"}
    _cancel.set()
    _set_progress(phase="cancelling", message="Stop requested…")
    return {"ok": True}


def _run(params: AsiaBoxJobParams) -> None:
    op = engine_params(params)
    src = str(params.data_source or "candles_5m").strip().lower()
    if src not in ("candles_5m", "ticks"):
        src = "candles_5m"
    chunks = _month_chunks(params.date_from, params.date_to)
    n_m = max(1, len(chunks))
    all_trades: List[AsiaBoxTrade] = []
    all_skips: List[AsiaBoxSkip] = []
    all_freezes: List[Dict[str, Any]] = []
    total_bars = 0
    try:
        for i, (a, b) in enumerate(chunks):
            if _cancel.is_set():
                break
            _set_progress(
                phase="replay",
                message=f"Month {i + 1}/{n_m} · {a} → {b}",
                pct=round(100.0 * i / n_m, 1),
                months_done=i,
                months_total=n_m,
                trades=len(all_trades),
            )
            start, end = _parse_range(a, b)
            lookback = start - _CHUNK_LOOKBACK
            if src == "ticks":
                ticks = load_ticks(
                    symbol=params.symbol,
                    date_from=lookback.date().isoformat(),
                    date_to=b,
                    force_download=params.force_download,
                )
                raw = run_asia_box(ticks, symbol=params.symbol, params=op)
                total_bars += len(ticks)
                del ticks
            else:
                candles = load_candles_range(
                    params.symbol,
                    lookback,
                    end,
                    tf_min=5,
                    force=params.force_download,
                )
                raw = run_asia_box_on_candles(candles, symbol=params.symbol, params=op)
                total_bars += len(candles)
                del candles
            rows = [r for r in (raw.get("rows") or []) if a <= r["local_date"] < b]
            skips = [s for s in (raw.get("skips") or []) if a <= s.get("local_date", "") < b]
            all_trades.extend(_rows_to_trades(rows))
            for f in raw.get("freezes") or []:
                if a <= str(f.get("local_date") or "") < b:
                    all_freezes.append(f)
            for s in skips:
                try:
                    all_skips.append(AsiaBoxSkip(**{k: s[k] for k in ("local_date", "reason") if k in s}))
                except Exception:
                    continue
            del raw
        cancelled = _cancel.is_set()
        result = summarize_asia_box(
            all_trades,
            all_skips,
            params=op,
            symbol=reaktor_symbol(params.symbol),
            data_source=src,
            n_bars=total_bars,
            freezes=all_freezes,
        )
        result["date_from"] = params.date_from
        result["date_to"] = params.date_to
        result["months"] = n_m
        result["cancelled"] = cancelled
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        sqlite_id = insert_run(
            None,
            date_from=params.date_from,
            date_to=params.date_to,
            result=result,
            status="cancelled" if cancelled else "complete",
        )
        result["sqlite_id"] = sqlite_id
        with _lock:
            _state.result = retain_result(result)
        n_tr = int(result.get("trades") or 0)
        saved = "saved" if sqlite_id else "not saved (0 trades)"
        _set_progress(
            phase="cancelled" if cancelled else "done",
            message=(
                f"{'Stopped' if cancelled else 'Done'} · {n_tr} trades · {saved}"
            ),
            pct=100.0,
            ticks=total_bars,
            trades=n_tr,
            finished_at=result["finished_at"],
            sqlite_id=sqlite_id,
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
