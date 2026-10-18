"""SQLite catalog for CRT runs and trades."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from backtest.runner import DEFAULT_RESULTS

PathLike = Union[str, Path]

DEFAULT_DB = DEFAULT_RESULTS / "crt.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'crt',
  created_at TEXT NOT NULL,
  finished_at TEXT,
  symbol TEXT NOT NULL,
  date_from TEXT NOT NULL,
  date_to TEXT NOT NULL,
  data_source TEXT NOT NULL,
  timezone TEXT NOT NULL,
  params_json TEXT NOT NULL,
  summary_json TEXT NOT NULL,
  status TEXT NOT NULL,
  json_run_id TEXT
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
  crh REAL,
  crl REAL,
  fvg_top REAL,
  fvg_bottom REAL,
  sweep_ts TEXT,
  sweep_extreme REAL,
  structure_high REAL,
  structure_low REAL,
  extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_crt_trades_run ON trades(run_id, local_date);
CREATE INDEX IF NOT EXISTS idx_crt_trades_side ON trades(side);
CREATE INDEX IF NOT EXISTS idx_crt_trades_date ON trades(local_date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_crt_runs_json ON runs(json_run_id);
"""

_SUMMARY_KEYS = (
    "trades",
    "sum_pts",
    "wins",
    "losses",
    "scratches",
    "win_pct",
    "avg_pts",
    "avg_win_pts",
    "avg_loss_pts",
    "profit_factor",
    "skipped",
    "skip_reasons",
    "exits",
    "entries",
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
    data = _row_dict(row)
    raw = data.pop("extras_json", None)
    try:
        data["extras"] = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        data["extras"] = {}
    return data


def _stamp_existing(conn: sqlite3.Connection, run_id: int, rows: List[Any]) -> None:
    found = conn.execute(
        "SELECT id, local_date, entry_ts FROM trades WHERE run_id = ?",
        (int(run_id),),
    ).fetchall()
    by = {(r["local_date"], r["entry_ts"]): int(r["id"]) for r in found}
    for trade in rows:
        if not isinstance(trade, dict):
            continue
        key = (trade.get("local_date"), trade.get("entry_ts") or "")
        if key in by:
            trade["id"] = by[key]
            trade["run_id"] = int(run_id)


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
    created = created_at or result.get("finished_at") or finished
    json_run_id = str(result.get("run_id") or "").strip() or None
    try:
        with _connect(db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO runs (
                  kind, created_at, finished_at, symbol, date_from, date_to,
                  data_source, timezone, params_json, summary_json, status, json_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(result.get("kind") or "crt"),
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
                    json_run_id,
                ),
            )
            run_id = int(cur.lastrowid)
            for trade in rows:
                if not isinstance(trade, dict):
                    continue
                extras = json.dumps(trade, default=str)
                cur = conn.execute(
                    """
                    INSERT INTO trades (
                      run_id, local_date, side, entry_reason, entry_ts, exit_ts,
                      entry, exit, sl, tp, pts, exit_reason,
                      crh, crl, fvg_top, fvg_bottom, sweep_ts, sweep_extreme,
                      structure_high, structure_low, extras_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        trade.get("local_date"),
                        trade.get("side") or "",
                        trade.get("entry_reason"),
                        trade.get("entry_ts") or "",
                        trade.get("exit_ts"),
                        float(trade.get("entry") or 0.0),
                        trade.get("exit"),
                        trade.get("sl"),
                        trade.get("tp"),
                        trade.get("pts"),
                        trade.get("exit_reason"),
                        trade.get("crh"),
                        trade.get("crl"),
                        trade.get("fvg_top"),
                        trade.get("fvg_bottom"),
                        trade.get("sweep_ts"),
                        trade.get("sweep_extreme"),
                        trade.get("structure_high"),
                        trade.get("structure_low"),
                        extras,
                    ),
                )
                trade["id"] = int(cur.lastrowid)
                trade["run_id"] = run_id
        return run_id
    except sqlite3.IntegrityError:
        if not json_run_id:
            return None
        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT id FROM runs WHERE json_run_id = ?",
                (json_run_id,),
            ).fetchone()
            if row is None:
                return None
            run_id = int(row["id"])
            _stamp_existing(conn, run_id, rows)
        return run_id


def list_runs(db_path: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    out = []
    for row in rows:
        data = _row_dict(row)
        try:
            data["params"] = json.loads(data.pop("params_json") or "{}")
        except (TypeError, ValueError):
            data["params"] = {}
        try:
            data["summary"] = json.loads(data.pop("summary_json") or "{}")
        except (TypeError, ValueError):
            data["summary"] = {}
        out.append(data)
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
    return [_trade_out(row) for row in rows]


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
    data = _row_dict(row)
    try:
        data["params"] = json.loads(data.pop("params_json") or "{}")
    except (TypeError, ValueError):
        data["params"] = {}
    try:
        data["summary"] = json.loads(data.pop("summary_json") or "{}")
    except (TypeError, ValueError):
        data["summary"] = {}
    return data


def delete_run(db_path: Optional[PathLike], run_id: int) -> bool:
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM runs WHERE id = ?", (int(run_id),))
        return cur.rowcount > 0


def sync_json_catalog(
    db_path: Optional[PathLike] = None,
    results_dir: Optional[PathLike] = None,
) -> int:
    """Insert crt JSON files that are not in the catalog yet."""
    folder = Path(results_dir) if results_dir is not None else DEFAULT_RESULTS
    if not folder.is_dir():
        return 0
    init_db(db_path)
    with _connect(db_path) as conn:
        known = {
            str(row["json_run_id"])
            for row in conn.execute(
                "SELECT json_run_id FROM runs WHERE json_run_id IS NOT NULL"
            ).fetchall()
            if row["json_run_id"]
        }
    added = 0
    for path in sorted(folder.glob("crt_*.json")):
        stem = path.stem
        if any(stem.endswith(str(key)) for key in known):
            continue
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(result, dict):
            continue
        json_run_id = str(result.get("run_id") or "").strip()
        if json_run_id and json_run_id in known:
            continue
        if not result.get("rows"):
            continue
        date_from = str(result.get("date_from") or (result.get("params") or {}).get("date_from") or "")
        date_to = str(result.get("date_to") or (result.get("params") or {}).get("date_to") or "")
        if not date_from or not date_to:
            continue
        status = "cancelled" if result.get("cancelled") else "complete"
        run_id = insert_run(
            db_path,
            date_from=date_from,
            date_to=date_to,
            result=result,
            status=status,
            created_at=result.get("finished_at"),
        )
        if run_id is not None:
            added += 1
            if json_run_id:
                known.add(json_run_id)
    return added
