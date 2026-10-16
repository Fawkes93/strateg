"""Run / stop / status, catalog, and chart routes for Asia pullback."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from zoneinfo import ZoneInfo

from backtest.asia_pullback import (
    AsiaPullbackParams,
    _ma_asof,
    _ma_values,
    normalize_params,
)
from backtest.asia_pullback_jobs import (
    AsiaPullbackJobParams,
    get_asia_pullback_state,
    start_asia_pullback_job,
    stop_asia_pullback,
)
from backtest.asia_pullback_store import (
    delete_run,
    get_run,
    get_trade,
    list_runs,
    list_trades,
    sync_json_catalog,
)
from backtest.candle_packs import load_candles_range
from backtest.candles import Candle, aggregate_tf, to_utc

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

router = APIRouter()

_ENTRY_LABELS = {
    "leg_fib": "Fib of the leg",
    "box_fib": "Fib of the box",
    "ema": "Moving average",
    "close5m": "5m close",
    "reversal": "Reversal",
}


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


def _ma_legend(params: Dict[str, Any]) -> str:
    kind = str(params.get("ma_type") or "ema").strip().lower()
    if kind == "kama":
        return (
            "KAMA "
            + str(int(params.get("ema_period") or 20))
            + "/"
            + str(int(params.get("kama_fast") or 2))
            + "/"
            + str(int(params.get("kama_slow") or 30))
        )
    period = int(params.get("ema_period") or 20)
    if kind == "hma":
        return "HMA " + str(period)
    if kind == "zlema":
        return "ZLEMA " + str(period)
    return "EMA " + str(period)


def _entry_label(reason: str, params: Dict[str, Any]) -> str:
    key = str(reason or "").strip()
    if key == "ema":
        return _ma_legend(params)
    return _ENTRY_LABELS.get(key, key or "Entry")


def _price_differs(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return True
    try:
        return abs(float(a) - float(b)) > 1e-6
    except (TypeError, ValueError):
        return True


def _event_time(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(str(iso)).timestamp())
    except ValueError:
        return None


def snap_bar(opens: List[int], iso: Optional[str], *, at_close: bool = False) -> Optional[int]:
    """Latest 15m open at or before the event.

    A close timestamp equals the next bar's open. at_close keeps that print
    on the bar that just finished.
    """
    t = _event_time(iso)
    if t is None or not opens:
        return None
    best = None
    for ot in opens:
        if at_close:
            if ot < t:
                best = ot
            else:
                break
        elif ot <= t:
            best = ot
        else:
            break
    return best


def _entry_at_close(trade: Dict[str, Any]) -> bool:
    extras = trade.get("extras") or {}
    confirm = str(trade.get("confirm_mode") or extras.get("confirm_mode") or "")
    reason = str(trade.get("entry_reason") or "")
    return confirm == "close5m" or reason == "reversal"


def chart_markers(trade: Dict[str, Any], opens: List[int], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    side = str(trade.get("side") or "")
    reason = _entry_label(str(trade.get("entry_reason") or ""), params)
    break_at = snap_bar(opens, trade.get("break_ts"), at_close=True)
    entry_at = snap_bar(opens, trade.get("entry_ts"), at_close=_entry_at_close(trade))
    exit_at = snap_bar(
        opens,
        trade.get("exit_ts"),
        at_close=str(trade.get("exit_reason") or "") == "flatten",
    )
    markers: List[Dict[str, Any]] = []
    if break_at is not None and break_at == entry_at:
        markers.append(
            {
                "time": entry_at,
                "position": "belowBar" if side == "UP" else "aboveBar",
                "color": "#3d9cf0",
                "shape": "arrowUp" if side == "UP" else "arrowDown",
                "text": "Break · " + reason,
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
                    "text": reason,
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
    return _merge_markers(markers)


def _merge_markers(markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One marker per bar. A shared bar keeps the later event's shape and both labels."""
    merged: List[Dict[str, Any]] = []
    for marker in markers:
        if merged and merged[-1]["time"] == marker["time"]:
            prev = merged[-1]
            prev["text"] = str(prev.get("text") or "") + " · " + str(marker.get("text") or "")
            prev["position"] = marker["position"]
            prev["color"] = marker["color"]
            prev["shape"] = marker["shape"]
            continue
        merged.append(dict(marker))
    return merged


def chart_lines(trade: Dict[str, Any]) -> List[Dict[str, Any]]:
    extras = trade.get("extras") or {}
    level = trade.get("level")
    if level is None:
        level = extras.get("level")
    extreme = trade.get("impulse_extreme")
    if extreme is None:
        extreme = extras.get("impulse_extreme")
    reason = str(trade.get("entry_reason") or "")
    level_title = "Shelf" if reason == "reversal" else "Level"
    lines: List[Dict[str, Any]] = [
        {"price": trade.get("box_high"), "color": "#e6b450", "title": "Box high"},
        {"price": trade.get("box_low"), "color": "#8b9aab", "title": "Box low"},
        {"price": trade.get("sl"), "color": "#f07178", "title": "SL", "dashed": True},
        {"price": trade.get("tp"), "color": "#3ecf8e", "title": "TP", "dashed": True},
    ]
    if level is not None:
        lines.append({"price": level, "color": "#c084fc", "title": level_title, "dashed": True})
    if extreme is not None and _price_differs(extreme, trade.get("box_high")) and _price_differs(
        extreme, trade.get("box_low")
    ):
        lines.append({"price": extreme, "color": "#d98a3a", "title": "Impulse"})
    return lines


