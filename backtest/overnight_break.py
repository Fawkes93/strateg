"""
Overnight / Asia range breakout strategy (pure — no web, no MT5).

Bucharest time Asia window → first 15m close outside with min break pts
→ optional pullback entry (EMA touch or higher/lower close resume).

Entry modes:
  off       : enter on break candle close
  required  : must get EMA touch (or higher-close resume if enabled) within max wait, else skip
  preferred : try pullback; on timeout skip, or enter at last wait-bar close (market)

Higher/lower close resume is a separate checkbox (ignored when mode is off).

Trail arm:
  fixed      : trail_arm_pts profit before trail activates (0 = off)
  asia       : arm = Asia range, capped at trail_arm_cap_pts (0 cap = uncapped)
  from_fill  : trail on from the fill. Distance = trail_pts, or the initial SL if 0.

Break-even: be_arm_pts profit moves SL to the fill (0 = off). Exit reason be.
Trail still tightens independently.

TP m12: mean of the last 12 complete months' daily-close ranges
(max close − min close that month), rounded up to 50 pts.
SL m12_frac: that same average × 1/4, 1/3, or 1/2, also rounded up to 50 pts.
Fixed SL still works with m12 TP.

No partial take-profit.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from math import ceil
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.asia_box import fib_px
from backtest.candles import Candle, CandleBuilder, aggregate_tf, is_market_open, to_utc
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.news_calendar import (
    events_on,
    format_news,
    kinds_for_set,
    normalize_news_mode,
    normalize_news_set,
)
from backtest.seasonality import (
    bias_side,
    build_daily_closes,
    build_daily_closes_from_candles,
    month_regime,
    normalize_seasonal_mode,
    normalize_week2_mode,
    seasonal_label,
    snapshot_bias,
)


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
    require_close_outside: bool = True  # False = wick (high/low) can print the break
    break_on_wick: bool = False  # True → same as require_close_outside False
    # Pullback / entry
    pullback_mode: str = "required"  # off | required | preferred
    # ema = wait for the EMA. fib = wait for a retracement of the Asia box.
    # Fib 0 is the Asia edge in the trade direction, Fib 1 the other edge.
    pullback_ref: str = "ema"  # ema | fib
    pullback_fib: float = 0.5
    ema_period: int = 21
    ema_tf_min: int = 15
    max_wait_candles: int = 8  # 15m candles after break
    wait_from_break: bool = False  # True = count wait from the break bar, not leftover post_asia
    timeout_action: str = "skip"  # skip | market  (only for preferred)
    # Preferred timeout quality. 0 = off (current ungated timeout).
    # Dist: closest wait-scan approach to EMA (pts). None / farther → skip.
    # Extra break floor applies only to timeout fills, not EMA-touch.
    timeout_max_ema_dist_pts: float = 0.0
    timeout_min_break_pts: float = 0.0
    # Preferred timeout: last wait close must be this many pts back from
    # the break close (long: below, short: above). 0 = off.
    timeout_min_pullback_pts: float = 0.0
    # Required-mode recovery: if wait times out, take timeout fill when the
    # last N wait candles all stayed within near_box_pts of asia_high (UP)
    # or asia_low (DOWN). near_box_bars=0 disables (default).
    near_box_bars: int = 0
    near_box_pts: float = 500.0
    # Extra gate on near-box timeout fills (ignored when near_box_bars=0):
    #   off          = distance-only
    #   closes_dir   = each of last N closes moves in break direction
    #   net_ext      = last close farther past Asia edge than first of last N
    #   outside      = last close still outside box by min_break
    #   breakout     = net_ext AND outside (steady push + still broken out)
    near_box_trend: str = "off"
    use_higher_close: bool = True  # higher/lower close resume during wait
    resume_closes: int = 1  # consecutive directional closes required (1 = current)
    # Resume close may not extend more than this many pts past the break close.
    # 0 = off. Pullback side of the break always allowed.
    resume_max_break_pts: float = 0.0
    # Skip DOWN entries from this wait bar onward when Asia is below the cap.
    # skip_late_short_wait 0 = off. skip_late_short_asia_pts 0 = any Asia size.
    skip_late_short_wait: int = 7
    skip_late_short_asia_pts: float = 3000.0
    # Risk
    sl_mode: str = "asia_opposite"  # fixed | asia_opposite | range | m12_frac
    sl_fixed_pts: float = 500.0
    sl_range_mult: float = 1.0
    sl_cap_pts: float = 0.0  # max SL distance (pts). 0 = off. asia_opposite + range.
    sl_m12_frac: float = 1.0 / 3.0  # of 12m avg when sl_mode=m12_frac
    tp_mode: str = "range_mult"  # fixed | range_mult | r_mult | m12
    tp_fixed_pts: float = 1000.0
    tp_range_mult: float = 1.5
    tp_r_mult: float = 2.0
    trail_arm_mode: str = "fixed"  # fixed | asia | from_fill
    trail_arm_pts: float = 400.0  # profit before trail activates when mode=fixed (0 = off)
    trail_arm_cap_pts: float = 2000.0  # max arm when mode=asia (0 = no cap)
    trail_pts: float = 250.0  # gap behind best price. from_fill + 0 = use initial SL
    be_arm_pts: float = 0.0  # profit before SL moves to entry. 0 = off
    max_hold_hours: float = 10.0
    flatten_hour: int = 18  # local hour hard flatten
    one_trade_per_day: bool = True
    # Second entry only after the first trade exits at its stop.
    # Needs this many signal candles in a row to close back through the
    # original fill. Fixed stop and target from that new fill. No trail.
    reentry_enabled: bool = False
    reentry_closes: int = 1
    reentry_sl_pts: float = 1000.0
    reentry_tp_pts: float = 3000.0
    side_filter: str = "both"  # both | long | short
    # Month bias (Bucharest). off = ignore table. tag = stamp only.
    # filter = skip Asia breaks that fight the month.
    seasonal_mode: str = "off"  # off | tag | filter
    # If the month has a bias and Asia never printed a valid break, enter with
    # that bias instead of skipping no_break.
    seasonal_join: bool = False
    # 2-week tape (close vs daily EMA + efficiency). Independent of the month
    # table: off | tag | filter. Legacy week2_trend=True maps in _normalize.
    week2_trend: bool = False
    week2_mode: str = "off"  # off | tag | filter
    trend_flat_pts: float = 1500.0
    trend_sessions: int = 10
    trend_efficiency_min: float = 0.35
    # Gold news days (backtest/xau_news_days.json). off = ignore.
    # tag = stamp only. filter = skip the whole local day.
    news_mode: str = "off"  # off | tag | filter
    news_set: str = "scheduled"  # scheduled | all


def _normalize_params(params: OvernightParams) -> OvernightParams:
    # Old UI had a dedicated "ema" pullback mode = required + resume off.
    if params.pullback_mode == "ema":
        params.pullback_mode = "required"
        params.use_higher_close = False
    ref = str(getattr(params, "pullback_ref", "ema") or "ema").strip().lower()
    params.pullback_ref = "fib" if ref == "fib" else "ema"
    try:
        params.pullback_fib = min(1.0, max(0.0, float(params.pullback_fib)))
    except (TypeError, ValueError):
        params.pullback_fib = 0.5
    try:
        params.reentry_closes = max(1, int(params.reentry_closes or 1))
    except (TypeError, ValueError):
        params.reentry_closes = 1
    params.reentry_enabled = bool(params.reentry_enabled)
    if bool(params.break_on_wick):
        params.require_close_outside = False
    elif not params.require_close_outside:
        params.break_on_wick = True
    params.seasonal_mode = normalize_seasonal_mode(params.seasonal_mode)
    params.seasonal_join = bool(params.seasonal_join)
    params.week2_mode = normalize_week2_mode(
        getattr(params, "week2_mode", None),
        week2_trend=bool(params.week2_trend),
        seasonal_mode=params.seasonal_mode,
    )
    params.week2_trend = params.week2_mode != "off"
    params.news_mode = normalize_news_mode(params.news_mode)
    params.news_set = normalize_news_set(params.news_set)
    try:
        params.trend_flat_pts = float(params.trend_flat_pts)
    except (TypeError, ValueError):
        params.trend_flat_pts = 1500.0
    try:
        params.trend_sessions = max(5, int(params.trend_sessions or 10))
    except (TypeError, ValueError):
        params.trend_sessions = 10
    try:
        params.trend_efficiency_min = max(
            0.0, float(params.trend_efficiency_min if params.trend_efficiency_min is not None else 0.35)
        )
    except (TypeError, ValueError):
        params.trend_efficiency_min = 0.35
    try:
        params.timeout_max_ema_dist_pts = max(
            0.0, float(params.timeout_max_ema_dist_pts or 0.0)
        )
    except (TypeError, ValueError):
        params.timeout_max_ema_dist_pts = 0.0
    try:
        params.timeout_min_break_pts = max(
            0.0, float(params.timeout_min_break_pts or 0.0)
        )
    except (TypeError, ValueError):
        params.timeout_min_break_pts = 0.0
    try:
        params.timeout_min_pullback_pts = max(
            0.0, float(params.timeout_min_pullback_pts or 0.0)
        )
    except (TypeError, ValueError):
        params.timeout_min_pullback_pts = 0.0
    try:
        params.near_box_bars = max(0, int(params.near_box_bars or 0))
    except (TypeError, ValueError):
        params.near_box_bars = 0
    try:
        params.near_box_pts = max(0.0, float(params.near_box_pts or 0.0))
    except (TypeError, ValueError):
        params.near_box_pts = 0.0
    trend = str(getattr(params, "near_box_trend", "off") or "off").strip().lower()
    if trend not in ("off", "closes_dir", "net_ext", "outside", "breakout"):
        trend = "off"
    params.near_box_trend = trend
    try:
        params.resume_max_break_pts = max(
            0.0, float(params.resume_max_break_pts or 0.0)
        )
    except (TypeError, ValueError):
        params.resume_max_break_pts = 0.0
    try:
        params.be_arm_pts = max(0.0, float(params.be_arm_pts or 0.0))
    except (TypeError, ValueError):
        params.be_arm_pts = 0.0
    act = str(params.timeout_action or "skip").strip().lower()
    # Legacy "worst" was a hindsight pullback fill; treat as live chase.
    if act == "worst":
        act = "market"
    if act not in ("skip", "market"):
        act = "skip"
    params.timeout_action = act
    mode = str(params.sl_mode or "asia_opposite").strip().lower()
    if mode in ("range", "asia_range", "range_width"):
        params.sl_mode = "range"
    elif mode == "fixed":
        params.sl_mode = "fixed"
    elif mode in ("m12_frac", "m12", "m12_pct", "month12"):
        params.sl_mode = "m12_frac"
    else:
        params.sl_mode = "asia_opposite"
    try:
        params.sl_m12_frac = _snap_m12_frac(params.sl_m12_frac)
    except (TypeError, ValueError):
        params.sl_m12_frac = 1.0 / 3.0
    tm = str(params.tp_mode or "range_mult").strip().lower()
    if tm in ("m12", "m12_avg", "month12", "avg12"):
        params.tp_mode = "m12"
    elif tm == "fixed":
        params.tp_mode = "fixed"
    elif tm in ("r_mult", "r"):
        params.tp_mode = "r_mult"
    else:
        params.tp_mode = "range_mult"
    try:
        params.sl_cap_pts = max(0.0, float(params.sl_cap_pts or 0.0))
    except (TypeError, ValueError):
        params.sl_cap_pts = 0.0
    tam = str(params.trail_arm_mode or "fixed").strip().lower()
    if tam in ("from_fill", "from_start", "immediate", "now", "sl"):
        params.trail_arm_mode = "from_fill"
    elif tam == "asia":
        params.trail_arm_mode = "asia"
    elif tam == "off":
        params.trail_arm_mode = "off"
    else:
        params.trail_arm_mode = "fixed"
    return params


def _use_wick_break(params: OvernightParams) -> bool:
    return bool(params.break_on_wick) or not bool(params.require_close_outside)


def _break_pts_for(
    side: str,
    candle: Candle,
    asia_high: float,
    asia_low: float,
    ps: float,
    *,
    wick: bool,
) -> float:
    if side == "UP":
        px = candle.high if wick else candle.close
        return (px - asia_high) / ps
    px = candle.low if wick else candle.close
    return (asia_low - px) / ps


def _resume_enabled(params: OvernightParams) -> bool:
    if params.pullback_mode == "off":
        return False
    return bool(params.use_higher_close)


def _resume_need(params: OvernightParams) -> int:
    return max(1, int(params.resume_closes or 1))


def resume_too_far_from_break(
    params: OvernightParams,
    side: str,
    wait_close: float,
    break_close: float,
    ps: float,
) -> bool:
    """True when a resume close extends more than resume_max_break_pts past the break.

    Long: wait close above break. Short: wait close below break. 0 cap = off.
    A close on the pullback side of the break always passes.
    """
    cap = 0.0
    try:
        cap = max(0.0, float(getattr(params, "resume_max_break_pts", 0.0) or 0.0))
    except (TypeError, ValueError):
        cap = 0.0
    if cap <= 0 or ps <= 0:
        return False
    if side == "UP":
        ext = (wait_close - break_close) / ps
    else:
        ext = (break_close - wait_close) / ps
    return ext > cap + 1e-9



def near_box_hug(
    params: OvernightParams,
    side: str,
    wait_candles: Sequence,
    asia_high: float,
    asia_low: float,
    ps: float,
) -> bool:
    """True when last N wait closes hug the Asia edge and optional trend gate passes.

    Distance: every close of wait_candles[-N:] within near_box_pts of asia_high (UP)
    or asia_low (DOWN). Bars=0 / pts=0 / too-few candles → False.

    Trend (near_box_trend):
      off        — distance only
      closes_dir — each close steps in break direction vs prior close in the tail
      net_ext    — last close farther past the edge than the first close of the tail
      outside    — last close still outside the box by min_break
      breakout   — net_ext AND outside (steady extension that never fully failed)
    """
    n = int(getattr(params, "near_box_bars", 0) or 0)
    d = float(getattr(params, "near_box_pts", 0.0) or 0.0)
    if n <= 0 or d <= 0.0 or not wait_candles or len(wait_candles) < n:
        return False
    if ps <= 0:
        return False
    ref = asia_high if side == "UP" else asia_low
    tail = list(wait_candles[-n:])
    for c in tail:
        if abs(float(c.close) - ref) / ps > d + 1e-12:
            return False

    trend = str(getattr(params, "near_box_trend", "off") or "off").strip().lower()
    if trend in ("", "off"):
        return True

    def _ext_pts(px: float) -> float:
        if side == "UP":
            return (float(px) - ref) / ps
        return (ref - float(px)) / ps

    if trend == "closes_dir":
        for i in range(1, len(tail)):
            if side == "UP":
                if float(tail[i].close) + 1e-12 < float(tail[i - 1].close):
                    return False
            else:
                if float(tail[i].close) > float(tail[i - 1].close) + 1e-12:
                    return False
        return True

    if trend == "net_ext":
        return _ext_pts(tail[-1].close) > _ext_pts(tail[0].close) + 1e-12

    min_br = (
        float(params.min_break_pts_above or 0.0)
        if side == "UP"
        else float(params.min_break_pts_below or 0.0)
    )

    def _outside() -> bool:
        return _ext_pts(tail[-1].close) + 1e-12 >= min_br

    if trend == "outside":
        return _outside()

    if trend == "breakout":
        return (
            _ext_pts(tail[-1].close) > _ext_pts(tail[0].close) + 1e-12
            and _outside()
        )

    return False


def late_short_blocked(
    params: OvernightParams,
    side: str,
    wait_i: int,
    asia_range_pts: float,
) -> bool:
    """True when a short EMA/resume fill should be ignored (late + small Asia)."""
    min_wait = int(params.skip_late_short_wait or 0)
    if min_wait <= 0 or side != "DOWN":
        return False
    if int(wait_i) < min_wait:
        return False
    cap = float(params.skip_late_short_asia_pts or 0.0)
    if cap > 0 and float(asia_range_pts) >= cap:
        return False
    return True


def timeout_quality_blocked(
    params: OvernightParams,
    *,
    closest_ema_pts: Optional[float],
    break_pts: Optional[float],
    last_wait_pullback_pts: Optional[float] = None,
) -> bool:
    """True when a preferred timeout fill fails the EMA-distance / extra-break / pullback gate.

    Dist cap 0 = off. Break floor 0 = no extra vs the existing min-break.
    Pullback floor 0 = off. Missing closest_ema_pts fails a positive dist cap (no wait scan).
    Missing last_wait_pullback_pts fails a positive pullback floor.
    """
    max_dist = float(params.timeout_max_ema_dist_pts or 0.0)
    if max_dist > 0:
        if closest_ema_pts is None or float(closest_ema_pts) > max_dist + 1e-9:
            return True
    min_break = float(params.timeout_min_break_pts or 0.0)
    if min_break > 0:
        if break_pts is None or float(break_pts) + 1e-9 < min_break:
            return True
    min_pb = float(params.timeout_min_pullback_pts or 0.0)
    if min_pb > 0:
        if last_wait_pullback_pts is None or float(last_wait_pullback_pts) + 1e-9 < min_pb:
            return True
    return False


def require_zone(name: str) -> ZoneInfo:
    """Resolve an IANA zone or raise a pip-install-tzdata error (do not fall back to UTC)."""
    key = (name or "").strip() or "Europe/Bucharest"
    try:
        return ZoneInfo(key)
    except Exception as e:
        raise RuntimeError(
            f"Timezone {key!r} is not available ({e}). "
            "This Python is missing IANA tz data — install it with: python -m pip install tzdata"
        ) from e


def trail_arm_for_range(params: OvernightParams, asia_range_pts: float) -> float:
    """Profit (pts) required before the trail activates for this day's Asia range.

    from_fill returns 0 (armed at the fill, not 'trail off').
    """
    mode = (params.trail_arm_mode or "fixed").strip().lower()
    if mode in ("from_fill", "from_start", "immediate", "now", "sl", "off"):
        return 0.0
    if mode == "asia":
        arm = float(asia_range_pts or 0.0)
        cap = float(params.trail_arm_cap_pts or 0.0)
        if cap > 0:
            arm = min(arm, cap)
        return max(0.0, arm)
    return max(0.0, float(params.trail_arm_pts or 0.0))


def trail_setup(
    params: OvernightParams,
    asia_range_pts: float,
    sl_pts: float,
) -> Tuple[float, float, bool]:
    """Return (arm_pts, trail_dist_pts, from_fill).

    from_fill: trail is on from the entry. trail_pts 0 → use the initial SL.
    Otherwise arm_pts 0 means the trail stays off.
    """
    mode = (params.trail_arm_mode or "fixed").strip().lower()
    if mode in ("from_fill", "from_start", "immediate", "now", "sl"):
        dist = max(0.0, float(params.trail_pts or 0.0))
        if dist <= 0:
            dist = max(0.0, float(sl_pts or 0.0))
        return 0.0, dist, True
    if mode == "off":
        return 0.0, 0.0, False
    arm = trail_arm_for_range(params, asia_range_pts)
    return arm, max(0.0, float(params.trail_pts or 0.0)), False


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
    tz = require_zone(timezone_name)
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
    entry_reason: str  # break_close | ema_touch | higher_close | timeout_market
    sl: float
    tp: float
    sl_pts: float
    tp_pts: float
    m12_pts: Optional[float] = None  # rounded 12m daily-close-range avg, if used
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None  # tp | sl | trail | flatten | timeout
    pts: float = 0.0
    trail_arm_used: float = 0.0
    trail_armed: bool = False
    be_armed: bool = False
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
    closest_ema_pts: Optional[float] = None  # wait-scan closest; >0 = never touched
    last_wait_pullback_pts: Optional[float] = None  # last wait close vs break close
    close_vs_prev_pts: Optional[float] = None
    same_bar_ema: bool = False
    decision: str = ""
    seasonal_regime: Optional[str] = None
    seasonal_label: Optional[str] = None
    trend_state: Optional[str] = None
    trend_side: Optional[str] = None
    trend_move_pts: Optional[float] = None
    bias_conflict: bool = False
    bias_side: Optional[str] = None
    news_kind: Optional[str] = None
    news_title: Optional[str] = None


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
    last_wait_pullback_pts: Optional[float] = None
    best_resume_pts: Optional[float] = None  # best close vs prev in trade direction
    break_pts: Optional[float] = None
    decision: Optional[str] = None
    detail: Optional[str] = None
    seasonal_regime: Optional[str] = None
    seasonal_label: Optional[str] = None
    trend_state: Optional[str] = None
    trend_side: Optional[str] = None
    trend_move_pts: Optional[float] = None
    bias_conflict: bool = False
    bias_side: Optional[str] = None
    news_kind: Optional[str] = None
    news_title: Optional[str] = None


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
        "near_box_timeout": "Near-box timeout",
        "seasonal_join": "Seasonal join (inside box)",
        "fib_touch": "Fib touch",
        "reentry": "Second trade",
    }.get(reason, reason or "—")


def trade_fib_px(asia_high: float, asia_low: float, side: str, level: float) -> float:
    """Asia-box fib. Fib 0 is the edge in the trade direction, Fib 1 the other edge."""
    if side == "UP":
        return fib_px(asia_high, asia_low, level)
    return fib_px(asia_low, asia_high, level)


def _close_through(side: str, close: float, entry: float) -> bool:
    if side == "UP":
        return close >= entry - 1e-9
    return close <= entry + 1e-9


def reentry_signal_candle(
    candles: Sequence[Candle],
    *,
    after: datetime,
    side: str,
    entry: float,
    need: int,
    tz: ZoneInfo,
    flatten_local: datetime,
) -> Optional[Candle]:
    """Nth signal candle in a row that closes back through the original fill."""
    streak = 0
    required = max(1, int(need))
    for candle in candles:
        if candle.close_time <= after:
            continue
        if _local(candle.open_time, tz) >= flatten_local:
            break
        if _close_through(side, candle.close, entry):
            streak += 1
            if streak >= required:
                return candle
        else:
            streak = 0
    return None


def _fmt_px(x: Optional[float]) -> str:
    if x is None:
        return "—"
    v = float(x)
    ax = abs(v)
    if ax >= 1000:
        return f"{v:.2f}"
    if ax >= 10:
        return f"{v:.3f}"
    return f"{v:.5f}"


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
    resume_closes: int = 1,
    pullback_ref: str = "ema",
    pullback_fib: float = 0.5,
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
        if resume_closes > 1:
            kind = "higher" if side == "UP" else "lower"
            parts.append(f"{resume_closes} consecutive {kind} closes")
        if same_bar_ema:
            touched = "Fib" if pullback_ref == "fib" else "EMA"
            parts.append(f"{touched} also touched this bar (close wins)")
        elif pullback_ref == "fib":
            parts.append(f"Fib {pullback_fib:g}")
        elif ema is not None:
            parts.append(f"EMA {_fmt_px(ema)}")
    elif reason == "fib_touch":
        parts.append(
            f"Fib {pullback_fib:g} at {_fmt_px(ema)} fill {_fmt_px(entry)}".strip()
        )
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
    elif reason == "near_box_timeout":
        parts.append("last wait closes hugged the Asia edge")
    elif reason.startswith("timeout"):
        if closest_ema_pts is None:
            parts.append("EMA not ready")
        else:
            parts.append(f"closest to EMA {closest_ema_pts:+.0f} pts")
        if not use_higher_close:
            parts.append("close resume off")
        else:
            if resume_closes > 1:
                parts.append(f"need {resume_closes} consecutive closes")
            if best_resume_pts is None:
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
    resume_closes: int = 1,
    resume_streak: Optional[int] = None,
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
        else:
            if resume_closes > 1:
                parts.append(
                    f"need {resume_closes} consecutive closes (streak {resume_streak or 0})"
                )
            if best_resume_pts is None:
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
    last_wait_pullback_pts: Optional[float] = None,
    best_resume_pts: Optional[float] = None,
    break_pts: Optional[float] = None,
    decision: Optional[str] = None,
    detail: Optional[str] = None,
    seasonal_regime: Optional[str] = None,
    seasonal_label: Optional[str] = None,
    trend_state: Optional[str] = None,
    trend_side: Optional[str] = None,
    trend_move_pts: Optional[float] = None,
    bias_conflict: bool = False,
    bias_side: Optional[str] = None,
    news_kind: Optional[str] = None,
    news_title: Optional[str] = None,
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
        last_wait_pullback_pts=_round_or_none(last_wait_pullback_pts, 1),
        best_resume_pts=_round_or_none(best_resume_pts, 1),
        break_pts=_round_or_none(break_pts, 1),
        decision=decision,
        detail=detail,
        seasonal_regime=seasonal_regime,
        seasonal_label=seasonal_label,
        trend_state=trend_state,
        trend_side=trend_side,
        trend_move_pts=_round_or_none(trend_move_pts, 1),
        bias_conflict=bool(bias_conflict),
        bias_side=bias_side,
        news_kind=news_kind,
        news_title=news_title,
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
) -> Tuple[float, float, float, float]:
    """
    Walk ticks after start until flatten (inclusive of the flatten tick).
    Ignores SL/TP/trail. Returns max_fav_pts, max_adv_pts, fav_peak_px, adv_peak_px.
    """
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    worst_px = entry
    if start_index < 0 or start_index >= len(ticks):
        return max_fav, max_adv, best_px, worst_px
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
        if loc >= flatten_local:
            break
    return max_fav, max_adv, best_px, worst_px


def round_pts_up(pts: float, step: float = 50.0) -> float:
    """Round a positive distance up to the next `step` pts (50 → 50, 51 → 100)."""
    try:
        p = float(pts)
    except (TypeError, ValueError):
        return 0.0
    if p <= 0 or step <= 0:
        return 0.0
    n = ceil(p / step - 1e-12)
    if n < 1:
        n = 1
    return float(n) * float(step)


def _snap_m12_frac(raw: Any) -> float:
    v = float(raw)
    if abs(v - 0.25) < 0.03:
        return 0.25
    if abs(v - 0.5) < 0.03:
        return 0.5
    if abs(v - (1.0 / 3.0)) < 0.03 or abs(v - 0.33) < 0.03:
        return 1.0 / 3.0
    if v <= 0:
        return 1.0 / 3.0
    return min(1.0, v)


def uses_m12(params: OvernightParams) -> bool:
    p = _normalize_params(params)
    return p.tp_mode == "m12" or p.sl_mode == "m12_frac"


def m12_avg_pts(
    dailies: Sequence[Any],
    asof: date,
    ps: float,
    n: int = 12,
) -> Optional[float]:
    """
    Mean of up to `n` prior calendar-month ranges of daily closes, in points.

    For each complete local month before `asof`'s month: max(close) − min(close).
    Months with fewer than 2 daily closes are skipped.
    """
    if ps <= 0 or not dailies:
        return None
    asof_key = (int(asof.year), int(asof.month))
    by_month: Dict[Tuple[int, int], List[float]] = defaultdict(list)
    for d in dailies:
        loc = getattr(d, "local_date", None)
        if loc is None:
            continue
        key = (int(loc.year), int(loc.month))
        if key >= asof_key:
            continue
        by_month[key].append(float(d.close))
    ranges: List[float] = []
    for key in sorted(by_month):
        xs = by_month[key]
        if len(xs) < 2:
            continue
        ranges.append((max(xs) - min(xs)) / ps)
    if not ranges:
        return None
    window = ranges[-max(1, int(n)) :]
    return float(sum(window) / len(window))


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
    m12_pts: Optional[float] = None,
) -> Tuple[float, float, float, float]:
    range_pts = (asia_high - asia_low) / ps

    sl_mode = str(params.sl_mode or "asia_opposite").strip().lower()
    if sl_mode in ("range", "asia_range", "range_width"):
        sl_mode = "range"
    elif sl_mode in ("m12_frac", "m12", "m12_pct", "month12"):
        sl_mode = "m12_frac"

    m12_raw = 0.0
    if m12_pts is not None:
        try:
            m12_raw = max(0.0, float(m12_pts))
        except (TypeError, ValueError):
            m12_raw = 0.0

    # SL
    if sl_mode == "fixed":
        sl_dist = params.sl_fixed_pts * ps
        sl = entry - sl_dist if side == "UP" else entry + sl_dist
    elif sl_mode == "range":
        sl_dist = range_pts * float(params.sl_range_mult or 1.0) * ps
        sl = entry - sl_dist if side == "UP" else entry + sl_dist
    elif sl_mode == "m12_frac":
        frac = _snap_m12_frac(getattr(params, "sl_m12_frac", 1.0 / 3.0))
        sl_pts_r = round_pts_up(m12_raw * frac)
        sl_dist = sl_pts_r * ps
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

    cap_pts = float(params.sl_cap_pts or 0.0)
    if sl_mode != "fixed" and cap_pts > 0 and ps > 0:
        cap = cap_pts * ps
        if side == "UP":
            floor = entry - cap
            if sl < floor:
                sl = floor
        else:
            ceiling = entry + cap
            if sl > ceiling:
                sl = ceiling

    sl_pts = abs(entry - sl) / ps

    # TP
    tp_mode = str(params.tp_mode or "range_mult").strip().lower()
    if tp_mode in ("m12", "m12_avg", "month12", "avg12"):
        tp_dist = round_pts_up(m12_raw) * ps
    elif tp_mode == "fixed":
        tp_dist = params.tp_fixed_pts * ps
    elif tp_mode in ("r_mult", "r"):
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
    trail_arm_pts: Optional[float] = None,
    trail_dist_pts: Optional[float] = None,
    trail_from_fill: bool = False,
    be_arm_override: Optional[float] = None,
) -> Tuple[str, datetime, float, float, bool, float, float, float, float]:
    """
    Walk ticks after fill.
    Returns (reason, exit_ts, exit_px, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed).
    """
    trail_armed = False
    trail_level: Optional[float] = None
    be_armed = False
    sl_now = sl
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    worst_px = entry
    last_ts = ticks[start_index].ts
    last_px = entry
    hold_deadline = ticks[start_index].ts + timedelta(hours=float(params.max_hold_hours))
    arm_pts = float(params.trail_arm_pts or 0.0) if trail_arm_pts is None else float(trail_arm_pts)
    gap = float(params.trail_pts or 0.0) if trail_dist_pts is None else float(trail_dist_pts)
    be_arm = 0.0
    if be_arm_override is not None:
        be_arm = max(0.0, float(be_arm_override))
    else:
        try:
            be_arm = max(0.0, float(getattr(params, "be_arm_pts", 0.0) or 0.0))
        except (TypeError, ValueError):
            be_arm = 0.0
    if trail_from_fill and gap > 0:
        trail_armed = True
        if side == "UP":
            trail_level = entry - gap * ps
        else:
            trail_level = entry + gap * ps

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

        if (not be_armed) and be_arm > 0 and fav + 1e-12 >= be_arm:
            be_armed = True
            sl_now = entry

        # Hard flatten
        if loc >= flatten_local or t.ts >= hold_deadline:
            pts = _fav_pts(side, entry, px, ps)
            return "flatten", t.ts, px, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed

        # Trail arm
        if (not trail_from_fill) and arm_pts > 0 and not trail_armed and fav >= arm_pts and gap > 0:
            trail_armed = True
            if side == "UP":
                trail_level = best_px - gap * ps
            else:
                trail_level = best_px + gap * ps

        # Update trail
        if trail_armed and trail_level is not None and gap > 0:
            if side == "UP":
                new_trail = best_px - gap * ps
                if new_trail > trail_level:
                    trail_level = new_trail
                if px <= trail_level + 1e-12:
                    pts = _fav_pts(side, entry, trail_level, ps)
                    return "trail", t.ts, trail_level, pts, True, max_fav, max_adv, best_px, worst_px, be_armed
            else:
                new_trail = best_px + gap * ps
                if new_trail < trail_level:
                    trail_level = new_trail
                if px >= trail_level - 1e-12:
                    pts = _fav_pts(side, entry, trail_level, ps)
                    return "trail", t.ts, trail_level, pts, True, max_fav, max_adv, best_px, worst_px, be_armed

        # Fixed SL / TP
        if _hit_level(side, px, sl_now, is_sl=True):
            reason = "be" if be_armed else "sl"
            pts = _fav_pts(side, entry, sl_now, ps)
            return reason, t.ts, sl_now, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed
        if _hit_level(side, px, tp, is_sl=False):
            pts = _fav_pts(side, entry, tp, ps)
            return "tp", t.ts, tp, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed

    pts = _fav_pts(side, entry, last_px, ps)
    return "timeout", last_ts, last_px, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed


def _ohlc_closest_ema_pts(candle: Candle, side: str, ema: float, ps: float) -> float:
    best: Optional[float] = None
    for px in (candle.open, candle.high, candle.low, candle.close):
        dist = (px - ema) / ps if side == "UP" else (ema - px) / ps
        if best is None or dist < best:
            best = dist
    return float(best if best is not None else 0.0)


def _ema_touch_from_candle(
    candle: Candle,
    *,
    side: str,
    ema: float,
    ps: float,
) -> Tuple[bool, Optional[datetime], Optional[float], Optional[float]]:
    """Conservative 5m EMA touch: fill at EMA, or at open if already through."""
    closest = _ohlc_closest_ema_pts(candle, side, ema, ps)
    if side == "UP":
        if candle.low <= ema + 1e-9:
            return True, candle.open_time, min(candle.open, ema), closest
        return False, None, None, closest
    if candle.high >= ema - 1e-9:
        return True, candle.open_time, max(candle.open, ema), closest
    return False, None, None, closest


def _simulate_from_candles(
    candles: Sequence[Candle],
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
    trail_arm_pts: Optional[float] = None,
    trail_dist_pts: Optional[float] = None,
    trail_from_fill: bool = False,
    be_arm_override: Optional[float] = None,
) -> Tuple[str, datetime, float, float, bool, float, float, float, float]:
    """Walk 5m bars from start_index (inclusive). Tightest stop > TP on the same bar."""
    trail_armed = False
    trail_level: Optional[float] = None
    be_armed = False
    sl_now = sl
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    worst_px = entry
    if start_index < 0 or start_index >= len(candles):
        return "timeout", datetime.now(timezone.utc), entry, 0.0, False, 0.0, 0.0, entry, entry, False
    last_ts = candles[start_index].open_time
    last_px = entry
    hold_deadline = to_utc(candles[start_index].open_time) + timedelta(
        hours=float(params.max_hold_hours)
    )
    arm_pts = float(params.trail_arm_pts or 0.0) if trail_arm_pts is None else float(trail_arm_pts)
    gap = float(params.trail_pts or 0.0) if trail_dist_pts is None else float(trail_dist_pts)
    be_arm = 0.0
    if be_arm_override is not None:
        be_arm = max(0.0, float(be_arm_override))
    else:
        try:
            be_arm = max(0.0, float(getattr(params, "be_arm_pts", 0.0) or 0.0))
        except (TypeError, ValueError):
            be_arm = 0.0
    if trail_from_fill and gap > 0:
        trail_armed = True
        if side == "UP":
            trail_level = entry - gap * ps
        else:
            trail_level = entry + gap * ps

    def fav_px(px: float) -> float:
        return _fav_pts(side, entry, px, ps)

    def adv_px(px: float) -> float:
        return _adv_pts(side, entry, px, ps)

    for i in range(start_index, len(candles)):
        c = candles[i]
        loc_open = _local(c.open_time, tz)
        loc_close = _local(c.close_time, tz)
        last_ts, last_px = c.close_time, c.close
        extreme_fav = c.high if side == "UP" else c.low
        extreme_adv = c.low if side == "UP" else c.high

        past_open = loc_open >= flatten_local or to_utc(c.open_time) >= hold_deadline
        if past_open:
            pts = fav_px(c.open)
            return (
                "flatten",
                c.open_time,
                c.open,
                pts,
                trail_armed,
                max_fav,
                max_adv,
                best_px,
                worst_px,
                be_armed,
            )

        fav = fav_px(extreme_fav)
        adv = adv_px(extreme_adv)
        if fav > max_fav:
            max_fav = fav
            best_px = extreme_fav
        if adv > max_adv:
            max_adv = adv
            worst_px = extreme_adv

        if (not be_armed) and be_arm > 0 and fav + 1e-12 >= be_arm:
            be_armed = True
            sl_now = entry

        if (not trail_from_fill) and arm_pts > 0 and not trail_armed and fav >= arm_pts and gap > 0:
            trail_armed = True
            if side == "UP":
                trail_level = best_px - gap * ps
            else:
                trail_level = best_px + gap * ps
        elif trail_armed and trail_level is not None and gap > 0:
            if side == "UP":
                new_trail = best_px - gap * ps
                if new_trail > trail_level:
                    trail_level = new_trail
            else:
                new_trail = best_px + gap * ps
                if new_trail < trail_level:
                    trail_level = new_trail

        stop = sl_now
        stop_reason = "be" if be_armed else "sl"
        if trail_armed and trail_level is not None and gap > 0:
            if side == "UP" and trail_level > stop:
                stop, stop_reason = trail_level, "trail"
            elif side == "DOWN" and trail_level < stop:
                stop, stop_reason = trail_level, "trail"
        if _hit_level(side, extreme_adv, stop, is_sl=True):
            pts = fav_px(stop)
            return (
                stop_reason,
                c.open_time,
                stop,
                pts,
                trail_armed,
                max_fav,
                max_adv,
                best_px,
                worst_px,
                be_armed,
            )
        if _hit_level(side, extreme_fav, tp, is_sl=False):
            pts = fav_px(tp)
            return "tp", c.open_time, tp, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed

        contains_flat = loc_open < flatten_local <= loc_close
        contains_hold = to_utc(c.open_time) < hold_deadline <= to_utc(c.close_time)
        if contains_flat or contains_hold:
            pts = fav_px(c.close)
            return (
                "flatten",
                c.close_time,
                c.close,
                pts,
                trail_armed,
                max_fav,
                max_adv,
                best_px,
                worst_px,
                be_armed,
            )

    pts = fav_px(last_px)
    return "timeout", last_ts, last_px, pts, trail_armed, max_fav, max_adv, best_px, worst_px, be_armed


def _excursion_from_candles(
    candles: Sequence[Candle],
    start_index: int,
    *,
    side: str,
    entry: float,
    ps: float,
    tz: ZoneInfo,
    flatten_local: datetime,
) -> Tuple[float, float, float, float]:
    max_fav = 0.0
    max_adv = 0.0
    best_px = entry
    worst_px = entry
    if start_index < 0 or start_index >= len(candles):
        return max_fav, max_adv, best_px, worst_px
    for i in range(start_index, len(candles)):
        c = candles[i]
        loc = _local(c.open_time, tz)
        if loc >= flatten_local:
            break
        extreme_fav = c.high if side == "UP" else c.low
        extreme_adv = c.low if side == "UP" else c.high
        fav = _fav_pts(side, entry, extreme_fav, ps)
        adv = _adv_pts(side, entry, extreme_adv, ps)
        if fav > max_fav:
            max_fav = fav
            best_px = extreme_fav
        if adv > max_adv:
            max_adv = adv
            worst_px = extreme_adv
        if _local(c.close_time, tz) >= flatten_local:
            break
    return max_fav, max_adv, best_px, worst_px


@dataclass
class _Fill:
    index: int
    ts: datetime
    px: float


class _TickFeed:
    def __init__(self, ticks: Sequence[Tick]):
        self.ticks = ticks
        self.n = len(ticks)

    def count(self) -> int:
        return self.n

    def find_index(self, ts: datetime) -> int:
        lo, hi = 0, self.n
        while lo < hi:
            mid = (lo + hi) // 2
            if self.ticks[mid].ts < ts:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def at_close(self, close_t: datetime, px: Optional[float] = None) -> Optional[_Fill]:
        i = self.find_index(close_t)
        if i >= self.n:
            return None
        return _Fill(i, self.ticks[i].ts, _mid(self.ticks[i]))

    def last_in_bar(self, open_t: datetime, close_t: datetime) -> Optional[_Fill]:
        close_i = self.find_index(close_t)
        fill_i = close_i - 1
        if fill_i < 0 or fill_i >= self.n or self.ticks[fill_i].ts < open_t:
            return None
        return _Fill(fill_i, self.ticks[fill_i].ts, _mid(self.ticks[fill_i]))

    def ema_scan(
        self,
        open_t: datetime,
        close_t: datetime,
        side: str,
        ema: float,
        ps: float,
    ) -> Tuple[bool, Optional[_Fill], Optional[float]]:
        c_start = self.find_index(open_t)
        c_end = self.find_index(close_t)
        touched = False
        fill: Optional[_Fill] = None
        closest: Optional[float] = None
        for ti in range(c_start, min(c_end + 1, self.n)):
            px = _mid(self.ticks[ti])
            if side == "UP":
                dist = (px - ema) / ps
                if px <= ema + 1e-9:
                    touched = True
                    if fill is None:
                        fill = _Fill(ti, self.ticks[ti].ts, px)
            else:
                dist = (ema - px) / ps
                if px >= ema - 1e-9:
                    touched = True
                    if fill is None:
                        fill = _Fill(ti, self.ticks[ti].ts, px)
            if closest is None or dist < closest:
                closest = dist
        return touched, fill, closest

    def simulate(self, start_index: int, **kwargs: Any):
        return _simulate_from_entry(self.ticks, start_index, **kwargs)

    def excursion(self, start_index: int, **kwargs: Any):
        return _excursion_from(self.ticks, start_index, **kwargs)

    def daily_closes(self, tz_name: str):
        return build_daily_closes(self.ticks, tz_name)


class _CandleFeed:
    def __init__(self, candles: Sequence[Candle]):
        self.candles = list(candles)
        self.n = len(self.candles)
        self._opens = [to_utc(c.open_time) for c in self.candles]

    def count(self) -> int:
        return self.n

    def find_index(self, ts: datetime) -> int:
        return bisect_left(self._opens, to_utc(ts))

    def at_close(self, close_t: datetime, px: Optional[float] = None) -> Optional[_Fill]:
        i = self.find_index(close_t)
        if i >= self.n:
            return None
        use = float(px) if px is not None else self.candles[i].open
        return _Fill(i, self.candles[i].open_time, use)

    def last_in_bar(self, open_t: datetime, close_t: datetime) -> Optional[_Fill]:
        end_i = self.find_index(close_t)
        fill_i = end_i - 1
        if fill_i < 0 or fill_i >= self.n:
            return None
        if to_utc(self.candles[fill_i].open_time) < to_utc(open_t):
            return None
        c = self.candles[fill_i]
        return _Fill(fill_i, c.close_time, c.close)

    def ema_scan(
        self,
        open_t: datetime,
        close_t: datetime,
        side: str,
        ema: float,
        ps: float,
    ) -> Tuple[bool, Optional[_Fill], Optional[float]]:
        i0 = self.find_index(open_t)
        i1 = self.find_index(close_t)
        closest: Optional[float] = None
        fill: Optional[_Fill] = None
        for i in range(i0, i1):
            hit, ts, px, bar_closest = _ema_touch_from_candle(
                self.candles[i], side=side, ema=ema, ps=ps
            )
            if bar_closest is not None and (closest is None or bar_closest < closest):
                closest = bar_closest
            if hit and fill is None and ts is not None and px is not None:
                fill = _Fill(i, ts, px)
        return fill is not None, fill, closest

    def simulate(self, start_index: int, **kwargs: Any):
        return _simulate_from_candles(self.candles, start_index, **kwargs)

    def excursion(self, start_index: int, **kwargs: Any):
        return _excursion_from_candles(self.candles, start_index, **kwargs)

    def daily_closes(self, tz_name: str):
        return build_daily_closes_from_candles(self.candles, tz_name)


def run_overnight(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[OvernightParams] = None,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    params = _normalize_params(params or OvernightParams())
    tz = require_zone(params.timezone)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return _empty_result(params, symbol=sym, ticks=len(ticks or []))

    builder = CandleBuilder(timeframe_minutes=15, max_completed=200, skip_ignored=False)
    completed: List[Candle] = []

    n_ticks = len(ticks)
    candle_step = max(n_ticks // 40, 80_000)
    for i, t in enumerate(ticks):
        closed = builder.add_price(_mid(t), t.ts)
        if closed is not None:
            completed.append(closed)
        if (
            progress
            and n_ticks > 80_000
            and ((i + 1) % candle_step == 0 or i + 1 == n_ticks)
        ):
            import time

            time.sleep(0.001)
            progress(
                phase="candles",
                ticks_done=i + 1,
                ticks_total=n_ticks,
                message=f"15m candles {i + 1:,}/{n_ticks:,}",
            )

    return _run_overnight_days(
        completed,
        _TickFeed(ticks),
        params=params,
        tz=tz,
        symbol=sym,
        ps=ps,
        progress=progress,
        data_source="ticks",
    )


def run_overnight_on_candles(
    candles_5m: Sequence[Candle],
    *,
    symbol: str = "XAU/USD",
    params: Optional[OvernightParams] = None,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    params = _normalize_params(params or OvernightParams())
    tz = require_zone(params.timezone)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not candles_5m:
        out = _empty_result(params, symbol=sym, ticks=len(candles_5m or []))
        out["data_source"] = "candles_5m"
        return out
    completed = aggregate_tf(candles_5m, 15)
    if progress:
        progress(
            phase="candles",
            message=f"5m→15m {len(completed):,} bars from {len(candles_5m):,} 5m",
            ticks_done=len(candles_5m),
            ticks_total=len(candles_5m),
        )
    return _run_overnight_days(
        completed,
        _CandleFeed(candles_5m),
        params=params,
        tz=tz,
        symbol=sym,
        ps=ps,
        progress=progress,
        data_source="candles_5m",
    )


def _run_overnight_days(
    completed: List[Candle],
    feed: Any,
    *,
    params: OvernightParams,
    tz: ZoneInfo,
    symbol: str,
    ps: float,
    progress: Optional[Callable[..., None]],
    data_source: str,
) -> Dict[str, Any]:
    n = feed.n

    # Group completed candles by local date
    by_day: Dict[date, List[Candle]] = {}
    for c in completed:
        d = _local(c.open_time, tz).date()
        by_day.setdefault(d, []).append(c)

    trades: List[OvernightTrade] = []
    skips: List[OvernightSkip] = []
    traded_days: set = set()
    use_season = params.seasonal_mode != "off"
    use_week2 = params.week2_mode != "off"
    need_m12 = uses_m12(params)
    dailies = (
        feed.daily_closes(params.timezone) if (use_week2 or need_m12) else []
    )
    m12_cache: Dict[Tuple[int, int], Optional[float]] = {}

    def m12_for(d: date) -> Optional[float]:
        key = (int(d.year), int(d.month))
        if key not in m12_cache:
            m12_cache[key] = m12_avg_pts(dailies, d, ps)
        return m12_cache[key]

    def day_bias(d: date):
        if not use_season and not use_week2:
            return None
        return snapshot_bias(
            d,
            dailies=dailies,
            use_season=use_season,
            use_week2=use_week2,
            season_filter=params.seasonal_mode == "filter",
            week2_filter=params.week2_mode == "filter",
            flat_pts=params.trend_flat_pts,
            sessions=params.trend_sessions,
            efficiency_min=params.trend_efficiency_min,
            ps=ps,
        )

    def stamp_bias(snap) -> Dict[str, Any]:
        if snap is None:
            return {}
        return {
            "seasonal_regime": snap.season_regime if use_season else None,
            "seasonal_label": snap.season_label if use_season else None,
            "trend_state": snap.trend_state if use_week2 else None,
            "trend_side": snap.trend_side if use_week2 else None,
            "trend_move_pts": snap.trend_move_pts if use_week2 else None,
            "bias_conflict": bool(snap.conflict),
            "bias_side": snap.filter_side,
        }

    dates = sorted(by_day.keys())
    open_times = [c.open_time for c in completed]
    closes = [c.close for c in completed]
    n_days = len(dates)

    for di, day in enumerate(dates):
        if progress and (di % 5 == 0 or di + 1 == n_days):
            progress(
                phase="replay",
                days_done=di + 1,
                days_total=n_days,
                trades=len(trades),
                message=f"Day {day.isoformat()} · {len(trades)} trades",
            )
        if params.one_trade_per_day and day in traded_days:
            continue

        seasonal_mode = params.seasonal_mode
        regime = month_regime(day) if seasonal_mode != "off" else "neutral"
        regime_lbl = seasonal_label(regime, day) if seasonal_mode != "off" else None
        bias_snap = day_bias(day)
        bias_kw = stamp_bias(bias_snap)
        news_mode = params.news_mode
        news_events = (
            events_on(day, kinds=kinds_for_set(params.news_set))
            if news_mode != "off"
            else []
        )
        news_kind, news_title = format_news(news_events)
        news_kw = (
            {"news_kind": news_kind, "news_title": news_title}
            if news_mode != "off" and news_events
            else {}
        )
        day_kw = {**bias_kw, **news_kw}
        if news_mode == "filter" and news_events:
            skips.append(
                _mk_skip(
                    day,
                    "news_day",
                    detail=news_title,
                    **day_kw,
                )
            )
            continue

        day_candles = by_day[day]
        if not day_candles:
            skips.append(
                _mk_skip(
                    day,
                    "no_candles",
                    **day_kw,
                )
            )
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
                _mk_skip(
                    day,
                    "thin_asia",
                    detail=f"{len(asia_candles)} candles",
                    **day_kw,
                )
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
                    **day_kw,
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

        wick_break = _use_wick_break(params)
        for c in post_asia:
            if not c.is_closed:
                continue
            if wick_break:
                up_break = c.high >= asia_high + params.min_break_pts_above * ps
                dn_break = c.low <= asia_low - params.min_break_pts_below * ps
            else:
                up_break = c.close >= asia_high + params.min_break_pts_above * ps
                dn_break = c.close <= asia_low - params.min_break_pts_below * ps
            if up_break:
                break_candle, side = c, "UP"
                break
            if dn_break:
                break_candle, side = c, "DOWN"
                break

        above_asia, below_asia = _asia_extensions(after_asia, asia_high, asia_low, ps)

        def skip_break(reason: str, **extra: Any) -> OvernightSkip:
            for k, v in day_kw.items():
                extra.setdefault(k, v)
            fav = adv = fav_px = adv_px = None
            bp = extra.get("break_pts")
            if break_candle is not None and side is not None:
                ref = break_candle.close
                br_fill = feed.at_close(break_candle.close_time, px=break_candle.close)
                if br_fill is not None:
                    fav, adv, fav_px, adv_px = feed.excursion(
                        br_fill.index,
                        side=side,
                        entry=ref,
                        ps=ps,
                        tz=tz,
                        flatten_local=flatten_local,
                    )
                if bp is None:
                    bp = _break_pts_for(
                        side,
                        break_candle,
                        asia_high,
                        asia_low,
                        ps,
                        wick=wick_break,
                    )
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
                    resume_closes=int(extra.get("resume_closes") or _resume_need(params)),
                    resume_streak=extra.get("resume_streak"),
                )
            waited = extra.pop("waited", None)
            extra.pop("break_pts", None)
            extra.pop("resume_closes", None)
            extra.pop("resume_streak", None)
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

        seasonal_join = False
        if break_candle is None or side is None:
            join_side = None
            if bool(params.seasonal_join) and (seasonal_mode != "off" or params.week2_mode != "off"):
                if bias_snap is not None and not bias_snap.conflict:
                    join_side = bias_snap.filter_side
                elif seasonal_mode != "off":
                    join_side = bias_side(regime)
            if join_side is None:
                skips.append(
                    _mk_skip(
                        day,
                        "no_break",
                        asia_high=asia_high,
                        asia_low=asia_low,
                        asia_range_pts=asia_range_pts,
                        max_above_asia_pts=above_asia,
                        max_below_asia_pts=below_asia,
                        **day_kw,
                    )
                )
                continue
            if params.side_filter == "long" and join_side != "UP":
                skips.append(
                    _mk_skip(
                        day,
                        "side_filter",
                        side=join_side,
                        asia_high=asia_high,
                        asia_low=asia_low,
                        asia_range_pts=asia_range_pts,
                        max_above_asia_pts=above_asia,
                        max_below_asia_pts=below_asia,
                        **day_kw,
                    )
                )
                continue
            if params.side_filter == "short" and join_side != "DOWN":
                skips.append(
                    _mk_skip(
                        day,
                        "side_filter",
                        side=join_side,
                        asia_high=asia_high,
                        asia_low=asia_low,
                        asia_range_pts=asia_range_pts,
                        max_above_asia_pts=above_asia,
                        max_below_asia_pts=below_asia,
                        **day_kw,
                    )
                )
                continue
            side = join_side
            break_candle = post_asia[-1] if post_asia else asia_candles[-1]
            seasonal_join = True

        if (not seasonal_join) and (
            seasonal_mode == "filter" or params.week2_mode == "filter"
        ):
            filt = (
                bias_snap.filter_side
                if bias_snap is not None
                else (bias_side(regime) if seasonal_mode == "filter" else None)
            )
            if filt and side != filt:
                skips.append(skip_break("seasonal_bias"))
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
        close_fill = feed.at_close(break_candle.close_time, px=break_candle.close)
        entry_idx = close_fill.index if close_fill is not None else n
        break_pts = (
            0.0
            if seasonal_join
            else _break_pts_for(
                side,
                break_candle,
                asia_high,
                asia_low,
                ps,
                wick=wick_break,
            )
        )

        wait_i: Optional[int] = 0
        wait_n: Optional[int] = None
        last_wait_pullback_pts: Optional[float] = None
        ema_at: Optional[float] = None
        prev_at: Optional[float] = None
        sig_close: Optional[float] = None
        same_bar_ema = False
        closest_ema_pts: Optional[float] = None
        best_resume_pts: Optional[float] = None
        waited = 0

        if seasonal_join:
            if close_fill is None:
                skips.append(skip_break("no_entry_tick", break_pts=break_pts))
                continue
            entry_ts = close_fill.ts
            entry_px = close_fill.px
            entry_idx = close_fill.index
            entry_reason = "seasonal_join"
            wait_i = 0
            wait_n = 0
        elif params.pullback_mode == "off":
            # Enter at break candle close (or first tick after)
            if close_fill is None:
                skips.append(skip_break("no_entry_tick", break_pts=break_pts))
                continue
            entry_ts = close_fill.ts
            entry_px = close_fill.px
            entry_idx = close_fill.index
            entry_reason = "break_close"
            wait_i = 0
            wait_n = 0
        else:
            wait_src = after_asia if params.wait_from_break else post_asia
            try:
                br_i = wait_src.index(break_candle)
            except ValueError:
                br_i = post_asia.index(break_candle)
                wait_src = post_asia
            wait_candles = wait_src[
                br_i + 1 : br_i + 1 + params.max_wait_candles
            ]
            if params.wait_from_break:
                wait_candles = [
                    c for c in wait_candles if _local(c.open_time, tz) < flatten_local
                ]
            wait_n = len(wait_candles)
            if wait_candles:
                last_close = wait_candles[-1].close
                if side == "UP":
                    last_wait_pullback_pts = (break_candle.close - last_close) / ps
                else:
                    last_wait_pullback_pts = (last_close - break_candle.close) / ps
            found = False
            blocked_late_short = False
            ema_val: Optional[float] = None
            resume_need = _resume_need(params)
            resume_streak = 0

            for wi, wc in enumerate(wait_candles, start=1):
                waited = wi
                ci = bisect_left(open_times, wc.open_time)
                ema_slice = closes[max(0, ci - params.ema_period * 2) : ci]
                ema_val = _ema(ema_slice, params.ema_period)
                prev_close = closes[ci - 1] if ci else None

                resume_hit = False
                resume_pts: Optional[float] = None
                if _resume_enabled(params) and prev_close is not None:
                    if side == "UP":
                        resume_pts = (wc.close - prev_close) / ps
                        directional = wc.close > prev_close + 1e-12
                    else:
                        resume_pts = (prev_close - wc.close) / ps
                        directional = wc.close < prev_close - 1e-12
                    resume_streak = resume_streak + 1 if directional else 0
                    resume_hit = resume_streak >= resume_need
                    if resume_hit and resume_too_far_from_break(
                        params, side, wc.close, break_candle.close, ps
                    ):
                        resume_hit = False
                    if best_resume_pts is None or resume_pts > best_resume_pts:
                        best_resume_pts = resume_pts
                else:
                    resume_streak = 0

                level_px = ema_val
                if params.pullback_ref == "fib":
                    level_px = trade_fib_px(
                        asia_high, asia_low, side, params.pullback_fib
                    )
                ema_touched = False
                ema_fill: Optional[_Fill] = None
                if level_px is not None:
                    ema_touched, ema_fill, bar_closest = feed.ema_scan(
                        wc.open_time, wc.close_time, side, level_px, ps
                    )
                    if bar_closest is not None and (
                        closest_ema_pts is None or bar_closest < closest_ema_pts
                    ):
                        closest_ema_pts = bar_closest

                late_block = late_short_blocked(
                    params, side, wi, asia_range_pts
                )
                if late_block and (resume_hit or ema_touched):
                    blocked_late_short = True

                if resume_hit and not late_block:
                    resume_fill = feed.at_close(wc.close_time, px=wc.close)
                    if resume_fill is not None:
                        entry_ts = resume_fill.ts
                        entry_px = resume_fill.px
                        entry_reason = (
                            "higher_close" if side == "UP" else "lower_close"
                        )
                        entry_idx = resume_fill.index
                        wait_i = wi
                        ema_at = ema_val
                        prev_at = prev_close
                        sig_close = wc.close
                        same_bar_ema = ema_touched
                        found = True
                        break

                if ema_touched and ema_fill is not None and not late_block:
                    entry_ts = ema_fill.ts
                    entry_px = ema_fill.px
                    entry_reason = (
                        "fib_touch" if params.pullback_ref == "fib" else "ema_touch"
                    )
                    entry_idx = ema_fill.index
                    wait_i = wi
                    ema_at = level_px if params.pullback_ref == "fib" else ema_val
                    prev_at = prev_close
                    sig_close = wc.close
                    found = True
                    break

            skip_diag = dict(
                wait_n=wait_n,
                waited=waited,
                ema=ema_val if wait_candles else None,
                closest_ema_pts=closest_ema_pts,
                last_wait_pullback_pts=last_wait_pullback_pts,
                best_resume_pts=best_resume_pts,
                break_pts=break_pts,
                resume_closes=resume_need,
                resume_streak=resume_streak,
            )

            if not found:
                if blocked_late_short:
                    skips.append(skip_break("late_short", **skip_diag))
                    continue
                if params.pullback_mode == "required":
                    # elif below: a near-box fill must not fall through into
                    # preferred timeout skip/market and get discarded or replaced.
                    if (
                        near_box_hug(
                            params,
                            side,
                            wait_candles,
                            asia_high,
                            asia_low,
                            ps,
                        )
                        and wait_candles
                    ):
                        last_wait = wait_candles[-1]
                        timeout_fill = feed.last_in_bar(
                            last_wait.open_time, last_wait.close_time
                        )
                        if timeout_fill is None:
                            skips.append(skip_break("no_entry_tick", **skip_diag))
                            continue
                        entry_idx = timeout_fill.index
                        entry_px = last_wait.close
                        entry_reason = "near_box_timeout"
                        entry_ts = timeout_fill.ts
                        wait_i = waited
                        ema_at = skip_diag["ema"]
                        sig_close = last_wait.close
                    else:
                        skips.append(skip_break("no_pullback", **skip_diag))
                        continue
                elif params.timeout_action == "skip":
                    skips.append(skip_break("no_pullback_timeout", **skip_diag))
                    continue
                elif timeout_quality_blocked(
                    params,
                    closest_ema_pts=closest_ema_pts,
                    break_pts=break_pts,
                    last_wait_pullback_pts=last_wait_pullback_pts,
                ):
                    skips.append(skip_break("no_pullback_timeout", **skip_diag))
                    continue
                elif not wait_candles:
                    skips.append(skip_break("no_pullback_timeout", **skip_diag))
                    continue
                else:
                    last_wait = wait_candles[-1]
                    timeout_fill = feed.last_in_bar(
                        last_wait.open_time, last_wait.close_time
                    )
                    if timeout_fill is None:
                        skips.append(skip_break("no_entry_tick", **skip_diag))
                        continue
                    entry_idx = timeout_fill.index
                    entry_px = last_wait.close
                    entry_reason = "timeout_market"
                    entry_ts = timeout_fill.ts
                    wait_i = waited
                    ema_at = skip_diag["ema"]
                    sig_close = last_wait.close

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
            resume_closes=_resume_need(params),
            pullback_ref=params.pullback_ref,
            pullback_fib=float(params.pullback_fib),
        )
        note = bias_snap.decision_note() if bias_snap is not None else regime_lbl
        if note:
            decision = (decision + " · " if decision else "") + note

        m12_raw = m12_for(day) if need_m12 else None
        if need_m12 and (m12_raw is None or m12_raw <= 0):
            skips.append(skip_break("no_m12"))
            continue
        sl, tp, sl_pts, tp_pts = _compute_sl_tp(
            side,
            entry_px,
            asia_high,
            asia_low,
            params,
            ps,
            m12_pts=m12_raw,
        )
        trail_arm_used, trail_dist_used, trail_from_fill = trail_setup(
            params, asia_range_pts, sl_pts
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
            _sim_fav,
            _sim_adv,
            _sim_best,
            _sim_worst,
            be_armed,
        ) = feed.simulate(
            entry_idx,
            side=side,
            entry=entry_px,
            sl=sl,
            tp=tp,
            params=params,
            ps=ps,
            tz=tz,
            flatten_local=flatten_local,
            trail_arm_pts=trail_arm_used,
            trail_dist_pts=trail_dist_used,
            trail_from_fill=trail_from_fill,
        )
        max_fav, max_adv, best_px, worst_px = feed.excursion(
            entry_idx,
            side=side,
            entry=entry_px,
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
                closest_ema_pts=_round_or_none(closest_ema_pts, 1),
                last_wait_pullback_pts=_round_or_none(last_wait_pullback_pts, 1),
                close_vs_prev_pts=_round_or_none(close_vs_prev_pts, 1),
                same_bar_ema=same_bar_ema,
                decision=decision,
                sl=round(sl, 5),
                tp=round(tp, 5),
                sl_pts=round(sl_pts, 1),
                tp_pts=round(tp_pts, 1),
                m12_pts=_round_or_none(round_pts_up(m12_raw) if m12_raw else None, 1),
                exit_ts=exit_ts.isoformat() if exit_ts else None,
                exit=round(exit_px, 5),
                exit_reason=reason,
                pts=round(pts, 1),
                trail_arm_used=round(trail_arm_used, 1),
                trail_armed=trail_armed,
                be_armed=bool(be_armed),
                max_fav_pts=round(max_fav, 1),
                max_adv_pts=round(max_adv, 1),
                max_fav_price=round(best_px, 5),
                max_adv_price=round(worst_px, 5),
                seasonal_regime=bias_kw.get("seasonal_regime"),
                seasonal_label=bias_kw.get("seasonal_label"),
                trend_state=bias_kw.get("trend_state"),
                trend_side=bias_kw.get("trend_side"),
                trend_move_pts=bias_kw.get("trend_move_pts"),
                bias_conflict=bool(bias_kw.get("bias_conflict")),
                bias_side=bias_kw.get("bias_side"),
                news_kind=day_kw.get("news_kind"),
                news_title=day_kw.get("news_title"),
            )
        )
        if (
            params.reentry_enabled
            and reason == "sl"
            and exit_ts is not None
            and float(params.reentry_sl_pts) > 0
            and float(params.reentry_tp_pts) > 0
        ):
            signal = reentry_signal_candle(
                day_candles,
                after=exit_ts,
                side=side,
                entry=entry_px,
                need=params.reentry_closes,
                tz=tz,
                flatten_local=flatten_local,
            )
            fill2 = (
                feed.at_close(signal.close_time, px=signal.close)
                if signal is not None
                else None
            )
            if fill2 is not None and _local(fill2.ts, tz) < flatten_local:
                sl2_pts = float(params.reentry_sl_pts)
                tp2_pts = float(params.reentry_tp_pts)
                if side == "UP":
                    sl2 = fill2.px - sl2_pts * ps
                    tp2 = fill2.px + tp2_pts * ps
                else:
                    sl2 = fill2.px + sl2_pts * ps
                    tp2 = fill2.px - tp2_pts * ps
                (
                    reason2,
                    exit_ts2,
                    exit_px2,
                    pts2,
                    trail2,
                    _f2,
                    _a2,
                    _b2,
                    _w2,
                    be2,
                ) = feed.simulate(
                    fill2.index,
                    side=side,
                    entry=fill2.px,
                    sl=sl2,
                    tp=tp2,
                    params=params,
                    ps=ps,
                    tz=tz,
                    flatten_local=flatten_local,
                    trail_arm_pts=0.0,
                    trail_dist_pts=0.0,
                    trail_from_fill=False,
                    be_arm_override=0.0,
                )
                fav2, adv2, best2, worst2 = feed.excursion(
                    fill2.index,
                    side=side,
                    entry=fill2.px,
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
                        entry_ts=fill2.ts.isoformat(),
                        entry=round(fill2.px, 5),
                        entry_reason="reentry",
                        entry_label=entry_label("reentry"),
                        wait_i=int(params.reentry_closes),
                        wait_n=int(params.reentry_closes),
                        signal_close=round(signal.close, 5) if signal else None,
                        break_pts=_round_or_none(break_pts, 1),
                        decision=(
                            f"Second trade · {int(params.reentry_closes)} close"
                            f"{'' if int(params.reentry_closes) == 1 else 's'} back through "
                            f"{_fmt_px(entry_px)} · SL {sl2_pts:.0f} · TP {tp2_pts:.0f}"
                        ),
                        sl=round(sl2, 5),
                        tp=round(tp2, 5),
                        sl_pts=round(sl2_pts, 1),
                        tp_pts=round(tp2_pts, 1),
                        exit_ts=exit_ts2.isoformat() if exit_ts2 else None,
                        exit=round(exit_px2, 5),
                        exit_reason=reason2,
                        pts=round(pts2, 1),
                        trail_arm_used=0.0,
                        trail_armed=bool(trail2),
                        be_armed=bool(be2),
                        max_fav_pts=round(fav2, 1),
                        max_adv_pts=round(adv2, 1),
                        max_fav_price=round(best2, 5),
                        max_adv_price=round(worst2, 5),
                        seasonal_regime=bias_kw.get("seasonal_regime"),
                        seasonal_label=bias_kw.get("seasonal_label"),
                        trend_state=bias_kw.get("trend_state"),
                        trend_side=bias_kw.get("trend_side"),
                        trend_move_pts=bias_kw.get("trend_move_pts"),
                        bias_conflict=bool(bias_kw.get("bias_conflict")),
                        bias_side=bias_kw.get("bias_side"),
                        news_kind=day_kw.get("news_kind"),
                        news_title=day_kw.get("news_title"),
                    )
                )
        traded_days.add(day)

    return summarize_overnight(
        trades,
        skips,
        params,
        symbol=symbol,
        ticks=feed.count(),
        data_source=data_source,
    )


def _month_key(local_date: Optional[str]) -> str:
    s = str(local_date or "")
    return s[:7] if len(s) >= 7 else "unknown"


def _pct(a: int, b: int) -> Optional[float]:
    if b <= 0:
        return None
    return round(100.0 * a / b, 1)


def _trade_stats(
    trades: Sequence[OvernightTrade], *, with_reentry: bool = True
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
    be_n = sum(1 for t in trades if t.be_armed)
    out = {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "scratches": scratches,
        "win_pct": _pct(wins, n),
        "exits": by_reason,
        "entries": by_entry,
        "trail_armed_n": trail_n,
        "trail_armed_pct": _pct(trail_n, n),
        "be_armed_n": be_n,
        "be_armed_pct": _pct(be_n, n),
        "avg_pts": avg_pts,
        "avg_win_pts": avg_win,
        "avg_loss_pts": avg_loss,
        "profit_factor": pf,
        "sum_pts": round(sum(t.pts for t in trades), 1),
    }
    if with_reentry:
        second = [t for t in trades if t.entry_reason == "reentry"]
        out["reentry"] = _trade_stats(second, with_reentry=False)
    return out


def _streak_kind(pts: float) -> Optional[str]:
    if pts > 1e-9:
        return "win"
    if pts < -1e-9:
        return "loss"
    return None


def _streak_stats(trades: Sequence[OvernightTrade]) -> Dict[str, Any]:
    """Consecutive wins/losses in local_date order. Scratch (0 pts) breaks a streak."""
    ordered = sorted(
        trades,
        key=lambda t: (str(t.local_date or ""), str(t.entry_ts or "")),
    )
    win_by_len: Dict[int, int] = defaultdict(int)
    loss_by_len: Dict[int, int] = defaultdict(int)
    max_win = 0
    max_loss = 0
    cur_side: Optional[str] = None
    cur_len = 0

    def close_run() -> None:
        nonlocal max_win, max_loss
        if cur_side == "win" and cur_len:
            win_by_len[cur_len] += 1
            if cur_len > max_win:
                max_win = cur_len
        elif cur_side == "loss" and cur_len:
            loss_by_len[cur_len] += 1
            if cur_len > max_loss:
                max_loss = cur_len

    for t in ordered:
        kind = _streak_kind(float(t.pts or 0.0))
        if kind is None:
            close_run()
            cur_side = None
            cur_len = 0
            continue
        if kind == cur_side:
            cur_len += 1
        else:
            close_run()
            cur_side = kind
            cur_len = 1
    close_run()
    current = None
    if cur_side and cur_len:
        current = {"side": cur_side, "len": cur_len}
    return {
        "max_win": max_win,
        "max_loss": max_loss,
        "win_streaks": int(sum(win_by_len.values())),
        "loss_streaks": int(sum(loss_by_len.values())),
        "win_by_len": {int(k): int(v) for k, v in sorted(win_by_len.items())},
        "loss_by_len": {int(k): int(v) for k, v in sorted(loss_by_len.items())},
        "current": current,
    }


def _skip_reason_counts(skips: Sequence[OvernightSkip]) -> Dict[str, int]:
    skip_reasons: Dict[str, int] = {}
    for s in skips:
        skip_reasons[s.reason] = skip_reasons.get(s.reason, 0) + 1
    return skip_reasons


def _month_summaries(
    trades: Sequence[OvernightTrade],
    skips: Sequence[OvernightSkip],
) -> List[Dict[str, Any]]:
    by_tr: Dict[str, List[OvernightTrade]] = defaultdict(list)
    by_sk: Dict[str, List[OvernightSkip]] = defaultdict(list)
    for t in trades:
        by_tr[_month_key(t.local_date)].append(t)
    for s in skips:
        by_sk[_month_key(s.local_date)].append(s)
    months = sorted(set(by_tr) | set(by_sk))
    rows: List[Dict[str, Any]] = []
    for ym in months:
        m_trades = by_tr.get(ym) or []
        m_skips = by_sk.get(ym) or []
        row = _trade_stats(m_trades)
        row["month"] = ym
        row["skipped"] = len(m_skips)
        row["skip_reasons"] = _skip_reason_counts(m_skips)
        rows.append(row)
    return rows


def summarize_overnight(
    trades: Sequence[OvernightTrade],
    skips: Sequence[OvernightSkip],
    params: OvernightParams,
    *,
    symbol: str,
    ticks: int,
    data_source: str = "ticks",
) -> Dict[str, Any]:
    n = len(trades)
    stats = _trade_stats(trades)
    skip_reasons = _skip_reason_counts(skips)
    return {
        "kind": "overnight_break",
        "symbol": symbol,
        "params": asdict(params),
        "data_source": data_source,
        "ticks": ticks,
        "days_seen": n + len(skips),
        "skipped": len(skips),
        "skip_reasons": skip_reasons,
        **stats,
        "streaks": _streak_stats(trades),
        "by_month": _month_summaries(trades, skips),
        "rows": [asdict(t) for t in trades],
        "skips": [asdict(s) for s in skips],
    }


def _empty_result(
    params: OvernightParams,
    *,
    symbol: str,
    ticks: int,
    data_source: str = "ticks",
) -> Dict[str, Any]:
    return summarize_overnight(
        [], [], params, symbol=symbol, ticks=ticks, data_source=data_source
    )
