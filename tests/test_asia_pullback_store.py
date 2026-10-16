from pathlib import Path

from backtest.asia_pullback_api import chart_lines, chart_markers, snap_bar
from backtest.asia_pullback_store import (
    delete_run,
    get_trade,
    insert_run,
    list_runs,
    list_trades,
    sync_json_catalog,
)


def _row(day, side="UP", reason="leg_fib", pts=100.0):
    return {
        "local_date": day,
        "weekday": "Tuesday",
        "side": side,
        "entry_reason": reason,
        "confirm_mode": "touch",
        "entry_ts": day + "T03:30:00+00:00",
        "exit_ts": day + "T08:20:00+00:00",
        "entry": 3012.62,
        "exit": 3021.66,
        "sl": 2999.48,
        "tp": 3021.66,
        "pts": pts,
        "exit_reason": "tp" if pts > 0 else "sl",
        "box_high": 3008.51,
        "box_low": 2999.48,
        "box_pts": 903.0,
        "break_ts": day + "T03:00:00+00:00",
        "break_price": 3011.0,
        "level": 3012.62,
        "impulse_extreme": 3015.17,
    }


def _payload(rows, run_id="20261016T120000Z_abcd1234"):
    pts = sum(r["pts"] for r in rows)
    return {
        "kind": "asia_pullback",
        "symbol": "XAU/USD",
        "data_source": "candles_5m",
        "run_id": run_id,
        "params": {"timezone": "Europe/Bucharest", "flatten_hour": 23},
        "trades": len(rows),
        "sum_pts": pts,
        "wins": sum(1 for r in rows if r["pts"] > 0),
        "skipped": 2,
        "skip_reasons": {"no_break": 2},
        "rows": rows,
    }


def test_insert_filters_and_delete(tmp_path: Path):
    db = tmp_path / "asia_pullback.sqlite"
    rows = [
        _row("2025-03-18", "UP", "leg_fib", 904),
        _row("2025-03-19", "DOWN", "box_fib", -400),
    ]
    payload = _payload(rows)
    run_id = insert_run(
        db,
        date_from="2025-03-01",
        date_to="2025-06-01",
        result=payload,
        status="complete",
    )
    assert run_id == 1
    assert rows[0]["id"] == 1
    assert rows[1]["run_id"] == 1

    again = insert_run(
        db,
        date_from="2025-03-01",
        date_to="2025-06-01",
        result=payload,
        status="complete",
    )
    assert again == 1
    assert list_runs(db)[0]["summary"]["skipped"] == 2
    assert list_runs(db)[0]["timezone"] == "Europe/Bucharest"
    assert len(list_trades(db)) == 2

    ups = list_trades(db, side="UP", entry_reason="leg_fib")
    assert len(ups) == 1
    assert ups[0]["level"] == 3012.62
    assert ups[0]["extras"]["impulse_extreme"] == 3015.17

    later = list_trades(db, date_from="2025-03-19", date_to="2025-03-20")
    assert [t["local_date"] for t in later] == ["2025-03-19"]

    trade = get_trade(db, rows[1]["id"])
    assert trade["side"] == "DOWN"
    assert trade["exit_reason"] == "sl"

    assert delete_run(db, run_id)
    assert list_trades(db) == []
    assert list_runs(db) == []


def test_empty_run_is_not_saved(tmp_path: Path):
    db = tmp_path / "asia_pullback.sqlite"
    assert (
        insert_run(
            db,
            date_from="2025-03-01",
            date_to="2025-06-01",
            result=_payload([]),
            status="complete",
        )
        is None
    )


def test_sync_imports_a_json_once(tmp_path: Path):
    db = tmp_path / "asia_pullback.sqlite"
    folder = tmp_path / "results"
    folder.mkdir()
    import json

    payload = _payload([_row("2025-03-18")], run_id="20261016T134909Z_cb7f00f1")
    payload["date_from"] = "2025-03-01"
    payload["date_to"] = "2025-06-01"
    (folder / "asiapullback_XAUUSD_5m_2025-03-01_2025-06-01_20261016T134909Z_cb7f00f1.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    assert sync_json_catalog(db, folder) == 1
    assert sync_json_catalog(db, folder) == 0
    runs = list_runs(db)
    assert runs[0]["json_run_id"] == "20261016T134909Z_cb7f00f1"
    assert runs[0]["summary"]["trades"] == 1


def test_break_marker_sits_on_the_bar_that_closed():
    # 15m opens. The break close is 03:00, which is also the next bar's open.
    opens = [int(1_741_000_000 + i * 900) for i in range(6)]
    break_at = opens[2]
    entry_at = opens[4]
    from datetime import datetime, timezone

    trade = _row("2025-03-18")
    trade["break_ts"] = datetime.fromtimestamp(break_at, tz=timezone.utc).isoformat()
    trade["entry_ts"] = datetime.fromtimestamp(entry_at, tz=timezone.utc).isoformat()
    trade["exit_ts"] = datetime.fromtimestamp(opens[5] + 300, tz=timezone.utc).isoformat()
    assert snap_bar(opens, trade["break_ts"], at_close=True) == opens[1]
    assert snap_bar(opens, trade["entry_ts"], at_close=False) == entry_at
    markers = chart_markers(trade, opens, {"level_ref": "leg_fib"})
    assert markers[0]["time"] == opens[1]
    assert markers[0]["text"] == "Break"
    assert markers[1]["text"] == "Fib of the leg"
    lines = chart_lines(trade)
    titles = [ln["title"] for ln in lines]
    assert titles == ["Box high", "Box low", "SL", "TP", "Level", "Impulse"]
