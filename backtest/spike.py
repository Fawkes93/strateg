"""
Short-window spike detector (standalone copy of Reaktor spike signal).

Optimized for multi-million tick replay (incremental window extrema).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Deque, Dict, List, Optional, Sequence, Tuple


def to_utc_ts(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.timestamp()


def candle_hl_points(candle, point_size: float) -> float:
    if candle is None or point_size <= 0:
        return 0.0
    return max(0.0, (float(candle.high) - float(candle.low)) / point_size)


def relative_spike_floor(
    completed_candles: Optional[Sequence],
    point_size: float,
    *,
    lookback: int = 3,
    mult: float = 2.0,
) -> Tuple[float, float, List[float]]:
    if not completed_candles or point_size <= 0 or lookback < 1 or mult <= 0:
        return 0.0, 0.0, []
    recent = list(completed_candles)[-int(lookback) :]
    if not recent:
        return 0.0, 0.0, []
    hls = [candle_hl_points(c, point_size) for c in recent]
    med = float(median(hls))
    return med, med * float(mult), hls


def effective_min_points(
    base_min: float,
    completed_candles: Optional[Sequence],
    point_size: float,
    *,
    lookback: int = 3,
    mult: float = 2.0,
    relative_enabled: bool = True,
) -> Tuple[float, float, float, List[float]]:
    base = float(base_min)
    if not relative_enabled:
        return base, base, 0.0, []
    med, rel, hls = relative_spike_floor(
        completed_candles, point_size, lookback=lookback, mult=mult
    )
    if not hls:
        return base, base, 0.0, []
    return max(base, rel), base, rel, hls


@dataclass
class SpikeHit:
    symbol: str
    direction: str
    points: float
    move_price: float
    ref_price: float
    extreme_price: float
    current_price: float
    window_sec: float
    point_size: float
    min_points: float
    base_min_points: float = 0.0
    relative_floor_points: float = 0.0
    median_hl_points: float = 0.0


class SymbolSpikeState:
    MAX_TICKS = 2500

    def __init__(self, window_sec: float):
        self.window_sec = window_sec
        self.ticks: Deque[Tuple[float, float]] = deque()
        # Incremental extrema (rebuilt when leftmost tick is removed)
        self._hi: float = float("-inf")
        self._lo: float = float("inf")
        self._dirty: bool = False

    def add(self, ts: float, price: float) -> None:
        self.ticks.append((ts, price))
        if price > self._hi:
            self._hi = price
        if price < self._lo:
            self._lo = price
        cutoff = ts - self.window_sec
        popped = False
        while self.ticks and self.ticks[0][0] < cutoff:
            self.ticks.popleft()
            popped = True
        while len(self.ticks) > self.MAX_TICKS:
            self.ticks.popleft()
            popped = True
        if popped:
            self._dirty = True

    def _ensure_extrema(self) -> None:
        if not self._dirty:
            return
        if not self.ticks:
            self._hi = float("-inf")
            self._lo = float("inf")
        else:
            prices = [p for _, p in self.ticks]
            self._hi = max(prices)
            self._lo = min(prices)
        self._dirty = False

    def evaluate(
        self,
        symbol: str,
        point_size: float,
        min_points: float,
        *,
        base_min_points: float = 0.0,
        relative_floor_points: float = 0.0,
        median_hl_points: float = 0.0,
    ) -> Optional[SpikeHit]:
        if len(self.ticks) < 2 or point_size <= 0:
            return None

        ref_ts, ref_price = self.ticks[0]
        last_ts, current_price = self.ticks[-1]
        span = last_ts - ref_ts
        if span < self.window_sec * 0.5:
            return None

        self._ensure_extrema()
        hi = self._hi
        lo = self._lo

        up_move = hi - ref_price
        down_move = ref_price - lo

        if up_move >= down_move:
            direction = "UP"
            extreme = hi
            move_price = up_move
        else:
            direction = "DOWN"
            extreme = lo
            move_price = down_move

        points = move_price / point_size
        if points + 1e-9 < min_points:
            return None

        return SpikeHit(
            symbol=symbol,
            direction=direction,
            points=points,
            move_price=move_price if direction == "UP" else -move_price,
            ref_price=ref_price,
            extreme_price=extreme,
            current_price=current_price,
            window_sec=span,
            point_size=point_size,
            min_points=min_points,
            base_min_points=base_min_points or min_points,
            relative_floor_points=relative_floor_points,
            median_hl_points=median_hl_points,
        )


class SpikeDetector:
    def __init__(self, cfg: Dict[str, dict]):
        self.config = cfg
        self._states: Dict[str, SymbolSpikeState] = {}
        self._last_alert_at: Dict[str, float] = {}
        # Cache relative floors keyed by completed-candle identity
        self._floor_cache: Dict[str, Tuple] = {}
        for symbol, sc in cfg.items():
            if sc.get("enabled", True):
                self._states[symbol] = SymbolSpikeState(
                    window_sec=float(sc.get("window_sec", 60))
                )

    def _floors(
        self,
        symbol: str,
        sc: dict,
        completed_candles: Optional[Sequence],
    ) -> Tuple[float, float, float, List[float]]:
        n = len(completed_candles) if completed_candles else 0
        last_ot = (
            completed_candles[-1].open_time
            if completed_candles and n
            else None
        )
        key = (
            n,
            last_ot,
            sc.get("relative_lookback"),
            sc.get("relative_mult"),
            sc.get("relative_enabled"),
            sc.get("min_points"),
            sc.get("point_size"),
        )
        cached = self._floor_cache.get(symbol)
        if cached and cached[0] == key:
            return cached[1]

        result = effective_min_points(
            float(sc["min_points"]),
            completed_candles,
            float(sc["point_size"]),
            lookback=int(sc.get("relative_lookback", 3)),
            mult=float(sc.get("relative_mult", 2.0)),
            relative_enabled=bool(sc.get("relative_enabled", True)),
        )
        eff, base, rel, hls = result
        med = float(median(hls)) if hls else 0.0
        packed = (eff, base, rel, med)
        self._floor_cache[symbol] = (key, packed)
        return packed

    def update(
        self,
        symbol: str,
        price: float,
        timestamp: Optional[datetime] = None,
        completed_candles: Optional[Sequence] = None,
    ) -> Optional[SpikeHit]:
        sc = self.config.get(symbol)
        if not sc or not sc.get("enabled", True):
            return None
        if symbol not in self._states or price <= 0:
            return None

        ts = (
            datetime.now(timezone.utc).timestamp()
            if timestamp is None
            else to_utc_ts(timestamp)
        )
        state = self._states[symbol]
        state.window_sec = float(sc.get("window_sec", 60))
        state.add(ts, price)

        cooldown_sec = float(sc.get("cooldown_min", 60)) * 60.0
        last = self._last_alert_at.get(symbol, 0.0)
        if ts - last < cooldown_sec:
            return None

        eff, base, rel, med = self._floors(symbol, sc, completed_candles)
        hit = state.evaluate(
            symbol=symbol,
            point_size=float(sc["point_size"]),
            min_points=eff,
            base_min_points=base,
            relative_floor_points=rel,
            median_hl_points=med,
        )
        if hit is None:
            return None
        self._last_alert_at[symbol] = ts
        return hit
