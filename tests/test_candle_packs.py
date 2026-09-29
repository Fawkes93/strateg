from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtest.candles import Candle, aggregate_tf, build_candles
from backtest.dukascopy import Tick


def _tick(ts, mid, spread=0.2):
    half = spread / 2.0
    return Tick(ts=ts, bid=mid - half, ask=mid + half)


def _candle(open_time, o, h, l, c, minutes=5, ticks=4):
    return Candle(
        open_time=open_time,
        close_time=open_time + timedelta(minutes=minutes),
        open=o,
        high=h,
        low=l,
        close=c,
        is_closed=True,
        tick_count=ticks,
    )


def test_build_candles_matches_candle_builder_buckets():
    """Gaps, a 7-minute grid, and the ignore window stay on the old builder rules."""
    from backtest.candles import CandleBuilder

    start = datetime(2025, 1, 6, 10, 56, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 100.0),
        _tick(start + timedelta(minutes=2), 110.0),  # still inside the :56 bar
        _tick(start + timedelta(minutes=7), 90.0),  # 11:03 closes it, opens :00
        _tick(start + timedelta(minutes=20), 120.0),  # gap, no empty bars
        _tick(start + timedelta(minutes=21), 80.0),
    ]

    def via_builder(tf, skip_ignored=False):
        builder = CandleBuilder(
            timeframe_minutes=tf, max_completed=10**9, skip_ignored=skip_ignored
        )
        closed = []
        for t in ticks:
            bar = builder.add_price(t.mid, t.ts)
            if bar is not None:
                closed.append(bar)
        return closed

    for tf in (5, 7, 15):
        got = build_candles(ticks, timeframe_minutes=tf, skip_ignored=False)
        exp = via_builder(tf, False)
        assert len(got) == len(exp)
        for g, e in zip(got, exp):
            assert g.open_time == e.open_time
            assert g.close_time == e.close_time
            assert g.open == e.open
            assert g.high == e.high
            assert g.low == e.low
            assert g.close == e.close
            assert g.tick_count == e.tick_count

    # 22:00 UTC in January is 00:00 Europe/Bucharest, inside the default ignore hour.
    quiet = datetime(2025, 1, 5, 22, 0, tzinfo=timezone.utc)
    night = [
        _tick(quiet, 100.0),
        _tick(quiet + timedelta(minutes=4), 101.0),
        _tick(quiet + timedelta(minutes=5), 102.0),
        _tick(quiet + timedelta(hours=2), 110.0),
        _tick(quiet + timedelta(hours=2, minutes=14), 111.0),
        _tick(quiet + timedelta(hours=2, minutes=15), 112.0),
    ]

    def closed_of(series, tf, skip_ignored):
        builder = CandleBuilder(
            timeframe_minutes=tf, max_completed=10**9, skip_ignored=skip_ignored
        )
        out = []
        for t in series:
            bar = builder.add_price(t.mid, t.ts)
            if bar is not None:
                out.append(bar)
        return out

    for skip in (False, True):
        got = build_candles(night, timeframe_minutes=15, skip_ignored=skip)
        exp = closed_of(night, 15, skip)
        assert [(c.open_time, c.close, c.tick_count) for c in got] == [
            (c.open_time, c.close, c.tick_count) for c in exp
        ]
    assert len(build_candles(night, timeframe_minutes=15, skip_ignored=True)) < len(
        build_candles(night, timeframe_minutes=15, skip_ignored=False)
    )


