"""Candle Range Theory, trading with the trend.

The model is the trend continuation from the CRT video, not the one-hour
candle before New York (that one fades the trend). An agent can run it from
the README section "CRT tab" or from GET /api/crt/rules without reading this
file. This module is the rules.

Higher timeframe, default 60 minutes:

1. The dealing range is the highest high and the lowest low of the last
   `structure_bars` closed bars before the range candle.
2. Up when that low prints before that high. Down when the high prints first.
   The same bar is chop and is skipped.
3. Uptrend: the range candle is bearish and stays inside the dealing range.
   Downtrend: it is bullish and stays inside. With the premium/discount filter
   on, a long range candle closes at or below equilibrium (discount) and a
   short closes at or above it (premium).
4. The next candle is the only sweep. A long must trade below the range low
   and close back inside. A close through the low is invalid. Shorts mirror
   that on the range high.

Lower timeframe, default 5 minutes:

5. `fvg` waits for a fair value gap that starts on or after the sweep wick.
   The limit goes live only after the sweep candle and the gap's third candle
   have both closed. `sweep_close` enters at the sweep candle's close.
6. The stop is beyond the gap, beyond the sweep wick, or a fixed point distance.
7. `partial_frac` of the trade closes at `partial_rr` R. The rest runs to the
   dealing-range extreme, or to `runner_rr` when that extreme is not beyond
   the partial. A partial then a stop is a scratch when the fraction is 0.5
   and the partial is 1 R.
8. Fills use lower-timeframe OHLC. A bar that trades the stop and a target
   takes the stop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import Candle, aggregate_tf, to_utc
from backtest.config import point_size
from backtest.dukascopy import reaktor_symbol
from backtest.news_calendar import is_news_day
from backtest.overnight_break import require_zone

HTF_CHOICES = (15, 30, 60, 120, 240)
LTF_CHOICES = (5, 15, 30)
ENTRY_MODES = ("fvg", "sweep_close")
FVG_SELECTS = ("first", "extreme", "all")
FVG_ENTRIES = ("proximal", "ce", "distal")
SL_MODES = ("beyond_fvg", "beyond_sweep", "fixed")
RUNNER_MODES = ("swing", "rr")
SIDES = ("both", "long", "short")

_EPS = 1e-9


@dataclass
class CrtParams:
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


def normalize_params(params: CrtParams) -> CrtParams:
    """Return params with clean types, or raise ValueError."""
    params.timezone = str(params.timezone or "Europe/Bucharest").strip() or "Europe/Bucharest"
    require_zone(params.timezone)
    params.htf_min = int(params.htf_min)
    params.ltf_min = int(params.ltf_min)
    if params.htf_min not in HTF_CHOICES:
        raise ValueError("htf_min must be one of 15, 30, 60, 120, 240")
    if params.ltf_min not in LTF_CHOICES:
        raise ValueError("ltf_min must be one of 5, 15, 30")
    if params.ltf_min >= params.htf_min or params.htf_min % params.ltf_min != 0:
        raise ValueError("ltf_min must divide htf_min and be smaller")
    params.structure_bars = int(params.structure_bars)
    if params.structure_bars < 4 or params.structure_bars > 200:
        raise ValueError("structure_bars must be from 4 to 200")
    params.pd_filter = bool(params.pd_filter)
    params.equilibrium = float(params.equilibrium)
    if not 0.05 <= params.equilibrium <= 0.95:
        raise ValueError("equilibrium must be from 0.05 to 0.95")
    params.min_leg_pts = max(0.0, float(params.min_leg_pts or 0))
    params.min_range_pts = max(0.0, float(params.min_range_pts or 0))
    params.entry_mode = str(params.entry_mode or "fvg").strip().lower()
    if params.entry_mode not in ENTRY_MODES:
        raise ValueError("entry_mode must be fvg or sweep_close")
    params.fvg_select = str(params.fvg_select or "extreme").strip().lower()
    if params.fvg_select not in FVG_SELECTS:
        raise ValueError("fvg_select must be first, extreme, or all")
    params.fvg_entry = str(params.fvg_entry or "proximal").strip().lower()
    if params.fvg_entry not in FVG_ENTRIES:
        raise ValueError("fvg_entry must be proximal, ce, or distal")
    params.max_fvgs = max(1, min(5, int(params.max_fvgs or 1)))
    params.fvg_wait_htf = max(1, min(20, int(params.fvg_wait_htf or 1)))
    params.sl_mode = str(params.sl_mode or "beyond_fvg").strip().lower()
    if params.sl_mode not in SL_MODES:
        raise ValueError("sl_mode must be beyond_fvg, beyond_sweep, or fixed")
    params.sl_buffer_pts = max(0.0, float(params.sl_buffer_pts or 0))
    params.sl_fixed_pts = float(params.sl_fixed_pts or 0)
    if params.sl_mode == "fixed" and params.sl_fixed_pts <= 0:
        raise ValueError("sl_fixed_pts must be positive when the stop is fixed")
    params.partial_frac = float(params.partial_frac)
    if not 0.0 <= params.partial_frac <= 1.0:
        raise ValueError("partial_frac must be from 0 to 1")
    params.partial_rr = float(params.partial_rr)
    if params.partial_rr <= 0:
        raise ValueError("partial_rr must be positive")
    params.runner_mode = str(params.runner_mode or "swing").strip().lower()
    if params.runner_mode not in RUNNER_MODES:
        raise ValueError("runner_mode must be swing or rr")
    params.runner_rr = float(params.runner_rr)
    if params.runner_rr <= 0:
        raise ValueError("runner_rr must be positive")
    params.max_hold_htf = max(1, min(200, int(params.max_hold_htf or 1)))
    params.max_open = max(1, min(10, int(params.max_open or 1)))
    params.session_enabled = bool(params.session_enabled)
    for name in (
        "session_start_hour",
        "session_end_hour",
    ):
        value = int(getattr(params, name))
        if not 0 <= value <= 23:
            raise ValueError(name + " must be from 0 to 23")
        setattr(params, name, value)
    for name in (
        "session_start_minute",
        "session_end_minute",
    ):
        value = int(getattr(params, name))
        if not 0 <= value <= 59:
            raise ValueError(name + " must be from 0 to 59")
        setattr(params, name, value)
    params.skip_news = bool(params.skip_news)
    params.side_filter = str(params.side_filter or "both").strip().lower()
    if params.side_filter not in SIDES:
        raise ValueError("side_filter must be both, long, or short")
    params.cost_pts = max(0.0, float(params.cost_pts or 0))
    return params


def rules_for(params: Optional[CrtParams] = None) -> List[Dict[str, str]]:
    """Plain sentences for the UI and for an agent. Numbers come from params."""
    p = normalize_params(params or CrtParams())
    pd = (
        "On. A long range candle must close at or below "
        + _num(p.equilibrium)
        + " of the dealing range (discount). A short must close at or above it (premium)."
        if p.pd_filter
        else "Off. Discount and premium are not required."
    )
    if p.entry_mode == "sweep_close":
        entry = "Enter at the sweep candle's close. No fair value gap."
    else:
        entry = (
            "After the sweep closes, use the first "
            + str(p.ltf_min)
            + "m fair value gap whose first candle is the sweep wick or later. "
            + "The limit is the "
            + p.fvg_entry
            + " edge of the gap. It goes live only once the sweep candle and the gap's third candle have closed. "
            + "Selection is "
            + p.fvg_select
            + ", at most "
            + str(p.max_fvgs)
            + ". The order expires "
            + str(p.fvg_wait_htf)
            + " higher-timeframe bars after the sweep close."
        )
    if p.sl_mode == "fixed":
        stop = "Stop is " + _num(p.sl_fixed_pts) + " points from the entry."
    elif p.sl_mode == "beyond_sweep":
        stop = (
            "Stop is "
            + _num(p.sl_buffer_pts)
            + " points beyond the sweep wick."
        )
    else:
        stop = (
            "Stop is "
            + _num(p.sl_buffer_pts)
            + " points beyond the far side of the gap. A sweep-close entry uses the sweep wick instead."
        )
    if p.runner_mode == "swing":
        runner = (
            "The rest targets the far side of the dealing range when that price is beyond the partial. "
            "Otherwise it targets "
            + _num(p.runner_rr)
            + " R."
        )
    else:
        runner = "The rest targets " + _num(p.runner_rr) + " R."
    if p.session_enabled:
        session = (
            "On. The sweep candle must open from "
            + _clock(p.session_start_hour, p.session_start_minute)
            + " until "
            + _clock(p.session_end_hour, p.session_end_minute)
            + " in "
            + p.timezone
            + "."
        )
    else:
        session = "Off. Any hour in " + p.timezone + " can set up."
    news = (
        "On. Days in the gold news calendar are skipped on every symbol."
        if p.skip_news
        else "Off. The gold news calendar is not applied."
    )
    return [
        {
            "id": "trend",
            "body": (
                "Dealing range is the highest high and lowest low of the last "
                + str(p.structure_bars)
                + " closed "
                + str(p.htf_min)
                + "m bars before the range candle. Up when the low prints before the high. "
                + "Down when the high prints first. The same bar is chop and is skipped."
            ),
        },
        {
            "id": "range",
            "body": (
                "Uptrend range candles are bearish and stay inside the dealing range. "
                "Downtrend range candles are bullish and stay inside it. "
                "Only the next candle may sweep."
            ),
        },
        {
            "id": "premium",
            "body": pd,
        },
        {
            "id": "sweep",
            "body": (
                "A long sweep trades below the range low and closes back inside: "
                "above the range low and at or below the range high. "
                "A close through the low invalidates it. Shorts mirror that on the range high. "
                "Wait for the candle to close."
            ),
        },
        {
            "id": "entry",
            "body": entry,
        },
        {
            "id": "stop",
            "body": stop,
        },
        {
            "id": "partial",
            "body": (
                "Close "
                + _num(p.partial_frac)
                + " of the position at "
                + _num(p.partial_rr)
                + " R. "
                + runner
                + " If the partial fills and the stop is hit later, the partial is kept and the rest loses 1 R. "
                + "At 0.5 and 1 R that trade is a scratch."
            ),
        },
        {
            "id": "hold",
            "body": (
                "Still-open trades flatten after "
                + str(p.max_hold_htf)
                + " higher-timeframe bars, or when the candles end. "
                + "At most "
                + str(p.max_open)
                + " trades are open at once."
            ),
        },
        {
            "id": "session",
            "body": session,
        },
        {
            "id": "news",
            "body": news,
        },
        {
            "id": "fills",
            "body": (
                "Fills are "
                + str(p.ltf_min)
                + "m OHLC, built from 5m candles. "
                + "A bar that trades both the stop and a target takes the stop. "
                + "A gap through a limit fills at the open. "
                + "This is the trend model. It does not fade the hour before New York."
            ),
        },
    ]


def trend_of(window: Sequence[Candle]) -> Optional[str]:
    """'up', 'down', or None when the extreme high and low share a bar."""
    if len(window) < 2:
        return None
    hi_i = max(range(len(window)), key=lambda i: (window[i].high, i))
    lo_i = max(range(len(window)), key=lambda i: (-window[i].low, i))
    if hi_i > lo_i:
        return "up"
    if lo_i > hi_i:
        return "down"
    return None


def cap_open(
    rows: Sequence[Dict[str, Any]], max_open: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Keep trades in entry order while fewer than max_open are still on."""
    kept: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    limit = max(1, int(max_open))
    ordered = sorted(rows, key=lambda r: (str(r.get("entry_ts") or ""), int(r.get("_seq") or 0)))
    for row in ordered:
        entry = str(row.get("entry_ts") or "")
        live = sum(1 for prev in kept if str(prev.get("exit_ts") or "") > entry)
        if live >= limit:
            skipped.append(row)
            continue
        kept.append(row)
    return kept, skipped


