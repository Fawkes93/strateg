"""
Disk cache of OHLC candle months built from ticks.

Layout: data/candles/<tf>m/<SYMBOL>/YYYY-MM.candlepack
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from backtest.candles import Candle, build_candles, to_utc
from backtest.dukascopy import (
    Tick,
    _cache_path,
    hour_range,
    normalize_duka_symbol,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDLES = ROOT / "data" / "candles"
DEFAULT_TICK_CACHE = ROOT / "data" / "dukascopy"

CANDLE_PACK_VERSION = 1
# open_ts, close_ts, o, h, l, c, tick_count
_REC = struct.Struct("<ddddddI")


@dataclass
class CandlePackMeta:
    version: int
    tf_min: int
    symbol: str
    n: int
    last_source_tick_ts: Optional[datetime]


def month_pack_path(
    cache_root: Path,
    symbol: str,
    year: int,
    month: int,
    tf_min: int = 5,
) -> Path:
    sym = normalize_duka_symbol(symbol)
    return (
        Path(cache_root)
        / f"{int(tf_min)}m"
        / sym
        / f"{int(year):04d}-{int(month):02d}.candlepack"
    )


def _unix(ts: Optional[datetime]) -> float:
    if ts is None:
        return 0.0
    return to_utc(ts).timestamp()


def _from_unix(value: float) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def save_candle_pack(
    path: Path,
    candles: Sequence[Candle],
    *,
    symbol: str,
    tf_min: int,
    last_source_tick_ts: Optional[datetime] = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    sym = normalize_duka_symbol(symbol).encode("utf-8")
    with tmp.open("wb") as f:
        f.write(struct.pack("<I", CANDLE_PACK_VERSION))
        f.write(struct.pack("<I", int(tf_min)))
        f.write(struct.pack("<H", len(sym)))
        f.write(sym)
        f.write(struct.pack("<d", _unix(last_source_tick_ts)))
        f.write(struct.pack("<Q", len(candles)))
        for c in candles:
            f.write(
                _REC.pack(
                    _unix(c.open_time),
                    _unix(c.close_time),
                    float(c.open),
                    float(c.high),
                    float(c.low),
                    float(c.close),
                    int(c.tick_count or 0),
                )
            )
    tmp.replace(path)
    return path


def load_candle_pack(path: Path) -> Tuple[CandlePackMeta, List[Candle]]:
    path = Path(path)
    with path.open("rb") as f:
        ver = struct.unpack("<I", f.read(4))[0]
        if ver != CANDLE_PACK_VERSION:
            raise ValueError(f"unsupported candle pack version {ver}")
        tf_min = struct.unpack("<I", f.read(4))[0]
        slen = struct.unpack("<H", f.read(2))[0]
        symbol = f.read(slen).decode("utf-8")
        last_src = _from_unix(struct.unpack("<d", f.read(8))[0])
        n = struct.unpack("<Q", f.read(8))[0]
        candles: List[Candle] = []
        rec = _REC.size
        for _ in range(n):
            blob = f.read(rec)
            if len(blob) < rec:
                break
            o_ts, c_ts, o, h, l, c, ticks = _REC.unpack(blob)
            candles.append(
                Candle(
                    open_time=datetime.fromtimestamp(o_ts, tz=timezone.utc),
                    close_time=datetime.fromtimestamp(c_ts, tz=timezone.utc),
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    is_closed=True,
                    tick_count=int(ticks),
                )
            )
    meta = CandlePackMeta(
        version=ver,
        tf_min=int(tf_min),
        symbol=symbol,
        n=len(candles),
        last_source_tick_ts=last_src,
    )
    return meta, candles


def pack_is_fresh(
    meta: CandlePackMeta,
    *,
    last_tick_hour: Optional[datetime],
) -> bool:
    """True when the pack already includes the latest cached tick hour."""
    if last_tick_hour is None:
        return True
    if meta.last_source_tick_ts is None:
        return False
    return to_utc(meta.last_source_tick_ts) >= to_utc(last_tick_hour)


def last_cached_tick_hour(
    symbol: str,
    start: datetime,
    end: datetime,
    tick_cache: Path = DEFAULT_TICK_CACHE,
) -> Optional[datetime]:
    """Last hour in [start, end) whose .bi5 file is non-empty.

    Zero-byte files (weekend / after-close placeholders) are not new ticks.
    """
    last: Optional[datetime] = None
    symbol = normalize_duka_symbol(symbol)
    for hour in hour_range(start, end):
        path = _cache_path(tick_cache, symbol, hour)
        try:
            if path.stat().st_size > 0:
                last = hour
        except OSError:
            continue
    return last


def _month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    start = datetime(int(year), int(month), 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(int(year) + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(int(year), int(month) + 1, 1, tzinfo=timezone.utc)
    return start, end


def ensure_month_candles(
    symbol: str,
    year: int,
    month: int,
    *,
    tf_min: int = 5,
    cache_root: Optional[Path] = None,
    tick_cache: Optional[Path] = None,
    force: bool = False,
    ticks: Optional[Sequence[Tick]] = None,
    last_tick_hour: Optional[datetime] = None,
    load_ticks_fn: Optional[Callable[..., List[Tick]]] = None,
    progress: Optional[Callable[..., None]] = None,
) -> List[Candle]:
    """
    Return completed candles for a UTC calendar month, building the pack if needed.

    Rebuilds when missing, `force`, or a newer tick hour exists than `last_source_tick_ts`.
    If `last_tick_hour` is omitted, it is inferred from `.bi5` files in `tick_cache`.
    """
    cache_root = Path(cache_root or DEFAULT_CANDLES)
    tick_cache = Path(tick_cache or DEFAULT_TICK_CACHE)
    path = month_pack_path(cache_root, symbol, year, month, tf_min)
    start, end = _month_bounds(year, month)
    date_from = start.date().isoformat()
    date_to = end.date().isoformat()

    inferred_hour = last_tick_hour
    if inferred_hour is None and ticks is None:
        inferred_hour = last_cached_tick_hour(symbol, start, end, tick_cache)

    if not force and path.exists() and path.stat().st_size >= 16:
        try:
            meta, cached = load_candle_pack(path)
            if meta.tf_min == int(tf_min) and pack_is_fresh(
                meta, last_tick_hour=inferred_hour
            ):
                if progress:
                    progress(
                        phase="candles",
                        message=f"cached {int(tf_min)}m {year:04d}-{month:02d}",
                    )
                return cached
        except (ValueError, struct.error, OSError):
            pass

    if ticks is None:
        if load_ticks_fn is None:
            from backtest.runner import load_ticks as _load_ticks

            load_ticks_fn = _load_ticks
        if progress:
            progress(
                phase="candles",
                message=f"building {int(tf_min)}m {year:04d}-{month:02d}…",
            )
        ticks = load_ticks_fn(
            symbol=symbol,
            date_from=date_from,
            date_to=date_to,
            force_download=force,
            progress=progress,
        )
    ticks = list(ticks or [])
    candles = build_candles(ticks, timeframe_minutes=tf_min, skip_ignored=False)
    last_src = ticks[-1].ts if ticks else inferred_hour
    save_candle_pack(
        path,
        candles,
        symbol=symbol,
        tf_min=tf_min,
        last_source_tick_ts=last_src,
    )
    return candles


def load_candles_range(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    tf_min: int = 5,
    cache_root: Optional[Path] = None,
    tick_cache: Optional[Path] = None,
    force: bool = False,
    load_ticks_fn: Optional[Callable[..., List[Tick]]] = None,
    progress: Optional[Callable[..., None]] = None,
) -> List[Candle]:
    """Ensure and concat month packs overlapping [start, end)."""
    start = to_utc(start)
    end = to_utc(end)
    cache_root = Path(cache_root or DEFAULT_CANDLES)
    out: List[Candle] = []
    cur = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    while cur < end:
        month_end = (
            datetime(cur.year + 1, 1, 1, tzinfo=timezone.utc)
            if cur.month == 12
            else datetime(cur.year, cur.month + 1, 1, tzinfo=timezone.utc)
        )
        bars = ensure_month_candles(
            symbol,
            cur.year,
            cur.month,
            tf_min=tf_min,
            cache_root=cache_root,
            tick_cache=tick_cache,
            force=force,
            load_ticks_fn=load_ticks_fn,
            progress=progress,
        )
        for c in bars:
            ts = to_utc(c.open_time)
            if start <= ts < end:
                out.append(c)
        cur = month_end
    return out