def test_fold_bi5_matches_decode_then_build():
    import lzma

    from backtest.dukascopy import TICK_STRUCT, decode_bi5, fold_bi5
    from backtest.candles import BarFold

    hour = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    scale = 1000.0
    rows = [
        (0, 3300.0, 3300.2),
        (50_000, 3304.0, 3304.2),
        (4 * 60_000 + 50_000, 3301.0, 3301.2),
        (5 * 60_000, 3305.0, 3305.2),
        (9 * 60_000, 3306.0, 3306.2),
        (10 * 60_000, 3307.0, 3307.2),  # opens a bar that must be dropped
        (1_000, 0.0, 1.0),  # non-positive bid, skipped
    ]
    raw = lzma.compress(
        b"".join(
            TICK_STRUCT.pack(ms, int(ask * scale), int(bid * scale), 1.0, 1.0)
            for ms, bid, ask in rows
        )
    )
    decoded = build_candles(decode_bi5(raw, hour, scale), timeframe_minutes=5)
    fold = BarFold(5)
    n = fold_bi5(raw, hour, scale, fold.add_ms)
    folded = fold.finish()
    assert n == len(decode_bi5(raw, hour, scale))
    assert len(folded) == len(decoded) == 2
    for g, e in zip(folded, decoded):
        assert g.open_time == e.open_time
        assert g.high == e.high
        assert g.low == e.low
        assert g.close == e.close
        assert g.tick_count == e.tick_count


def test_build_candles_5m_from_ticks_drops_in_progress():
    start = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    ticks = []
    # two full 5m bars + one tick of a third (must not persist)
    for i, mid in enumerate((3300.0, 3301.0, 3302.0, 3303.0)):
        ticks.append(_tick(start + timedelta(seconds=i), mid))
    ticks.append(_tick(start + timedelta(minutes=4, seconds=50), 3304.0))
    ticks.append(_tick(start + timedelta(minutes=5), 3305.0))
    ticks.append(_tick(start + timedelta(minutes=9, seconds=50), 3306.0))
    ticks.append(_tick(start + timedelta(minutes=10), 3307.0))  # opens third bar
    out = build_candles(ticks, timeframe_minutes=5, skip_ignored=False)
    assert len(out) == 2
    assert out[0].open == 3300.0
    assert out[0].high == 3304.0
    assert out[0].low == 3300.0
    assert out[0].close == 3304.0
    assert out[0].open_time == start
    assert out[1].open == 3305.0
    assert out[1].close == 3306.0


def test_aggregate_5m_to_15m_ohlc():
    t0 = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    fives = [
        _candle(t0, 3300.0, 3305.0, 3299.0, 3302.0),
        _candle(t0 + timedelta(minutes=5), 3302.0, 3310.0, 3301.0, 3308.0),
        _candle(t0 + timedelta(minutes=10), 3308.0, 3309.0, 3295.0, 3297.0),
    ]
    out = aggregate_tf(fives, 15)
    assert len(out) == 1
    bar = out[0]
    assert bar.open_time == t0
    assert bar.close_time == t0 + timedelta(minutes=15)
    assert bar.open == 3300.0
    assert bar.high == 3310.0
    assert bar.low == 3295.0
    assert bar.close == 3297.0
    assert bar.tick_count == 12


def test_candle_pack_roundtrip_and_atomic_replace(tmp_path: Path):
    from backtest.candle_packs import load_candle_pack, save_candle_pack

    t0 = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    candles = [_candle(t0, 3300.0, 3305.0, 3299.0, 3302.0)]
    path = tmp_path / "XAUUSD" / "2025-01.candlepack"
    last = t0 + timedelta(minutes=4, seconds=59)
    save_candle_pack(
        path,
        candles,
        symbol="XAUUSD",
        tf_min=5,
        last_source_tick_ts=last,
    )
    assert path.exists()
    assert not path.with_suffix(path.suffix + ".tmp").exists()
    meta, loaded = load_candle_pack(path)
    assert meta.tf_min == 5
    assert meta.symbol == "XAUUSD"
    assert meta.n == 1
    assert meta.last_source_tick_ts == last
    assert loaded[0].open == 3300.0
    assert loaded[0].high == 3305.0
    assert loaded[0].low == 3299.0
    assert loaded[0].close == 3302.0
    assert loaded[0].tick_count == 4


