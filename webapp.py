#!/usr/bin/env python3
"""Local Strateg research UI — single run + overnight sweep + overnight break + Asia liquidity."""

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
from backtest.saved_results import (
    KNOWN_KINDS,
    list_saved_results,
    load_into_job,
    read_saved_result,
)
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
from backtest.micro_momentum_jobs import (
    MicroJobParams,
    get_micro_state,
    start_micro_job,
    stop_micro,
)
from backtest.overnight_jobs import (
    OvernightJobParams,
    get_overnight_state,
    start_overnight_job,
    stop_overnight,
)
from backtest.asia_liquidity_jobs import (
    AsiaLiqJobParams,
    get_asia_liq_state,
    start_asia_liq_job,
    stop_asia_liq,
)
from backtest.impulse_fork_jobs import (
    ForkJobParams,
    get_fork_state,
    start_fork_job,
    stop_fork,
)
from backtest.cooloff_jobs import (
    CoolOffJobParams,
    get_cooloff_state,
    start_cooloff_job,
    stop_cooloff,
)
from backtest.fvg_jobs import (
    FvgJobParams,
    get_fvg_state,
    start_fvg_job,
    stop_fvg,
)
from backtest.dawn_cross import ma_line_spec, same_average
from backtest.dawn_cross_jobs import (
    DawnCrossJobParams,
    get_dawn_state,
    start_dawn_job,
    stop_dawn,
)
from backtest.asia_box_api import router as asia_box_router
from backtest.overnight_api import router as overnight_router

WEB_DIR = ROOT / "web"
app = FastAPI(title="Strateg", version="0.5", docs_url="/docs")
app.include_router(asia_box_router)
app.include_router(overnight_router)


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
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)


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


class LoadSavedRequest(BaseModel):
    kind: str
    name: str


@app.get("/api/results")
def results_list(kind: str = Query(...)):
    try:
        files = list_saved_results(kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"kind": kind, "files": files}


