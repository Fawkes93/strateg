"""Asia box Fibonacci retracement engine (pure — no web, no jobs).

Not Asia liquidity and not Overnight break. Operator notes are the README
section "Asia box tab". Hours are Europe/Chisinau.

01:00–06:00 builds the box. Fib 0 is the later extreme. Nothing fills before
03:30, but the box and the arm flags still update. Shallow waits until 05:30,
EMA retest until 07:00, entries stop at 10:00, flatten is 13:30.

Continuation stop starts at Fib .786 and trails `continuation_trail_steps`
(default 2) behind a new high or low, only tighter. The ladder toward the
stop is 0, .236, .382, .5, .618, .786, 1, 1.618. Fib 0 counts as a step, so
a print through Fib 0 pulls the stop to .236.

If the signal 5m is wider than `impulse_freeze_frac` of the box (default 40%),
that entry is skipped and every setup waits `impulse_freeze_minutes` (default
90) after the candle close. The box keeps extending. This is the 2026-03-16
02:00 and 2026-04-06 05:15 reverse longs.

EMA retest auto-stop uses the same step count (`ema_retest_sl_steps`, default
2). The fixed 0.382 SL applies only when auto levels are off.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import Candle, to_utc
from backtest.config import point_size
from backtest.dukascopy import reaktor_symbol


FIB_LEVELS: Tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.5, 1.618)
# Walked toward Fib 1 for SL; negative extensions walked for TP when through Fib 0.
_FIB_SL_STEPS: Tuple[float, ...] = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.618)
_FIB_TP_EXT: Tuple[float, ...] = (-0.236, -0.382, -0.5, -0.618, -0.786, -1.0, -1.618)


@dataclass
class AsiaBoxParams:
    timezone: str = "Europe/Chisinau"
    box_start_hour: int = 1
    box_end_hour: int = 6
    shallow_hour: int = 5
    shallow_minute: int = 30
    ema_retest_hour: int = 7
    entry_cutoff_hour: int = 10
    flatten_hour: int = 13
    flatten_minute: int = 30
    min_range_pts: float = 3000.0
    min_range_mode: str = "fixed"  # fixed | pct_price
    min_range_bps: float = 0.014  # fraction of the box midpoint; 0.014 = 1.4%
    ema_period: int = 32
    shallow_ema_near_pts: float = 100.0
    continuation_sl_fib: float = 0.786
    continuation_tp_fib: float = 0.0
    reverse_confirm_sl_fib: float = 0.5
    reverse_confirm_tp_fib: float = 1.5
    reverse_ema_sl_fib: float = 0.5
    reverse_ema_tp_fib: float = 1.0
    reverse_sl_fib: float = 0.5
    reverse_tp_fib: float = 1.0
    shallow_ema_sl_fib: float = 0.5
    shallow_ema_tp_fib: float = 0.0
    shallow_confirm_sl_fib: float = 0.5
    shallow_confirm_tp_fib: float = 0.0
    shallow_sl_fib: float = 0.5
    ema_retest_sl_fib: float = 0.382
    ema_retest_tp_fib: float = 0.0
    ema_retest_auto_levels: bool = True
    ema_retest_sl_steps: int = 2
    trade_start_enabled: bool = True
    trade_start_hour: int = 3
    trade_start_minute: int = 30
    continuation_trail: bool = True
    continuation_trail_steps: int = 2
    impulse_freeze: bool = True
    impulse_freeze_frac: float = 0.40
    impulse_freeze_minutes: int = 90
    tp_double_fib0: bool = False
    bounce_236: bool = False
    bounce_236_count: int = 2
    enable_continuation: bool = True
    enable_reverse_confirm: bool = True
    enable_reverse_ema: bool = True
    enable_shallow_ema: bool = True
    enable_shallow_confirm: bool = True
    enable_ema_retest: bool = True


def fib_px(fib0: float, fib1: float, level: float) -> float:
    return fib0 + (fib1 - fib0) * float(level)


def fib_anchors(
    high: float,
    low: float,
    high_ts: datetime,
    low_ts: datetime,
) -> Tuple[str, float, float]:
    """Fib 0 = later extreme. Equal timestamps prefer the high (UP)."""
    if high_ts >= low_ts:
        return "UP", high, low
    return "DOWN", low, high


def wick_786(side: str, candle: Candle, fib0: float, fib1: float) -> bool:
    p = fib_px(fib0, fib1, 0.786)
    if side == "UP":
        return candle.low <= p + 1e-12
    return candle.high >= p - 1e-12


def close_through_786(side: str, candle: Candle, fib0: float, fib1: float) -> bool:
    p = fib_px(fib0, fib1, 0.786)
    if side == "UP":
        return candle.close < p - 1e-12
    return candle.close > p + 1e-12


def in_continuation_band(side: str, close: float, fib0: float, fib1: float) -> bool:
    p500 = fib_px(fib0, fib1, 0.5)
    p786 = fib_px(fib0, fib1, 0.786)
    lo, hi = (p786, p500) if side == "UP" else (p500, p786)
    if lo > hi:
        lo, hi = hi, lo
    return lo - 1e-12 <= close <= hi + 1e-12


def tagged_level(side: str, candle: Candle, level_px: float) -> bool:
    if side == "UP":
        return candle.low <= level_px + 1e-12
    return candle.high >= level_px - 1e-12


def closes_with(side: str, candle: Candle) -> bool:
    if side == "UP":
        return candle.close > candle.open + 1e-12
    return candle.close < candle.open - 1e-12


def opposite(side: str) -> str:
    return "DOWN" if side == "UP" else "UP"


def ema_series(values: Sequence[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    if period < 1 or len(values) < period:
        return out
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / float(period)
    e = seed
    out[period - 1] = e
    for i in range(period, len(values)):
        e = values[i] * k + e * (1.0 - k)
        out[i] = e
    return out


WITH_TREND = frozenset(
    {"continuation", "shallow_ema", "shallow_confirm", "ema_retest"}
)


@dataclass
class AsiaBoxTrade:
    local_date: str
    setup: str
    box_n: int
    side: str
    entry_ts: str
    entry: float
    sl: float
    tp: float
    fib0: float
    fib1: float
    box_high: float
    box_low: float
    range_pts: float
    box_high_ts: Optional[str] = None
    box_low_ts: Optional[str] = None
    box_start_ts: Optional[str] = None
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    pts: float = 0.0
    exit_reason: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AsiaBoxSkip:
    local_date: str
    reason: str


def _iso(ts: Optional[datetime]) -> Optional[str]:
    if ts is None:
        return None
    return to_utc(ts).isoformat()


def _local(ts: datetime, tz: ZoneInfo) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    return ts.astimezone(tz)


def _at(d: date, hour: int, minute: int, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time(int(hour), int(minute)), tzinfo=tz)


def session_window_utc(
    d: date,
    tz_name: str,
    start_hour: int,
    end_hour: int,
    start_minute: int = 0,
    end_minute: int = 0,
) -> Tuple[datetime, datetime]:
    """01:00–06:00 in tz_name, returned as UTC instants."""
    tz = ZoneInfo(tz_name)
    start = _at(d, start_hour, start_minute, tz)
    end = _at(d, end_hour, end_minute, tz)
    return to_utc(start), to_utc(end)


def _pts(side: str, entry: float, exit_px: float, ps: float) -> float:
    if ps <= 0:
        return 0.0
    if side == "UP":
        return (exit_px - entry) / ps
    return (entry - exit_px) / ps


class _Sess:
    __slots__ = ("high", "low", "high_ts", "low_ts", "start_ts")

    def __init__(self) -> None:
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.high_ts: Optional[datetime] = None
        self.low_ts: Optional[datetime] = None
        self.start_ts: Optional[datetime] = None

    def range_px(self) -> float:
        if self.high is None or self.low is None:
            return 0.0
        return self.high - self.low

    def update(self, c: Candle, ts: datetime) -> bool:
        """Return True if a new extreme was printed (fib must redraw)."""
        new_ext = False
        if self.high is None or c.high > self.high + 1e-12:
            self.high = c.high
            self.high_ts = ts
            new_ext = True
        if self.low is None or c.low < self.low - 1e-12:
            self.low = c.low
            self.low_ts = ts
            new_ext = True
        if self.start_ts is None:
            self.start_ts = ts
        return new_ext

    def ready(self, ps: float, min_pts: float) -> bool:
        if self.high is None or self.low is None or self.high_ts is None or self.low_ts is None:
            return False
        return self.range_px() / ps >= min_pts - 1e-9

    def anchors(self) -> Tuple[str, float, float]:
        assert self.high is not None and self.low is not None
        assert self.high_ts is not None and self.low_ts is not None
        return fib_anchors(self.high, self.low, self.high_ts, self.low_ts)

    def snapshot(self, ps: float, *, side: Optional[str] = None) -> Dict[str, Any]:
        if side is None:
            side, fib0, fib1 = self.anchors()
        elif side == "UP":
            fib0, fib1 = self.high, self.low
        else:
            fib0, fib1 = self.low, self.high
        return {
            "side": side,
            "fib0": fib0,
            "fib1": fib1,
            "box_high": self.high,
            "box_low": self.low,
            "box_high_ts": self.high_ts,
            "box_low_ts": self.low_ts,
            "box_start_ts": self.start_ts,
            "range_pts": self.range_px() / ps if ps else 0.0,
        }


def min_range_threshold_pts(sess: _Sess, params: AsiaBoxParams, ps: float) -> float:
    """Point floor for the Asia box.

    fixed: min_range_pts, same every day.
    pct_price: min_range_bps × midpoint / point size. 0.014 at a 2500 mid
    with a 0.01 point is 3500 points. The floor moves with the price.
    """
    mode = str(params.min_range_mode or "fixed").strip().lower()
    if mode != "pct_price":
        return float(params.min_range_pts)
    if sess.high is None or sess.low is None or ps <= 0:
        return float(params.min_range_pts)
    mid = (float(sess.high) + float(sess.low)) / 2.0
    return abs(mid) * float(params.min_range_bps) / ps


@dataclass
class _Flags:
    tagged_500: bool = False
    tagged_382: bool = False
    reverse_armed: bool = False
    reverse_ema_dead: bool = False
    cont_taint: int = 0
    box1_filled: bool = False
    box2_active: bool = False
    box1_snap: Optional[Dict[str, Any]] = None
    box1_range: float = 0.0
    box_n: int = 1
    early_exit: bool = False
    trades_today: int = 0
    asia_close: Optional[float] = None
    freeze_until: Optional[datetime] = None
    freezes: List[Dict[str, Any]] = field(default_factory=list)

    def reset_depth(self) -> None:
        self.tagged_500 = False
        self.tagged_382 = False
        self.reverse_armed = False
        self.reverse_ema_dead = False
        self.cont_taint = 0


def target_in_front(side: str, entry: float, tp: float) -> bool:
    """TP must be beyond entry in the trade direction (UP: above, DOWN: below)."""
    if side == "UP":
        return tp > entry + 1e-12
    return tp < entry - 1e-12


def _fib_pos(entry: float, fib0: float, fib1: float) -> float:
    span = fib1 - fib0
    if abs(span) < 1e-12:
        return 0.0
    return (entry - fib0) / span


def _nth_step(pos: float, levels: Sequence[float], n: int, *, toward_higher: bool) -> float:
    """Nth fib strictly past pos. n=1 is the next level, n=2 is the one after that."""
    steps = max(1, int(n))
    if toward_higher:
        found = [lv for lv in levels if lv > pos + 1e-12]
    else:
        found = [lv for lv in levels if lv < pos - 1e-12]
    if len(found) >= steps:
        return found[steps - 1]
    if found:
        return found[-1]
    return levels[-1]


def _second_step(pos: float, levels: Sequence[float], *, toward_higher: bool) -> float:
    return _nth_step(pos, levels, 2, toward_higher=toward_higher)


def ema_retest_sl_tp(
    entry: float,
    fib0: float,
    fib1: float,
    sl_steps: int = 2,
) -> Tuple[float, float]:
    """SL = Nth fib toward Fib 1. TP = Fib 0 if in front, else 2nd extension through 0."""
    pos = _fib_pos(entry, fib0, fib1)
    sl_lv = _nth_step(pos, _FIB_SL_STEPS, sl_steps, toward_higher=True)
    sl = fib_px(fib0, fib1, sl_lv)
    if pos > 1e-12:
        tp = fib0
    else:
        tp_lv = _second_step(pos, _FIB_TP_EXT, toward_higher=False)
        tp = fib_px(fib0, fib1, tp_lv)
    return sl, tp


def _sl_tp(
    setup: str,
    box_side: str,
    fib0: float,
    fib1: float,
    entry: float,
    params: AsiaBoxParams,
) -> Tuple[str, float, float]:
    with_trend = setup in WITH_TREND
    trade_side = box_side if with_trend else opposite(box_side)
    if setup == "ema_retest" and params.ema_retest_auto_levels:
        sl, tp = ema_retest_sl_tp(entry, fib0, fib1, params.ema_retest_sl_steps)
    else:
        sl_lv, tp_lv = {
            "continuation": (params.continuation_sl_fib, params.continuation_tp_fib),
            "reverse_confirm": (params.reverse_confirm_sl_fib, params.reverse_confirm_tp_fib),
            "reverse_ema": (params.reverse_ema_sl_fib, params.reverse_ema_tp_fib),
            "shallow_ema": (params.shallow_ema_sl_fib, params.shallow_ema_tp_fib),
            "shallow_confirm": (params.shallow_confirm_sl_fib, params.shallow_confirm_tp_fib),
            "ema_retest": (params.ema_retest_sl_fib, params.ema_retest_tp_fib),
        }[setup]
        sl = fib_px(fib0, fib1, sl_lv)
        tp = fib_px(fib0, fib1, tp_lv)
    if params.tp_double_fib0 and with_trend:
        dist = abs(fib0 - entry)
        tp = entry + 2.0 * dist if trade_side == "UP" else entry - 2.0 * dist
    return trade_side, sl, tp


def _enabled(params: AsiaBoxParams, setup: str) -> bool:
    return bool(
        {
            "continuation": params.enable_continuation,
            "reverse_confirm": params.enable_reverse_confirm,
            "reverse_ema": params.enable_reverse_ema,
            "shallow_ema": params.enable_shallow_ema,
            "shallow_confirm": params.enable_shallow_confirm,
            "ema_retest": params.enable_ema_retest,
        }[setup]
    )


def _opposing_ema_touch(
    candle: Candle,
    *,
    trade_side: str,
    ema: Optional[float],
) -> Tuple[bool, float]:
    """Opposing 5m vs trade side tags EMA. Fill at EMA, or open if already through."""
    if ema is None:
        return False, candle.close
    if trade_side == "UP":
        if not (candle.close < candle.open - 1e-12):
            return False, candle.close
        if candle.open < ema - 1e-12:
            return False, candle.close
        if candle.low <= ema + 1e-12:
            return True, min(candle.open, ema)
        return False, candle.close
    if not (candle.close > candle.open + 1e-12):
        return False, candle.close
    if candle.open > ema + 1e-12:
        return False, candle.close
    if candle.high >= ema - 1e-12:
        return True, max(candle.open, ema)
    return False, candle.close


def _beyond_500(side: str, close: float, fib0: float, fib1: float) -> bool:
    """Price still on the Fib 1 side of .500 (needed for reverse EMA)."""
    p500 = fib_px(fib0, fib1, 0.5)
    if side == "UP":
        return close < p500 - 1e-12
    return close > p500 + 1e-12


def _in_shallow_close(side: str, close: float, fib0: float, fib1: float) -> bool:
    p500 = fib_px(fib0, fib1, 0.5)
    if side == "UP":
        return p500 + 1e-12 < close < fib0 - 1e-12
    return fib0 + 1e-12 < close < p500 - 1e-12


def _simulate_from_candles(
    candles: Sequence[Candle],
    start_index: int,
    *,
    side: str,
    entry: float,
    sl: float,
    tp: float,
    flatten: datetime,
    tz: ZoneInfo,
    ps: float,
    params: AsiaBoxParams,
    fib0: float,
    fib1: float,
    trail_steps: int = 0,
) -> Tuple[str, datetime, float, float]:
    """Walk 5m bars from start_index inclusive. Same-bar SL beats TP.

    Returns reason, exit time, exit price, and the stop in force at the exit.
    A continuation trail tightens from this bar's extreme before the stop test.
    """
    last_ts = candles[start_index - 1].close_time if start_index > 0 else candles[0].open_time
    last_px = entry
    bounce_hits = 0
    last_was_236 = False
    p236 = fib_px(fib0, fib1, 0.236)
    p618 = fib_px(fib0, fib1, 0.618)
    sl_now = sl
    best = entry
    steps = max(0, int(trail_steps or 0))

    if start_index >= len(candles):
        return "eod", last_ts, entry, sl_now

    for i in range(start_index, len(candles)):
        c = candles[i]
        loc = _local(c.open_time, tz)
        if loc >= flatten:
            return "flatten", c.open_time, c.open, sl_now

        if params.bounce_236:
            tagged = tagged_level(side, c, p236)
            if tagged and not last_was_236:
                bounce_hits += 1
            last_was_236 = tagged
            if bounce_hits >= int(params.bounce_236_count or 2):
                sl_now = p618

        if steps > 0:
            if side == "UP":
                if c.high > best + 1e-12:
                    best = c.high
            elif c.low < best - 1e-12:
                best = c.low
            trail_lv = _nth_step(
                _fib_pos(best, fib0, fib1), _FIB_SL_STEPS, steps, toward_higher=True
            )
            trail_px = fib_px(fib0, fib1, trail_lv)
            if side == "UP":
                if trail_px > sl_now + 1e-12:
                    sl_now = trail_px
            elif trail_px < sl_now - 1e-12:
                sl_now = trail_px

        hit_sl = (
            (c.low <= sl_now + 1e-12) if side == "UP" else (c.high >= sl_now - 1e-12)
        )
        hit_tp = target_in_front(side, entry, tp) and (
            (c.high >= tp - 1e-12) if side == "UP" else (c.low <= tp + 1e-12)
        )
        last_ts = c.close_time
        last_px = c.close
        if hit_sl and hit_tp:
            return "sl", c.open_time, sl_now, sl_now
        if hit_sl:
            return "sl", c.open_time, sl_now, sl_now
        if hit_tp:
            return "tp", c.open_time, tp, sl_now

    return "eod", last_ts, last_px, sl_now


def _retest_snap(sess: _Sess, asia_close: Optional[float], ps: float) -> Optional[Dict[str, Any]]:
    """EMA retest follows the last Asia leg: 06:00 close vs box midpoint, not later-extreme."""
    if asia_close is None or sess.high is None or sess.low is None:
        return None
    if not sess.ready(ps, 0.0):
        return None
    mid = (sess.high + sess.low) / 2.0
    if asia_close < mid - 1e-12:
        side = "DOWN"
    elif asia_close > mid + 1e-12:
        side = "UP"
    else:
        side, _, _ = sess.anchors()
    return sess.snapshot(ps, side=side)


def _hunt_snap(sess: _Sess, flags: _Flags, ps: float) -> Optional[Dict[str, Any]]:
    if flags.box2_active or not flags.box1_filled:
        if not sess.ready(ps, 0.0) or sess.high is None:
            return None
        try:
            return sess.snapshot(ps)
        except Exception:
            return None
    return flags.box1_snap


def _candle_too_wide(c: Candle, snap: Dict[str, Any], params: AsiaBoxParams) -> bool:
    if not params.impulse_freeze:
        return False
    box = float(snap["box_high"]) - float(snap["box_low"])
    if box <= 1e-12:
        return False
    return (c.high - c.low) > box * float(params.impulse_freeze_frac) + 1e-12


def _arm_freeze(
    flags: _Flags,
    c: Candle,
    *,
    tz: ZoneInfo,
    params: AsiaBoxParams,
    ps: float,
    setup: str,
    snap: Dict[str, Any],
) -> None:
    close_loc = _local(c.close_time, tz)
    until = close_loc + timedelta(minutes=max(0, int(params.impulse_freeze_minutes)))
    flags.freeze_until = until
    box_px = float(snap["box_high"]) - float(snap["box_low"])
    flags.freezes.append(
        {
            "local_date": close_loc.date().isoformat(),
            "until": until.isoformat(),
            "setup": setup,
            "candle_pts": (c.high - c.low) / ps if ps else 0.0,
            "box_pts": box_px / ps if ps else 0.0,
        }
    )


def _pick_setup(
    c: Candle,
    *,
    sess: _Sess,
    flags: _Flags,
    params: AsiaBoxParams,
    ps: float,
    loc: datetime,
    tz: ZoneInfo,
    ema: Optional[float],
    box_end: datetime,
    shallow_at: datetime,
    ema_at: datetime,
    trade_at: datetime,
    cutoff: datetime,
) -> Optional[Dict[str, Any]]:
    if loc >= cutoff:
        return None
    if flags.trades_today >= 2:
        return None

    if flags.box1_filled and not flags.box2_active:
        if not flags.early_exit:
            return None
        only_retest = True
    else:
        only_retest = False
    snap = None
    if only_retest:
        snap = flags.box1_snap
        if not snap:
            return None
        if flags.box1_snap and flags.box1_snap.get("side") and flags.reverse_armed:
            return None
    else:
        if not sess.ready(ps, min_range_threshold_pts(sess, params, ps)):
            return None
        snap = sess.snapshot(ps)

    box_side = snap["side"]
    fib0 = snap["fib0"]
    fib1 = snap["fib1"]

    if not only_retest:
        if close_through_786(box_side, c, fib0, fib1):
            flags.reverse_armed = True
            flags.cont_taint = 2
        p500 = fib_px(fib0, fib1, 0.5)
        p382 = fib_px(fib0, fib1, 0.382)
        if tagged_level(box_side, c, p500):
            flags.tagged_500 = True
        if tagged_level(box_side, c, p382):
            flags.tagged_382 = True
        if flags.reverse_armed and not _beyond_500(box_side, c.close, fib0, fib1):
            flags.reverse_ema_dead = True

    def consider(
        setup: str,
        entry: float,
        use_snap: Dict[str, Any],
        use_side: str,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        trade_side, sl, tp = _sl_tp(
            setup, use_side, use_snap["fib0"], use_snap["fib1"], entry, params
        )
        if not target_in_front(trade_side, entry, tp):
            return None
        frozen = flags.freeze_until is not None and loc < flags.freeze_until
        if not frozen and _candle_too_wide(c, use_snap, params):
            _arm_freeze(
                flags, c, tz=tz, params=params, ps=ps, setup=setup, snap=use_snap
            )
            return None
        if params.trade_start_enabled and loc < trade_at:
            return None
        if flags.freeze_until is not None and loc < flags.freeze_until:
            return None
        return {
            "setup": setup,
            "box_side": use_side,
            "trade_side": trade_side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "snap": use_snap,
            "extras": extras or {},
        }

    def emit(setup: str, entry: float, extras: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        return consider(setup, entry, snap, box_side, extras)

    def try_retest() -> Optional[Dict[str, Any]]:
        if ema is None or not _enabled(params, "ema_retest"):
            return None
        rsnap = _retest_snap(sess, flags.asia_close, ps)
        if not rsnap:
            return None
        hit, fill = _opposing_ema_touch(c, trade_side=rsnap["side"], ema=ema)
        if not hit:
            return None
        extra = {
            "ema": ema,
            "asia_close": flags.asia_close,
            "retest_side": rsnap["side"],
        }
        return consider("ema_retest", fill, rsnap, rsnap["side"], extra)

    # --- reverse owns the fib ---
    if flags.reverse_armed and not only_retest:
        if _enabled(params, "reverse_confirm") and closes_with(opposite(box_side), c):
            return emit("reverse_confirm", c.close)
        if (
            _enabled(params, "reverse_ema")
            and not flags.reverse_ema_dead
            and ema is not None
            and _beyond_500(box_side, c.close, fib0, fib1)
        ):
            hit, fill = _opposing_ema_touch(c, trade_side=opposite(box_side), ema=ema)
            if hit:
                return emit("reverse_ema", fill, {"ema": ema})
        return None

    if only_retest:
        if loc < ema_at:
            return None
        if flags.reverse_armed:
            return None
        sig = try_retest()
        if sig:
            sig["extras"]["box_n_source"] = 1
        return sig

    # with-trend on the live fib
    if _enabled(params, "continuation") and flags.cont_taint < 2:
        if closes_with(box_side, c) and in_continuation_band(box_side, c.close, fib0, fib1):
            if wick_786(box_side, c, fib0, fib1):
                flags.cont_taint = min(2, flags.cont_taint + 1)
            else:
                return emit("continuation", c.close, {"taint": flags.cont_taint})

    if not flags.tagged_500 and loc >= shallow_at:
        p382 = fib_px(fib0, fib1, 0.382)
        if _enabled(params, "shallow_ema") and ema is not None:
            if tagged_level(box_side, c, p382):
                near = abs(ema - p382) / ps
                if near <= params.shallow_ema_near_pts + 1e-9:
                    return emit("shallow_ema", c.close, {"ema": ema, "ema_near_pts": near})
        if _enabled(params, "shallow_confirm") and flags.tagged_382:
            if closes_with(box_side, c) and _in_shallow_close(box_side, c.close, fib0, fib1):
                return emit("shallow_confirm", c.close)

    if loc >= ema_at:
        return try_retest()
    return None


def _trade_from_signal(
    sig: Dict[str, Any],
    *,
    c: Candle,
    local_date: date,
    flags: _Flags,
    candles: Sequence[Candle],
    idx: int,
    flatten: datetime,
    tz: ZoneInfo,
    ps: float,
    params: AsiaBoxParams,
    close_fill: bool,
) -> Tuple[AsiaBoxTrade, int]:
    snap = sig["snap"]
    start = idx + 1 if close_fill else idx
    trail_steps = 0
    if sig["setup"] == "continuation" and params.continuation_trail:
        trail_steps = max(1, int(params.continuation_trail_steps or 2))
    reason, exit_ts, exit_px, sl_final = _simulate_from_candles(
        candles,
        start,
        side=sig["trade_side"],
        entry=sig["entry"],
        sl=sig["sl"],
        tp=sig["tp"],
        flatten=flatten,
        tz=tz,
        ps=ps,
        params=params,
        fib0=snap["fib0"],
        fib1=snap["fib1"],
        trail_steps=trail_steps,
    )
    entry_ts = c.close_time if close_fill else c.open_time
    extras = dict(sig.get("extras") or {})
    if trail_steps:
        extras["sl_initial"] = float(sig["sl"])
    trade = AsiaBoxTrade(
        local_date=str(local_date),
        setup=sig["setup"],
        box_n=int(flags.box_n),
        side=sig["trade_side"],
        entry_ts=_iso(entry_ts) or "",
        entry=float(sig["entry"]),
        sl=float(sl_final),
        tp=float(sig["tp"]),
        fib0=float(snap["fib0"]),
        fib1=float(snap["fib1"]),
        box_high=float(snap["box_high"]),
        box_low=float(snap["box_low"]),
        range_pts=float(snap["range_pts"]),
        box_high_ts=_iso(snap.get("box_high_ts")),
        box_low_ts=_iso(snap.get("box_low_ts")),
        box_start_ts=_iso(snap.get("box_start_ts")),
        exit_ts=_iso(exit_ts),
        exit=float(exit_px),
        pts=_pts(sig["trade_side"], sig["entry"], exit_px, ps),
        exit_reason=reason,
        extras=extras,
    )
    # skip to first bar at/after exit
    next_i = idx + 1
    exit_utc = to_utc(exit_ts)
    for j in range(idx + 1, len(candles)):
        if to_utc(candles[j].open_time) >= exit_utc:
            next_i = j
            break
        next_i = j + 1
    return trade, next_i


def _run_day(
    d: date,
    day_candles: List[Tuple[int, Candle]],
    all_candles: Sequence[Candle],
    emas: Sequence[Optional[float]],
    *,
    params: AsiaBoxParams,
    tz: ZoneInfo,
    ps: float,
) -> Tuple[List[AsiaBoxTrade], Optional[AsiaBoxSkip], List[Dict[str, Any]]]:
    box_start = _at(d, params.box_start_hour, 0, tz)
    box_end = _at(d, params.box_end_hour, 0, tz)
    shallow_at = _at(d, params.shallow_hour, params.shallow_minute, tz)
    ema_at = _at(d, params.ema_retest_hour, 0, tz)
    trade_at = _at(d, params.trade_start_hour, params.trade_start_minute, tz)
    cutoff = _at(d, params.entry_cutoff_hour, 0, tz)
    flatten = _at(d, params.flatten_hour, params.flatten_minute, tz)

    sess = _Sess()
    flags = _Flags()
    trades: List[AsiaBoxTrade] = []
    i = 0
    n = len(day_candles)

    while i < n:
        glob_i, c = day_candles[i]
        loc = _local(c.open_time, tz)
        if loc < box_start:
            i += 1
            continue

        if box_start <= loc < box_end:
            new_ext = sess.update(c, loc)
            flags.asia_close = c.close
            if new_ext and not flags.box1_filled:
                flags.reset_depth()
            if (
                flags.box1_filled
                and not flags.box2_active
                and flags.early_exit
                and flags.trades_today < 2
                and sess.ready(ps, min_range_threshold_pts(sess, params, ps))
                and sess.range_px() / ps > flags.box1_range + 1e-9
            ):
                flags.box2_active = True
                flags.box_n = 2
                flags.reset_depth()

        ema = emas[glob_i] if glob_i < len(emas) else None
        sig = _pick_setup(
            c,
            sess=sess,
            flags=flags,
            params=params,
            ps=ps,
            loc=loc,
            tz=tz,
            ema=ema,
            box_end=box_end,
            shallow_at=shallow_at,
            ema_at=ema_at,
            trade_at=trade_at,
            cutoff=cutoff,
        )
        if sig is None:
            i += 1
            continue

        close_fill = sig["setup"] in (
            "continuation",
            "reverse_confirm",
            "shallow_ema",
            "shallow_confirm",
        )
        trade, _ = _trade_from_signal(
            sig,
            c=c,
            local_date=d,
            flags=flags,
            candles=all_candles,
            idx=glob_i,
            flatten=flatten,
            tz=tz,
            ps=ps,
            params=params,
            close_fill=close_fill,
        )
        trades.append(trade)
        flags.trades_today += 1
        exit_loc = _local(datetime.fromisoformat(trade.exit_ts), tz) if trade.exit_ts else loc
        if not flags.box1_filled:
            flags.box1_filled = True
            flags.box1_snap = dict(sig["snap"])
            flags.box1_range = float(sig["snap"]["range_pts"])
            flags.early_exit = exit_loc < box_end
        # advance day index to first bar with open >= exit
        exit_utc = to_utc(datetime.fromisoformat(trade.exit_ts)) if trade.exit_ts else to_utc(c.close_time)
        i += 1
        while i < n and to_utc(day_candles[i][1].open_time) < exit_utc:
            # keep session H/L updating through the trade
            _, cc = day_candles[i]
            cloc = _local(cc.open_time, tz)
            if box_start <= cloc < box_end:
                sess.update(cc, cloc)
                flags.asia_close = cc.close
            i += 1

    if not trades:
        if sess.high is None or not sess.ready(ps, min_range_threshold_pts(sess, params, ps)):
            return trades, AsiaBoxSkip(str(d), "range_too_small"), flags.freezes
        return trades, AsiaBoxSkip(str(d), "no_setup"), flags.freezes
    return trades, None, flags.freezes


def summarize_asia_box(
    trades: Sequence[AsiaBoxTrade],
    skips: Sequence[AsiaBoxSkip],
    *,
    params: AsiaBoxParams,
    symbol: str,
    data_source: str,
    n_bars: int,
    freezes: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    rows = [asdict(t) for t in trades]
    by_setup: Dict[str, Dict[str, Any]] = {}
    sum_pts = 0.0
    wins = 0
    for t in trades:
        sum_pts += float(t.pts)
        if t.pts > 0:
            wins += 1
        b = by_setup.setdefault(t.setup, {"n": 0, "sum_pts": 0.0, "wins": 0})
        b["n"] += 1
        b["sum_pts"] += float(t.pts)
        if t.pts > 0:
            b["wins"] += 1
    skip_counts: Dict[str, int] = {}
    for s in skips:
        skip_counts[s.reason] = skip_counts.get(s.reason, 0) + 1
    n = len(trades)
    return {
        "kind": "asia_box",
        "symbol": symbol,
        "params": asdict(params),
        "data_source": data_source,
        "rows": rows,
        "skips": [asdict(s) for s in skips],
        "trades": n,
        "sum_pts": sum_pts,
        "wins": wins,
        "win_rate": (wins / n) if n else 0.0,
        "by_setup": by_setup,
        "skip_counts": skip_counts,
        "freezes": [dict(f) for f in (freezes or [])],
        "bars": n_bars,
    }


def run_asia_box_on_candles(
    candles: Sequence[Candle],
    *,
    symbol: str = "XAUUSD",
    params: Optional[AsiaBoxParams] = None,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    params = params or AsiaBoxParams()
    tz = ZoneInfo(params.timezone)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not candles:
        return summarize_asia_box([], [], params=params, symbol=sym, data_source="candles_5m", n_bars=0)

    emas = ema_series([c.close for c in candles], int(params.ema_period))
    by_day: Dict[date, List[Tuple[int, Candle]]] = {}
    for i, c in enumerate(candles):
        d = _local(c.open_time, tz).date()
        by_day.setdefault(d, []).append((i, c))

    trades: List[AsiaBoxTrade] = []
    skips: List[AsiaBoxSkip] = []
    freezes: List[Dict[str, Any]] = []
    days = sorted(by_day)
    for di, d in enumerate(days):
        if progress:
            progress(phase="scan", days_done=di, days_total=len(days), trades=len(trades))
        day_trades, skip, day_freezes = _run_day(
            d,
            by_day[d],
            candles,
            emas,
            params=params,
            tz=tz,
            ps=ps,
        )
        trades.extend(day_trades)
        freezes.extend(day_freezes)
        if skip is not None:
            skips.append(skip)
    if progress:
        progress(phase="scan", days_done=len(days), days_total=len(days), trades=len(trades))
    return summarize_asia_box(
        trades,
        skips,
        params=params,
        symbol=sym,
        data_source="candles_5m",
        n_bars=len(candles),
        freezes=freezes,
    )


def run_asia_box(
    ticks: Sequence[Any],
    *,
    symbol: str = "XAUUSD",
    params: Optional[AsiaBoxParams] = None,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    """Tick path: 5m signals, tick exits. Built in the jobs layer; here we fall back to 5m."""
    from backtest.candles import build_candles

    candles = build_candles(ticks, timeframe_minutes=5)
    out = run_asia_box_on_candles(candles, symbol=symbol, params=params, progress=progress)
    out["data_source"] = "ticks"
    return out