def test_ensure_month_reuses_fresh_pack_rebuilds_when_new_hours(tmp_path: Path):
    from backtest.candle_packs import ensure_month_candles, load_candle_pack

    start = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    ticks_a = [
        _tick(start, 3300.0),
        _tick(start + timedelta(minutes=4, seconds=50), 3301.0),
        _tick(start + timedelta(minutes=5), 3302.0),
        _tick(start + timedelta(minutes=9, seconds=50), 3303.0),
    ]
    calls = {"n": 0}

    def load_a(**kwargs):
        calls["n"] += 1
        return ticks_a

    first = ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=tmp_path,
        load_ticks_fn=load_a,
        last_tick_hour=datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc),
    )
    assert len(first) == 1
    assert calls["n"] == 1

    reused = ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=tmp_path,
        load_ticks_fn=load_a,
        last_tick_hour=datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc),
    )
    assert calls["n"] == 1
    assert [c.close for c in reused] == [c.close for c in first]

    ticks_b = ticks_a + [
        _tick(start + timedelta(hours=1), 3310.0),
        _tick(start + timedelta(hours=1, minutes=4, seconds=50), 3311.0),
    ]

    def load_b(**kwargs):
        calls["n"] += 1
        return ticks_b

    rebuilt = ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=tmp_path,
        load_ticks_fn=load_b,
        last_tick_hour=datetime(2025, 1, 6, 11, 0, tzinfo=timezone.utc),
    )
    assert calls["n"] == 2
    assert len(rebuilt) == 2
    _, loaded = load_candle_pack(tmp_path / "5m" / "XAUUSD" / "2025-01.candlepack")
    assert len(loaded) == 2


def test_ensure_month_force_rebuilds(tmp_path: Path):
    from backtest.candle_packs import ensure_month_candles

    start = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 3300.0),
        _tick(start + timedelta(minutes=4, seconds=50), 3301.0),
    ]
    calls = {"n": 0}

    def load_fn(**kwargs):
        calls["n"] += 1
        return ticks

    hour = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    ensure_month_candles(
        "XAUUSD", 2025, 1, tf_min=5, cache_root=tmp_path, load_ticks_fn=load_fn, last_tick_hour=hour
    )
    ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=tmp_path,
        load_ticks_fn=load_fn,
        last_tick_hour=hour,
        force=True,
    )
    assert calls["n"] == 2


def test_load_candles_range_concats_months(tmp_path: Path):
    from backtest.candle_packs import ensure_month_candles, load_candles_range

    def ticks_for(year, month):
        t0 = datetime(year, month, 2, 10, 0, tzinfo=timezone.utc)
        return [
            _tick(t0, 1000.0 + month),
            _tick(t0 + timedelta(minutes=4, seconds=50), 1001.0 + month),
            _tick(t0 + timedelta(minutes=5), 1001.0 + month),
        ]

    def load_fn(*, date_from, date_to, **kwargs):
        y, m, _ = date_from.split("-")
        return ticks_for(int(y), int(m))

    ensure_month_candles(
        "XAUUSD", 2025, 1, tf_min=5, cache_root=tmp_path, load_ticks_fn=load_fn
    )
    ensure_month_candles(
        "XAUUSD", 2025, 2, tf_min=5, cache_root=tmp_path, load_ticks_fn=load_fn
    )
    out = load_candles_range(
        "XAUUSD",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 3, 1, tzinfo=timezone.utc),
        tf_min=5,
        cache_root=tmp_path,
        tick_cache=tmp_path,
        load_ticks_fn=load_fn,
    )
    assert len(out) == 2
    assert out[0].open_time.month == 1
    assert out[1].open_time.month == 2


