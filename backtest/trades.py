"""
TP / SL trade simulation on tick data (first touch wins).

Entry convention (realistic retail):
  LONG  → fill at ask, SL/TP checked against bid
  SHORT → fill at bid, SL/TP checked against ask

Optional mid mode for research (ignore spread).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional, Sequence

from backtest.config import point_size
from backtest.dukascopy import Tick

Side = Literal["UP", "DOWN"]
Outcome = Literal["tp", "sl", "timeout", "open"]
PriceMode = Literal["spread", "mid"]


@dataclass
class AlertSignal:
    kind: str  # "candle" | "spike"
    symbol: str
    side: Side
    ts: datetime
    price: float  # mid at fire
    meta: dict = field(default_factory=dict)


@dataclass
class TradeResult:
    alert: AlertSignal
    entry: float
    tp: float
    sl: float
    side: Side
    outcome: Outcome
    exit_price: Optional[float]
    exit_ts: Optional[datetime]
    hold_sec: Optional[float]
    r_multiple: Optional[float]  # +1 TP, -1 SL, partial if timeout at mid

    @property
    def win(self) -> Optional[bool]:
        if self.outcome == "tp":
            return True
        if self.outcome == "sl":
            return False
        return None


def _entry_and_levels(
    side: Side,
    tick: Tick,
    tp_pts: float,
    sl_pts: float,
    symbol: str,
    mode: PriceMode,
) -> tuple[float, float, float]:
    ps = point_size(symbol)
    if mode == "mid":
        entry = tick.mid
    else:
        entry = tick.ask if side == "UP" else tick.bid

    if side == "UP":
        tp = entry + tp_pts * ps
        sl = entry - sl_pts * ps
    else:
        tp = entry - tp_pts * ps
        sl = entry + sl_pts * ps
    return entry, tp, sl


def simulate_trade(
    alert: AlertSignal,
    ticks: Sequence[Tick],
    *,
    tp_pts: float,
    sl_pts: float,
    mode: PriceMode = "spread",
    max_hold_sec: Optional[float] = None,
    start_index: int = 0,
) -> TradeResult:
    """
    Walk ticks after the alert. First touch of TP or SL ends the trade.

    `ticks` should be the full series; `start_index` is the tick index at/after fire.
    Entry uses that tick (or next available).
    """
    if start_index >= len(ticks):
        return TradeResult(
            alert=alert,
            entry=alert.price,
            tp=0.0,
            sl=0.0,
            side=alert.side,
            outcome="open",
            exit_price=None,
            exit_ts=None,
            hold_sec=None,
            r_multiple=None,
        )

    entry_tick = ticks[start_index]
    entry, tp, sl = _entry_and_levels(
        alert.side, entry_tick, tp_pts, sl_pts, alert.symbol, mode
    )
    t0 = entry_tick.ts

    for i in range(start_index + 1, len(ticks)):
        t = ticks[i]
        elapsed = (t.ts - t0).total_seconds()
        if max_hold_sec is not None and elapsed > max_hold_sec:
            mid = t.mid
            if alert.side == "UP":
                r = (mid - entry) / (entry - sl) if entry != sl else 0.0
            else:
                r = (entry - mid) / (sl - entry) if sl != entry else 0.0
            return TradeResult(
                alert=alert,
                entry=entry,
                tp=tp,
                sl=sl,
                side=alert.side,
                outcome="timeout",
                exit_price=mid,
                exit_ts=t.ts,
                hold_sec=elapsed,
                r_multiple=r,
            )

        if mode == "mid":
            hi = lo = t.mid
            # same price both ways — check both; SL first if same tick touches both
            # (conservative: if mid beyond both, prefer SL)
            if alert.side == "UP":
                hit_sl = lo <= sl
                hit_tp = hi >= tp
            else:
                hit_sl = hi >= sl
                hit_tp = lo <= tp
        else:
            # Long: exit at bid; Short: exit at ask
            if alert.side == "UP":
                px = t.bid
                hit_sl = px <= sl
                hit_tp = px >= tp
            else:
                px = t.ask
                hit_sl = px >= sl
                hit_tp = px <= tp

        if hit_sl and hit_tp:
            # same tick ambiguity → count as SL (conservative)
            return TradeResult(
                alert=alert,
                entry=entry,
                tp=tp,
                sl=sl,
                side=alert.side,
                outcome="sl",
                exit_price=sl,
                exit_ts=t.ts,
                hold_sec=elapsed,
                r_multiple=-1.0,
            )
        if hit_sl:
            return TradeResult(
                alert=alert,
                entry=entry,
                tp=tp,
                sl=sl,
                side=alert.side,
                outcome="sl",
                exit_price=sl,
                exit_ts=t.ts,
                hold_sec=elapsed,
                r_multiple=-1.0,
            )
        if hit_tp:
            return TradeResult(
                alert=alert,
                entry=entry,
                tp=tp,
                sl=sl,
                side=alert.side,
                outcome="tp",
                exit_price=tp,
                exit_ts=t.ts,
                hold_sec=elapsed,
                r_multiple=1.0,
            )

    last = ticks[-1]
    elapsed = (last.ts - t0).total_seconds()
    mid = last.mid
    if alert.side == "UP":
        r = (mid - entry) / max(entry - sl, 1e-12)
    else:
        r = (entry - mid) / max(sl - entry, 1e-12)
    return TradeResult(
        alert=alert,
        entry=entry,
        tp=tp,
        sl=sl,
        side=alert.side,
        outcome="timeout",
        exit_price=mid,
        exit_ts=last.ts,
        hold_sec=elapsed,
        r_multiple=r,
    )


def summarize(trades: List[TradeResult]) -> dict:
    closed = [t for t in trades if t.outcome in ("tp", "sl")]
    wins = [t for t in closed if t.outcome == "tp"]
    losses = [t for t in closed if t.outcome == "sl"]
    timeouts = [t for t in trades if t.outcome == "timeout"]
    n = len(closed)
    wr = (len(wins) / n * 100.0) if n else 0.0
    # Expectancy in R if TP=1R SL=1R (or scale by tp/sl ratio outside)
    exp_r = sum(t.r_multiple or 0.0 for t in closed) / n if n else 0.0
    return {
        "trades": len(trades),
        "closed": n,
        "wins": len(wins),
        "losses": len(losses),
        "timeouts": len(timeouts),
        "win_rate_pct": round(wr, 2),
        "expectancy_r": round(exp_r, 3),
        "hits_55pct": wr >= 55.0 if n else False,
    }
