"""SQLite catalog for Asia box runs and trades."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backtest.runner import DEFAULT_RESULTS

PathLike = Union[str, Path]

DEFAULT_DB = DEFAULT_RESULTS / "asia_box.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'asia_box',
  created_at TEXT NOT NULL,
  finished_at TEXT,
  symbol TEXT NOT NULL,
  date_from TEXT NOT NULL,
  date_to TEXT NOT NULL,
  data_source TEXT NOT NULL,
  timezone TEXT NOT NULL,
  params_json TEXT NOT NULL,
  summary_json TEXT NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  local_date TEXT NOT NULL,
  setup TEXT NOT NULL,
  box_n INTEGER NOT NULL,
  side TEXT NOT NULL,
  entry_ts TEXT NOT NULL,
  exit_ts TEXT,
  entry REAL NOT NULL,
  exit REAL,
  sl REAL NOT NULL,
  tp REAL NOT NULL,
  pts REAL,
  exit_reason TEXT,
  fib0 REAL NOT NULL,
  fib1 REAL NOT NULL,
  box_high REAL NOT NULL,
  box_low REAL NOT NULL,
  box_high_ts TEXT,
  box_low_ts TEXT,
  box_start_ts TEXT,
  range_pts REAL NOT NULL,
  extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_ab_trades_run_setup ON trades(run_id, setup);
CREATE INDEX IF NOT EXISTS idx_ab_trades_setup ON trades(setup);
CREATE INDEX IF NOT EXISTS idx_ab_trades_date ON trades(local_date);
"""


def _path(db_path: Optional[PathLike] = None) -> Path:
    return Path(db_path) if db_path is not None else DEFAULT_DB


def _connect(db_path: Optional[PathLike] = None) -> sqlite3.Connection:
    path = _path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[PathLike] = None) -> Path:
    path = _path(db_path)
    with _connect(path) as conn:
        conn.executescript(SCHEMA)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _trade_out(row: sqlite3.Row) -> Dict[str, Any]:
    d = _row_dict(row)
    raw = d.pop("extras_json", None)
    try:
        d["extras"] = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        d["extras"] = {}
    return d


def insert_run(
    db_path: Optional[PathLike],
    *,
    date_from: str,
    date_to: str,
    result: Dict[str, Any],
    status: str = "complete",
    created_at: Optional[str] = None,
) -> Optional[int]:
    rows = result.get("rows") or []
    n_trades = int(result.get("trades") or len(rows) or 0)
    if n_trades <= 0 or not rows:
        return None
    init_db(db_path)
    params = result.get("params") or {}
    summary = {
        "trades": result.get("trades") or len(result.get("rows") or []),
        "sum_pts": result.get("sum_pts") or 0.0,
        "wins": result.get("wins") or 0,
        "win_rate": result.get("win_rate") or 0.0,
        "by_setup": result.get("by_setup") or {},
        "skip_counts": result.get("skip_counts") or {},
    }
    finished = _now()
    created = created_at or finished
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO runs (
              kind, created_at, finished_at, symbol, date_from, date_to,
              data_source, timezone, params_json, summary_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(result.get("kind") or "asia_box"),
                created,
                finished,
                str(result.get("symbol") or "XAU/USD"),
                date_from,
                date_to,
                str(result.get("data_source") or "candles_5m"),
                str(params.get("timezone") or "Europe/Chisinau"),
                json.dumps(params),
                json.dumps(summary),
                status,
            ),
        )
        run_id = int(cur.lastrowid)
        rows = result.get("rows") or []
        for t in rows:
            extras = t.get("extras")
            if extras is None:
                extras_json = t.get("extras_json")
            else:
                extras_json = json.dumps(extras)
            conn.execute(
                """
                INSERT INTO trades (
                  run_id, local_date, setup, box_n, side, entry_ts, exit_ts,
                  entry, exit, sl, tp, pts, exit_reason, fib0, fib1,
                  box_high, box_low, box_high_ts, box_low_ts, box_start_ts,
                  range_pts, extras_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    t.get("local_date"),
                    t.get("setup"),
                    int(t.get("box_n") or 1),
                    t.get("side"),
                    t.get("entry_ts"),
                    t.get("exit_ts"),
                    t.get("entry"),
                    t.get("exit"),
                    t.get("sl"),
                    t.get("tp"),
                    t.get("pts"),
                    t.get("exit_reason"),
                    t.get("fib0"),
                    t.get("fib1"),
                    t.get("box_high"),
                    t.get("box_low"),
                    t.get("box_high_ts"),
                    t.get("box_low_ts"),
                    t.get("box_start_ts"),
                    float(t.get("range_pts") or 0.0),
                    extras_json,
                ),
            )
    return run_id


def list_runs(db_path: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        d = _row_dict(r)
        try:
            d["params"] = json.loads(d.pop("params_json") or "{}")
        except (TypeError, ValueError):
            d["params"] = {}
        try:
            d["summary"] = json.loads(d.pop("summary_json") or "{}")
        except (TypeError, ValueError):
            d["summary"] = {}
        out.append(d)
    return out


def list_trades(
    db_path: Optional[PathLike] = None,
    *,
    run_id: Optional[int] = None,
    setup: Optional[str] = None,
    side: Optional[str] = None,
    box_n: Optional[int] = None,
    exit_reason: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    clauses = []
    args: List[Any] = []
    if run_id is not None:
        clauses.append("run_id = ?")
        args.append(int(run_id))
    if setup:
        clauses.append("setup = ?")
        args.append(setup)
    if side:
        clauses.append("side = ?")
        args.append(side)
    if box_n is not None:
        clauses.append("box_n = ?")
        args.append(int(box_n))
    if exit_reason:
        clauses.append("exit_reason = ?")
        args.append(exit_reason)
    if date_from:
        clauses.append("local_date >= ?")
        args.append(date_from)
    if date_to:
        clauses.append("local_date < ?")
        args.append(date_to)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = "SELECT * FROM trades" + where + " ORDER BY local_date, id"
    with _connect(db_path) as conn:
        rows = conn.execute(sql, args).fetchall()
    return [_trade_out(r) for r in rows]


def get_trade(db_path: Optional[PathLike], trade_id: int) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM trades WHERE id = ?", (int(trade_id),)).fetchone()
    if row is None:
        return None
    return _trade_out(row)


def get_run(db_path: Optional[PathLike], run_id: int) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (int(run_id),)).fetchone()
    if row is None:
        return None
    d = _row_dict(row)
    try:
        d["params"] = json.loads(d.pop("params_json") or "{}")
    except (TypeError, ValueError):
        d["params"] = {}
    try:
        d["summary"] = json.loads(d.pop("summary_json") or "{}")
    except (TypeError, ValueError):
        d["summary"] = {}
    return d


def delete_run(db_path: Optional[PathLike], run_id: int) -> bool:
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM runs WHERE id = ?", (int(run_id),))
        return cur.rowcount > 0
