from pathlib import Path

from backtest.overnight_store import delete_run, get_trade, insert_run, list_runs, list_trades


def _row(day, side="UP", reason="ema_touch", pts=100.0):
    return {
        "local_date": day,
        "side": side,
        "entry_reason": reason,
        "entry_ts": day + "T07:15:00+00:00",
        "exit_ts": day + "T09:00:00+00:00",
        "entry": 3300.0,
        "exit": 3310.0,
        "sl": 3280.0,
        "tp": 3340.0,
        "pts": pts,
        "exit_reason": "tp" if pts > 0 else "sl",
        "asia_high": 3290.0,
        "asia_low": 3270.0,
        "asia_range_pts": 2000.0,
        "break_ts": day + "T07:00:00+00:00",
        "break_price": 3295.0,
        "decision": "wait 2 EMA touch",
    }


def _payload(rows):
    pts = sum(r["pts"] for r in rows)
    return {
        "kind": "overnight_break",
        "symbol": "XAU/USD",
        "data_source": "candles_5m",
        "params": {"timezone": "Europe/Bucharest", "flatten_hour": 18},
        "trades": len(rows),
        "sum_pts": pts,
        "wins": sum(1 for r in rows if r["pts"] > 0),
        "skipped": 2,
        "skip_reasons": {"no_break": 2},
        "rows": rows,
    }


def test_insert_filters_and_delete(tmp_path: Path):
    db = tmp_path / "overnight.sqlite"
    rows = [
        _row("2026-05-04", "UP", "ema_touch", 120),
        _row("2026-05-05", "DOWN", "higher_close", -40),
    ]
    payload = _payload(rows)
    run_id = insert_run(
        db,
        date_from="2026-05-01",
        date_to="2026-06-01",
        result=payload,
        status="complete",
    )
    assert run_id == 1
    assert rows[0]["id"] == 1
    assert rows[1]["run_id"] == 1

    runs = list_runs(db)
    assert runs[0]["summary"]["skipped"] == 2
    assert runs[0]["timezone"] == "Europe/Bucharest"

    ups = list_trades(db, side="UP")
    assert len(ups) == 1
    assert ups[0]["entry_reason"] == "ema_touch"
    assert ups[0]["extras"]["decision"] == "wait 2 EMA touch"

    later = list_trades(db, date_from="2026-05-05", date_to="2026-05-06")
    assert [t["local_date"] for t in later] == ["2026-05-05"]

    trade = get_trade(db, rows[1]["id"])
    assert trade["side"] == "DOWN"
    assert trade["exit_reason"] == "sl"

    assert delete_run(db, run_id)
    assert list_trades(db) == []
    assert list_runs(db) == []


def test_empty_run_is_not_saved(tmp_path: Path):
    db = tmp_path / "overnight.sqlite"
    assert (
        insert_run(
            db,
            date_from="2026-05-01",
            date_to="2026-06-01",
            result=_payload([]),
            status="complete",
        )
        is None
    )
