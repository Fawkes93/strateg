"""Asia pullback: half-hour box, fractional close break, one resting level.

The 15m box is bars that open in [00:00, box_end). The first later 15m close
at least break_frac of that range past an edge arms the side. The arming bar
does not fill. A new impulse extreme moves a leg-fib order and that bar does
not enter. Entry is a touch, or a 5m close back in the break direction after
the touch. Stop and target come from the overnight exit engine.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from backtest.asia_liquidity import wilder_atr
from backtest.candles import Candle, CandleBuilder, aggregate_tf, build_candles, to_utc
from backtest.config import point_size
from backtest.dukascopy import reaktor_symbol
from backtest.overnight_break import (
    OvernightParams,
    _CandleFeed,
    _TickFeed,
    _at_local,
    _compute_sl_tp,
    _ema,
    _local,
    _mid,
    ma_series_values,
    require_zone,
    trade_fib_px,
)

_LEVELS = ("leg_fib", "box_fib", "ema")
_CONFIRMS = ("touch", "close5m")
_MAS = ("ema", "kama", "hma", "zlema")
_SL_MODES = ("asia_opposite", "fixed", "range")
_TP_MODES = ("range_mult", "fixed", "sl_mult", "fixed_cap")
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass
class AsiaPullbackParams:
    timezone: str = "Europe/Bucharest"
    box_end_hour: int = 4
    box_end_minute: int = 30
    listen_end_hour: int = 9
    listen_end_minute: int = 0
    break_frac: float = 0.25
    level_ref: str = "leg_fib"  # leg_fib | box_fib | ema
    fib_level: float = 0.382
    ma_type: str = "ema"  # ema | kama | hma | zlema
    ema_period: int = 20
    ema_tf_min: int = 60
    kama_fast: int = 2
    kama_slow: int = 30
    confirm_mode: str = "touch"  # touch | close5m
    sl_mode: str = "asia_opposite"  # asia_opposite | fixed | range
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    sl_cap_pts: float = 0.0
    tp_mode: str = "range_mult"  # range_mult | fixed | sl_mult | fixed_cap
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.0
    tp_sl_mult: float = 2.0
    flatten_hour: int = 23
    cost_pts: float = 0.0  # flat round-trip cost, subtracted from pts. 0 = off
    # Optional fade. Off leaves the continuation path unchanged.
    reversal: bool = False
    sr_days: int = 5
    sr_min_touches: int = 2
    sr_tol_frac: float = 0.25  # shelf width, as a fraction of H1 ATR
    sr_pdhl: bool = True  # yesterday's high and low count even as a single print


def normalize_params(params: AsiaPullbackParams) -> AsiaPullbackParams:
    params.timezone = str(params.timezone or "Europe/Bucharest").strip() or "Europe/Bucharest"
    require_zone(params.timezone)
    params.box_end_hour = _clamp_int(params.box_end_hour, 0, 23, 4)
    params.box_end_minute = _clamp_int(params.box_end_minute, 0, 59, 30)
    params.listen_end_hour = _clamp_int(params.listen_end_hour, 0, 23, 9)
    params.listen_end_minute = _clamp_int(params.listen_end_minute, 0, 59, 0)
    box_m = params.box_end_hour * 60 + params.box_end_minute
    listen_m = params.listen_end_hour * 60 + params.listen_end_minute
    if listen_m <= box_m:
        raise ValueError("listen_end must be after box_end on the same day")
    try:
        params.break_frac = max(0.0, float(params.break_frac))
    except (TypeError, ValueError):
        params.break_frac = 0.25
    ref = str(params.level_ref or "leg_fib").strip().lower().replace("-", "_")
    if ref in ("leg", "legfib"):
        ref = "leg_fib"
    if ref in ("box", "boxfib", "asia"):
        ref = "box_fib"
    if ref not in _LEVELS:
        raise ValueError("level_ref must be leg_fib, box_fib, or ema")
    params.level_ref = ref
    try:
        params.fib_level = min(1.0, max(0.0, float(params.fib_level)))
    except (TypeError, ValueError):
        params.fib_level = 0.382
    kind = str(params.ma_type or "ema").strip().lower()
    if kind not in _MAS:
        raise ValueError("ma_type must be ema, kama, hma, or zlema")
    params.ma_type = kind
    params.ema_period = max(1, _clamp_int(params.ema_period, 1, 500, 20))
    params.ema_tf_min = max(15, _clamp_int(params.ema_tf_min, 15, 240, 60))
    params.kama_fast = max(1, _clamp_int(params.kama_fast, 1, 50, 2))
    params.kama_slow = max(1, _clamp_int(params.kama_slow, 1, 200, 30))
    confirm = str(params.confirm_mode or "touch").strip().lower().replace("-", "")
    if confirm in ("close", "close_5m", "5m"):
        confirm = "close5m"
    if confirm not in _CONFIRMS:
        raise ValueError("confirm_mode must be touch or close5m")
    params.confirm_mode = confirm
    sl = str(params.sl_mode or "asia_opposite").strip().lower()
    if sl in ("asia", "opposite", "asia_opp"):
        sl = "asia_opposite"
    if sl not in _SL_MODES:
        raise ValueError("sl_mode must be asia_opposite, fixed, or range")
    params.sl_mode = sl
    params.sl_fixed_pts = max(1.0, _flt(params.sl_fixed_pts, 500.0))
    params.sl_range_mult = max(0.0, _flt(params.sl_range_mult, 1.0))
    params.sl_cap_pts = max(0.0, _flt(params.sl_cap_pts, 0.0))
    tp = str(params.tp_mode or "range_mult").strip().lower()
    if tp not in _TP_MODES:
        raise ValueError("tp_mode must be range_mult, fixed, sl_mult, or fixed_cap")
    params.tp_mode = tp
    params.tp_fixed_pts = max(1.0, _flt(params.tp_fixed_pts, 1000.0))
    params.tp_range_mult = max(0.0, _flt(params.tp_range_mult, 1.0))
    params.tp_sl_mult = max(0.0, _flt(params.tp_sl_mult, 2.0))
    params.flatten_hour = _clamp_int(params.flatten_hour, 0, 23, 23)
    params.cost_pts = max(0.0, _flt(params.cost_pts, 0.0))
    params.reversal = bool(params.reversal)
    params.sr_days = _clamp_int(params.sr_days, 1, 30, 5)
    params.sr_min_touches = _clamp_int(params.sr_min_touches, 1, 10, 2)
    params.sr_tol_frac = min(2.0, max(0.0, _flt(params.sr_tol_frac, 0.25)))
    params.sr_pdhl = bool(params.sr_pdhl)
    return params


def leg_fib_px(extreme: float, edge: float, level: float) -> float:
    """Fib 0 is the live extreme. Fib 1 is the broken box edge."""
    return float(extreme) - float(level) * (float(extreme) - float(edge))


def run_asia_pullback(
    ticks: Sequence[Any],
    *,
    symbol: str = "XAUUSD",
    params: Optional[AsiaPullbackParams] = None,
    progress: Optional[Callable[..., None]] = None,
    stop: Optional[Callable[[], bool]] = None,
    date_from: Any = None,
    date_to: Any = None,
) -> Dict[str, Any]:
    params = normalize_params(params or AsiaPullbackParams())
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return _empty(params, symbol=sym, ticks=len(ticks or []), data_source="ticks")
    completed: List[Candle] = []
    builder = CandleBuilder(timeframe_minutes=15, max_completed=200, skip_ignored=False)
    for t in ticks:
        closed = builder.add_price(_mid(t), t.ts)
        if closed is not None:
            completed.append(closed)
    m5 = build_candles(ticks, 5, skip_ignored=False)
    return _run_days(
        completed,
        m5,
        _TickFeed(ticks),
        params=params,
        symbol=sym,
        ps=ps,
        progress=progress,
        stop=stop,
        date_from=_as_date(date_from),
        date_to=_as_date(date_to),
        data_source="ticks",
        n_source=len(ticks),
    )


def run_asia_pullback_on_candles(
    candles_5m: Sequence[Candle],
    *,
    symbol: str = "XAUUSD",
    params: Optional[AsiaPullbackParams] = None,
    progress: Optional[Callable[..., None]] = None,
    stop: Optional[Callable[[], bool]] = None,
    date_from: Any = None,
    date_to: Any = None,
) -> Dict[str, Any]:
    params = normalize_params(params or AsiaPullbackParams())
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not candles_5m:
        return _empty(
            params, symbol=sym, ticks=len(candles_5m or []), data_source="candles_5m"
        )
    m5 = list(candles_5m)
    m15 = aggregate_tf(m5, 15)
    if progress:
        progress(
            phase="candles",
            message=f"5m→15m {len(m15):,} bars from {len(m5):,} 5m",
            days_done=0,
            days_total=0,
            trades=0,
        )
    return _run_days(
        m15,
        m5,
        _CandleFeed(m5),
        params=params,
        symbol=sym,
        ps=ps,
        progress=progress,
        stop=stop,
        date_from=_as_date(date_from),
        date_to=_as_date(date_to),
        data_source="candles_5m",
        n_source=len(m5),
    )


def _run_days(
    m15: Sequence[Candle],
    m5: Sequence[Candle],
    feed: Any,
    *,
    params: AsiaPullbackParams,
    symbol: str,
    ps: float,
    progress: Optional[Callable[..., None]],
    stop: Optional[Callable[[], bool]],
    date_from: Optional[date],
    date_to: Optional[date],
    data_source: str,
    n_source: int,
) -> Dict[str, Any]:
    tz = require_zone(params.timezone)
    box_m = params.box_end_hour * 60 + params.box_end_minute
    listen_m = params.listen_end_hour * 60 + params.listen_end_minute
    by_day: Dict[date, List[Candle]] = {}
    for bar in m15:
        d = _local(bar.open_time, tz).date()
        by_day.setdefault(d, []).append(bar)
    ma_bars = aggregate_tf(m15, int(params.ema_tf_min))
    ma_values = _ma_values([c.close for c in ma_bars], params)
    ma_closes = [to_utc(c.close_time) for c in ma_bars]
    h1 = aggregate_tf(m15, 60)
    h1_atr = wilder_atr(h1, 14)
    h1_closes = [to_utc(c.close_time) for c in h1]
    five_opens = [to_utc(c.open_time) for c in m5]
    tick_feed = hasattr(feed, "ticks")
    exit_params = _exit_params(params)
    trades: List[Dict[str, Any]] = []
    skips: List[Dict[str, Any]] = []
    cancelled = False
    days = sorted(by_day)
    n_days = len(days)

    for di, day in enumerate(days):
        if stop and stop():
            cancelled = True
            break
        if progress and (di % 5 == 0 or di + 1 == n_days):
            progress(
                phase="replay",
                days_done=di + 1,
                days_total=n_days,
                trades=len(trades),
                message=f"Day {day.isoformat()} · {len(trades)} trades",
            )
        if date_from is not None and day < date_from:
            continue
        if date_to is not None and day >= date_to:
            continue
        listen_dt = _at_local(day, params.listen_end_hour, params.listen_end_minute, tz)
        flatten_local = _at_local(day, params.flatten_hour, 0, tz)
        box_end_dt = _at_local(day, params.box_end_hour, params.box_end_minute, tz)
        day_bars = by_day[day]
        box = [b for b in day_bars if _minutes(_local(b.open_time, tz)) < box_m]
        if not box:
            skips.append(_skip(day, "no_box"))
            continue
        box_high = max(b.high for b in box)
        box_low = min(b.low for b in box)
        box_rng = box_high - box_low
        signal = [
            b
            for b in day_bars
            if box_m <= _minutes(_local(b.open_time, tz)) < listen_m
            and _local(b.close_time, tz) <= listen_dt
        ]
        entered = False
        if params.reversal and box_rng > 0:
            entered = _scan_reversal(
                trades,
                day=day,
                day_bars=day_bars,
                signal=signal,
                by_day=by_day,
                box_high=box_high,
                box_low=box_low,
                box_rng=box_rng,
                ps=ps,
                tz=tz,
                params=params,
                exit_params=exit_params,
                feed=feed,
                tick_feed=tick_feed,
                m5=m5,
                five_opens=five_opens,
                flatten_local=flatten_local,
                h1=h1,
                h1_atr=h1_atr,
                h1_closes=h1_closes,
                box_end_dt=box_end_dt,
                listen_dt=listen_dt,
            )
        if entered:
            continue
        side, arm_i = _first_break(signal, box_high, box_low, params.break_frac)
        if side is None or arm_i is None:
            skips.append(
                _skip(day, "no_break", high=box_high, low=box_low, ps=ps)
            )
            continue
        arm = signal[arm_i]
        extreme = arm.high if side == "UP" else arm.low
        edge = box_high if side == "UP" else box_low
        pending: Optional[float] = None
        reason_skip = "no_fill"
        for bar in signal[arm_i + 1 :]:
            extended = _extended(side, bar, extreme)
            if params.level_ref == "leg_fib" and extended:
                # The bar that makes a new extreme moves the order and does not fill.
                # A 5m close through the far edge on the way still cancels the setup.
                if params.confirm_mode == "close5m":
                    probe = _close5m_fill(
                        m5, five_opens, bar, side, None, None, box_high, box_low
                    )
                    if probe == "cancel":
                        reason_skip = "cancelled"
                        break
                if _through_opposite(side, bar.close, box_high, box_low):
                    reason_skip = "cancelled"
                    break
                extreme = bar.high if side == "UP" else bar.low
                pending = None
                continue
            level = _level_at(
                params,
                side,
                extreme,
                edge,
                box_high,
                box_low,
                _ma_asof(ma_closes, ma_values, bar.open_time),
            )
            if params.confirm_mode == "close5m":
                hit = _close5m_fill(
                    m5,
                    five_opens,
                    bar,
                    side,
                    level,
                    pending,
                    box_high,
                    box_low,
                )
                if hit == "cancel":
                    reason_skip = "cancelled"
                    break
                if isinstance(hit, tuple):
                    pending = hit[2]
                    if _take(
                        trades,
                        day=day,
                        side=side,
                        box_high=box_high,
                        box_low=box_low,
                        ps=ps,
                        tz=tz,
                        params=params,
                        exit_params=exit_params,
                        feed=feed,
                        arm=arm,
                        extreme=extreme,
                        level=hit[2],
                        entry_ts=hit[0],
                        entry_px=hit[1],
                        start_index=_sim_start_after_close(feed, hit[0], tick_feed),
                        flatten_local=flatten_local,
                        h1=h1,
                        h1_atr=h1_atr,
                        h1_closes=h1_closes,
                        box_end_dt=box_end_dt,
                    ):
                        entered = True
                    else:
                        reason_skip = "past_flatten"
                    break
                if isinstance(hit, float):
                    pending = hit
            elif level is not None:
                touched, fill, _dist = feed.ema_scan(
                    bar.open_time, bar.close_time, side, level, ps
                )
                if (
                    touched
                    and fill is not None
                    and _local(fill.ts, tz) <= listen_dt
                ):
                    if _take(
                        trades,
                        day=day,
                        side=side,
                        box_high=box_high,
                        box_low=box_low,
                        ps=ps,
                        tz=tz,
                        params=params,
                        exit_params=exit_params,
                        feed=feed,
                        arm=arm,
                        extreme=extreme,
                        level=level,
                        entry_ts=fill.ts,
                        entry_px=fill.px,
                        start_index=fill.index,
                        flatten_local=flatten_local,
                        h1=h1,
                        h1_atr=h1_atr,
                        h1_closes=h1_closes,
                        box_end_dt=box_end_dt,
                    ):
                        entered = True
                    else:
                        reason_skip = "past_flatten"
                    break
            if _through_opposite(side, bar.close, box_high, box_low):
                reason_skip = "cancelled"
                break
            if extended:
                extreme = bar.high if side == "UP" else bar.low
        if not entered:
            skips.append(
                _skip(
                    day,
                    reason_skip,
                    side=side,
                    high=box_high,
                    low=box_low,
                    ps=ps,
                    detail=f"break {arm.close_time.isoformat()}",
                )
            )

    return summarize_asia_pullback(
        trades,
        skips,
        params,
        symbol=symbol,
        ticks=n_source,
        data_source=data_source,
        cancelled=cancelled,
    )


def summarize_asia_pullback(
    trades: Sequence[Dict[str, Any]],
    skips: Sequence[Dict[str, Any]],
    params: AsiaPullbackParams,
    *,
    symbol: str,
    ticks: int,
    data_source: str,
    cancelled: bool = False,
) -> Dict[str, Any]:
    rows = sorted(trades, key=lambda r: (str(r.get("local_date")), str(r.get("entry_ts"))))
    skip_rows = list(skips)
    return {
        "kind": "asia_pullback",
        "symbol": symbol,
        "params": asdict(params),
        "data_source": data_source,
        "ticks": int(ticks),
        "days_seen": len(rows) + len(skip_rows),
        "skipped": len(skip_rows),
        "skip_reasons": _skip_counts(skip_rows),
        "cancelled": bool(cancelled),
        **_stats(rows),
        "by_month": _by_month(rows, skip_rows),
        "rows": rows,
        "skips": skip_rows,
    }


def _take(
    trades: List[Dict[str, Any]],
    *,
    day: date,
    side: str,
    box_high: float,
    box_low: float,
    ps: float,
    tz: Any,
    params: AsiaPullbackParams,
    exit_params: OvernightParams,
    feed: Any,
    arm: Candle,
    extreme: float,
    level: float,
    entry_ts: datetime,
    entry_px: float,
    start_index: int,
    flatten_local: datetime,
    h1: Sequence[Candle],
    h1_atr: Sequence[Optional[float]],
    h1_closes: Sequence[datetime],
    box_end_dt: datetime,
    exit_high: Optional[float] = None,
    exit_low: Optional[float] = None,
    reason: Optional[str] = None,
    sr_kind: Optional[str] = None,
    sr_touches: Optional[int] = None,
) -> bool:
    if _local(entry_ts, tz) >= flatten_local:
        return False
    sl, tp, sl_pts, tp_pts = _compute_sl_tp(
        side,
        float(entry_px),
        box_high if exit_high is None else float(exit_high),
        box_low if exit_low is None else float(exit_low),
        exit_params,
        ps,
    )
    (
        exit_reason,
        exit_ts,
        exit_px,
        pts,
        _trail_armed,
        max_fav,
        max_adv,
        _best,
        _worst,
        _be,
        _shock,
    ) = feed.simulate(
        int(start_index),
        side=side,
        entry=float(entry_px),
        sl=sl,
        tp=tp,
        params=exit_params,
        ps=ps,
        tz=tz,
        flatten_local=flatten_local,
        trail_arm_pts=0.0,
        trail_dist_pts=0.0,
        trail_from_fill=False,
        be_arm_override=0.0,
    )
    gross = float(pts)
    net = gross - float(params.cost_pts or 0.0)
    rng = box_high - box_low
    atr = _ma_asof(list(h1_closes), list(h1_atr), box_end_dt)
    atr_pts = (float(atr) / ps) if atr else None
    box_pts = rng / ps if ps else 0.0
    ratio = (rng / float(atr)) if atr and float(atr) > 0 else None
    entry_reason = reason or (
        "close5m" if params.confirm_mode == "close5m" else params.level_ref
    )
    loc_entry = _local(entry_ts, tz)
    loc_exit = _local(exit_ts, tz) if exit_ts else None
    trades.append(
        {
            "local_date": day.isoformat(),
            "weekday": _WEEKDAYS[day.weekday()],
            "weekday_num": int(day.weekday()),
            "side": side,
            "level_ref": params.level_ref,
            "confirm_mode": params.confirm_mode,
            "box_high": round(box_high, 5),
            "box_low": round(box_low, 5),
            "box_pts": round(box_pts, 1),
            "h1_atr": None if atr is None else round(float(atr), 5),
            "h1_atr_pts": None if atr_pts is None else round(atr_pts, 1),
            "box_h1_atr": None if ratio is None else round(ratio, 3),
            "break_ts": arm.close_time.isoformat(),
            "break_price": round(arm.close, 5),
            "impulse_extreme": round(float(extreme), 5),
            "level": round(float(level), 5),
            "entry_ts": entry_ts.isoformat(),
            "entry_local": loc_entry.strftime("%Y-%m-%d %H:%M"),
            "entry": round(float(entry_px), 5),
            "entry_reason": entry_reason,
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "sl_pts": round(sl_pts, 1),
            "tp_pts": round(tp_pts, 1),
            "exit_ts": exit_ts.isoformat() if exit_ts else None,
            "exit_local": loc_exit.strftime("%Y-%m-%d %H:%M") if loc_exit else None,
            "exit": round(float(exit_px), 5),
            "exit_reason": exit_reason,
            "pts_gross": round(gross, 1),
            "cost_pts": round(float(params.cost_pts or 0.0), 1),
            "pts": round(net, 1),
            "max_fav_pts": round(float(max_fav), 1),
            "max_adv_pts": round(float(max_adv), 1),
            "sr_kind": sr_kind,
            "sr_touches": sr_touches,
        }
    )
    return True


def _scan_reversal(
    trades: List[Dict[str, Any]],
    *,
    day: date,
    day_bars: Sequence[Candle],
    signal: Sequence[Candle],
    by_day: Dict[date, List[Candle]],
    box_high: float,
    box_low: float,
    box_rng: float,
    ps: float,
    tz: Any,
    params: AsiaPullbackParams,
    exit_params: OvernightParams,
    feed: Any,
    tick_feed: bool,
    m5: Sequence[Candle],
    five_opens: Sequence[datetime],
    flatten_local: datetime,
    h1: Sequence[Candle],
    h1_atr: Sequence[Optional[float]],
    h1_closes: Sequence[datetime],
    box_end_dt: datetime,
    listen_dt: datetime,
) -> bool:
    """Fade the first 15m rejection of a shelf built from the prior sessions.

    A shelf is a cluster of daily highs or daily lows inside sr_days, plus
    yesterday's high and low when sr_pdhl is on. The level has to sit outside
    today's locked box. A later close through the level kills it for the day.
    """
    atr = _ma_asof(h1_closes, list(h1_atr), box_end_dt)
    shelves = _obvious_shelves(by_day, day, params, atr, box_rng)
    if not shelves:
        return False
    signal_ids = {id(b) for b in signal}
    dead: set = set()
    for bar in day_bars:
        for i, shelf in enumerate(shelves):
            if i in dead:
                continue
            if _shelf_accepted(bar, shelf):
                dead.add(i)
        if id(bar) not in signal_ids or _local(bar.close_time, tz) > listen_dt:
            continue
        bounce = _best_bounce(bar, shelves, dead, _sr_tol(atr, box_rng, params.sr_tol_frac), box_high, box_low)
        if bounce is None:
            continue
        shelf, side = bounce
        fill = _reversal_fill(
            bar, shelf, side, params, m5, five_opens, box_high, box_low
        )
        if fill is None:
            continue
        entry_ts, entry_px = fill
        if _local(entry_ts, tz) > listen_dt:
            continue
        stop, exit_high, exit_low = _reversal_exit(side, entry_px, bar, box_rng)
        if _take(
            trades,
            day=day,
            side=side,
            box_high=box_high,
            box_low=box_low,
            ps=ps,
            tz=tz,
            params=params,
            exit_params=exit_params,
            feed=feed,
            arm=bar,
            extreme=bar.high if side == "DOWN" else bar.low,
            level=shelf[0],
            entry_ts=entry_ts,
            entry_px=entry_px,
            start_index=_sim_start_after_close(feed, entry_ts, tick_feed),
            flatten_local=flatten_local,
            h1=h1,
            h1_atr=h1_atr,
            h1_closes=h1_closes,
            box_end_dt=box_end_dt,
            exit_high=exit_high,
            exit_low=exit_low,
            reason="reversal",
            sr_kind=shelf[1],
            sr_touches=shelf[2],
        ):
            return True
    return False


def _obvious_shelves(
    by_day: Dict[date, List[Candle]],
    day: date,
    params: AsiaPullbackParams,
    atr: Optional[float],
    box_rng: float,
) -> List[Tuple[float, str, int]]:
    """(price, resistance|support, touches) from completed sessions before day."""
    prior = [d for d in sorted(by_day) if d < day and by_day[d]]
    prior = prior[-int(params.sr_days) :]
    if not prior:
        return []
    highs: List[float] = []
    lows: List[float] = []
    for d in prior:
        bars = by_day[d]
        highs.append(max(b.high for b in bars))
        lows.append(min(b.low for b in bars))
    tol = _sr_tol(atr, box_rng, params.sr_tol_frac)
    shelves: List[Tuple[float, str, int]] = []
    shelves.extend(_cluster_prices(highs, "resistance", tol, int(params.sr_min_touches)))
    shelves.extend(_cluster_prices(lows, "support", tol, int(params.sr_min_touches)))
    if params.sr_pdhl:
        shelves.append((highs[-1], "resistance", 1))
        shelves.append((lows[-1], "support", 1))
    return _merge_shelves(shelves, tol)


def _cluster_prices(
    prices: Sequence[float], kind: str, tol: float, min_touches: int
) -> List[Tuple[float, str, int]]:
    xs = sorted(float(p) for p in prices)
    if not xs:
        return []
    groups: List[List[float]] = [[xs[0]]]
    for x in xs[1:]:
        if x - groups[-1][0] <= tol + 1e-12:
            groups[-1].append(x)
        else:
            groups.append([x])
    out: List[Tuple[float, str, int]] = []
    need = max(1, int(min_touches))
    for g in groups:
        if len(g) >= need:
            out.append((sum(g) / len(g), kind, len(g)))
    return out


def _merge_shelves(
    shelves: Sequence[Tuple[float, str, int]], tol: float
) -> List[Tuple[float, str, int]]:
    """Collapse a repeated extreme and a nearby cluster into one price."""
    out: List[Tuple[float, str, int]] = []
    for price, kind, touches in shelves:
        merged = False
        for i, (p0, k0, n0) in enumerate(out):
            if k0 == kind and abs(p0 - price) <= tol + 1e-12:
                n = max(n0, touches)
                # Keep the price with more prints. A tie stays on the first.
                kept = p0 if n0 >= touches else price
                out[i] = (kept, kind, n)
                merged = True
                break
        if not merged:
            out.append((price, kind, touches))
    return out


def _sr_tol(atr: Optional[float], box_rng: float, frac: float) -> float:
    width = max(0.0, float(frac))
    if atr and float(atr) > 0:
        return width * float(atr)
    return 0.15 * max(0.0, box_rng)


def _shelf_accepted(bar: Candle, shelf: Tuple[float, str, int]) -> bool:
    price, kind, _n = shelf
    if kind == "resistance":
        return bar.close > price + 1e-9
    return bar.close < price - 1e-9


def _best_bounce(
    bar: Candle,
    shelves: Sequence[Tuple[float, str, int]],
    dead: set,
    tol: float,
    box_high: float,
    box_low: float,
) -> Optional[Tuple[Tuple[float, str, int], str]]:
    hits: List[Tuple[Tuple[float, str, int], str]] = []
    for i, shelf in enumerate(shelves):
        if i in dead:
            continue
        side = _bounce_side(bar, shelf, tol, box_high, box_low)
        if side is not None:
            hits.append((shelf, side))
    if not hits:
        return None
    kinds = {side for _shelf, side in hits}
    if len(kinds) > 1:
        return None
    if hits[0][1] == "DOWN":
        # Rising into resistance: the nearest ceiling is the lowest one reached.
        return min(hits, key=lambda h: h[0][0])
    return max(hits, key=lambda h: h[0][0])


def _bounce_side(
    bar: Candle,
    shelf: Tuple[float, str, int],
    tol: float,
    box_high: float,
    box_low: float,
) -> Optional[str]:
    price, kind, _n = shelf
    if kind == "resistance":
        if price <= box_high + 1e-9:
            return None
        reached = bar.high >= price - tol
        back = bar.close < price - 1e-12 and bar.close < bar.open - 1e-12
        still_alive = bar.close > box_low + 1e-12
        return "DOWN" if reached and back and still_alive else None
    if price >= box_low - 1e-9:
        return None
    reached = bar.low <= price + tol
    back = bar.close > price + 1e-12 and bar.close > bar.open + 1e-12
    still_alive = bar.close < box_high - 1e-12
    return "UP" if reached and back and still_alive else None


def _reversal_fill(
    bar: Candle,
    shelf: Tuple[float, str, int],
    side: str,
    params: AsiaPullbackParams,
    m5: Sequence[Candle],
    five_opens: Sequence[datetime],
    box_high: float,
    box_low: float,
) -> Optional[Tuple[datetime, float]]:
    price = shelf[0]
    if params.confirm_mode != "close5m":
        return bar.close_time, float(bar.close)
    a = bisect_left(five_opens, to_utc(bar.open_time))
    b = bisect_left(five_opens, to_utc(bar.close_time))
    tagged = False
    tol_tag = bar.high >= price - 1e-9 if side == "DOWN" else bar.low <= price + 1e-9
    for c5 in m5[a:b]:
        if _through_opposite(side, c5.close, box_high, box_low):
            return None
        if not tagged:
            if side == "DOWN" and c5.high >= price - 1e-9:
                tagged = True
            elif side == "UP" and c5.low <= price + 1e-9:
                tagged = True
        if tagged and _confirm_close(side, c5, price):
            return c5.close_time, float(c5.close)
    if tol_tag and _confirm_close(side, bar, price):
        return bar.close_time, float(bar.close)
    return None


def _reversal_exit(
    side: str, entry: float, bar: Candle, box_rng: float
) -> Tuple[float, float, float]:
    """Stop beyond the rejection wick, at least 0.15 of the box away.

    The fake box passed to the exit engine keeps the target at 1x today's range.
    """
    room = 0.15 * max(0.0, box_rng)
    span = max(box_rng, 1e-9)
    if side == "DOWN":
        stop = max(float(bar.high), float(entry) + room)
        if stop <= entry:
            stop = entry + max(room, span * 0.15)
        return stop, stop, stop - span
    stop = min(float(bar.low), float(entry) - room)
    if stop >= entry:
        stop = entry - max(room, span * 0.15)
    return stop, stop + span, stop


def _close5m_fill(
    m5: Sequence[Candle],
    five_opens: Sequence[datetime],
    bar: Candle,
    side: str,
    level: Optional[float],
    pending: Optional[float],
    box_high: float,
    box_low: float,
) -> Any:
    """Walk the 5m bars inside this 15m bar.

    Returns 'cancel', a float (the tagged level, still waiting), or
    (entry_ts, entry_px, level) when a 5m close confirms.
    """
    a = bisect_left(five_opens, to_utc(bar.open_time))
    b = bisect_left(five_opens, to_utc(bar.close_time))
    tagged = pending
    for c5 in m5[a:b]:
        if _through_opposite(side, c5.close, box_high, box_low):
            return "cancel"
        if tagged is None and level is not None and _wick_tag(side, c5, level):
            tagged = float(level)
        if tagged is not None and _confirm_close(side, c5, tagged):
            return (c5.close_time, float(c5.close), float(tagged))
    if tagged is None:
        return None
    return float(tagged)


def _level_at(
    params: AsiaPullbackParams,
    side: str,
    extreme: float,
    edge: float,
    box_high: float,
    box_low: float,
    ma: Optional[float],
) -> Optional[float]:
    if params.level_ref == "leg_fib":
        return leg_fib_px(extreme, edge, params.fib_level)
    if params.level_ref == "box_fib":
        return trade_fib_px(box_high, box_low, side, params.fib_level)
    return None if ma is None else float(ma)


def _first_break(
    signal: Sequence[Candle], high: float, low: float, frac: float
) -> Tuple[Optional[str], Optional[int]]:
    dist = max(0.0, float(frac)) * (high - low)
    for i, bar in enumerate(signal):
        if bar.close > high + 1e-12 and bar.close + 1e-12 >= high + dist:
            return "UP", i
        if bar.close < low - 1e-12 and bar.close - 1e-12 <= low - dist:
            return "DOWN", i
    return None, None


def _extended(side: str, bar: Candle, extreme: float) -> bool:
    if side == "UP":
        return bar.high > extreme + 1e-9
    return bar.low < extreme - 1e-9


def _through_opposite(side: str, close: float, high: float, low: float) -> bool:
    if side == "UP":
        return close < low - 1e-12
    return close > high + 1e-12


def _wick_tag(side: str, bar: Candle, level: float) -> bool:
    if side == "UP":
        return bar.low <= level + 1e-9
    return bar.high >= level - 1e-9


def _confirm_close(side: str, bar: Candle, level: float) -> bool:
    if side == "UP":
        return bar.close > bar.open + 1e-12 and bar.close > level + 1e-12
    return bar.close < bar.open - 1e-12 and bar.close < level - 1e-12


def _sim_start_after_close(feed: Any, close_time: datetime, tick_feed: bool) -> int:
    i = int(feed.find_index(close_time))
    if not tick_feed:
        return i
    if i <= 0:
        return 0
    return i - 1


def _ma_values(closes: Sequence[float], params: AsiaPullbackParams) -> List[Optional[float]]:
    kind = params.ma_type
    if kind == "ema":
        period = max(1, int(params.ema_period))
        out: List[Optional[float]] = []
        for i in range(len(closes)):
            out.append(_ema(closes[max(0, i + 1 - period * 2) : i + 1], period))
        return out

    class _Spec:
        pass

    spec = _Spec()
    spec.kama_er = int(params.ema_period)
    spec.kama_fast = int(params.kama_fast)
    spec.kama_slow = int(params.kama_slow)
    spec.hma_period = int(params.ema_period)
    spec.zlema_period = int(params.ema_period)
    return list(ma_series_values(closes, kind, spec))


def _ma_asof(
    close_times: Sequence[datetime],
    values: Sequence[Optional[float]],
    t: datetime,
) -> Optional[float]:
    if not close_times:
        return None
    i = bisect_right(close_times, to_utc(t)) - 1
    while i >= 0 and values[i] is None:
        i -= 1
    if i < 0:
        return None
    return values[i]


def _exit_params(params: AsiaPullbackParams) -> OvernightParams:
    op = OvernightParams()
    op.timezone = params.timezone
    op.sl_mode = params.sl_mode
    op.sl_fixed_pts = float(params.sl_fixed_pts)
    op.sl_range_mult = float(params.sl_range_mult)
    op.sl_cap_pts = float(params.sl_cap_pts)
    op.tp_mode = params.tp_mode
    op.tp_fixed_pts = float(params.tp_fixed_pts)
    op.tp_range_mult = float(params.tp_range_mult)
    op.tp_sl_mult = float(params.tp_sl_mult)
    op.tp_r_mult = float(params.tp_sl_mult)
    op.trail_arm_mode = "off"
    op.trail_arm_pts = 0.0
    op.trail_pts = 0.0
    op.be_arm_pts = 0.0
    op.shock_trail = False
    op.entry_shock = False
    op.max_hold_hours = 30.0
    op.flatten_hour = int(params.flatten_hour)
    return op


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
        "avg_loss_pts": round(-gl / losses, 1) if losses else None,
        "profit_factor": round(gp / gl, 2) if gl > 1e-9 else None,
        "sum_pts": round(sum(float(r["pts"]) for r in rows), 1),
    }


def _by_month(
    rows: Sequence[Dict[str, Any]], skips: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    by_tr: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_sk: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_tr[str(r.get("local_date") or "")[:7]].append(r)
    for s in skips:
        by_sk[str(s.get("local_date") or "")[:7]].append(s)
    out: List[Dict[str, Any]] = []
    for ym in sorted(set(by_tr) | set(by_sk)):
        row = _stats(by_tr.get(ym) or [])
        row["month"] = ym
        row["skipped"] = len(by_sk.get(ym) or [])
        row["skip_reasons"] = _skip_counts(by_sk.get(ym) or [])
        out.append(row)
    return out


def _skip_counts(skips: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for s in skips:
        key = str(s.get("reason") or "?")
        out[key] = out.get(key, 0) + 1
    return out


def _skip(
    day: date,
    reason: str,
    *,
    side: Optional[str] = None,
    high: Optional[float] = None,
    low: Optional[float] = None,
    ps: float = 0.0,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    rng = None
    if high is not None and low is not None and ps:
        rng = round((high - low) / ps, 1)
    return {
        "local_date": day.isoformat(),
        "weekday": _WEEKDAYS[day.weekday()],
        "reason": reason,
        "side": side,
        "box_high": None if high is None else round(high, 5),
        "box_low": None if low is None else round(low, 5),
        "box_pts": rng,
        "detail": detail,
    }


def _empty(
    params: AsiaPullbackParams, *, symbol: str, ticks: int, data_source: str
) -> Dict[str, Any]:
    return summarize_asia_pullback(
        [], [], params, symbol=symbol, ticks=ticks, data_source=data_source
    )


def _minutes(loc: datetime) -> int:
    return loc.hour * 60 + loc.minute


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _flt(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
