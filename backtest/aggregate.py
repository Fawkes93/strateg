"""
Aggregate lower-timeframe OHLC bars into higher timeframes.

Ported from reaktor/candles/aggregate.py for Strateg IFVG (30/60/240 from 15m).
Does not write to any database — pure transform.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Union


def _parse_time(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
    else:
        s = str(val).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _bucket_start(dt: datetime, timeframe_min: int) -> datetime:
    """Floor UTC time to timeframe boundary."""
    ts = int(dt.timestamp())
    step = timeframe_min * 60
    floored = ts - (ts % step)
    return datetime.fromtimestamp(floored, tz=timezone.utc)


def _bar_dict(
    *,
    open_time: datetime,
    close_time: datetime,
    o: float,
    h: float,
    l: float,
    c: float,
    timeframe_min: int,
    source: str = "agg",
    tick_count: Optional[int] = None,
    volume: Optional[float] = None,
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "open_time": open_time.isoformat(),
        "close_time": close_time.isoformat(),
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
        "timeframe_min": int(timeframe_min),
        "source": source,
        "range_pct": (
            round(((float(h) - float(l)) / float(o)) * 100, 6) if o else None
        ),
    }
    if tick_count is not None:
        d["tick_count"] = int(tick_count)
    if volume is not None:
        d["volume"] = float(volume)
    return d


def _opt_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _opt_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def aggregate_candles(
    bars: Sequence[Union[Dict[str, Any], Any]],
    timeframe_min: int,
    *,
    base_tf_min: int = 15,
    include_incomplete: bool = True,
) -> List[Dict[str, Any]]:
    """
    Aggregate OHLC bars into a higher timeframe.

    `bars` may be dicts (API/Supabase rows) with open_time/open/high/low/close
    or objects with the same attributes. Expected oldest → newest.

    timeframe_min must be a multiple of base_tf_min (e.g. 60, 240 from 15).
    """
    tf = int(timeframe_min)
    base = int(base_tf_min)
    if tf < base:
        raise ValueError(f"timeframe_min {tf} < base {base}")
    if tf % base != 0:
        raise ValueError(f"timeframe_min {tf} must be a multiple of {base}")

    if tf == base:
        # Normalize to dict list
        out: List[Dict[str, Any]] = []
        for b in bars:
            if isinstance(b, dict):
                out.append(dict(b))
            else:
                ot = _parse_time(getattr(b, "open_time", None))
                ct = _parse_time(getattr(b, "close_time", None))
                if ot is None:
                    continue
                out.append(
                    _bar_dict(
                        open_time=ot,
                        close_time=ct or (ot + timedelta(minutes=base)),
                        o=float(b.open),
                        h=float(b.high),
                        l=float(b.low),
                        c=float(b.close),
                        timeframe_min=base,
                        source=getattr(b, "source", "ws") or "ws",
                        tick_count=_opt_int(getattr(b, "tick_count", None)),
                        volume=_opt_float(getattr(b, "volume", None)),
                    )
                )
        return out

    # Parse & sort: (ot, o, h, l, c, tick_count|None, volume|None)
    parsed: List[tuple] = []
    for b in bars:
        if isinstance(b, dict):
            ot = _parse_time(b.get("open_time"))
            if ot is None:
                continue
            parsed.append(
                (
                    ot,
                    float(b["open"]),
                    float(b["high"]),
                    float(b["low"]),
                    float(b["close"]),
                    _opt_int(b.get("tick_count")),
                    _opt_float(b.get("volume")),
                )
            )
        else:
            ot = _parse_time(getattr(b, "open_time", None))
            if ot is None:
                continue
            parsed.append(
                (
                    ot,
                    float(b.open),
                    float(b.high),
                    float(b.low),
                    float(b.close),
                    _opt_int(getattr(b, "tick_count", None)),
                    _opt_float(getattr(b, "volume", None)),
                )
            )
    parsed.sort(key=lambda x: x[0])

    if not parsed:
        return []

    buckets: Dict[datetime, list] = {}
    order: List[datetime] = []
    for row in parsed:
        ot = row[0]
        start = _bucket_start(ot, tf)
        if start not in buckets:
            buckets[start] = []
            order.append(start)
        buckets[start].append(row)

    need = tf // base  # e.g. 4 for 1h from 15m; 96 for 1d
    # Daily: gold rarely has a full 96×15m every calendar day (session gaps).
    # Requiring `need` dropped almost all days → ~3 candles on the 1d chart.
    min_bars = 1 if tf >= 1440 else need
    strict = min_bars >= need
    result: List[Dict[str, Any]] = []
    for i, start in enumerate(order):
        group = buckets[start]
        group.sort(key=lambda x: x[0])
        complete = len(group) >= need
        is_last = i == len(order) - 1
        if strict:
            if not complete and not (include_incomplete and is_last and len(group) > 0):
                continue
        elif len(group) < min_bars:
            continue
        o = group[0][1]
        h = max(x[2] for x in group)
        l = min(x[3] for x in group)
        c = group[-1][4]
        tcs = [x[5] for x in group if x[5] is not None]
        vols = [x[6] for x in group if x[6] is not None]
        tick_sum = sum(tcs) if tcs else None
        vol_sum = sum(vols) if vols else None
        close_time = start + timedelta(minutes=tf)
        if complete:
            src = "agg"
        elif is_last:
            src = "agg_forming"
        else:
            src = "agg_partial"
        result.append(
            _bar_dict(
                open_time=start,
                close_time=close_time,
                o=o,
                h=h,
                l=l,
                c=c,
                timeframe_min=tf,
                source=src,
                tick_count=tick_sum,
                volume=vol_sum,
            )
        )
    return result
