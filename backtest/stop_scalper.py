"""Stop scalper — buy stop and sell stop near the bar open, then one reversal.

Each 1-minute bar, while flat, a buy stop sits `entry_pts` above the open and a
sell stop sits the same distance below. The first stop the bar trades is the
fill. The other is cancelled. The position carries a safety stop. Auto
break-even moves that stop to the entry after `be_pts` of profit. Trailing
starts after the arm and keeps the stop `trail_pts` behind the best price.
When the stop-entry closes, the opposite side is entered at that price. When
the reversal closes, the next bar places a fresh pair. A reversal does not
reverse again.

Bars are walked open → low → high → close when the close is at or above the
open, and open → high → low → close otherwise. The stop that exists at the
start of a segment is the one that can fill on that segment. Break-even and
the trail update after the segment, for the next one.

Pure — no web, no MT5. The MQL5 twin with these filters is mql5/ScalperProV2.mq5.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from backtest.candles import Candle, is_market_open, to_utc
from backtest.config import point_size
from backtest.dukascopy import reaktor_symbol


@dataclass
class StopScalperParams:
    timezone: str = "Europe/Chisinau"
    entry_pts: float = 50.0
    sl_pts: float = 500.0
    trail_pts: float = 100.0  # 0 = trailing off
    trail_arm_pts: float = 200.0  # 0 = arm once profit reaches trail_pts
    be_pts: float = 150.0  # 0 = break-even off
    lock_arm_pts: float = 0.0  # 0 = profit lock off
    lock_pts: float = 0.0  # stop distance past entry once the lock arms
    tp_pts: float = 0.0  # 0 = no fixed target
    spread_pts: float = 0.0  # assumed spread, charged on the entry
    max_spread_pts: float = 0.0  # 0 = no cap; above this, skip new entries
    reverse: bool = True
    reverse_on: str = "close"  # close = any exit, sl = safety stop only


@dataclass
class StopScalperTrade:
    local_date: str
    side: str  # UP long | DOWN short
    origin: str  # stop | reverse
    entry_ts: str
    entry_local: str
    entry: float
    sl_init: float
    sl: float
    exit_ts: Optional[str] = None
    exit_local: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None  # sl | be | lock | trail | tp | data_end
    pts: float = 0.0
    max_fav_pts: float = 0.0
    entry_pts: float = 0.0
    sl_pts: float = 0.0
    trail_pts: float = 0.0
    trail_arm_pts: float = 0.0
    be_pts: float = 0.0
    lock_arm_pts: float = 0.0
    lock_pts: float = 0.0
    tp_pts: float = 0.0
    spread_pts: float = 0.0


def validate_params(params: StopScalperParams) -> None:
    """Raise ValueError when a distance cannot be traded."""
    if float(params.entry_pts) <= 0:
        raise ValueError("Entry distance must be greater than 0")
    if float(params.sl_pts) <= 0:
        raise ValueError("SL must be greater than 0")
    if float(params.trail_pts) < 0 or float(params.trail_arm_pts) < 0 or float(params.be_pts) < 0:
        raise ValueError("Trailing stop, trailing arm, and auto BE must be 0 or greater")
    if (
        float(params.lock_arm_pts) < 0
        or float(params.lock_pts) < 0
        or float(params.tp_pts) < 0
        or float(params.spread_pts) < 0
        or float(params.max_spread_pts) < 0
    ):
        raise ValueError("Profit lock, target, and spread must be 0 or greater")
    mode = str(params.reverse_on or "close").lower()
    if mode not in ("close", "sl"):
        raise ValueError("Reversal must be after any close or only after the safety stop")


def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(name or "Europe/Chisinau")


def _local(ts: datetime, zone: ZoneInfo) -> datetime:
    return to_utc(ts).astimezone(zone)


def _local_stamp(ts: datetime, zone: ZoneInfo) -> str:
    return _local(ts, zone).strftime("%Y-%m-%d %H:%M")


def _pts(side: str, entry: float, px: float, ps: float) -> float:
    if ps <= 0:
        return 0.0
    if side == "UP":
        return (px - entry) / ps
    return (entry - px) / ps


def _flip(side: str) -> str:
    return "DOWN" if side == "UP" else "UP"


def _path(bar: Candle) -> List[float]:
    """Intrabar path. Bullish and doji bars dip first. Bearish bars rally first."""
    o = float(bar.open)
    h = float(bar.high)
    l = float(bar.low)
    c = float(bar.close)
    raw = [o, l, h, c] if c >= o else [o, h, l, c]
    out = [raw[0]]
    for px in raw[1:]:
        if abs(px - out[-1]) > 1e-12:
            out.append(px)
    return out


def _reached(level: float, start: float, end: float) -> bool:
    """True when `level` lies on the segment strictly after `start`, through `end`."""
    if end > start:
        return start + 1e-12 < level <= end + 1e-12
    if end < start:
        return end - 1e-12 <= level < start - 1e-12
    return False


def _tighter(side: str, candidate: float, current: float) -> bool:
    if side == "UP":
        return candidate > current + 1e-12
    return candidate < current - 1e-12


def _through_sl(side: str, sl: float, px: float) -> bool:
    if side == "UP":
        return px <= sl + 1e-12
    return px >= sl - 1e-12


def _first_stop(start: float, end: float, buy: float, sell: float) -> Optional[tuple]:
    """The stop this segment reaches, in the direction of travel."""
    if end > start and _reached(buy, start, end):
        return "UP", buy
    if end < start and _reached(sell, start, end):
        return "DOWN", sell
    return None


def _trail_arm(params: StopScalperParams) -> float:
    trail = float(params.trail_pts or 0.0)
    if trail <= 1e-12:
        return 0.0
    arm = float(params.trail_arm_pts or 0.0)
    if arm <= 1e-12:
        return trail
    return arm


class _Pos:
    def __init__(
        self,
        side: str,
        origin: str,
        entry: float,
        sl: float,
        when: datetime,
        trade: StopScalperTrade,
    ) -> None:
        self.side = side
        self.origin = origin
        self.entry = entry
        self.sl = sl
        self.kind = "sl"
        self.best = entry
        self.max_fav = 0.0
        self.when = when
        self.trade = trade


def run_stop_scalper(
    candles: Sequence[Candle],
    *,
    symbol: str = "XAUUSD",
    params: Optional[StopScalperParams] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Dict[str, Any]:
    params = params or StopScalperParams()
    validate_params(params)
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    zone = _zone(params.timezone)
    entry_dist = float(params.entry_pts) * ps
    sl_dist = float(params.sl_pts) * ps

    trades: List[StopScalperTrade] = []
    pos: Optional[_Pos] = None

    def _keep(trade: StopScalperTrade) -> bool:
        if date_from is None and date_to is None:
            return True
        d = date.fromisoformat(trade.local_date)
        if date_from is not None and d < date_from:
            return False
        if date_to is not None and d >= date_to:
            return False
        return True

    def _tighten() -> None:
        assert pos is not None
        fav = _pts(pos.side, pos.entry, pos.best, ps)
        if fav > pos.max_fav:
            pos.max_fav = fav
        if float(params.be_pts) > 1e-12 and fav + 1e-12 >= float(params.be_pts):
            if _tighter(pos.side, pos.entry, pos.sl):
                pos.sl = pos.entry
                pos.kind = "be"
        lock_arm = float(params.lock_arm_pts or 0.0)
        if lock_arm > 1e-12 and fav + 1e-12 >= lock_arm:
            lock_dist = float(params.lock_pts or 0.0) * ps
            lock_px = pos.entry + lock_dist if pos.side == "UP" else pos.entry - lock_dist
            if _tighter(pos.side, lock_px, pos.sl):
                pos.sl = lock_px
                pos.kind = "lock"
        arm = _trail_arm(params)
        if float(params.trail_pts) > 1e-12 and fav + 1e-12 >= arm:
            dist = float(params.trail_pts) * ps
            trail_sl = pos.best - dist if pos.side == "UP" else pos.best + dist
            if _tighter(pos.side, trail_sl, pos.sl):
                pos.sl = trail_sl
                pos.kind = "trail"

    def _with_spread(side: str, px: float) -> float:
        spr = float(params.spread_pts or 0.0) * ps
        if spr <= 0:
            return px
        return px + spr if side == "UP" else px - spr

    def _spread_ok() -> bool:
        cap = float(params.max_spread_pts or 0.0)
        if cap <= 1e-12:
            return True
        return float(params.spread_pts or 0.0) <= cap + 1e-12

    def _tp_price() -> Optional[float]:
        if pos is None or float(params.tp_pts or 0.0) <= 1e-12:
            return None
        dist = float(params.tp_pts) * ps
        return pos.entry + dist if pos.side == "UP" else pos.entry - dist

    def _wants_reverse(reason: str, origin: str) -> bool:
        if reason == "data_end" or origin != "stop" or not bool(params.reverse):
            return False
        if str(params.reverse_on or "close").lower() == "sl":
            return reason == "sl"
        return True

    def _open(side: str, px: float, origin: str, when: datetime) -> None:
        nonlocal pos
        px = _with_spread(side, px)
        sl = px - sl_dist if side == "UP" else px + sl_dist
        local = _local(when, zone)
        trade = StopScalperTrade(
            local_date=local.date().isoformat(),
            side=side,
            origin=origin,
            entry_ts=to_utc(when).isoformat(),
            entry_local=_local_stamp(when, zone),
            entry=px,
            sl_init=sl,
            sl=sl,
            entry_pts=float(params.entry_pts),
            sl_pts=float(params.sl_pts),
            trail_pts=float(params.trail_pts),
            trail_arm_pts=float(params.trail_arm_pts),
            be_pts=float(params.be_pts),
            lock_arm_pts=float(params.lock_arm_pts),
            lock_pts=float(params.lock_pts),
            tp_pts=float(params.tp_pts),
            spread_pts=float(params.spread_pts),
        )
        pos = _Pos(side, origin, px, sl, when, trade)

    def _exit(exit_px: float, reason: str, when: datetime) -> None:
        nonlocal pos
        assert pos is not None
        pos.trade.exit = exit_px
        pos.trade.exit_reason = reason
        pos.trade.sl = pos.sl
        pos.trade.exit_ts = to_utc(when).isoformat()
        pos.trade.exit_local = _local_stamp(when, zone)
        pos.trade.pts = round(_pts(pos.side, pos.entry, exit_px, ps), 1)
        pos.trade.max_fav_pts = round(pos.max_fav, 1)
        if _keep(pos.trade):
            trades.append(pos.trade)
        origin = pos.origin
        side = pos.side
        pos = None
        if _wants_reverse(reason, origin) and _spread_ok():
            _open(_flip(side), exit_px, "reverse", when)

    def _manage(start: float, end: float, when: datetime) -> None:
        cursor = start
        for _ in range(3):
            if pos is None or abs(cursor - end) <= 1e-12:
                return
            if _reached(pos.sl, cursor, end):
                _exit(pos.sl, pos.kind, when)
                if pos is None:
                    return
                cursor = pos.entry
                continue
            tp_px = _tp_price()
            if tp_px is not None and _reached(tp_px, cursor, end):
                _exit(tp_px, "tp", when)
                if pos is None:
                    return
                cursor = pos.entry
                continue
            if pos.side == "UP" and end > pos.best + 1e-12:
                pos.best = end
                _tighten()
            elif pos.side == "DOWN" and end < pos.best - 1e-12:
                pos.best = end
                _tighten()
            return

    for bar in candles:
        when = bar.open_time
        open_px = float(bar.open)
        blocked = False
        if pos is not None and _through_sl(pos.side, pos.sl, open_px):
            _exit(open_px, pos.kind, when)
            if pos is None:
                blocked = True
        tp_at_open = _tp_price()
        if pos is not None and tp_at_open is not None:
            through_tp = (pos.side == "UP" and open_px >= tp_at_open - 1e-12) or (
                pos.side == "DOWN" and open_px <= tp_at_open + 1e-12
            )
            if through_tp:
                _exit(open_px, "tp", when)
                if pos is None:
                    blocked = True
        armed = False
        buy_px = 0.0
        sell_px = 0.0
        if pos is None and not blocked and is_market_open(when) and _spread_ok():
            buy_px = open_px + entry_dist
            sell_px = open_px - entry_dist
            armed = True
        path = _path(bar)
        for start, end in zip(path, path[1:]):
            if pos is None:
                if not armed:
                    continue
                hit = _first_stop(start, end, buy_px, sell_px)
                if hit is None:
                    continue
                side, px = hit
                armed = False
                _open(side, px, "stop", when)
                _manage(px, end, when)
            else:
                _manage(start, end, when)

    if pos is not None and candles:
        last = candles[-1]
        _exit(float(last.close), "data_end", last.close_time)

    return _summary(trades, params=params, symbol=sym, n_bars=len(candles))


def _month_key(local_date: Optional[str]) -> str:
    s = str(local_date or "")
    return s[:7] if len(s) >= 7 else "unknown"


def _pct(a: int, b: int) -> Optional[float]:
    if b <= 0:
        return None
    return round(100.0 * a / b, 1)


def _profit_factor(gross: float, loss: float) -> Optional[float]:
    if loss > 1e-9:
        return round(gross / loss, 2)
    if gross > 0:
        return None
    return 0.0


def _trade_stats(trades: Sequence[StopScalperTrade]) -> Dict[str, Any]:
    n = len(trades)
    wins = sum(1 for t in trades if t.pts > 1e-9)
    losses = sum(1 for t in trades if t.pts < -1e-9)
    gross = sum(t.pts for t in trades if t.pts > 0)
    loss = sum(-t.pts for t in trades if t.pts < 0)
    summed = sum(t.pts for t in trades)
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / n, 3) if n else 0.0,
        "win_pct": _pct(wins, n),
        "sum_pts": round(summed, 1),
        "avg_pts": round(summed / n, 1) if n else 0.0,
        "avg_win_pts": round(gross / wins, 1) if wins else None,
        "avg_loss_pts": round(-loss / losses, 1) if losses else None,
        "profit_factor": _profit_factor(gross, loss),
    }


def _streak_kind(pts: float) -> Optional[str]:
    if pts > 1e-9:
        return "win"
    if pts < -1e-9:
        return "loss"
    return None


def _streak_stats(trades: Sequence[StopScalperTrade]) -> Dict[str, Any]:
    """Consecutive wins and losses in fill order. A scratch (0 pts) breaks the run."""
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


def _month_rows(trades: Sequence[StopScalperTrade]) -> List[Dict[str, Any]]:
    by_month: Dict[str, List[StopScalperTrade]] = defaultdict(list)
    for t in trades:
        by_month[_month_key(t.local_date)].append(t)
    rows: List[Dict[str, Any]] = []
    for ym in sorted(by_month):
        row = _trade_stats(by_month[ym])
        row["month"] = ym
        rows.append(row)
    return rows


def _origin_rows(trades: Sequence[StopScalperTrade]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for origin in ("stop", "reverse"):
        group = [t for t in trades if t.origin == origin]
        row = _trade_stats(group)
        row["origin"] = origin
        rows.append(row)
    return rows


def _summary(
    trades: Sequence[StopScalperTrade],
    *,
    params: StopScalperParams,
    symbol: str,
    n_bars: int,
) -> Dict[str, Any]:
    stats = _trade_stats(trades)
    return {
        "kind": "stop_scalper",
        "name": "Stop Scalper",
        "symbol": symbol,
        "params": asdict(params),
        "data_source": "candles_1m",
        "bars": n_bars,
        **stats,
        "streaks": _streak_stats(trades),
        "by_month": _month_rows(trades),
        "by_origin": _origin_rows(trades),
        "rows": [asdict(t) for t in trades],
    }
