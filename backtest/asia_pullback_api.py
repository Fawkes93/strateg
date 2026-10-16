"""Run / stop / status for the Asia pullback tab."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backtest.asia_pullback_jobs import (
    AsiaPullbackJobParams,
    get_asia_pullback_state,
    start_asia_pullback_job,
    stop_asia_pullback,
)

router = APIRouter()


class AsiaPullbackRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-03-01"
    date_to: str = "2025-06-01"
    timezone: str = "Europe/Bucharest"
    box_end_hour: int = 4
    box_end_minute: int = 30
    listen_end_hour: int = 9
    listen_end_minute: int = 0
    break_frac: float = 0.25
    level_ref: str = "leg_fib"
    fib_level: float = 0.382
    ma_type: str = "ema"
    ema_period: int = 20
    ema_tf_min: int = 60
    kama_fast: int = 2
    kama_slow: int = 30
    confirm_mode: str = "touch"
    sl_mode: str = "asia_opposite"
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    sl_cap_pts: float = 0.0
    tp_mode: str = "range_mult"
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.0
    tp_sl_mult: float = 2.0
    flatten_hour: int = 23
    cost_pts: float = 0.0
    reversal: bool = False
    sr_days: int = 5
    sr_min_touches: int = 2
    sr_tol_frac: float = 0.25
    sr_pdhl: bool = True
    workers: int = 2
    force_download: bool = False
    data_source: str = "candles_5m"


@router.get("/api/asia-pullback")
def asia_pullback_status():
    return get_asia_pullback_state()


@router.post("/api/asia-pullback/run")
def asia_pullback_run(body: AsiaPullbackRunRequest):
    params = AsiaPullbackJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        timezone=body.timezone,
        box_end_hour=int(body.box_end_hour),
        box_end_minute=int(body.box_end_minute),
        listen_end_hour=int(body.listen_end_hour),
        listen_end_minute=int(body.listen_end_minute),
        break_frac=float(body.break_frac),
        level_ref=str(body.level_ref or "leg_fib"),
        fib_level=float(body.fib_level),
        ma_type=str(body.ma_type or "ema"),
        ema_period=int(body.ema_period),
        ema_tf_min=int(body.ema_tf_min),
        kama_fast=int(body.kama_fast or 2),
        kama_slow=int(body.kama_slow or 30),
        confirm_mode=str(body.confirm_mode or "touch"),
        sl_mode=str(body.sl_mode or "asia_opposite"),
        sl_fixed_pts=float(body.sl_fixed_pts),
        sl_range_mult=float(body.sl_range_mult),
        sl_cap_pts=float(body.sl_cap_pts or 0.0),
        tp_mode=str(body.tp_mode or "range_mult"),
        tp_fixed_pts=float(body.tp_fixed_pts),
        tp_range_mult=float(body.tp_range_mult),
        tp_sl_mult=float(body.tp_sl_mult if body.tp_sl_mult is not None else 2.0),
        flatten_hour=int(body.flatten_hour),
        cost_pts=float(body.cost_pts or 0.0),
        reversal=bool(body.reversal),
        sr_days=int(body.sr_days or 5),
        sr_min_touches=int(body.sr_min_touches or 2),
        sr_tol_frac=float(body.sr_tol_frac if body.sr_tol_frac is not None else 0.25),
        sr_pdhl=bool(body.sr_pdhl),
        workers=max(1, min(6, int(body.workers or 1))),
        force_download=bool(body.force_download),
        data_source=str(body.data_source or "candles_5m"),
    )
    out = start_asia_pullback_job(params)
    if not out.get("ok"):
        err = str(out.get("error") or "busy")
        code = 409 if "running" in err.lower() else 400
        raise HTTPException(status_code=code, detail=err)
    return out


@router.post("/api/asia-pullback/stop")
def asia_pullback_stop():
    out = stop_asia_pullback()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out
