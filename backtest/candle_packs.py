"""
Disk cache of OHLC candle months built from ticks.

Layout: data/candles/<tf>m/<SYMBOL>/YYYY-MM.candlepack

A month is folded straight from the .tickpack or the .bi5 hours. The quote
list is never materialized, and it is not pinned in the process tick cache.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from backtest.candles import BarFold, Candle, _from_ms, build_candles, to_utc
from backtest.dukascopy import (
    Tick,
    _cache_path,
    cache_hours,
    fold_bi5,
    fold_tick_pack,
    hour_range,
    normalize_duka_symbol,
    pack_path,
    price_scale,
    tick_pack_last_ts,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDLES = ROOT / "data" / "candles"
DEFAULT_TICK_CACHE = ROOT / "data" / "dukascopy"
# Same directory as backtest.runner.DEFAULT_PACKS. Not imported from runner
# so a candle build does not pull the research stack into the process.
DEFAULT_TICK_PACKS = ROOT / "data" / "tick_packs"

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


def _paced_add(fold: BarFold, progress: Optional[Callable[..., None]], label: str):
    """add_ms wrapper that lets the UI poll during a long fold."""
    n = 0

    def add_ms(ms: int, mid: float) -> None:
        nonlocal n
        fold.add_ms(ms, mid)
        n += 1
        if n % 200_000 == 0:
            time.sleep(0.002)
            if progress:
                progress(
                    phase="candles",
                    message=f"{label} · {n:,} quotes",
                    ticks=n,
                )

    return add_ms


def _fold_month_from_disk(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    tf_min: int,
    tick_cache: Path,
    tick_pack_dir: Path,
    force: bool,
    inferred_hour: Optional[datetime],
    progress: Optional[Callable[..., None]],
    label: str,
) -> Tuple[List[Candle], Optional[datetime]]:
    """Build the month from a fresh tick pack, otherwise from .bi5 hours."""
    fold = BarFold(tf_min, skip_ignored=False)
    sym = normalize_duka_symbol(symbol)
    if not force:
        packed = pack_path(tick_pack_dir, sym, start, end)
        if packed.exists():
            last = tick_pack_last_ts(packed)
            fresh = last is not None and (
                inferred_hour is None or to_utc(last) >= to_utc(inferred_hour)
            )
            if fresh:
                if progress:
                    progress(phase="candles", message=f"{label} from tick pack…")
                n = fold_tick_pack(packed, fold.add_ms, progress=progress)
                if n <= 0:
                    raise RuntimeError(
                        f"No ticks for {start.date().isoformat()}→{end.date().isoformat()}"
                    )
                last_src = _from_ms(fold.last_ms) if fold.last_ms is not None else last
                return fold.finish(), last_src

    hours = hour_range(start, end)
    if progress:
        progress(phase="candles", message=f"{label} from hours…")
    cache_hours(
        sym,
        hours,
        cache_dir=tick_cache,
        force=force,
        progress=progress,
    )
    add_ms = _paced_add(fold, progress, label)
    scale = price_scale(sym)
    n = 0
    for hour in hours:
        path = _cache_path(tick_cache, sym, hour)
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        n += fold_bi5(raw, hour, scale, add_ms)
    if n <= 0:
        raise RuntimeError(
            f"No ticks for {start.date().isoformat()}→{end.date().isoformat()}"
        )
    last_src = _from_ms(fold.last_ms) if fold.last_ms is not None else inferred_hour
    return fold.finish(), last_src


def _window_inside_month(
    month_start: datetime,
    month_end: datetime,
    range_start: Optional[datetime],
    range_end: Optional[datetime],
) -> Tuple[datetime, datetime, bool]:
    """Hours to fetch. A request shorter than the month does not widen to it."""
    win_start = month_start if range_start is None else max(month_start, to_utc(range_start))
    win_end = month_end if range_end is None else min(month_end, to_utc(range_end))
    if win_end < win_start:
        win_end = win_start
    partial = win_start > month_start or win_end < month_end
    return win_start, win_end, partial


def _pack_serves_window(
    meta: CandlePackMeta,
    candles: Sequence[Candle],
    win_start: datetime,
    win_end: datetime,
) -> bool:
    """True when a saved month pack already holds this shorter window.

    A pack built from the whole month qualifies. A pack that never reached
    the window does not, so a 3-day run cannot skip the download.
    """
    last_src = meta.last_source_tick_ts
    if last_src is None:
        return False
    last_src = to_utc(last_src)
    if last_src < win_start:
        return False
    if last_src >= win_end - timedelta(seconds=1):
        return True
    return any(win_start <= to_utc(c.open_time) < win_end for c in candles)


def ensure_month_candles(
    symbol: str,
    year: int,
    month: int,
    *,
    tf_min: int = 5,
    cache_root: Optional[Path] = None,
    tick_cache: Optional[Path] = None,
    tick_pack_dir: Optional[Path] = None,
    force: bool = False,
    ticks: Optional[Sequence[Tick]] = None,
    last_tick_hour: Optional[datetime] = None,
    load_ticks_fn: Optional[Callable[..., List[Tick]]] = None,
    progress: Optional[Callable[..., None]] = None,
    range_start: Optional[datetime] = None,
    range_end: Optional[datetime] = None,
) -> List[Candle]:
    """
    Return completed candles for a UTC calendar month, building the pack if needed.

    Rebuilds when missing, `force`, or a newer tick hour exists than `last_source_tick_ts`.
    If `last_tick_hour` is omitted, it is inferred from `.bi5` files in `tick_cache`.
    `range_start`/`range_end` limit the download to that slice of the month. A partial
    slice is not written back as the month pack.
    """
    cache_root = Path(cache_root or DEFAULT_CANDLES)
    tick_cache = Path(tick_cache or DEFAULT_TICK_CACHE)
    path = month_pack_path(cache_root, symbol, year, month, tf_min)
    start, end = _month_bounds(year, month)
    win_start, win_end, partial = _window_inside_month(start, end, range_start, range_end)
    date_from = start.date().isoformat()
    date_to = end.date().isoformat()

    inferred_hour = last_tick_hour
    if inferred_hour is None and ticks is None:
        inferred_hour = last_cached_tick_hour(
            symbol,
            win_start if partial else start,
            win_end if partial else end,
            tick_cache,
        )

    if not force and path.exists() and path.stat().st_size >= 16:
        try:
            meta, cached = load_candle_pack(path)
            fresh = meta.tf_min == int(tf_min) and pack_is_fresh(
                meta, last_tick_hour=inferred_hour
            )
            serves = (not partial) or _pack_serves_window(meta, cached, win_start, win_end)
            if fresh and serves:
                if progress:
                    progress(
                        phase="candles",
                        message=f"cached {int(tf_min)}m {year:04d}-{month:02d}",
                    )
                return cached
        except (ValueError, struct.error, OSError):
            pass

    label = (
        f"building {int(tf_min)}m {win_start.date().isoformat()}→{win_end.date().isoformat()}"
        if partial
        else f"building {int(tf_min)}m {year:04d}-{month:02d}"
    )
    if ticks is None and load_ticks_fn is None:
        if progress:
            progress(phase="candles", message=f"{label}…")
        candles, last_src = _fold_month_from_disk(
            symbol,
            win_start,
            win_end,
            tf_min=int(tf_min),
            tick_cache=tick_cache,
            tick_pack_dir=Path(tick_pack_dir or DEFAULT_TICK_PACKS),
            force=force,
            inferred_hour=inferred_hour,
            progress=progress,
            label=label,
        )
        if partial:
            return candles
    else:
        if ticks is None:
            if progress:
                progress(phase="candles", message=f"{label}…")
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
            range_start=start,
            range_end=end,
        )
        for c in bars:
            ts = to_utc(c.open_time)
            if start <= ts < end:
                out.append(c)
        cur = month_end
    return out