def _params_obj(raw: Dict[str, Any]) -> AsiaPullbackParams:
    params = AsiaPullbackParams()
    for key, value in (raw or {}).items():
        if hasattr(params, key):
            setattr(params, key, value)
    try:
        return normalize_params(params)
    except (TypeError, ValueError):
        return params


def _ma_points(
    fine: List[Candle],
    display: List[Candle],
    raw_params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if str(raw_params.get("level_ref") or "") != "ema":
        return []
    params = _params_obj(raw_params)
    m15 = aggregate_tf(fine, 15)
    tf = int(params.ema_tf_min or 60)
    ma_bars = m15 if tf <= 15 else aggregate_tf(m15, tf)
    if not ma_bars:
        return []
    values = _ma_values([c.close for c in ma_bars], params)
    closes = [to_utc(c.close_time) for c in ma_bars]
    out: List[Dict[str, Any]] = []
    for bar in display:
        value = _ma_asof(closes, values, bar.open_time)
        if value is None:
            continue
        out.append({"time": int(to_utc(bar.open_time).timestamp()), "value": float(value)})
    return out


def _clock(hour: Any, minute: Any) -> str:
    try:
        h = int(hour)
        m = int(minute or 0)
    except (TypeError, ValueError):
        return "—"
    return f"{h:02d}:{m:02d}"


def decision_text(trade: Dict[str, Any]) -> str:
    if str(trade.get("entry_reason") or "") == "reversal":
        return (
            "The shelf is the prior high or low that rejected. "
            "Stop sits beyond the rejection wick. "
            "The break marker is that rejection bar. "
            "Entry and exit sit on the 15-minute bar that contained them."
        )
    return (
        "Box high and low are the locked midnight box. "
        "The level is the resting pullback. "
        "Stop and target are this trade. "
        "The break sits on the 15-minute bar that closed through the edge. "
        "Entry and exit sit on the bar that contained them."
    )


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


@router.get("/api/asia-pullback/runs")
def asia_pullback_runs():
    sync_json_catalog()
    return {"runs": list_runs()}


@router.delete("/api/asia-pullback/runs/{run_id}")
def asia_pullback_delete_run(run_id: int):
    if not delete_run(None, run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"ok": True, "id": run_id}


@router.get("/api/asia-pullback/trades")
def asia_pullback_trades(
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


@router.get("/api/asia-pullback/trade/{trade_id}")
def asia_pullback_trade(trade_id: int):
    row = get_trade(None, trade_id)
    if not row:
        raise HTTPException(status_code=404, detail="trade not found")
    return row


@router.get("/api/asia-pullback/chart-data")
def asia_pullback_chart_data(trade_id: int = Query(...)):
    trade = get_trade(None, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    run = get_run(None, int(trade["run_id"])) or {}
    params = run.get("params") or {}
    tz_name = str(params.get("timezone") or run.get("timezone") or "Europe/Bucharest")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
        tz_name = "UTC"
    d = date.fromisoformat(str(trade["local_date"]))
    flatten_h = int(params.get("flatten_hour") or 23)
    flatten_h = min(23, max(0, flatten_h))
    box_h = int(params.get("box_end_hour") or 4)
    box_m = int(params.get("box_end_minute") or 0)
    listen_h = int(params.get("listen_end_hour") or 9)
    listen_m = int(params.get("listen_end_minute") or 0)
    start = datetime.combine(d, time(0, 0), tzinfo=tz) - timedelta(hours=6)
    end = datetime.combine(d, time(flatten_h, 0), tzinfo=tz) + timedelta(hours=2)
    symbol = str(run.get("symbol") or "XAUUSD").replace("/", "")
    want_ma = str(params.get("level_ref") or "") == "ema"
    lookback = timedelta(0)
    if want_ma:
        period = max(1, int(params.get("ema_period") or 20))
        tf_min = max(15, int(params.get("ema_tf_min") or 60))
        lookback = timedelta(minutes=period * 2 * tf_min)
    fine: List[Candle] = []
    try:
        fine = load_candles_range(symbol, start - lookback, end, tf_min=5, force=False)
    except Exception:
        fine = []
    start_ts = int(to_utc(start).timestamp())
    end_ts = int(to_utc(end).timestamp())
    m15 = aggregate_tf(fine, 15)
    display = [
        c
        for c in m15
        if start_ts <= int(to_utc(c.open_time).timestamp()) < end_ts
    ]
    candles_out: List[Dict[str, Any]] = []
    opens: List[int] = []
    for c in display:
        ot = int(to_utc(c.open_time).timestamp())
        opens.append(ot)
        candles_out.append(
            {"time": ot, "open": c.open, "high": c.high, "low": c.low, "close": c.close}
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
        "ema": _ma_points(fine, display, params) if want_ma else [],
        "ema_period": int(params.get("ema_period") or 20),
        "ma_label": _ma_legend(params),
        "tf_min": 15,
        "markers": chart_markers(trade, opens, params),
        "lines": chart_lines(trade),
        "decision": decision_text(trade),
        "session": {
            "box_end": _clock(box_h, box_m),
            "listen_end": _clock(listen_h, listen_m),
            "flatten_hour": flatten_h,
        },
    }


@router.get("/asia-pullback/results")
def asia_pullback_results_page():
    return FileResponse(WEB_DIR / "asia_pullback_results.html")


@router.get("/asia-pullback/chart")
def asia_pullback_chart_page():
    return FileResponse(WEB_DIR / "asia_pullback_chart.html")
