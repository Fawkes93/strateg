from datetime import datetime, timezone
from pathlib import Path

from backtest.crt_api import chart_lines, chart_markers, snap_bar
from backtest.crt_store import delete_run, get_trade, insert_run, list_runs, list_trades


def _row(day="2025-03-03", pts=1150.0, reason="tp"):
    return {
        "local_date": day,
        "weekday": "Monday",
        "side": "UP",
        "entry_reason": "fvg",
        "entry_ts": day + "T09:30:00+00:00",
        "exit_ts": day + "T09:40:00+00:00",
        "entry": 2010.0,
        "exit": 2030.0,
        "sl": 2007.0,
        "tp": 2030.0,
        "partial_px": 2013.0,
        "pts": pts,
        "exit_reason": reason,
        "crh": 2025.0,
        "crl": 2004.0,
        "fvg_top": 2010.0,
        "fvg_bottom": 2007.0,
        "sweep_ts": day + "T09:15:00+00:00",
        "sweep_extreme": 2000.0,
        "structure_high": 2030.0,
        "structure_low": 1990.0,
        "range_open_ts": day + "T09:00:00+00:00",
        "partial_hit": True,
        "story": "Uptrend. The next candle closed back inside.",
    }


def test_insert_stamps_ids_and_skips_an_empty_run(tmp_path: Path):
    db = tmp_path / "crt.sqlite"
    rows = [_row(), _row("2025-03-04", pts=0, reason="partial_sl")]
    rows[1]["entry_ts"] = "2025-03-04T09:30:00+00:00"
    payload = {
        "kind": "crt",
        "symbol": "XAU/USD",
        "data_source": "candles_5m",
        "run_id": "20261018T120000Z_abcd1234",
        "params": {"timezone": "Europe/Bucharest", "htf_min": 60, "ltf_min": 5},
        "trades": 2,
        "sum_pts": 1150,
        "wins": 1,
        "rows": rows,
    }
    assert insert_run(db, date_from="2025-03-01", date_to="2025-04-01", result={"rows": []}) is None
    run_id = insert_run(db, date_from="2025-03-01", date_to="2025-04-01", result=payload)
    assert run_id == 1
    assert rows[0]["id"] == 1
    assert rows[1]["run_id"] == 1
    again = insert_run(db, date_from="2025-03-01", date_to="2025-04-01", result=payload)
    assert again == 1
    assert len(list_runs(db)) == 1
    longs = list_trades(db, side="UP")
    assert len(longs) == 2
    stored = get_trade(db, 1)
    assert stored["crh"] == 2025
    assert stored["extras"]["story"].startswith("Uptrend")
    assert delete_run(db, 1) is True
    assert list_runs(db) == []


def test_chart_marks_the_sweep_and_the_gap():
    trade = _row()
    opens = [
        int(datetime(2025, 3, 3, 9, 0, tzinfo=timezone.utc).timestamp()),
        int(datetime(2025, 3, 3, 9, 15, tzinfo=timezone.utc).timestamp()),
        int(datetime(2025, 3, 3, 9, 30, tzinfo=timezone.utc).timestamp()),
        int(datetime(2025, 3, 3, 9, 35, tzinfo=timezone.utc).timestamp()),
        int(datetime(2025, 3, 3, 9, 40, tzinfo=timezone.utc).timestamp()),
    ]
    assert snap_bar(opens, trade["entry_ts"]) == opens[2]
    markers = chart_markers(trade, opens)
    labels = [m["text"] for m in markers]
    assert "Range" in labels
    assert "Sweep" in labels
    assert "FVG" in labels
    titles = [line["title"] for line in chart_lines(trade)]
    assert "CRH" in titles
    assert "CRL" in titles
    assert "FVG" in titles
    assert "1:1" in titles
    assert "Runner" in titles
