#!/usr/bin/env python3
"""Local Strateg research UI — single run + overnight sweep."""

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

WEB_DIR = ROOT / "web"
app = FastAPI(title="Strateg", version="0.4", docs_url="/docs")


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
    workers: int = 4  # process workers for parallel date groups / split variants
    test_range: bool = True
    test_spike: bool = True
    test_spike_neo: bool = False
    test_impulse_retrace: bool = False
    test_range_wick: bool = False
    pairing: str = "together"  # together | grid
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
def batch_schema():
    return batch_param_schema()


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
