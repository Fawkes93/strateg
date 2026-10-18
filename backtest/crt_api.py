"""Run / stop / status, catalog, and chart routes for CRT."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backtest.candle_packs import load_candles_range
from backtest.candles import Candle, aggregate_tf, to_utc
from backtest.crt import CrtParams, rules_for
from backtest.crt_jobs import CrtJobParams, get_crt_state, start_crt_job, stop_crt
from backtest.crt_store import delete_run, get_run, get_trade, list_runs, list_trades, sync_json_catalog
from backtest.overnight_break import require_zone

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"

router = APIRouter()


class CrtRunRequest(BaseModel):
    symbol: str = "XAUUSD"
    date_from: str = "2025-03-01"
    date_to: str = "2025-04-01"
    timezone: str = "Europe/Bucharest"
    htf_min: int = 60
    ltf_min: int = 5
    structure_bars: int = 24
    pd_filter: bool = True
    equilibrium: float = 0.5
    min_leg_pts: float = 0.0
    min_range_pts: float = 0.0
    entry_mode: str = "fvg"
    fvg_select: str = "extreme"
    fvg_entry: str = "proximal"
    max_fvgs: int = 2
    fvg_wait_htf: int = 3
    sl_mode: str = "beyond_fvg"
    sl_buffer_pts: float = 0.0
    sl_fixed_pts: float = 300.0
    partial_frac: float = 0.5
    partial_rr: float = 1.0
    runner_mode: str = "swing"
    runner_rr: float = 2.0
    max_hold_htf: int = 48
    max_open: int = 2
    session_enabled: bool = False
    session_start_hour: int = 8
    session_start_minute: int = 0
    session_end_hour: int = 17
    session_end_minute: int = 0
    skip_news: bool = False
    side_filter: str = "both"
    cost_pts: float = 0.0
    force_download: bool = False


def _params_from_body(body: CrtRunRequest) -> CrtJobParams:
    return CrtJobParams(
        symbol=body.symbol,
        date_from=body.date_from,
        date_to=body.date_to,
        timezone=body.timezone,
        htf_min=int(body.htf_min),
        ltf_min=int(body.ltf_min),
        structure_bars=int(body.structure_bars),
        pd_filter=bool(body.pd_filter),
        equilibrium=float(body.equilibrium),
        min_leg_pts=float(body.min_leg_pts or 0),
        min_range_pts=float(body.min_range_pts or 0),
        entry_mode=str(body.entry_mode or "fvg"),
        fvg_select=str(body.fvg_select or "extreme"),
        fvg_entry=str(body.fvg_entry or "proximal"),
        max_fvgs=int(body.max_fvgs or 1),
        fvg_wait_htf=int(body.fvg_wait_htf or 1),
        sl_mode=str(body.sl_mode or "beyond_fvg"),
        sl_buffer_pts=float(body.sl_buffer_pts or 0),
        sl_fixed_pts=float(body.sl_fixed_pts or 0),
        partial_frac=float(body.partial_frac),
        partial_rr=float(body.partial_rr),
        runner_mode=str(body.runner_mode or "swing"),
        runner_rr=float(body.runner_rr),
        max_hold_htf=int(body.max_hold_htf),
        max_open=int(body.max_open or 1),
        session_enabled=bool(body.session_enabled),
        session_start_hour=int(body.session_start_hour),
        session_start_minute=int(body.session_start_minute),
        session_end_hour=int(body.session_end_hour),
        session_end_minute=int(body.session_end_minute),
        skip_news=bool(body.skip_news),
        side_filter=str(body.side_filter or "both"),
        cost_pts=float(body.cost_pts or 0),
        force_download=bool(body.force_download),
    )


def _field(trade: Dict[str, Any], key: str) -> Any:
    if trade.get(key) is not None:
        return trade.get(key)
    return (trade.get("extras") or {}).get(key)


def _event_time(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(str(iso)).timestamp())
    except ValueError:
        return None


def snap_bar(opens: List[int], iso: Optional[str], *, at_close: bool = False) -> Optional[int]:
    """Latest bar open at or before the event. A close time belongs to the bar that just finished."""
    stamp = _event_time(iso)
    if stamp is None or not opens:
        return None
    best = None
    for opened in opens:
        if at_close:
            if opened < stamp:
                best = opened
            else:
                break
        elif opened <= stamp:
            best = opened
        else:
            break
    return best


def chart_markers(trade: Dict[str, Any], opens: List[int]) -> List[Dict[str, Any]]:
    side = str(trade.get("side") or "")
    long = side == "UP"
    markers: List[Dict[str, Any]] = []
    range_at = snap_bar(opens, _field(trade, "range_open_ts"))
    sweep_at = snap_bar(opens, _field(trade, "sweep_ts"))
    entry_at = snap_bar(opens, trade.get("entry_ts"))
    partial_at = snap_bar(opens, _field(trade, "partial_ts")) if _field(trade, "partial_hit") else None
    exit_at = snap_bar(
        opens,
        trade.get("exit_ts"),
        at_close=str(trade.get("exit_reason") or "") == "time",
    )
    if range_at is not None:
        markers.append(
            {
                "time": range_at,
                "position": "aboveBar" if long else "belowBar",
                "color": "#8b9aab",
                "shape": "square",
                "text": "Range",
            }
        )
    if sweep_at is not None:
        markers.append(
            {
                "time": sweep_at,
                "position": "belowBar" if long else "aboveBar",
                "color": "#e6b450",
                "shape": "arrowUp" if long else "arrowDown",
                "text": "Sweep",
            }
        )
    if entry_at is not None:
        markers.append(
            {
                "time": entry_at,
                "position": "belowBar" if long else "aboveBar",
                "color": "#3d9cf0",
                "shape": "circle",
                "text": "FVG" if str(trade.get("entry_reason") or "") == "fvg" else "Close",
            }
        )
    if partial_at is not None:
        markers.append(
            {
                "time": partial_at,
                "position": "aboveBar" if long else "belowBar",
                "color": "#c084fc",
                "shape": "circle",
                "text": "1:1",
            }
        )
    if exit_at is not None:
        reason = str(trade.get("exit_reason") or "exit")
        lost = reason in ("sl", "partial_sl")
        markers.append(
            {
                "time": exit_at,
                "position": "aboveBar" if long else "belowBar",
                "color": "#f07178" if lost else "#3ecf8e",
                "shape": "circle",
                "text": reason,
            }
        )
    return _merge_markers(markers)


def _merge_markers(markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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


def _line(price: Any, color: str, title: str, dashed: bool = False) -> Optional[Dict[str, Any]]:
    if price is None:
        return None
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    return {"price": value, "color": color, "title": title, "dashed": dashed}


def chart_lines(trade: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines = [
        _line(_field(trade, "structure_high"), "#d98a3a", "Dealing high"),
        _line(_field(trade, "structure_low"), "#d98a3a", "Dealing low"),
        _line(_field(trade, "crh"), "#e6b450", "CRH"),
        _line(_field(trade, "crl"), "#8b9aab", "CRL"),
        _line(_field(trade, "fvg_top"), "#c084fc", "FVG"),
        _line(_field(trade, "fvg_bottom"), "#c084fc", "FVG", dashed=True),
        _line(trade.get("sl"), "#f07178", "SL", dashed=True),
        _line(_field(trade, "partial_px"), "#3d9cf0", "1:1", dashed=True),
        _line(trade.get("tp"), "#3ecf8e", "Runner", dashed=True),
    ]
    return [line for line in lines if line is not None]


def decision_text(trade: Dict[str, Any]) -> str:
    story = _field(trade, "story")
    if story:
        return str(story)
    return (
        "CRH and CRL are the higher-timeframe range candle. "
        "The sweep wick has to close back inside that range. "
        "The fair value gap is the lower-timeframe entry. "
        "Half of the trade is the 1:1 line. The runner is the other half."
    )


@router.get("/api/crt/rules")
def crt_rules():
    params = CrtParams()
    return {
        "rules": rules_for(params),
        "params": {
            "timezone": params.timezone,
            "htf_min": params.htf_min,
            "ltf_min": params.ltf_min,
            "structure_bars": params.structure_bars,
            "pd_filter": params.pd_filter,
            "equilibrium": params.equilibrium,
            "entry_mode": params.entry_mode,
            "fvg_select": params.fvg_select,
            "fvg_entry": params.fvg_entry,
            "max_fvgs": params.max_fvgs,
            "fvg_wait_htf": params.fvg_wait_htf,
            "sl_mode": params.sl_mode,
            "partial_frac": params.partial_frac,
            "partial_rr": params.partial_rr,
            "runner_mode": params.runner_mode,
            "runner_rr": params.runner_rr,
            "max_hold_htf": params.max_hold_htf,
            "max_open": params.max_open,
        },
        "run": "POST /api/crt/run with JSON. Poll GET /api/crt until running is false. "
        "Trades with an id open at /crt/chart?trade=<id>. The catalog is /crt/results.",
    }


@router.get("/api/crt")
def crt_status():
    return get_crt_state()


@router.post("/api/crt/run")
def crt_run(body: CrtRunRequest):
    out = start_crt_job(_params_from_body(body))
    if not out.get("ok"):
        err = str(out.get("error") or "busy")
        code = 409 if "running" in err.lower() else 400
        raise HTTPException(status_code=code, detail=err)
    return out


@router.post("/api/crt/stop")
def crt_stop():
    out = stop_crt()
    if not out.get("ok"):
        raise HTTPException(status_code=409, detail=out.get("error") or "not running")
    return out


@router.get("/api/crt/runs")
def crt_runs():
    sync_json_catalog()
    return {"runs": list_runs()}


@router.delete("/api/crt/runs/{run_id}")
def crt_delete_run(run_id: int):
    if not delete_run(None, run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"ok": True, "id": run_id}


@router.get("/api/crt/trades")
def crt_trades(
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


@router.get("/api/crt/trade/{trade_id}")
def crt_trade(trade_id: int):
    row = get_trade(None, trade_id)
    if not row:
        raise HTTPException(status_code=404, detail="trade not found")
    return row


@router.get("/api/crt/chart-data")
def crt_chart_data(trade_id: int = Query(...)):
    trade = get_trade(None, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    run = get_run(None, int(trade["run_id"])) or {}
    params = run.get("params") or {}
    tz_name = str(params.get("timezone") or run.get("timezone") or "Europe/Bucharest")
    try:
        require_zone(tz_name)
    except Exception:
        tz_name = "UTC"
    htf = int(params.get("htf_min") or _field(trade, "htf_min") or 60)
    ltf = int(params.get("ltf_min") or _field(trade, "ltf_min") or 5)
    start = _parse_ts(_field(trade, "range_open_ts")) or _parse_ts(trade.get("entry_ts"))
    end = _parse_ts(trade.get("exit_ts")) or start
    if start is None:
        raise HTTPException(status_code=404, detail="trade has no time")
    start = start - timedelta(minutes=htf * 3)
    end = (end or start) + timedelta(minutes=htf * 4)
    symbol = str(run.get("symbol") or "XAUUSD").replace("/", "")
    fine: List[Candle] = []
    try:
        fine = load_candles_range(symbol, start - timedelta(hours=6), end, tf_min=5, force=False)
    except Exception:
        fine = []
    display = fine if ltf <= 5 else aggregate_tf(fine, ltf)
    start_ts = int(to_utc(start).timestamp())
    end_ts = int(to_utc(end).timestamp())
    candles_out: List[Dict[str, Any]] = []
    opens: List[int] = []
    for candle in display:
        opened = int(to_utc(candle.open_time).timestamp())
        if opened < start_ts or opened >= end_ts:
            continue
        opens.append(opened)
        candles_out.append(
            {
                "time": opened,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
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
        "tf_min": ltf,
        "htf_min": htf,
        "markers": chart_markers(trade, opens),
        "lines": chart_lines(trade),
        "decision": decision_text(trade),
    }


def _parse_ts(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso))
    except ValueError:
        return None


@router.get("/crt/results")
def crt_results_page():
    return FileResponse(WEB_DIR / "crt_results.html")


@router.get("/crt/chart")
def crt_chart_page():
    return FileResponse(WEB_DIR / "crt_chart.html")
