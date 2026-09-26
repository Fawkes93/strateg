"""Catalog and chart routes for Overnight break."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from zoneinfo import ZoneInfo

from backtest.candle_packs import load_candles_range
from backtest.candles import Candle, aggregate_tf, to_utc
from backtest.overnight_break import entry_label
from backtest.overnight_store import delete_run, get_run, get_trade, list_runs, list_trades

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

router = APIRouter()


def _ema_points(closes: List[float], times: List[int], period: int) -> List[Dict[str, Any]]:
    """Same recurrence as the overnight engine: seed on the first close."""
    if period < 1 or len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    e = closes[0]
    out: List[Dict[str, Any]] = []
    for i, c in enumerate(closes):
        if i:
            e = c * k + e * (1.0 - k)
        if i + 1 >= period:
            out.append({"time": times[i], "value": e})
    return out


def _snap(opens: List[int], iso: Optional[str]) -> Optional[int]:
    if not iso or not opens:
        return None
    try:
        t = int(datetime.fromisoformat(str(iso)).timestamp())
    except ValueError:
        return None
    best = None
    for ot in opens:
        if ot <= t:
            best = ot
        else:
            break
    return best


@router.get("/api/overnight/runs")
def overnight_runs():
    return {"runs": list_runs()}


@router.delete("/api/overnight/runs/{run_id}")
def overnight_delete_run(run_id: int):
    if not delete_run(None, run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"ok": True, "id": run_id}


@router.get("/api/overnight/trades")
def overnight_trades(
    run_id: Optional[int] = None,
    side: Optional[str] = None,
    entry_reason: Optional[str] = None,
    exit_reason: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    rows = list_trades(
        None,
        run_id=run_id,
        side=side,
        entry_reason=entry_reason,
        exit_reason=exit_reason,
        date_from=date_from,
        date_to=date_to,
    )
    return {"trades": rows, "n": len(rows)}


@router.get("/api/overnight/trade/{trade_id}")
def overnight_trade(trade_id: int):
    row = get_trade(None, trade_id)
    if not row:
        raise HTTPException(status_code=404, detail="trade not found")
    return row


@router.get("/api/overnight/chart-data")
def overnight_chart_data(trade_id: int = Query(...)):
    trade = get_trade(None, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    run = get_run(None, int(trade["run_id"])) or {}
    params = run.get("params") or {}
    tz_name = str(params.get("timezone") or run.get("timezone") or "Europe/Bucharest")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
        tz_name = "UTC"
    d = date.fromisoformat(str(trade["local_date"]))
    flatten_h = int(params.get("flatten_hour") or 18)
    flatten_h = min(23, max(0, flatten_h))
    start = datetime.combine(d, time(0, 0), tzinfo=tz) - timedelta(hours=18)
    end = datetime.combine(d, time(flatten_h, 0), tzinfo=tz) + timedelta(hours=2)
    symbol = str(run.get("symbol") or "XAUUSD").replace("/", "")
    tf = int(params.get("ema_tf_min") or 15)
    bars: List[Candle] = []
    try:
        fine = load_candles_range(symbol, start, end, tf_min=5, force=False)
        bars = aggregate_tf(fine, tf) if tf != 5 else list(fine)
    except Exception:
        bars = []
    candles_out: List[Dict[str, Any]] = []
    opens: List[int] = []
    closes: List[float] = []
    for c in bars:
        ot = int(to_utc(c.open_time).timestamp())
        if ot < int(to_utc(start).timestamp()) or ot >= int(to_utc(end).timestamp()):
            continue
        opens.append(ot)
        closes.append(c.close)
        candles_out.append(
            {"time": ot, "open": c.open, "high": c.high, "low": c.low, "close": c.close}
        )
    period = int(params.get("ema_period") or 21)
    extras = trade.get("extras") or {}
    markers = []
    break_at = _snap(opens, trade.get("break_ts"))
    entry_at = _snap(opens, trade.get("entry_ts"))
    exit_at = _snap(opens, trade.get("exit_ts"))
    side = str(trade.get("side") or "")
    if break_at is not None and break_at == entry_at:
        markers.append(
            {
                "time": entry_at,
                "position": "belowBar" if side == "UP" else "aboveBar",
                "color": "#3d9cf0",
                "shape": "arrowUp" if side == "UP" else "arrowDown",
                "text": "Break · " + entry_label(str(trade.get("entry_reason") or "")),
            }
        )
    else:
        if break_at is not None:
            markers.append(
                {
                    "time": break_at,
                    "position": "aboveBar" if side == "UP" else "belowBar",
                    "color": "#e6b450",
                    "shape": "square",
                    "text": "Break",
                }
            )
        if entry_at is not None:
            markers.append(
                {
                    "time": entry_at,
                    "position": "belowBar" if side == "UP" else "aboveBar",
                    "color": "#3d9cf0",
                    "shape": "arrowUp" if side == "UP" else "arrowDown",
                    "text": entry_label(str(trade.get("entry_reason") or "")),
                }
            )
    if exit_at is not None:
        markers.append(
            {
                "time": exit_at,
                "position": "aboveBar" if side == "UP" else "belowBar",
                "color": "#f07178" if str(trade.get("exit_reason")) == "sl" else "#3ecf8e",
                "shape": "circle",
                "text": str(trade.get("exit_reason") or "exit"),
            }
        )
    return {
        "trade": trade,
        "run": {
            "id": run.get("id"),
            "symbol": run.get("symbol"),
            "timezone": tz_name,
            "data_source": run.get("data_source"),
        },
        "timezone": tz_name,
        "candles": candles_out,
        "ema": _ema_points(closes, opens, period),
        "ema_period": period,
        "tf_min": tf,
        "markers": markers,
        "lines": [
            {"price": trade.get("asia_high"), "color": "#e6b450", "title": "Asia high"},
            {"price": trade.get("asia_low"), "color": "#8b9aab", "title": "Asia low"},
            {"price": trade.get("sl"), "color": "#f07178", "title": "SL", "dashed": True},
            {"price": trade.get("tp"), "color": "#3ecf8e", "title": "TP", "dashed": True},
        ],
        "decision": extras.get("decision") or "",
        "asia": {
            "start_hour": int(params.get("asia_start_hour") or 0),
            "end_hour": int(params.get("asia_end_hour") or 7),
            "flatten_hour": flatten_h,
        },
    }


@router.get("/overnight/results")
def overnight_results_page():
    return FileResponse(WEB_DIR / "overnight_results.html")


@router.get("/overnight/chart")
def overnight_chart_page():
    return FileResponse(WEB_DIR / "overnight_chart.html")
