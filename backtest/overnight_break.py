"""
Overnight / Asia range breakout strategy (pure — no web, no MT5).

Bucharest time Asia window → first 15m close outside with min break pts
→ optional pullback entry (EMA touch or higher/lower close resume).

Entry modes:
  off       : enter on break candle close
  required  : must get EMA touch or higher-close resume within max wait, else skip
  ema       : must get EMA touch within max wait (ignore close resume), else skip
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
    pullback_mode: str = "required"  # off | required | ema | preferred
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


def _resume_enabled(params: OvernightParams) -> bool:
    if params.pullback_mode in ("off", "ema"):
        return False
    return bool(params.use_higher_close)


def asia_window_start_utc(
    local_day: date,
    timezone_name: str = "Europe/Bucharest",
    asia_start_hour: int = 0,
    asia_end_hour: int = 7,
) -> datetime:
    """UTC instant of the Asia window open for `local_day`.

    Bucharest 00:00 is 21:00 UTC the previous evening in summer, 22:00 in winter.
    If start > end the window wraps midnight and begins the previous local evening.
    """
    tz = ZoneInfo(timezone_name)
    day = local_day - timedelta(days=1) if asia_start_hour > asia_end_hour else local_day
    local_open = datetime.combine(day, time(asia_start_hour, 0), tzinfo=tz)
    return local_open.astimezone(timezone.utc)


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
    max_fav_price: Optional[float] = None
    max_adv_price: Optional[float] = None  # worst mid against the trade (opp peak)
    # Decision factors (why this entry)
    entry_label: str = ""
    wait_i: Optional[int] = None  # 1-based wait candle; 0 = break close
    wait_n: Optional[int] = None
    ema: Optional[float] = None
    prev_close: Optional[float] = None
    signal_close: Optional[float] = None
    break_pts: Optional[float] = None
    entry_vs_ema_pts: Optional[float] = None
    close_vs_prev_pts: Optional[float] = None
    same_bar_ema: bool = False
    decision: str = ""


@dataclass
class OvernightSkip:
    local_date: str
    reason: str
    side: Optional[str] = None
    asia_high: Optional[float] = None
    asia_low: Optional[float] = None
    asia_range_pts: Optional[float] = None
    break_price: Optional[float] = None
    max_fav_pts: Optional[float] = None
    max_adv_pts: Optional[float] = None
    max_fav_price: Optional[float] = None
    max_adv_price: Optional[float] = None  # opposite-direction peak after break
    max_above_asia_pts: Optional[float] = None
    max_below_asia_pts: Optional[float] = None
    wait_i: Optional[int] = None
    wait_n: Optional[int] = None
    ema: Optional[float] = None
    closest_ema_pts: Optional[float] = None  # >0 = never touched, 0/neg = would have
    best_resume_pts: Optional[float] = None  # best close vs prev in trade direction
    break_pts: Optional[float] = None
    decision: Optional[str] = None
    detail: Optional[str] = None


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


def _round_or_none(v: Optional[float], nd: int) -> Optional[float]:
    if v is None:
        return None
    return round(float(v), nd)


def entry_label(reason: str) -> str:
    return {
        "ema_touch": "EMA touch",
        "higher_close": "Higher close resume",
        "lower_close": "Lower close resume",
        "break_close": "Break close",
        "timeout_market": "Timeout market",
        "timeout_worst": "Timeout worst",
    }.get(reason, reason or "—")


def _fmt_px(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{x:.2f}"


def _decision_line(
    *,
    reason: str,
    side: str,
    wait_i: Optional[int],
    wait_n: Optional[int],
    ema: Optional[float],
    prev_close: Optional[float],
    signal_close: Optional[float],
    entry: Optional[float],
    break_pts: Optional[float],
    entry_vs_ema_pts: Optional[float],
    close_vs_prev_pts: Optional[float],
    same_bar_ema: bool,
    pullback_mode: str,
    closest_ema_pts: Optional[float] = None,
    best_resume_pts: Optional[float] = None,
    use_higher_close: bool = True,
) -> str:
    parts: List[str] = [entry_label(reason)]
    if wait_n is not None:
        wi = wait_i if wait_i is not None else 0
        parts.append(f"wait {wi}/{wait_n}")
    if break_pts is not None:
        edge = "Asia high" if side == "UP" else "Asia low"
        parts.append(f"break +{break_pts:.0f} pts vs {edge}")
    if reason in ("higher_close", "lower_close"):
        cmp = ">" if side == "UP" else "<"
        extra = (
            f"({close_vs_prev_pts:+.0f} pts)"
            if close_vs_prev_pts is not None
            else ""
        )
        if prev_close is not None and signal_close is not None:
            parts.append(
                f"close {_fmt_px(signal_close)} {cmp} prev {_fmt_px(prev_close)} {extra}".strip()
            )
        if same_bar_ema:
            parts.append("EMA also touched this bar (close wins)")
        elif ema is not None:
            parts.append(f"EMA {_fmt_px(ema)}")
    elif reason == "ema_touch":
        rel = (
            f"({entry_vs_ema_pts:+.0f} pts vs EMA)"
            if entry_vs_ema_pts is not None
            else ""
        )
        parts.append(
            f"EMA {_fmt_px(ema)} fill {_fmt_px(entry)} {rel}".strip()
        )
        if close_vs_prev_pts is not None:
            parts.append(f"bar close vs prev {close_vs_prev_pts:+.0f} pts")
    elif reason == "break_close":
        parts.append(f"pullback {pullback_mode}")
    elif reason.startswith("timeout"):
        if closest_ema_pts is None:
            parts.append("EMA not ready")
        else:
            parts.append(f"closest to EMA {closest_ema_pts:+.0f} pts")
        if not use_higher_close:
            parts.append("close resume off")
        elif best_resume_pts is None:
            parts.append("no close to compare")
        else:
            parts.append(f"best close vs prev {best_resume_pts:+.0f} pts")
    return " · ".join(p for p in parts if p)


def _skip_decision(
    *,
    reason: str,
    wait_n: Optional[int],
    waited: Optional[int],
    ema: Optional[float],
    closest_ema_pts: Optional[float],
    best_resume_pts: Optional[float],
    use_higher_close: bool,
    break_pts: Optional[float],
    side: Optional[str],
) -> str:
    parts: List[str] = []
    if wait_n is not None:
        parts.append(f"wait {waited or 0}/{wait_n}")
    if break_pts is not None and side:
        edge = "Asia high" if side == "UP" else "Asia low"
        parts.append(f"break +{break_pts:.0f} pts vs {edge}")
    if reason in ("no_pullback", "no_pullback_timeout"):
        if ema is None and closest_ema_pts is None:
            parts.append("EMA not ready")
        elif closest_ema_pts is None:
            parts.append(f"EMA {_fmt_px(ema)} · no tick scan")
        elif closest_ema_pts > 1e-9:
            parts.append(
                f"no EMA touch (closest {closest_ema_pts:.0f} pts away, EMA {_fmt_px(ema)})"
            )
        else:
            parts.append(
                f"EMA would have touched ({closest_ema_pts:.0f} pts, EMA {_fmt_px(ema)})"
            )
        if not use_higher_close:
            parts.append("close resume off")
        elif best_resume_pts is None:
            parts.append("no close to compare")
        elif best_resume_pts <= 1e-9:
            parts.append(f"no close resume (best {best_resume_pts:+.0f} pts vs prev)")
        else:
            parts.append(f"best close vs prev {best_resume_pts:+.0f} pts")
        if wait_n is not None and (waited or 0) == 0:
            parts.append("no wait candles after break (Asia window already full)")
    return " · ".join(parts) if parts else ""


def _mk_skip(
    day: date,
    reason: str,
    *,
    side: Optional[str] = None,
    asia_high: Optional[float] = None,
    asia_low: Optional[float] = None,
    asia_range_pts: Optional[float] = None,
    break_price: Optional[float] = None,
    max_fav_pts: Optional[float] = None,
    max_adv_pts: Optional[float] = None,
    max_fav_price: Optional[float] = None,
    max_adv_price: Optional[float] = None,
    max_above_asia_pts: Optional[float] = None,
    max_below_asia_pts: Optional[float] = None,
    wait_i: Optional[int] = None,
    wait_n: Optional[int] = None,
    ema: Optional[float] = None,
    closest_ema_pts: Optional[float] = None,
    best_resume_pts: Optional[float] = None,
    break_pts: Optional[float] = None,
    decision: Optional[str] = None,
    detail: Optional[str] = None,
) -> OvernightSkip:
    return OvernightSkip(
        local_date=day.isoformat(),
        reason=reason,
        side=side,
        asia_high=_round_or_none(asia_high, 5),
        asia_low=_round_or_none(asia_low, 5),
        asia_range_pts=_round_or_none(asia_range_pts, 1),
        break_price=_round_or_none(break_price, 5),
        max_fav_pts=_round_or_none(max_fav_pts, 1),
        max_adv_pts=_round_or_none(max_adv_pts, 1),
        max_fav_price=_round_or_none(max_fav_price, 5),
        max_adv_price=_round_or_none(max_adv_price, 5),
        max_above_asia_pts=_round_or_none(max_above_asia_pts, 1),
        max_below_asia_pts=_round_or_none(max_below_asia_pts, 1),
        wait_i=wait_i,
        wait_n=wait_n,
        ema=_round_or_none(ema, 5),
        closest_ema_pts=_round_or_none(closest_ema_pts, 1),
        best_resume_pts=_round_or_none(best_resume_pts, 1),
        break_pts=_round_or_none(break_pts, 1),
        decision=decision,
        detail=detail,
    )


def _asia_extensions(
    candles: Sequence[Candle],
    asia_high: float,
    asia_low: float,
    ps: float,
) -> Tuple[Optional[float], Optional[float]]:
    """Pts beyond Asia high / below Asia low (negative = never reached that side)."""
    if not candles:
        return None, None
    hi = max(c.high for c in candles)
    lo = min(c.low for c in candles)
    return round((hi - asia_high) / ps, 1), round((asia_low - lo) / ps, 1)


def _excursion_from(
    ticks: Sequence[Tick],
    start_index: int,
    *,
    side: str,
    entry: float,
    ps: float,
    tz: ZoneInfo,
    flatten_local: datetime,
    max_hold_hours: float,
) -> Tuple[float, float, float, float]:
    """
    Walk ticks after start until flatten / max hold.
    Returns max_fav_pts, max_adv_pts, fav_peak_px, adv_peak_px.
    """
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    worst_px = entry
    if start_index < 0 or start_index >= len(ticks):
        return max_fav, max_adv, best_px, worst_px
    hold_deadline = ticks[start_index].ts + timedelta(hours=float(max_hold_hours))
    for i in range(start_index + 1, len(ticks)):
        t = ticks[i]
        loc = _local(t.ts, tz)
        px = _mid(t)
        fav = _fav_pts(side, entry, px, ps)
        adv = _adv_pts(side, entry, px, ps)
        if fav > max_fav:
            max_fav = fav
            best_px = px
        if adv > max_adv:
            max_adv = adv
            worst_px = px
        if loc >= flatten_local or t.ts >= hold_deadline:
            break
    return max_fav, max_adv, best_px, worst_px


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
) -> Tuple[str, datetime, float, float, bool, float, float, float, float]:
    """
    Walk ticks after fill.
    Returns (reason, exit_ts, exit_px, pts, trail_armed, max_fav, max_adv, best_px, worst_px).
    """
    trail_armed = False
    trail_level: Optional[float] = None
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    worst_px = entry
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
            worst_px = px

        # Hard flatten
        if loc >= flatten_local or t.ts >= hold_deadline:
            pts = _fav_pts(side, entry, px, ps)
            return "flatten", t.ts, px, pts, trail_armed, max_fav, max_adv, best_px, worst_px

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
                    return "trail", t.ts, trail_level, pts, True, max_fav, max_adv, best_px, worst_px
            else:
                new_trail = best_px + params.trail_pts * ps
                if new_trail < trail_level:
                    trail_level = new_trail
                if px >= trail_level - 1e-12:
                    pts = _fav_pts(side, entry, trail_level, ps)
                    return "trail", t.ts, trail_level, pts, True, max_fav, max_adv, best_px, worst_px

        # Fixed SL / TP
        if _hit_level(side, px, sl, is_sl=True):
            pts = _fav_pts(side, entry, sl, ps)
            return "sl", t.ts, sl, pts, trail_armed, max_fav, max_adv, best_px, worst_px
        if _hit_level(side, px, tp, is_sl=False):
            pts = _fav_pts(side, entry, tp, ps)
            return "tp", t.ts, tp, pts, trail_armed, max_fav, max_adv, best_px, worst_px

    pts = _fav_pts(side, entry, last_px, ps)
    return "timeout", last_ts, last_px, pts, trail_armed, max_fav, max_adv, best_px, worst_px


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

    builder = CandleBuilder(timeframe_minutes=15, max_completed=200, skip_ignored=False)
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
            skips.append(_mk_skip(day, "no_candles"))
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
            skips.append(
                _mk_skip(day, "thin_asia", detail=f"{len(asia_candles)} candles")
            )
            continue

        asia_high = max(c.high for c in asia_candles)
        asia_low = min(c.low for c in asia_candles)
        asia_range_pts = (asia_high - asia_low) / ps
        if asia_range_pts < params.min_asia_range_pts:
            skips.append(
                _mk_skip(
                    day,
                    "asia_too_small",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    asia_range_pts=asia_range_pts,
                )
            )
            continue

        flatten_local = _at_local(day, params.flatten_hour, 0, tz)
        after_asia = [
            c
            for c in day_candles
            if _local(c.open_time, tz).hour >= params.asia_end_hour
        ]
        # Candles after Asia end that can still produce the first break
        post_asia = after_asia[: params.max_break_candles_after]

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

        above_asia, below_asia = _asia_extensions(after_asia, asia_high, asia_low, ps)

        def skip_break(reason: str, **extra: Any) -> OvernightSkip:
            fav = adv = fav_px = adv_px = None
            bp = extra.get("break_pts")
            if break_candle is not None and side is not None:
                ref = break_candle.close
                idx = find_tick_index(break_candle.close_time)
                fav, adv, fav_px, adv_px = _excursion_from(
                    ticks,
                    idx,
                    side=side,
                    entry=ref,
                    ps=ps,
                    tz=tz,
                    flatten_local=flatten_local,
                    max_hold_hours=params.max_hold_hours,
                )
                if bp is None:
                    if side == "UP":
                        bp = (break_candle.close - asia_high) / ps
                    else:
                        bp = (asia_low - break_candle.close) / ps
            if extra.get("decision") is None:
                extra["decision"] = _skip_decision(
                    reason=reason,
                    wait_n=extra.get("wait_n"),
                    waited=extra.get("waited"),
                    ema=extra.get("ema"),
                    closest_ema_pts=extra.get("closest_ema_pts"),
                    best_resume_pts=extra.get("best_resume_pts"),
                    use_higher_close=_resume_enabled(params),
                    break_pts=bp,
                    side=side,
                )
            waited = extra.pop("waited", None)
            extra.pop("break_pts", None)
            if extra.get("wait_i") is None and waited is not None:
                extra["wait_i"] = waited
            return _mk_skip(
                day,
                reason,
                side=side,
                asia_high=asia_high,
                asia_low=asia_low,
                asia_range_pts=asia_range_pts,
                break_price=break_candle.close if break_candle is not None else None,
                max_fav_pts=fav,
                max_adv_pts=adv,
                max_fav_price=fav_px,
                max_adv_price=adv_px,
                max_above_asia_pts=above_asia,
                max_below_asia_pts=below_asia,
                break_pts=bp,
                **extra,
            )

        if break_candle is None or side is None:
            skips.append(
                _mk_skip(
                    day,
                    "no_break",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    asia_range_pts=asia_range_pts,
                    max_above_asia_pts=above_asia,
                    max_below_asia_pts=below_asia,
                )
            )
            continue

        if params.side_filter == "long" and side != "UP":
            skips.append(skip_break("side_filter"))
            continue
        if params.side_filter == "short" and side != "DOWN":
            skips.append(skip_break("side_filter"))
            continue

        # --- Entry logic ---
        entry_ts: Optional[datetime] = None
        entry_px: Optional[float] = None
        entry_reason = "break_close"
        entry_idx = find_tick_index(break_candle.close_time)
        if side == "UP":
            break_pts = (break_candle.close - asia_high) / ps
        else:
            break_pts = (asia_low - break_candle.close) / ps

        wait_i: Optional[int] = 0
        wait_n: Optional[int] = None
        ema_at: Optional[float] = None
        prev_at: Optional[float] = None
        sig_close: Optional[float] = None
        same_bar_ema = False
        closest_ema_pts: Optional[float] = None
        best_resume_pts: Optional[float] = None
        waited = 0

        if params.pullback_mode == "off":
            # Enter at break candle close (or first tick after)
            if entry_idx >= n:
                skips.append(skip_break("no_entry_tick", break_pts=break_pts))
                continue
            entry_ts = ticks[entry_idx].ts
            entry_px = _mid(ticks[entry_idx])
            entry_reason = "break_close"
            wait_i = 0
            wait_n = 0
        else:
            wait_candles = post_asia[
                post_asia.index(break_candle) + 1 : post_asia.index(break_candle)
                + 1
                + params.max_wait_candles
            ]
            wait_n = len(wait_candles)
            found = False
            ema_val: Optional[float] = None
            worst_px = _mid(ticks[entry_idx]) if entry_idx < n else break_candle.close

            for wi, wc in enumerate(wait_candles, start=1):
                waited = wi
                closes_for_ema = [
                    c.close for c in completed if c.open_time < wc.open_time
                ]
                ema_val = _ema(
                    closes_for_ema[-params.ema_period * 2 :], params.ema_period
                )
                prev_close = closes_for_ema[-1] if closes_for_ema else None

                resume_hit = False
                resume_pts: Optional[float] = None
                if _resume_enabled(params) and prev_close is not None:
                    if side == "UP":
                        resume_pts = (wc.close - prev_close) / ps
                        resume_hit = wc.close > prev_close + 1e-12
                    else:
                        resume_pts = (prev_close - wc.close) / ps
                        resume_hit = wc.close < prev_close - 1e-12
                    if best_resume_pts is None or resume_pts > best_resume_pts:
                        best_resume_pts = resume_pts

                ema_touched = False
                ema_touch_idx: Optional[int] = None
                ema_touch_px: Optional[float] = None
                if ema_val is not None:
                    c_start = find_tick_index(wc.open_time)
                    c_end = find_tick_index(wc.close_time)
                    for ti in range(c_start, min(c_end + 1, n)):
                        px = _mid(ticks[ti])
                        if side == "UP":
                            dist = (px - ema_val) / ps
                            worst_px = min(worst_px, px)
                            if px <= ema_val + 1e-9:
                                ema_touched = True
                                if ema_touch_idx is None:
                                    ema_touch_idx = ti
                                    ema_touch_px = px
                        else:
                            dist = (ema_val - px) / ps
                            worst_px = max(worst_px, px)
                            if px >= ema_val - 1e-9:
                                ema_touched = True
                                if ema_touch_idx is None:
                                    ema_touch_idx = ti
                                    ema_touch_px = px
                        if closest_ema_pts is None or dist < closest_ema_pts:
                            closest_ema_pts = dist

                if resume_hit:
                    idx = find_tick_index(wc.close_time)
                    if idx < n:
                        entry_ts = ticks[idx].ts
                        entry_px = _mid(ticks[idx])
                        entry_reason = (
                            "higher_close" if side == "UP" else "lower_close"
                        )
                        entry_idx = idx
                        wait_i = wi
                        ema_at = ema_val
                        prev_at = prev_close
                        sig_close = wc.close
                        same_bar_ema = ema_touched
                        found = True
                        break

                if ema_touched and ema_touch_idx is not None and ema_touch_px is not None:
                    entry_ts = ticks[ema_touch_idx].ts
                    entry_px = ema_touch_px
                    entry_reason = "ema_touch"
                    entry_idx = ema_touch_idx
                    wait_i = wi
                    ema_at = ema_val
                    prev_at = prev_close
                    sig_close = wc.close
                    found = True
                    break

            skip_diag = dict(
                wait_n=wait_n,
                waited=waited,
                ema=ema_val if wait_candles else None,
                closest_ema_pts=closest_ema_pts,
                best_resume_pts=best_resume_pts,
                break_pts=break_pts,
            )

            if not found:
                if params.pullback_mode in ("required", "ema"):
                    skips.append(skip_break("no_pullback", **skip_diag))
                    continue
                if params.timeout_action == "skip":
                    skips.append(skip_break("no_pullback_timeout", **skip_diag))
                    continue
                if entry_idx >= n:
                    skips.append(skip_break("no_entry_tick", **skip_diag))
                    continue
                if params.timeout_action == "worst":
                    entry_px = worst_px
                    entry_reason = "timeout_worst"
                else:
                    entry_px = _mid(ticks[entry_idx])
                    entry_reason = "timeout_market"
                entry_ts = ticks[entry_idx].ts
                wait_i = waited
                ema_at = skip_diag["ema"]

        if entry_ts is None or entry_px is None:
            skips.append(skip_break("no_entry"))
            continue

        close_vs_prev_pts: Optional[float] = None
        if prev_at is not None and sig_close is not None:
            if side == "UP":
                close_vs_prev_pts = (sig_close - prev_at) / ps
            else:
                close_vs_prev_pts = (prev_at - sig_close) / ps
        entry_vs_ema_pts: Optional[float] = None
        if ema_at is not None:
            if side == "UP":
                entry_vs_ema_pts = (entry_px - ema_at) / ps
            else:
                entry_vs_ema_pts = (ema_at - entry_px) / ps
        decision = _decision_line(
            reason=entry_reason,
            side=side,
            wait_i=wait_i,
            wait_n=wait_n,
            ema=ema_at,
            prev_close=prev_at,
            signal_close=sig_close,
            entry=entry_px,
            break_pts=break_pts,
            entry_vs_ema_pts=entry_vs_ema_pts,
            close_vs_prev_pts=close_vs_prev_pts,
            same_bar_ema=same_bar_ema,
            pullback_mode=params.pullback_mode,
            closest_ema_pts=closest_ema_pts,
            best_resume_pts=best_resume_pts,
            use_higher_close=_resume_enabled(params),
        )

        sl, tp, sl_pts, tp_pts = _compute_sl_tp(
            side, entry_px, asia_high, asia_low, params, ps
        )

        if _local(entry_ts, tz) >= flatten_local:
            skips.append(
                skip_break(
                    "past_flatten",
                    wait_n=wait_n,
                    waited=waited,
                    ema=ema_at,
                    closest_ema_pts=closest_ema_pts,
                    best_resume_pts=best_resume_pts,
                    break_pts=break_pts,
                    decision=decision + " · past flatten",
                )
            )
            continue

        (
            reason,
            exit_ts,
            exit_px,
            pts,
            trail_armed,
            max_fav,
            max_adv,
            best_px,
            worst_px,
        ) = _simulate_from_entry(
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
                entry_label=entry_label(entry_reason),
                wait_i=wait_i,
                wait_n=wait_n,
                ema=_round_or_none(ema_at, 5),
                prev_close=_round_or_none(prev_at, 5),
                signal_close=_round_or_none(sig_close, 5),
                break_pts=_round_or_none(break_pts, 1),
                entry_vs_ema_pts=_round_or_none(entry_vs_ema_pts, 1),
                close_vs_prev_pts=_round_or_none(close_vs_prev_pts, 1),
                same_bar_ema=same_bar_ema,
                decision=decision,
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
                max_fav_price=round(best_px, 5),
                max_adv_price=round(worst_px, 5),
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
