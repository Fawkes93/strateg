"""Candle Range Theory.

Hunt mode checks every higher-timeframe candle that fits the trend. There is
no daily limit. max_concurrent 0 leaves every fill open; a positive number
caps how many trades are active. ny_open mode uses only the candle that
closes at New York open, one attempt that day.

An agent can run it from the README section "CRT tab" or from GET /api/crt/rules
without reading this file. This module is the rules.

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
from datetime import date, datetime, time as dt_time, timedelta, timezone
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
MODES = ("hunt", "ny_open")

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
    min_sl_pts: float = 0.0
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
    max_concurrent: int = 0
    mode: str = "hunt"
    ny_timezone: str = "America/New_York"
    ny_open_hour: int = 8
    ny_open_minute: int = 0
    session_enabled: bool = False
    session_start_hour: int = 8
    session_start_minute: int = 0
    session_end_hour: int = 17
    session_end_minute: int = 0
    skip_news: bool = False
    direction: str = "both"
    cost_pts: float = 0.0
    commission_pts: float = 0.0
    # Two ranges can claim the same lower-timeframe gap. On: only the earliest range books it.
    dedupe_fvg_across_ranges: bool = True


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
    params.min_sl_pts = max(0.0, float(params.min_sl_pts or 0))
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
    params.max_concurrent = int(params.max_concurrent or 0)
    if params.max_concurrent < 0:
        params.max_concurrent = 0
    if params.max_concurrent > 500:
        raise ValueError("max_concurrent must be 0 (no cap) or at most 500")
    params.mode = str(params.mode or "hunt").strip().lower()
    if params.mode not in MODES:
        raise ValueError("mode must be hunt or ny_open")
    params.ny_timezone = str(params.ny_timezone or "America/New_York").strip() or "America/New_York"
    require_zone(params.ny_timezone)
    params.ny_open_hour = int(params.ny_open_hour)
    params.ny_open_minute = int(params.ny_open_minute)
    if not 0 <= params.ny_open_hour <= 23:
        raise ValueError("ny_open_hour must be from 0 to 23")
    if not 0 <= params.ny_open_minute <= 59:
        raise ValueError("ny_open_minute must be from 0 to 59")
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
    legacy = getattr(params, "side_filter", None)
    chosen = params.direction if params.direction else legacy
    params.direction = str(chosen or "both").strip().lower()
    if params.direction not in SIDES:
        raise ValueError("direction must be both, long, or short")
    params.cost_pts = max(0.0, float(params.cost_pts or 0))
    params.commission_pts = max(0.0, float(params.commission_pts or 0))
    params.dedupe_fvg_across_ranges = bool(params.dedupe_fvg_across_ranges)
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
    stop += (
        " If price trades through that stop before the limit fills, the order is cancelled "
        "(invalidated_before_fill). A stop on the wrong side of the fill is cancelled too."
    )
    if p.min_sl_pts > 0:
        stop += (
            " A fill whose stop is tighter than "
            + _num(p.min_sl_pts)
            + " points, measured after the buffer, is skipped (min_sl)."
        )
    if p.mode == "ny_open" and p.runner_mode == "swing":
        runner = (
            "The rest targets the other side of the New York candle when that price is beyond the partial. "
            "Otherwise it targets "
            + _num(p.runner_rr)
            + " R."
        )
    elif p.runner_mode == "swing":
        runner = (
            "The rest targets the far side of the dealing range when that price is beyond the partial. "
            "Otherwise it targets "
            + _num(p.runner_rr)
            + " R."
        )
    else:
        runner = "The rest targets " + _num(p.runner_rr) + " R."
    if p.max_concurrent <= 0:
        concurrent = "max_concurrent is 0, so there is no cap. Every setup that fills can be open together."
    else:
        concurrent = (
            "At most "
            + str(p.max_concurrent)
            + " trades are open at once. A new signal is skipped until one of them exits."
        )
    if p.mode == "ny_open":
        mode_body = (
            "New York open. One attempt per day: the "
            + str(p.htf_min)
            + "m candle that closes at "
            + _clock(p.ny_open_hour, p.ny_open_minute)
            + " "
            + p.ny_timezone
            + ". The next candle is the only sweep. A sweep of the low is a long. A sweep of the high is a short. "
            + "Trend and discount are not used. min_leg_pts still applies to the dealing range in front of that candle."
        )
        range_body = "The range is that one candle, whatever its color. No other candle that day is a candidate."
        premium_body = "Ignored in New York open mode."
    else:
        mode_body = (
            "Hunt. Every higher-timeframe candle that passes the trend rules is a candidate. "
            + "There is no daily limit. Set mode to ny_open for the single candle that closes at New York open."
        )
        range_body = (
            "Uptrend range candles are bearish and stay inside the dealing range. "
            "Downtrend range candles are bullish and stay inside it. "
            "Only the next candle may sweep."
        )
        premium_body = pd
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
    trend_body = (
        "Dealing range is the highest high and lowest low of the last "
        + str(p.structure_bars)
        + " closed "
        + str(p.htf_min)
        + "m bars before the range candle. Up when the low prints before the high. "
        + "Down when the high prints first. The same bar is chop and is skipped."
    )
    if p.mode == "ny_open":
        trend_body = "Not used. New York open does not require a dealing-range trend."
    return [
        {
            "id": "mode",
            "body": mode_body,
        },
        {
            "id": "trend",
            "body": trend_body,
        },
        {
            "id": "range",
            "body": range_body,
        },
        {
            "id": "premium",
            "body": premium_body,
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
                + concurrent
                + " direction is "
                + p.direction
                + ". cost_pts is the spread, charged once on the entry. commission_pts is charged on the entry and on each exit fill. A partial and a runner are two exits."
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
                + "Hunt checks every candle. New York open checks one candle a day."
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
    rows: Sequence[Dict[str, Any]], max_concurrent: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Keep trades in entry order. 0 leaves every fill. A positive cap skips the extras."""
    limit = int(max_concurrent or 0)
    ordered = sorted(rows, key=lambda r: (str(r.get("entry_ts") or ""), int(r.get("_seq") or 0)))
    if limit <= 0:
        return list(ordered), []
    kept: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for row in ordered:
        entry = str(row.get("entry_ts") or "")
        live = sum(1 for prev in kept if str(prev.get("exit_ts") or "") > entry)
        if live >= limit:
            skipped.append(row)
            continue
        kept.append(row)
    return kept, skipped


