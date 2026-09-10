"""
Impulse Fork — classify a gold blast, then fade or join (never both).

Detect a 3s rip/dump. In the next 10s: snapback → fade the extreme.
No snap: wait for a 50% retrace toward the origin → join the blast.
Chase / one-way tape → skip or stand aside.

No session box. No extra oscillators. News days allowed.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.spike_fade import _detect, _fav_pts, to_utc, weekend_reopen_blackout


@dataclass
class ForkParams:
    window_sec: float = 3.0
    min_blast_pts: float = 1100.0
    snap_pts: float = 300.0
    snap_sec: float = 10.0
    join_retrace: float = 0.50
    join_wait_sec: float = 90.0
    chase_ext: float = 0.50
    fade_lag_sec: float = 1.0
    fade_sl_pct: float = 100.0
    fade_sl_cap_pts: float = 1500.0
    fade_tp_pct: float = 200.0
    fade_tp_cap_pts: float = 3000.0
    fade_trail_pts: float = 600.0
    fade_trail_arm_pts: float = 750.0
    fade_hold_sec: float = 250.0
    join_stop_beyond: float = 0.15
    join_tp1_r: float = 1.0
    join_tp2_r: float = 1.5
    join_be_r: float = 0.1
    join_hold_sec: float = 1200.0
    cooldown_sec: float = 30.0
    weekend_blackout_min: float = 10.0
    stand_aside_n: int = 3
    skip_london_utc: bool = True
    london_start_hour: int = 7
    london_end_hour: int = 10
    fade_enabled: bool = True
    join_enabled: bool = True
    stand_aside_enabled: bool = True
    risk_pct: float = 0.5
    start_equity: float = 1_000.0
    daily_halt_r: float = 1.5
    weekly_halt_r: float = 4.0


@dataclass
class ForkTrade:
    entry_ts: str
    mode: str  # fade | join
    side: str  # UP | DOWN
    blast_dir: str
    blast_pts: float
    origin: float
    extreme: float
    entry: float
    sl: float
    tp1: float
    tp2: float
    sl_pts: float
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None
    pts: float = 0.0
    r: float = 0.0
    tp1_hit: bool = False
    size: float = 0.0
    equity_after: Optional[float] = None
    hold_sec: Optional[float] = None


@dataclass
class ForkSkip:
    ts: str
    reason: str
    blast_pts: Optional[float] = None
    blast_dir: Optional[str] = None
    detail: Optional[str] = None


def _hit_stop(side: str, px: float, sl: float) -> bool:
    if side == "UP":
        return px <= sl + 1e-12
    return px >= sl - 1e-12


def _hit_tp(side: str, px: float, tp: float) -> bool:
    if side == "UP":
        return px >= tp - 1e-12
    return px <= tp + 1e-12


def _week_key(ts: datetime) -> Tuple[int, int]:
    iso = to_utc(ts).isocalendar()
    return int(iso[0]), int(iso[1])


def _in_london_skip(ts: datetime, params: ForkParams) -> bool:
    if not params.skip_london_utc:
        return False
    h = to_utc(ts).hour
    return int(params.london_start_hour) <= h < int(params.london_end_hour)


def retrace_pts(blast_dir: str, extreme: float, px: float, ps: float) -> float:
    if blast_dir == "UP":
        return (extreme - px) / ps
    return (px - extreme) / ps


def join_level(blast_dir: str, origin: float, extreme: float, frac: float) -> float:
    if blast_dir == "UP":
        return extreme - frac * (extreme - origin)
    return extreme + frac * (origin - extreme)


def origin_taken(blast_dir: str, origin: float, px: float) -> bool:
    if blast_dir == "UP":
        return px <= origin + 1e-12
    return px >= origin - 1e-12


def chased(blast_dir: str, extreme: float, px: float, spike_pts: float, ps: float, ext: float) -> bool:
    extra = float(ext) * spike_pts * ps
    if blast_dir == "UP":
        return px + 1e-12 >= extreme + extra
    return px - 1e-12 <= extreme - extra


def fade_levels(
    fade_side: str,
    fill: float,
    spike_pts: float,
    params: ForkParams,
    ps: float,
) -> Tuple[float, float, float]:
    sl_off = min(
        spike_pts * float(params.fade_sl_pct) / 100.0,
        float(params.fade_sl_cap_pts),
    )
    tp_off = min(
        spike_pts * float(params.fade_tp_pct) / 100.0,
        float(params.fade_tp_cap_pts),
    )
    if fade_side == "UP":
        return fill + tp_off * ps, fill - sl_off * ps, sl_off
    return fill - tp_off * ps, fill + sl_off * ps, sl_off


def join_levels(
    join_side: str,
    fill: float,
    origin: float,
    extreme: float,
    spike_pts: float,
    params: ForkParams,
    ps: float,
) -> Tuple[float, float, float, float]:
    beyond = float(params.join_stop_beyond) * spike_pts * ps
    if join_side == "UP":
        sl = origin - beyond
    else:
        sl = origin + beyond
    sl_pts = abs(fill - sl) / ps
    if sl_pts <= 1e-9:
        sl_pts = max(1.0, 0.15 * spike_pts)
        sl = fill - sl_pts * ps if join_side == "UP" else fill + sl_pts * ps
    rpx = sl_pts * ps
    tp1 = fill + float(params.join_tp1_r) * rpx if join_side == "UP" else fill - float(params.join_tp1_r) * rpx
    dist2 = float(params.join_tp2_r) * rpx
    # cap TP2 at the blast extreme if that is closer
    if join_side == "UP":
        tp2 = min(fill + dist2, extreme) if extreme > fill else fill + dist2
    else:
        tp2 = max(fill - dist2, extreme) if extreme < fill else fill - dist2
    return sl, tp1, tp2, sl_pts


def run_impulse_fork(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[ForkParams] = None,
    progress=None,
) -> Dict[str, Any]:
    params = params or ForkParams()
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return summarize_fork([], [], params, symbol=sym, ticks=len(ticks or []))

    window_sec = float(params.window_sec)
    min_pts = float(params.min_blast_pts)
    snap_pts = float(params.snap_pts)
    snap_sec = float(params.snap_sec)
    join_wait = float(params.join_wait_sec)
    cd_sec = float(params.cooldown_sec)
    blackout = float(params.weekend_blackout_min)
    lag = max(0.0, float(params.fade_lag_sec))

    dq: Deque[Tuple[float, float]] = deque()
    win_hi = float("-inf")
    win_lo = float("inf")
    win_hi_ts = 0.0
    win_lo_ts = 0.0

    trades: List[ForkTrade] = []
    skips: List[ForkSkip] = []
    equity = float(params.start_equity)
    peak_eq = equity
    max_dd_pct = 0.0
    daily_r: Dict[str, float] = defaultdict(float)
    weekly_r: Dict[Tuple[int, int], float] = defaultdict(float)
    weekly_off_until = 0.0
    cooldown_until = 0.0
    suppress_until = 0.0
    aside = False
    recent: Deque[str] = deque(maxlen=max(1, int(params.stand_aside_n)))

    # pending blast classification
    blast: Optional[Dict[str, Any]] = None
    open_t: Optional[ForkTrade] = None
    open_meta: Optional[Dict[str, Any]] = None

    n = len(ticks)
    step = max(n // 40, 80_000)

    def record_outcome(label: str, ts: datetime) -> None:
        nonlocal aside
        recent.append(label)
        if label == "snap":
            aside = False
            return
        if not params.stand_aside_enabled:
            return
        need = int(params.stand_aside_n)
        if len(recent) >= need and all(x in ("chase", "join_dead", "join_timeout") for x in list(recent)[-need:]):
            aside = True

    def apply_pnl(tr: ForkTrade, ts: datetime) -> None:
        nonlocal equity, peak_eq, max_dd_pct
        sl_pts = tr.sl_pts if tr.sl_pts > 1e-9 else 1.0
        tr.r = round(tr.pts / sl_pts, 3)
        risk_cash = equity * (float(params.risk_pct) / 100.0)
        sl_px = sl_pts * ps
        tr.size = round(risk_cash / sl_px, 4) if sl_px > 0 else 0.0
        equity = equity + risk_cash * tr.r
        tr.equity_after = round(equity, 2)
        if equity > peak_eq:
            peak_eq = equity
        if peak_eq > 0:
            dd = (peak_eq - equity) / peak_eq * 100.0
            if dd > max_dd_pct:
                max_dd_pct = dd
        day = to_utc(ts).date().isoformat()
        daily_r[day] += tr.r
        weekly_r[_week_key(ts)] += tr.r

    def close_open(ts: datetime, px: float, reason: str, pts: Optional[float] = None) -> None:
        nonlocal open_t, open_meta, cooldown_until
        assert open_t is not None
        if pts is None:
            pts = _fav_pts(open_t.side, open_t.entry, px, ps)
        open_t.exit_ts = ts.isoformat()
        open_t.exit = round(px, 5)
        open_t.exit_reason = reason
        open_t.pts = round(pts, 1)
        try:
            t0 = datetime.fromisoformat(open_t.entry_ts)
            open_t.hold_sec = round((to_utc(ts) - to_utc(t0)).total_seconds(), 2)
        except Exception:
            open_t.hold_sec = None
        apply_pnl(open_t, ts)
        trades.append(open_t)
        open_t = None
        open_meta = None
        cooldown_until = ts.timestamp() + cd_sec

    def halted(ts: datetime) -> Optional[str]:
        day = to_utc(ts).date().isoformat()
        if daily_r[day] <= -float(params.daily_halt_r):
            return "daily_halt"
        wk = _week_key(ts)
        if weekly_r[wk] <= -float(params.weekly_halt_r):
            return "weekly_halt"
        if ts.timestamp() < weekly_off_until:
            return "weekly_halt"
        return None

    for i, t in enumerate(ticks):
        ts = t.ts if t.ts.tzinfo is not None else to_utc(t.ts)
        epoch = ts.timestamp()
        px = t.mid

        if progress and n > 80_000 and ((i + 1) % step == 0 or i + 1 == n):
            progress(
                phase="replay",
                ticks_done=i + 1,
                ticks_total=n,
                trades=len(trades),
                message=f"ticks {i + 1:,}/{n:,} · {len(trades)} trades",
            )

        dq.append((epoch, px))
        if px >= win_hi:
            win_hi, win_hi_ts = px, epoch
        if px <= win_lo:
            win_lo, win_lo_ts = px, epoch
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
                    win_hi, win_hi_ts = p, e
                if p <= win_lo:
                    win_lo, win_lo_ts = p, e
        elif not dq:
            win_hi, win_lo = float("-inf"), float("inf")
            win_hi_ts = win_lo_ts = 0.0

        # manage open trade
        if open_t is not None and open_meta is not None:
            side = open_t.side
            fav = _fav_pts(side, open_t.entry, px, ps)
            if fav > open_meta["best_fav"]:
                open_meta["best_fav"] = fav
            held = epoch - open_meta["entry_epoch"]
            if open_t.mode == "fade":
                trail_on = open_meta["best_fav"] + 1e-9 >= float(params.fade_trail_arm_pts)
                if side == "UP":
                    trail_px = (open_t.entry + open_meta["best_fav"] * ps) - float(params.fade_trail_pts) * ps
                    hit_trail = trail_on and px <= trail_px + 1e-12
                else:
                    trail_px = (open_t.entry - open_meta["best_fav"] * ps) + float(params.fade_trail_pts) * ps
                    hit_trail = trail_on and px >= trail_px - 1e-12
                if _hit_tp(side, px, open_t.tp1):
                    close_open(ts, open_t.tp1, "tp")
                elif _hit_stop(side, px, open_t.sl):
                    close_open(ts, open_t.sl, "sl")
                elif hit_trail:
                    close_open(ts, px, "trail")
                elif held + 1e-9 >= float(params.fade_hold_sec):
                    close_open(ts, px, "timeout")
            else:
                # join partial
                if not open_meta["tp1_hit"]:
                    if _hit_stop(side, px, open_t.sl):
                        close_open(ts, open_t.sl, "sl")
                    elif _hit_tp(side, px, open_t.tp1):
                        open_meta["tp1_hit"] = True
                        open_t.tp1_hit = True
                        be = float(params.join_be_r) * open_t.sl_pts * ps
                        open_t.sl = open_t.entry + be if side == "UP" else open_t.entry - be
                        if _hit_tp(side, px, open_t.tp2):
                            pts = 0.5 * (open_t.sl_pts * params.join_tp1_r) + 0.5 * _fav_pts(
                                side, open_t.entry, open_t.tp2, ps
                            )
                            close_open(ts, open_t.tp2, "tp2", pts=pts)
                    elif held + 1e-9 >= float(params.join_hold_sec):
                        close_open(ts, px, "timeout")
                else:
                    if _hit_stop(side, px, open_t.sl):
                        pts = 0.5 * (open_t.sl_pts * params.join_tp1_r) + 0.5 * _fav_pts(
                            side, open_t.entry, open_t.sl, ps
                        )
                        close_open(ts, open_t.sl, "sl", pts=pts)
                    elif _hit_tp(side, px, open_t.tp2):
                        pts = 0.5 * (open_t.sl_pts * params.join_tp1_r) + 0.5 * _fav_pts(
                            side, open_t.entry, open_t.tp2, ps
                        )
                        close_open(ts, open_t.tp2, "tp2", pts=pts)
                    elif held + 1e-9 >= float(params.join_hold_sec):
                        pts = 0.5 * (open_t.sl_pts * params.join_tp1_r) + 0.5 * _fav_pts(
                            side, open_t.entry, px, ps
                        )
                        close_open(ts, px, "timeout", pts=pts)
            continue

        # classify / fill pending blast
        if blast is not None:
            age = epoch - float(blast["t0"])
            bdir = blast["dir"]
            extreme = float(blast["extreme"])
            origin = float(blast["origin"])
            spike = float(blast["spike_pts"])
            phase = blast["phase"]

            if phase == "snap":
                if chased(bdir, extreme, px, spike, ps, params.chase_ext):
                    skips.append(
                        ForkSkip(
                            ts=ts.isoformat(),
                            reason="chase",
                            blast_pts=spike,
                            blast_dir=bdir,
                        )
                    )
                    record_outcome("chase", ts)
                    blast = None
                    suppress_until = epoch + window_sec
                    continue
                if retrace_pts(bdir, extreme, px, ps) + 1e-9 >= snap_pts:
                    blast["phase"] = "fade_wait"
                    blast["fill_at"] = epoch + lag
                    continue
                if age + 1e-9 >= snap_sec:
                    blast["phase"] = "join"
                    continue
            elif phase == "fade_wait":
                if epoch + 1e-12 >= float(blast["fill_at"]):
                    if not params.fade_enabled:
                        skips.append(
                            ForkSkip(ts=ts.isoformat(), reason="fade_off", blast_pts=spike, blast_dir=bdir)
                        )
                        record_outcome("snap", ts)
                        blast = None
                        continue
                    halt = halted(ts)
                    if halt:
                        skips.append(ForkSkip(ts=ts.isoformat(), reason=halt, blast_pts=spike, blast_dir=bdir))
                        blast = None
                        continue
                    fade_side = "DOWN" if bdir == "UP" else "UP"
                    tp, sl, sl_off = fade_levels(fade_side, px, spike, params, ps)
                    open_t = ForkTrade(
                        entry_ts=ts.isoformat(),
                        mode="fade",
                        side=fade_side,
                        blast_dir=bdir,
                        blast_pts=round(spike, 1),
                        origin=round(origin, 5),
                        extreme=round(extreme, 5),
                        entry=round(px, 5),
                        sl=round(sl, 5),
                        tp1=round(tp, 5),
                        tp2=round(tp, 5),
                        sl_pts=round(sl_off, 1),
                    )
                    open_meta = {"entry_epoch": epoch, "best_fav": 0.0, "tp1_hit": False}
                    record_outcome("snap", ts)
                    blast = None
                    suppress_until = epoch + window_sec
                    continue
            elif phase == "join":
                if chased(bdir, extreme, px, spike, ps, params.chase_ext):
                    skips.append(
                        ForkSkip(ts=ts.isoformat(), reason="chase", blast_pts=spike, blast_dir=bdir)
                    )
                    record_outcome("chase", ts)
                    blast = None
                    suppress_until = epoch + window_sec
                    continue
                if origin_taken(bdir, origin, px):
                    skips.append(
                        ForkSkip(ts=ts.isoformat(), reason="join_dead", blast_pts=spike, blast_dir=bdir)
                    )
                    record_outcome("join_dead", ts)
                    blast = None
                    suppress_until = epoch + window_sec
                    continue
                if age + 1e-9 >= join_wait:
                    skips.append(
                        ForkSkip(ts=ts.isoformat(), reason="join_timeout", blast_pts=spike, blast_dir=bdir)
                    )
                    record_outcome("join_timeout", ts)
                    blast = None
                    suppress_until = epoch + window_sec
                    continue
                lvl = join_level(bdir, origin, extreme, float(params.join_retrace))
                touched = (bdir == "UP" and px <= lvl + 1e-12) or (bdir == "DOWN" and px >= lvl - 1e-12)
                if touched:
                    if aside and params.stand_aside_enabled:
                        skips.append(
                            ForkSkip(
                                ts=ts.isoformat(),
                                reason="stand_aside",
                                blast_pts=spike,
                                blast_dir=bdir,
                            )
                        )
                        blast = None
                        continue
                    if not params.join_enabled:
                        skips.append(
                            ForkSkip(ts=ts.isoformat(), reason="join_off", blast_pts=spike, blast_dir=bdir)
                        )
                        blast = None
                        continue
                    halt = halted(ts)
                    if halt:
                        skips.append(ForkSkip(ts=ts.isoformat(), reason=halt, blast_pts=spike, blast_dir=bdir))
                        blast = None
                        continue
                    join_side = "UP" if bdir == "UP" else "DOWN"
                    sl, tp1, tp2, sl_pts = join_levels(
                        join_side, px, origin, extreme, spike, params, ps
                    )
                    open_t = ForkTrade(
                        entry_ts=ts.isoformat(),
                        mode="join",
                        side=join_side,
                        blast_dir=bdir,
                        blast_pts=round(spike, 1),
                        origin=round(origin, 5),
                        extreme=round(extreme, 5),
                        entry=round(px, 5),
                        sl=round(sl, 5),
                        tp1=round(tp1, 5),
                        tp2=round(tp2, 5),
                        sl_pts=round(sl_pts, 1),
                    )
                    open_meta = {"entry_epoch": epoch, "best_fav": 0.0, "tp1_hit": False}
                    blast = None
                    suppress_until = epoch + window_sec
                    continue
            continue

        if epoch < cooldown_until or epoch < suppress_until:
            continue
        if weekend_reopen_blackout(ts, blackout):
            continue
        if open_t is not None:
            continue
        if halted(ts):
            continue
        if _in_london_skip(ts, params):
            continue
        if aside:
            # still detect snapbacks to clear stand-aside; do not enter
            pass

        hit = _detect(dq, ps, min_pts, window_sec, win_hi, win_lo, 0.0, win_hi_ts, win_lo_ts)
        if hit is None:
            continue
        bdir, spike, span, last_px, extreme = hit
        origin = dq[0][1]
        if aside and params.stand_aside_enabled:
            # only a snap can clear; start classify but fade/join fills are blocked unless snap
            skips.append(
                ForkSkip(
                    ts=ts.isoformat(),
                    reason="stand_aside",
                    blast_pts=spike,
                    blast_dir=bdir,
                )
            )
            # still watch for snap to clear
            blast = {
                "phase": "snap",
                "dir": bdir,
                "spike_pts": spike,
                "extreme": extreme,
                "origin": origin,
                "t0": epoch,
                "aside_watch": True,
            }
            suppress_until = epoch + 0.2
            continue

        blast = {
            "phase": "snap",
            "dir": bdir,
            "spike_pts": spike,
            "extreme": extreme,
            "origin": origin,
            "t0": epoch,
        }
        suppress_until = epoch + 0.2

    # if a blast is still open at EOF, skip it
    if blast is not None:
        skips.append(
            ForkSkip(
                ts=ticks[-1].ts.isoformat() if ticks else "",
                reason="eof",
                blast_pts=float(blast.get("spike_pts") or 0),
                blast_dir=str(blast.get("dir")),
            )
        )
    if open_t is not None:
        last = ticks[-1]
        close_open(last.ts, last.mid, "timeout")

    return summarize_fork(
        trades, skips, params, symbol=sym, ticks=n, equity=equity, max_dd_pct=max_dd_pct
    )


def _pct(a: int, b: int) -> Optional[float]:
    if b <= 0:
        return None
    return round(100.0 * a / b, 1)


def _trade_stats(trades: Sequence[ForkTrade]) -> Dict[str, Any]:
    n = len(trades)
    wins = sum(1 for t in trades if t.r > 1e-9)
    losses = sum(1 for t in trades if t.r < -1e-9)
    gp = sum(t.r for t in trades if t.r > 0)
    gl = -sum(t.r for t in trades if t.r < 0)
    pf = round(gp / gl, 2) if gl > 1e-9 else None
    by_reason: Dict[str, int] = {}
    by_hour: Dict[str, List[ForkTrade]] = defaultdict(list)
    for t in trades:
        by_reason[t.exit_reason or "?"] = by_reason.get(t.exit_reason or "?", 0) + 1
        try:
            hour = datetime.fromisoformat(t.entry_ts.replace("Z", "+00:00")).hour
        except Exception:
            hour = -1
        by_hour[str(hour)].append(t)
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
    }


def summarize_fork(
    trades: Sequence[ForkTrade],
    skips: Sequence[ForkSkip],
    params: ForkParams,
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
    by_mode = {}
    for mode in ("fade", "join"):
        by_mode[mode] = _trade_stats([t for t in trades if t.mode == mode])
    return {
        "kind": "impulse_fork",
        "symbol": symbol,
        "params": asdict(params),
        "ticks": ticks,
        "skipped": len(skips),
        "skip_reasons": skip_reasons,
        **stats,
        "max_dd_pct": round(max_dd_pct, 2),
        "equity": round(equity, 2) if equity is not None else round(float(params.start_equity), 2),
        "start_equity": float(params.start_equity),
        "by_mode": by_mode,
        "rows": [asdict(t) for t in trades],
        "skips": [asdict(s) for s in skips][:2000],
        "skips_truncated": len(skips) > 2000,
    }
