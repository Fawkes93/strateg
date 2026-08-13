"""
Build 1-hour bars from ticks in a local timezone (default Europe/Chisinau).

Open hour is the local wall hour (DST-aware). Times on the bar are UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from backtest.dukascopy import Tick


@dataclass
class H1Bar:
    open_time: datetime  # UTC
    close_time: datetime  # UTC
    local_date: date
    local_hour: int
    open: float
    high: float
    low: float
    close: float
    tick_count: int = 0


def _local_hour_start(ts: datetime, tz: ZoneInfo) -> datetime:
    loc = ts.astimezone(tz)
    return loc.replace(minute=0, second=0, microsecond=0)


def build_h1(
    ticks: Iterable[Tick],
    tz_name: str = "Europe/Chisinau",
) -> List[H1Bar]:
    tz = ZoneInfo(tz_name)
    bars: List[H1Bar] = []
    cur: Optional[H1Bar] = None

    for t in ticks:
        px = t.mid
        start_local = _local_hour_start(t.ts, tz)
        open_utc = start_local.astimezone(ZoneInfo("UTC"))
        close_utc = (start_local + timedelta(hours=1)).astimezone(ZoneInfo("UTC"))
        key = (start_local.date(), start_local.hour)

        if cur is None or (cur.local_date, cur.local_hour) != key:
            if cur is not None:
                bars.append(cur)
            cur = H1Bar(
                open_time=open_utc,
                close_time=close_utc,
                local_date=start_local.date(),
                local_hour=start_local.hour,
                open=px,
                high=px,
                low=px,
                close=px,
                tick_count=1,
            )
            continue

        cur.high = max(cur.high, px)
        cur.low = min(cur.low, px)
        cur.close = px
        cur.tick_count += 1

    if cur is not None:
        bars.append(cur)
    return bars


def utc_hours_for_local_window(
    date_from: str,
    date_to: str,
    tz_name: str = "Europe/Chisinau",
    *,
    hour_from: int = 3,
    hour_to: int = 12,
    skip_weekends: bool = True,
) -> List[datetime]:
    """
    UTC hour-starts covering local [hour_from, hour_to] inclusive
    on each local date in [date_from, date_to).

    hour_to=12 includes 12:00–13:00 so a noon flatten tick exists.
    Weekends (Sat/Sun local) are skipped by default — gold is closed then.
    """
    from datetime import time as dtime

    tz = ZoneInfo(tz_name)
    d0 = datetime.strptime(date_from, "%Y-%m-%d").date()
    d1 = datetime.strptime(date_to, "%Y-%m-%d").date()
    out: List[datetime] = []
    d = d0
    while d < d1:
        if skip_weekends and d.weekday() >= 5:
            d += timedelta(days=1)
            continue
        for h in range(int(hour_from), int(hour_to) + 1):
            local = datetime.combine(d, dtime(h, 0), tzinfo=tz)
            out.append(local.astimezone(ZoneInfo("UTC")).replace(minute=0, second=0, microsecond=0))
        d += timedelta(days=1)
    # unique + sorted (DST can theoretically collide; keep order)
    seen = set()
    uniq: List[datetime] = []
    for h in out:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def index_h1(bars: Iterable[H1Bar]) -> Dict[Tuple[date, int], H1Bar]:
    """(local_date, local_hour) → bar. Last write wins if duplicates."""
    out: Dict[Tuple[date, int], H1Bar] = {}
    for b in bars:
        out[(b.local_date, b.local_hour)] = b
    return out