def _touch_bi5(tick_cache: Path, when: datetime, size: int) -> None:
    from backtest.dukascopy import _cache_path

    path = _cache_path(tick_cache, "XAUUSD", when)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_empty_trailing_bi5_hours_do_not_rebuild(tmp_path: Path):
    """Weekend / after-close 0-byte .bi5 files must not mark a month stale."""
    from backtest.candle_packs import ensure_month_candles

    start = datetime(2025, 1, 31, 21, 0, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 3300.0),
        _tick(start + timedelta(minutes=4, seconds=50), 3301.0),
        _tick(start + timedelta(minutes=5), 3301.0),
    ]
    calls = {"n": 0}

    def load_fn(**kwargs):
        calls["n"] += 1
        return ticks

    candles_root = tmp_path / "candles"
    tick_cache = tmp_path / "dukascopy"
    _touch_bi5(tick_cache, datetime(2025, 1, 31, 21, tzinfo=timezone.utc), 80)
    ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=candles_root,
        tick_cache=tick_cache,
        load_ticks_fn=load_fn,
    )
    assert calls["n"] == 1
    _touch_bi5(tick_cache, datetime(2025, 1, 31, 22, tzinfo=timezone.utc), 0)
    _touch_bi5(tick_cache, datetime(2025, 1, 31, 23, tzinfo=timezone.utc), 0)
    ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=candles_root,
        tick_cache=tick_cache,
        load_ticks_fn=load_fn,
    )
    assert calls["n"] == 1


def test_ensure_month_folds_tick_pack_without_materializing_ticks(tmp_path: Path):
    """A fresh .tickpack is streamed. No quote list is kept, and no download runs."""
    from backtest.candle_packs import ensure_month_candles
    from backtest.dukascopy import pack_path, save_tick_pack

    start = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 3300.0),
        _tick(start + timedelta(minutes=4, seconds=50), 3301.0),
        _tick(start + timedelta(minutes=5), 3302.0),
        _tick(start + timedelta(minutes=9, seconds=50), 3303.0),
    ]
    pack_dir = tmp_path / "packs"
    tick_cache = tmp_path / "dukascopy"
    save_tick_pack(
        pack_path(
            pack_dir,
            "XAUUSD",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 2, 1, tzinfo=timezone.utc),
        ),
        ticks,
    )
    out = ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=tmp_path / "candles",
        tick_cache=tick_cache,
        tick_pack_dir=pack_dir,
    )
    assert len(out) == 1
    assert out[0].open == 3300.0
    assert out[0].close == 3301.0
    assert out[0].tick_count == 2


def test_stale_tick_pack_loses_to_a_newer_bi5_hour(tmp_path: Path, monkeypatch):
    import lzma

    from backtest.candle_packs import ensure_month_candles
    from backtest.dukascopy import TICK_STRUCT, pack_path, save_tick_pack

    hour = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
    later = datetime(2025, 1, 6, 11, 0, tzinfo=timezone.utc)
    scale = 1000.0
    pack_dir = tmp_path / "packs"
    tick_cache = tmp_path / "dukascopy"
    save_tick_pack(
        pack_path(
            pack_dir,
            "XAUUSD",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 2, 1, tzinfo=timezone.utc),
        ),
        [
            _tick(hour, 1000.0),
            _tick(hour + timedelta(minutes=4), 1001.0),
        ],
    )

    def _bi5(when, bid):
        from backtest.dukascopy import _cache_path

        path = _cache_path(tick_cache, "XAUUSD", when)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Two quotes finish one 5m bar. The next hour's first quote closes it.
        blob = b"".join(
            TICK_STRUCT.pack(ms, int(bid * scale), int(bid * scale), 1.0, 1.0)
            for ms in (0, 4 * 60_000)
        )
        if when == later:
            blob = b"".join(
                TICK_STRUCT.pack(ms, int(bid * scale), int(bid * scale), 1.0, 1.0)
                for ms in (0, 4 * 60_000, 5 * 60_000, 9 * 60_000)
            )
        path.write_bytes(lzma.compress(blob))

    _bi5(hour, 3300.0)
    _bi5(later, 3400.0)
    monkeypatch.setattr(
        "backtest.candle_packs.hour_range",
        lambda start, end: [hour, later],
    )
    monkeypatch.setattr(
        "backtest.candle_packs.cache_hours",
        lambda *args, **kwargs: {"hours": 2, "cache": 2, "net": 0, "empty": 0},
    )
    out = ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=tmp_path / "candles",
        tick_cache=tick_cache,
        tick_pack_dir=pack_dir,
    )
    assert len(out) == 2
    assert out[0].open == 3300.0
    assert out[1].open == 3400.0


