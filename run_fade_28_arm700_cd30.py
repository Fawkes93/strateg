#!/usr/bin/env python3
"""After cd0+arm700 finishes: window 2.8 / arm 700 / cd 30 / hold 200 and 320."""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.runner import DEFAULT_RESULTS
from backtest.spike_fade_jobs import SpikeFadeJobParams
from run_fade_oat import execute, log, slim, write_summary

BASE = SpikeFadeJobParams(
    symbol="XAUUSD",
    date_from="2025-01-01",
    date_to="2026-08-01",
    window_sec=2.8,
    min_spike_pts=1100.0,
    tp_pct=0.0,
    sl_pct=0.0,
    tp_pts=3000.0,
    sl_pts=1000.0,
    trail_pts=500.0,
    trail_arm_pts=700.0,
    confirm_pts=0.0,
    confirm_timeout_sec=5.0,
    max_hold_sec=200.0,
    cooldown_sec=30.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=6,
    force_download=False,
)

JOBS = [
    ("28+arm700+cd30+hold200", {"max_hold_sec": 200.0}),
    ("28+arm700+cd30+hold320", {"max_hold_sec": 320.0}),
]


def predecessor_running() -> bool:
    me = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-fl", "run_fade_"], text=True)
    except subprocess.CalledProcessError:
        return False
    for line in out.splitlines():
        if "run_fade_28_arm700_cd30" in line:
            continue
        if "run_fade_sum_arm700" not in line and "run_fade_arm700_hold" not in line:
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if pid != me:
            return True
    return False


def main() -> int:
    while predecessor_running():
        log("waiting for cd0+arm700 (or leftover hold sweep) to finish…")
        time.sleep(30)
    log("predecessors done — starting 2.8 / arm700 / cd30")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_28_arm700_cd30_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"output → {out_dir}")

    rows: list[dict] = []
    n = len(JOBS)
    for i, (label, overrides) in enumerate(JOBS, 1):
        params = SpikeFadeJobParams(**asdict(BASE))
        for k, v in overrides.items():
            setattr(params, k, v)
        log(f"=== {i}/{n}  {label} ===")
        t0 = time.time()
        try:
            result = execute(params)
        except Exception as e:
            log(f"FAILED {label}: {e}")
            traceback.print_exc()
            rows.append({"label": label, "error": str(e)})
            write_summary(out_dir, rows)
            continue
        elapsed = round(time.time() - t0, 1)
        result["label"] = "base" if i == 1 else label
        result["changed"] = "max_hold_sec"
        result["elapsed_sec"] = elapsed
        slim_r = slim(result)
        (out_dir / f"{i:02d}_{label}.json").write_text(
            json.dumps(slim_r, indent=2, default=str)
        )
        rows.append(slim_r)
        write_summary(out_dir, rows)
        log(
            f"    → trades={result.get('trades')} avg={result.get('avg_pts')} "
            f"PF={result.get('profit_factor')} sum={result.get('sum_pts')} "
            f"to%={result.get('timeout_pct')} ({elapsed}s)"
        )
        gc.collect()

    write_summary(out_dir, rows)
    log(f"done. {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
