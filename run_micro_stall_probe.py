#!/usr/bin/env python3
"""Stall-fade probe: quiet hours (Asia + 8–11pm Chisinau), then Jun/Jul/Aug 2026."""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

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


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def stall_job(date_from: str, date_to: str, **kw) -> MicroJobParams:
    p = MicroJobParams(
        symbol="XAUUSD",
        date_from=date_from,
        date_to=date_to,
        window_sec=4.0,
        min_burst_pts=100.0,
        max_burst_pts=300.0,
        persist_frac=0.35,
        use_1m=False,
        mode="fade",
        pause_sec=1.0,
        pause_give_up_sec=8.0,
        tp_frac=0.35,
        rr_one_to_one=True,
        trail_frac=0.5,
        max_hold_sec=20.0,
        cooldown_sec=20.0,
        lag_sec=0.0,
        session="quiet",
        max_spread_pts=40.0,
        max_spread_vs_tp=0.4,
        trail_pts=0.0,
        workers=2,
        force_download=False,
    )
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def run_one(name: str, params: MicroJobParams) -> dict:
    log(
        f"START {name}  {params.date_from}→{params.date_to}  "
        f"pause={params.pause_sec} tp_frac={params.tp_frac} session={params.session}"
    )
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
        while not stop.wait(20):
            s = get_micro_state()
            p = s.get("progress") or {}
            line = (
                f"  {name}  {p.get('pct')}%  {p.get('phase')}  "
                f"{p.get('message')}  trades={p.get('trades')}"
            )
            if line != last:
                print(line, flush=True)
                last = line

    threading.Thread(target=heartbeat, daemon=True).start()
    t0 = time.time()
    try:
        _run(params)
    finally:
        stop.set()
    s = get_micro_state(include_rows=False)
    result = s.get("result") or {}
    prog = s.get("progress") or {}
    keys = (
        "kind", "symbol", "trades", "wins", "losses", "scratches",
        "win_pct", "tp_n", "sl_n", "trail_n", "timeout_n", "avg_pts",
        "sum_pts", "profit_factor", "ticks", "months", "date_from", "date_to",
    )
    row = {k: result.get(k) for k in keys}
    row.update({
        "name": name,
        "elapsed_sec": round(time.time() - t0, 1),
        "progress_phase": prog.get("phase"),
        "progress_error": prog.get("error"),
        "pause_sec": params.pause_sec,
        "tp_frac": params.tp_frac,
        "session": params.session,
    })
    saved = result.get("saved_to")
    if saved:
        src = Path(saved)
        dest = DEFAULT_RESULTS / (
            f"micro_stall_{name}_{params.date_from}_{params.date_to}.json"
        )
        if src.exists():
            dest.write_bytes(src.read_bytes())
            row["saved_to"] = str(dest)
    log(
        f"DONE {name}  trades={row.get('trades')} wr={row.get('win_pct')} "
        f"pf={row.get('profit_factor')} sum={row.get('sum_pts')} "
        f"elapsed={row.get('elapsed_sec')}s"
    )
    return row


def main() -> int:
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("full-p1-f35", stall_job("2025-01-01", "2026-08-30")),
    ]
    months = [
        ("2026-06", "2026-06-01", "2026-07-01"),
        ("2026-07", "2026-07-01", "2026-08-01"),
        ("2026-08", "2026-08-01", "2026-08-31"),
    ]
    variants = [
        ("p1-f35", {}),
        ("p05-f35", {"pause_sec": 0.5}),
        ("p2-f35", {"pause_sec": 2.0}),
        ("p1-f25", {"tp_frac": 0.25}),
        ("p1-f50", {"tp_frac": 0.50}),
    ]
    for mname, a, b in months:
        for vname, kw in variants:
            jobs.append((f"{mname}-{vname}", stall_job(a, b, **kw)))

    rows = []
    for name, params in jobs:
        row = run_one(name, params)
        rows.append(row)
        board = DEFAULT_RESULTS / "micro_stall_board.json"
        board.write_text(json.dumps(rows, indent=2, default=str))
        if row.get("progress_phase") == "error":
            log(f"error {name}: {row.get('progress_error')}")
            break
    out = DEFAULT_RESULTS / "micro_stall_probe.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    log(f"summary → {out}")
    print(json.dumps(rows, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
