"""Saved-run listing, classification, path safety, and idle/busy load."""

from __future__ import annotations

import json

import pytest

from backtest import saved_results as sr
from backtest.jobs import load_saved as research_load
from backtest.session_jobs import load_saved as session_load
from backtest import jobs as jobs_mod
from backtest import session_jobs as session_mod


def test_overnight_label_names_the_data_source():
    assert "5m candles" in sr._label(
        "overnight_XAUUSD_5m_2025-05-01_2025-08-01.json",
        {"symbol": "XAU/USD", "date_from": "2025-05-01", "date_to": "2025-08-01", "trades": 4, "data_source": "candles_5m"},
        "overnight_break",
    )
    assert "ticks" in sr._label(
        "overnight_XAUUSD_ticks_2025-05-01_2025-08-01.json",
        {"symbol": "XAU/USD", "trades": 4, "data_source": "ticks"},
        "overnight_break",
    )


def test_classify_filename():
    assert sr.classify_filename("batch_XAUUSD_20260831T094332.json") == "batch_sweep"
    assert (
        sr.classify_filename("summary_XAUUSD_2026-03-02_2026-03-09_forward.json")
        == "research"
    )
    assert sr.classify_filename("session_XAUUSD_2025-05-01_2025-08-01.json") == "session_clock"
    assert sr.classify_filename("spikefade_XAUUSD_2025-05-01_2025-06-01.json") == "spike_fade"
    assert sr.classify_filename("overnight_XAUUSD_2025-05-01_2025-08-01.json") == "overnight_break"
    assert sr.classify_filename("asialiq_XAUUSD_2025-05-01_2025-08-01.json") == "asia_liquidity"
    assert sr.classify_filename("fork_XAUUSD_2026-06-01_2026-07-01.json") == "impulse_fork"
    assert sr.classify_filename("cooloff_XAUUSD_2026-06-01_2026-07-01.json") == "cooloff"
    assert sr.classify_filename("ifvg_XAUUSD_2025-05-01_2025-06-01.json") == "fvg"
    assert sr.classify_filename("stopscalp_20261006T120000Z_abc12345.json") == "stop_scalper"
    assert sr.classify_filename("crt_XAUUSD_5m_2025-03-01_2025-04-01.json") == "crt"
    assert sr.classify_filename("summary_XAUUSD_2026-06-01_2026-07-01_forward_20260904T120000Z_abc12345.json") == "research"
    assert sr.classify_filename("micro_XAUUSD_2026-06-01_2026-08-31.json") == "micro"
    assert sr.classify_filename("micro_sweep_board.json") == "micro"
    assert sr.classify_filename("fade_heatmap.json") is None


def test_classify_result_filename_wins_over_nested_kind():
    peek = '{"symbol": "XAU/USD", "alerts": 19, "detail": {"kind": "impulse_retrace"}}'
    assert (
        sr.classify_result("summary_XAUUSD_2026-03-02_2026-03-09_forward.json", peek)
        == "research"
    )


def test_classify_micro_uses_json_kind():
    assert (
        sr.classify_result(
            "micro_XAUUSD_2026-06-01_2026-08-31.json",
            '{"kind": "micro_fade", "trades": 12}',
        )
        == "micro_fade"
    )
    assert (
        sr.classify_result(
            "micro_tp=120_2025-01-01_2026-08-30.json",
            '{"kind": "micro_momentum", "trades": 4}',
        )
        == "micro_momentum"
    )
    assert (
        sr.classify_result("micro_sweep_board.json", '{"rows": []}') is None
    )


def test_skip_unknown_json():
    assert sr.classify_result("fade_heatmap_min1400.json", '{"kind": "heatmap"}') is None


