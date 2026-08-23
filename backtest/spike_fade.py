"""
Fade a 1–3s spike of at least 2000 pts: enter opposite immediately,
TP / SL as a % of that spike (or fixed pts if % is 0),
trail 1000 behind best fav (arms at +1000 = BE),
max hold 2 minutes. Skip first 10 minutes after weekend reopen (Sun 22:00 UTC).

Pure — no web, no MT5.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol


@dataclass
class FadeParams:
    window_sec: float = 3.0
    min_spike_pts: float = 2000.0
    tp_pts: float = 2000.0
    sl_pts: float = 2000.0
    tp_pct: float = 100.0  # % of this spike; 0 = use tp_pts
    sl_pct: float = 100.0  # % of this spike; 0 = use sl_pts
    trail_pts: float = 1000.0
    trail_arm_pts: float = 0.0  # 0 = arm when fav reaches trail_pts
    confirm_pts: float = 0.0  # wait for this much bounce from the extreme; 0 = off
    confirm_timeout_sec: float = 5.0  # drop the signal if no bounce in time
    max_extreme_age_sec: float = 0.0  # 0 = off; only fire if window hi/lo printed this recently
    max_hold_sec: float = 120.0
    cooldown_sec: float = 30.0
    weekend_blackout_min: float = 10.0
    lag_sec: float = 0.0  # 0 / 1 / 2 — fill this many seconds after detect


@dataclass
class FadeTrade:
    entry_ts: str
    side: str  # UP fade of a dump, DOWN fade of a rip
    spike_dir: str
    spike_pts: float
    window_sec: float
    entry: float
    tp: float
    sl_init: float
    tp_pts: float = 0.0
    sl_pts: float = 0.0
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None  # tp | sl | trail | timeout
    pts: float = 0.0
    max_fav_pts: float = 0.0
    lag_sec: float = 0.0
    detect_px: Optional[float] = None
    hold_sec: Optional[float] = None


def target_pts(pct: float, spike_pts: float, fixed_pts: float) -> float:
    """Size TP/SL. pct > 0 → that fraction of the spike; else fixed pts."""
    if pct is not None and float(pct) > 0:
        return max(1.0, float(spike_pts) * (float(pct) / 100.0))
    return max(1.0, float(fixed_pts))


def to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def weekend_reopen_blackout(ts: datetime, minutes: float = 10.0) -> bool:
    """True in [Sunday 22:00 UTC, Sunday 22:00 + minutes)."""
    ts = to_utc(ts)
    if ts.weekday() != 6:  # Sunday
        return False
    sec = ts.hour * 3600 + ts.minute * 60 + ts.second + ts.microsecond / 1e6
    start = 22 * 3600
    return start <= sec < start + float(minutes) * 60.0


def _fav_pts(side: str, entry: float, px: float, ps: float) -> float:
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _detect(
    window: Deque[Tuple[float, float]],
    ps: float,
    min_pts: float,
    window_sec: float,
    hi: float,
    lo: float,
    max_extreme_age_sec: float = 0.0,
    hi_ts: float = 0.0,
    lo_ts: float = 0.0,
):
    if len(window) < 2 or ps <= 0:
        return None
    ref_ts, ref = window[0]
    last_ts, last = window[-1]
    span = last_ts - ref_ts
    if span < min(0.4, window_sec * 0.25):
        return None
    up = (hi - ref) / ps
    down = (ref - lo) / ps
    if up >= down and up + 1e-9 >= min_pts:
        side, spike, extreme, ext_ts = "UP", up, hi, hi_ts
    elif down > up and down + 1e-9 >= min_pts:
        side, spike, extreme, ext_ts = "DOWN", down, lo, lo_ts
    else:
        return None
    if max_extreme_age_sec > 1e-12 and last_ts - ext_ts > max_extreme_age_sec + 1e-12:
        return None
    return side, spike, span, last, extreme


def _retraced(side: str, extreme: float, px: float, confirm_pts: float, ps: float) -> bool:
    """True when price has bounced `confirm_pts` from the spike extreme toward the fade."""
    if confirm_pts <= 1e-12:
        return True
    need = float(confirm_pts) * ps
    if side == "UP":  # dump → long; extreme is the low
        return px + 1e-12 >= extreme + need
    return px - 1e-12 <= extreme - need


def run_spike_fade(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[FadeParams] = None,
    progress=None,
) -> Dict[str, Any]:
    params = params or FadeParams()
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return summarize_fade([], params, symbol=sym, ticks=len(ticks or []))

    window_sec = float(params.window_sec)
    min_pts = float(params.min_spike_pts)
    tp_fixed = float(params.tp_pts)
    sl_fixed = float(params.sl_pts)
    tp_pct = float(params.tp_pct if params.tp_pct is not None else 0.0)
    sl_pct = float(params.sl_pct if params.sl_pct is not None else 0.0)
    trail_pts = float(params.trail_pts)
    arm_pts = float(params.trail_arm_pts or 0.0)
    if arm_pts <= 1e-12:
        arm_pts = trail_pts
    confirm_pts = float(params.confirm_pts or 0.0)
    confirm_timeout = max(0.5, float(params.confirm_timeout_sec or 5.0))
    max_ext_age = float(params.max_extreme_age_sec or 0.0)

    def levels(side: str, fill_px: float, spike: float) -> Tuple[float, float, float, float]:
        tp_off = target_pts(tp_pct, spike, tp_fixed)
        sl_off = target_pts(sl_pct, spike, sl_fixed)
        if side == "UP":
            return fill_px + tp_off * ps, fill_px - sl_off * ps, tp_off, sl_off
        return fill_px - tp_off * ps, fill_px + sl_off * ps, tp_off, sl_off
    hold_sec = float(params.max_hold_sec)
    cd_sec = float(params.cooldown_sec)
    blackout_min = float(params.weekend_blackout_min)
    lag_sec = max(0.0, float(params.lag_sec or 0.0))

    dq: Deque[Tuple[float, float]] = deque()
    trades: List[FadeTrade] = []
    open_t: Optional[FadeTrade] = None
    pending: Optional[Dict[str, Any]] = None
    best_fav = 0.0
    entry_epoch = 0.0
    cooldown_until = 0.0
    suppress_until = 0.0
    win_hi = float("-inf")
    win_lo = float("inf")
    win_hi_ts = 0.0
    win_lo_ts = 0.0
    n = len(ticks)
    last_yield = time.monotonic()

    def close_trade(tr: FadeTrade, ts: datetime, px: float, reason: str) -> None:
        nonlocal open_t, best_fav, cooldown_until
        pts = _fav_pts(tr.side, tr.entry, px, ps)
        if reason == "trail" and pts < 0 and arm_pts + 1e-9 >= trail_pts:
            pts = 0.0  # default trail arms at BE; skip tick-noise reds
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

    for i, t in enumerate(ticks):
        ts = t.ts if t.ts.tzinfo is not None else to_utc(t.ts)
        epoch = ts.timestamp()
        px = t.mid
        dq.append((epoch, px))
        if px >= win_hi:
            win_hi = px
            win_hi_ts = epoch
        if px <= win_lo:
            win_lo = px
            win_lo_ts = epoch
        cutoff = epoch - window_sec
        popped = False
        while dq and dq[0][0] < cutoff:
            dq.popleft()
            popped = True
        if popped and dq:
            win_hi, win_lo = float("-inf"), float("inf")
            win_hi_ts = win_lo_ts = 0.0
            for e, p in dq:
                if p >= win_hi:
                    win_hi = p
                    win_hi_ts = e
                if p <= win_lo:
                    win_lo = p
                    win_lo_ts = e
        elif not dq:
            win_hi, win_lo = float("-inf"), float("inf")
            win_hi_ts = win_lo_ts = 0.0

        if open_t is not None:
            fav = _fav_pts(open_t.side, open_t.entry, px, ps)
            if fav > best_fav:
                best_fav = fav
            held = epoch - entry_epoch
            if open_t.side == "UP":
                hit_tp = px + 1e-12 >= open_t.tp
                hit_hard = px <= open_t.sl_init + 1e-12
                trail_on = best_fav + 1e-9 >= arm_pts
                trail_px = (open_t.entry + best_fav * ps) - trail_pts * ps
                hit_trail = trail_on and px <= trail_px + 1e-12
            else:
                hit_tp = px - 1e-12 <= open_t.tp
                hit_hard = px >= open_t.sl_init - 1e-12
                trail_on = best_fav + 1e-9 >= arm_pts
                trail_px = (open_t.entry - best_fav * ps) + trail_pts * ps
                hit_trail = trail_on and px >= trail_px - 1e-12

            if hit_tp:
                close_trade(open_t, ts, open_t.tp, "tp")
            elif hit_hard:
                close_trade(open_t, ts, open_t.sl_init, "sl")
            elif hit_trail:
                close_trade(open_t, ts, px, "trail")
            elif held + 1e-9 >= hold_sec:
                close_trade(open_t, ts, px, "timeout")
        elif pending is not None:
            if epoch > float(pending["deadline"]) + 1e-12:
                pending = None
                suppress_until = epoch + window_sec
            elif epoch + 1e-12 >= float(pending["fill_at"]) and _retraced(
                pending["side"],
                float(pending["extreme"]),
                px,
                confirm_pts,
                ps,
            ):
                fill_px = px
                side = pending["side"]
                spike = float(pending["spike_pts"])
                tp, sl, tp_off, sl_off = levels(side, fill_px, spike)
                open_t = FadeTrade(
                    entry_ts=ts.isoformat(),
                    side=side,
                    spike_dir=pending["spike_dir"],
                    spike_pts=spike,
                    window_sec=pending["span"],
                    entry=round(fill_px, 5),
                    tp=round(tp, 5),
                    sl_init=round(sl, 5),
                    tp_pts=round(tp_off, 1),
                    sl_pts=round(sl_off, 1),
                    lag_sec=lag_sec,
                    detect_px=pending["detect_px"],
                )
                best_fav = 0.0
                entry_epoch = epoch
                pending = None
        else:
            if (
                epoch >= cooldown_until
                and epoch >= suppress_until
                and not weekend_reopen_blackout(ts, blackout_min)
            ):
                hit = _detect(
                    dq,
                    ps,
                    min_pts,
                    window_sec,
                    win_hi,
                    win_lo,
                    max_ext_age,
                    win_hi_ts,
                    win_lo_ts,
                )
                if hit is not None:
                    spike_dir, spike_pts, span, last_px, extreme = hit
                    side = "DOWN" if spike_dir == "UP" else "UP"
                    wait = lag_sec > 1e-12 or confirm_pts > 1e-12
                    if not wait:
                        tp, sl, tp_off, sl_off = levels(side, last_px, spike_pts)
                        open_t = FadeTrade(
                            entry_ts=ts.isoformat(),
                            side=side,
                            spike_dir=spike_dir,
                            spike_pts=round(spike_pts, 1),
                            window_sec=round(span, 3),
                            entry=round(last_px, 5),
                            tp=round(tp, 5),
                            sl_init=round(sl, 5),
                            tp_pts=round(tp_off, 1),
                            sl_pts=round(sl_off, 1),
                            lag_sec=0.0,
                            detect_px=round(last_px, 5),
                        )
                        best_fav = 0.0
                        entry_epoch = epoch
                    else:
                        pending = {
                            "fill_at": epoch + lag_sec,
                            "deadline": epoch + lag_sec + confirm_timeout,
                            "side": side,
                            "spike_dir": spike_dir,
                            "spike_pts": round(spike_pts, 1),
                            "span": round(span, 3),
                            "detect_px": round(last_px, 5),
                            "extreme": extreme,
                        }

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

    return summarize_fade(trades, params, symbol=sym, ticks=n)


def summarize_fade(
    trades: Sequence[FadeTrade],
    params: FadeParams,
    *,
    symbol: str,
    ticks: int,
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
        "kind": "spike_fade",
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
        "exits": by,
        "avg_pts": round(sum(t.pts for t in trades) / n, 1) if n else 0.0,
        "sum_pts": round(sum(t.pts for t in trades), 1),
        "profit_factor": round(gp / gl, 2) if gl > 1e-9 else None,
        "rows": [asdict(t) for t in trades],
    }