@app.get("/api/results/file")
def results_file(name: str = Query(...)):
    try:
        data, path = read_saved_result(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Not found: {name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return data


@app.post("/api/results/load")
def results_load(body: LoadSavedRequest):
    if body.kind not in KNOWN_KINDS:
        raise HTTPException(status_code=400, detail=f"Unknown kind: {body.kind}")
    try:
        out = load_into_job(body.kind, body.name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Not found: {body.name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
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


class MicroRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2026-06-01"
    date_to: str = "2026-08-31"
    window_sec: float = 4.0
    min_burst_pts: float = 100.0
    max_burst_pts: float = 300.0
    persist_frac: float = 0.35
    use_1m: bool = False
    min_1m_body: float = 40.0
    tp_pts: float = 100.0
    sl_pts: float = 80.0
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0
    max_hold_sec: float = 20.0
    cooldown_sec: float = 20.0
    weekend_blackout_min: float = 10.0
    lag_sec: float = 0.0
    session: str = "all"
    max_spread_pts: float = 40.0
    mode: str = "fade"
    pause_sec: float = 1.0
    pause_give_up_sec: float = 8.0
    tp_frac: float = 0.5
    sl_mult: float = 1.0
    rr_one_to_one: bool = True
    trail_frac: float = 0.5
    be_asap: bool = False
    be_asap_pts: float = 1.0
    workers: int = 2
    force_download: bool = False


@app.get("/api/micro-momentum")
def micro_status(
    rows: int = Query(0),
    limit: int = Query(400),
):
    return get_micro_state(include_rows=bool(rows), row_limit=int(limit))


@app.post("/api/micro-momentum/run")
def micro_run(body: MicroRunRequest):
    params = MicroJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        window_sec=float(body.window_sec),
        min_burst_pts=float(body.min_burst_pts),
        max_burst_pts=float(body.max_burst_pts),
        persist_frac=float(body.persist_frac),
        use_1m=bool(body.use_1m),
        min_1m_body=float(body.min_1m_body),
        tp_pts=float(body.tp_pts),
        sl_pts=float(body.sl_pts),
        trail_pts=float(body.trail_pts or 0.0),
        trail_arm_pts=float(body.trail_arm_pts or 0.0),
        max_hold_sec=float(body.max_hold_sec),
        cooldown_sec=float(body.cooldown_sec),
        weekend_blackout_min=float(body.weekend_blackout_min),
        lag_sec=float(body.lag_sec or 0.0),
        session=str(body.session or "all"),
        max_spread_pts=float(body.max_spread_pts or 0.0),
        mode=str(body.mode or "fade"),
        pause_sec=float(body.pause_sec or 1.0),
        pause_give_up_sec=float(body.pause_give_up_sec or 8.0),
        tp_frac=float(body.tp_frac or 0.0),
        sl_mult=float(body.sl_mult or 1.0),
        rr_one_to_one=bool(body.rr_one_to_one),
        trail_frac=float(body.trail_frac or 0.0),
        be_asap=bool(body.be_asap),
        be_asap_pts=float(body.be_asap_pts or 0.0),
        workers=int(body.workers or 2),
        force_download=bool(body.force_download),
    )
    out = start_micro_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/micro-momentum/stop")
def micro_stop():
    out = stop_micro()
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
    break_on_wick: bool = False
    pullback_mode: str = "required"  # off | required | preferred
    pullback_ref: str = "ema"  # ema | fib | both
    pullback_fib: float = 0.5
    fib_anchor: str = "asia"  # asia | roll
    ma_type: str = "ema"  # ema | kama | hma | zlema
    ema_period: int = 21
    kama_er: int = 10
    kama_fast: int = 2
    kama_slow: int = 30
    hma_period: int = 21
    zlema_period: int = 21
    max_wait_candles: int = 8
    wait_from_break: bool = False
    timeout_action: str = "skip"  # skip | market
    timeout_max_ema_dist_pts: float = 0.0
    timeout_min_break_pts: float = 0.0
    timeout_min_pullback_pts: float = 0.0
    near_box_bars: int = 0
    near_box_pts: float = 500.0
    near_box_trend: str = "off"
    near_box_min_range_pts: float = 0.0
    use_higher_close: bool = True
    resume_closes: int = 1
    resume_max_break_pts: float = 0.0
    skip_late_short_wait: int = 7
    skip_late_short_asia_pts: float = 3000.0
    sl_mode: str = "asia_opposite"
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    sl_cap_pts: float = 0.0
    sl_m12_frac: float = 1.0 / 3.0
    tp_mode: str = "range_mult"
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.5
    tp_sl_mult: Optional[float] = None
    tp_r_mult: Optional[float] = None
    trail_arm_mode: str = "fixed"  # fixed | asia
    trail_arm_pts: float = 400.0
    trail_arm_cap_pts: float = 2000.0
    trail_pts: float = 250.0
    be_arm_pts: float = 0.0
    shock_trail: bool = False
    shock_window_sec: float = 2.0
    shock_move_pts: float = 300.0
    shock_arm_pts: float = 1500.0
    shock_trail_pts: float = 1000.0
    shock_settle_min: float = 0.0
    shock_settle_pts: float = 800.0
    shock_tight_pts: float = 800.0
    max_hold_hours: float = 10.0
    flatten_hour: int = 18
    one_trade_per_day: bool = True
    side_filter: str = "both"
    seasonal_mode: str = "off"
    seasonal_join: bool = False
    week2_trend: bool = False
    week2_mode: str = "off"
    trend_flat_pts: float = 1500.0
    trend_sessions: int = 10
    trend_efficiency_min: float = 0.35
    news_mode: str = "off"
    news_set: str = "scheduled"
    workers: int = 3
    force_download: bool = False
    data_source: str = "candles_5m"


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
        break_on_wick=bool(body.break_on_wick),
        pullback_mode=str(body.pullback_mode or "required"),
        pullback_ref=str(body.pullback_ref or "ema"),
        pullback_fib=float(body.pullback_fib if body.pullback_fib is not None else 0.5),
        fib_anchor=str(body.fib_anchor or "asia"),
        ma_type=str(body.ma_type or "ema"),
        ema_period=int(body.ema_period),
        kama_er=max(1, int(body.kama_er or 10)),
        kama_fast=max(1, int(body.kama_fast or 2)),
        kama_slow=max(1, int(body.kama_slow or 30)),
        hma_period=max(2, int(body.hma_period or 21)),
        zlema_period=max(1, int(body.zlema_period or 21)),
        max_wait_candles=int(body.max_wait_candles),
        wait_from_break=bool(body.wait_from_break),
        timeout_action=str(body.timeout_action or "skip"),
        timeout_max_ema_dist_pts=float(body.timeout_max_ema_dist_pts or 0.0),
        timeout_min_break_pts=float(body.timeout_min_break_pts or 0.0),
        timeout_min_pullback_pts=float(body.timeout_min_pullback_pts or 0.0),
        near_box_bars=max(0, int(getattr(body, "near_box_bars", 0) or 0)),
        near_box_pts=max(0.0, float(getattr(body, "near_box_pts", 500.0) or 0.0)),
        near_box_trend=str(getattr(body, "near_box_trend", "off") or "off"),
        near_box_min_range_pts=max(
            0.0, float(getattr(body, "near_box_min_range_pts", 0.0) or 0.0)
        ),
        use_higher_close=bool(body.use_higher_close),
        resume_closes=max(1, int(body.resume_closes or 1)),
        resume_max_break_pts=max(0.0, float(body.resume_max_break_pts or 0.0)),
        skip_late_short_wait=max(0, int(body.skip_late_short_wait or 0)),
        skip_late_short_asia_pts=float(body.skip_late_short_asia_pts or 0.0),
        sl_mode=str(body.sl_mode or "asia_opposite"),
        sl_fixed_pts=float(body.sl_fixed_pts),
        sl_range_mult=float(body.sl_range_mult),
        sl_cap_pts=float(body.sl_cap_pts or 0.0),
        sl_m12_frac=float(
            body.sl_m12_frac if body.sl_m12_frac is not None else (1.0 / 3.0)
        ),
        tp_mode=str(body.tp_mode or "range_mult"),
        tp_fixed_pts=float(body.tp_fixed_pts),
        tp_range_mult=float(body.tp_range_mult),
        tp_sl_mult=(
            None if body.tp_sl_mult is None else float(body.tp_sl_mult)
        ),
        tp_r_mult=float(2.0 if body.tp_r_mult is None else body.tp_r_mult),
        trail_arm_mode=str(body.trail_arm_mode or "fixed"),
        trail_arm_pts=float(body.trail_arm_pts),
        trail_arm_cap_pts=float(body.trail_arm_cap_pts),
        trail_pts=float(body.trail_pts),
        be_arm_pts=max(0.0, float(body.be_arm_pts or 0.0)),
        shock_trail=bool(getattr(body, "shock_trail", False)),
        shock_window_sec=float(getattr(body, "shock_window_sec", 2.0) or 0.0),
        shock_move_pts=float(getattr(body, "shock_move_pts", 300.0) or 0.0),
        shock_arm_pts=float(getattr(body, "shock_arm_pts", 1500.0) or 0.0),
        shock_trail_pts=float(getattr(body, "shock_trail_pts", 1000.0) or 0.0),
        shock_settle_min=float(getattr(body, "shock_settle_min", 0.0) or 0.0),
        shock_settle_pts=float(getattr(body, "shock_settle_pts", 800.0) or 0.0),
        shock_tight_pts=float(getattr(body, "shock_tight_pts", 800.0) or 0.0),
        max_hold_hours=float(body.max_hold_hours),
        flatten_hour=int(body.flatten_hour),
        one_trade_per_day=bool(body.one_trade_per_day),
        side_filter=str(body.side_filter or "both"),
        seasonal_mode=str(body.seasonal_mode or "off"),
        seasonal_join=bool(body.seasonal_join),
        week2_trend=bool(body.week2_trend),
        week2_mode=str(body.week2_mode or "off"),
        trend_flat_pts=float(body.trend_flat_pts or 1500.0),
        trend_sessions=max(5, int(body.trend_sessions or 10)),
        trend_efficiency_min=float(
            body.trend_efficiency_min if body.trend_efficiency_min is not None else 0.35
        ),
        news_mode=str(body.news_mode or "off"),
        news_set=str(body.news_set or "scheduled"),
        workers=max(1, min(6, int(body.workers or 1))),
        force_download=bool(body.force_download),
        data_source=(
            "ticks"
            if str(body.data_source or "").strip().lower() == "ticks"
            else "candles_5m"
        ),
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


# ---------------------------------------------------------------------------
# Dual-Mode Asia Liquidity Engine
# ---------------------------------------------------------------------------


class AsiaLiqRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-08-01"
    timezone: str = "UTC"
    exec_timezone: str = "UTC"
    asia_start_hour: int = 0
    asia_end_hour: int = 7
    london_wait_minutes: int = 30
    signal_start_hour: int = 7
    signal_end_hour: int = 11
    mode_b_end_hour: int = 9
    mode_b_end_minute: int = 30
    flatten_hour: int = 16
    atr_period: int = 14
    box_atr_min: float = 0.25
    box_atr_max: float = 0.85
    compression_lookback: int = 20
    htf_enabled: bool = True
    htf_ema_period: int = 50
    news_mode: str = "filter"
    news_set: str = "scheduled"
    news_blackout_minutes: int = 60
    spread_filter: bool = True
    spread_mult: float = 1.5
    mode_a_enabled: bool = True
    break_buffer_atr: float = 0.1
    body_frac: float = 0.50
    min_range_atr: float = 0.6
    tp1_r: float = 1.0
    tp2_r: float = 1.8
    tp2_select: str = "nearer"
    be_offset_r: float = 0.1
    trail_swing_bars: int = 3
    mode_b_enabled: bool = True
    sweep_buffer_atr: float = 0.15
    reclaim_bars: int = 4
    mode_b_confirm: bool = True
    sweep_stop_atr: float = 0.1
    risk_pct: float = 0.5
    start_equity: float = 1000.0
    daily_halt_r: float = 1.5
    weekly_halt_r: float = 4.0
    workers: int = 3
    force_download: bool = False


@app.get("/api/asia-liquidity")
def asia_liq_status():
    return get_asia_liq_state()


@app.post("/api/asia-liquidity/run")
def asia_liq_run(body: AsiaLiqRunRequest):
    params = AsiaLiqJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        timezone=str(body.timezone or "UTC"),
        exec_timezone=str(body.exec_timezone or "UTC"),
        asia_start_hour=int(body.asia_start_hour),
        asia_end_hour=int(body.asia_end_hour),
        london_wait_minutes=int(body.london_wait_minutes),
        signal_start_hour=int(body.signal_start_hour),
        signal_end_hour=int(body.signal_end_hour),
        mode_b_end_hour=int(body.mode_b_end_hour),
        mode_b_end_minute=int(body.mode_b_end_minute),
        flatten_hour=int(body.flatten_hour),
        atr_period=int(body.atr_period),
        box_atr_min=float(body.box_atr_min),
        box_atr_max=float(body.box_atr_max),
        compression_lookback=int(body.compression_lookback),
        htf_enabled=bool(body.htf_enabled),
        htf_ema_period=int(body.htf_ema_period),
        news_mode=str(body.news_mode or "filter"),
        news_set=str(body.news_set or "scheduled"),
        news_blackout_minutes=int(body.news_blackout_minutes),
        spread_filter=bool(body.spread_filter),
        spread_mult=float(body.spread_mult),
        mode_a_enabled=bool(body.mode_a_enabled),
        break_buffer_atr=float(body.break_buffer_atr),
        body_frac=float(body.body_frac),
        min_range_atr=float(body.min_range_atr),
        tp1_r=float(body.tp1_r),
        tp2_r=float(body.tp2_r),
        tp2_select=str(body.tp2_select or "nearer"),
        be_offset_r=float(body.be_offset_r),
        trail_swing_bars=int(body.trail_swing_bars),
        mode_b_enabled=bool(body.mode_b_enabled),
        sweep_buffer_atr=float(body.sweep_buffer_atr),
        reclaim_bars=int(body.reclaim_bars),
        mode_b_confirm=bool(body.mode_b_confirm),
        sweep_stop_atr=float(body.sweep_stop_atr),
        risk_pct=float(body.risk_pct),
        start_equity=float(body.start_equity),
        daily_halt_r=float(body.daily_halt_r),
        weekly_halt_r=float(body.weekly_halt_r),
        workers=max(1, min(6, int(body.workers or 1))),
        force_download=bool(body.force_download),
    )
    out = start_asia_liq_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/asia-liquidity/stop")
def asia_liq_stop():
    out = stop_asia_liq()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


class ImpulseForkRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2026-06-01"
    date_to: str = "2026-07-01"
    window_sec: float = 3.0
    min_blast_pts: float = 1100.0
    snap_pts: float = 300.0
    snap_sec: float = 10.0
    join_retrace: float = 0.50
    join_wait_sec: float = 90.0
    chase_ext: float = 0.50
    fade_lag_sec: float = 1.0
    fade_sl_pct: float = 100.0
    fade_sl_cap_pts: float = 1500.0
    fade_tp_pct: float = 200.0
    fade_tp_cap_pts: float = 3000.0
    fade_trail_pts: float = 600.0
    fade_trail_arm_pts: float = 750.0
    fade_hold_sec: float = 250.0
    join_stop_beyond: float = 0.15
    join_tp1_r: float = 1.0
    join_tp2_r: float = 1.5
    join_be_r: float = 0.1
    join_hold_sec: float = 1200.0
    cooldown_sec: float = 30.0
    weekend_blackout_min: float = 10.0
    stand_aside_n: int = 3
    skip_london_utc: bool = True
    london_start_hour: int = 7
    london_end_hour: int = 10
    fade_enabled: bool = True
    join_enabled: bool = True
    stand_aside_enabled: bool = True
    risk_pct: float = 0.5
    start_equity: float = 1000.0
    daily_halt_r: float = 1.5
    weekly_halt_r: float = 4.0
    workers: int = 3
    force_download: bool = False


@app.get("/api/impulse-fork")
def fork_status():
    return get_fork_state()


@app.post("/api/impulse-fork/run")
def fork_run(body: ImpulseForkRunRequest):
    fields = ForkJobParams.__dataclass_fields__
    kwargs = {k: getattr(body, k) for k in fields if hasattr(body, k)}
    kwargs["workers"] = max(1, min(6, int(kwargs.get("workers") or 1)))
    params = ForkJobParams(**kwargs)
    out = start_fork_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/impulse-fork/stop")
def fork_stop():
    out = stop_fork()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


# ---------------------------------------------------------------------------
# Trend Cool-Off (15m run → reverse >30% / join <30% + HH/LL reclaim)
# ---------------------------------------------------------------------------


class CoolOffRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2026-06-01"
    date_to: str = "2026-07-01"
    invert: bool = False
    min_run: int = 5
    max_tolerance: int = 2
    min_run_range_pts: float = 0.0
    max_run_range_pts: float = 0.0
    reverse_frac: float = 0.30
    reverse_min_bars: int = 2
    reverse_max_bars: int = 3
    join_min_bars: int = 2
    join_max_bars: int = 4
    tp_pts: float = 500.0
    sl_pts: float = 500.0
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0
    max_hold_hours: float = 4.0
    cooldown_min: float = 0.0
    weekend_blackout_min: float = 10.0
    workers: int = 2
    force_download: bool = False


@app.get("/api/cooloff")
def cooloff_status(
    rows: int = Query(0),
    limit: int = Query(400),
):
    return get_cooloff_state(include_rows=bool(rows), row_limit=int(limit))


@app.post("/api/cooloff/run")
def cooloff_run(body: CoolOffRunRequest):
    min_run_range_pts = max(0.0, float(body.min_run_range_pts or 0.0))
    max_run_range_pts = max(0.0, float(body.max_run_range_pts or 0.0))
    if max_run_range_pts > 0 and max_run_range_pts < min_run_range_pts:
        raise HTTPException(status_code=422, detail="Maximum run range must be at least the minimum run range")
    params = CoolOffJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        invert=bool(body.invert),
        min_run=max(2, int(body.min_run)),
        max_tolerance=max(0, int(body.max_tolerance)),
        min_run_range_pts=min_run_range_pts,
        max_run_range_pts=max_run_range_pts,
        reverse_frac=float(body.reverse_frac),
        reverse_min_bars=max(1, int(body.reverse_min_bars)),
        reverse_max_bars=max(1, int(body.reverse_max_bars)),
        join_min_bars=max(1, int(body.join_min_bars)),
        join_max_bars=max(1, int(body.join_max_bars)),
        tp_pts=float(body.tp_pts),
        sl_pts=float(body.sl_pts),
        trail_pts=float(body.trail_pts or 0.0),
        trail_arm_pts=float(body.trail_arm_pts or 0.0),
        max_hold_hours=float(body.max_hold_hours),
        cooldown_sec=float(body.cooldown_min or 0.0) * 60.0,
        weekend_blackout_min=float(body.weekend_blackout_min or 0.0),
        workers=max(1, min(6, int(body.workers or 1))),
        force_download=bool(body.force_download),
    )
    out = start_cooloff_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/cooloff/stop")
def cooloff_stop():
    out = stop_cooloff()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


# ---------------------------------------------------------------------------
# Dawn Cross — 02:00–06:00 Moldova, 5m average cross, pullback fill
# ---------------------------------------------------------------------------

class DawnCrossRunRequest(BaseModel):
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


@app.get("/api/dawn-cross")
def dawn_status(rows: int = Query(0), limit: int = Query(400)):
    return get_dawn_state(include_rows=bool(rows), row_limit=int(limit))


@app.post("/api/dawn-cross/run")
def dawn_run(body: DawnCrossRunRequest):
    fast = ma_line_spec(body.fast_ma, body.fast_ema, body.fast_kama_fast, body.fast_kama_slow)
    slow = ma_line_spec(body.slow_ma, body.slow_ema, body.slow_kama_fast, body.slow_kama_slow)
    pull = ma_line_spec(body.pull_ma, body.pullback_ema, body.pull_kama_fast, body.pull_kama_slow)
    if same_average(fast, slow):
        raise HTTPException(status_code=422, detail="Fast and slow averages must differ")
    start_h = int(body.window_start_hour)
    start_m = int(body.window_start_minute)
    end_h = int(body.window_end_hour)
    end_m = int(body.window_end_minute)
    if not (0 <= start_h <= 23 and 0 <= start_m <= 59):
        raise HTTPException(status_code=422, detail="Window start must be an hour 0–23 and a minute 0–59")
    end_ok = (0 <= end_h <= 23 and 0 <= end_m <= 59) or (end_h == 24 and end_m == 0)
    if not end_ok:
        raise HTTPException(status_code=422, detail="Window end must be an hour 0–23 and a minute 0–59")
    if start_h * 60 + start_m == end_h * 60 + end_m:
        raise HTTPException(status_code=422, detail="Window start and end must differ")
    sl = float(body.sl_pts)
    tp = float(body.tp_pts)
    if sl <= 0 or tp <= 0:
        raise HTTPException(status_code=422, detail="SL and TP must be greater than 0")
    params = DawnCrossJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        timezone=body.timezone or "Europe/Chisinau",
        window_start_hour=start_h,
        window_start_minute=start_m,
        window_end_hour=end_h,
        window_end_minute=end_m,
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
        sl_pts=sl,
        tp_pts=tp,
        flatten_hour=max(0, min(23, int(body.flatten_hour))),
        one_trade_per_day=bool(body.one_trade_per_day),
        force_download=bool(body.force_download),
    )
    out = start_dawn_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/dawn-cross/stop")
