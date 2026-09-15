"""
Dual-Mode Asia Liquidity Engine (pure — no web, no MT5).

UTC (default) or Moldova (Europe/Chisinau) Asia box, locked at 07:00 local.
Execution clock defaults to UTC London hours so a Moldova lock still waits
for London. Mode A = continuation close-through. Mode B = sweep and reclaim.
One setup per symbol per session date. No extra oscillators.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from statistics import median
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import Candle, CandleBuilder, aggregate_tf, to_utc
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.news_calendar import (
    events_on,
    format_news,
    kinds_for_set,
    normalize_news_mode,
    normalize_news_set,
)

TZ_UTC = "UTC"
TZ_MOLDOVA = "Europe/Chisinau"
_MOLDOVA_ALIASES = {
    "moldova",
    "chisinau",
    "europe/chisinau",
    "europe/bucharest",  # same offset; Moldova is the labelled preset
}


@dataclass
class AsiaLiqParams:
    timezone: str = TZ_UTC  # box clock: UTC | Europe/Chisinau
    exec_timezone: str = TZ_UTC  # signal / Mode B / flatten clock
    asia_start_hour: int = 0
    asia_end_hour: int = 7
    asia_end_minute: int = 0
    london_wait_minutes: int = 30
    signal_start_hour: int = 7
    signal_end_hour: int = 11
    mode_b_end_hour: int = 9
    mode_b_end_minute: int = 30
    flatten_hour: int = 16
    # Filters
    atr_period: int = 14
    box_atr_min: float = 0.25
    box_atr_max: float = 0.85
    compression_lookback: int = 20  # 0 = off
    htf_enabled: bool = True
    htf_ema_period: int = 50
    htf_tf_min: int = 240
    news_mode: str = "filter"  # off | tag | filter
    news_set: str = "scheduled"
    news_blackout_minutes: int = 60
    news_anchor_start_hour_utc: int = 7
    news_anchor_end_hour_utc: int = 8
    news_windows: List[str] = field(default_factory=list)  # "HH:MM-HH:MM" UTC
    spread_filter: bool = True
    spread_mult: float = 1.5
    # Mode A
    mode_a_enabled: bool = True
    break_buffer_atr: float = 0.1
    body_frac: float = 0.50
    min_range_atr: float = 0.6
    tp1_r: float = 1.0
    tp2_r: float = 1.8
    tp2_select: str = "nearer"  # nearer | farther
    be_offset_r: float = 0.1
    trail_swing_bars: int = 3
    # Mode B
    mode_b_enabled: bool = True
    sweep_buffer_atr: float = 0.15
    reclaim_bars: int = 4
    mode_b_confirm: bool = True
    sweep_stop_atr: float = 0.1
    # Risk
    risk_pct: float = 0.5
    start_equity: float = 1_000.0
    daily_halt_r: float = 1.5
    weekly_halt_r: float = 4.0
    one_trade_per_day: bool = True


@dataclass
class AsiaLiqTrade:
    local_date: str
    mode: str  # A | B
    side: str  # UP | DOWN
    asia_high: float
    asia_low: float
    asia_mid: float
    box_height: float
    box_height_pts: float
    atr: float
    htf_side: Optional[str]
    entry_ts: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    sl_pts: float
    entry_reason: str
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None
    pts: float = 0.0
    r: float = 0.0
    tp1_hit: bool = False
    trail_used: bool = False
    max_fav_pts: float = 0.0
    max_adv_pts: float = 0.0
    box_atr_ratio: Optional[float] = None
    news_kind: Optional[str] = None
    news_title: Optional[str] = None
    size: float = 0.0
    equity_after: Optional[float] = None


@dataclass
class AsiaLiqSkip:
    local_date: str
    reason: str
    asia_high: Optional[float] = None
    asia_low: Optional[float] = None
    box_height: Optional[float] = None
    atr: Optional[float] = None
    htf_side: Optional[str] = None
    detail: Optional[str] = None
    news_kind: Optional[str] = None
    news_title: Optional[str] = None


@dataclass
class AsiaLiqSetup:
    session_date: date
    mode: str
    side: str
    signal: Candle
    entry: float
    sl: float
    tp1: float
    tp2: float
    asia_high: float
    asia_low: float
    asia_mid: float
    box_height: float
    atr: float
    htf_side: Optional[str]
    reason: str
    sweep_wick: Optional[float] = None


def require_zone(name: str) -> ZoneInfo:
    key = (name or "").strip() or TZ_UTC
    if key.upper() in ("UTC", "GMT", "Z", "ETC/UTC"):
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(key)
    except Exception as e:
        raise RuntimeError(
            f"Timezone {key!r} is not available ({e}). "
            "Install tzdata: python -m pip install tzdata"
        ) from e


def normalize_box_timezone(name: Optional[str]) -> str:
    raw = (name or TZ_UTC).strip()
    low = raw.lower().replace(" ", "")
    if low in _MOLDOVA_ALIASES or low in ("eet", "eest"):
        return TZ_MOLDOVA
    if low in ("utc", "gmt", "z", "etc/utc"):
        return TZ_UTC
    return raw


def normalize_exec_timezone(name: Optional[str], box_tz: str) -> str:
    raw = (name or TZ_UTC).strip()
    low = raw.lower().replace(" ", "")
    if low in ("session", "box", "same", "local"):
        return box_tz
    if low in _MOLDOVA_ALIASES:
        return TZ_MOLDOVA
    if low in ("utc", "gmt", "z", "", "etc/utc"):
        return TZ_UTC
    return raw


def _normalize_params(params: AsiaLiqParams) -> AsiaLiqParams:
    params.timezone = normalize_box_timezone(params.timezone)
    params.exec_timezone = normalize_exec_timezone(
        params.exec_timezone, params.timezone
    )
    params.news_mode = normalize_news_mode(params.news_mode)
    params.news_set = normalize_news_set(params.news_set)
    sel = str(params.tp2_select or "nearer").strip().lower()
    params.tp2_select = "farther" if sel in ("farther", "max", "longer") else "nearer"
    params.london_wait_minutes = max(0, int(params.london_wait_minutes or 0))
    params.reclaim_bars = max(1, int(params.reclaim_bars or 4))
    params.trail_swing_bars = max(1, int(params.trail_swing_bars or 3))
    params.atr_period = max(1, int(params.atr_period or 14))
    params.htf_ema_period = max(2, int(params.htf_ema_period or 50))
    params.htf_tf_min = max(15, int(params.htf_tf_min or 240))
    params.compression_lookback = max(0, int(params.compression_lookback or 0))
    try:
        params.risk_pct = max(0.0, float(params.risk_pct or 0.0))
    except (TypeError, ValueError):
        params.risk_pct = 0.5
    if not isinstance(params.news_windows, list):
        params.news_windows = []
    return params


def _local(ts: datetime, tz: ZoneInfo) -> datetime:
    return to_utc(ts).astimezone(tz)


def _at_local(d: date, hour: int, minute: int, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time(int(hour) % 24, int(minute) % 60), tzinfo=tz)


def moldova_lock_utc(local_day: date) -> datetime:
    """07:00 Europe/Chisinau as UTC (04:00 in summer, 05:00 in winter)."""
    tz = require_zone(TZ_MOLDOVA)
    return _at_local(local_day, 7, 0, tz).astimezone(timezone.utc)


def session_bounds(
    local_day: date,
    params: AsiaLiqParams,
) -> Tuple[datetime, datetime, datetime, datetime, datetime, datetime]:
    """Return UTC instants: asia_start, lock, first_entry, signal_end, mode_b_end, flatten."""
    box_tz = require_zone(params.timezone)
    exec_tz = require_zone(params.exec_timezone)
    if int(params.asia_start_hour) > int(params.asia_end_hour):
        asia_day = local_day - timedelta(days=1)
    else:
        asia_day = local_day
    asia_start = _at_local(asia_day, params.asia_start_hour, 0, box_tz).astimezone(
        timezone.utc
    )
    lock = _at_local(
        local_day, params.asia_end_hour, params.asia_end_minute, box_tz
    ).astimezone(timezone.utc)
    signal_start = _at_local(
        local_day, params.signal_start_hour, 0, exec_tz
    ).astimezone(timezone.utc)
    first_entry = max(lock, signal_start) + timedelta(
        minutes=int(params.london_wait_minutes or 0)
    )
    signal_end = _at_local(
        local_day, params.signal_end_hour, 0, exec_tz
    ).astimezone(timezone.utc)
    mode_b_end = _at_local(
        local_day, params.mode_b_end_hour, params.mode_b_end_minute, exec_tz
    ).astimezone(timezone.utc)
    flatten = _at_local(local_day, params.flatten_hour, 0, exec_tz).astimezone(
        timezone.utc
    )
    return asia_start, lock, first_entry, signal_end, mode_b_end, flatten


def true_range(high: float, low: float, prev_close: Optional[float]) -> float:
    if prev_close is None:
        return max(0.0, high - low)
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def wilder_atr(candles: Sequence[Candle], period: int) -> List[Optional[float]]:
    """Wilder ATR aligned with `candles`. None until `period` TRs exist."""
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    if n == 0 or period < 1:
        return out
    trs: List[float] = []
    prev_c: Optional[float] = None
    atr: Optional[float] = None
    for i, c in enumerate(candles):
        tr = true_range(c.high, c.low, prev_c)
        trs.append(tr)
        prev_c = c.close
        if i + 1 < period:
            continue
        if atr is None:
            atr = sum(trs[:period]) / float(period)
        else:
            atr = (atr * (period - 1) + tr) / float(period)
        out[i] = atr
    return out


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


def _body_frac(c: Candle) -> float:
    rng = c.high - c.low
    if rng <= 1e-12:
        return 0.0
    return abs(c.close - c.open) / rng


def _candle_range(c: Candle) -> float:
    return max(0.0, c.high - c.low)


def mode_a_side(
    c: Candle,
    *,
    asia_high: float,
    asia_low: float,
    atr: float,
    params: AsiaLiqParams,
) -> Optional[str]:
    if atr <= 0:
        return None
    body_ok = _body_frac(c) + 1e-12 >= float(params.body_frac)
    range_ok = _candle_range(c) + 1e-12 >= float(params.min_range_atr) * atr
    if not body_ok or not range_ok:
        return None
    buf = float(params.break_buffer_atr) * atr
    if c.close > asia_high + buf:
        return "UP"
    if c.close < asia_low - buf:
        return "DOWN"
    return None


def close_inside(c: Candle, asia_high: float, asia_low: float) -> bool:
    return asia_low < c.close < asia_high


def _fav(side: str, entry: float, px: float, ps: float) -> float:
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _hit_stop(side: str, px: float, sl: float) -> bool:
    if side == "UP":
        return px <= sl + 1e-12
    return px >= sl - 1e-12


def _hit_tp(side: str, px: float, tp: float) -> bool:
    if side == "UP":
        return px >= tp - 1e-12
    return px <= tp + 1e-12


def mode_a_targets(
    side: str,
    entry: float,
    sl: float,
    box_height: float,
    params: AsiaLiqParams,
) -> Tuple[float, float]:
    r_dist = abs(entry - sl)
    tp1 = entry + r_dist * float(params.tp1_r) if side == "UP" else entry - r_dist * float(
        params.tp1_r
    )
    dist_r = r_dist * float(params.tp2_r)
    dist_box = abs(float(box_height))
    if str(params.tp2_select) == "farther":
        dist = max(dist_r, dist_box)
    else:
        dist = min(dist_r, dist_box) if dist_box > 0 else dist_r
    tp2 = entry + dist if side == "UP" else entry - dist
    return tp1, tp2


def mode_b_targets(
    side: str,
    asia_high: float,
    asia_low: float,
    asia_mid: float,
) -> Tuple[float, float]:
    if side == "DOWN":
        return asia_mid, asia_low
    return asia_mid, asia_high


def last_closed_htf(
    htf: Sequence[Candle],
    htf_ema: Sequence[Optional[float]],
    ts: datetime,
) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """HTF side, close, ema using the last bar closed at or before ts."""
    ts = to_utc(ts)
    chosen: Optional[int] = None
    for i in range(len(htf) - 1, -1, -1):
        if to_utc(htf[i].close_time) <= ts:
            chosen = i
            break
    if chosen is None:
        return None, None, None
    ema = htf_ema[chosen] if chosen < len(htf_ema) else None
    close = htf[chosen].close
    if ema is None:
        return None, close, None
    if close > ema:
        return "UP", close, ema
    if close < ema:
        return "DOWN", close, ema
    return None, close, ema


def _parse_hhmm(raw: str) -> Optional[Tuple[int, int]]:
    parts = str(raw or "").strip().split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None


def event_time_utc(ev: Any) -> Optional[datetime]:
    t = getattr(ev, "time_et", None)
    if not t:
        return None
    hm = _parse_hhmm(str(t))
    if hm is None:
        return None
    try:
        et = ZoneInfo("America/New_York")
    except Exception:
        et = timezone(timedelta(hours=-5))
    local = datetime.combine(ev.date, time(hm[0], hm[1]), tzinfo=et)
    return local.astimezone(timezone.utc)


def news_window_hit(
    session_date: date,
    events: Sequence[Any],
    params: AsiaLiqParams,
    extra_windows: Sequence[str],
) -> Optional[str]:
    """Return a reason if a timed window overlaps London-open blackout."""
    pad = timedelta(minutes=max(0, int(params.news_blackout_minutes or 0)))
    anchor0 = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        int(params.news_anchor_start_hour_utc),
        0,
        tzinfo=timezone.utc,
    )
    anchor1 = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        int(params.news_anchor_end_hour_utc),
        0,
        tzinfo=timezone.utc,
    )
    lo, hi = anchor0 - pad, anchor1 + pad
    for ev in events:
        ts = event_time_utc(ev)
        if ts is None:
            continue
        if lo <= ts <= hi:
            return f"news_window:{getattr(ev, 'title', ev)}"
    for raw in extra_windows or []:
        s = str(raw).strip()
        if "-" not in s:
            continue
        a, b = s.split("-", 1)
        ha, hb = _parse_hhmm(a), _parse_hhmm(b)
        if ha is None or hb is None:
            continue
        wa = datetime(
            session_date.year,
            session_date.month,
            session_date.day,
            ha[0],
            ha[1],
            tzinfo=timezone.utc,
        )
        wb = datetime(
            session_date.year,
            session_date.month,
            session_date.day,
            hb[0],
            hb[1],
            tzinfo=timezone.utc,
        )
        if wb < wa:
            wb += timedelta(days=1)
        if wa <= hi and wb >= lo:
            return f"news_window:{s}"
    return None


def _week_key(d: date) -> Tuple[int, int]:
    iso = d.isocalendar()
    return int(iso[0]), int(iso[1])


def _mk_skip(
    day: date,
    reason: str,
    **extra: Any,
) -> AsiaLiqSkip:
    return AsiaLiqSkip(
        local_date=day.isoformat(),
        reason=reason,
        asia_high=extra.get("asia_high"),
        asia_low=extra.get("asia_low"),
        box_height=extra.get("box_height"),
        atr=extra.get("atr"),
        htf_side=extra.get("htf_side"),
        detail=extra.get("detail"),
        news_kind=extra.get("news_kind"),
        news_title=extra.get("news_title"),
    )


def _find_tick_index(times: Sequence[datetime], ts: datetime) -> int:
    return bisect_left(times, to_utc(ts))


def simulate_partial(
    ticks: Sequence[Tick],
    times: Sequence[datetime],
    start_index: int,
    *,
    side: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    flatten_utc: datetime,
    ps: float,
    trail_candles: Sequence[Candle],
    trail_bars: int,
    use_trail: bool,
    be_offset_px: float,
) -> Tuple[str, datetime, float, float, bool, bool, float, float]:
    """
    Walk ticks after fill. 50% at TP1, remainder to TP2 / trail / flatten.
    Returns reason, exit_ts, exit_px, pts, tp1_hit, trail_used, max_fav, max_adv.
    """
    if start_index < 0 or start_index >= len(ticks):
        return "no_entry_tick", flatten_utc, entry, 0.0, False, False, 0.0, 0.0

    sl_now = sl
    tp1_hit = False
    trail_used = False
    trail_level: Optional[float] = None
    be = entry + be_offset_px if side == "UP" else entry - be_offset_px
    qty1, qty2 = 1.0, 0.0
    pts1 = 0.0
    max_fav = 0.0
    max_adv = 0.0
    last_ts = ticks[start_index].ts
    last_px = entry
    flatten_utc = to_utc(flatten_utc)

    closed_i = 0
    n_trail = len(trail_candles)

    def swing_stop(upto_ts: datetime) -> Optional[float]:
        nonlocal closed_i
        ts = to_utc(upto_ts)
        while closed_i < n_trail and to_utc(trail_candles[closed_i].close_time) <= ts:
            closed_i += 1
        if closed_i < trail_bars:
            return None
        window = trail_candles[closed_i - trail_bars : closed_i]
        if side == "UP":
            return min(c.low for c in window)
        return max(c.high for c in window)

    for i in range(start_index + 1, len(ticks)):
        t = ticks[i]
        px = t.mid
        last_ts, last_px = t.ts, px
        fav = _fav(side, entry, px, ps)
        adv = -fav
        if fav > max_fav:
            max_fav = fav
        if adv > max_adv:
            max_adv = adv

        if to_utc(t.ts) >= flatten_utc:
            if tp1_hit:
                pts2 = _fav(side, entry, px, ps)
                pts = 0.5 * pts1 + 0.5 * pts2
            else:
                pts = _fav(side, entry, px, ps)
            return "flatten", t.ts, px, pts, tp1_hit, trail_used, max_fav, max_adv

        if use_trail and tp1_hit:
            sw = swing_stop(t.ts)
            if sw is not None:
                if side == "UP":
                    cand = max(sw, be)
                    if trail_level is None or cand > trail_level:
                        trail_level = cand
                        sl_now = trail_level
                        trail_used = True
                else:
                    cand = min(sw, be)
                    if trail_level is None or cand < trail_level:
                        trail_level = cand
                        sl_now = trail_level
                        trail_used = True

        if not tp1_hit:
            if _hit_stop(side, px, sl_now):
                pts = _fav(side, entry, sl_now, ps)
                return "sl", t.ts, sl_now, pts, False, False, max_fav, max_adv
            if _hit_tp(side, px, tp1):
                tp1_hit = True
                qty1, qty2 = 0.5, 0.5
                pts1 = _fav(side, entry, tp1, ps)
                sl_now = be
                if _hit_tp(side, px, tp2):
                    pts2 = _fav(side, entry, tp2, ps)
                    pts = 0.5 * pts1 + 0.5 * pts2
                    return "tp2", t.ts, tp2, pts, True, False, max_fav, max_adv
                continue
        else:
            if _hit_stop(side, px, sl_now):
                pts2 = _fav(side, entry, sl_now, ps)
                pts = 0.5 * pts1 + 0.5 * pts2
                reason = "trail" if trail_used and trail_level is not None else "sl"
                return reason, t.ts, sl_now, pts, True, trail_used, max_fav, max_adv
            if _hit_tp(side, px, tp2):
                pts2 = _fav(side, entry, tp2, ps)
                pts = 0.5 * pts1 + 0.5 * pts2
                return "tp2", t.ts, tp2, pts, True, trail_used, max_fav, max_adv

    if tp1_hit:
        pts2 = _fav(side, entry, last_px, ps)
        pts = 0.5 * pts1 + 0.5 * pts2
    else:
        pts = _fav(side, entry, last_px, ps)
    return "timeout", last_ts, last_px, pts, tp1_hit, trail_used, max_fav, max_adv


def _scan_post_asia(
    post: Sequence[Candle],
    *,
    asia_high: float,
    asia_low: float,
    asia_mid: float,
    box_height: float,
    atr: float,
    params: AsiaLiqParams,
    first_entry: datetime,
    signal_end: datetime,
    mode_b_end: datetime,
    htf: Optional[Sequence[Candle]] = None,
    htf_ema: Optional[Sequence[Optional[float]]] = None,
    htf_side_locked: Optional[str] = None,
) -> Optional[AsiaLiqSetup]:
    """First completed Mode A or Mode B setup on closed 15m bars. No lookahead."""
    if atr <= 0 or not post:
        return None
    sweep_buf = float(params.sweep_buffer_atr) * atr
    stop_buf = float(params.sweep_stop_atr) * atr
    reclaim_n = int(params.reclaim_bars)
    confirm_on = bool(params.mode_b_confirm)
    a_on = bool(params.mode_a_enabled)
    b_on = bool(params.mode_b_enabled)

    sweep_side: Optional[str] = None  # UP = highs taken (short reclaim)
    sweep_i: Optional[int] = None
    sweep_wick: Optional[float] = None
    pending_confirm: Optional[Tuple[int, str, float]] = None  # reclaim_i, side, wick

    def a_blocked(side: str) -> bool:
        if sweep_side is None and pending_confirm is None:
            return False
        if pending_confirm is not None:
            return pending_confirm[1] == side
        return sweep_side == side

    n = len(post)
    for i, c in enumerate(post):
        close_ts = to_utc(c.close_time)
        if close_ts > signal_end:
            break
        if htf is not None and htf_ema is not None:
            htf_side, _, _ = last_closed_htf(htf, htf_ema, close_ts)
        else:
            htf_side = htf_side_locked

        # 1) resolve Mode B confirm from previous reclaim
        if pending_confirm is not None:
            rec_i, bside, wick = pending_confirm
            pending_confirm = None
            rebreak = (bside == "UP" and c.high >= asia_high - 1e-12) or (
                bside == "DOWN" and c.low <= asia_low + 1e-12
            )
            if (
                b_on
                and not rebreak
                and close_ts >= first_entry
                and close_ts <= mode_b_end
            ):
                trade_side = "DOWN" if bside == "UP" else "UP"
                sl = wick + stop_buf if trade_side == "DOWN" else wick - stop_buf
                tp1, tp2 = mode_b_targets(trade_side, asia_high, asia_low, asia_mid)
                return AsiaLiqSetup(
                    session_date=date.min,
                    mode="B",
                    side=trade_side,
                    signal=c,
                    entry=c.close,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    asia_high=asia_high,
                    asia_low=asia_low,
                    asia_mid=asia_mid,
                    box_height=box_height,
                    atr=atr,
                    htf_side=htf_side,
                    reason="sweep_reclaim_confirm",
                    sweep_wick=wick,
                )
            sweep_side = None
            sweep_i = None
            sweep_wick = None

        # 2) Mode A on this close (if not blocked on that side)
        if a_on and close_ts >= first_entry:
            a_side = mode_a_side(
                c,
                asia_high=asia_high,
                asia_low=asia_low,
                atr=atr,
                params=params,
            )
            if a_side is not None and not a_blocked(a_side):
                htf_ok = (not params.htf_enabled) or (htf_side == a_side)
                if htf_ok:
                    sl = asia_mid
                    tp1, tp2 = mode_a_targets(a_side, c.close, sl, box_height, params)
                    return AsiaLiqSetup(
                        session_date=date.min,
                        mode="A",
                        side=a_side,
                        signal=c,
                        entry=c.close,
                        sl=sl,
                        tp1=tp1,
                        tp2=tp2,
                        asia_high=asia_high,
                        asia_low=asia_low,
                        asia_mid=asia_mid,
                        box_height=box_height,
                        atr=atr,
                        htf_side=htf_side,
                        reason="continuation",
                    )

        # 3) Mode B sweep / reclaim bookkeeping (through mode_b_end)
        if not b_on or close_ts > mode_b_end:
            continue

        high_liq = c.high >= asia_high + sweep_buf
        low_liq = c.low <= asia_low - sweep_buf

        if sweep_side is None:
            if high_liq:
                sweep_side, sweep_i, sweep_wick = "UP", i, c.high
            elif low_liq:
                sweep_side, sweep_i, sweep_wick = "DOWN", i, c.low
        else:
            assert sweep_i is not None and sweep_wick is not None
            if sweep_side == "UP":
                if c.high > sweep_wick:
                    sweep_wick = c.high
            else:
                if c.low < sweep_wick:
                    sweep_wick = c.low

        if sweep_side is not None and sweep_i is not None:
            if i - sweep_i >= reclaim_n:
                sweep_side = None
                sweep_i = None
                sweep_wick = None
            elif close_inside(c, asia_high, asia_low):
                if confirm_on:
                    pending_confirm = (i, sweep_side, float(sweep_wick))
                    # keep sweep_side so Mode A stays blocked on confirm bar
                elif close_ts >= first_entry:
                    trade_side = "DOWN" if sweep_side == "UP" else "UP"
                    wick = float(sweep_wick)
                    sl = wick + stop_buf if trade_side == "DOWN" else wick - stop_buf
                    tp1, tp2 = mode_b_targets(
                        trade_side, asia_high, asia_low, asia_mid
                    )
                    return AsiaLiqSetup(
                        session_date=date.min,
                        mode="B",
                        side=trade_side,
                        signal=c,
                        entry=c.close,
                        sl=sl,
                        tp1=tp1,
                        tp2=tp2,
                        asia_high=asia_high,
                        asia_low=asia_low,
                        asia_mid=asia_mid,
                        box_height=box_height,
                        atr=atr,
                        htf_side=htf_side,
                        reason="sweep_reclaim",
                        sweep_wick=wick,
                    )
                else:
                    sweep_side = None
                    sweep_i = None
                    sweep_wick = None

    return None


def lock_asia_box(
    candles: Sequence[Candle],
    asia_start: datetime,
    lock: datetime,
) -> Tuple[List[Candle], Optional[float], Optional[float]]:
    """Asia bars with open in [asia_start, lock). Box is frozen at lock."""
    a0, a1 = to_utc(asia_start), to_utc(lock)
    asia = [
        c
        for c in candles
        if a0 <= to_utc(c.open_time) < a1
    ]
    if not asia:
        return [], None, None
    return asia, max(c.high for c in asia), min(c.low for c in asia)


def _hour_spread_sample(
    ticks: Sequence[Tick],
    times: Sequence[datetime],
    hour_start: datetime,
) -> Optional[float]:
    i = _find_tick_index(times, hour_start)
    if i >= len(ticks):
        return None
    end = to_utc(hour_start) + timedelta(hours=1)
    spreads: List[float] = []
    for j in range(i, min(len(ticks), i + 4000)):
        if to_utc(ticks[j].ts) >= end:
            break
        spreads.append(float(ticks[j].spread))
        if len(spreads) >= 40:
            break
    if not spreads:
        return None
    return float(median(spreads))


def run_asia_liquidity(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[AsiaLiqParams] = None,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    params = _normalize_params(params or AsiaLiqParams())
    box_tz = require_zone(params.timezone)
    require_zone(params.exec_timezone)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return _empty_result(params, symbol=sym, ticks=len(ticks or []))

    builder = CandleBuilder(timeframe_minutes=15, max_completed=200, skip_ignored=False)
    completed: List[Candle] = []
    n_ticks = len(ticks)
    step = max(n_ticks // 40, 80_000)
    for i, t in enumerate(ticks):
        closed = builder.add_price(t.mid, t.ts)
        if closed is not None:
            completed.append(closed)
        if progress and n_ticks > 80_000 and ((i + 1) % step == 0 or i + 1 == n_ticks):
            progress(
                phase="candles",
                ticks_done=i + 1,
                ticks_total=n_ticks,
                message=f"15m candles {i + 1:,}/{n_ticks:,}",
            )

    if not completed:
        return _empty_result(params, symbol=sym, ticks=n_ticks)

    atrs = wilder_atr(completed, params.atr_period)
    htf = aggregate_tf(completed, params.htf_tf_min)
    htf_ema = ema_series([c.close for c in htf], params.htf_ema_period)
    times = [to_utc(t.ts) for t in ticks]

    first_local = _local(completed[0].open_time, box_tz).date()
    last_local = _local(completed[-1].open_time, box_tz).date()

    # Pre-lock boxes for compression (every session with a real Asia range).
    box_by_day: Dict[date, Tuple[float, float, float]] = {}
    day = first_local
    while day <= last_local:
        asia_start, lock, *_ = session_bounds(day, params)
        asia, hi, lo = lock_asia_box(completed, asia_start, lock)
        if hi is not None and lo is not None and len(asia) >= 2:
            box_by_day[day] = (hi, lo, hi - lo)
        day += timedelta(days=1)

    trades: List[AsiaLiqTrade] = []
    skips: List[AsiaLiqSkip] = []
    equity = float(params.start_equity)
    peak_eq = equity
    max_dd_pct = 0.0
    daily_r: Dict[date, float] = defaultdict(float)
    weekly_r: Dict[Tuple[int, int], float] = defaultdict(float)
    weekly_off_until: Optional[date] = None
    spread_hist: List[float] = []
    traded_days: set = set()

    dates = []
    d = first_local
    while d <= last_local:
        dates.append(d)
        d += timedelta(days=1)
    n_days = len(dates)

    for di, session_day in enumerate(dates):
        if progress and (di % 5 == 0 or di + 1 == n_days):
            progress(
                phase="replay",
                days_done=di + 1,
                days_total=n_days,
                trades=len(trades),
                message=f"Day {session_day.isoformat()} · {len(trades)} trades",
            )

        news_mode = params.news_mode
        news_events = (
            events_on(session_day, kinds=kinds_for_set(params.news_set))
            if news_mode != "off"
            else []
        )
        news_kind, news_title = format_news(news_events)
        news_kw: Dict[str, Any] = {}
        if news_mode != "off" and news_events:
            news_kw = {"news_kind": news_kind, "news_title": news_title}

        asia_start, lock, first_entry, signal_end, mode_b_end, flatten = session_bounds(
            session_day, params
        )
        asia, asia_high, asia_low = lock_asia_box(completed, asia_start, lock)

        if weekly_off_until is not None and session_day < weekly_off_until:
            skips.append(
                _mk_skip(
                    session_day,
                    "weekly_halt",
                    detail=f"off until {weekly_off_until.isoformat()}",
                    **news_kw,
                )
            )
            continue

        timed = news_window_hit(
            session_day,
            news_events if news_mode != "off" else [],
            params,
            params.news_windows,
        )
        if timed:
            skips.append(
                _mk_skip(session_day, "news_window", detail=timed, **news_kw)
            )
            continue
        if news_mode == "filter" and news_events:
            skips.append(
                _mk_skip(
                    session_day,
                    "news_day",
                    detail=news_title,
                    **news_kw,
                )
            )
            continue

        if len(asia) < 2 or asia_high is None or asia_low is None:
            skips.append(
                _mk_skip(
                    session_day,
                    "thin_asia",
                    detail=f"{len(asia)} candles",
                    **news_kw,
                )
            )
            continue

        asia_mid = (asia_high + asia_low) / 2.0
        box_height = asia_high - asia_low

        atr_val: Optional[float] = None
        for i, c in enumerate(completed):
            if to_utc(c.close_time) <= lock:
                atr_val = atrs[i]
            else:
                break
        if atr_val is None or atr_val <= 0:
            skips.append(
                _mk_skip(
                    session_day,
                    "atr_warmup",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    box_height=box_height,
                    **news_kw,
                )
            )
            continue

        ratio = box_height / atr_val
        if ratio < float(params.box_atr_min):
            skips.append(
                _mk_skip(
                    session_day,
                    "box_too_tight",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    box_height=box_height,
                    atr=atr_val,
                    detail=f"box/atr={ratio:.3f}",
                    **news_kw,
                )
            )
            continue
        if ratio > float(params.box_atr_max):
            skips.append(
                _mk_skip(
                    session_day,
                    "box_too_wide",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    box_height=box_height,
                    atr=atr_val,
                    detail=f"box/atr={ratio:.3f}",
                    **news_kw,
                )
            )
            continue

        look = int(params.compression_lookback or 0)
        if look > 0:
            prior = [
                box_by_day[d][2]
                for d in sorted(box_by_day)
                if d < session_day
            ]
            if len(prior) < look:
                skips.append(
                    _mk_skip(
                        session_day,
                        "compression_warmup",
                        asia_high=asia_high,
                        asia_low=asia_low,
                        box_height=box_height,
                        atr=atr_val,
                        detail=f"{len(prior)}/{look}",
                        **news_kw,
                    )
                )
                continue
            avg = sum(prior[-look:]) / float(look)
            if box_height >= avg:
                skips.append(
                    _mk_skip(
                        session_day,
                        "not_compressed",
                        asia_high=asia_high,
                        asia_low=asia_low,
                        box_height=box_height,
                        atr=atr_val,
                        detail=f"box={box_height:.5f} avg={avg:.5f}",
                        **news_kw,
                    )
                )
                continue

        htf_side, _, _ = last_closed_htf(htf, htf_ema, lock)
        post = [
            c
            for c in completed
            if to_utc(c.open_time) >= lock and to_utc(c.close_time) <= flatten
        ]
        setup = _scan_post_asia(
            post,
            asia_high=asia_high,
            asia_low=asia_low,
            asia_mid=asia_mid,
            box_height=box_height,
            atr=atr_val,
            params=params,
            first_entry=first_entry,
            signal_end=signal_end,
            mode_b_end=mode_b_end,
            htf=htf,
            htf_ema=htf_ema,
            htf_side_locked=htf_side,
        )
        if setup is None:
            skips.append(
                _mk_skip(
                    session_day,
                    "no_setup",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    box_height=box_height,
                    atr=atr_val,
                    htf_side=htf_side,
                    **news_kw,
                )
            )
            continue
        setup.session_date = session_day

        if params.one_trade_per_day and session_day in traded_days:
            skips.append(
                _mk_skip(
                    session_day,
                    "one_per_day",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    **news_kw,
                )
            )
            continue

        wk = _week_key(session_day)
        if weekly_r[wk] <= -float(params.weekly_halt_r):
            monday = session_day + timedelta(days=(7 - session_day.weekday()) % 7)
            if session_day.weekday() != 0:
                monday = session_day + timedelta(days=7 - session_day.weekday())
            weekly_off_until = monday if monday > session_day else session_day + timedelta(
                days=7
            )
            skips.append(
                _mk_skip(
                    session_day,
                    "weekly_halt",
                    detail=f"week {wk} r={weekly_r[wk]:.2f}",
                    **news_kw,
                )
            )
            continue
        if daily_r[session_day] <= -float(params.daily_halt_r):
            skips.append(
                _mk_skip(
                    session_day,
                    "daily_halt",
                    detail=f"day r={daily_r[session_day]:.2f}",
                    **news_kw,
                )
            )
            continue

        fill_i = _find_tick_index(times, setup.signal.close_time)
        if fill_i >= len(ticks):
            skips.append(
                _mk_skip(
                    session_day,
                    "no_entry_tick",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    **news_kw,
                )
            )
            continue
        fill_tick = ticks[fill_i]
        if params.spread_filter and spread_hist:
            med = float(median(spread_hist[-20:]))
            if med > 0 and fill_tick.spread > float(params.spread_mult) * med:
                skips.append(
                    _mk_skip(
                        session_day,
                        "wide_spread",
                        asia_high=asia_high,
                        asia_low=asia_low,
                        detail=f"spread={fill_tick.spread:.5f} med={med:.5f}",
                        **news_kw,
                    )
                )
                samp = _hour_spread_sample(ticks, times, lock)
                if samp is not None:
                    spread_hist.append(samp)
                continue
        samp = _hour_spread_sample(ticks, times, lock)
        if samp is not None:
            spread_hist.append(samp)

        sl_pts = abs(setup.entry - setup.sl) / ps
        if sl_pts <= 1e-9:
            skips.append(
                _mk_skip(
                    session_day,
                    "zero_stop",
                    asia_high=asia_high,
                    asia_low=asia_low,
                    **news_kw,
                )
            )
            continue

        be_px = sl_pts * float(params.be_offset_r) * ps
        trail = setup.mode == "A"
        (
            reason,
            exit_ts,
            exit_px,
            pts,
            tp1_hit,
            trail_used,
            max_fav,
            max_adv,
        ) = simulate_partial(
            ticks,
            times,
            fill_i,
            side=setup.side,
            entry=setup.entry,
            sl=setup.sl,
            tp1=setup.tp1,
            tp2=setup.tp2,
            flatten_utc=flatten,
            ps=ps,
            trail_candles=post,
            trail_bars=int(params.trail_swing_bars),
            use_trail=trail,
            be_offset_px=be_px,
        )
        r_mult = pts / sl_pts if sl_pts else 0.0
        risk_cash = equity * (float(params.risk_pct) / 100.0)
        size = risk_cash / (sl_pts * ps) if sl_pts * ps > 0 else 0.0
        equity = equity + risk_cash * r_mult
        if equity > peak_eq:
            peak_eq = equity
        if peak_eq > 0:
            dd = (peak_eq - equity) / peak_eq * 100.0
            if dd > max_dd_pct:
                max_dd_pct = dd
        daily_r[session_day] += r_mult
        weekly_r[wk] += r_mult
        if weekly_r[wk] <= -float(params.weekly_halt_r):
            weekly_off_until = session_day + timedelta(days=7 - session_day.weekday())
            if weekly_off_until <= session_day:
                weekly_off_until = session_day + timedelta(days=7)

        trades.append(
            AsiaLiqTrade(
                local_date=session_day.isoformat(),
                mode=setup.mode,
                side=setup.side,
                asia_high=round(asia_high, 5),
                asia_low=round(asia_low, 5),
                asia_mid=round(asia_mid, 5),
                box_height=round(box_height, 5),
                box_height_pts=round(box_height / ps, 1),
                atr=round(atr_val, 5),
                htf_side=htf_side,
                entry_ts=to_utc(setup.signal.close_time).isoformat(),
                entry=round(setup.entry, 5),
                sl=round(setup.sl, 5),
                tp1=round(setup.tp1, 5),
                tp2=round(setup.tp2, 5),
                sl_pts=round(sl_pts, 1),
                entry_reason=setup.reason,
                exit_ts=to_utc(exit_ts).isoformat() if exit_ts else None,
                exit=round(exit_px, 5),
                exit_reason=reason,
                pts=round(pts, 1),
                r=round(r_mult, 3),
                tp1_hit=tp1_hit,
                trail_used=trail_used,
                max_fav_pts=round(max_fav, 1),
                max_adv_pts=round(max_adv, 1),
                box_atr_ratio=round(ratio, 3),
                news_kind=news_kw.get("news_kind"),
                news_title=news_kw.get("news_title"),
                size=round(size, 4),
                equity_after=round(equity, 2),
            )
        )
        traded_days.add(session_day)

    return summarize_asia_liq(
        trades,
        skips,
        params,
        symbol=sym,
        ticks=n_ticks,
        equity=equity,
        max_dd_pct=max_dd_pct,
    )


def signal_from_candles(
    candles: Sequence[Candle],
    *,
    symbol: str = "XAUUSD",
    params: Optional[AsiaLiqParams] = None,
    asof: Optional[datetime] = None,
    spread: Optional[float] = None,
    equity: float = 1_000.0,
) -> Dict[str, Any]:
    """Live helper: last closed-bar setup for the current session (no ticks)."""
    params = _normalize_params(params or AsiaLiqParams())
    if not candles:
        return {"symbol": symbol, "mode": None, "reason": "no_candles"}
    closed = [c for c in candles if c.is_closed]
    if not closed:
        return {"symbol": symbol, "mode": None, "reason": "open_bar"}
    asof = to_utc(asof or closed[-1].close_time)
    # refuse if the newest bar is still open relative to asof
    newest = candles[-1]
    if not newest.is_closed and to_utc(newest.open_time) <= asof < to_utc(newest.close_time):
        return {"symbol": symbol, "mode": None, "reason": "open_bar"}

    box_tz = require_zone(params.timezone)
    session_day = _local(asof, box_tz).date()
    # If asof is before lock, the session box is not frozen yet.
    asia_start, lock, first_entry, signal_end, mode_b_end, flatten = session_bounds(
        session_day, params
    )
    if asof < lock:
        return {"symbol": symbol, "mode": None, "reason": "box_not_locked"}

    atrs = wilder_atr(closed, params.atr_period)
    htf = aggregate_tf(closed, params.htf_tf_min)
    htf_ema = ema_series([c.close for c in htf], params.htf_ema_period)
    asia, asia_high, asia_low = lock_asia_box(closed, asia_start, lock)
    if asia_high is None or asia_low is None or len(asia) < 2:
        return {"symbol": symbol, "mode": None, "reason": "thin_asia"}
    atr_val = None
    for i, c in enumerate(closed):
        if to_utc(c.close_time) <= lock:
            atr_val = atrs[i]
        else:
            break
    if atr_val is None or atr_val <= 0:
        return {"symbol": symbol, "mode": None, "reason": "atr_warmup"}
    asia_mid = (asia_high + asia_low) / 2.0
    box_height = asia_high - asia_low
    ratio = box_height / atr_val
    if ratio < float(params.box_atr_min):
        return {"symbol": symbol, "mode": None, "reason": "box_too_tight"}
    if ratio > float(params.box_atr_max):
        return {"symbol": symbol, "mode": None, "reason": "box_too_wide"}
    look = int(params.compression_lookback or 0)
    if look > 0:
        # live path: compare to prior boxes from the provided history
        box_tz = require_zone(params.timezone)
        heights: List[float] = []
        d0 = _local(closed[0].open_time, box_tz).date()
        d = d0
        while d < session_day:
            s0, lk, *_ = session_bounds(d, params)
            a, hi, lo = lock_asia_box(closed, s0, lk)
            if hi is not None and lo is not None and len(a) >= 2:
                heights.append(hi - lo)
            d += timedelta(days=1)
        if len(heights) < look:
            return {"symbol": symbol, "mode": None, "reason": "compression_warmup"}
        avg = sum(heights[-look:]) / float(look)
        if box_height >= avg:
            return {"symbol": symbol, "mode": None, "reason": "not_compressed"}

    htf_side, _, _ = last_closed_htf(htf, htf_ema, min(asof, lock))
    post = [
        c
        for c in closed
        if to_utc(c.open_time) >= lock and to_utc(c.close_time) <= min(asof, flatten)
    ]
    setup = _scan_post_asia(
        post,
        asia_high=asia_high,
        asia_low=asia_low,
        asia_mid=asia_mid,
        box_height=box_height,
        atr=atr_val,
        params=params,
        first_entry=first_entry,
        signal_end=signal_end,
        mode_b_end=mode_b_end,
        htf=htf,
        htf_ema=htf_ema,
        htf_side_locked=htf_side,
    )
    if setup is None:
        return {"symbol": symbol, "mode": None, "reason": "no_setup"}
    ps = point_size(symbol if "/" in symbol else reaktor_symbol(symbol))
    sl_dist = abs(setup.entry - setup.sl)
    size = 0.0
    if sl_dist > 0 and ps > 0:
        size = (float(equity) * (float(params.risk_pct) / 100.0)) / sl_dist
    return {
        "symbol": symbol,
        "mode": setup.mode,
        "side": "long" if setup.side == "UP" else "short",
        "entry": round(setup.entry, 5),
        "stop": round(setup.sl, 5),
        "tp1": round(setup.tp1, 5),
        "tp2": round(setup.tp2, 5),
        "size": round(size, 4),
        "reason": setup.reason,
        "r_distance": round(sl_dist / ps, 1) if ps else None,
        "flatten_utc": flatten.isoformat(),
        "asia_high": round(asia_high, 5),
        "asia_low": round(asia_low, 5),
        "htf_side": htf_side,
        "spread": spread,
    }


def _pct(a: int, b: int) -> Optional[float]:
    if b <= 0:
        return None
    return round(100.0 * a / b, 1)


def _trade_stats(trades: Sequence[AsiaLiqTrade]) -> Dict[str, Any]:
    n = len(trades)
    wins = sum(1 for t in trades if t.r > 1e-9)
    losses = sum(1 for t in trades if t.r < -1e-9)
    gp = sum(t.r for t in trades if t.r > 0)
    gl = -sum(t.r for t in trades if t.r < 0)
    pf = round(gp / gl, 2) if gl > 1e-9 else None
    by_reason: Dict[str, int] = {}
    by_hour: Dict[str, List[AsiaLiqTrade]] = defaultdict(list)
    buckets: Dict[str, List[AsiaLiqTrade]] = defaultdict(list)
    for t in trades:
        by_reason[t.exit_reason or "?"] = by_reason.get(t.exit_reason or "?", 0) + 1
        try:
            hour = datetime.fromisoformat(t.entry_ts.replace("Z", "+00:00")).hour
        except Exception:
            hour = -1
        by_hour[str(hour)].append(t)
        ratio = t.box_atr_ratio
        if ratio is None:
            b = "unknown"
        elif ratio < 0.40:
            b = "0.25-0.40"
        elif ratio < 0.60:
            b = "0.40-0.60"
        else:
            b = "0.60-0.85"
        buckets[b].append(t)
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "scratches": n - wins - losses,
        "win_pct": _pct(wins, n),
        "profit_factor": pf,
        "avg_r": round(sum(t.r for t in trades) / n, 3) if n else 0.0,
        "sum_r": round(sum(t.r for t in trades), 3),
        "avg_pts": round(sum(t.pts for t in trades) / n, 1) if n else 0.0,
        "sum_pts": round(sum(t.pts for t in trades), 1),
        "exits": by_reason,
        "by_hour": {
            h: {
                "trades": len(v),
                "win_pct": _pct(sum(1 for t in v if t.r > 0), len(v)),
                "avg_r": round(sum(t.r for t in v) / len(v), 3) if v else 0.0,
                "sum_r": round(sum(t.r for t in v), 3),
            }
            for h, v in sorted(by_hour.items(), key=lambda kv: int(kv[0]))
        },
        "box_buckets": {
            k: {
                "trades": len(v),
                "win_pct": _pct(sum(1 for t in v if t.r > 0), len(v)),
                "avg_r": round(sum(t.r for t in v) / len(v), 3) if v else 0.0,
                "sum_r": round(sum(t.r for t in v), 3),
                "profit_factor": (
                    round(
                        sum(t.r for t in v if t.r > 0)
                        / max(-sum(t.r for t in v if t.r < 0), 1e-9),
                        2,
                    )
                    if any(t.r < 0 for t in v)
                    else None
                ),
            }
            for k, v in buckets.items()
        },
    }


def _mode_split(trades: Sequence[AsiaLiqTrade]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for mode in ("A", "B"):
        subset = [t for t in trades if t.mode == mode]
        stats = _trade_stats(subset)
        out[mode] = stats
    return out


def summarize_asia_liq(
    trades: Sequence[AsiaLiqTrade],
    skips: Sequence[AsiaLiqSkip],
    params: AsiaLiqParams,
    *,
    symbol: str,
    ticks: int,
    equity: Optional[float] = None,
    max_dd_pct: float = 0.0,
) -> Dict[str, Any]:
    stats = _trade_stats(trades)
    skip_reasons: Dict[str, int] = {}
    for s in skips:
        skip_reasons[s.reason] = skip_reasons.get(s.reason, 0) + 1
    by_tr: Dict[str, List[AsiaLiqTrade]] = defaultdict(list)
    by_sk: Dict[str, List[AsiaLiqSkip]] = defaultdict(list)
    for t in trades:
        by_tr[(t.local_date or "")[:7]].append(t)
    for s in skips:
        by_sk[(s.local_date or "")[:7]].append(s)
    months = []
    for ym in sorted(set(by_tr) | set(by_sk)):
        row = _trade_stats(by_tr.get(ym) or [])
        row["month"] = ym
        row["skipped"] = len(by_sk.get(ym) or [])
        row["skip_reasons"] = {}
        for s in by_sk.get(ym) or []:
            row["skip_reasons"][s.reason] = row["skip_reasons"].get(s.reason, 0) + 1
        months.append(row)
    start_eq = float(params.start_equity)
    return {
        "kind": "asia_liquidity",
        "symbol": symbol,
        "params": asdict(params),
        "ticks": ticks,
        "days_seen": len(trades) + len(skips),
        "skipped": len(skips),
        "skip_reasons": skip_reasons,
        **stats,
        "max_dd_pct": round(max_dd_pct, 2),
        "equity": round(equity, 2) if equity is not None else round(start_eq, 2),
        "start_equity": start_eq,
        "by_mode": _mode_split(trades),
        "by_month": months,
        "rows": [asdict(t) for t in trades],
        "skips": [asdict(s) for s in skips],
    }


def _empty_result(params: AsiaLiqParams, *, symbol: str, ticks: int) -> Dict[str, Any]:
    return summarize_asia_liq([], [], params, symbol=symbol, ticks=ticks)
