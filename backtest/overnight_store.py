"""SQLite catalog for Overnight break runs and trades."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backtest.runner import DEFAULT_RESULTS

PathLike = Union[str, Path]

DEFAULT_DB = DEFAULT_RESULTS / "overnight.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'overnight_break',
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
  side TEXT NOT NULL,
  entry_reason TEXT,
  entry_ts TEXT NOT NULL,
  exit_ts TEXT,
  entry REAL NOT NULL,
  exit REAL,
  sl REAL,
  tp REAL,
  pts REAL,
  exit_reason TEXT,
  asia_high REAL,
  asia_low REAL,
  asia_range_pts REAL,
  break_ts TEXT,
  break_price REAL,
  extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_ob_trades_run ON trades(run_id, local_date);
CREATE INDEX IF NOT EXISTS idx_ob_trades_side ON trades(side);
CREATE INDEX IF NOT EXISTS idx_ob_trades_date ON trades(local_date);
"""

_SUMMARY_KEYS = (
    "trades",
    "sum_pts",
    "wins",
    "win_pct",
    "avg_pts",
    "profit_factor",
    "skipped",
    "skip_reasons",
    "trail_armed_pct",
    "be_armed_pct",
    "avg_win_pts",
    "avg_loss_pts",
)


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
    """Save the run. Stamps id and run_id onto each trade row. None if there are no trades."""
    rows = result.get("rows") or []
    n_trades = int(result.get("trades") or len(rows) or 0)
    if n_trades <= 0 or not rows:
        return None
    init_db(db_path)
    params = result.get("params") or {}
    summary = {k: result.get(k) for k in _SUMMARY_KEYS if k in result}
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
                str(result.get("kind") or "overnight_break"),
                created,
                finished,
                str(result.get("symbol") or "XAU/USD"),
                date_from,
                date_to,
                str(result.get("data_source") or "candles_5m"),
                str(params.get("timezone") or "Europe/Bucharest"),
                json.dumps(params, default=str),
                json.dumps(summary, default=str),
                status,
            ),
        )
        run_id = int(cur.lastrowid)
        for t in rows:
            if not isinstance(t, dict):
                continue
            extras = json.dumps(t, default=str)
            cur = conn.execute(
                """
                INSERT INTO trades (
                  run_id, local_date, side, entry_reason, entry_ts, exit_ts,
                  entry, exit, sl, tp, pts, exit_reason,
                  asia_high, asia_low, asia_range_pts, break_ts, break_price,
                  extras_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    t.get("local_date"),
                    t.get("side") or "",
                    t.get("entry_reason"),
                    t.get("entry_ts") or "",
                    t.get("exit_ts"),
                    float(t.get("entry") or 0.0),
                    t.get("exit"),
                    t.get("sl"),
                    t.get("tp"),
                    t.get("pts"),
                    t.get("exit_reason"),
                    t.get("asia_high"),
                    t.get("asia_low"),
                    t.get("asia_range_pts"),
                    t.get("break_ts"),
                    t.get("break_price"),
                    extras,
                ),
            )
            t["id"] = int(cur.lastrowid)
            t["run_id"] = run_id
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
    side: Optional[str] = None,
    entry_reason: Optional[str] = None,
    exit_reason: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    clauses: List[str] = []
    args: List[Any] = []
    if run_id is not None:
        clauses.append("run_id = ?")
        args.append(int(run_id))
    if side:
        clauses.append("side = ?")
        args.append(side)
    if entry_reason:
        clauses.append("entry_reason = ?")
        args.append(entry_reason)
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
