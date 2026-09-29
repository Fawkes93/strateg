"""Dawn Cross — 5m average cross in the Moldova dawn window, then a pullback fill.

Watch 02:00–06:00 Europe/Chisinau. A fast average cross of the slow average on
a closed 5m bar arms the side: up is a buy, down is a sell. Each line is an
EMA, KAMA, HMA, or ZLEMA. The fill waits for a later bar in that same window
whose range tags the pullback average. Stop and target are fixed point
distances. One position at a time.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from backtest.candles import Candle, to_utc
from backtest.config import point_size
from backtest.dukascopy import reaktor_symbol
from backtest.overnight_break import _hma_series, _kama_series, _zlema_series


@dataclass
class DawnCrossParams:
    timezone: str = "Europe/Chisinau"
    window_start_hour: int = 2
    window_start_minute: int = 0
    window_end_hour: int = 6
    window_end_minute: int = 0
    fast_ma: str = "ema"  # ema | kama | hma | zlema
    fast_ema: int = 9
    fast_kama_fast: int = 2
    fast_kama_slow: int = 30
    slow_ma: str = "ema"
    slow_ema: int = 20
    slow_kama_fast: int = 2
    slow_kama_slow: int = 30
    pull_ma: str = "ema"
    pullback_ema: int = 9
    pull_kama_fast: int = 2
    pull_kama_slow: int = 30
    sl_pts: float = 400.0
    tp_pts: float = 800.0
    flatten_hour: int = 12  # local hour; 0 = hold for SL/TP only
    one_trade_per_day: bool = True


@dataclass
class DawnCrossTrade:
    local_date: str
    side: str  # UP long | DOWN short
    cross_ts: str
    entry_ts: str
    entry_local: str
    entry: float
    sl: float
    tp: float
    sl_pts: float
    tp_pts: float
    fast_ema: float
    slow_ema: float
    pullback_ema: float
    exit_ts: Optional[str] = None
    exit_local: Optional[str] = None
    exit: Optional[float] = None
    exit_reason: Optional[str] = None
    pts: float = 0.0


MA_KINDS = ("ema", "kama", "hma", "zlema")


def ema_series(values: Sequence[float], period: int) -> List[Optional[float]]:
    """SMA-seeded EMA. Index period-1 is the first valid value."""
    n = len(values)
    out: List[Optional[float]] = [None] * n
    p = int(period)
    if p < 1 or n < p:
        return out
    seed = sum(float(v) for v in values[:p]) / p
    out[p - 1] = seed
    k = 2.0 / (p + 1)
    ema = seed
    for i in range(p, n):
        ema = float(values[i]) * k + ema * (1.0 - k)
        out[i] = ema
    return out


def ma_line_spec(
    kind: str,
    period: int,
    kama_fast: int = 2,
    kama_slow: int = 30,
) -> Tuple[str, int, int, int]:
    """Normalize one Dawn Cross line. HMA length is at least 2. KAMA length is the ER window."""
    name = str(kind or "ema").strip().lower()
    if name not in MA_KINDS:
        name = "ema"
    length = int(period or (2 if name == "hma" else 1))
    length = max(2, length) if name == "hma" else max(1, length)
    return (
        name,
        length,
        max(1, int(kama_fast or 2)),
        max(1, int(kama_slow or 30)),
    )


def same_average(
    left: Tuple[str, int, int, int], right: Tuple[str, int, int, int]
) -> bool:
    """True when two lines would plot the same series. KAMA fast/slow matter only for KAMA."""
    if left[0] != right[0] or left[1] != right[1]:
        return False
    if left[0] == "kama":
        return left[2] == right[2] and left[3] == right[3]
    return True


def ma_line_series(
    closes: Sequence[float], spec: Tuple[str, int, int, int]
) -> List[Optional[float]]:
    """EMA, KAMA, HMA, or ZLEMA over the full close series. Same KAMA/HMA/ZLEMA math as overnight."""
    kind, period, kama_fast, kama_slow = spec
    if kind == "kama":
        return _kama_series(closes, period, kama_fast, kama_slow)
    if kind == "hma":
        return _hma_series(closes, period)
    if kind == "zlema":
        return _zlema_series(closes, period)
    return ema_series(closes, period)


def _apply_lines(params: DawnCrossParams):
    fast = ma_line_spec(
        params.fast_ma, params.fast_ema, params.fast_kama_fast, params.fast_kama_slow
    )
    slow = ma_line_spec(
        params.slow_ma, params.slow_ema, params.slow_kama_fast, params.slow_kama_slow
    )
    pull = ma_line_spec(
        params.pull_ma, params.pullback_ema, params.pull_kama_fast, params.pull_kama_slow
    )
    params.fast_ma, params.fast_ema, params.fast_kama_fast, params.fast_kama_slow = fast
    params.slow_ma, params.slow_ema, params.slow_kama_fast, params.slow_kama_slow = slow
    params.pull_ma, params.pullback_ema, params.pull_kama_fast, params.pull_kama_slow = pull
    return fast, slow, pull


def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(name or "Europe/Chisinau")


def _local(ts: datetime, zone: ZoneInfo) -> datetime:
    return to_utc(ts).astimezone(zone)


def in_window(
    ts: datetime,
    zone: ZoneInfo,
    start_hour: int,
    end_hour: int,
    start_minute: int = 0,
    end_minute: int = 0,
) -> bool:
    """Local clock is inside [start, end). End is exclusive. Overnight wrap is allowed."""
    local = _local(ts, zone)
    minutes = local.hour * 60 + local.minute
    start = int(start_hour) * 60 + int(start_minute)
    end = int(end_hour) * 60 + int(end_minute)
    if start == end:
        return False
    if start < end:
        return start <= minutes < end
    return minutes >= start or minutes < end


def _cross(prev_fast: float, prev_slow: float, fast: float, slow: float) -> Optional[str]:
    if prev_fast <= prev_slow and fast > slow:
        return "UP"
    if prev_fast >= prev_slow and fast < slow:
        return "DOWN"
    return None


def _bracket(side: str, entry: float, sl_pts: float, tp_pts: float, ps: float) -> Tuple[float, float]:
    dist_sl = sl_pts * ps
    dist_tp = tp_pts * ps
    if side == "UP":
        return entry - dist_sl, entry + dist_tp
    return entry + dist_sl, entry - dist_tp


def _pts(side: str, entry: float, exit_px: float, ps: float) -> float:
    if ps <= 0:
        return 0.0
    if side == "UP":
        return (exit_px - entry) / ps
    return (entry - exit_px) / ps


def _bar_exit(side: str, bar: Candle, sl: float, tp: float) -> Optional[Tuple[float, str]]:
    """SL wins when the same 5m bar trades both prices. Wick order is unknown."""
    if side == "UP":
        hit_sl = bar.low <= sl
        hit_tp = bar.high >= tp
    else:
        hit_sl = bar.high >= sl
        hit_tp = bar.low <= tp
    if hit_sl:
        return sl, "SL"
    if hit_tp:
        return tp, "TP"
    return None


def _local_stamp(ts: datetime, zone: ZoneInfo) -> str:
    return _local(ts, zone).strftime("%Y-%m-%d %H:%M")


def _flatten_due(bar: Candle, zone: ZoneInfo, flatten_hour: int) -> bool:
    if flatten_hour <= 0:
        return False
    return _local(bar.open_time, zone).hour >= int(flatten_hour)


def run_dawn_cross(
    candles: Sequence[Candle],
    *,
    symbol: str = "XAUUSD",
    params: Optional[DawnCrossParams] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Dict[str, Any]:
    params = params or DawnCrossParams()
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    zone = _zone(params.timezone)
    closes = [float(c.close) for c in candles]
    fast_spec, slow_spec, pull_spec = _apply_lines(params)
    fast = ma_line_series(closes, fast_spec)
    slow = ma_line_series(closes, slow_spec)
    if same_average(pull_spec, fast_spec):
        pull = fast
    elif same_average(pull_spec, slow_spec):
        pull = slow
    else:
        pull = ma_line_series(closes, pull_spec)

    trades: List[DawnCrossTrade] = []
    traded_days: set[str] = set()
    one_a_day = bool(params.one_trade_per_day)
    armed: Optional[Tuple[str, int]] = None
    open_side: Optional[str] = None
    open_trade: Optional[DawnCrossTrade] = None
    open_sl = 0.0
    open_tp = 0.0

    def _keep(trade: DawnCrossTrade) -> bool:
        if date_from is None and date_to is None:
            return True
        d = date.fromisoformat(trade.local_date)
        if date_from is not None and d < date_from:
            return False
        if date_to is not None and d >= date_to:
            return False
        return True

    def _close(exit_px: float, reason: str, when: datetime) -> None:
        nonlocal open_side, open_trade
        assert open_trade is not None and open_side is not None
        open_trade.exit = exit_px
        open_trade.exit_reason = reason
        open_trade.exit_ts = to_utc(when).isoformat()
        open_trade.exit_local = _local_stamp(when, zone)
        open_trade.pts = round(_pts(open_side, open_trade.entry, exit_px, ps), 1)
        if _keep(open_trade):
            trades.append(open_trade)
        open_side = None
        open_trade = None

    n = len(candles)
    for i in range(1, n):
        bar = candles[i]
        if open_trade is not None and open_side is not None:
            if _flatten_due(bar, zone, params.flatten_hour):
                _close(bar.open, "flatten", bar.open_time)
            else:
                hit = _bar_exit(open_side, bar, open_sl, open_tp)
                if hit is not None:
                    _close(hit[0], hit[1], bar.close_time)
            continue

        local_day = _local(bar.open_time, zone).date().isoformat()
        if one_a_day and local_day in traded_days:
            armed = None
            continue

        window = in_window(
            bar.open_time,
            zone,
            params.window_start_hour,
            params.window_end_hour,
            params.window_start_minute,
            params.window_end_minute,
        )
        if armed is not None and not window:
            armed = None

        if (
            armed is not None
            and window
            and i > armed[1]
            and pull[i] is not None
        ):
            ema = float(pull[i])
            side = armed[0]
            if bar.low <= ema <= bar.high:
                sl, tp = _bracket(side, ema, float(params.sl_pts), float(params.tp_pts), ps)
                local = _local(bar.open_time, zone)
                open_trade = DawnCrossTrade(
                    local_date=local.date().isoformat(),
                    side=side,
                    cross_ts=to_utc(candles[armed[1]].close_time).isoformat(),
                    entry_ts=to_utc(bar.open_time).isoformat(),
                    entry_local=_local_stamp(bar.open_time, zone),
                    entry=ema,
                    sl=sl,
                    tp=tp,
                    sl_pts=float(params.sl_pts),
                    tp_pts=float(params.tp_pts),
                    fast_ema=float(fast[armed[1]] or 0.0),
                    slow_ema=float(slow[armed[1]] or 0.0),
                    pullback_ema=ema,
                )
                open_side = side
                open_sl = sl
                open_tp = tp
                armed = None
                traded_days.add(open_trade.local_date)
                hit = _bar_exit(side, bar, sl, tp)
                if hit is not None:
                    _close(hit[0], hit[1], bar.close_time)
                continue

        if not window:
            continue
        pf, ps_ = fast[i - 1], slow[i - 1]
        cf, cs = fast[i], slow[i]
        if None in (pf, ps_, cf, cs):
            continue
        side = _cross(float(pf), float(ps_), float(cf), float(cs))
        if side is None:
            continue
        if armed is None or armed[0] != side:
            armed = (side, i)

    if open_trade is not None and open_side is not None and candles:
        last = candles[-1]
        _close(last.close, "data_end", last.close_time)

    return _summary(trades, params=params, symbol=sym, n_bars=n)


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


def _trade_stats(trades: Sequence[DawnCrossTrade]) -> Dict[str, Any]:
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


def _streak_stats(trades: Sequence[DawnCrossTrade]) -> Dict[str, Any]:
    """Consecutive wins/losses in local date order. A scratch (0 pts) breaks the run."""
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


def _month_rows(trades: Sequence[DawnCrossTrade]) -> List[Dict[str, Any]]:
    by_month: Dict[str, List[DawnCrossTrade]] = defaultdict(list)
    for t in trades:
        by_month[_month_key(t.local_date)].append(t)
    rows: List[Dict[str, Any]] = []
    for ym in sorted(by_month):
        row = _trade_stats(by_month[ym])
        row["month"] = ym
        rows.append(row)
    return rows


def _summary(
    trades: Sequence[DawnCrossTrade],
    *,
    params: DawnCrossParams,
    symbol: str,
    n_bars: int,
) -> Dict[str, Any]:
    stats = _trade_stats(trades)
    return {
        "kind": "dawn_cross",
        "name": "Dawn Cross",
        "symbol": symbol,
        "params": asdict(params),
        "data_source": "candles_5m",
        "bars": n_bars,
        **stats,
        "streaks": _streak_stats(trades),
        "by_month": _month_rows(trades),
        "rows": [asdict(t) for t in trades],
    }
