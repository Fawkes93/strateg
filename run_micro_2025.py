#!/usr/bin/env python3
"""Micro burst scalp: 2025-01-01 → today, default UI params + a couple of variants."""

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
DATE_TO = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def run_one(name: str, params: MicroJobParams) -> dict:
    log(f"START {name}  {params.date_from} → {params.date_to}  session={params.session} trail={params.trail_pts}/{params.trail_arm_pts}")
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
                f"{p.get('message')}  trades={p.get('trades')} ticks={p.get('ticks')}"
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
    elapsed = time.time() - t0
    slim = {k: result.get(k) for k in (
        "kind", "symbol", "trades", "wins", "losses", "scratches",
        "win_pct", "tp_n", "sl_n", "trail_n", "timeout_n",
        "avg_pts", "sum_pts", "profit_factor", "ticks", "months",
        "date_from", "date_to", "cancelled", "saved_to",
    )}
    slim["name"] = name
    slim["elapsed_sec"] = round(elapsed, 1)
    slim["progress_phase"] = (s.get("progress") or {}).get("phase")
    slim["progress_error"] = (s.get("progress") or {}).get("error")
    log(f"DONE {name}  {json.dumps(slim, default=str)}")
    return slim


def main() -> int:
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("default-all", MicroJobParams(
            symbol="XAUUSD",
            date_from=DATE_FROM,
            date_to=DATE_TO,
            session="all",
            workers=2,
        )),
        ("trail40-arm50", MicroJobParams(
            symbol="XAUUSD",
            date_from=DATE_FROM,
            date_to=DATE_TO,
            session="all",
            trail_pts=40.0,
            trail_arm_pts=50.0,
            workers=2,
        )),
        ("asia", MicroJobParams(
            symbol="XAUUSD",
            date_from=DATE_FROM,
            date_to=DATE_TO,
            session="asia",
            workers=2,
        )),
    ]
    summaries = []
    for name, params in jobs:
        summaries.append(run_one(name, params))
        if (summaries[-1].get("progress_phase") or "") == "error":
            break
    out = DEFAULT_RESULTS / f"micro_summary_{DATE_FROM}_{DATE_TO}.json"
    out.write_text(json.dumps(summaries, indent=2, default=str))
    log(f"summary → {out}")
    print(json.dumps(summaries, indent=2, default=str), flush=True)
    return 0 if all((s.get("progress_phase") or "done") in ("done", "cancelled") for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
