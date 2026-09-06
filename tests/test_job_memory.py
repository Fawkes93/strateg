"""RAM release helpers for long-lived webapp job state."""

from __future__ import annotations

from backtest.dukascopy import _MEM_PACKS, clear_mem_packs
from backtest.job_memory import (
    DEFAULT_UI_ROW_LIMIT,
    release_job_memory,
    retain_result,
    slim_retained_result,
    slim_state_result_inplace,
)
from datetime import datetime, timezone


def test_slim_truncates_rows_and_skips_keeps_metrics():
    rows = [{"i": i} for i in range(1000)]
    skips = [{"j": j} for j in range(500)]
    raw = {
        "kind": "cooloff",
        "trades": 1000,
        "ticks": 12_345_678,
        "by_threshold": {"100": {"hit_rate": 0.5}},
        "rows": rows,
        "skips": skips,
    }
    slim = slim_retained_result(raw, row_limit=50)
    assert slim is not None
    assert slim["trades"] == 1000
    assert slim["ticks"] == 12_345_678
    assert slim["by_threshold"] == {"100": {"hit_rate": 0.5}}
    assert slim["row_count"] == 1000
    assert slim["skips_count"] == 500
    assert len(slim["rows"]) == 50
    assert len(slim["skips"]) == 50
    assert slim["rows_truncated"] is True
    assert slim["skips_truncated"] is True
    # Original untouched for disk write scenarios
    assert len(raw["rows"]) == 1000


def test_slim_drops_research_detail():
    detail = {"100": [{"a": 1}] * 200, "200": [{"b": 2}] * 100}
    raw = {
        "kind": "research",
        "alerts": 300,
        "overall": {"hit": 1},
        "detail_by_threshold": detail,
    }
    slim = slim_retained_result(raw)
    assert slim["detail_by_threshold"] == {}
    assert slim["detail_row_count"] == 300
    assert slim["detail_truncated"] is True
    assert slim["alerts"] == 300
    assert slim["overall"] == {"hit": 1}


def test_slim_noop_when_under_limit():
    raw = {"rows": [{"i": 1}, {"i": 2}], "trades": 2}
    slim = slim_retained_result(raw, row_limit=400)
    assert len(slim["rows"]) == 2
    assert slim["row_count"] == 2
    assert slim["rows_truncated"] is False


def test_retain_result_none():
    assert retain_result(None) is None


def test_clear_mem_packs_and_release():
    _MEM_PACKS.clear()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 2, 1, tzinfo=timezone.utc)

    class T:
        def __init__(self, ts, bid, ask):
            self.ts = ts
            self.bid = bid
            self.ask = ask

    ticks = [T(start.timestamp() + i, 1.0, 1.1) for i in range(10)]
    # store_cached_pack also writes disk — use direct mem insert to avoid pack format deps
    from backtest.dukascopy import pack_key

    _MEM_PACKS[pack_key("XAUUSD", start, end)] = ticks
    assert len(_MEM_PACKS) == 1
    clear_mem_packs()
    assert _MEM_PACKS == {}

    _MEM_PACKS[pack_key("XAUUSD", start, end)] = ticks
    release_job_memory()
    assert _MEM_PACKS == {}


def test_slim_state_result_inplace():
    class S:
        result = {"rows": [{"i": i} for i in range(DEFAULT_UI_ROW_LIMIT + 10)], "trades": 999}

    s = S()
    slim_state_result_inplace(s)
    assert len(s.result["rows"]) == DEFAULT_UI_ROW_LIMIT
    assert s.result["row_count"] == DEFAULT_UI_ROW_LIMIT + 10
    assert s.result["trades"] == 999
