from pathlib import Path

from backtest.asia_box_store import (
    get_trade,
    init_db,
    insert_run,
    list_runs,
    list_trades,
)


def _run_payload(setup="continuation", pts=100.0):
    return {
        "kind": "asia_box",
        "symbol": "XAU/USD",
        "data_source": "candles_5m",
        "params": {"min_range_pts": 3000, "timezone": "UTC"},
        "trades": 1,
        "sum_pts": pts,
        "wins": 1 if pts > 0 else 0,
        "win_rate": 1.0 if pts > 0 else 0.0,
        "by_setup": {setup: {"n": 1, "sum_pts": pts, "wins": 1 if pts > 0 else 0}},
        "skip_counts": {},
        "rows": [
            {
                "local_date": "2026-07-10",
                "setup": setup,
                "box_n": 1,
                "side": "UP",
                "entry_ts": "2026-07-10T03:05:00+00:00",
                "exit_ts": "2026-07-10T03:10:00+00:00",
                "entry": 3314.6,
                "exit": 3330.0,
                "sl": 3306.42,
                "tp": 3330.0,
                "pts": pts,
                "exit_reason": "tp",
                "fib0": 3330.0,
                "fib1": 3300.0,
                "box_high": 3330.0,
                "box_low": 3300.0,
                "box_high_ts": "2026-07-10T02:00:00+00:00",
                "box_low_ts": "2026-07-10T01:00:00+00:00",
                "box_start_ts": "2026-07-10T01:00:00+00:00",
                "range_pts": 3000.0,
                "extras": {"taint": 0},
            }
        ],
    }


def test_insert_and_filter_trades_across_runs(tmp_path: Path):
    db = tmp_path / "asia_box.sqlite"
    init_db(db)
    r1 = insert_run(
        db,
        date_from="2026-07-01",
        date_to="2026-07-31",
        result=_run_payload("continuation", 100),
        status="complete",
    )
    r2 = insert_run(
        db,
        date_from="2026-08-01",
        date_to="2026-08-31",
        result=_run_payload("reverse_confirm", -50),
        status="complete",
    )
    runs = list_runs(db)
    assert len(runs) == 2
    assert runs[0]["kind"] == "asia_box"
    assert runs[0]["id"] == r2  # newest first

    cont = list_trades(db, setup="continuation")
    assert len(cont) == 1
    assert cont[0]["run_id"] == r1
    assert cont[0]["setup"] == "continuation"

    all_rows = list_trades(db)
    assert len(all_rows) == 2

    one = get_trade(db, cont[0]["id"])
    assert one["fib0"] == 3330.0
    assert one["extras"]["taint"] == 0


def test_session_window_chisinau_is_not_utc_clock():
    from datetime import date

    from backtest.asia_box import session_window_utc

    start, end = session_window_utc(date(2025, 5, 1), "Europe/Chisinau", 1, 6)
    assert start.isoformat() == "2025-04-30T22:00:00+00:00"
    assert end.isoformat() == "2025-05-01T03:00:00+00:00"


def test_insert_skips_run_with_no_trades(tmp_path: Path):
    db = tmp_path / "asia_box.sqlite"
    init_db(db)
    empty = _run_payload()
    empty["trades"] = 0
    empty["rows"] = []
    empty["sum_pts"] = 0
    rid = insert_run(
        db,
        date_from="2026-07-01",
        date_to="2026-07-31",
        result=empty,
        status="complete",
    )
    assert rid is None
    assert list_runs(db) == []
    assert list_trades(db) == []


def test_delete_run_cascades_trades(tmp_path: Path):
    db = tmp_path / "asia_box.sqlite"
    init_db(db)
    rid = insert_run(
        db,
        date_from="2026-07-01",
        date_to="2026-07-31",
        result=_run_payload(),
        status="complete",
    )
    from backtest.asia_box_store import delete_run

    delete_run(db, rid)
    assert list_runs(db) == []
    assert list_trades(db) == []