def ny_side(rng: Candle, nxt: Candle) -> Tuple[Optional[str], Optional[str]]:
    """Side and sweep state for the New York candle. Direction comes from the sweep."""
    up = _sweep_state(rng, nxt, "UP")
    down = _sweep_state(rng, nxt, "DOWN")
    if up == "ok" and down == "ok":
        up_depth = float(rng.low) - float(nxt.low)
        down_depth = float(nxt.high) - float(rng.high)
        return ("UP" if up_depth >= down_depth else "DOWN"), "ok"
    if up == "ok":
        return "UP", "ok"
    if down == "ok":
        return "DOWN", "ok"
    if up == "close_through" or down == "close_through":
        return ("UP" if up == "close_through" else "DOWN"), "close_through"
    if up == "no_reclaim" or down == "no_reclaim":
        return ("UP" if up == "no_reclaim" else "DOWN"), "no_reclaim"
    return None, None


def ny_range_index(
    htf: Sequence[Candle], day: date, params: CrtParams, ny_tz: ZoneInfo
) -> Optional[int]:
    """Index of the higher-timeframe bar that closes at New York open on this date."""
    local = datetime.combine(
        day, dt_time(params.ny_open_hour, params.ny_open_minute), tzinfo=ny_tz
    )
    want = int(to_utc(local).timestamp())
    step = int(params.htf_min) * 60
    nearest: Optional[int] = None
    nearest_gap: Optional[int] = None
    for i in range(len(htf) - 1):
        close_ts = int(to_utc(htf[i].close_time).timestamp())
        if close_ts == want:
            return i
        gap = want - close_ts
        if 0 < gap < step and (nearest_gap is None or gap < nearest_gap):
            nearest = i
            nearest_gap = gap
    return nearest


def _ny_dates(htf: Sequence[Candle], ny_tz: ZoneInfo) -> List[date]:
    if not htf:
        return []
    first = to_utc(htf[0].open_time).astimezone(ny_tz).date()
    last = to_utc(htf[-1].close_time).astimezone(ny_tz).date()
    days: List[date] = []
    day = first
    while day <= last:
        days.append(day)
        day += timedelta(days=1)
    return days