def dawn_stop():
    out = stop_dawn()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out



# ---------------------------------------------------------------------------
# Inverse FVG (IFVG after liquidity raid)
# ---------------------------------------------------------------------------


class FvgRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-05-01"
    date_to: str = "2025-06-01"
    timeframe_min: int = 15
    swing_lookback: int = 3
    entry_mode: str = "first_touch"
    sl_mode: str = "far_edge"
    hours: float = 6.0
    thresholds: list[float] = Field(
        default_factory=lambda: [100, 200, 500, 800, 1000, 1200, 1500, 2000]
    )
    adverse_mult: float = 1.0
    side_filter: str = "both"
    max_wait_bars: int = 24
    fvg_after_raid_bars: int = 8
    entry_hours_utc: Optional[list[int]] = None
    entry_weekdays: Optional[list[int]] = None
    workers: int = 3
    force_download: bool = False


@app.get("/api/fvg")
def fvg_status(
    rows: int = Query(0),
    limit: int = Query(400),
):
    return get_fvg_state(include_rows=bool(rows), row_limit=int(limit))


@app.post("/api/fvg/run")
def fvg_run(body: FvgRunRequest):
    thr = list(body.thresholds or [500.0])
    eh = body.entry_hours_utc
    if eh is not None:
        eh = [int(h) for h in eh]
        if not eh:
            eh = None
    ew = body.entry_weekdays
    if ew is not None:
        ew = [int(d) for d in ew]
        if not ew:
            ew = None
    params = FvgJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        timeframe_min=int(body.timeframe_min or 15),
        swing_lookback=max(1, int(body.swing_lookback or 3)),
        entry_mode=str(body.entry_mode or "first_touch"),
        sl_mode=str(body.sl_mode or "far_edge"),
        hours=float(body.hours or 6.0),
        thresholds=[float(x) for x in thr],
        adverse_mult=float(body.adverse_mult if body.adverse_mult is not None else 1.0),
        side_filter=str(body.side_filter or "both"),
        max_wait_bars=max(1, int(body.max_wait_bars or 24)),
        fvg_after_raid_bars=max(1, int(body.fvg_after_raid_bars or 8)),
        entry_hours_utc=eh,
        entry_weekdays=ew,
        workers=max(1, min(6, int(body.workers or 1))),
        force_download=bool(body.force_download),
    )
    out = start_fvg_job(params)
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "busy")
    return out


@app.post("/api/fvg/stop")
def fvg_stop():
    out = stop_fvg()
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
