"""
Micro-burst scalp: ride a short one-way tick move for a few gold points.

Detect a 2–8s burst that is large enough to notice, small enough not to be a
Spike-fade vertical, and persistent (little pullback in the window). Enter
WITH the burst. Fill at ask (long) / bid (short). Flatten on TP, SL, trail, or time.

Pure — no web, no MT5.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import CandleBuilder
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.spike_fade import weekend_reopen_blackout


# UTC hour windows. Asia wraps midnight (Sydney/Tokyo into London open).
CHISINAU = ZoneInfo("Europe/Chisinau")

SESSION_HELP = {
    "all": "Every hour (weekend blackout still applies).",
    "asia": "22:00–07:00 UTC (Asia / gold overnight).",
    "asia_core": "00:00–05:00 UTC (quietest Asia hours).",
    "late_chisinau": "20:00–23:00 Europe/Chisinau (8–11pm local, late NY).",
    "quiet": "Asia 22:00–07:00 UTC plus 20:00–23:00 Chisinau.",
    "asia_london": "22:00–16:00 UTC (Asia + London; skip NY-only afternoon).",
    "london_ny": "07:00–21:00 UTC (London + New York).",
}


@dataclass
class BurstParams:
    window_sec: float = 4.0
    min_burst_pts: float = 100.0
    max_burst_pts: float = 400.0
    persist_frac: float = 0.35
    use_1m: bool = True
    min_1m_body: float = 40.0
    tp_pts: float = 100.0
    sl_pts: float = 80.0
    trail_pts: float = 0.0  # 0 = trail off
    trail_arm_pts: float = 0.0  # 0 = arm when fav reaches trail_pts
    max_hold_sec: float = 45.0
    cooldown_sec: float = 15.0
    weekend_blackout_min: float = 10.0
    lag_sec: float = 0.5
    session: str = "all"  # all | asia | asia_core | quiet | late_chisinau | ...
    max_spread_pts: float = 50.0  # skip new entries if spread wider than this
    # fade = enter opposite after a stall. with = ride the burst.
    mode: str = "with"  # with | fade
    confirm_pts: float = 0.0  # unused for stall fade; kept for old tests
    confirm_timeout_sec: float = 3.0
    pause_sec: float = 1.0  # fade: no new extreme for this long, then enter
    pause_give_up_sec: float = 8.0  # fade: abort stall wait after this from detect
    tp_frac: float = 0.0  # fade: TP = burst * frac (0 = use tp_pts)
    tp_cap_pts: float = 0.0  # 0 = no cap
    sl_extra_pts: float = 0.0  # fade: SL = burst + extra (0 = use sl_pts)
    rr_one_to_one: bool = False  # fade: SL = TP * sl_mult
    sl_mult: float = 1.0  # with rr_one_to_one: SL = TP * this (1.0 = 1:1)
    trail_frac: float = 0.0  # fade: trail_pts = trail_arm = this * TP (0.5 → BE at +½R)
    max_spread_vs_tp: float = 0.4  # skip fill if spread >= this fraction of TP
    be_asap: bool = False  # with-momentum: move SL to entry after be_asap_pts of fav
    be_asap_pts: float = 1.0


@dataclass
class BurstTrade:
    entry_ts: str
    side: str  # UP with an up-burst, DOWN with a down-burst
    burst_pts: float
    window_sec: float
    entry: float
    tp: float
    sl_init: float
    tp_pts: float = 0.0
    sl_pts: float = 0.0
    spread_pts: float = 0.0
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None  # tp | sl | trail | timeout
    pts: float = 0.0
    max_fav_pts: float = 0.0
    lag_sec: float = 0.0
    hold_sec: Optional[float] = None
    session_hour: Optional[int] = None
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0


def to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _in_late_chisinau(ts: datetime) -> bool:
    """8pm–11pm Chisinau (20:00 ≤ local < 23:00), DST-aware."""
    local = to_utc(ts).astimezone(CHISINAU)
    return 20 <= local.hour < 23


def in_session(ts: datetime, session: str) -> bool:
    """True if `ts` is inside the named session window."""
    mode = (session or "all").strip().lower().replace("-", "_").replace("+", "_")
    if mode in ("all", "any", "all_day", "allday"):
        return True
    utc = to_utc(ts)
    h = utc.hour
    asia = h >= 22 or h < 7
    if mode == "asia":
        return asia
    if mode in ("asia_core", "quiet_asia"):
        return 0 <= h < 5
    if mode in ("late_chisinau", "late_ny_chisinau", "late_ny"):
        return _in_late_chisinau(utc)
    if mode in ("quiet", "quiet_hours"):
        return asia or _in_late_chisinau(utc)
    if mode in ("asia_london", "asia_lon"):
        return h >= 22 or h < 16
    if mode in ("london_ny", "london_newyork", "lon_ny"):
        return 7 <= h < 21
    return True


def _fav_pts(side: str, entry: float, px: float, ps: float) -> float:
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _detect(
    window: Deque[Tuple[float, float]],
    ps: float,
    min_pts: float,
    max_pts: float,
    persist_frac: float,
    window_sec: float,
) -> Optional[Tuple[str, float, float]]:
    """
    Burst from window-start mid → last mid, with pullback vs start.

    Returns (side, burst_pts, span_sec) or None.
    """
    if len(window) < 2 or ps <= 0:
        return None
    ref_ts, ref = window[0]
    last_ts, last = window[-1]
    span = last_ts - ref_ts
    if span < min(0.4, window_sec * 0.25):
        return None
    hi = max(p for _, p in window)
    lo = min(p for _, p in window)
    up = (last - ref) / ps
    down = (ref - last) / ps
    if up >= down and up + 1e-9 >= min_pts:
        if up > max_pts + 1e-9:
            return None
        adverse = (ref - lo) / ps
        if adverse > persist_frac * up + 1e-9:
            return None
        return "UP", up, span
    if down > up and down + 1e-9 >= min_pts:
        if down > max_pts + 1e-9:
            return None
        adverse = (hi - ref) / ps
        if adverse > persist_frac * down + 1e-9:
            return None
        return "DOWN", down, span
    return None


def _fade_retraced(burst_side: str, extreme: float, mid: float, confirm_pts: float, ps: float) -> bool:
    """True when mid has snapped `confirm_pts` from the burst extreme toward origin."""
    if confirm_pts <= 1e-12:
        return True
    need = float(confirm_pts) * ps
    if burst_side == "UP":
        return mid - 1e-12 <= extreme - need
    return mid + 1e-12 >= extreme + need


def _fade_offsets(burst_pts: float, params: BurstParams) -> Tuple[float, float]:
    """TP/SL in pts for a fade of this burst."""
    tp_frac = float(params.tp_frac or 0.0)
    if tp_frac > 1e-12:
        tp_off = burst_pts * tp_frac
        cap = float(params.tp_cap_pts or 0.0)
        if cap > 1e-12:
            tp_off = min(tp_off, cap)
    else:
        tp_off = float(params.tp_pts)
    extra = float(params.sl_extra_pts or 0.0)
    if bool(params.rr_one_to_one):
        sl_off = tp_off * max(1.0, float(params.sl_mult or 1.0))
    elif extra > 1e-12:
        sl_off = burst_pts + extra
    else:
        sl_off = float(params.sl_pts)
    return max(1.0, tp_off), max(1.0, sl_off)


def _1m_ok(builder: CandleBuilder, side: str, min_body: float, ps: float) -> bool:
    c = builder.get_current_candle()
    if c is None or ps <= 0:
        return False
    body = (c.close - c.open) / ps
    if side == "UP":
        return body + 1e-9 >= min_body
    return -body + 1e-9 >= min_body


def run_micro_momentum(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[BurstParams] = None,
    progress=None,
) -> Dict[str, Any]:
    params = params or BurstParams()
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return summarize_burst([], params, symbol=sym, ticks=len(ticks or []))

    window_sec = float(params.window_sec)
    min_pts = float(params.min_burst_pts)
    max_pts = float(params.max_burst_pts)
    persist = max(0.0, float(params.persist_frac))
    use_1m = bool(params.use_1m)
    min_1m = float(params.min_1m_body)
    tp_pts = max(1.0, float(params.tp_pts))
    sl_pts = max(1.0, float(params.sl_pts))
    trail_pts = max(0.0, float(params.trail_pts or 0.0))
    arm_pts = float(params.trail_arm_pts or 0.0)
    if trail_pts > 1e-12 and arm_pts <= 1e-12:
        arm_pts = trail_pts
    hold_sec = float(params.max_hold_sec)
    cd_sec = float(params.cooldown_sec)
    blackout_min = float(params.weekend_blackout_min)
    lag_sec = max(0.0, float(params.lag_sec or 0.0))
    session = str(params.session or "all")
    max_spread = float(params.max_spread_pts or 0.0)
    fade = str(params.mode or "with").strip().lower() == "fade"
    confirm_pts = float(params.confirm_pts or 0.0)
    pause_sec = max(0.0, float(params.pause_sec or 0.0))
    pause_give_up = max(pause_sec, float(params.pause_give_up_sec or 8.0))
    trail_frac = max(0.0, float(params.trail_frac or 0.0))
    spread_vs_tp = float(params.max_spread_vs_tp or 0.0)
    be_asap = (not fade) and bool(params.be_asap)
    be_asap_pts = max(0.0, float(params.be_asap_pts or 0.0))

    builder = CandleBuilder(timeframe_minutes=1, max_completed=8, skip_ignored=False)

    dq: Deque[Tuple[float, float]] = deque()
    trades: List[BurstTrade] = []
    open_t: Optional[BurstTrade] = None
    pending: Optional[Dict[str, Any]] = None
    best_fav = 0.0
    entry_epoch = 0.0
    cooldown_until = 0.0
    n = len(ticks)
    last_yield = time.monotonic()

    def levels(side: str, fill_px: float, tp_off: float, sl_off: float) -> Tuple[float, float]:
        if side == "UP":
            return fill_px + tp_off * ps, fill_px - sl_off * ps
        return fill_px - tp_off * ps, fill_px + sl_off * ps

    def fill_px(side: str, tick: Tick) -> float:
        return tick.ask if side == "UP" else tick.bid

    def mark_px(side: str, tick: Tick) -> float:
        """Price we can actually exit at."""
        return tick.bid if side == "UP" else tick.ask

    def _trail_for(tr: BurstTrade) -> Tuple[float, float]:
        t_pts = float(tr.trail_pts or 0.0) or trail_pts
        t_arm = float(tr.trail_arm_pts or 0.0) or arm_pts
        return t_pts, t_arm

    def open_trade(
        *,
        side: str,
        burst_pts: float,
        span: float,
        ts: datetime,
        epoch: float,
        tick: Tick,
        lag_used: float,
    ) -> bool:
        nonlocal open_t, best_fav, entry_epoch, pending, cooldown_until
        tp_off, sl_off = (
            _fade_offsets(burst_pts, params) if fade else (tp_pts, sl_pts)
        )
        spr = (tick.ask - tick.bid) / ps
        if fade and spread_vs_tp > 1e-12 and spr + 1e-9 >= spread_vs_tp * tp_off:
            pending = None
            cooldown_until = epoch + cd_sec
            return False
        fill = fill_px(side, tick)
        # Skip when spread already covers TP or SL (a 20-pt stop vs a 27-pt
        # gold spread is an instant loss). Levels stay on the *fill* so a
        # 100-pt SL is a 100-pt P/L, not 100+spread.
        if not fade and spr + 1e-9 >= min(tp_off, sl_off):
            pending = None
            cooldown_until = epoch + cd_sec
            return False
        tp, sl = levels(side, fill, tp_off, sl_off)
        if fade and trail_frac > 1e-12:
            tr_pts = trail_frac * tp_off
            tr_arm = trail_frac * tp_off
        else:
            tr_pts, tr_arm = trail_pts, arm_pts
        open_t = BurstTrade(
            entry_ts=ts.isoformat(),
            side=side,
            burst_pts=round(burst_pts, 1),
            window_sec=round(span, 3),
            entry=round(fill, 5),
            tp=round(tp, 5),
            sl_init=round(sl, 5),
            tp_pts=round(tp_off, 1),
            sl_pts=round(sl_off, 1),
            spread_pts=round(spr, 1),
            lag_sec=lag_used,
            session_hour=ts.hour,
            trail_pts=round(tr_pts, 1),
            trail_arm_pts=round(tr_arm, 1),
        )
        best_fav = 0.0
        entry_epoch = epoch
        pending = None
        return True

    def close_trade(tr: BurstTrade, ts: datetime, px: float, reason: str) -> None:
        nonlocal open_t, best_fav, cooldown_until
        pts = _fav_pts(tr.side, tr.entry, px, ps)
        t_pts, t_arm = _trail_for(tr)
        if reason == "be" and pts < 0:
            pts = 0.0
        if reason == "trail" and pts < 0 and t_arm + 1e-9 >= t_pts:
            pts = 0.0
        tr.exit_ts = ts.isoformat()
        tr.exit = round(px, 5)
        tr.exit_reason = reason
        tr.pts = round(pts, 1)
        tr.max_fav_pts = round(best_fav, 1)
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
        cooldown_until = ts.timestamp() + cd_sec

    def live_rows() -> List[dict]:
        return [asdict(t) for t in trades]

    for i, t in enumerate(ticks):
        ts = t.ts if t.ts.tzinfo is not None else to_utc(t.ts)
        epoch = ts.timestamp()
        mid = t.mid
        builder.add_price(mid, ts)
        dq.append((epoch, mid))
        cutoff = epoch - window_sec
        while dq and dq[0][0] < cutoff:
            dq.popleft()

        if open_t is not None:
            px = mark_px(open_t.side, t)
            fav = _fav_pts(open_t.side, open_t.entry, px, ps)
            if fav > best_fav:
                best_fav = fav
            held = epoch - entry_epoch
            t_pts, t_arm = _trail_for(open_t)
            be_on = be_asap and best_fav + 1e-9 >= be_asap_pts
            if open_t.side == "UP":
                hit_tp = px + 1e-12 >= open_t.tp
                sl_px = open_t.entry if be_on else open_t.sl_init
                hit_sl = px <= sl_px + 1e-12
                trail_on = t_pts > 1e-12 and best_fav + 1e-9 >= t_arm
                trail_px = (open_t.entry + best_fav * ps) - t_pts * ps
                hit_trail = trail_on and px <= trail_px + 1e-12
            else:
                hit_tp = px - 1e-12 <= open_t.tp
                sl_px = open_t.entry if be_on else open_t.sl_init
                hit_sl = px >= sl_px - 1e-12
                trail_on = t_pts > 1e-12 and best_fav + 1e-9 >= t_arm
                trail_px = (open_t.entry - best_fav * ps) + t_pts * ps
                hit_trail = trail_on and px >= trail_px - 1e-12
            if hit_tp:
                close_trade(open_t, ts, open_t.tp, "tp")
            elif hit_sl:
                if be_on:
                    close_trade(open_t, ts, open_t.entry, "be")
                else:
                    close_trade(open_t, ts, open_t.sl_init, "sl")
            elif hit_trail:
                close_trade(open_t, ts, px, "trail")
            elif held + 1e-9 >= hold_sec:
                close_trade(open_t, ts, px, "timeout")
        elif pending is not None:
            if fade:
                bside = str(pending["burst_side"])
                ext = float(pending["extreme"])
                ref = float(pending["ref"])
                last_ext = float(pending["last_ext_epoch"])
                extended = False
                if bside == "UP" and mid > ext + 1e-12:
                    ext, last_ext, extended = mid, epoch, True
                elif bside == "DOWN" and mid < ext - 1e-12:
                    ext, last_ext, extended = mid, epoch, True
                if extended:
                    burst_now = (ext - ref) / ps if bside == "UP" else (ref - ext) / ps
                    if burst_now > max_pts + 1e-9:
                        pending = None
                    else:
                        pending["extreme"] = ext
                        pending["last_ext_epoch"] = last_ext
                        pending["burst_pts"] = round(burst_now, 1)
                if pending is not None:
                    if epoch - float(pending["detect_epoch"]) > pause_give_up + 1e-12:
                        pending = None
                    elif epoch - float(pending["last_ext_epoch"]) + 1e-12 >= pause_sec:
                        open_trade(
                            side=str(pending["side"]),
                            burst_pts=float(pending["burst_pts"]),
                            span=float(pending["span"]),
                            ts=ts,
                            epoch=epoch,
                            tick=t,
                            lag_used=pause_sec,
                        )
            elif epoch + 1e-12 >= float(pending["fill_at"]):
                open_trade(
                    side=str(pending["side"]),
                    burst_pts=float(pending["burst_pts"]),
                    span=float(pending["span"]),
                    ts=ts,
                    epoch=epoch,
                    tick=t,
                    lag_used=lag_sec,
                )
        else:
            spr = (t.ask - t.bid) / ps if ps > 0 else 0.0
            if (
                epoch >= cooldown_until
                and not weekend_reopen_blackout(ts, blackout_min)
                and in_session(ts, session)
                and (max_spread <= 1e-12 or spr <= max_spread + 1e-9)
            ):
                hit = _detect(dq, ps, min_pts, max_pts, persist, window_sec)
                if hit is not None:
                    burst_side, burst_pts, span = hit
                    if (not use_1m) or _1m_ok(builder, burst_side, min_1m, ps):
                        side = ("DOWN" if burst_side == "UP" else "UP") if fade else burst_side
                        wait_stall = fade and pause_sec > 1e-12
                        wait_lag = (not fade) and lag_sec > 1e-12
                        if wait_stall:
                            ref = dq[0][1] if dq else mid
                            pending = {
                                "side": side,
                                "burst_side": burst_side,
                                "burst_pts": round(burst_pts, 1),
                                "span": round(span, 3),
                                "extreme": mid,
                                "ref": ref,
                                "last_ext_epoch": epoch,
                                "detect_epoch": epoch,
                            }
                        elif wait_lag:
                            pending = {
                                "fill_at": epoch + lag_sec,
                                "side": side,
                                "burst_pts": round(burst_pts, 1),
                                "span": round(span, 3),
                            }
                        else:
                            open_trade(
                                side=side,
                                burst_pts=burst_pts,
                                span=span,
                                ts=ts,
                                epoch=epoch,
                                tick=t,
                                lag_used=0.0,
                            )

        now = time.monotonic()
        if now - last_yield >= 0.25 or i == n - 1:
            last_yield = now
            time.sleep(0.002)
            if progress:
                progress(
                    ticks_done=i + 1,
                    ticks_total=n,
                    trades=len(trades) + (1 if open_t else 0),
                    rows=live_rows(),
                    pct=round(70.0 + 28.0 * ((i + 1) / n), 1),
                )

    if open_t is not None:
        last = ticks[-1]
        close_trade(open_t, to_utc(last.ts), mark_px(open_t.side, last), "timeout")

    return summarize_burst(trades, params, symbol=sym, ticks=n)


def summarize_burst(
    trades: Sequence[BurstTrade],
    params: BurstParams,
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

    def pct(a: int, b: int) -> Optional[float]:
        if b <= 0:
            return None
        return round(100.0 * a / b, 1)

    gp = sum(t.pts for t in trades if t.pts > 0)
    gl = -sum(t.pts for t in trades if t.pts < 0)
    return {
        "kind": "micro_fade" if str(params.mode or "with").lower() == "fade" else "micro_momentum",
        "symbol": symbol,
        "params": asdict(params),
        "ticks": ticks,
        "trades": n,
        "wins": wins,
        "losses": losses,
        "scratches": n - wins - losses,
        "win_pct": pct(wins, n),
        "tp_n": by.get("tp", 0),
        "tp_pct": pct(by.get("tp", 0), n),
        "sl_n": by.get("sl", 0),
        "sl_pct": pct(by.get("sl", 0), n),
        "trail_n": by.get("trail", 0),
        "trail_pct": pct(by.get("trail", 0), n),
        "timeout_n": by.get("timeout", 0),
        "timeout_pct": pct(by.get("timeout", 0), n),
        "be_n": by.get("be", 0),
        "be_pct": pct(by.get("be", 0), n),
        "exits": by,
        "avg_pts": round(sum(t.pts for t in trades) / n, 1) if n else 0.0,
        "sum_pts": round(sum(t.pts for t in trades), 1),
        "profit_factor": round(gp / gl, 2) if gl > 1e-9 else None,
        "partial": partial,
        "rows": [asdict(t) for t in trades],
    }
