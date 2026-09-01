#!/usr/bin/env python3
"""Asia quiet-hours micro-fade probe (2025-01-01 → 2026-08-30)."""

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


def fade_job(**kw) -> MicroJobParams:
    p = MicroJobParams(
        symbol="XAUUSD",
        date_from=DATE_FROM,
        date_to=DATE_TO,
        window_sec=4.0,
        min_burst_pts=100.0,
        max_burst_pts=400.0,
        persist_frac=0.35,
        use_1m=True,
        min_1m_body=40.0,
        mode="fade",
        confirm_pts=40.0,
        confirm_timeout_sec=3.0,
        tp_frac=0.5,
        tp_cap_pts=80.0,
        sl_extra_pts=40.0,
        max_hold_sec=15.0,
        cooldown_sec=20.0,
        lag_sec=0.0,
        session="asia",
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
    log(f"START {name}  session={params.session} min={params.min_burst_pts}")
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
            line = f"  {name}  {p.get('pct')}%  {p.get('phase')}  {p.get('message')}  trades={p.get('trades')}"
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
        "win_pct", "tp_n", "sl_n", "timeout_n", "avg_pts", "sum_pts",
        "profit_factor", "ticks", "months", "date_from", "date_to",
    )
    row = {k: result.get(k) for k in keys}
    row.update({
        "name": name,
        "elapsed_sec": round(time.time() - t0, 1),
        "progress_phase": prog.get("phase"),
        "progress_error": prog.get("error"),
        "params": result.get("params"),
    })
    saved = result.get("saved_to")
    if saved:
        src = Path(saved)
        dest = DEFAULT_RESULTS / f"micro_fade_{name}_{DATE_FROM}_{DATE_TO}.json"
        if src.exists():
            dest.write_bytes(src.read_bytes())
            row["saved_to"] = str(dest)
    log(
        f"DONE {name}  trades={row.get('trades')} wr={row.get('win_pct')} "
        f"pf={row.get('profit_factor')} sum={row.get('sum_pts')} "
        f"elapsed={row.get('elapsed_sec')}s phase={row.get('progress_phase')}"
    )
    return row


def main() -> int:
    DEFAULT_RESULTS.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("asia-min100", fade_job()),
        ("asia-min50", fade_job(min_burst_pts=50.0, use_1m=False, confirm_pts=25.0)),
        ("asia-core-min50", fade_job(
            min_burst_pts=50.0, use_1m=False, confirm_pts=25.0, session="asia_core"
        )),
    ]
    rows = [run_one(name, params) for name, params in jobs]
    out = DEFAULT_RESULTS / f"micro_fade_probe_{DATE_FROM}_{DATE_TO}.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    log(f"probe summary → {out}")
    print(json.dumps(rows, indent=2, default=str), flush=True)
    bad = any((r.get("progress_phase") or "") == "error" for r in rows)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
