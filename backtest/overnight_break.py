"""
Overnight / Asia range breakout strategy (pure — no web, no MT5).

Bucharest time Asia window → first 15m close outside with min break pts
→ optional pullback entry (EMA touch or higher/lower close resume).

Entry modes:
  off       : enter on break candle close
  required  : must get EMA touch or higher-close resume within max wait, else skip
  preferred : try pullback; on timeout enter at market (or skip / worst)

No partial take-profit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import Candle, CandleBuilder, is_market_open, to_utc
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol


@dataclass
class OvernightParams:
    timezone: str = "Europe/Bucharest"
    # Asia window (local hours, inclusive start, exclusive end)
    asia_start_hour: int = 0
    asia_end_hour: int = 7
    min_asia_range_pts: float = 300.0
    # Break confirmation
    min_break_pts_above: float = 200.0
    min_break_pts_below: float = 200.0
    max_break_candles_after: int = 8  # how many closed 15m after Asia end still count as first break
    require_close_outside: bool = True
    # Pullback / entry
    pullback_mode: str = "required"  # off | required | preferred
    ema_period: int = 21
    ema_tf_min: int = 15
    max_wait_candles: int = 8  # 15m candles after break
    timeout_action: str = "skip"  # skip | market | worst  (only for preferred)
    use_higher_close: bool = True  # higher/lower close resume during wait
    # Risk
    sl_mode: str = "asia_opposite"  # fixed | asia_opposite | range_width
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    tp_mode: str = "range_mult"  # fixed | range_mult | r_mult
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.5
    tp_r_mult: float = 2.0
    trail_arm_pts: float = 400.0  # profit before trail activates (0 = off)
    trail_pts: float = 250.0
    max_hold_hours: float = 10.0
    flatten_hour: int = 18  # local hour hard flatten
    one_trade_per_day: bool = True
    side_filter: str = "both"  # both | long | short


@dataclass
class OvernightTrade:
    local_date: str
    side: str  # UP | DOWN
    asia_high: float
    asia_low: float
    asia_range_pts: float
    break_ts: str
    break_price: float
    break_candle_open: float
    break_candle_close: float
    entry_ts: str
    entry: float
    entry_reason: str  # break_close | ema_touch | higher_close | timeout_market | timeout_worst
    sl: float
    tp: float
    sl_pts: float
    tp_pts: float
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None  # tp | sl | trail | flatten | timeout
    pts: float = 0.0
    trail_armed: bool = False
    max_fav_pts: float = 0.0
    max_adv_pts: float = 0.0


@dataclass
class OvernightSkip:
    local_date: str
    reason: str


def _local(ts: datetime, tz: ZoneInfo) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(tz)


def _at_local(d: date, hour: int, minute: int, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=tz)


def _mid(tick: Tick) -> float:
    return tick.mid


def _ema(values: Sequence[float], period: int) -> Optional[float]:
    if len(values) < period or period < 1:
        return None
    k = 2.0 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1.0 - k)
    return e


def _fav_pts(side: str, entry: float, px: float, ps: float) -> float:
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _adv_pts(side: str, entry: float, px: float, ps: float) -> float:
    return -_fav_pts(side, entry, px, ps)


def _hit_level(side: str, px: float, level: float, is_sl: bool) -> bool:
    if is_sl:
        if side == "UP":
            return px <= level + 1e-12
        return px >= level - 1e-12
    # TP
    if side == "UP":
        return px >= level - 1e-12
    return px <= level + 1e-12


def _compute_sl_tp(
    side: str,
    entry: float,
    asia_high: float,
    asia_low: float,
    params: OvernightParams,
    ps: float,
) -> Tuple[float, float, float, float]:
    range_pts = (asia_high - asia_low) / ps

    # SL
    if params.sl_mode == "fixed":
        sl_dist = params.sl_fixed_pts * ps
        sl = entry - sl_dist if side == "UP" else entry + sl_dist
    elif params.sl_mode == "range_width":
        sl_dist = range_pts * params.sl_range_mult * ps
        sl = entry - sl_dist if side == "UP" else entry + sl_dist
    else:  # asia_opposite
        if side == "UP":
            sl = asia_low
            if sl >= entry:
                sl = entry - params.sl_fixed_pts * ps
        else:
            sl = asia_high
            if sl <= entry:
                sl = entry + params.sl_fixed_pts * ps

    sl_pts = abs(entry - sl) / ps

    # TP
    if params.tp_mode == "fixed":
        tp_dist = params.tp_fixed_pts * ps
    elif params.tp_mode == "r_mult":
        tp_dist = sl_pts * params.tp_r_mult * ps
    else:  # range_mult
        tp_dist = range_pts * params.tp_range_mult * ps

    tp = entry + tp_dist if side == "UP" else entry - tp_dist
    tp_pts = abs(tp - entry) / ps
    return sl, tp, sl_pts, tp_pts


def _simulate_from_entry(
    ticks: Sequence[Tick],
    start_index: int,
    *,
    side: str,
    entry: float,
    sl: float,
    tp: float,
    params: OvernightParams,
    ps: float,
    tz: ZoneInfo,
    flatten_local: datetime,
) -> Tuple[str, datetime, float, float, bool, float, float]:
    """
    Walk ticks after fill.
    Returns (reason, exit_ts, exit_px, pts, trail_armed, max_fav, max_adv).
    """
    trail_armed = False
    trail_level: Optional[float] = None
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    last_ts = ticks[start_index].ts
    last_px = entry
    hold_deadline = ticks[start_index].ts + timedelta(hours=float(params.max_hold_hours))

    for i in range(start_index + 1, len(ticks)):
        t = ticks[i]
        loc = _local(t.ts, tz)
        px = _mid(t)
        last_ts, last_px = t.ts, px

        fav = _fav_pts(side, entry, px, ps)
        adv = _adv_pts(side, entry, px, ps)
        if fav > max_fav:
            max_fav = fav
            best_px = px
        if adv > max_adv:
            max_adv = adv

        # Hard flatten
        if loc >= flatten_local or t.ts >= hold_deadline:
            pts = _fav_pts(side, entry, px, ps)
            return "flatten", t.ts, px, pts, trail_armed, max_fav, max_adv

        # Trail arm
        if params.trail_arm_pts > 0 and not trail_armed and fav >= params.trail_arm_pts:
            trail_armed = True
            if side == "UP":
                trail_level = best_px - params.trail_pts * ps
            else:
                trail_level = best_px + params.trail_pts * ps

        # Update trail
        if trail_armed and trail_level is not None:
            if side == "UP":
                new_trail = best_px - params.trail_pts * ps
                if new_trail > trail_level:
                    trail_level = new_trail
                if px <= trail_level + 1e-12:
                    pts = _fav_pts(side, entry, trail_level, ps)
                    return "trail", t.ts, trail_level, pts, True, max_fav, max_adv
            else:
                new_trail = best_px + params.trail_pts * ps
                if new_trail < trail_level:
                    trail_level = new_trail
                if px >= trail_level - 1e-12:
                    pts = _fav_pts(side, entry, trail_level, ps)
                    return "trail", t.ts, trail_level, pts, True, max_fav, max_adv

        # Fixed SL / TP
        if _hit_level(side, px, sl, is_sl=True):
            pts = _fav_pts(side, entry, sl, ps)
            return "sl", t.ts, sl, pts, trail_armed, max_fav, max_adv
        if _hit_level(side, px, tp, is_sl=False):
            pts = _fav_pts(side, entry, tp, ps)
            return "tp", t.ts, tp, pts, trail_armed, max_fav, max_adv

    pts = _fav_pts(side, entry, last_px, ps)
    return "timeout", last_ts, last_px, pts, trail_armed, max_fav, max_adv


def run_overnight(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[OvernightParams] = None,
) -> Dict[str, Any]:
    params = params or OvernightParams()
    tz = ZoneInfo(params.timezone)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return _empty_result(params, symbol=sym, ticks=len(ticks or []))

    builder = CandleBuilder(timeframe_minutes=15, max_completed=200)
    completed: List[Candle] = []

    # Pre-build all 15m candles from ticks
    for t in ticks:
        closed = builder.add_price(_mid(t), t.ts)
        if closed is not None:
            completed.append(closed)

    # Index ticks by time for fast seek
    n = len(ticks)

    def find_tick_index(ts: datetime) -> int:
        # linear is fine for day-sized packs; binary would be better for long ranges
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if ticks[mid].ts < ts:
                lo = mid + 1
            else:
                hi = mid
        return lo

    # Group completed candles by local date
    by_day: Dict[date, List[Candle]] = {}
    for c in completed:
        d = _local(c.open_time, tz).date()
        by_day.setdefault(d, []).append(c)

    trades: List[OvernightTrade] = []
    skips: List[OvernightSkip] = []
    traded_days: set = set()

    dates = sorted(by_day.keys())

    for day in dates:
        if params.one_trade_per_day and day in traded_days:
            continue

        day_candles = by_day[day]
        if not day_candles:
            skips.append(OvernightSkip(day.isoformat(), "no_candles"))
            continue

        # Asia window candles (open_time local hour in [start, end))
        asia_candles = [
            c
            for c in day_candles
            if params.asia_start_hour
            <= _local(c.open_time, tz).hour
            < params.asia_end_hour
        ]
        if not asia_candles:
            # also include previous day's late candles if window crosses midnight
            prev = day - timedelta(days=1)
            if prev in by_day and params.asia_start_hour > params.asia_end_hour:
                asia_candles = [
                    c
                    for c in by_day[prev]
                    if _local(c.open_time, tz).hour >= params.asia_start_hour
                ] + [
                    c
                    for c in day_candles
                    if _local(c.open_time, tz).hour < params.asia_end_hour
                ]
        if len(asia_candles) < 2:
            skips.append(OvernightSkip(day.isoformat(), "thin_asia"))
            continue

        asia_high = max(c.high for c in asia_candles)
        asia_low = min(c.low for c in asia_candles)
        asia_range_pts = (asia_high - asia_low) / ps
        if asia_range_pts < params.min_asia_range_pts:
            skips.append(OvernightSkip(day.isoformat(), "asia_too_small"))
            continue

        # Candles after Asia end that can still produce the first break
        post_asia = [
            c
            for c in day_candles
            if _local(c.open_time, tz).hour >= params.asia_end_hour
        ][: params.max_break_candles_after]

        break_candle: Optional[Candle] = None
        side: Optional[str] = None

        for c in post_asia:
            if not c.is_closed:
                continue
            up_break = c.close >= asia_high + params.min_break_pts_above * ps
            dn_break = c.close <= asia_low - params.min_break_pts_below * ps
            if params.require_close_outside:
                if up_break:
                    break_candle, side = c, "UP"
                    break
                if dn_break:
                    break_candle, side = c, "DOWN"
                    break
            else:
                # wick-based (less strict)
                if c.high >= asia_high + params.min_break_pts_above * ps:
                    break_candle, side = c, "UP"
                    break
                if c.low <= asia_low - params.min_break_pts_below * ps:
                    break_candle, side = c, "DOWN"
                    break

        if break_candle is None or side is None:
            skips.append(OvernightSkip(day.isoformat(), "no_break"))
            continue

        if params.side_filter == "long" and side != "UP":
            skips.append(OvernightSkip(day.isoformat(), "side_filter"))
            continue
        if params.side_filter == "short" and side != "DOWN":
            skips.append(OvernightSkip(day.isoformat(), "side_filter"))
            continue

        # --- Entry logic ---
        entry_ts: Optional[datetime] = None
        entry_px: Optional[float] = None
        entry_reason = "break_close"
        entry_idx = find_tick_index(break_candle.close_time)

        if params.pullback_mode == "off":
            # Enter at break candle close (or first tick after)
            if entry_idx >= n:
                skips.append(OvernightSkip(day.isoformat(), "no_entry_tick"))
                continue
            entry_ts = ticks[entry_idx].ts
            entry_px = _mid(ticks[entry_idx])
            entry_reason = "break_close"
        else:
            # Wait window for EMA or higher-close
            wait_candles = post_asia[
                post_asia.index(break_candle) + 1 : post_asia.index(break_candle)
                + 1
                + params.max_wait_candles
            ]
            # Need enough history for EMA
            hist_closes = [c.close for c in completed if c.close_time <= break_candle.close_time]
            found = False
            worst_px = _mid(ticks[entry_idx]) if entry_idx < n else break_candle.close

            for wc in wait_candles:
                # Update EMA with closes up to previous candle
                closes_for_ema = [
                    c.close for c in completed if c.close_time < wc.open_time
                ]
                ema_val = _ema(closes_for_ema[-params.ema_period * 2 :], params.ema_period)

                # Higher / lower close resume
                if params.use_higher_close and len(closes_for_ema) >= 1:
                    prev_close = closes_for_ema[-1]
                    if side == "UP" and wc.close > prev_close + 1e-12:
                        # resume strength
                        idx = find_tick_index(wc.close_time)
                        if idx < n:
                            entry_ts = ticks[idx].ts
                            entry_px = _mid(ticks[idx])
                            entry_reason = "higher_close"
                            entry_idx = idx
                            found = True
                            break
                    if side == "DOWN" and wc.close < prev_close - 1e-12:
                        idx = find_tick_index(wc.close_time)
                        if idx < n:
                            entry_ts = ticks[idx].ts
                            entry_px = _mid(ticks[idx])
                            entry_reason = "higher_close"  # same label, direction handled by side
                            entry_idx = idx
                            found = True
                            break

                # EMA touch during this candle (scan ticks of the candle)
                if ema_val is not None:
                    c_start = find_tick_index(wc.open_time)
                    c_end = find_tick_index(wc.close_time)
                    for ti in range(c_start, min(c_end + 1, n)):
                        px = _mid(ticks[ti])
                        if side == "UP":
                            worst_px = min(worst_px, px)
                            if px <= ema_val + 1e-9:
                                entry_ts = ticks[ti].ts
                                entry_px = px
                                entry_reason = "ema_touch"
                                entry_idx = ti
                                found = True
                                break
                        else:
                            worst_px = max(worst_px, px)
                            if px >= ema_val - 1e-9:
                                entry_ts = ticks[ti].ts
                                entry_px = px
                                entry_reason = "ema_touch"
                                entry_idx = ti
                                found = True
                                break
                    if found:
                        break

            if not found:
                if params.pullback_mode == "required":
                    skips.append(OvernightSkip(day.isoformat(), "no_pullback"))
                    continue
                # preferred → timeout action
                if params.timeout_action == "skip":
                    skips.append(OvernightSkip(day.isoformat(), "no_pullback_timeout"))
                    continue
                if entry_idx >= n:
                    skips.append(OvernightSkip(day.isoformat(), "no_entry_tick"))
                    continue
                if params.timeout_action == "worst":
                    entry_px = worst_px
                    entry_reason = "timeout_worst"
                else:
                    entry_px = _mid(ticks[entry_idx])
                    entry_reason = "timeout_market"
                entry_ts = ticks[entry_idx].ts

        if entry_ts is None or entry_px is None:
            skips.append(OvernightSkip(day.isoformat(), "no_entry"))
            continue

        sl, tp, sl_pts, tp_pts = _compute_sl_tp(
            side, entry_px, asia_high, asia_low, params, ps
        )

        flatten_local = _at_local(day, params.flatten_hour, 0, tz)
        if _local(entry_ts, tz) >= flatten_local:
            skips.append(OvernightSkip(day.isoformat(), "past_flatten"))
            continue

        reason, exit_ts, exit_px, pts, trail_armed, max_fav, max_adv = _simulate_from_entry(
            ticks,
            entry_idx,
            side=side,
            entry=entry_px,
            sl=sl,
            tp=tp,
            params=params,
            ps=ps,
            tz=tz,
            flatten_local=flatten_local,
        )

        trades.append(
            OvernightTrade(
                local_date=day.isoformat(),
                side=side,
                asia_high=round(asia_high, 5),
                asia_low=round(asia_low, 5),
                asia_range_pts=round(asia_range_pts, 1),
                break_ts=break_candle.close_time.isoformat(),
                break_price=round(break_candle.close, 5),
                break_candle_open=round(break_candle.open, 5),
                break_candle_close=round(break_candle.close, 5),
                entry_ts=entry_ts.isoformat(),
                entry=round(entry_px, 5),
                entry_reason=entry_reason,
                sl=round(sl, 5),
                tp=round(tp, 5),
                sl_pts=round(sl_pts, 1),
                tp_pts=round(tp_pts, 1),
                exit_ts=exit_ts.isoformat() if exit_ts else None,
                exit=round(exit_px, 5),
                exit_reason=reason,
                pts=round(pts, 1),
                trail_armed=trail_armed,
                max_fav_pts=round(max_fav, 1),
                max_adv_pts=round(max_adv, 1),
            )
        )
        traded_days.add(day)

    return summarize_overnight(trades, skips, params, symbol=sym, ticks=len(ticks))


def summarize_overnight(
    trades: Sequence[OvernightTrade],
    skips: Sequence[OvernightSkip],
    params: OvernightParams,
    *,
    symbol: str,
    ticks: int,
) -> Dict[str, Any]:
    n = len(trades)
    wins = sum(1 for t in trades if t.pts > 1e-9)
    losses = sum(1 for t in trades if t.pts < -1e-9)
    scratches = n - wins - losses
    by_reason: Dict[str, int] = {}
    by_entry: Dict[str, int] = {}
    for t in trades:
        r = t.exit_reason or "?"
        by_reason[r] = by_reason.get(r, 0) + 1
        e = t.entry_reason or "?"
        by_entry[e] = by_entry.get(e, 0) + 1
    skip_reasons: Dict[str, int] = {}
    for s in skips:
        skip_reasons[s.reason] = skip_reasons.get(s.reason, 0) + 1

    def pct(a: int, b: int) -> Optional[float]:
        if b <= 0:
            return None
        return round(100.0 * a / b, 1)

    avg_pts = round(sum(t.pts for t in trades) / n, 1) if n else 0.0
    avg_win = (
        round(sum(t.pts for t in trades if t.pts > 0) / wins, 1) if wins else None
    )
    avg_loss = (
        round(sum(t.pts for t in trades if t.pts < 0) / losses, 1) if losses else None
    )
    gp = sum(t.pts for t in trades if t.pts > 0)
    gl = -sum(t.pts for t in trades if t.pts < 0)
    pf = round(gp / gl, 2) if gl > 1e-9 else None
    trail_n = sum(1 for t in trades if t.trail_armed)

    return {
        "kind": "overnight_break",
        "symbol": symbol,
        "params": asdict(params),
        "ticks": ticks,
        "days_seen": n + len(skips),
        "trades": n,
        "skipped": len(skips),
        "skip_reasons": skip_reasons,
        "wins": wins,
        "losses": losses,
        "scratches": scratches,
        "win_pct": pct(wins, n),
        "exits": by_reason,
        "entries": by_entry,
        "trail_armed_n": trail_n,
        "trail_armed_pct": pct(trail_n, n),
        "avg_pts": avg_pts,
        "avg_win_pts": avg_win,
        "avg_loss_pts": avg_loss,
        "profit_factor": pf,
        "sum_pts": round(sum(t.pts for t in trades), 1),
        "rows": [asdict(t) for t in trades],
        "skips": [asdict(s) for s in skips],
    }


def _empty_result(params: OvernightParams, *, symbol: str, ticks: int) -> Dict[str, Any]:
    return summarize_overnight([], [], params, symbol=symbol, ticks=ticks)
