"""
15m candle builder (standalone copy of Reaktor logic).

UTC buckets; optional local-hour ignore window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Dict, List, Optional, Sequence, Union
from zoneinfo import ZoneInfo

from backtest import config

TzLike = Union[tzinfo, ZoneInfo]


def to_utc(timestamp: Optional[datetime] = None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def resolve_zone(name: Optional[str]) -> TzLike:
    """
    IANA zone, or datetime.timezone.utc.

    Windows has no system tz database unless the `tzdata` package is installed.
    ZoneInfo('UTC') raises ZoneInfoNotFoundError there — never use it as a fallback.
    """
    key = (name or "").strip() or "UTC"
    if key.upper() in ("UTC", "GMT", "Z", "ETC/UTC"):
        return timezone.utc
    try:
        return ZoneInfo(key)
    except Exception:
        return timezone.utc


_ZONE: Optional[TzLike] = None


def _display_zone() -> TzLike:
    global _ZONE
    if _ZONE is None:
        _ZONE = resolve_zone(getattr(config, "DISPLAY_TZ", None))
    return _ZONE


def is_candle_ignored(open_time: Optional[datetime]) -> bool:
    if open_time is None:
        return False
    cfg = config.CANDLE_IGNORE or {}
    if not cfg.get("enabled", True):
        return False
    start = int(cfg.get("local_hour_start", 0))
    end = int(cfg.get("local_hour_end", 1))
    local = to_utc(open_time).astimezone(_display_zone())
    hour = local.hour
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def is_market_open(now: Optional[datetime] = None) -> bool:
    """Forex/gold session UTC — same rules as Reaktor."""
    now = to_utc(now)
    weekday = now.weekday()  # Mon=0 … Sun=6
    hour = now.hour
    open_h = int(getattr(config, "FOREX_OPEN_SUNDAY_UTC_HOUR", 22))
    close_h = int(getattr(config, "FOREX_CLOSE_FRIDAY_UTC_HOUR", 22))
    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday
        return hour >= open_h
    if weekday == 4:  # Friday
        return hour < close_h
    return True


def market_open_blackout(when: Optional[datetime] = None) -> Optional[str]:
    """
    Factor-compatible market-open blackout.

    If `when` falls in [open, open + N minutes) in MARKET_OPEN_TZ on an
    allowed weekday, return a reason string; else None.
    Default: Monday 01:05 Europe/Bucharest, 15 minutes
    (see factor/config.py MARKET_OPEN_*).
    """
    from datetime import time as dtime

    cfg = getattr(config, "MARKET_OPEN_BLACKOUT", None) or {}
    if not cfg.get("enabled", True):
        return None
    mins = int(cfg.get("minutes") or 0)
    if mins <= 0:
        return None

    raw = str(cfg.get("open_time") or "01:05").strip()
    parts = raw.replace(".", ":").split(":")
    try:
        open_h = int(parts[0])
        open_m = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        return None
    if not (0 <= open_h <= 23 and 0 <= open_m <= 59):
        return None

    tz_s = str(cfg.get("open_tz") or "Europe/Bucharest").strip()
    tz = resolve_zone(tz_s)

    when_utc = to_utc(when)
    local = when_utc.astimezone(tz)

    wd_cfg = cfg.get("weekdays")
    if wd_cfg:
        try:
            allowed = {int(x) for x in wd_cfg}
        except (TypeError, ValueError):
            allowed = set()
        if allowed and local.weekday() not in allowed:
            return None

    open_t = dtime(open_h, open_m)
    open_dt = datetime.combine(local.date(), open_t, tzinfo=tz)
    end_dt = open_dt + timedelta(minutes=mins)

    if local < open_dt:
        open_dt_prev = open_dt - timedelta(days=1)
        end_prev = open_dt_prev + timedelta(minutes=mins)
        if open_dt_prev <= local < end_prev:
            open_dt, end_dt = open_dt_prev, end_prev
        else:
            return None
    elif local >= end_dt:
        return None

    elapsed = (local - open_dt).total_seconds()
    left = max(0.0, mins * 60 - elapsed)
    return (
        f"market_open_blackout:"
        f"{open_h:02d}:{open_m:02d}-{end_dt.strftime('%H:%M')} "
        f"{tz_s} (~{left:.0f}s left)"
    )


def is_session_open_skip(now: Optional[datetime] = None) -> bool:
    """True if Factor-style market-open blackout applies (alerts suppressed)."""
    return market_open_blackout(now) is not None


@dataclass
class Candle:
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    is_closed: bool = False
    tick_count: int = 0


class CandleBuilder:
    def __init__(
        self,
        timeframe_minutes: int = 15,
        max_completed: int = 80,
        skip_ignored: bool = True,
    ):
        self.timeframe_minutes = timeframe_minutes
        self.max_completed = max_completed
        self.skip_ignored = skip_ignored
        self.current_candle: Optional[Candle] = None
        self.completed_candles: List[Candle] = []

    def _get_candle_bounds(self, timestamp: datetime) -> tuple:
        timestamp = to_utc(timestamp)
        minutes = (timestamp.minute // self.timeframe_minutes) * self.timeframe_minutes
        candle_start = timestamp.replace(minute=minutes, second=0, microsecond=0)
        candle_end = candle_start + timedelta(minutes=self.timeframe_minutes)
        return candle_start, candle_end

    def _drop(self, open_time: Optional[datetime]) -> bool:
        return self.skip_ignored and is_candle_ignored(open_time)

    def _append_completed(self, candle: Candle) -> None:
        if self._drop(candle.open_time):
            return
        self.completed_candles.append(candle)
        if len(self.completed_candles) > self.max_completed:
            self.completed_candles = self.completed_candles[-self.max_completed :]

    def add_price(
        self, price: float, timestamp: Optional[datetime] = None
    ) -> Optional[Candle]:
        timestamp = to_utc(timestamp)
        closed: Optional[Candle] = None

        if self.current_candle is not None and timestamp >= self.current_candle.close_time:
            self.current_candle.is_closed = True
            candidate = self.current_candle
            self.current_candle = None
            if not self._drop(candidate.open_time):
                self._append_completed(candidate)
                closed = candidate

        open_time, close_time = self._get_candle_bounds(timestamp)
        if self._drop(open_time):
            return closed

        if self.current_candle is None:
            self.current_candle = Candle(
                open_time=open_time,
                close_time=close_time,
                open=price,
                high=price,
                low=price,
                close=price,
                is_closed=False,
                tick_count=1,
            )
            return closed

        if timestamp < self.current_candle.close_time:
            self.current_candle.high = max(self.current_candle.high, price)
            self.current_candle.low = min(self.current_candle.low, price)
            self.current_candle.close = price
            self.current_candle.tick_count = int(self.current_candle.tick_count or 0) + 1
            return closed

        self.current_candle = Candle(
            open_time=open_time,
            close_time=close_time,
            open=price,
            high=price,
            low=price,
            close=price,
            is_closed=False,
            tick_count=1,
        )
        return closed

    def get_current_candle(self) -> Optional[Candle]:
        return self.current_candle

    def get_completed_candles(self, count: int = 5) -> List[Candle]:
        return self.completed_candles[-count:]


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def epoch_ms(timestamp: datetime) -> int:
    """UTC unix milliseconds. Naive timestamps are treated as UTC."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    elif timestamp.tzinfo is not timezone.utc:
        timestamp = timestamp.astimezone(timezone.utc)
    delta = timestamp - _EPOCH
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def _from_ms(ms: int) -> datetime:
    return _EPOCH + timedelta(milliseconds=int(ms))


