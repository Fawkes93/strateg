"""
Inverse FVG (IFVG) after liquidity raid — not plain FVG.

Bullish IFVG:
  1. Confirmed swing low (lookback bars each side).
  2. Bearish expansion raids below that low (SSL).
  3. Bearish FVG: C1.low > C3.high; P=C1.low, bottom=C3.high, CE=(P+bottom)/2.
  4. Confirm: a later candle closes above P.
  5. Entry: retrace into upper half [CE, P] — first touch, or require CE touch first.
  6. SL meta: far edge (below bottom) or below CE.

Bearish IFVG mirrors (BSL → bullish FVG → close below P → retrace into [P, CE]).

Candles: CandleBuilder(15) from ticks; if TF in {30,60,240} aggregate via
backtest.aggregate.aggregate_candles. Scoring = research look-ahead hit/clean.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from backtest.aggregate import aggregate_candles
from backtest.candles import Candle, CandleBuilder, to_utc
from backtest.config import point_size
from backtest.dukascopy import Tick, reaktor_symbol
from backtest.forward import (
    score_all_alerts,
    summarize_forward,
)
from backtest.trades import AlertSignal


ALLOWED_TF = frozenset({15, 30, 60, 240})

def _normalize_entry_hours_utc(hours: Optional[Sequence[int]]) -> Optional[set]:
    """Return a set of allowed UTC hours, or None for no filter."""
    if not hours:
        return None
    out = {int(h) % 24 for h in hours if h is not None}
    return out or None


def _entry_hour_allowed(ts, allowed: Optional[set]) -> bool:
    """True if entry_hours_utc is unset/empty or ts's UTC hour is in the set."""
    if not allowed:
        return True
    return to_utc(ts).hour in allowed


@dataclass
class IfvgParams:
    timeframe_min: int = 15
    swing_lookback: int = 3
    entry_mode: str = "first_touch"  # first_touch | ce_touch
    sl_mode: str = "far_edge"  # far_edge | below_ce
    hours: float = 6.0
    thresholds: List[float] = field(
        default_factory=lambda: [100.0, 200.0, 500.0, 800.0, 1000.0, 1200.0, 1500.0, 2000.0]
    )
    adverse_mult: float = 1.0
    side_filter: str = "both"  # both | long | short
    max_wait_bars: int = 24
    fvg_after_raid_bars: int = 8
    skip_ignored: bool = True
    # None or empty = allow all UTC hours; else only enter when tick hour is in set.
    entry_hours_utc: Optional[List[int]] = None


@dataclass
class IfvgSignal:
    entry_ts: str
    side: str  # UP | DOWN
    entry: float
    p: float
    ce: float
    distal: float
    sl: float
    swing: float
    raid_ts: str
    fvg_ts: str
    confirm_ts: str
    timeframe_min: int
    entry_mode: str
    sl_mode: str
    tick_index: int = 0
    # per-threshold score stamps (filled after forward walk)
    scores: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _PendingFvg:
    side: str  # bullish IFVG = long after SSL; bearish IFVG = short after BSL
    p: float
    distal: float
    ce: float
    swing: float
    raid_ts: str
    fvg_ts: str
    fvg_bar_i: int
    confirmed: bool = False
    confirm_ts: Optional[str] = None
    ce_touched: bool = False
    wait_bars: int = 0


def _iso(ts: datetime) -> str:
    return to_utc(ts).isoformat()


