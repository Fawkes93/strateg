#!/usr/bin/env python3
"""
Micro burst param sweep for a wall-clock budget (default 8 hours).

Runs sequential full-range jobs, one-at-a-time changes from the UI default
plus a handful of stacked combos. Stops when the budget is spent or the
queue is empty. Writes per-job JSON plus a running leaderboard.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.micro_momentum_jobs import (  # noqa: E402
    MicroJobParams,
    MicroProgress,
    _cancel,
    _lock,
    _run,
    _state,
    get_micro_state,
)
from backtest.runner import DEFAULT_RESULTS  # noqa: E402

DATE_FROM = "2025-01-01"
DATE_TO = "2026-08-30"
BUDGET_SEC = 8 * 3600
WORKERS = 2


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def base_params(**kw) -> MicroJobParams:
    p = MicroJobParams(
        symbol="XAUUSD",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        workers=WORKERS,
        force_download=False,
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def job_queue() -> List[Tuple[str, MicroJobParams]]:
    """Research-shaped queue: singles, then stacks. Skip the already-timed default."""
    out: List[Tuple[str, MicroJobParams]] = []

    def add(name: str, **kw) -> None:
        out.append((name, base_params(**kw)))

    # Sessions
    add("session-asia", session="asia")
    add("session-asia-london", session="asia_london")
    add("session-london-ny", session="london_ny")

    # Burst window / size
    for v in (2.0, 3.0, 6.0, 8.0):
        add(f"win={v:g}", window_sec=v)
    for v in (80, 120, 150, 200):
        add(f"min={v}", min_burst_pts=float(v))
    for v in (300, 500, 600):
        add(f"max={v}", max_burst_pts=float(v))
    for v in (0.20, 0.25, 0.45, 0.55):
        add(f"persist={v}", persist_frac=float(v))

    # 1m filter
    add("1m-off", use_1m=False)
    for v in (20, 60, 80):
        add(f"1m-body={v}", min_1m_body=float(v))

    # Exits
    for v in (60, 80, 120, 150, 200):
        add(f"tp={v}", tp_pts=float(v))
    for v in (60, 100, 120, 150):
        add(f"sl={v}", sl_pts=float(v))
    for v in (30, 40, 50, 60):
        add(f"trail={v}", trail_pts=float(v), trail_arm_pts=0.0)
    add("trail40-arm40", trail_pts=40.0, trail_arm_pts=40.0)
    add("trail40-arm50", trail_pts=40.0, trail_arm_pts=50.0)
    add("trail50-arm80", trail_pts=50.0, trail_arm_pts=80.0)
    for v in (20, 30, 60, 90, 120):
        add(f"hold={v}", max_hold_sec=float(v))
    for v in (0, 30, 45):
        add(f"cd={v}", cooldown_sec=float(v))
    for v in (0.0, 1.0):
        add(f"lag={v:g}", lag_sec=float(v))
    for v in (30, 40, 80):
        add(f"spread={v}", max_spread_pts=float(v))

    # Stacks — the new strategy's interesting corners
    add("tight-scalp", window_sec=2.0, min_burst_pts=80.0, tp_pts=60.0, sl_pts=50.0, max_hold_sec=25.0)
    add("wider-burst", window_sec=8.0, min_burst_pts=200.0, max_burst_pts=500.0, tp_pts=150.0, sl_pts=120.0, max_hold_sec=90.0)
    add("asia-trail", session="asia", trail_pts=40.0, trail_arm_pts=50.0)
    add("lonny-trail", session="london_ny", trail_pts=40.0, trail_arm_pts=50.0)
    add("asia-min80-hold60", session="asia", min_burst_pts=80.0, max_hold_sec=60.0)
    add("be-trail", trail_pts=40.0, trail_arm_pts=40.0, tp_pts=120.0, sl_pts=80.0)
    add("no1m-persist25", use_1m=False, persist_frac=0.25)
    add("win3-min80-tp80", window_sec=3.0, min_burst_pts=80.0, tp_pts=80.0, sl_pts=60.0)
    add("win6-min150-tp120", window_sec=6.0, min_burst_pts=150.0, tp_pts=120.0, sl_pts=100.0)
    add("asia-london-trail40", session="asia_london", trail_pts=40.0, trail_arm_pts=50.0, max_hold_sec=60.0)
    add("fast-lag0-cd0", lag_sec=0.0, cooldown_sec=0.0)
    add("spread30-trail40", max_spread_pts=30.0, trail_pts=40.0, trail_arm_pts=50.0)
    return out


def slim_result(name: str, result: dict, elapsed: float, phase: str, error) -> dict:
    keys = (
        "kind", "symbol", "trades", "wins", "losses", "scratches",
        "win_pct", "tp_n", "sl_n", "trail_n", "timeout_n",
        "avg_pts", "sum_pts", "profit_factor", "ticks", "months",
        "date_from", "date_to", "cancelled", "saved_to",
    )
    out = {k: result.get(k) for k in keys}
    out["name"] = name
    out["elapsed_sec"] = round(elapsed, 1)
    out["progress_phase"] = phase
    out["progress_error"] = error
    out["params"] = result.get("params")
    return out


def run_one(name: str, params: MicroJobParams) -> dict:
    log(f"START {name}")
    with _lock:
        _cancel.clear()
        _state.params = params
        _state.result = None
        _state.running = True
        _state.progress = MicroProgress(
            phase="download",
            message="Starting…",
            pct=0.0,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    stop = threading.Event()

    def heartbeat() -> None:
        last = ""
        while not stop.wait(30):
            s = get_micro_state()
            p = s.get("progress") or {}
            line = (
                f"  {name}  {p.get('pct')}%  {p.get('phase')}  "
                f"{p.get('message')}  trades={p.get('trades')}"
            )
            if line != last:
                print(line, flush=True)
                last = line

    hb = threading.Thread(target=heartbeat, daemon=True)
    hb.start()
    t0 = time.time()
    try:
        _run(params)
    finally:
        stop.set()

    s = get_micro_state(include_rows=False)
    result = s.get("result") or {}
    prog = s.get("progress") or {}
    row = slim_result(name, result, time.time() - t0, prog.get("phase"), prog.get("error"))
    saved = result.get("saved_to")
    if saved:
        src = Path(saved)
        dest = DEFAULT_RESULTS / f"micro_{name}_{params.date_from}_{params.date_to}.json"
        if src.exists():
            dest.write_bytes(src.read_bytes())
            row["saved_to"] = str(dest)
    log(
        f"DONE {name}  trades={row.get('trades')} sum={row.get('sum_pts')} "
        f"win={row.get('win_pct')} pf={row.get('profit_factor')} "
        f"elapsed={row.get('elapsed_sec')}s phase={row.get('progress_phase')}"
    )
    return row


def write_board(path: Path, rows: list, deadline: float) -> None:
    ranked = sorted(
        [r for r in rows if r.get("progress_phase") == "done" and r.get("trades")],
        key=lambda r: (r.get("sum_pts") is None, -(r.get("sum_pts") or 0), -(r.get("profit_factor") or 0)),
    )
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "seconds_left": round(max(0.0, deadline - time.time()), 1),
        "jobs_done": len(rows),
        "leaderboard": ranked[:15],
        "all": rows,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))


def main() -> int:
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    board = DEFAULT_RESULTS / "micro_sweep_board.json"
    deadline = time.time() + BUDGET_SEC
    log(f"sweep  {DATE_FROM} → {DATE_TO}  budget={BUDGET_SEC/3600:.1f}h  workers={WORKERS}")
    rows = []
    for name, params in job_queue():
        left = deadline - time.time()
        if left < 90:
            log(f"budget exhausted ({left:.0f}s left) — stopping before {name}")
            break
        row = run_one(name, params)
        rows.append(row)
        write_board(board, rows, deadline)
        if row.get("progress_phase") == "error":
            log(f"error on {name}: {row.get('progress_error')}")
            # keep going unless it's a systemic failure
            if not rows or all(r.get("progress_phase") == "error" for r in rows[-3:]):
                if len(rows) >= 3:
                    log("three errors in a row — abort")
                    break
    write_board(board, rows, deadline)
    log(f"sweep finished  jobs={len(rows)}  board={board}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
