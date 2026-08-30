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

from backtest.candles import CandleBuilder
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.spike_fade import weekend_reopen_blackout


# UTC hour windows. Asia wraps midnight (Sydney/Tokyo into London open).
SESSION_HELP = {
    "all": "Every hour (weekend blackout still applies).",
    "asia": "22:00–07:00 UTC (Asia / gold overnight).",
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
    session: str = "all"  # all | asia | asia_london | london_ny
    max_spread_pts: float = 50.0  # skip new entries if spread wider than this


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


def to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def in_session(ts: datetime, session: str) -> bool:
    """True if `ts` is inside the named UTC session window."""
    mode = (session or "all").strip().lower().replace("-", "_").replace("+", "_")
    if mode in ("all", "any", "all_day", "allday"):
        return True
    h = to_utc(ts).hour
    if mode == "asia":
        return h >= 22 or h < 7
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

    def levels(side: str, fill_px: float) -> Tuple[float, float]:
        if side == "UP":
            return fill_px + tp_pts * ps, fill_px - sl_pts * ps
        return fill_px - tp_pts * ps, fill_px + sl_pts * ps

    def fill_px(side: str, tick: Tick) -> float:
        return tick.ask if side == "UP" else tick.bid

    def mark_px(side: str, tick: Tick) -> float:
        """Price we can actually exit at."""
        return tick.bid if side == "UP" else tick.ask

    def close_trade(tr: BurstTrade, ts: datetime, px: float, reason: str) -> None:
        nonlocal open_t, best_fav, cooldown_until
        pts = _fav_pts(tr.side, tr.entry, px, ps)
        if reason == "trail" and pts < 0 and arm_pts + 1e-9 >= trail_pts:
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
            if open_t.side == "UP":
                hit_tp = px + 1e-12 >= open_t.tp
                hit_sl = px <= open_t.sl_init + 1e-12
                trail_on = trail_pts > 1e-12 and best_fav + 1e-9 >= arm_pts
                trail_px = (open_t.entry + best_fav * ps) - trail_pts * ps
                hit_trail = trail_on and px <= trail_px + 1e-12
            else:
                hit_tp = px - 1e-12 <= open_t.tp
                hit_sl = px >= open_t.sl_init - 1e-12
                trail_on = trail_pts > 1e-12 and best_fav + 1e-9 >= arm_pts
                trail_px = (open_t.entry - best_fav * ps) + trail_pts * ps
                hit_trail = trail_on and px >= trail_px - 1e-12
            if hit_tp:
                close_trade(open_t, ts, open_t.tp, "tp")
            elif hit_sl:
                close_trade(open_t, ts, open_t.sl_init, "sl")
            elif hit_trail:
                close_trade(open_t, ts, px, "trail")
            elif held + 1e-9 >= hold_sec:
                close_trade(open_t, ts, px, "timeout")
        elif pending is not None:
            if epoch + 1e-12 >= float(pending["fill_at"]):
                side = pending["side"]
                fill = fill_px(side, t)
                tp, sl = levels(side, fill)
                spr = (t.ask - t.bid) / ps
                open_t = BurstTrade(
                    entry_ts=ts.isoformat(),
                    side=side,
                    burst_pts=float(pending["burst_pts"]),
                    window_sec=float(pending["span"]),
                    entry=round(fill, 5),
                    tp=round(tp, 5),
                    sl_init=round(sl, 5),
                    tp_pts=round(tp_pts, 1),
                    sl_pts=round(sl_pts, 1),
                    spread_pts=round(spr, 1),
                    lag_sec=lag_sec,
                    session_hour=ts.hour,
                )
                best_fav = 0.0
                entry_epoch = epoch
                pending = None
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
                    side, burst_pts, span = hit
                    if (not use_1m) or _1m_ok(builder, side, min_1m, ps):
                        if lag_sec > 1e-12:
                            pending = {
                                "fill_at": epoch + lag_sec,
                                "side": side,
                                "burst_pts": round(burst_pts, 1),
                                "span": round(span, 3),
                            }
                        else:
                            fill = fill_px(side, t)
                            tp, sl = levels(side, fill)
                            open_t = BurstTrade(
                                entry_ts=ts.isoformat(),
                                side=side,
                                burst_pts=round(burst_pts, 1),
                                window_sec=round(span, 3),
                                entry=round(fill, 5),
                                tp=round(tp, 5),
                                sl_init=round(sl, 5),
                                tp_pts=round(tp_pts, 1),
                                sl_pts=round(sl_pts, 1),
                                spread_pts=round(spr, 1),
                                lag_sec=0.0,
                                session_hour=ts.hour,
                            )
                            best_fav = 0.0
                            entry_epoch = epoch

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
        "kind": "micro_momentum",
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
        "partial": partial,
        "rows": [asdict(t) for t in trades],
    }
