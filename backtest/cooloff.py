"""
Trend Cool-Off backtest (15m structure, tick fills).

After a directional run of ≥ min_run 15m candles (UP or DOWN, from price):

  Reverse — pullback of ≥ reverse_frac of the run within reverse_min..reverse_max
            pause bars (default 2–3). Enter opposite the run on the tick that
            tags the level (or at the open of bar 2 if bar 1 already tagged it).

  Join    — pullback stayed < reverse_frac over join_min..join_max pause bars
            (default 2–4) and the forming candle reclaims the run's higher high
            (UP) or lower low (DOWN). Enter with the run on that tick.

`invert=True` flips the fill (join short after an UP reclaim, etc.) so you can
test the opposite side of the same setups.

Pause bar 1 is tracking only: a reclaim of HH/LL there is treated as the run
continuing, not a join. One trade at a time. Mid fill.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from backtest.candles import Candle, CandleBuilder, is_market_open, is_session_open_skip, to_utc
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.spike_fade import weekend_reopen_blackout


@dataclass
class CoolOffParams:
    invert: bool = False  # True = fill the opposite side of the setup
    min_run: int = 5
    max_tolerance: int = 2
    min_run_range_pts: float = 0.0  # 0 = no lower bound; measured high-to-low
    max_run_range_pts: float = 0.0  # 0 = no upper bound; measured high-to-low
    reverse_frac: float = 0.30
    reverse_min_bars: int = 2
    reverse_max_bars: int = 3
    join_min_bars: int = 2
    join_max_bars: int = 4
    tp_pts: float = 500.0
    sl_pts: float = 500.0
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0
    max_hold_hours: float = 4.0
    cooldown_sec: float = 0.0
    weekend_blackout_min: float = 10.0
    skip_ignored: bool = True


@dataclass
class CoolOffTrade:
    entry_ts: str
    side: str  # UP long | DOWN short
    kind: str  # join | reverse
    run_dir: str
    run_length: int
    run_range_pts: float
    retrace: float
    pause_bars: int
    run_high: float
    run_low: float
    reverse_px: float
    join_px: float
    entry: float
    tp: Optional[float]
    sl: float
    tp_pts: float
    sl_pts: float
    inverted: bool = False
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None
    pts: float = 0.0
    max_fav_pts: float = 0.0
    max_adv_pts: float = 0.0
    max_fav_price: Optional[float] = None
    max_adv_price: Optional[float] = None
    hold_sec: Optional[float] = None


@dataclass
class _Watch:
    direction: str
    run_length: int
    tolerance_count: int
    run_first_open: float
    run_last_close: float
    run_high: float
    run_low: float
    run_range: float
    reverse_px: float
    join_px: float
    pause_start: datetime
    max_retrace: float = 0.0
    pause_extreme: float = 0.0


def _flip(side: str) -> str:
    return "DOWN" if side == "UP" else "UP"


def _is_bull_strong(c: Candle) -> bool:
    return c.close > c.open


def _is_bear_strong(c: Candle) -> bool:
    return c.close < c.open


def _is_bull_tolerance(c: Candle, prev: Optional[Candle]) -> bool:
    if prev is None:
        return False
    return c.close <= c.open and c.close > prev.open


def _is_bear_tolerance(c: Candle, prev: Optional[Candle]) -> bool:
    if prev is None:
        return False
    return c.close >= c.open and c.close < prev.open


def extract_run(
    candles: Sequence[Candle],
    *,
    bull: bool,
    min_run: int,
    max_tolerance: int,
) -> Optional[Tuple[List[Candle], int]]:
    """Contiguous directional suffix of `candles` (oldest→newest)."""
    if candles is None or len(candles) < min_run:
        return None
    run_rev: List[Candle] = []
    tolerance = 0
    for i in range(len(candles) - 1, -1, -1):
        c = candles[i]
        prev = candles[i - 1] if i > 0 else None
        if bull:
            strong = _is_bull_strong(c)
            tol = _is_bull_tolerance(c, prev)
        else:
            strong = _is_bear_strong(c)
            tol = _is_bear_tolerance(c, prev)
        if strong:
            run_rev.append(c)
            continue
        if tol and tolerance < max_tolerance:
            run_rev.append(c)
            tolerance += 1
            continue
        break
    run = list(reversed(run_rev))
    if len(run) < min_run:
        return None
    if bull and not (run[-1].close > run[0].open):
        return None
    if not bull and not (run[-1].close < run[0].open):
        return None
    return run, tolerance


def run_levels(
    run: Sequence[Candle],
    *,
    bull: bool,
    reverse_frac: float,
) -> Optional[Dict[str, float]]:
    if not run:
        return None
    run_high = max(c.high for c in run)
    run_low = min(c.low for c in run)
    first = float(run[0].open)
    if bull:
        rng = run_high - first
        if rng <= 1e-12:
            return None
        rev = run_high - float(reverse_frac) * rng
        join = run_high
    else:
        rng = first - run_low
        if rng <= 1e-12:
            return None
        rev = run_low + float(reverse_frac) * rng
        join = run_low
    return {
        "run_high": run_high,
        "run_low": run_low,
        "run_range": rng,
        "reverse_px": rev,
        "join_px": join,
        "first_open": first,
        "last_close": float(run[-1].close),
    }


def retrace_frac(
    *,
    bull: bool,
    run_high: float,
    run_low: float,
    run_range: float,
    pause_extreme: float,
) -> float:
    if run_range <= 1e-12:
        return 0.0
    if bull:
        return max(0.0, (run_high - pause_extreme) / run_range)
    return max(0.0, (pause_extreme - run_low) / run_range)


def _make_watch(
    run: Sequence[Candle],
    tol: int,
    pause_start: datetime,
    params: CoolOffParams,
    bull: bool,
    ps: float,
) -> Optional[_Watch]:
    lv = run_levels(run, bull=bull, reverse_frac=float(params.reverse_frac))
    if lv is None:
        return None
    # This deliberately uses the full candle span, rather than the directional
    # open-to-extreme move used for the retracement calculation below.
    full_range_pts = (lv["run_high"] - lv["run_low"]) / ps
    min_range_pts = max(0.0, float(params.min_run_range_pts or 0.0))
    max_range_pts = max(0.0, float(params.max_run_range_pts or 0.0))
    if full_range_pts + 1e-9 < min_range_pts:
        return None
    if max_range_pts > 1e-12 and full_range_pts - 1e-9 > max_range_pts:
        return None
    extreme0 = lv["run_high"] if bull else lv["run_low"]
    return _Watch(
        direction="UP" if bull else "DOWN",
        run_length=len(run),
        tolerance_count=tol,
        run_first_open=lv["first_open"],
        run_last_close=lv["last_close"],
        run_high=lv["run_high"],
        run_low=lv["run_low"],
        run_range=lv["run_range"],
        reverse_px=lv["reverse_px"],
        join_px=lv["join_px"],
        pause_start=pause_start,
        max_retrace=0.0,
        pause_extreme=extreme0,
    )


def _touch_watch(w: _Watch, low: float, high: float) -> None:
    bull = w.direction == "UP"
    if bull:
        w.pause_extreme = min(w.pause_extreme, low)
    else:
        w.pause_extreme = max(w.pause_extreme, high)
    w.max_retrace = max(
        w.max_retrace,
        retrace_frac(
            bull=bull,
            run_high=w.run_high,
            run_low=w.run_low,
            run_range=w.run_range,
            pause_extreme=w.pause_extreme,
        ),
    )


def _pause_index(
    w: _Watch,
    completed: Sequence[Candle],
    forming: Optional[Candle],
) -> int:
    n = 0
    start = w.pause_start
    for c in completed:
        if c.open_time >= start:
            n += 1
    if forming is not None and forming.open_time >= start:
        n += 1
    return n


def _best_run(
    candles: Sequence[Candle],
    min_run: int,
    max_tol: int,
) -> Optional[Tuple[List[Candle], int, bool]]:
    up = extract_run(candles, bull=True, min_run=min_run, max_tolerance=max_tol)
    dn = extract_run(candles, bull=False, min_run=min_run, max_tolerance=max_tol)
    if up and dn:
        if len(up[0]) >= len(dn[0]):
            return up[0], up[1], True
        return dn[0], dn[1], False
    if up:
        return up[0], up[1], True
    if dn:
        return dn[0], dn[1], False
    return None


def _watch_from_completed_dir(
    completed: Sequence[Candle],
    params: CoolOffParams,
    bull: bool,
    ps: float,
) -> Optional[_Watch]:
    max_pause = max(int(params.join_max_bars), int(params.reverse_max_bars))
    min_run = int(params.min_run)
    max_tol = int(params.max_tolerance)
    for n in range(1, max_pause + 1):
        if len(completed) < min_run + n:
            continue
        extracted = extract_run(
            completed[:-n],
            bull=bull,
            min_run=min_run,
            max_tolerance=max_tol,
        )
        if extracted is None:
            continue
        run, tol = extracted
        w = _make_watch(run, tol, completed[-n].open_time, params, bull, ps)
        if w is None:
            continue
        for p in completed[-n:]:
            _touch_watch(w, p.low, p.high)
        return w
    return None


def _watch_from_completed(
    completed: Sequence[Candle],
    params: CoolOffParams,
    ps: float,
) -> Optional[_Watch]:
    up = _watch_from_completed_dir(completed, params, True, ps)
    dn = _watch_from_completed_dir(completed, params, False, ps)
    if up and dn:
        return up if up.run_length >= dn.run_length else dn
    return up or dn


def _fav_pts(side: str, entry: float, px: float, ps: float) -> float:
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _adv_pts(side: str, entry: float, px: float, ps: float) -> float:
    """Distance in points moved against the position."""
    if side == "UP":
        return (entry - px) / ps
    return (px - entry) / ps


def _hit_level(side: str, px: float, level: float, is_sl: bool) -> bool:
    if is_sl:
        if side == "UP":
            return px <= level + 1e-12
        return px >= level - 1e-12
    if side == "UP":
        return px >= level - 1e-12
    return px <= level + 1e-12


def _reclaimed(w: _Watch, px: float) -> bool:
    if w.direction == "UP":
        return px >= w.join_px - 1e-12
    return px <= w.join_px + 1e-12


def _now_reversed(w: _Watch, px: float) -> bool:
    """True while live price is still on the reverse side of the 30% level."""
    if w.direction == "UP":
        return px <= w.reverse_px + 1e-12
    return px >= w.reverse_px - 1e-12


def _current_retrace(w: _Watch) -> float:
    return retrace_frac(
        bull=w.direction == "UP",
        run_high=w.run_high,
        run_low=w.run_low,
        run_range=w.run_range,
        pause_extreme=w.pause_extreme,
    )


def run_cooloff(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[CoolOffParams] = None,
    progress: Optional[Callable[..., None]] = None,
    entry_from: Optional[datetime] = None,
    entry_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    params = params or CoolOffParams()
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return summarize_cooloff([], params, symbol=sym, ticks=len(ticks or []))

    invert = bool(params.invert)
    min_run = max(2, int(params.min_run))
    max_tol = max(0, int(params.max_tolerance))
    rev_frac = float(params.reverse_frac)
    rev_lo = max(1, int(params.reverse_min_bars))
    rev_hi = max(rev_lo, int(params.reverse_max_bars))
    join_lo = max(1, int(params.join_min_bars))
    join_hi = max(join_lo, int(params.join_max_bars))
    # A zero TP is useful when the trailing stop is intended to manage the
    # entire exit.  Previously it was silently coerced to one point.
    tp_off = max(0.0, float(params.tp_pts))
    sl_off = max(1.0, float(params.sl_pts))
    trail_pts = max(0.0, float(params.trail_pts or 0.0))
    arm_pts = max(0.0, float(params.trail_arm_pts or 0.0))
    if trail_pts > 1e-12 and arm_pts <= 1e-12:
        arm_pts = trail_pts
    hold = timedelta(hours=float(params.max_hold_hours))
    cd = float(params.cooldown_sec or 0.0)
    blackout_min = float(params.weekend_blackout_min or 0.0)

    builder = CandleBuilder(
        timeframe_minutes=15,
        max_completed=120,
        skip_ignored=bool(params.skip_ignored),
    )

    trades: List[CoolOffTrade] = []
    open_t: Optional[CoolOffTrade] = None
    watch: Optional[_Watch] = None
    active_run: Optional[Tuple[List[Candle], int, bool]] = None
    consumed_pause: Optional[datetime] = None
    best_fav = 0.0
    best_adv = 0.0
    best_fav_px: Optional[float] = None
    best_adv_px: Optional[float] = None
    trail_armed = False
    trail_level: Optional[float] = None
    cooldown_until: Optional[datetime] = None
    n = len(ticks)
    last_yield = time.monotonic()

    def close_trade(tr: CoolOffTrade, ts: datetime, px: float, reason: str) -> None:
        nonlocal open_t, best_fav, best_adv, best_fav_px, best_adv_px, trail_armed, trail_level, cooldown_until
        pts = _fav_pts(tr.side, tr.entry, px, ps)
        tr.exit_ts = ts.isoformat()
        tr.exit = round(px, 5)
        tr.exit_reason = reason
        tr.pts = round(pts, 1)
        tr.max_fav_pts = round(best_fav, 1)
        tr.max_adv_pts = round(best_adv, 1)
        tr.max_fav_price = round(best_fav_px if best_fav_px is not None else tr.entry, 5)
        tr.max_adv_price = round(best_adv_px if best_adv_px is not None else tr.entry, 5)
        try:
            t0 = datetime.fromisoformat(tr.entry_ts)
            if t0.tzinfo is None:
                t0 = t0.replace(tzinfo=timezone.utc)
            tr.hold_sec = round((ts - t0).total_seconds(), 2)
        except Exception:
            tr.hold_sec = None
        trades.append(tr)
        open_t = None
        best_fav = 0.0
        best_adv = 0.0
        best_fav_px = None
        best_adv_px = None
        trail_armed = False
        trail_level = None
        if cd > 1e-12:
            cooldown_until = ts + timedelta(seconds=cd)

    def open_trade(
        ts: datetime,
        px: float,
        kind: str,
        w: _Watch,
        pause_i: int,
        retrace: float,
    ) -> None:
        nonlocal open_t, best_fav, best_adv, best_fav_px, best_adv_px, trail_armed, trail_level, watch, consumed_pause
        natural = w.direction if kind == "join" else _flip(w.direction)
        side = _flip(natural) if invert else natural
        if side == "UP":
            tp = px + tp_off * ps if tp_off > 1e-12 else None
            sl = px - sl_off * ps
        else:
            tp = px - tp_off * ps if tp_off > 1e-12 else None
            sl = px + sl_off * ps
        open_t = CoolOffTrade(
            entry_ts=ts.isoformat(),
            side=side,
            kind=kind,
            inverted=invert,
            run_dir=w.direction,
            run_length=w.run_length,
            run_range_pts=round(w.run_range / ps, 1),
            retrace=round(retrace, 4),
            pause_bars=pause_i,
            run_high=round(w.run_high, 5),
            run_low=round(w.run_low, 5),
            reverse_px=round(w.reverse_px, 5),
            join_px=round(w.join_px, 5),
            entry=round(px, 5),
            tp=round(tp, 5) if tp is not None else None,
            sl=round(sl, 5),
            tp_pts=round(tp_off, 1),
            sl_pts=round(sl_off, 1),
        )
        best_fav = 0.0
        best_adv = 0.0
        best_fav_px = px
        best_adv_px = px
        trail_armed = False
        trail_level = None
        consumed_pause = w.pause_start
        watch = None

    for i, t in enumerate(ticks):
        ts = to_utc(t.ts)
        px = t.mid

        if open_t is not None:
            fav = _fav_pts(open_t.side, open_t.entry, px, ps)
            if fav > best_fav:
                best_fav = fav
                best_fav_px = px
            adv = _adv_pts(open_t.side, open_t.entry, px, ps)
            if adv > best_adv:
                best_adv = adv
                best_adv_px = px
            entry_dt = datetime.fromisoformat(open_t.entry_ts)
            if entry_dt.tzinfo is None:
                entry_dt = entry_dt.replace(tzinfo=timezone.utc)
            if ts - entry_dt >= hold:
                close_trade(open_t, ts, px, "timeout")
            else:
                if trail_pts > 1e-12 and arm_pts > 1e-12:
                    if not trail_armed and fav >= arm_pts:
                        trail_armed = True
                        if open_t.side == "UP":
                            trail_level = px - trail_pts * ps
                        else:
                            trail_level = px + trail_pts * ps
                    if trail_armed and trail_level is not None:
                        if open_t.side == "UP":
                            new_tr = px - trail_pts * ps
                            if new_tr > trail_level:
                                trail_level = new_tr
                            if px <= trail_level + 1e-12:
                                close_trade(open_t, ts, trail_level, "trail")
                        else:
                            new_tr = px + trail_pts * ps
                            if new_tr < trail_level:
                                trail_level = new_tr
                            if px >= trail_level - 1e-12:
                                close_trade(open_t, ts, trail_level, "trail")
                if open_t is not None and _hit_level(open_t.side, px, open_t.sl, True):
                    close_trade(open_t, ts, open_t.sl, "sl")
                elif open_t is not None and open_t.tp is not None and _hit_level(open_t.side, px, open_t.tp, False):
                    close_trade(open_t, ts, open_t.tp, "tp")

        closed = builder.add_price(px, ts)
        completed = builder.completed_candles
        forming = builder.current_candle

        if closed is not None:
            extracted = _best_run(completed, min_run, max_tol)
            if watch is not None:
                watch_bull = watch.direction == "UP"
                if _pause_index(watch, completed, forming) > join_hi:
                    consumed_pause = watch.pause_start
                    watch = None
                elif extracted is not None:
                    run_now, _tol, run_bull = extracted
                    lv = run_levels(run_now, bull=run_bull, reverse_frac=rev_frac)
                    # New HH/LL on the close = the run continued. A pause bar
                    # that is merely still "in the run" by color is not enough
                    # to cancel the pullback window.
                    continued = (
                        lv is not None
                        and run_bull == watch_bull
                        and (
                            (watch_bull and lv["run_high"] > watch.run_high + 1e-12)
                            or ((not watch_bull) and lv["run_low"] < watch.run_low - 1e-12)
                        )
                    )
                    if continued:
                        active_run = extracted
                        watch = None
                else:
                    active_run = None
            if watch is None:
                if extracted is not None:
                    active_run = extracted
                else:
                    active_run = None
                    nxt = _watch_from_completed(completed, params, ps)
                    if nxt is not None and nxt.pause_start != consumed_pause:
                        watch = nxt

        if open_t is not None:
            pass
        elif cooldown_until is not None and ts < cooldown_until:
            pass
        elif entry_from is not None and ts < entry_from:
            pass
        elif entry_to is not None and ts >= entry_to:
            pass
        elif not is_market_open(ts):
            watch = None
            active_run = None
        elif is_session_open_skip(ts):
            pass
        elif blackout_min > 1e-12 and weekend_reopen_blackout(ts, blackout_min):
            pass
        else:
            if watch is None and active_run is not None and forming is not None:
                if forming.open_time != consumed_pause:
                    run, tol, run_bull = active_run
                    probe = _make_watch(run, tol, forming.open_time, params, run_bull, ps)
                    if probe is not None:
                        _touch_watch(probe, forming.low, forming.high)
                        _touch_watch(probe, px, px)
                        if probe.max_retrace > 1e-9:
                            watch = probe

            if watch is not None and forming is not None:
                _touch_watch(watch, forming.low, forming.high)
                _touch_watch(watch, px, px)
                pause_i = _pause_index(watch, completed, forming)
                if pause_i > join_hi:
                    consumed_pause = watch.pause_start
                    watch = None
                elif pause_i == 1 and _reclaimed(watch, px):
                    # First pause bar tagging HH/LL = run continuation, not a join.
                    watch = None
                else:
                    cur = _current_retrace(watch)
                    if rev_lo <= pause_i <= rev_hi and _now_reversed(watch, px):
                        open_trade(ts, px, "reverse", watch, pause_i, cur)
                    elif (
                        join_lo <= pause_i <= join_hi
                        and watch.max_retrace + 1e-12 < rev_frac
                        and watch.max_retrace > 1e-9
                        and _reclaimed(watch, px)
                    ):
                        open_trade(ts, px, "join", watch, pause_i, watch.max_retrace)

        now = time.monotonic()
        if now - last_yield >= 0.25 or i == n - 1:
            last_yield = now
            time.sleep(0.002)
            if progress:
                progress(
                    ticks_done=i + 1,
                    ticks_total=n,
                    trades=len(trades) + (1 if open_t else 0),
                    pct=round(70.0 + 28.0 * ((i + 1) / n), 1),
                )

    if open_t is not None:
        last = ticks[-1]
        close_trade(open_t, to_utc(last.ts), last.mid, "timeout")

    return summarize_cooloff(trades, params, symbol=sym, ticks=n)


def summarize_cooloff(
    trades: Sequence[CoolOffTrade],
    params: CoolOffParams,
    *,
    symbol: str,
    ticks: int,
    partial: bool = False,
) -> Dict[str, Any]:
    n = len(trades)
    wins = sum(1 for t in trades if t.pts > 1e-9)
    losses = sum(1 for t in trades if t.pts < -1e-9)
    by: Dict[str, int] = {}
    for t in trades:
        r = t.exit_reason or "?"
        by[r] = by.get(r, 0) + 1
    join_n = sum(1 for t in trades if t.kind == "join")
    reverse_n = sum(1 for t in trades if t.kind == "reverse")
    join_w = sum(1 for t in trades if t.kind == "join" and t.pts > 1e-9)
    reverse_w = sum(1 for t in trades if t.kind == "reverse" and t.pts > 1e-9)

    def pct(a: int, b: int) -> Optional[float]:
        if b <= 0:
            return None
        return round(100.0 * a / b, 1)

    gp = sum(t.pts for t in trades if t.pts > 0)
    gl = -sum(t.pts for t in trades if t.pts < 0)
    return {
        "kind": "cooloff",
        "symbol": symbol,
        "params": asdict(params),
        "ticks": ticks,
        "partial": partial,
        "trades": n,
        "wins": wins,
        "losses": losses,
        "scratches": n - wins - losses,
        "win_pct": pct(wins, n),
        "join_n": join_n,
        "reverse_n": reverse_n,
        "join_win_pct": pct(join_w, join_n),
        "reverse_win_pct": pct(reverse_w, reverse_n),
        "tp_n": by.get("tp", 0),
        "tp_pct": pct(by.get("tp", 0), n),
        "sl_n": by.get("sl", 0),
        "sl_pct": pct(by.get("sl", 0), n),
        "trail_n": by.get("trail", 0),
        "trail_pct": pct(by.get("trail", 0), n),
        "timeout_n": by.get("timeout", 0),
        "timeout_pct": pct(by.get("timeout", 0), n),
        "exits": by,
        "avg_pts": round(sum(t.pts for t in trades) / n, 1) if n else 0.0,
        "sum_pts": round(sum(t.pts for t in trades), 1),
        "profit_factor": round(gp / gl, 2) if gl > 1e-9 else None,
        "rows": [asdict(t) for t in trades],
    }
