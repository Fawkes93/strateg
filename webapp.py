#!/usr/bin/env python3
"""Local Strateg research UI — single run + overnight sweep + overnight break."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backtest.batch import (
    batch_param_schema,
    get_batch_state,
    load_report,
    start_batch,
    stop_batch,
)
from backtest.runner import DEFAULT_RESULTS
from backtest.config import defaults_snapshot
from backtest.dukascopy import reaktor_symbol
from backtest.jobs import JobParams, get_state, start_job
from backtest.session_jobs import (
    SessionJobParams,
    get_session_state,
    start_session_job,
)
from backtest.spike_fade_jobs import (
    SpikeFadeJobParams,
    get_spike_fade_state,
    start_spike_fade_job,
    stop_spike_fade,
)
from backtest.overnight_jobs import (
    OvernightJobParams,
    get_overnight_state,
    start_overnight_job,
    stop_overnight,
)

WEB_DIR = ROOT / "web"
app = FastAPI(title="Strateg", version="0.5", docs_url="/docs")


class RunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2026-03-02"
    date_to: str = "2026-03-09"
    engines: list[str] = Field(default_factory=lambda: ["candle", "spike"])
    hours: float = 6.0
    thresholds: list[float] = Field(
        default_factory=lambda: [100, 200, 500, 800, 1000, 1200, 1500, 2000, 3000]
    )
    adverse_mult: float = 1.0
    signal_price: str = "mid"
    sl_manage: str = "off"  # off | be | lock
    sl_manage_at_frac: float = 0.5
    sl_manage_lock_pts: float = 100.0
    force_download: bool = False
    signal: Optional[Dict[str, Any]] = None


class BatchRequest(BaseModel):
    symbol: str = "XAUUSD"
    hours: float = 6.0
    thresholds: list[float] = Field(
        default_factory=lambda: [100, 200, 500, 800, 1000, 1200, 1500, 2000]
    )
    adverse_mult: float = 1.0
    top_n: int = 3
    workers: int = 4  # process workers; backend caps at 4
    test_range: bool = True
    test_spike: bool = True
    test_spike_neo: bool = False
    test_impulse_retrace: bool = False
    test_range_wick: bool = False
    pairing: str = "together"  # together | grid
    sl_manage: str = "off"  # off | be | lock
    sl_manage_at_frac: float = 0.5
    sl_manage_lock_pts: float = 100.0
    date_ranges: List[Dict[str, str]] = Field(default_factory=list)
    range_rows: List[Dict[str, Any]] = Field(default_factory=list)
    spike_rows: List[Dict[str, Any]] = Field(default_factory=list)
    spike_neo_rows: List[Dict[str, Any]] = Field(default_factory=list)
    impulse_retrace_rows: List[Dict[str, Any]] = Field(default_factory=list)
    range_wick_rows: List[Dict[str, Any]] = Field(default_factory=list)
    filters: Optional[Dict[str, Any]] = None


@app.get("/api/health")
def health():
    return {"ok": True, "service": "strateg", "local_only": True}


@app.get("/api/signal-defaults")
def signal_defaults(symbol: str = Query("XAUUSD")):
    return defaults_snapshot(reaktor_symbol(symbol))


@app.get("/api/batch/schema")
def batch_schema(symbol: str = Query("XAUUSD")):
    return batch_param_schema(symbol)


@app.get("/api/job")
def job_status():
    return get_state()


@app.post("/api/job/run")
def job_run(body: RunRequest):
    params = JobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        engines=list(body.engines) or ["candle", "spike"],
        hours=float(body.hours),
        thresholds=list(body.thresholds) or [500.0],
        adverse_mult=float(body.adverse_mult),
        signal_price=body.signal_price or "mid",
        sl_manage=body.sl_manage or "off",
        sl_manage_at_frac=float(body.sl_manage_at_frac or 0.5),
        sl_manage_lock_pts=float(body.sl_manage_lock_pts or 100.0),
        force_download=bool(body.force_download),
        signal=body.signal,
    )
    out = start_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.get("/api/batch")
def batch_status():
    return get_batch_state()


@app.post("/api/batch/run")
def batch_run(body: BatchRequest):
    cfg = body.model_dump()
    out = start_batch(cfg)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/batch/stop")
def batch_stop():
    out = stop_batch()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


class LoadReportRequest(BaseModel):
    """Load a saved batch JSON into the Sweep UI (no tick re-run)."""
    path: Optional[str] = None  # absolute or relative under results/


@app.post("/api/batch/load-report")
def batch_load_report(body: LoadReportRequest = LoadReportRequest()):
    import json
    from pathlib import Path

    if body.path:
        p = Path(body.path).expanduser()
        if not p.is_absolute():
            p = DEFAULT_RESULTS / body.path
    else:
        # newest batch_*.json
        cands = sorted(
            DEFAULT_RESULTS.glob("batch_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if not cands:
            raise HTTPException(status_code=404, detail="No batch_*.json in results/")
        p = cands[0]
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {p}")
    try:
        report = json.loads(p.read_text())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e
    out = load_report(report)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    out["path"] = str(p)
    return out


class SessionRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    timezone: str = "Europe/Chisinau"
    min_range_usd: float = 15.0
    min_body_pts: float = 200.0
    sl_floor_pts: float = 500.0
    flatten_hour: int = 12
    force_download: bool = False


@app.get("/api/session")
def session_status():
    return get_session_state()


@app.post("/api/session/run")
def session_run(body: SessionRunRequest):
    params = SessionJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        timezone=body.timezone or "Europe/Chisinau",
        min_range_usd=float(body.min_range_usd),
        min_body_pts=float(body.min_body_pts),
        sl_floor_pts=float(body.sl_floor_pts),
        flatten_hour=int(body.flatten_hour),
        force_download=bool(body.force_download),
    )
    out = start_session_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


class SpikeFadeRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-06-01"
    window_sec: float = 3.0
    min_spike_pts: float = 2000.0
    tp_pts: float = 2000.0
    sl_pts: float = 2000.0
    tp_pct: float = 100.0
    sl_pct: float = 100.0
    trail_pts: float = 1000.0
    trail_arm_pts: float = 0.0
    confirm_pts: float = 0.0
    confirm_timeout_sec: float = 5.0
    max_extreme_age_sec: float = 0.0
    max_hold_sec: float = 120.0
    cooldown_sec: float = 30.0
    weekend_blackout_min: float = 10.0
    lag_sec: float = 0.0
    workers: int = 3
    force_download: bool = False


@app.get("/api/spike-fade")
def spike_fade_status(
    rows: int = Query(0),
    limit: int = Query(400),
):
    return get_spike_fade_state(include_rows=bool(rows), row_limit=int(limit))


@app.post("/api/spike-fade/run")
def spike_fade_run(body: SpikeFadeRunRequest):
    params = SpikeFadeJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        window_sec=float(body.window_sec),
        min_spike_pts=float(body.min_spike_pts),
        tp_pts=float(body.tp_pts),
        sl_pts=float(body.sl_pts),
        tp_pct=float(body.tp_pct if body.tp_pct is not None else 100.0),
        sl_pct=float(body.sl_pct if body.sl_pct is not None else 100.0),
        trail_pts=float(body.trail_pts),
        trail_arm_pts=float(body.trail_arm_pts or 0.0),
        confirm_pts=float(body.confirm_pts or 0.0),
        confirm_timeout_sec=float(body.confirm_timeout_sec or 5.0),
        max_extreme_age_sec=float(body.max_extreme_age_sec or 0.0),
        max_hold_sec=float(body.max_hold_sec),
        cooldown_sec=float(body.cooldown_sec),
        weekend_blackout_min=float(body.weekend_blackout_min),
        lag_sec=float(body.lag_sec or 0.0),
        workers=int(body.workers or 3),
        force_download=bool(body.force_download),
    )
    out = start_spike_fade_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/spike-fade/stop")
def spike_fade_stop():
    out = stop_spike_fade()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


# ---------------------------------------------------------------------------
# Overnight Break (Asia range + EMA / higher-close entry)
# ---------------------------------------------------------------------------


class OvernightRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    asia_start_hour: int = 0
    asia_end_hour: int = 7
    min_asia_range_pts: float = 300.0
    min_break_pts_above: float = 200.0
    min_break_pts_below: float = 200.0
    max_break_candles_after: int = 8
    pullback_mode: str = "required"  # off | required | preferred
    ema_period: int = 21
    max_wait_candles: int = 8
    timeout_action: str = "skip"
    use_higher_close: bool = True
    resume_closes: int = 1
    skip_late_short_wait: int = 7
    skip_late_short_asia_pts: float = 3000.0
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
    workers: int = 3
    force_download: bool = False


@app.get("/api/overnight")
def overnight_status():
    return get_overnight_state()


@app.post("/api/overnight/run")
def overnight_run(body: OvernightRunRequest):
    params = OvernightJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        asia_start_hour=int(body.asia_start_hour),
        asia_end_hour=int(body.asia_end_hour),
        min_asia_range_pts=float(body.min_asia_range_pts),
        min_break_pts_above=float(body.min_break_pts_above),
        min_break_pts_below=float(body.min_break_pts_below),
        max_break_candles_after=int(body.max_break_candles_after),
        pullback_mode=str(body.pullback_mode or "required"),
        ema_period=int(body.ema_period),
        max_wait_candles=int(body.max_wait_candles),
        timeout_action=str(body.timeout_action or "skip"),
        use_higher_close=bool(body.use_higher_close),
        resume_closes=max(1, int(body.resume_closes or 1)),
        skip_late_short_wait=max(0, int(body.skip_late_short_wait or 0)),
        skip_late_short_asia_pts=float(body.skip_late_short_asia_pts or 0.0),
        sl_mode=str(body.sl_mode or "asia_opposite"),
        sl_fixed_pts=float(body.sl_fixed_pts),
        sl_range_mult=float(body.sl_range_mult),
        tp_mode=str(body.tp_mode or "range_mult"),
        tp_fixed_pts=float(body.tp_fixed_pts),
        tp_range_mult=float(body.tp_range_mult),
        tp_r_mult=float(body.tp_r_mult),
        trail_arm_mode=str(body.trail_arm_mode or "fixed"),
        trail_arm_pts=float(body.trail_arm_pts),
        trail_arm_cap_pts=float(body.trail_arm_cap_pts),
        trail_pts=float(body.trail_pts),
        max_hold_hours=float(body.max_hold_hours),
        flatten_hour=int(body.flatten_hour),
        one_trade_per_day=bool(body.one_trade_per_day),
        side_filter=str(body.side_filter or "both"),
        workers=max(1, min(6, int(body.workers or 1))),
        force_download=bool(body.force_download),
    )
    out = start_overnight_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/overnight/stop")
def overnight_stop():
    out = stop_overnight()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def main():
    import uvicorn

    print("Strateg local UI → http://127.0.0.1:8765", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
