"""FastAPI routes for Asia box: jobs, catalog, chart data, pages."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backtest.asia_box import (
    FIB_LEVELS,
    AsiaBoxParams,
    ema_series,
    fib_px,
    session_window_utc,
)
from backtest.asia_box_describe import describe_rules, describe_setups
from backtest.asia_box_jobs import (
    AsiaBoxJobParams,
    engine_params,
    get_asia_box_state,
    start_asia_box_job,
    stop_asia_box,
)
from backtest.asia_box_store import delete_run, get_run, get_trade, list_runs, list_trades
from backtest.candle_packs import load_candles_range
from backtest.candles import to_utc as candle_utc

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

router = APIRouter()

FIB_COLORS = {
    0.0: "#e6b450",
    0.236: "#f44336",
    0.382: "#81c784",
    0.5: "#4caf50",
    0.618: "#089981",
    0.786: "#64b5f6",
    1.0: "#8b9aab",
    1.5: "#ce93d8",
    1.618: "#3d9cf0",
}


class AsiaBoxRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    workers: int = 1
    force_download: bool = False
    data_source: str = "candles_5m"
    timezone: str = "Europe/Chisinau"
    box_start_hour: int = 1
    box_end_hour: int = 6
    shallow_hour: int = 5
    shallow_minute: int = 30
    ema_retest_hour: int = 7
    entry_cutoff_hour: int = 10
    flatten_hour: int = 13
    flatten_minute: int = 30
    min_range_pts: float = 3000.0
    min_range_mode: str = "fixed"
    min_range_bps: float = 0.014
    ema_period: int = 32
    shallow_ema_near_pts: float = 100.0
    continuation_sl_fib: float = 0.786
    continuation_tp_fib: float = 0.0
    reverse_confirm_sl_fib: float = 0.5
    reverse_confirm_tp_fib: float = 1.5
    reverse_ema_sl_fib: float = 0.5
    reverse_ema_tp_fib: float = 1.0
    reverse_sl_fib: float = 0.5
    reverse_tp_fib: float = 1.0
    shallow_ema_sl_fib: float = 0.5
    shallow_ema_tp_fib: float = 0.0
    shallow_confirm_sl_fib: float = 0.5
    shallow_confirm_tp_fib: float = 0.0
    shallow_sl_fib: float = 0.5
    ema_retest_sl_fib: float = 0.382
    ema_retest_tp_fib: float = 0.0
    ema_retest_auto_levels: bool = True
    ema_retest_sl_steps: int = 2
    trade_start_enabled: bool = True
    trade_start_hour: int = 3
    trade_start_minute: int = 30
    continuation_trail: bool = True
    continuation_trail_steps: int = 2
    impulse_freeze: bool = True
    impulse_freeze_frac: float = 0.40
    impulse_freeze_minutes: int = 90
    tp_double_fib0: bool = False
    bounce_236: bool = False
    bounce_236_count: int = 2
    enable_continuation: bool = True
    enable_reverse_confirm: bool = True
    enable_reverse_ema: bool = True
    enable_shallow_ema: bool = True
    enable_shallow_confirm: bool = True
    enable_ema_retest: bool = True


def _job_from_req(body: AsiaBoxRunRequest) -> AsiaBoxJobParams:
    data = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    fields = AsiaBoxJobParams.__dataclass_fields__
    return AsiaBoxJobParams(**{k: data[k] for k in fields if k in data})


def _engine_from_req(body: AsiaBoxRunRequest) -> AsiaBoxParams:
    return engine_params(_job_from_req(body))


@router.get("/api/asia-box")
def asia_box_status():
    return get_asia_box_state()


@router.post("/api/asia-box/run")
def asia_box_run(body: AsiaBoxRunRequest):
    out = start_asia_box_job(_job_from_req(body))
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@router.post("/api/asia-box/stop")
def asia_box_stop():
    out = stop_asia_box()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


def _setup_payload(params: AsiaBoxParams) -> Dict[str, Any]:
    return {"setups": describe_setups(params), "rules": describe_rules(params)}


@router.get("/api/asia-box/setups")
def asia_box_setups_default():
    return _setup_payload(AsiaBoxParams())


@router.post("/api/asia-box/setups")
def asia_box_setups(body: AsiaBoxRunRequest):
    return _setup_payload(_engine_from_req(body))


@router.get("/api/asia-box/runs")
def asia_box_runs():
    return {"runs": list_runs()}


@router.delete("/api/asia-box/runs/{run_id}")
def asia_box_delete_run(run_id: int):
    if not delete_run(None, run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"ok": True, "id": run_id}


@router.get("/api/asia-box/trades")
def asia_box_trades(
    run_id: Optional[int] = None,
    setup: Optional[str] = None,
    side: Optional[str] = None,
    box_n: Optional[int] = None,
    exit_reason: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    rows = list_trades(
        None,
        run_id=run_id,
        setup=setup,
        side=side,
        box_n=box_n,
        exit_reason=exit_reason,
        date_from=date_from,
        date_to=date_to,
    )
    return {"trades": rows, "n": len(rows)}


@router.get("/api/asia-box/trade/{trade_id}")
def asia_box_trade(trade_id: int):
    row = get_trade(None, trade_id)
    if not row:
        raise HTTPException(status_code=404, detail="trade not found")
    return row


@router.get("/api/asia-box/chart-data")
def asia_box_chart_data(trade_id: int = Query(...)):
    trade = get_trade(None, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    run = get_run(None, int(trade["run_id"])) or {}
    tz_name = str(run.get("timezone") or (run.get("params") or {}).get("timezone") or "Europe/Chisinau")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    d = date.fromisoformat(str(trade["local_date"]))
    start = datetime.combine(d, time(0, 0), tzinfo=tz) - timedelta(hours=3)
    end = datetime.combine(d, time(14, 30), tzinfo=tz)
    symbol = str(run.get("symbol") or "XAUUSD")
    if "/" in symbol:
        symbol = symbol.replace("/", "")
    candles_out: List[Dict[str, Any]] = []
    ema_out: List[Dict[str, Any]] = []
    try:
        bars = load_candles_range(symbol, start, end, tf_min=5, force=False)
        period = int((run.get("params") or {}).get("ema_period") or 32)
        emas = ema_series([c.close for c in bars], period)
        for i, c in enumerate(bars):
            ts = int(candle_utc(c.open_time).timestamp())
            candles_out.append(
                {
                    "time": ts,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                }
            )
            if emas[i] is not None:
                ema_out.append({"time": ts, "value": emas[i]})
    except Exception:
        bars = []
    fib0 = float(trade["fib0"])
    fib1 = float(trade["fib1"])
    levels = [
        {
            "level": lv,
            "price": fib_px(fib0, fib1, lv),
            "color": FIB_COLORS.get(lv, "#8b9aab"),
        }
        for lv in FIB_LEVELS
    ]
    params = run.get("params") or {}
    box_start_h = int(params.get("box_start_hour") or 1)
    box_end_h = int(params.get("box_end_hour") or 6)
    win_start, win_end = session_window_utc(d, tz_name, box_start_h, box_end_h)
    return {
        "trade": trade,
        "run": {"id": run.get("id"), "symbol": run.get("symbol"), "timezone": tz_name},
        "timezone": tz_name,
        "candles": candles_out,
        "ema": ema_out,
        "fibs": levels,
        "box": {
            "high": trade.get("box_high"),
            "low": trade.get("box_low"),
            "start": trade.get("box_start_ts"),
            "end": win_end.isoformat(),
            "start_unix": int(win_start.timestamp()),
            "end_unix": int(win_end.timestamp()),
            "high_ts": trade.get("box_high_ts"),
            "low_ts": trade.get("box_low_ts"),
            "start_hour": box_start_h,
            "end_hour": box_end_h,
        },
    }


@router.get("/asia-box/results")
def asia_box_results_page():
    return FileResponse(WEB_DIR / "asia_box_results.html")


@router.get("/asia-box/chart")
def asia_box_chart_page():
    return FileResponse(WEB_DIR / "asia_box_chart.html")