def run_crt_on_candles(
    candles: Sequence[Candle],
    *,
    symbol: str,
    params: CrtParams,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    progress: Optional[Callable[[int, int], None]] = None,
    stop: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Scan 5-minute candles. `date_to` is exclusive on the local entry date."""
    params = normalize_params(params)
    ps = point_size(reaktor_symbol(symbol))
    tz = require_zone(params.timezone)
    d0 = _as_date(date_from)
    d1 = _as_date(date_to)
    fine = [c for c in candles if c.is_closed or True]
    fine = sorted(fine, key=lambda c: to_utc(c.open_time))
    if params.ltf_min == 5:
        ltf = fine
    else:
        ltf = aggregate_tf(fine, params.ltf_min)
    htf = aggregate_tf(fine, params.htf_min)
    groups = _groups(ltf, params.htf_min)
    rows: List[Dict[str, Any]] = []
    skips: List[Dict[str, Any]] = []
    total = max(0, len(htf) - params.structure_bars - 1)
    seq = 0
    cancelled = False
    for i in range(params.structure_bars, len(htf) - 1):
        if stop and stop():
            cancelled = True
            break
        if progress and (i == params.structure_bars or (i % 24) == 0):
            progress(i - params.structure_bars, total)
        window = htf[i - params.structure_bars : i]
        trend = trend_of(window)
        if trend is None:
            continue
        side = "UP" if trend == "up" else "DOWN"
        if params.side_filter == "long" and side != "UP":
            continue
        if params.side_filter == "short" and side != "DOWN":
            continue
        rng = htf[i]
        nxt = htf[i + 1]
        struct_high = max(c.high for c in window)
        struct_low = min(c.low for c in window)
        if struct_high - struct_low <= _EPS:
            continue
        if not _range_ok(rng, side, struct_high, struct_low, params, ps):
            continue
        sweep_state = _sweep_state(rng, nxt, side)
        if sweep_state is None:
            continue
        day, weekday = _local_day(nxt.open_time, tz)
        if not _in_window(day, d0, d1):
            continue
        if sweep_state == "close_through":
            skips.append(_skip(day, weekday, "close_through", side, "The next candle closed through the range."))
            continue
        if sweep_state == "no_reclaim":
            skips.append(_skip(day, weekday, "no_reclaim", side, "The sweep did not close back inside the range."))
            continue
        if not _in_session(params, nxt.open_time, tz):
            skips.append(_skip(day, weekday, "session", side, "The sweep candle opened outside the session."))
            continue
        if params.skip_news and is_news_day(day):
            skips.append(_skip(day, weekday, "news", side, "Gold news calendar."))
            continue
        ltf_idxs = groups.get(_bucket(nxt.open_time, params.htf_min), [])
        made = _orders_for_setup(
            side=side,
            rng=rng,
            nxt=nxt,
            ltf=ltf,
            ltf_idxs=ltf_idxs,
            struct_high=struct_high,
            struct_low=struct_low,
            params=params,
            ps=ps,
        )
        if not made:
            skips.append(_skip(day, weekday, "no_fill", side, "No entry before the order expired."))
            continue
        filled_any = False
        for order in made:
            trade = _simulate(order, ltf, params, ps)
            if trade is None:
                continue
            entry_day, entry_wd = _local_day(trade["entry_bar"].open_time, tz)
            if not _in_window(entry_day, d0, d1):
                continue
            filled_any = True
            seq += 1
            rows.append(
                _trade_row(
                    trade,
                    seq=seq,
                    day=entry_day,
                    weekday=entry_wd,
                    side=side,
                    rng=rng,
                    nxt=nxt,
                    struct_high=struct_high,
                    struct_low=struct_low,
                    params=params,
                    ps=ps,
                    symbol=symbol,
                )
            )
        if not filled_any:
            skips.append(_skip(day, weekday, "no_fill", side, "The level was not traded before it expired."))
    if progress:
        progress(total, total)
    kept, crowded = cap_open(rows, params.max_open)
    for row in crowded:
        skips.append(
            _skip(
                _as_date(row.get("local_date")) or date.min,
                str(row.get("weekday") or ""),
                "max_open",
                str(row.get("side") or ""),
                "Another trade was still open.",
            )
        )
    for row in kept:
        row.pop("_seq", None)
    return {
        "rows": kept,
        "skips": skips,
        "cancelled": cancelled,
        "ticks": len(fine),
        "symbol": reaktor_symbol(symbol),
        "point_size": ps,
    }


def summarize_crt(
    raw: Dict[str, Any],
    params: CrtParams,
    *,
    symbol: str,
    data_source: str = "candles_5m",
    cancelled: bool = False,
) -> Dict[str, Any]:
    rows = list(raw.get("rows") or [])
    skips = list(raw.get("skips") or [])
    stats = _stats(rows)
    out = {
        "kind": "crt",
        "symbol": raw.get("symbol") or reaktor_symbol(symbol),
        "data_source": data_source,
        "point_size": raw.get("point_size") or point_size(reaktor_symbol(symbol)),
        "cancelled": bool(cancelled or raw.get("cancelled")),
        "params": asdict(params),
        "rules": rules_for(params),
        "rows": rows,
        "skips": skips,
        "skipped": len(skips),
        "skip_reasons": _skip_counts(skips),
        "by_month": _by_month(rows),
        "ticks": int(raw.get("ticks") or 0),
    }
    out.update(stats)
    return out


# --- setup geometry -------------------------------------------------------


def _range_ok(
    rng: Candle,
    side: str,
    struct_high: float,
    struct_low: float,
    params: CrtParams,
    ps: float,
) -> bool:
    if side == "UP":
        bearish = rng.close < rng.open - _EPS
        inside = rng.low > struct_low + _EPS and rng.high <= struct_high + _EPS
    else:
        bearish = rng.close > rng.open + _EPS
        inside = rng.high < struct_high - _EPS and rng.low >= struct_low - _EPS
    if not bearish or not inside:
        return False
    leg = (struct_high - struct_low) / ps
    span = (rng.high - rng.low) / ps
    if params.min_leg_pts > 0 and leg + 1e-6 < params.min_leg_pts:
        return False
    if params.min_range_pts > 0 and span + 1e-6 < params.min_range_pts:
        return False
    if not params.pd_filter:
        return True
    eq = struct_low + params.equilibrium * (struct_high - struct_low)
    if side == "UP":
        return rng.close <= eq + _EPS
    return rng.close >= eq - _EPS


def _sweep_state(rng: Candle, nxt: Candle, side: str) -> Optional[str]:
    """'ok', 'close_through', 'no_reclaim', or None when price never left the range."""
    if side == "UP":
        if nxt.low >= rng.low - _EPS:
            return None
        if nxt.close <= rng.low + _EPS:
            return "close_through"
        if nxt.close <= rng.high + _EPS:
            return "ok"
        return "no_reclaim"
    if nxt.high <= rng.high + _EPS:
        return None
    if nxt.close >= rng.high - _EPS:
        return "close_through"
    if nxt.close >= rng.low - _EPS:
        return "ok"
    return "no_reclaim"


def _orders_for_setup(
    *,
    side: str,
    rng: Candle,
    nxt: Candle,
    ltf: Sequence[Candle],
    ltf_idxs: Sequence[int],
    struct_high: float,
    struct_low: float,
    params: CrtParams,
    ps: float,
) -> List[Dict[str, Any]]:
    sweep_extreme = nxt.low if side == "UP" else nxt.high
    manage_i = _index_at_or_after(ltf, nxt.close_time)
    if params.entry_mode == "sweep_close":
        if manage_i is None:
            return []
        entry = float(nxt.close)
        sl = _stop_level(side, entry, None, None, sweep_extreme, params, ps)
        return [
            _order(
                side=side,
                market=True,
                active_i=manage_i,
                expire_i=len(ltf),
                entry=entry,
                sl=sl,
                partial=_partial_px(side, entry, sl, params),
                runner=_runner_px(side, entry, sl, struct_high, struct_low, params),
                bottom=None,
                top=None,
                sweep_extreme=sweep_extreme,
                wick_i=ltf_idxs[0] if ltf_idxs else manage_i,
            )
        ]
    if not ltf_idxs:
        return []
    wick_i = _wick_index(ltf, ltf_idxs, side, rng)
    if wick_i is None:
        return []
    expire_at = to_utc(nxt.close_time) + timedelta(minutes=params.fvg_wait_htf * params.htf_min)
    gaps = _gaps_after(ltf, wick_i, side, expire_at)
    chosen = _choose_gaps(gaps, side, params.fvg_select, params.max_fvgs)
    expire_i = _index_at_or_after(ltf, expire_at)
    if expire_i is None:
        expire_i = len(ltf)
    orders = []
    for gap in chosen:
        entry = _entry_level(side, gap["bottom"], gap["top"], params.fvg_entry)
        active_at = max(to_utc(gap["c3"].close_time), to_utc(nxt.close_time))
        active_i = _index_at_or_after(ltf, active_at)
        if active_i is None or active_i >= expire_i:
            continue
        sl = _stop_level(side, entry, gap["bottom"], gap["top"], sweep_extreme, params, ps)
        orders.append(
            _order(
                side=side,
                market=False,
                active_i=active_i,
                expire_i=expire_i,
                entry=entry,
                sl=sl,
                partial=_partial_px(side, entry, sl, params),
                runner=_runner_px(side, entry, sl, struct_high, struct_low, params),
                bottom=gap["bottom"],
                top=gap["top"],
                sweep_extreme=sweep_extreme,
                wick_i=wick_i,
            )
        )
    return orders


def _gaps_after(
    ltf: Sequence[Candle], wick_i: int, side: str, expire_at: datetime
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    expire_at = to_utc(expire_at)
    for c3_i in range(wick_i + 2, len(ltf)):
        c3 = ltf[c3_i]
        if to_utc(c3.close_time) > expire_at:
            break
        c1_i = c3_i - 2
        if c1_i < wick_i:
            continue
        gap = _gap(side, ltf[c1_i], c3)
        if gap is None:
            continue
        bottom, top = gap
        out.append({"i": c3_i, "bottom": bottom, "top": top, "c1": ltf[c1_i], "c3": c3})
    return out


def _gap(side: str, c1: Candle, c3: Candle) -> Optional[Tuple[float, float]]:
    if side == "UP":
        if c1.high + _EPS < c3.low:
            return float(c1.high), float(c3.low)
        return None
    if c1.low > c3.high + _EPS:
        return float(c3.high), float(c1.low)
    return None


def _choose_gaps(
    gaps: Sequence[Dict[str, Any]], side: str, mode: str, limit: int
) -> List[Dict[str, Any]]:
    if not gaps:
        return []
    if mode == "first":
        ordered = sorted(gaps, key=lambda g: (g["i"], g["bottom"]))
        return ordered[:1]
    if side == "UP":
        ordered = sorted(gaps, key=lambda g: (g["bottom"], g["top"], g["i"]))
    else:
        ordered = sorted(gaps, key=lambda g: (-g["top"], g["bottom"], g["i"]))
    if mode == "extreme":
        return ordered[:1]
    return list(ordered[: max(1, int(limit))])


def _entry_level(side: str, bottom: float, top: float, how: str) -> float:
    if how == "ce":
        return (bottom + top) / 2.0
    if how == "distal":
        return bottom if side == "UP" else top
    return top if side == "UP" else bottom


def _stop_level(
    side: str,
    entry: float,
    bottom: Optional[float],
    top: Optional[float],
    sweep_extreme: float,
    params: CrtParams,
    ps: float,
) -> float:
    buf = max(0.0, params.sl_buffer_pts) * ps
    if params.sl_mode == "fixed":
        dist = params.sl_fixed_pts * ps
        sl = entry - dist if side == "UP" else entry + dist
    elif params.sl_mode == "beyond_sweep" or bottom is None or top is None:
        sl = sweep_extreme - buf if side == "UP" else sweep_extreme + buf
    else:
        edge = bottom if side == "UP" else top
        sl = edge - buf if side == "UP" else edge + buf
    if side == "UP" and sl >= entry:
        sl = entry - max(ps, _EPS)
    if side == "DOWN" and sl <= entry:
        sl = entry + max(ps, _EPS)
    return sl


def _partial_px(side: str, entry: float, sl: float, params: CrtParams) -> float:
    risk = abs(entry - sl)
    if side == "UP":
        return entry + params.partial_rr * risk
    return entry - params.partial_rr * risk


def _runner_px(
    side: str,
    entry: float,
    sl: float,
    struct_high: float,
    struct_low: float,
    params: CrtParams,
) -> float:
    risk = abs(entry - sl)
    if side == "UP":
        rr_px = entry + params.runner_rr * risk
        partial = entry + params.partial_rr * risk
        if params.runner_mode == "swing" and struct_high > partial + _EPS:
            return struct_high
        return rr_px
    rr_px = entry - params.runner_rr * risk
    partial = entry - params.partial_rr * risk
    if params.runner_mode == "swing" and struct_low < partial - _EPS:
        return struct_low
    return rr_px


def _order(**kwargs: Any) -> Dict[str, Any]:
    return kwargs


def _wick_index(
    ltf: Sequence[Candle], idxs: Sequence[int], side: str, rng: Candle
) -> Optional[int]:
    for i in idxs:
        bar = ltf[i]
        if side == "UP" and bar.low < rng.low - _EPS:
            return i
        if side == "DOWN" and bar.high > rng.high + _EPS:
            return i
    return None


# --- fills ----------------------------------------------------------------


def _simulate(
    order: Dict[str, Any], bars: Sequence[Candle], params: CrtParams, ps: float
) -> Optional[Dict[str, Any]]:
    if order["active_i"] >= len(bars):
        return None
    if order["market"]:
        i = order["active_i"]
        bar = bars[i]
        imm = _adverse_on_bar(order["side"], bar, order["entry"], order["sl"])
        return _finish(order, bars, i, float(order["entry"]), imm, params, ps)
    last = min(int(order["expire_i"]), len(bars))
    for i in range(int(order["active_i"]), last):
        got = _limit_fill(order["side"], bars[i], float(order["entry"]), float(order["sl"]))
        if got is None:
            continue
        fill, imm = got
        return _finish(order, bars, i, fill, imm, params, ps)
    return None


def _adverse_on_bar(
    side: str, bar: Candle, entry: float, sl: float
) -> Optional[Tuple[float, str]]:
    """Stop on this bar, before any target. None when the stop is untouched."""
    if side == "UP":
        if bar.open <= sl + _EPS:
            return min(bar.open, sl), "sl"
        if bar.low <= sl + _EPS:
            return sl, "sl"
        return None
    if bar.open >= sl - _EPS:
        return max(bar.open, sl), "sl"
    if bar.high >= sl - _EPS:
        return sl, "sl"
    return None


def _limit_fill(
    side: str, bar: Candle, entry: float, sl: float
) -> Optional[Tuple[float, Optional[Tuple[float, str]]]]:
    if side == "UP":
        if bar.low > entry + _EPS:
            return None
        if bar.open <= sl + _EPS:
            return bar.open, (bar.open, "sl")
        fill = entry if bar.open >= entry - _EPS else bar.open
        if bar.low <= sl + _EPS:
            return fill, (sl, "sl")
        return fill, None
    if bar.high < entry - _EPS:
        return None
    if bar.open >= sl - _EPS:
        return bar.open, (bar.open, "sl")
    fill = entry if bar.open <= entry + _EPS else bar.open
    if bar.high >= sl - _EPS:
        return fill, (sl, "sl")
    return fill, None


def _finish(
    order: Dict[str, Any],
    bars: Sequence[Candle],
    i: int,
    fill: float,
    imm: Optional[Tuple[float, str]],
    params: CrtParams,
    ps: float,
) -> Dict[str, Any]:
    side = order["side"]
    partial = float(order["partial"])
    runner = float(order["runner"])
    partial_on = params.partial_frac > 1e-12
    bar = bars[i]
    partial_hit = False
    partial_bar: Optional[Candle] = None
    if imm is not None:
        exit_px, reason = imm
        exit_bar = bar
    else:
        stepped = _targets(side, bar, partial, runner, partial_on, False)
        reason = stepped[0]
        exit_px = stepped[1]
        partial_hit = stepped[2]
        if partial_hit:
            partial_bar = bar
        exit_bar = bar
        if reason is None:
            deadline = to_utc(bar.open_time) + timedelta(minutes=params.max_hold_htf * params.htf_min)
            last_bar = bar
            j = i + 1
            while j < len(bars):
                nxt = bars[j]
                if to_utc(nxt.open_time) >= deadline:
                    break
                last_bar = nxt
                hit = _adverse_on_bar(side, nxt, fill, float(order["sl"]))
                if hit is not None:
                    reason = "partial_sl" if partial_hit else "sl"
                    exit_px = hit[0]
                    exit_bar = nxt
                    break
                stepped = _targets(side, nxt, partial, runner, partial_on, partial_hit)
                if stepped[2] and not partial_hit:
                    partial_hit = True
                    partial_bar = nxt
                if stepped[0] is not None:
                    reason = stepped[0]
                    exit_px = stepped[1]
                    exit_bar = nxt
                    partial_hit = True if partial_on else partial_hit
                    break
                j += 1
            if reason is None:
                reason = "time"
                exit_px = float(last_bar.close)
                exit_bar = last_bar
    if reason == "tp" and partial_on:
        partial_hit = True
        if partial_bar is None:
            partial_bar = exit_bar
    if reason == "sl" and partial_hit:
        reason = "partial_sl"
    pts = _pnl(side, fill, float(exit_px), partial, partial_hit, params.partial_frac, ps, params.cost_pts)
    wick_i = order.get("wick_i")
    sweep_bar = bars[wick_i] if isinstance(wick_i, int) and 0 <= wick_i < len(bars) else bar
    return {
        "entry_bar": bar,
        "exit_bar": exit_bar,
        "partial_bar": partial_bar,
        "sweep_bar": sweep_bar,
        "fill": float(fill),
        "exit": float(exit_px),
        "sl": float(order["sl"]),
        "partial": partial,
        "runner": runner,
        "partial_hit": partial_hit,
        "reason": reason,
        "pts": pts,
        "bottom": order.get("bottom"),
        "top": order.get("top"),
        "sweep_extreme": order.get("sweep_extreme"),
        "wick_i": order.get("wick_i"),
        "entry_reason": "sweep_close" if order["market"] else "fvg",
    }


def _targets(
    side: str,
    bar: Candle,
    partial: float,
    runner: float,
    partial_on: bool,
    partial_hit: bool,
) -> Tuple[Optional[str], Optional[float], bool]:
    """Target progress after the stop has already been ruled out on this bar."""
    if side == "UP":
        if partial_on and not partial_hit and (bar.open >= partial - _EPS or bar.high >= partial - _EPS):
            partial_hit = True
        if bar.open >= runner - _EPS:
            return "tp", max(bar.open, runner), True if partial_on else partial_hit
        if (not partial_on or partial_hit) and bar.high >= runner - _EPS:
            return "tp", runner, True if partial_on else partial_hit
        return None, None, partial_hit
    if partial_on and not partial_hit and (bar.open <= partial + _EPS or bar.low <= partial + _EPS):
        partial_hit = True
    if bar.open <= runner + _EPS:
        return "tp", min(bar.open, runner), True if partial_on else partial_hit
    if (not partial_on or partial_hit) and bar.low <= runner + _EPS:
        return "tp", runner, True if partial_on else partial_hit
    return None, None, partial_hit


def _pnl(
    side: str,
    entry: float,
    exit_px: float,
    partial: float,
    partial_hit: bool,
    frac: float,
    ps: float,
    cost: float,
) -> float:
    sign = 1.0 if side == "UP" else -1.0
    full = sign * (exit_px - entry) / ps
    if frac <= 1e-12 or not partial_hit:
        return round(full - cost, 2)
    part = sign * (partial - entry) / ps
    return round(frac * part + (1.0 - frac) * full - cost, 2)


def _trade_row(
    trade: Dict[str, Any],
    *,
    seq: int,
    day: date,
    weekday: str,
    side: str,
    rng: Candle,
    nxt: Candle,
    struct_high: float,
    struct_low: float,
    params: CrtParams,
    ps: float,
    symbol: str,
) -> Dict[str, Any]:
    entry_bar: Candle = trade["entry_bar"]
    exit_bar: Candle = trade["exit_bar"]
    partial_bar: Optional[Candle] = trade.get("partial_bar")
    sweep_bar: Candle = trade.get("sweep_bar") or nxt
    row = {
        "_seq": seq,
        "local_date": day.isoformat(),
        "weekday": weekday,
        "side": side,
        "entry_reason": trade["entry_reason"],
        "entry_ts": _iso(entry_bar.open_time),
        "exit_ts": _iso(exit_bar.open_time if trade["reason"] != "time" else exit_bar.close_time),
        "entry": trade["fill"],
        "exit": trade["exit"],
        "sl": trade["sl"],
        "tp": trade["runner"],
        "partial_px": trade["partial"],
        "pts": trade["pts"],
        "exit_reason": trade["reason"],
        "crh": float(rng.high),
        "crl": float(rng.low),
        "sweep_ts": _iso(sweep_bar.open_time),
        "sweep_extreme": trade.get("sweep_extreme"),
        "fvg_bottom": trade.get("bottom"),
        "fvg_top": trade.get("top"),
        "structure_high": struct_high,
        "structure_low": struct_low,
        "range_open_ts": _iso(rng.open_time),
        "range_close_ts": _iso(rng.close_time),
        "partial_ts": _iso(partial_bar.open_time) if partial_bar is not None else None,
        "partial_hit": bool(trade["partial_hit"]),
        "htf_min": params.htf_min,
        "ltf_min": params.ltf_min,
    }
    row["story"] = _story(row, params, symbol, ps)
    return row


def _story(row: Dict[str, Any], params: CrtParams, symbol: str, ps: float) -> str:
    def px(value: Any) -> str:
        if value is None:
            return "—"
        digits = 2 if ps >= 0.01 - 1e-12 else (3 if ps >= 0.001 - 1e-12 else 5)
        return f"{float(value):.{digits}f}"

    trend = "Uptrend" if row["side"] == "UP" else "Downtrend"
    color = "bearish" if row["side"] == "UP" else "bullish"
    where = ""
    if params.pd_filter:
        where = " It closed in " + ("discount" if row["side"] == "UP" else "premium") + "."
    if row["entry_reason"] == "sweep_close":
        how = "Entry is the sweep close at " + px(row["entry"]) + "."
    else:
        how = (
            "Buy limit"
            if row["side"] == "UP"
            else "Sell limit"
        )
        how += (
            " at the "
            + params.fvg_entry
            + " edge of the "
            + str(params.ltf_min)
            + "m fair value gap "
            + px(row["fvg_bottom"])
            + "–"
            + px(row["fvg_top"])
            + ", filled at "
            + px(row["entry"])
            + "."
        )
    half = ""
    if params.partial_frac > 0 and row.get("partial_hit"):
        half = (
            " "
            + _num(params.partial_frac)
            + " closed at "
            + px(row["partial_px"])
            + " ("
            + _num(params.partial_rr)
            + " R)."
        )
    return (
        trend
        + " dealing range "
        + px(row["structure_low"])
        + "–"
        + px(row["structure_high"])
        + ". The "
        + color
        + " "
        + str(params.htf_min)
        + "m candle is the range, CRH "
        + px(row["crh"])
        + " CRL "
        + px(row["crl"])
        + "."
        + where
        + " The next candle swept "
        + ("CRL" if row["side"] == "UP" else "CRH")
        + " and closed back inside. "
        + how
        + " Stop "
        + px(row["sl"])
        + "."
        + half
        + " Runner "
        + px(row["tp"])
        + ". Exit "
        + str(row["exit_reason"])
        + " at "
        + px(row["exit"])
        + "."
    )


# --- stats ----------------------------------------------------------------


def _stats(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    wins = sum(1 for r in rows if float(r.get("pts") or 0) > 1e-9)
    losses = sum(1 for r in rows if float(r.get("pts") or 0) < -1e-9)
    gp = sum(float(r["pts"]) for r in rows if float(r["pts"]) > 0)
    gl = -sum(float(r["pts"]) for r in rows if float(r["pts"]) < 0)
    exits: Dict[str, int] = {}
    entries: Dict[str, int] = {}
    for r in rows:
        er = str(r.get("exit_reason") or "?")
        exits[er] = exits.get(er, 0) + 1
        en = str(r.get("entry_reason") or "?")
        entries[en] = entries.get(en, 0) + 1
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "scratches": n - wins - losses,
        "win_pct": round(100.0 * wins / n, 1) if n else 0.0,
        "exits": exits,
        "entries": entries,
        "avg_pts": round(sum(float(r["pts"]) for r in rows) / n, 1) if n else 0.0,
        "avg_win_pts": round(gp / wins, 1) if wins else None,
        "avg_loss_pts": round(gl / losses, 1) if losses else None,
        "profit_factor": round(gp / gl, 2) if gl > 1e-9 else None,
        "sum_pts": round(sum(float(r["pts"]) for r in rows), 1),
    }


def _by_month(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        key = str(r.get("local_date") or "")[:7]
        buckets.setdefault(key, []).append(r)
    out = []
    for key in sorted(buckets):
        row = _stats(buckets[key])
        row["month"] = key
        out.append(row)
    return out


def _skip_counts(skips: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for s in skips:
        key = str(s.get("reason") or "?")
        out[key] = out.get(key, 0) + 1
    return out


def _skip(day: date, weekday: str, reason: str, side: str, detail: str) -> Dict[str, Any]:
    return {
        "local_date": day.isoformat() if isinstance(day, date) else str(day),
        "weekday": weekday,
        "reason": reason,
        "side": side,
        "detail": detail,
    }


# --- time -----------------------------------------------------------------


def _groups(ltf: Sequence[Candle], htf_min: int) -> Dict[int, List[int]]:
    out: Dict[int, List[int]] = {}
    for i, bar in enumerate(ltf):
        out.setdefault(_bucket(bar.open_time, htf_min), []).append(i)
    return out


def _bucket(ts: datetime, tf_min: int) -> int:
    step = int(tf_min) * 60
    unix = int(to_utc(ts).timestamp())
    return unix - (unix % step)


def _index_at_or_after(bars: Sequence[Candle], ts: datetime) -> Optional[int]:
    want = to_utc(ts)
    for i, bar in enumerate(bars):
        if to_utc(bar.open_time) >= want:
            return i
    return None


def _in_session(params: CrtParams, open_time: datetime, tz: ZoneInfo) -> bool:
    if not params.session_enabled:
        return True
    loc = to_utc(open_time).astimezone(tz)
    minutes = loc.hour * 60 + loc.minute
    start = params.session_start_hour * 60 + params.session_start_minute
    end = params.session_end_hour * 60 + params.session_end_minute
    if start == end:
        return True
    if start < end:
        return start <= minutes < end
    return minutes >= start or minutes < end


def _local_day(ts: datetime, tz: ZoneInfo) -> Tuple[date, str]:
    loc = to_utc(ts).astimezone(tz)
    return loc.date(), loc.strftime("%A")


def _in_window(day: date, d0: Optional[date], d1: Optional[date]) -> bool:
    if d0 is not None and day < d0:
        return False
    if d1 is not None and day >= d1:
        return False
    return True


def _as_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _iso(ts: datetime) -> str:
    return to_utc(ts).isoformat()


def _num(value: float) -> str:
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _clock(hour: int, minute: int) -> str:
    return f"{int(hour):02d}:{int(minute):02d}"
