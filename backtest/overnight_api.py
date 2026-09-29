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
from types import SimpleNamespace

from backtest.overnight_break import entry_label, ma_series_values
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


def _ma_legend(params: Dict[str, Any]) -> str:
    kind = str(params.get("ma_type") or "ema").strip().lower()
    if kind == "kama":
        return (
            "KAMA "
            + str(int(params.get("kama_er") or 10))
            + "/"
            + str(int(params.get("kama_fast") or 2))
            + "/"
            + str(int(params.get("kama_slow") or 30))
        )
    if kind == "hma":
        return "HMA " + str(int(params.get("hma_period") or 21))
    if kind == "zlema":
        return "ZLEMA " + str(int(params.get("zlema_period") or 21))
    return "EMA " + str(int(params.get("ema_period") or 21))


def _ma_points(
    closes: List[float], times: List[int], params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """EMA keeps the chart's full-window recurrence. Other averages use the engine series."""
    kind = str(params.get("ma_type") or "ema").strip().lower()
    if kind not in ("kama", "hma", "zlema"):
        return _ema_points(closes, times, int(params.get("ema_period") or 21))
    spec = SimpleNamespace(
        kama_er=int(params.get("kama_er") or 10),
        kama_fast=int(params.get("kama_fast") or 2),
        kama_slow=int(params.get("kama_slow") or 30),
        hma_period=int(params.get("hma_period") or 21),
        zlema_period=int(params.get("zlema_period") or 21),
    )
    series = ma_series_values(closes, kind, spec)
    out: List[Dict[str, Any]] = []
    for i, value in enumerate(series):
        if value is None:
            continue
        out.append({"time": times[i], "value": value})
    return out


def _price_differs(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return True
    try:
        return abs(float(a) - float(b)) > 1e-6
    except (TypeError, ValueError):
        return True


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
    ma_kind = str(params.get("ma_type") or "ema")
    extras = trade.get("extras") or {}
    markers = []
    break_at = _snap(opens, trade.get("break_ts"))
    entry_at = _snap(opens, trade.get("entry_ts"))
    exit_at = _snap(opens, trade.get("exit_ts"))
    side = str(trade.get("side") or "")
    reason_label = entry_label(str(trade.get("entry_reason") or ""), ma_kind)
    if break_at is not None and break_at == entry_at:
        markers.append(
            {
                "time": entry_at,
                "position": "belowBar" if side == "UP" else "aboveBar",
                "color": "#3d9cf0",
                "shape": "arrowUp" if side == "UP" else "arrowDown",
                "text": "Break · " + reason_label,
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
                    "text": reason_label,
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
    lines: List[Dict[str, Any]] = [
        {"price": trade.get("asia_high"), "color": "#e6b450", "title": "Asia high"},
        {"price": trade.get("asia_low"), "color": "#8b9aab", "title": "Asia low"},
        {"price": trade.get("sl"), "color": "#f07178", "title": "SL", "dashed": True},
        {"price": trade.get("tp"), "color": "#3ecf8e", "title": "TP", "dashed": True},
    ]
    fib_high = extras.get("fib_high")
    fib_low = extras.get("fib_low")
    fib_level = extras.get("fib_level")
    if fib_high is not None and _price_differs(fib_high, trade.get("asia_high")):
        lines.append({"price": fib_high, "color": "#d98a3a", "title": "Fib high"})
    if fib_low is not None and _price_differs(fib_low, trade.get("asia_low")):
        lines.append({"price": fib_low, "color": "#6f8fdb", "title": "Fib low"})
    if fib_level is not None:
        lines.append(
            {"price": fib_level, "color": "#c084fc", "title": "Fib level", "dashed": True}
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
        "ema": _ma_points(closes, opens, params),
        "ema_period": period,
        "ma_label": _ma_legend(params),
        "tf_min": tf,
        "markers": markers,
        "lines": lines,
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