def _bars_from_completed(completed: Sequence[Candle]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in completed:
        out.append(
            {
                "open_time": c.open_time,
                "close_time": c.close_time,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "tick_count": int(c.tick_count or 0),
            }
        )
    return out


def _as_candle_list(bars: Sequence[Any]) -> List[Candle]:
    """Normalize aggregate dicts or Candle objects to Candle list."""
    out: List[Candle] = []
    for b in bars:
        if isinstance(b, Candle):
            out.append(b)
            continue
        if isinstance(b, dict):
            ot = b.get("open_time")
            ct = b.get("close_time")
            if isinstance(ot, str):
                ot = datetime.fromisoformat(ot.replace("Z", "+00:00"))
            if isinstance(ct, str):
                ct = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            if ot is None:
                continue
            ot = to_utc(ot)
            if ct is None:
                ct = ot + timedelta(minutes=int(b.get("timeframe_min") or 15))
            else:
                ct = to_utc(ct)
            out.append(
                Candle(
                    open_time=ot,
                    close_time=ct,
                    open=float(b["open"]),
                    high=float(b["high"]),
                    low=float(b["low"]),
                    close=float(b["close"]),
                    is_closed=True,
                    tick_count=int(b.get("tick_count") or 0),
                )
            )
    return out


def build_tf_candles(
    ticks: Sequence[Tick],
    *,
    timeframe_min: int = 15,
    skip_ignored: bool = True,
    progress: Optional[Callable[..., None]] = None,
) -> List[Candle]:
    """Build 15m from ticks; aggregate to 30/60/240 when requested."""
    tf = int(timeframe_min)
    if tf not in ALLOWED_TF:
        raise ValueError(f"timeframe_min must be one of {sorted(ALLOWED_TF)}")
    builder = CandleBuilder(
        timeframe_minutes=15,
        max_completed=50_000,
        skip_ignored=skip_ignored,
    )
    n = len(ticks)
    last = time.monotonic()
    for i, t in enumerate(ticks):
        builder.add_price(float(t.mid), to_utc(t.ts))
        now = time.monotonic()
        if progress and (now - last >= 0.4 or i == n - 1):
            last = now
            progress(phase="candles", ticks_done=i + 1, ticks_total=n, pct=round(5 + 25 * (i + 1) / max(n, 1), 1))
    # finalize forming bar if any ticks remain conceptually — only completed used
    completed = list(builder.completed_candles)
    if tf == 15:
        return completed
    agg = aggregate_candles(_bars_from_completed(completed), tf, base_tf_min=15, include_incomplete=False)
    return _as_candle_list(agg)


def _is_swing_low(bars: Sequence[Candle], i: int, lb: int) -> bool:
    if i < lb or i + lb >= len(bars):
        return False
    lo = bars[i].low
    for j in range(i - lb, i + lb + 1):
        if j == i:
            continue
        if bars[j].low <= lo + 1e-12:
            return False
    return True


def _is_swing_high(bars: Sequence[Candle], i: int, lb: int) -> bool:
    if i < lb or i + lb >= len(bars):
        return False
    hi = bars[i].high
    for j in range(i - lb, i + lb + 1):
        if j == i:
            continue
        if bars[j].high >= hi - 1e-12:
            return False
    return True


def _bearish_fvg(c1: Candle, c3: Candle) -> Optional[Tuple[float, float, float]]:
    """Bearish FVG: C1.low > C3.high. Returns (P, bottom/distal, CE)."""
    if float(c1.low) > float(c3.high) + 1e-12:
        p = float(c1.low)
        distal = float(c3.high)
        ce = (p + distal) / 2.0
        return p, distal, ce
    return None


def _bullish_fvg(c1: Candle, c3: Candle) -> Optional[Tuple[float, float, float]]:
    """Bullish FVG: C1.high < C3.low. Returns (P, top/distal, CE)."""
    if float(c1.high) + 1e-12 < float(c3.low):
        p = float(c1.high)
        distal = float(c3.low)
        ce = (p + distal) / 2.0
        return p, distal, ce
    return None


def _sl_price(side: str, distal: float, ce: float, sl_mode: str, ps: float) -> float:
    buf = max(ps, 1e-9)  # one point buffer past the edge
    if side == "UP":
        if sl_mode == "below_ce":
            return ce - buf
        return distal - buf
    if sl_mode == "below_ce":  # for shorts: above CE
        return ce + buf
    return distal + buf


def _in_long_zone(px: float, p: float, ce: float) -> bool:
    lo = min(p, ce)
    hi = max(p, ce)
    return lo - 1e-12 <= px <= hi + 1e-12


def _in_short_zone(px: float, p: float, ce: float) -> bool:
    lo = min(p, ce)
    hi = max(p, ce)
    return lo - 1e-12 <= px <= hi + 1e-12


def _tick_index_at_or_after(ticks: Sequence[Tick], ts: datetime, hint: int = 0) -> int:
    """First tick with ts >= target. hint is a lower bound for speed."""
    target = to_utc(ts).timestamp()
    i = max(0, min(hint, len(ticks) - 1)) if ticks else 0
    # rewind a bit if hint overshot
    while i > 0 and to_utc(ticks[i].ts).timestamp() > target:
        i -= 1
    while i < len(ticks) and to_utc(ticks[i].ts).timestamp() < target - 1e-9:
        i += 1
    if i >= len(ticks):
        return max(0, len(ticks) - 1)
    return i


def detect_ifvg_on_bars(
    bars: Sequence[Candle],
    *,
    params: IfvgParams,
    ps: float,
) -> List[Dict[str, Any]]:
    """
    Pure bar walk → pending entry setups that are confirmed and still waiting.
    Returns armed setups with bar index of confirm (entry searched on ticks separately).
    """
    lb = max(1, int(params.swing_lookback))
    after = max(1, int(params.fvg_after_raid_bars))
    max_wait = max(1, int(params.max_wait_bars))
    side_f = (params.side_filter or "both").lower()

    swing_lows: List[Tuple[int, float]] = []  # (bar_i, price)
    swing_highs: List[Tuple[int, float]] = []
    armed: List[_PendingFvg] = []
    # temporary: SSL/BSL events awaiting FVG
    ssl_events: List[Tuple[int, float, str]] = []  # bar_i, swing, iso
    bsl_events: List[Tuple[int, float, str]] = []

    confirmed_entries: List[Dict[str, Any]] = []

    for i, bar in enumerate(bars):
        # confirm swings that just became valid (center = i - lb)
        center = i - lb
        if center >= lb:
            if _is_swing_low(bars, center, lb):
                swing_lows.append((center, float(bars[center].low)))
            if _is_swing_high(bars, center, lb):
                swing_highs.append((center, float(bars[center].high)))

        # raids
        if swing_lows and float(bar.low) < swing_lows[-1][1] - 1e-12:
            ssl_events.append((i, swing_lows[-1][1], _iso(bar.close_time)))
            # keep only recent
            ssl_events = [e for e in ssl_events if i - e[0] <= after]
        if swing_highs and float(bar.high) > swing_highs[-1][1] + 1e-12:
            bsl_events.append((i, swing_highs[-1][1], _iso(bar.close_time)))
            bsl_events = [e for e in bsl_events if i - e[0] <= after]

        # FVG detection on completed triple ending at i
        if i >= 2:
            c1, c3 = bars[i - 2], bars[i]
            bear = _bearish_fvg(c1, c3)
            bull = _bullish_fvg(c1, c3)
            if bear and side_f in ("both", "long", "up"):
                # need a recent SSL at or before this FVG
                for raid_i, swing, raid_ts in reversed(ssl_events):
                    if raid_i > i:
                        continue
                    if i - raid_i > after:
                        break
                    # FVG should relate to the raid move (C3 near/through raid)
                    p, distal, ce = bear
                    if distal <= swing + 1e-9 or float(c3.low) <= swing + 1e-9:
                        armed.append(
                            _PendingFvg(
                                side="UP",
                                p=p,
                                distal=distal,
                                ce=ce,
                                swing=swing,
                                raid_ts=raid_ts,
                                fvg_ts=_iso(c3.close_time),
                                fvg_bar_i=i,
                            )
                        )
                        break
            if bull and side_f in ("both", "short", "down"):
                for raid_i, swing, raid_ts in reversed(bsl_events):
                    if raid_i > i:
                        continue
                    if i - raid_i > after:
                        break
                    p, distal, ce = bull
                    if distal >= swing - 1e-9 or float(c3.high) >= swing - 1e-9:
                        armed.append(
                            _PendingFvg(
                                side="DOWN",
                                p=p,
                                distal=distal,
                                ce=ce,
                                swing=swing,
                                raid_ts=raid_ts,
                                fvg_ts=_iso(c3.close_time),
                                fvg_bar_i=i,
                            )
                        )
                        break

        # confirm + expire armed
        still: List[_PendingFvg] = []
        for pend in armed:
            if i <= pend.fvg_bar_i:
                still.append(pend)
                continue
            if not pend.confirmed:
                if pend.side == "UP" and float(bar.close) > pend.p + 1e-12:
                    pend.confirmed = True
                    pend.confirm_ts = _iso(bar.close_time)
                    pend.wait_bars = 0
                elif pend.side == "DOWN" and float(bar.close) < pend.p - 1e-12:
                    pend.confirmed = True
                    pend.confirm_ts = _iso(bar.close_time)
                    pend.wait_bars = 0
                else:
                    # still waiting for confirm; expire if too long after FVG
                    if i - pend.fvg_bar_i > max_wait:
                        continue
                    still.append(pend)
                    continue
            if pend.confirmed:
                pend.wait_bars += 1
                if pend.wait_bars > max_wait:
                    continue
                confirmed_entries.append(
                    {
                        "pending": pend,
                        "confirm_bar_i": i if pend.wait_bars == 1 else None,
                        "active_from_bar": i,
                    }
                )
                # keep pending for tick-level entry search — store once confirmed
                still.append(pend)
        armed = still

    # Deduplicate: return unique confirmed pendings (by fvg_bar_i + side)
    uniq: Dict[Tuple[str, int], _PendingFvg] = {}
    for pend in armed:
        if pend.confirmed:
            uniq[(pend.side, pend.fvg_bar_i)] = pend
    # Also include any that were confirmed but expired from still? They are gone.
    # Re-walk to collect all that got confirmed (even if expired without fill — entries done on ticks)
    return list(uniq.values())


def run_ifvg(
    ticks: Sequence[Tick],
    *,
    symbol: str = "XAU/USD",
    params: Optional[IfvgParams] = None,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    params = params or IfvgParams()
    sym = symbol if "/" in symbol else reaktor_symbol(symbol)
    ps = point_size(sym)
    if ps <= 0 or not ticks:
        return summarize_ifvg([], params, symbol=sym, ticks=len(ticks or []), by_t={})

    tf = int(params.timeframe_min)
    if tf not in ALLOWED_TF:
        raise ValueError(f"timeframe_min must be one of {sorted(ALLOWED_TF)}")

    bars = build_tf_candles(
        ticks,
        timeframe_min=tf,
        skip_ignored=bool(params.skip_ignored),
        progress=progress,
    )
    if len(bars) < max(10, int(params.swing_lookback) * 2 + 3):
        return summarize_ifvg([], params, symbol=sym, ticks=len(ticks), by_t={})

    lb = max(1, int(params.swing_lookback))
    after = max(1, int(params.fvg_after_raid_bars))
    max_wait = max(1, int(params.max_wait_bars))
    entry_mode = (params.entry_mode or "first_touch").lower()
    sl_mode = (params.sl_mode or "far_edge").lower()
    side_f = (params.side_filter or "both").lower()
    entry_hours = _normalize_entry_hours_utc(params.entry_hours_utc)

    swing_lows: List[Tuple[int, float]] = []
    swing_highs: List[Tuple[int, float]] = []
    ssl_events: List[Tuple[int, float, str]] = []
    bsl_events: List[Tuple[int, float, str]] = []
    pending: List[_PendingFvg] = []
    signals: List[IfvgSignal] = []
    alerts: List[AlertSignal] = []
    alert_idx: List[int] = []

    # Map bar close_time → approximate tick index (built on the fly)
    tick_hint = 0

    def bar_tick_i(bar: Candle) -> int:
        nonlocal tick_hint
        tick_hint = _tick_index_at_or_after(ticks, bar.close_time, tick_hint)
        return tick_hint

    n_bars = len(bars)
    last_yield = time.monotonic()

    for i, bar in enumerate(bars):
        center = i - lb
        if center >= lb:
            if _is_swing_low(bars, center, lb):
                swing_lows.append((center, float(bars[center].low)))
            if _is_swing_high(bars, center, lb):
                swing_highs.append((center, float(bars[center].high)))

        if swing_lows and float(bar.low) < swing_lows[-1][1] - 1e-12:
            ssl_events.append((i, swing_lows[-1][1], _iso(bar.close_time)))
            ssl_events = [e for e in ssl_events if i - e[0] <= after]
        if swing_highs and float(bar.high) > swing_highs[-1][1] + 1e-12:
            bsl_events.append((i, swing_highs[-1][1], _iso(bar.close_time)))
            bsl_events = [e for e in bsl_events if i - e[0] <= after]

        if i >= 2:
            c1, c3 = bars[i - 2], bars[i]
            bear = _bearish_fvg(c1, c3)
            bull = _bullish_fvg(c1, c3)
            if bear and side_f in ("both", "long", "up"):
                for raid_i, swing, raid_ts in reversed(ssl_events):
                    if i - raid_i > after:
                        break
                    p, distal, ce = bear
                    if distal <= swing + 1e-9 or float(c3.low) <= swing + 1e-9:
                        pending.append(
                            _PendingFvg(
                                side="UP",
                                p=p,
                                distal=distal,
                                ce=ce,
                                swing=swing,
                                raid_ts=raid_ts,
                                fvg_ts=_iso(c3.close_time),
                                fvg_bar_i=i,
                            )
                        )
                        break
            if bull and side_f in ("both", "short", "down"):
                for raid_i, swing, raid_ts in reversed(bsl_events):
                    if i - raid_i > after:
                        break
                    p, distal, ce = bull
                    if distal >= swing - 1e-9 or float(c3.high) >= swing - 1e-9:
                        pending.append(
                            _PendingFvg(
                                side="DOWN",
                                p=p,
                                distal=distal,
                                ce=ce,
                                swing=swing,
                                raid_ts=raid_ts,
                                fvg_ts=_iso(c3.close_time),
                                fvg_bar_i=i,
                            )
                        )
                        break

        # Update pending: confirm / expire; entry search uses ticks in (prev_close, this_close]
        prev_close = bars[i - 1].close_time if i > 0 else bar.open_time
        t0 = _tick_index_at_or_after(ticks, prev_close, max(0, tick_hint - 50))
        t1 = bar_tick_i(bar)

        still: List[_PendingFvg] = []
        for pend in pending:
            if i < pend.fvg_bar_i:
                still.append(pend)
                continue

            if not pend.confirmed:
                if i == pend.fvg_bar_i:
                    still.append(pend)
                    continue
                if pend.side == "UP" and float(bar.close) > pend.p + 1e-12:
                    pend.confirmed = True
                    pend.confirm_ts = _iso(bar.close_time)
                    pend.wait_bars = 0
                elif pend.side == "DOWN" and float(bar.close) < pend.p - 1e-12:
                    pend.confirmed = True
                    pend.confirm_ts = _iso(bar.close_time)
                    pend.wait_bars = 0
                elif i - pend.fvg_bar_i > max_wait:
                    continue
                else:
                    still.append(pend)
                    continue

            # confirmed — look for entry on ticks of this bar (after confirm bar)
            if pend.wait_bars == 0 and pend.confirm_ts and i > pend.fvg_bar_i:
                # first bar after confirm starts wait
                pass
            if i > pend.fvg_bar_i and pend.confirmed:
                # only search entry after the confirm candle has closed
                confirm_done = pend.confirm_ts is not None and i >= 0
                # Entry starts from the bar AFTER confirm
                confirmed_at_or_before = False
                if pend.confirm_ts:
                    try:
                        cts = datetime.fromisoformat(pend.confirm_ts.replace("Z", "+00:00"))
                        confirmed_at_or_before = to_utc(bar.close_time) >= to_utc(cts)
                    except Exception:
                        confirmed_at_or_before = True
                if confirmed_at_or_before and i > pend.fvg_bar_i:
                    # if this bar is the confirm bar itself, don't enter yet
                    is_confirm_bar = False
                    try:
                        cts = datetime.fromisoformat(pend.confirm_ts.replace("Z", "+00:00"))
                        is_confirm_bar = abs((to_utc(bar.close_time) - to_utc(cts)).total_seconds()) < 1.0
                    except Exception:
                        is_confirm_bar = False
                    if not is_confirm_bar:
                        filled = False
                        for ti in range(t0, min(t1 + 1, len(ticks))):
                            px = float(ticks[ti].mid)
                            if pend.side == "UP":
                                if entry_mode == "ce_touch":
                                    if px <= pend.ce + 1e-12:
                                        pend.ce_touched = True
                                    if not pend.ce_touched:
                                        continue
                                if _in_long_zone(px, pend.p, pend.ce):
                                    if not _entry_hour_allowed(ticks[ti].ts, entry_hours):
                                        continue
                                    sl = _sl_price("UP", pend.distal, pend.ce, sl_mode, ps)
                                    sig = IfvgSignal(
                                        entry_ts=_iso(ticks[ti].ts),
                                        side="UP",
                                        entry=round(px, 5),
                                        p=round(pend.p, 5),
                                        ce=round(pend.ce, 5),
                                        distal=round(pend.distal, 5),
                                        sl=round(sl, 5),
                                        swing=round(pend.swing, 5),
                                        raid_ts=pend.raid_ts,
                                        fvg_ts=pend.fvg_ts,
                                        confirm_ts=pend.confirm_ts or "",
                                        timeframe_min=tf,
                                        entry_mode=entry_mode,
                                        sl_mode=sl_mode,
                                        tick_index=ti,
                                    )
                                    signals.append(sig)
                                    alerts.append(
                                        AlertSignal(
                                            kind="ifvg",
                                            symbol=sym,
                                            side="UP",
                                            ts=to_utc(ticks[ti].ts),
                                            price=px,
                                            meta={
                                                "p": pend.p,
                                                "ce": pend.ce,
                                                "distal": pend.distal,
                                                "sl": sl,
                                                "swing": pend.swing,
                                            },
                                        )
                                    )
                                    alert_idx.append(ti)
                                    filled = True
                                    break
                            else:
                                if entry_mode == "ce_touch":
                                    if px >= pend.ce - 1e-12:
                                        pend.ce_touched = True
                                    if not pend.ce_touched:
                                        continue
                                if _in_short_zone(px, pend.p, pend.ce):
                                    if not _entry_hour_allowed(ticks[ti].ts, entry_hours):
                                        continue
                                    sl = _sl_price("DOWN", pend.distal, pend.ce, sl_mode, ps)
                                    sig = IfvgSignal(
                                        entry_ts=_iso(ticks[ti].ts),
                                        side="DOWN",
                                        entry=round(px, 5),
                                        p=round(pend.p, 5),
                                        ce=round(pend.ce, 5),
                                        distal=round(pend.distal, 5),
                                        sl=round(sl, 5),
                                        swing=round(pend.swing, 5),
                                        raid_ts=pend.raid_ts,
                                        fvg_ts=pend.fvg_ts,
                                        confirm_ts=pend.confirm_ts or "",
                                        timeframe_min=tf,
                                        entry_mode=entry_mode,
                                        sl_mode=sl_mode,
                                        tick_index=ti,
                                    )
                                    signals.append(sig)
                                    alerts.append(
                                        AlertSignal(
                                            kind="ifvg",
                                            symbol=sym,
                                            side="DOWN",
                                            ts=to_utc(ticks[ti].ts),
                                            price=px,
                                            meta={
                                                "p": pend.p,
                                                "ce": pend.ce,
                                                "distal": pend.distal,
                                                "sl": sl,
                                                "swing": pend.swing,
                                            },
                                        )
                                    )
                                    alert_idx.append(ti)
                                    filled = True
                                    break
                        if filled:
                            continue  # drop pend
                    pend.wait_bars += 1
                    if pend.wait_bars > max_wait:
                        continue
            still.append(pend)
        pending = still

        now = time.monotonic()
        if progress and (now - last_yield >= 0.35 or i == n_bars - 1):
            last_yield = now
            progress(
                phase="scan",
                bars_done=i + 1,
                bars_total=n_bars,
                ticks_done=i + 1,
                ticks_total=n_bars,
                trades=len(signals),
                pct=round(30.0 + 40.0 * ((i + 1) / max(n_bars, 1)), 1),
            )

    # Forward score
    window_sec = float(params.hours) * 3600.0
    thr = [float(t) for t in (params.thresholds or [500.0])]
    by_t: Dict[str, Any] = {}
    if alerts:
        if progress:
            progress(phase="score", message="Forward scoring…", pct=75.0, trades=len(signals))

        def _cb(done: int, total: int) -> None:
            if progress:
                progress(
                    phase="score",
                    message=f"Score {done}/{total}",
                    pct=round(75.0 + 20.0 * done / max(total, 1), 1),
                    trades=len(signals),
                )

        scored = score_all_alerts(
            alerts,
            alert_idx,
            ticks,
            thresholds=thr,
            window_sec=window_sec,
            adverse_mult=float(params.adverse_mult),
            price_field="mid",
            progress_cb=_cb,
        )
        by_t = {
            k: summarize_forward(paths)
            for k, paths in scored.items()
        }
        # stamp each signal
        keys = list(scored.keys())
        for j, sig in enumerate(signals):
            sc: Dict[str, Any] = {}
            for k in keys:
                path = scored[k][j]
                sc[k] = {
                    "hit": bool(path.hit),
                    "clean": bool(path.clean),
                    "max_fav_pts": round(float(path.max_fav_pts), 1),
                    "max_adv_pts": round(float(path.max_adv_pts), 1),
                    "realized_pts": round(float(path.realized_pts), 1),
                    "first_hit_sec": path.first_hit_sec,
                }
            sig.scores = sc

    if progress:
        progress(phase="done", pct=98.0, trades=len(signals))
    return summarize_ifvg(signals, params, symbol=sym, ticks=len(ticks), by_t=by_t)


def summarize_ifvg(
    signals: Sequence[IfvgSignal],
    params: IfvgParams,
    *,
    symbol: str,
    ticks: int,
    by_t: Dict[str, Any],
) -> Dict[str, Any]:
    n = len(signals)
    ups = sum(1 for s in signals if s.side == "UP")
    dns = n - ups
    # Prefer a mid threshold for headline sum_pts
    headline_key = None
    if by_t:
        # pick 500 if present else first
        if "500" in by_t:
            headline_key = "500"
        else:
            headline_key = next(iter(by_t))
    head = by_t.get(headline_key) if headline_key else None
    rows = []
    for s in signals:
        d = asdict(s)
        rows.append(d)
    return {
        "kind": "fvg",
        "symbol": symbol,
        "params": asdict(params),
        "ticks": ticks,
        "trades": n,
        "alerts": n,
        "longs": ups,
        "shorts": dns,
        "by_threshold": by_t,
        "headline_threshold": headline_key,
        "hit_rate_pct": (head or {}).get("hit_rate_pct"),
        "clean_rate_pct": (head or {}).get("clean_rate_pct"),
        "avg_pts": (head or {}).get("avg_realized_pts"),
        "sum_pts": (head or {}).get("sum_realized_pts"),
        "rows": rows,
    }