def _record_attempt(
    *,
    rows: List[Dict[str, Any]],
    skips: List[Dict[str, Any]],
    seq: int,
    side: str,
    rng: Candle,
    nxt: Candle,
    struct_high: float,
    struct_low: float,
    ltf: Sequence[Candle],
    groups: Dict[int, List[int]],
    params: CrtParams,
    ps: float,
    tz: ZoneInfo,
    d0: Optional[date],
    d1: Optional[date],
    symbol: str,
    sweep_state: str,
) -> int:
    day, weekday = _local_day(nxt.open_time, tz)
    if not _in_window(day, d0, d1):
        return seq
    if sweep_state == "close_through":
        skips.append(_skip(day, weekday, "close_through", side, "The next candle closed through the range."))
        return seq
    if sweep_state == "no_reclaim":
        skips.append(_skip(day, weekday, "no_reclaim", side, "The sweep did not close back inside the range."))
        return seq
    if not _in_session(params, nxt.open_time, tz):
        skips.append(_skip(day, weekday, "session", side, "The sweep candle opened outside the session."))
        return seq
    if params.skip_news and is_news_day(day):
        skips.append(_skip(day, weekday, "news", side, "Gold news calendar."))
        return seq
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
        return seq
    filled_any = False
    skip_reason = None
    for order in made:
        trade = _simulate(order, ltf, params, ps)
        if trade is None:
            continue
        reason = trade.get("_skip")
        if reason:
            if skip_reason != "invalidated_before_fill":
                skip_reason = reason
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
        if skip_reason == "min_sl":
            detail = "Stop distance was below min_sl_pts."
        elif skip_reason == "invalidated_before_fill":
            detail = "Price traded through the stop before the limit filled."
        else:
            skip_reason = "no_fill"
            detail = "The level was not traded before it expired."
        skips.append(_skip(day, weekday, skip_reason, side, detail))
    return seq


