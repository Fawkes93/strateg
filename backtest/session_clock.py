"""
Moldova H1 session-clock strategy (pure — no web, no MT5).

Direction: first of 6am → 5am → 4am with H−L ≥ $15 and a real body.
Entry: 07:00 local mid.
SL: 5am opposite extreme, at least sl_floor_pts from entry.
09:00: close if P&L ≥ 0; else hold for breakeven.
After 09:00: same SL, exit at BE (0 pts) or SL or flatten_hour (default 12:00).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import is_market_open
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.h1 import H1Bar, build_h1, index_h1


@dataclass
class SessionParams:
    timezone: str = "Europe/Chisinau"
    min_range_usd: float = 15.0
    min_body_pts: float = 200.0
    sl_floor_pts: float = 500.0
    define_hours: Tuple[int, ...] = (6, 5, 4)
    sl_hour: int = 5
    entry_hour: int = 7
    eval_hour: int = 9
    flatten_hour: int = 12


@dataclass
class SessionTrade:
    local_date: str
    side: str  # UP | DOWN
    defining_hour: int
    defining_open: float
    defining_high: float
    defining_low: float
    defining_close: float
    defining_range_usd: float
    sl_hour: int
    sl_high: float
    sl_low: float
    entry_ts: str
    entry: float
    sl: float
    sl_pts: float
    exit_ts: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None  # sl | eval_flat | be | noon_flat
    pts: float = 0.0


@dataclass
class SessionSkip:
    local_date: str
    reason: str


def _local(ts: datetime, tz: ZoneInfo) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    return ts.astimezone(tz)


def _at_local(d: date, hour: int, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time(hour, 0), tzinfo=tz)


def _mid(tick: Tick) -> float:
    return tick.mid


def pick_defining_bar(
    by_hour: Dict[Tuple[date, int], H1Bar],
    day: date,
    params: SessionParams,
    ps: float,
) -> Optional[H1Bar]:
    min_body = float(params.min_body_pts) * ps
    min_range = float(params.min_range_usd)
    for h in params.define_hours:
        bar = by_hour.get((day, int(h)))
        if bar is None:
            continue
        if (bar.high - bar.low) + 1e-12 < min_range:
            continue
        if abs(bar.close - bar.open) + 1e-12 < min_body:
            continue
        return bar
    return None


def sl_price(
    side: str,
    entry: float,
    bar5: H1Bar,
    *,
    sl_floor_pts: float,
    ps: float,
) -> float:
    floor = float(sl_floor_pts) * ps
    if side == "UP":
        extreme = float(bar5.low)
        if extreme >= entry - 1e-12:
            return entry - floor
        return min(extreme, entry - floor)
    extreme = float(bar5.high)
    if extreme <= entry + 1e-12:
        return entry + floor
    return max(extreme, entry + floor)


def _fav_pts(side: str, entry: float, px: float, ps: float) -> float:
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _hit_sl(side: str, px: float, sl: float) -> bool:
    if side == "UP":
        return px <= sl + 1e-12
    return px >= sl - 1e-12


def simulate_trade(
    ticks: Sequence[Tick],
    start_index: int,
    *,
    side: str,
    entry: float,
    sl: float,
    entry_local: datetime,
    eval_local: datetime,
    flatten_local: datetime,
    ps: float,
    tz: ZoneInfo,
) -> Tuple[str, datetime, float, float]:
    """
    Walk ticks after fill.
    Returns (reason, exit_ts, exit_px, pts).
    """
    seen_eval = False
    last_ts = ticks[start_index].ts
    last_px = entry

    for i in range(start_index + 1, len(ticks)):
        t = ticks[i]
        loc = _local(t.ts, tz)
        px = _mid(t)
        last_ts, last_px = t.ts, px

        if loc >= flatten_local:
            pts = _fav_pts(side, entry, px, ps)
            return "noon_flat", t.ts, px, pts

        if _hit_sl(side, px, sl):
            pts = _fav_pts(side, entry, sl, ps)
            return "sl", t.ts, sl, pts

        if loc >= eval_local:
            fav = _fav_pts(side, entry, px, ps)
            if not seen_eval:
                seen_eval = True
                if fav + 1e-12 >= 0.0:
                    return "eval_flat", t.ts, px, fav
            elif fav + 1e-12 >= 0.0:
                return "be", t.ts, px, 0.0

    pts = _fav_pts(side, entry, last_px, ps)
    return "noon_flat", last_ts, last_px, pts


def run_session(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[SessionParams] = None,
) -> Dict[str, Any]:
    params = params or SessionParams()
    tz = ZoneInfo(params.timezone)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return _empty_result(params, symbol=sym, ticks=len(ticks or []))

    bars = build_h1(ticks, params.timezone)
    by_hour = index_h1(bars)

    # Local dates that have any tick
    dates = sorted({_local(t.ts, tz).date() for t in ticks})

    # Pre-index first tick index per roughly-sorted stream
    trades: List[SessionTrade] = []
    skips: List[SessionSkip] = []
    i = 0
    n = len(ticks)

    def advance_to(ts_utc: datetime) -> int:
        nonlocal i
        while i < n and ticks[i].ts < ts_utc:
            i += 1
        return i

    for day in dates:
        entry_local = _at_local(day, params.entry_hour, tz)
        eval_local = _at_local(day, params.eval_hour, tz)
        flatten_local = _at_local(day, params.flatten_hour, tz)
        if not is_market_open(entry_local.astimezone(ZoneInfo("UTC"))):
            skips.append(SessionSkip(day.isoformat(), "market_closed"))
            continue

        bar5 = by_hour.get((day, int(params.sl_hour)))
        if bar5 is None:
            skips.append(SessionSkip(day.isoformat(), "no_5am_bar"))
            continue

        defining = pick_defining_bar(by_hour, day, params, ps)
        if defining is None:
            skips.append(SessionSkip(day.isoformat(), "no_defining_bar"))
            continue

        if defining.close > defining.open:
            side = "UP"
        elif defining.close < defining.open:
            side = "DOWN"
        else:
            skips.append(SessionSkip(day.isoformat(), "flat_defining_bar"))
            continue

        entry_utc = entry_local.astimezone(ZoneInfo("UTC"))
        idx = advance_to(entry_utc)
        if idx >= n:
            skips.append(SessionSkip(day.isoformat(), "no_entry_tick"))
            continue
        # First tick at/after 07:00 must still be before eval (same morning)
        if _local(ticks[idx].ts, tz) >= eval_local:
            skips.append(SessionSkip(day.isoformat(), "no_entry_tick"))
            continue
        if not is_market_open(ticks[idx].ts):
            skips.append(SessionSkip(day.isoformat(), "market_closed"))
            continue

        entry = _mid(ticks[idx])
        sl = sl_price(
            side,
            entry,
            bar5,
            sl_floor_pts=params.sl_floor_pts,
            ps=ps,
        )
        sl_pts = abs(entry - sl) / ps

        reason, exit_ts, exit_px, pts = simulate_trade(
            ticks,
            idx,
            side=side,
            entry=entry,
            sl=sl,
            entry_local=entry_local,
            eval_local=eval_local,
            flatten_local=flatten_local,
            ps=ps,
            tz=tz,
        )
        trades.append(
            SessionTrade(
                local_date=day.isoformat(),
                side=side,
                defining_hour=defining.local_hour,
                defining_open=round(defining.open, 5),
                defining_high=round(defining.high, 5),
                defining_low=round(defining.low, 5),
                defining_close=round(defining.close, 5),
                defining_range_usd=round(defining.high - defining.low, 4),
                sl_hour=bar5.local_hour,
                sl_high=round(bar5.high, 5),
                sl_low=round(bar5.low, 5),
                entry_ts=ticks[idx].ts.isoformat(),
                entry=round(entry, 5),
                sl=round(sl, 5),
                sl_pts=round(sl_pts, 1),
                exit_ts=exit_ts.isoformat() if exit_ts is not None else None,
                exit=round(exit_px, 5),
                exit_reason=reason,
                pts=round(pts, 1),
            )
        )

    return summarize_session(trades, skips, params, symbol=sym, ticks=len(ticks))


def summarize_session(
    trades: Sequence[SessionTrade],
    skips: Sequence[SessionSkip],
    params: SessionParams,
    *,
    symbol: str,
    ticks: int,
) -> Dict[str, Any]:
    n = len(trades)
    wins = sum(1 for t in trades if t.pts > 1e-9)
    losses = sum(1 for t in trades if t.pts < -1e-9)
    scratches = n - wins - losses
    by_reason: Dict[str, int] = {}
    for t in trades:
        r = t.exit_reason or "?"
        by_reason[r] = by_reason.get(r, 0) + 1
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

    return {
        "kind": "session_clock",
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
        "sl_n": by_reason.get("sl", 0),
        "sl_pct": pct(by_reason.get("sl", 0), n),
        "eval_flat_n": by_reason.get("eval_flat", 0),
        "eval_flat_pct": pct(by_reason.get("eval_flat", 0), n),
        "be_n": by_reason.get("be", 0),
        "be_pct": pct(by_reason.get("be", 0), n),
        "noon_n": by_reason.get("noon_flat", 0),
        "noon_pct": pct(by_reason.get("noon_flat", 0), n),
        "exits": by_reason,
        "avg_pts": avg_pts,
        "avg_win_pts": avg_win,
        "avg_loss_pts": avg_loss,
        "profit_factor": pf,
        "sum_pts": round(sum(t.pts for t in trades), 1),
        "rows": [asdict(t) for t in trades],
        "skips": [asdict(s) for s in skips],
    }


def _empty_result(params: SessionParams, *, symbol: str, ticks: int) -> Dict[str, Any]:
    return summarize_session([], [], params, symbol=symbol, ticks=ticks)
