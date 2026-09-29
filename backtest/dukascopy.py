"""
Free Dukascopy historical tick download (public datafeed .bi5 files).

No account. Same feed used by dukascopy-node, duka, Tickstory, etc.

URL (month is **0-indexed** — January = 00):
  https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM}/{DD}/{HH}h_ticks.bi5

Record (20 bytes, big-endian after LZMA):
  ms_offset u32, ask u32, bid u32, ask_vol f32, bid_vol f32
"""

from __future__ import annotations

import lzma
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

# Parallel net downloads (Dukascopy public feed). Lower if you hit 429s.
DEFAULT_DOWNLOAD_WORKERS = 16
# A finished hour from this feed took 15–25s here. A 10s cap timed out every try.
HTTP_TIMEOUT_SEC = 60.0
HTTP_CONNECT_SEC = 30.0
# Pause between tries. The request itself uses HTTP_TIMEOUT_SEC.
HTTP_BACKOFF_SEC = 10.0
HTTP_RETRIES = 16
# Outer passes over the hours that still failed after HTTP_RETRIES.
HOUR_ATTEMPTS = 8

# Dukascopy symbol → (reaktor-style symbol, price_scale)
# price_scale is the integer divisor in the .bi5 feed.
# 5-digit FX (EURUSD and the other majors here) is 100000.
# USDJPY is 3 digits (1000), gold is 3 digits (1000), bitcoin is 10.
INSTRUMENTS: Dict[str, Tuple[str, float]] = {
    "XAUUSD": ("XAU/USD", 1000.0),
    "EURUSD": ("EUR/USD", 100000.0),
    "GBPUSD": ("GBP/USD", 100000.0),
    "USDJPY": ("USD/JPY", 1000.0),
    "AUDUSD": ("AUD/USD", 100000.0),
    "NZDUSD": ("NZD/USD", 100000.0),
    "USDCAD": ("USD/CAD", 100000.0),
    "USDCHF": ("USD/CHF", 100000.0),
    "BTCUSD": ("BTC/USD", 10.0),
}

DEFAULT_BASE = "https://datafeed.dukascopy.com/datafeed"
TICK_STRUCT = struct.Struct(">IIIff")
RECORD_SIZE = 20
# Compact assembled range cache (one file per symbol+from+to)
TICK_PACK_STRUCT = struct.Struct("<ddd")  # unix_ts, bid, ask
TICK_PACK_VERSION = 1

# Process-local packs so re-runs in the same UI server skip disk entirely
_MEM_PACKS: Dict[str, List["Tick"]] = {}


@dataclass(frozen=True)
class Tick:
    ts: datetime  # aware UTC
    bid: float
    ask: float
    bid_vol: float = 0.0
    ask_vol: float = 0.0

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) * 0.5

    @property
    def spread(self) -> float:
        return max(0.0, self.ask - self.bid)


def normalize_duka_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("_", "").replace("-", "")


def reaktor_symbol(duka_symbol: str) -> str:
    key = normalize_duka_symbol(duka_symbol)
    if key in INSTRUMENTS:
        return INSTRUMENTS[key][0]
    if key.startswith("XAU"):
        return "XAU/USD"
    if key.startswith("EUR") and key.endswith("USD"):
        return "EUR/USD"
    if key.endswith("JPY") and len(key) == 6:
        return f"{key[:3]}/{key[3:]}"
    if key.startswith("BTC"):
        return "BTC/USD"
    return duka_symbol


def price_scale(duka_symbol: str) -> float:
    key = normalize_duka_symbol(duka_symbol)
    if key in INSTRUMENTS:
        return INSTRUMENTS[key][1]
    # 3-digit quotes (USDJPY and metals). 5-digit FX is listed in INSTRUMENTS.
    if "JPY" in key:
        return 1000.0
    return 1000.0


def _hour_url(base: str, symbol: str, when: datetime) -> str:
    y, m, d, h = when.year, when.month - 1, when.day, when.hour
    return f"{base.rstrip('/')}/{symbol}/{y}/{m:02d}/{d:02d}/{h:02d}h_ticks.bi5"


def _cache_path(cache_dir: Path, symbol: str, when: datetime) -> Path:
    return (
        cache_dir
        / symbol
        / f"{when.year:04d}"
        / f"{when.month:02d}"
        / f"{when.day:02d}"
        / f"{when.hour:02d}h_ticks.bi5"
    )