def test_list_filters_by_kind_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "DEFAULT_RESULTS", tmp_path)
    (tmp_path / "batch_old.json").write_text(
        json.dumps({"kind": "batch_sweep", "symbol": "XAUUSD", "run_count": 2})
    )
    (tmp_path / "batch_new.json").write_text(
        json.dumps({"kind": "batch_sweep", "symbol": "XAUUSD", "run_count": 9})
    )
    (tmp_path / "session_XAUUSD_a.json").write_text(
        json.dumps(
            {
                "kind": "session_clock",
                "symbol": "XAU/USD",
                "date_from": "2025-05-01",
                "date_to": "2025-08-01",
                "trades": 40,
                "sum_pts": 1200,
            }
        )
    )
    (tmp_path / "micro_sweep_board.json").write_text(json.dumps({"rows": []}))
    # mtime: make batch_new newer
    import os
    import time

    now = time.time()
    os.utime(tmp_path / "batch_old.json", (now - 20, now - 20))
    os.utime(tmp_path / "batch_new.json", (now - 5, now - 5))

    batches = sr.list_saved_results("batch_sweep")
    assert [r["name"] for r in batches] == ["batch_new.json", "batch_old.json"]
    sessions = sr.list_saved_results("session_clock")
    assert len(sessions) == 1
    assert sessions[0]["trades"] == 40
    assert "40 trades" in sessions[0]["label"]
    assert sr.list_saved_results("spike_fade") == []
    with pytest.raises(ValueError):
        sr.list_saved_results("nope")


def test_path_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "DEFAULT_RESULTS", tmp_path)
    (tmp_path / "ok.json").write_text(json.dumps({"kind": "session_clock"}))
    with pytest.raises(ValueError):
        sr.resolve_saved_path("../ok.json")
    with pytest.raises(ValueError):
        sr.resolve_saved_path("foo/ok.json")
    with pytest.raises(ValueError):
        sr.resolve_saved_path(".ok.json")
    with pytest.raises(FileNotFoundError):
        sr.read_saved_result("missing.json")
    data, path = sr.read_saved_result("ok.json")
    assert data["kind"] == "session_clock"
    assert path.name == "ok.json"


def test_load_injects_when_idle_and_refuses_when_running(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "DEFAULT_RESULTS", tmp_path)
    payload = {
        "kind": "session_clock",
        "symbol": "XAU/USD",
        "trades": 3,
        "ticks": 100,
        "date_from": "2025-05-01",
        "date_to": "2025-06-01",
    }
    (tmp_path / "session_XAUUSD_x.json").write_text(json.dumps(payload))

    session_mod._state.running = False
    session_mod._state.result = None
    try:
        out = sr.load_into_job("session_clock", "session_XAUUSD_x.json")
        assert out["ok"] is True
        assert session_mod._state.result["trades"] == 3
        assert session_mod._state.progress.phase == "done"
        assert "session_XAUUSD_x.json" in session_mod._state.progress.message
    finally:
        session_mod._state.running = False
        session_mod._state.result = None

    session_mod._state.running = True
    try:
        out = sr.load_into_job("session_clock", "session_XAUUSD_x.json")
        assert out["ok"] is False
        assert "running" in (out.get("error") or "").lower()
    finally:
        session_mod._state.running = False
        session_mod._state.result = None


def test_load_kind_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "DEFAULT_RESULTS", tmp_path)
    (tmp_path / "session_XAUUSD_x.json").write_text(
        json.dumps({"kind": "session_clock", "trades": 1})
    )
    with pytest.raises(ValueError, match="not research"):
        sr.load_into_job("research", "session_XAUUSD_x.json")


def test_research_load_saved_refuses_when_running():
    jobs_mod._state.running = True
    try:
        out = research_load({"kind": "research", "alerts": 1}, name="x.json")
        assert out["ok"] is False
    finally:
        jobs_mod._state.running = False
        jobs_mod._state.result = None


def test_session_load_saved_idle():
    session_mod._state.running = False
    try:
        out = session_load({"kind": "session_clock", "trades": 2, "ticks": 9}, name="a.json")
        assert out["ok"] is True
        assert session_mod.get_session_state()["result"]["trades"] == 2
    finally:
        session_mod._state.result = None