class BarFold:
    """OHLC fold that matches CandleBuilder bucket rules without a Tick per quote.

    Buckets are UTC minute-of-hour floors (a 5-minute bar opens at :00, :05, …).
    The bar that is still open after the last quote is dropped, same as build_candles.
    """

    def __init__(self, timeframe_minutes: int = 5, skip_ignored: bool = False):
        self.tf_min = max(1, int(timeframe_minutes))
        self.step_ms = self.tf_min * 60_000
        self.skip_ignored = bool(skip_ignored)
        self.out: List[Candle] = []
        self.last_ms: Optional[int] = None
        self._open_ms: Optional[int] = None
        self._close_ms = 0
        self._o = self._h = self._l = self._c = 0.0
        self._n = 0

    def _bucket_ms(self, ms: int) -> int:
        hour_ms = ms - (ms % 3_600_000)
        minute = ((ms // 1000) % 3600) // 60
        bucket_minute = (minute // self.tf_min) * self.tf_min
        return hour_ms + bucket_minute * 60_000

    def add_ms(self, ms: int, mid: float) -> None:
        ms = int(ms)
        self.last_ms = ms
        if self._open_ms is not None and ms >= self._close_ms:
            self._emit()
            self._open_ms = None
        if self._open_ms is None:
            bucket = self._bucket_ms(ms)
            if self.skip_ignored and is_candle_ignored(_from_ms(bucket)):
                return
            self._open_ms = bucket
            self._close_ms = bucket + self.step_ms
            self._o = self._h = self._l = self._c = float(mid)
            self._n = 1
            return
        price = float(mid)
        if price > self._h:
            self._h = price
        elif price < self._l:
            self._l = price
        self._c = price
        self._n += 1

    def _emit(self) -> None:
        if self._open_ms is None or self._n <= 0:
            return
        self.out.append(
            Candle(
                open_time=_from_ms(self._open_ms),
                close_time=_from_ms(self._close_ms),
                open=self._o,
                high=self._h,
                low=self._l,
                close=self._c,
                is_closed=True,
                tick_count=self._n,
            )
        )

    def finish(self) -> List[Candle]:
        return self.out


def build_candles(
    ticks: Sequence,
    timeframe_minutes: int = 5,
    skip_ignored: bool = False,
) -> List[Candle]:
    """Completed OHLC bars from mids. Drops the in-progress last bar."""
    fold = BarFold(timeframe_minutes, skip_ignored=skip_ignored)
    add = fold.add_ms
    for t in ticks:
        add(epoch_ms(t.ts), (float(t.bid) + float(t.ask)) * 0.5)
    return fold.finish()


def aggregate_tf(candles: Sequence[Candle], tf_min: int) -> List[Candle]:
    """Closed higher-TF bars from a finer UTC bucket. Oldest → newest."""
    step = int(tf_min) * 60
    if step <= 0 or not candles:
        return []
    buckets: Dict[int, List[Candle]] = {}
    order: List[int] = []
    for c in candles:
        ts = int(to_utc(c.open_time).timestamp())
        key = ts - (ts % step)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(c)
    out: List[Candle] = []
    now_limit = to_utc(candles[-1].close_time)
    for key in order:
        parts = buckets[key]
        start = datetime.fromtimestamp(key, tz=timezone.utc)
        end = start + timedelta(minutes=int(tf_min))
        if end > now_limit + timedelta(seconds=1):
            continue
        out.append(
            Candle(
                open_time=start,
                close_time=end,
                open=parts[0].open,
                high=max(p.high for p in parts),
                low=min(p.low for p in parts),
                close=parts[-1].close,
                is_closed=True,
                tick_count=sum(p.tick_count for p in parts),
            )
        )
    return out