def fold_bi5(
    raw: bytes,
    hour_start: datetime,
    scale: float,
    add_ms,
) -> int:
    """Feed one hour's .bi5 quotes to add_ms(unix_ms, mid). No Tick objects.

    Same filter as decode_bi5: non-positive bid or ask is skipped. Returns
    how many quotes were passed through.
    """
    if not raw or scale <= 0:
        return 0
    try:
        data = lzma.decompress(raw)
    except lzma.LZMAError:
        return 0
    if hour_start.tzinfo is None:
        hour_start = hour_start.replace(tzinfo=timezone.utc)
    else:
        hour_start = hour_start.astimezone(timezone.utc)
    base_ms = int(hour_start.timestamp()) * 1000
    n = 0
    usable = data[: (len(data) // RECORD_SIZE) * RECORD_SIZE]
    for ms, ask_i, bid_i, _ask_v, _bid_v in TICK_STRUCT.iter_unpack(usable):
        bid = bid_i / scale
        ask = ask_i / scale
        if bid <= 0 or ask <= 0:
            continue
        add_ms(base_ms + int(ms), (bid + ask) * 0.5)
        n += 1
    return n


def decode_bi5(raw: bytes, hour_start: datetime, scale: float) -> List[Tick]:
    if not raw:
        return []
    try:
        data = lzma.decompress(raw)
    except lzma.LZMAError:
        return []

    if hour_start.tzinfo is None:
        hour_start = hour_start.replace(tzinfo=timezone.utc)
    else:
        hour_start = hour_start.astimezone(timezone.utc)

    n = len(data) // RECORD_SIZE
    out: List[Tick] = []
    for i in range(n):
        ms, ask_i, bid_i, ask_v, bid_v = TICK_STRUCT.unpack_from(data, i * RECORD_SIZE)
        ask = ask_i / scale
        bid = bid_i / scale
        if bid <= 0 or ask <= 0:
            continue
        ts = hour_start + timedelta(milliseconds=ms)
        out.append(Tick(ts=ts, bid=bid, ask=ask, bid_vol=bid_v, ask_vol=ask_v))
    return out


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def _pause(seconds: float, note: Optional[Callable[[str], None]], message: str) -> None:
    """Sleep, ticking the status line so a long backoff does not look frozen."""
    if seconds <= 0:
        return
    if note is None:
        time.sleep(seconds)
        return
    left = float(seconds)
    while left > 0:
        note(message.format(left=max(1, int(round(left)))))
        step = min(5.0, left)
        time.sleep(step)
        left -= step


def _http_get(
    url: str,
    timeout: float = HTTP_TIMEOUT_SEC,
    *,
    client: Optional["httpx.Client"] = None,
    retries: int = HTTP_RETRIES,
    backoff: float = 2.0,
    note: Optional[Callable[[str], None]] = None,
) -> Tuple[int, bytes]:
    if httpx is None:
        raise RuntimeError("httpx is required: pip install httpx")
    last_err: Optional[Exception] = None
    owns = client is None
    if owns:
        client = httpx.Client(timeout=timeout, follow_redirects=True, headers=_HEADERS)
    assert client is not None
    try:
        for attempt in range(retries):
            try:
                r = client.get(url)
                # Retry rate limits / temporary failures
                if r.status_code in (429, 500, 502, 503, 504):
                    wait = min(backoff * (2**attempt), HTTP_BACKOFF_SEC)
                    _pause(
                        wait,
                        note,
                        f"HTTP {r.status_code} · try {attempt + 1}/{retries} · {{left}}s",
                    )
                    continue
                return r.status_code, r.content
            except Exception as e:
                last_err = e
                wait = min(backoff * (2**attempt), HTTP_BACKOFF_SEC)
                _pause(
                    wait,
                    note,
                    f"{type(e).__name__} · try {attempt + 1}/{retries} · {{left}}s",
                )
    finally:
        if owns:
            client.close()
    raise RuntimeError(f"Dukascopy GET failed after {retries} tries: {url} ({last_err})")


def fetch_hour(
    symbol: str,
    when: datetime,
    *,
    cache_dir: Path,
    base_url: str = DEFAULT_BASE,
    force: bool = False,
    sleep_sec: float = 0.0,
    client: Optional["httpx.Client"] = None,
    note: Optional[Callable[[str], None]] = None,
) -> List[Tick]:
    """
    Load one hour of ticks. Disk cache hit is free; net fetch has no default
    throttle (use fetch_hours_parallel for concurrent downloads).
    """
    symbol = normalize_duka_symbol(symbol)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    else:
        when = when.astimezone(timezone.utc)
    hour = when.replace(minute=0, second=0, microsecond=0)

    path = _cache_path(cache_dir, symbol, hour)
    scale = price_scale(symbol)

    if path.exists() and not force:
        raw = path.read_bytes()
        if len(raw) == 0:
            return []
        return decode_bi5(raw, hour, scale)

    path.parent.mkdir(parents=True, exist_ok=True)
    url = _hour_url(base_url, symbol, hour)
    status, content = _http_get(url, client=client, note=note)
    if sleep_sec > 0:
        time.sleep(sleep_sec)

    if status == 404 or not content:
        path.write_bytes(b"")
        return []
    if status != 200:
        raise RuntimeError(f"Dukascopy HTTP {status} for {url}")

    ticks = decode_bi5(content, hour, scale)
    path.write_bytes(content)
    return ticks


def cache_hour(
    symbol: str,
    when: datetime,
    *,
    cache_dir: Path,
    base_url: str = DEFAULT_BASE,
    force: bool = False,
    client: Optional["httpx.Client"] = None,
    note: Optional[Callable[[str], None]] = None,
) -> str:
    """
    Ensure one hour's .bi5 is on disk. Does **not** decode ticks (safe for
    multi-month downloads). Returns 'cache' | 'net' | 'empty'.
    """
    symbol = normalize_duka_symbol(symbol)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    else:
        when = when.astimezone(timezone.utc)
    hour = when.replace(minute=0, second=0, microsecond=0)
    path = _cache_path(cache_dir, symbol, hour)

    if path.exists() and not force:
        return "cache"

    path.parent.mkdir(parents=True, exist_ok=True)
    url = _hour_url(base_url, symbol, hour)
    status, content = _http_get(url, client=client, note=note)

    if status == 404 or not content:
        path.write_bytes(b"")
        return "empty"
    if status != 200:
        raise RuntimeError(f"Dukascopy HTTP {status} for {url}")

    path.write_bytes(content)
    return "net"


def fetch_hours_parallel(
    symbol: str,
    hours: List[datetime],
    *,
    cache_dir: Path,
    base_url: str = DEFAULT_BASE,
    force: bool = False,
    max_workers: int = DEFAULT_DOWNLOAD_WORKERS,
    progress: Optional[Callable[..., None]] = None,
) -> List[Tick]:
    """
    Fetch many hours with thread pool. Cached hours read from disk in the
    workers too (fast). Returns ticks sorted by time (all hours concatenated).
    """
    if not hours:
        return []
    symbol = normalize_duka_symbol(symbol)
    n = len(hours)
    workers = max(1, min(int(max_workers), n, 32))

    # Split cache hits vs net so progress is honest and we don't open client for all-cache
    need_net: List[datetime] = []
    cached_hours: List[datetime] = []
    for h in hours:
        if not force and bi5_hour_is_cached(cache_dir, symbol, h):
            cached_hours.append(h)
        else:
            need_net.append(h)

    results: Dict[datetime, List[Tick]] = {}
    lock = threading.Lock()
    done = 0
    n_net = 0
    n_cache = 0
    tick_total = 0

    def _bump(from_cache: bool, hour: datetime, ticks: List[Tick]) -> None:
        nonlocal done, n_net, n_cache, tick_total
        with lock:
            results[hour] = ticks
            done += 1
            tick_total += len(ticks)
            if from_cache:
                n_cache += 1
            else:
                n_net += 1
            d, nc, nn, tt = done, n_cache, n_net, tick_total
        if progress:
            progress(
                hours_done=d,
                hours_total=n,
                ticks=tt,
                from_cache=nc,
                from_net=nn,
                pct=round(100.0 * d / max(n, 1), 1),
                message=(
                    f"Hour {d}/{n} · cache {nc} · net {nn} · {tt:,} ticks"
                ),
            )

    def _note(h: datetime, msg: str) -> None:
        if not progress:
            return
        with lock:
            d = done
        progress(
            hours_done=d,
            hours_total=n,
            pct=round(100.0 * d / max(n, 1), 1),
            message=f"Hour {d}/{n} · {h.strftime('%Y-%m-%d %H')}:00 · {msg}",
        )

    def _load_one(h: datetime, client: Optional["httpx.Client"], from_cache: bool) -> None:
        ticks = fetch_hour(
            symbol,
            h,
            cache_dir=cache_dir,
            base_url=base_url,
            force=force and not from_cache,
            sleep_sec=0.0,
            client=client,
            note=None if from_cache else (lambda msg, h=h: _note(h, msg)),
        )
        _bump(from_cache, h, ticks)

    # Disk cache: parallel file reads (no HTTP)
    if cached_hours:
        cw = max(1, min(8, len(cached_hours)))
        with ThreadPoolExecutor(max_workers=cw) as pool:
            futs = [pool.submit(_load_one, h, None, True) for h in cached_hours]
            for f in as_completed(futs):
                f.result()

    # Network: shared client + many threads. Failed hours retried with fewer workers.
    pending = list(need_net)
    attempt = 0
    while pending:
        attempt += 1
        w = workers if attempt == 1 else max(2, workers // 2)
        if progress:
            with lock:
                d, nc, nn, tt = done, n_cache, n_net, tick_total
            progress(
                hours_done=d,
                hours_total=n,
                ticks=tt,
                from_cache=nc,
                from_net=nn,
                pct=round(100.0 * d / max(n, 1), 1),
                message=(
                    f"Hour {d}/{n} · cache {nc} · net {nn} · {tt:,} ticks"
                    + (
                        f" · retry {attempt} · {len(pending)} left · {w} workers"
                        if attempt > 1
                        else f" · fetching {len(pending)}"
                    )
                ),
            )
        if httpx is None:
            raise RuntimeError("httpx is required: pip install httpx")
        limits = httpx.Limits(
            max_connections=w + 4,
            max_keepalive_connections=w,
        )
        failed: List[Tuple[datetime, str]] = []
        with httpx.Client(
            timeout=httpx.Timeout(HTTP_TIMEOUT_SEC, connect=HTTP_CONNECT_SEC),
            follow_redirects=True,
            headers=_HEADERS,
            limits=limits,
        ) as client:
            with ThreadPoolExecutor(max_workers=w) as pool:
                fut_map = {
                    pool.submit(_load_one, h, client, False): h for h in pending
                }
                for f in as_completed(fut_map):
                    h = fut_map[f]
                    try:
                        f.result()
                    except Exception as e:
                        failed.append((h, str(e)))
        if not failed:
            break
        if attempt >= HOUR_ATTEMPTS:
            sample = "; ".join(f"{h.isoformat()}: {err[:80]}" for h, err in failed[:3])
            raise RuntimeError(
                f"Dukascopy still failing {len(failed)} hour(s) after {attempt} attempts. "
                f"Examples: {sample}"
            )
        # brief pause then retry only missing hours
        next_w = max(2, workers // 2)
        pending = [h for h, _ in failed]
        if progress:
            with lock:
                d = done
            progress(
                hours_done=d,
                hours_total=n,
                pct=round(100.0 * d / max(n, 1), 1),
                message=(
                    f"Hour {d}/{n} · retry {attempt}: "
                    f"{len(pending)} {'hour' if len(pending) == 1 else 'hours'} failed"
                    f" · next pass {next_w} workers"
                ),
            )
        time.sleep(min(2.0 * attempt, 8.0))

    # Preserve chronological hour order
    all_ticks: List[Tick] = []
    for h in hours:
        all_ticks.extend(results.get(h) or [])
    return all_ticks


def cache_hours(
    symbol: str,
    hours: List[datetime],
    *,
    cache_dir: Path,
    base_url: str = DEFAULT_BASE,
    force: bool = False,
    max_workers: int = DEFAULT_DOWNLOAD_WORKERS,
    progress: Optional[Callable[..., None]] = None,
) -> Dict[str, int]:
    """
    Download missing .bi5 hours to disk without decoding ticks.

    Returns counts: hours, cache, net, empty.
    """
    counts = {"hours": 0, "cache": 0, "net": 0, "empty": 0}
    if not hours:
        return counts

    symbol = normalize_duka_symbol(symbol)
    n = len(hours)
    workers = max(1, min(int(max_workers), n, 32))
    counts["hours"] = n

    need_net: List[datetime] = []
    n_cache = 0
    for h in hours:
        if not force and bi5_hour_is_cached(cache_dir, symbol, h):
            n_cache += 1
        else:
            need_net.append(h)
    counts["cache"] = n_cache

    if progress:
        progress(
            hours_done=n_cache,
            hours_total=n,
            from_cache=n_cache,
            from_net=0,
            message=f"Hour {n_cache}/{n} · cache {n_cache} · net 0 (scan done)",
        )

    lock = threading.Lock()
    n_net = 0
    n_empty = 0
    done = n_cache

    def _bump(kind: str) -> None:
        nonlocal done, n_net, n_empty
        with lock:
            done += 1
            if kind == "net":
                n_net += 1
            elif kind == "empty":
                n_empty += 1
            d, nn, ne = done, n_net, n_empty
        if progress:
            progress(
                hours_done=d,
                hours_total=n,
                from_cache=n_cache,
                from_net=nn,
                pct=round(100.0 * d / max(n, 1), 1),
                message=f"Hour {d}/{n} · cache {n_cache} · net {nn} · empty {ne}",
            )

    def _note(h: datetime, msg: str) -> None:
        if not progress:
            return
        with lock:
            d = done
        progress(
            hours_done=d,
            hours_total=n,
            from_cache=n_cache,
            pct=round(100.0 * d / max(n, 1), 1),
            message=f"Hour {d}/{n} · {h.strftime('%Y-%m-%d %H')}:00 · {msg}",
        )

    def _one(h: datetime, client: "httpx.Client") -> None:
        kind = cache_hour(
            symbol,
            h,
            cache_dir=cache_dir,
            base_url=base_url,
            force=force,
            client=client,
            note=lambda msg, h=h: _note(h, msg),
        )
        _bump(kind if kind in ("net", "empty") else "net")

    pending = list(need_net)
    attempt = 0
    while pending:
        attempt += 1
        w = workers if attempt == 1 else max(2, workers // 2)
        if progress:
            with lock:
                d, nn, ne = done, n_net, n_empty
            progress(
                hours_done=d,
                hours_total=n,
                from_cache=n_cache,
                from_net=nn,
                pct=round(100.0 * d / max(n, 1), 1),
                message=(
                    f"Hour {d}/{n} · cache {n_cache} · net {nn} · empty {ne}"
                    + (
                        f" · retry {attempt} · {len(pending)} left · {w} workers"
                        if attempt > 1
                        else f" · fetching {len(pending)}"
                    )
                ),
            )
        if httpx is None:
            raise RuntimeError("httpx is required: pip install httpx")
        limits = httpx.Limits(
            max_connections=w + 4,
            max_keepalive_connections=w,
        )
        failed: List[Tuple[datetime, str]] = []
        with httpx.Client(
            timeout=httpx.Timeout(HTTP_TIMEOUT_SEC, connect=HTTP_CONNECT_SEC),
            follow_redirects=True,
            headers=_HEADERS,
            limits=limits,
        ) as client:
            with ThreadPoolExecutor(max_workers=w) as pool:
                fut_map = {pool.submit(_one, h, client): h for h in pending}
                for f in as_completed(fut_map):
                    h = fut_map[f]
                    try:
                        f.result()
                    except Exception as e:
                        failed.append((h, str(e)))
        if not failed:
            break
        if attempt >= HOUR_ATTEMPTS:
            sample = "; ".join(f"{h.isoformat()}: {err[:80]}" for h, err in failed[:3])
            raise RuntimeError(
                f"Dukascopy still failing {len(failed)} hour(s) after {attempt} attempts. "
                f"Examples: {sample}"
            )
        next_w = max(2, workers // 2)
        pending = [h for h, _ in failed]
        if progress:
            with lock:
                d = done
            progress(
                hours_done=d,
                hours_total=n,
                pct=round(100.0 * d / max(n, 1), 1),
                message=(
                    f"Hour {d}/{n} · retry {attempt}: "
                    f"{len(pending)} {'hour' if len(pending) == 1 else 'hours'} failed"
                    f" · next pass {next_w} workers"
                ),
            )
        time.sleep(min(2.0 * attempt, 8.0))

    counts["net"] = n_net
    counts["empty"] = n_empty
    return counts


def hour_range(start: datetime, end: datetime) -> List[datetime]:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)
    if end <= start:
        return []

    cur = start.replace(minute=0, second=0, microsecond=0)
    last = (end - timedelta(microseconds=1)).replace(minute=0, second=0, microsecond=0)
    out: List[datetime] = []
    while cur <= last:
        out.append(cur)
        cur += timedelta(hours=1)
    return out


def download_range(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    cache_dir: Path,
    base_url: str = DEFAULT_BASE,
    force: bool = False,
    progress: bool = True,
    max_workers: int = DEFAULT_DOWNLOAD_WORKERS,
) -> List[Tick]:
    hours = hour_range(start, end)

    def _prog(**kwargs) -> None:
        if progress and kwargs.get("hours_done"):
            d = kwargs["hours_done"]
            n = kwargs.get("hours_total") or len(hours)
            if d % 24 == 0 or d == n:
                print(
                    f"  duka {normalize_duka_symbol(symbol)}: "
                    f"{kwargs.get('message') or f'hour {d}/{n}'}",
                    flush=True,
                )

    all_ticks = fetch_hours_parallel(
        symbol,
        hours,
        cache_dir=cache_dir,
        base_url=base_url,
        force=force,
        max_workers=max_workers,
        progress=_prog if progress else None,
    )

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)

    filtered = [t for t in all_ticks if start <= t.ts < end]
    filtered.sort(key=lambda t: t.ts)
    return filtered


def month_windows(start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
    """Split [start, end) into calendar-month windows (UTC)."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)
    if end <= start:
        return []

    cur = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    out: List[Tuple[datetime, datetime]] = []
    while cur < end:
        if cur.month == 12:
            nxt = datetime(cur.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            nxt = datetime(cur.year, cur.month + 1, 1, tzinfo=timezone.utc)
        a, b = max(cur, start), min(nxt, end)
        if a < b:
            out.append((a, b))
        cur = nxt
    return out


def cache_range(
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    cache_dir: Path,
    base_url: str = DEFAULT_BASE,
    force: bool = False,
    progress: Optional[Callable[..., None]] = None,
    max_workers: int = DEFAULT_DOWNLOAD_WORKERS,
) -> Dict[str, int]:
    """Download [start, end) hours to the bi5 cache without assembling ticks."""
    hours = hour_range(start, end)
    return cache_hours(
        symbol,
        hours,
        cache_dir=cache_dir,
        base_url=base_url,
        force=force,
        max_workers=max_workers,
        progress=progress,
    )


def parse_ymd(s: str) -> datetime:
    s = s.strip()
    if "T" in s:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    else:
        d = date.fromisoformat(s)
        dt = datetime(d.year, d.month, d.day)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def pack_key(symbol: str, start: datetime, end: datetime) -> str:
    symbol = normalize_duka_symbol(symbol)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)
    return (
        f"{symbol}_"
        f"{start.strftime('%Y%m%dT%H%M')}_"
        f"{end.strftime('%Y%m%dT%H%M')}"
    )


def pack_path(pack_dir: Path, symbol: str, start: datetime, end: datetime) -> Path:
    return pack_dir / f"{pack_key(symbol, start, end)}.tickpack"


def save_tick_pack(path: Path, ticks: List[Tick]) -> None:
    """Write assembled ticks as a single binary file (fast reload)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        f.write(struct.pack("<I", TICK_PACK_VERSION))
        f.write(struct.pack("<Q", len(ticks)))
        for t in ticks:
            f.write(
                TICK_PACK_STRUCT.pack(
                    t.ts.timestamp(),
                    float(t.bid),
                    float(t.ask),
                )
            )
    tmp.replace(path)


def tick_pack_last_ts(path: Path) -> Optional[datetime]:
    """Timestamp of the last record, or None if the file is empty or unreadable."""
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError:
        return None
    rec = TICK_PACK_STRUCT.size
    if size < 12 + rec:
        return None
    with path.open("rb") as f:
        ver = struct.unpack("<I", f.read(4))[0]
        if ver != TICK_PACK_VERSION:
            return None
        n = struct.unpack("<Q", f.read(8))[0]
        if n <= 0:
            return None
        f.seek(12 + (int(n) - 1) * rec)
        blob = f.read(rec)
    if len(blob) < rec:
        return None
    ts, _bid, _ask = TICK_PACK_STRUCT.unpack(blob)
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


def fold_tick_pack(path: Path, add_ms, *, progress: Optional[Callable[..., None]] = None) -> int:
    """Stream a .tickpack into add_ms(unix_ms, mid). Does not build Tick objects."""
    path = Path(path)
    with path.open("rb") as f:
        ver = struct.unpack("<I", f.read(4))[0]
        if ver != TICK_PACK_VERSION:
            raise ValueError(f"unsupported tick pack version {ver}")
        n = struct.unpack("<Q", f.read(8))[0]
        rec = TICK_PACK_STRUCT.size
        unpack = TICK_PACK_STRUCT.unpack
        read = f.read
        count = 0
        for i in range(int(n)):
            blob = read(rec)
            if len(blob) < rec:
                break
            ts, bid, ask = unpack(blob)
            if bid <= 0 or ask <= 0:
                continue
            ms = int(float(ts) * 1000.0 + 0.5)
            add_ms(ms, (float(bid) + float(ask)) * 0.5)
            count += 1
            if count % 200_000 == 0:
                time.sleep(0.002)  # release GIL so the UI can poll
                if progress:
                    progress(
                        phase="candles",
                        message=f"Fold pack {count:,}/{int(n):,}",
                        ticks=count,
                    )
        return count


def load_tick_pack(
    path: Path,
    progress: Optional[Callable[..., None]] = None,
) -> List[Tick]:
    """Load ticks written by save_tick_pack."""
    with path.open("rb") as f:
        ver = struct.unpack("<I", f.read(4))[0]
        if ver != TICK_PACK_VERSION:
            raise ValueError(f"unsupported tick pack version {ver}")
        n = struct.unpack("<Q", f.read(8))[0]
        out: List[Tick] = []
        out_append = out.append
        fromtimestamp = datetime.fromtimestamp
        utc = timezone.utc
        unpack = TICK_PACK_STRUCT.unpack
        read = f.read
        rec = TICK_PACK_STRUCT.size
        yield_every = 200_000
        for i in range(n):
            blob = read(rec)
            if len(blob) < rec:
                break
            ts, bid, ask = unpack(blob)
            out_append(
                Tick(
                    ts=fromtimestamp(ts, tz=utc),
                    bid=bid,
                    ask=ask,
                )
            )
            if (i + 1) % yield_every == 0:
                time.sleep(0.002)  # release GIL so the UI can poll
                if progress:
                    progress(
                        phase="download",
                        message=f"Unpack pack {i + 1:,}/{n:,}",
                        ticks=i + 1,
                        pct=round(5.0 + 40.0 * ((i + 1) / max(n, 1)), 1),
                    )
        return out


def get_cached_pack(
    symbol: str,
    start: datetime,
    end: datetime,
    pack_dir: Path,
    progress: Optional[Callable[..., None]] = None,
) -> Optional[List[Tick]]:
    """Memory first, then disk pack. None if missing."""
    key = pack_key(symbol, start, end)
    if key in _MEM_PACKS:
        return _MEM_PACKS[key]
    path = pack_path(pack_dir, symbol, start, end)
    if not path.exists() or path.stat().st_size < 16:
        return None
    ticks = load_tick_pack(path, progress=progress)
    _MEM_PACKS[key] = ticks
    return ticks


def drop_cached_pack(
    symbol: str,
    start: datetime,
    end: datetime,
) -> None:
    """Free a month pack from RAM after we finish scanning it."""
    _MEM_PACKS.pop(pack_key(symbol, start, end), None)


def clear_mem_packs() -> None:
    """Drop every in-process tick pack (call when a job finishes)."""
    _MEM_PACKS.clear()


def store_cached_pack(
    symbol: str,
    start: datetime,
    end: datetime,
    pack_dir: Path,
    ticks: List[Tick],
) -> Path:
    key = pack_key(symbol, start, end)
    _MEM_PACKS[key] = ticks
    path = pack_path(pack_dir, symbol, start, end)
    save_tick_pack(path, ticks)
    return path


def bi5_hour_is_cached(cache_dir: Path, symbol: str, when: datetime) -> bool:
    path = _cache_path(cache_dir, normalize_duka_symbol(symbol), when)
    return path.exists()