def test_nonempty_later_bi5_hour_does_rebuild(tmp_path: Path):
    from backtest.candle_packs import ensure_month_candles

    start = datetime(2025, 1, 31, 21, 0, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 3300.0),
        _tick(start + timedelta(minutes=4, seconds=50), 3301.0),
        _tick(start + timedelta(minutes=5), 3301.0),
    ]
    later = ticks + [
        _tick(datetime(2025, 1, 31, 22, 0, tzinfo=timezone.utc), 3302.0),
        _tick(datetime(2025, 1, 31, 22, 4, 50, tzinfo=timezone.utc), 3303.0),
        _tick(datetime(2025, 1, 31, 22, 5, tzinfo=timezone.utc), 3303.0),
    ]
    calls = {"n": 0}

    def load_fn(**kwargs):
        calls["n"] += 1
        return later if calls["n"] > 1 else ticks

    candles_root = tmp_path / "candles"
    tick_cache = tmp_path / "dukascopy"
    _touch_bi5(tick_cache, datetime(2025, 1, 31, 21, tzinfo=timezone.utc), 80)
    ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=candles_root,
        tick_cache=tick_cache,
        load_ticks_fn=load_fn,
    )
    _touch_bi5(tick_cache, datetime(2025, 1, 31, 22, tzinfo=timezone.utc), 80)
    out = ensure_month_candles(
        "XAUUSD",
        2025,
        1,
        tf_min=5,
        cache_root=candles_root,
        tick_cache=tick_cache,
        load_ticks_fn=load_fn,
    )
    assert calls["n"] == 2
    assert any(c.open_time.hour == 22 for c in out)


def test_short_range_downloads_only_those_hours(tmp_path: Path, monkeypatch):
    from backtest.candle_packs import ensure_month_candles, load_candles_range

    seen = []

    def fake_cache(symbol, hours, **kwargs):
        seen.append(list(hours))
        return {}

    monkeypatch.setattr("backtest.candle_packs.cache_hours", fake_cache)
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end = datetime(2026, 8, 4, tzinfo=timezone.utc)
    try:
        load_candles_range(
            "XAUUSD",
            start,
            end,
            tf_min=5,
            cache_root=tmp_path / "candles",
            tick_cache=tmp_path / "dukascopy",
        )
    except RuntimeError as exc:
        assert "No ticks" in str(exc)
    assert len(seen) == 1
    hours = seen[0]
    assert hours[0] == start
    assert hours[-1] == datetime(2026, 8, 3, 23, tzinfo=timezone.utc)
    assert len(hours) == 72
    assert not list((tmp_path / "candles").rglob("*.candlepack"))


def test_short_range_reuses_a_full_month_pack(tmp_path: Path, monkeypatch):
    from backtest.candle_packs import ensure_month_candles, load_candles_range

    start = datetime(2026, 8, 2, 10, tzinfo=timezone.utc)
    ticks = [
        _tick(start, 3300.0),
        _tick(start + timedelta(minutes=4, seconds=50), 3301.0),
        _tick(start + timedelta(minutes=5), 3302.0),
    ]
    ensure_month_candles(
        "XAUUSD",
        2026,
        8,
        tf_min=5,
        cache_root=tmp_path / "candles",
        ticks=ticks,
        last_tick_hour=start.replace(minute=0),
    )

    def fail_cache(*args, **kwargs):
        raise AssertionError("short range must not download when the month pack covers it")

    monkeypatch.setattr("backtest.candle_packs.cache_hours", fail_cache)
    out = load_candles_range(
        "XAUUSD",
        datetime(2026, 8, 2, tzinfo=timezone.utc),
        datetime(2026, 8, 3, tzinfo=timezone.utc),
        tf_min=5,
        cache_root=tmp_path / "candles",
        tick_cache=tmp_path / "dukascopy",
    )
    assert len(out) == 1
    assert out[0].open == 3300.0