def dedupe_fvg_rows(
    rows: Sequence[Dict[str, Any]], symbol: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Keep one trade per (symbol, side, FVG open time, entry). The earliest range wins.

    Rows without an FVG open time (sweep_close entries) are never merged.
    Returns (kept, dropped)."""
    ordered = sorted(rows, key=lambda r: (str(r.get("range_open_ts") or ""), int(r.get("_seq") or 0)))
    seen = set()
    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for row in ordered:
        fvg_ts = row.get("fvg_open_ts")
        if not fvg_ts:
            kept.append(row)
            continue
        key = (str(symbol), str(row.get("side")), str(fvg_ts), round(float(row.get("entry") or 0.0), 8))
        if key in seen:
            dropped.append(row)
            continue
        seen.add(key)
        kept.append(row)
    kept.sort(key=lambda r: int(r.get("_seq") or 0))
    return kept, dropped


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
    total = max(0, len(htf) - 1)
    seq = 0
    cancelled = False
    if params.mode == "ny_open":
        ny_tz = require_zone(params.ny_timezone)
        days = _ny_dates(htf, ny_tz)
        for n, day in enumerate(days):
            if stop and stop():
                cancelled = True
                break
            if progress and (n % 5) == 0:
                progress(n, max(len(days), 1))
            index = ny_range_index(htf, day, params, ny_tz)
            if index is None:
                continue
            rng = htf[index]
            nxt = htf[index + 1]
            span = (rng.high - rng.low) / ps
            if params.min_range_pts > 0 and span + 1e-6 < params.min_range_pts:
                continue
            side, sweep_state = ny_side(rng, nxt)
            if side is None or sweep_state is None:
                continue
            if not _direction_ok(params, side):
                continue
            if not _leg_ok(htf, index, params, ps):
                continue
            seq = _record_attempt(
                rows=rows,
                skips=skips,
                seq=seq,
                side=side,
                rng=rng,
                nxt=nxt,
                struct_high=float(rng.high),
                struct_low=float(rng.low),
                ltf=ltf,
                groups=groups,
                params=params,
                ps=ps,
                tz=tz,
                d0=d0,
                d1=d1,
                symbol=symbol,
                sweep_state=sweep_state,
            )
    else:
        total = max(0, len(htf) - params.structure_bars - 1)
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
            if not _direction_ok(params, side):
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
            seq = _record_attempt(
                rows=rows,
                skips=skips,
                seq=seq,
                side=side,
                rng=rng,
                nxt=nxt,
                struct_high=struct_high,
                struct_low=struct_low,
                ltf=ltf,
                groups=groups,
                params=params,
                ps=ps,
                tz=tz,
                d0=d0,
                d1=d1,
                symbol=symbol,
                sweep_state=sweep_state,
            )
    if progress:
        progress(total, total)
    if params.dedupe_fvg_across_ranges:
        rows, dupes = dedupe_fvg_rows(rows, symbol)
        for row in dupes:
            skips.append(
                _skip(
                    _as_date(row.get("local_date")) or date.min,
                    str(row.get("weekday") or ""),
                    "duplicate_fvg",
                    str(row.get("side") or ""),
                    "An earlier range already booked this fair value gap.",
                )
            )
    kept, crowded = cap_open(rows, params.max_concurrent)
    for row in crowded:
        skips.append(
            _skip(
                _as_date(row.get("local_date")) or date.min,
                str(row.get("weekday") or ""),
                "max_concurrent",
                str(row.get("side") or ""),
                "max_concurrent trades were already open.",
            )
        )
    for row in kept:
        row.pop("_seq", None)
    return {
        "rows": kept,
        "skips": skips,
        "skipped": len(skips),
        "skip_reasons": _skip_counts(skips),
        **_mark_drawdown(kept, ltf, params, ps),
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
        "by_year": _by_year(rows),
        "by_direction": _by_direction(rows),
        "max_dd_pts": raw.get("max_dd_pts", 0.0),
        "max_dd_closed_pts": raw.get("max_dd_closed_pts", 0.0),
        "ticks": int(raw.get("ticks") or 0),
    }
    out.update(stats)
    return out


# --- setup geometry -------------------------------------------------------


def _direction_ok(params: CrtParams, side: str) -> bool:
    want = str(params.direction or "both")
    if want == "long":
        return side == "UP"
    if want == "short":
        return side == "DOWN"
    return True


def _dealing_leg_pts(htf: Sequence[Candle], index: int, params: CrtParams, ps: float) -> Optional[float]:
    """Points from the lowest low to the highest high of the structure window before index."""
    if ps <= 0 or index < int(params.structure_bars):
        return None
    window = htf[index - int(params.structure_bars) : index]
    if len(window) < int(params.structure_bars):
        return None
    hi = max(c.high for c in window)
    lo = min(c.low for c in window)
    return (hi - lo) / ps


def _leg_ok(htf: Sequence[Candle], index: int, params: CrtParams, ps: float) -> bool:
    """min_leg_pts applies in Hunt and in New York open. 0 disables it."""
    if params.min_leg_pts <= 0:
        return True
    leg = _dealing_leg_pts(htf, index, params, ps)
    if leg is None:
        return False
    return leg + 1e-6 >= float(params.min_leg_pts)


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
                watch_i=manage_i,
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
        watch_i = manage_i if params.sl_mode == "beyond_sweep" and manage_i is not None else active_i
        orders.append(
            _order(
                side=side,
                market=False,
                active_i=active_i,
                watch_i=watch_i,
                expire_i=expire_i,
                entry=entry,
                sl=sl,
                partial=_partial_px(side, entry, sl, params),
                runner=_runner_px(side, entry, sl, struct_high, struct_low, params),
                bottom=gap["bottom"],
                top=gap["top"],
                fvg_ts=_iso(gap["c1"].open_time),
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
    return sl


def _stop_protects(side: str, entry: float, sl: float) -> bool:
    """True when the stop is strictly beyond the fill. A stop on the entry or past it is not a trade."""
    if side == "UP":
        return sl < entry - _EPS
    return sl > entry + _EPS


def _touched_stop(side: str, bar: Candle, sl: float) -> bool:
    if side == "UP":
        return bar.low <= sl + _EPS
    return bar.high >= sl - _EPS


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


def _skipped(reason: str) -> Dict[str, Any]:
    return {"_skip": reason}


def _stop_distance_pts(entry: float, sl: float, ps: float) -> float:
    if ps <= 0:
        return 0.0
    return abs(float(entry) - float(sl)) / ps


def _stop_too_tight(entry: float, sl: float, params: CrtParams, ps: float) -> bool:
    if params.min_sl_pts <= 0:
        return False
    return _stop_distance_pts(entry, sl, ps) + 1e-9 < float(params.min_sl_pts)


def _simulate(
    order: Dict[str, Any], bars: Sequence[Candle], params: CrtParams, ps: float
) -> Optional[Dict[str, Any]]:
    if order["active_i"] >= len(bars):
        return None
    side = order["side"]
    entry = float(order["entry"])
    sl = float(order["sl"])
    if not _stop_protects(side, entry, sl):
        return _skipped("invalidated_before_fill")
    if order["market"]:
        i = order["active_i"]
        bar = bars[i]
        imm = _adverse_on_bar(side, bar, entry, sl)
        fill = entry
        if not _stop_protects(side, fill, sl):
            return _skipped("invalidated_before_fill")
        if _stop_too_tight(fill, sl, params, ps):
            return _skipped("min_sl")
        return _finish(order, bars, i, fill, imm, params, ps)
    last = min(int(order["expire_i"]), len(bars))
    watch_i = int(order.get("watch_i") if order.get("watch_i") is not None else order["active_i"])
    watch_i = max(0, min(watch_i, int(order["active_i"])))
    for i in range(watch_i, int(order["active_i"])):
        if _touched_stop(side, bars[i], sl):
            return _skipped("invalidated_before_fill")
    for i in range(int(order["active_i"]), last):
        got = _limit_fill(side, bars[i], entry, sl)
        if got is None:
            if _touched_stop(side, bars[i], sl):
                return _skipped("invalidated_before_fill")
            continue
        fill, imm = got
        if not _stop_protects(side, fill, sl):
            return _skipped("invalidated_before_fill")
        if _stop_too_tight(fill, sl, params, ps):
            return _skipped("min_sl")
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
    pts = _pnl(
        side,
        fill,
        float(exit_px),
        partial,
        partial_hit,
        params.partial_frac,
        ps,
        params.cost_pts,
        params.commission_pts,
    )
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
        "fvg_ts": order.get("fvg_ts"),
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


def trade_charges(partial_hit: bool, frac: float, cost_pts: float, commission_pts: float) -> float:
    """Spread once on the entry, plus commission on every fill.

    The entry is one fill. A single exit is the second. When part of the
    position is closed at the partial and the rest runs, those are two exits,
    so the commission is paid three times.
    """
    fills = 1.0
    if partial_hit and 1e-12 < float(frac) < 1.0 - 1e-12:
        fills += 2.0
    else:
        fills += 1.0
    return float(cost_pts) + float(commission_pts) * fills


def _charges_while_open(partial_locked: bool, frac: float, cost_pts: float, commission_pts: float) -> float:
    """Entry spread and entry commission, plus the partial exit once it has filled."""
    paid = float(cost_pts) + float(commission_pts)
    if partial_locked and 1e-12 < float(frac) < 1.0 - 1e-12:
        paid += float(commission_pts)
    return paid


def _gross_pts(
    side: str,
    entry: float,
    price: float,
    partial: float,
    partial_hit: bool,
    frac: float,
    ps: float,
) -> float:
    sign = 1.0 if side == "UP" else -1.0
    full = sign * (float(price) - float(entry)) / ps
    if frac <= 1e-12 or not partial_hit:
        return full
    part = sign * (float(partial) - float(entry)) / ps
    return float(frac) * part + (1.0 - float(frac)) * full


def _pnl(
    side: str,
    entry: float,
    exit_px: float,
    partial: float,
    partial_hit: bool,
    frac: float,
    ps: float,
    cost_pts: float,
    commission_pts: float,
) -> float:
    gross = _gross_pts(side, entry, exit_px, partial, partial_hit, frac, ps)
    return round(gross - trade_charges(partial_hit, frac, cost_pts, commission_pts), 2)


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
        "fvg_open_ts": trade.get("fvg_ts"),
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
    swept = "CRL" if row["side"] == "UP" else "CRH"
    if params.mode == "ny_open":
        lead = (
            "New York open. The "
            + str(params.htf_min)
            + "m candle that closed at "
            + _clock(params.ny_open_hour, params.ny_open_minute)
            + " "
            + params.ny_timezone
            + " is the day's only range, CRH "
            + px(row["crh"])
            + " CRL "
            + px(row["crl"])
            + ". "
        )
    else:
        lead = (
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
            + " "
        )
    return (
        lead
        + "The next candle swept "
        + swept
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


def _by_year(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        key = str(row.get("local_date") or "")[:4]
        if len(key) < 4:
            continue
        buckets.setdefault(key, []).append(row)
    out = []
    for key in sorted(buckets):
        stats = _stats(buckets[key])
        stats["year"] = key
        out.append(stats)
    return out


def _by_direction(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    longs = [row for row in rows if row.get("side") == "UP"]
    shorts = [row for row in rows if row.get("side") == "DOWN"]
    return {"long": _stats(longs), "short": _stats(shorts)}


def _stamp(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(str(iso)).timestamp())
    except ValueError:
        return None


def _open_mark_pts(trade: Dict[str, Any], mark: float, params: CrtParams, ps: float, partial_locked: bool) -> float:
    gross = _gross_pts(
        str(trade.get("side") or "UP"),
        float(trade.get("entry") or 0),
        mark,
        float(trade.get("partial_px") or trade.get("entry") or 0),
        partial_locked,
        float(params.partial_frac),
        ps,
    )
    paid = _charges_while_open(partial_locked, float(params.partial_frac), params.cost_pts, params.commission_pts)
    return gross - paid


def mark_drawdown(
    rows: Sequence[Dict[str, Any]],
    bars: Sequence[Candle],
    params: CrtParams,
    ps: float,
) -> Dict[str, float]:
    """Closed-trade drawdown, and mark-to-market drawdown that includes open P&L.

    Both are peak-to-trough in points, starting from zero. The mark uses each
    lower-timeframe close. A partial that has already filled stays locked, and
    the runner is marked. Costs already paid are included. At the exit bar the
    trade contributes its final pts.
    """
    closed = 0.0
    closed_peak = 0.0
    closed_dd = 0.0
    for row in sorted(rows, key=lambda r: (str(r.get("exit_ts") or ""), int(r.get("_seq") or 0))):
        closed += float(row.get("pts") or 0)
        if closed > closed_peak:
            closed_peak = closed
        closed_dd = max(closed_dd, closed_peak - closed)

    if not rows or not bars:
        return {"max_dd_pts": round(closed_dd, 2), "max_dd_closed_pts": round(closed_dd, 2)}

    opens = [int(to_utc(bar.open_time).timestamp()) for bar in bars]
    indexed: List[Tuple[int, int, Dict[str, Any]]] = []
    first = len(bars)
    last = 0
    for trade in rows:
        entry_at = _stamp(trade.get("entry_ts"))
        exit_at = _stamp(trade.get("exit_ts"))
        if entry_at is None or exit_at is None:
            continue
        entry_i = None
        exit_i = None
        for i, opened in enumerate(opens):
            if entry_i is None and opened >= entry_at:
                entry_i = i
            if opened <= exit_at:
                exit_i = i
        if entry_i is None or exit_i is None:
            continue
        indexed.append((entry_i, exit_i, trade))
        first = min(first, entry_i)
        last = max(last, exit_i)
    if not indexed:
        return {"max_dd_pts": round(closed_dd, 2), "max_dd_closed_pts": round(closed_dd, 2)}

    peak = 0.0
    max_dd = 0.0
    for i in range(first, last + 1):
        stamp = opens[i]
        mark = float(bars[i].close)
        equity = 0.0
        for entry_i, exit_i, trade in indexed:
            if i < entry_i:
                continue
            if i >= exit_i:
                equity += float(trade.get("pts") or 0)
                continue
            partial_at = _stamp(trade.get("partial_ts"))
            locked = bool(trade.get("partial_hit")) and partial_at is not None and stamp >= partial_at
            equity += _open_mark_pts(trade, mark, params, ps, locked)
        if equity > peak:
            peak = equity
        max_dd = max(max_dd, peak - equity)
    return {"max_dd_pts": round(max_dd, 2), "max_dd_closed_pts": round(closed_dd, 2)}


def _mark_drawdown(
    rows: Sequence[Dict[str, Any]],
    bars: Sequence[Candle],
    params: CrtParams,
    ps: float,
) -> Dict[str, float]:
    return mark_drawdown(rows, bars, params, ps)


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
