#!/usr/bin/env python3
"""All-day stall-fade grid. Quiet hours starved the sample; June 50% TP had the best WR."""

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

DATE_FROM = "2025-01-01"
DATE_TO = "2026-08-30"


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def job(**kw) -> MicroJobParams:
    p = MicroJobParams(
        symbol="XAUUSD",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        window_sec=4.0,
        min_burst_pts=100.0,
        max_burst_pts=300.0,
        persist_frac=0.35,
        use_1m=False,
        mode="fade",
        pause_sec=1.0,
        pause_give_up_sec=8.0,
        tp_frac=0.50,
        rr_one_to_one=True,
        sl_mult=1.0,
        trail_frac=0.5,
        max_hold_sec=20.0,
        cooldown_sec=20.0,
        lag_sec=0.0,
        session="all",
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
        f"START {name}  session={params.session} pause={params.pause_sec} "
        f"tp={params.tp_frac} min={params.min_burst_pts} sl_mult={params.sl_mult}"
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
        "kind", "symbol", "trades", "wins", "losses", "win_pct",
        "tp_n", "sl_n", "trail_n", "timeout_n", "avg_pts", "sum_pts",
        "profit_factor", "ticks", "months",
    )
    row = {k: result.get(k) for k in keys}
    row.update({
        "name": name,
        "elapsed_sec": round(time.time() - t0, 1),
        "progress_phase": prog.get("phase"),
        "progress_error": prog.get("error"),
        "session": params.session,
        "pause_sec": params.pause_sec,
        "tp_frac": params.tp_frac,
        "min_burst_pts": params.min_burst_pts,
        "sl_mult": params.sl_mult,
        "persist_frac": params.persist_frac,
    })
    saved = result.get("saved_to")
    if saved:
        src = Path(saved)
        dest = DEFAULT_RESULTS / f"micro_allday_{name}_{DATE_FROM}_{DATE_TO}.json"
        if src.exists():
            dest.write_bytes(src.read_bytes())
            row["saved_to"] = str(dest)
    log(
        f"DONE {name}  n={row.get('trades')} wr={row.get('win_pct')} "
        f"pf={row.get('profit_factor')} sum={row.get('sum_pts')} "
        f"{row.get('elapsed_sec')}s"
    )
    return row


def main() -> int:
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("all-p1-f50", job()),
        ("all-p1-f35", job(tp_frac=0.35)),
        ("all-p05-f50", job(pause_sec=0.5)),
        ("all-p2-f50", job(pause_sec=2.0)),
        ("all-min150-f50", job(min_burst_pts=150.0)),
        ("all-p1-f50-sl15", job(sl_mult=1.5)),
        ("all-p1-f50-persist20", job(persist_frac=0.20)),
    ]
    rows = []
    for name, params in jobs:
        row = run_one(name, params)
        rows.append(row)
        (DEFAULT_RESULTS / "micro_allday_board.json").write_text(
            json.dumps(rows, indent=2, default=str)
        )
        if row.get("progress_phase") == "error":
            log(f"error {name}: {row.get('progress_error')}")
            break
    out = DEFAULT_RESULTS / "micro_allday_probe.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    log(f"summary → {out}")
    print(json.dumps(rows, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
