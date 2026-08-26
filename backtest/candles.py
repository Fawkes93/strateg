"""
15m candle builder (standalone copy of Reaktor logic).

UTC buckets; optional local-hour ignore window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from backtest import config


def to_utc(timestamp: Optional[datetime] = None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


_ZONE: Optional[ZoneInfo] = None


def _display_zone() -> ZoneInfo:
    global _ZONE
    if _ZONE is None:
        try:
            _ZONE = ZoneInfo(config.DISPLAY_TZ)
        except Exception:
            _ZONE = ZoneInfo("UTC")
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
    try:
        tz = ZoneInfo(tz_s)
    except Exception:
        tz = ZoneInfo("Europe/Bucharest")

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
