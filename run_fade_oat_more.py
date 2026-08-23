#!/usr/bin/env python3
"""
Phase 2 overnight fade sweep. Waits for run_fade_oat.py to finish, then
runs ~60 more combos: extra one-knob neighbors + a few stacked winners.
"""

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
from run_fade_oat import BASE, execute, log, slim, write_summary

# Extra one-knob vs original screenshot base (not already in phase 1).
OAT: list[tuple[str, str, object]] = [
    # min — higher looked better
    ("min_spike_pts", "min=1050", 1050.0),
    ("min_spike_pts", "min=1150", 1150.0),
    ("min_spike_pts", "min=1250", 1250.0),
    ("min_spike_pts", "min=1350", 1350.0),
    ("min_spike_pts", "min=1400", 1400.0),
    ("min_spike_pts", "min=1500", 1500.0),
    ("min_spike_pts", "min=1600", 1600.0),
    ("min_spike_pts", "min=1800", 1800.0),
    ("min_spike_pts", "min=2000", 2000.0),
    # SL — 800 already beat 1000
    ("sl_pts", "sl=600", 600.0),
    ("sl_pts", "sl=700", 700.0),
    ("sl_pts", "sl=900", 900.0),
    ("sl_pts", "sl=1100", 1100.0),
    ("sl_pts", "sl=1300", 1300.0),
    ("sl_pts", "sl=1400", 1400.0),
    ("sl_pts", "sl=1600", 1600.0),
    ("sl_pts", "sl=1800", 1800.0),
    ("sl_pts", "sl=2000", 2000.0),
    # trail
    ("trail_pts", "trail=250", 250.0),
    ("trail_pts", "trail=300", 300.0),
    ("trail_pts", "trail=350", 350.0),
    ("trail_pts", "trail=450", 450.0),
    ("trail_pts", "trail=550", 550.0),
    ("trail_pts", "trail=650", 650.0),
    ("trail_pts", "trail=800", 800.0),
    ("trail_pts", "trail=1000", 1000.0),
    # hold
    ("max_hold_sec", "hold=120", 120.0),
    ("max_hold_sec", "hold=140", 140.0),
    ("max_hold_sec", "hold=180", 180.0),
    ("max_hold_sec", "hold=220", 220.0),
    ("max_hold_sec", "hold=260", 260.0),
    ("max_hold_sec", "hold=300", 300.0),
    ("max_hold_sec", "hold=360", 360.0),
    # window
    ("window_sec", "win=2.0", 2.0),
    ("window_sec", "win=2.2", 2.2),
    ("window_sec", "win=2.8", 2.8),
    ("window_sec", "win=3.2", 3.2),
    ("window_sec", "win=4.0", 4.0),
    ("window_sec", "win=5.0", 5.0),
    # lag (float ok)
    ("lag_sec", "lag=0.5", 0.5),
    ("lag_sec", "lag=1.5", 1.5),
    # TP rarely hits; still map it
    ("tp_pts", "tp=2000", 2000.0),
    ("tp_pts", "tp=2200", 2200.0),
    ("tp_pts", "tp=2800", 2800.0),
    ("tp_pts", "tp=3200", 3200.0),
    ("tp_pts", "tp=4000", 4000.0),
    ("tp_pts", "tp=5000", 5000.0),
    # cooldown
    ("cooldown_sec", "cd=0", 0.0),
    ("cooldown_sec", "cd=10", 10.0),
    ("cooldown_sec", "cd=20", 20.0),
    ("cooldown_sec", "cd=45", 45.0),
    ("cooldown_sec", "cd=90", 90.0),
    ("cooldown_sec", "cd=120", 120.0),
    # weekend skip (not in phase 1)
    ("weekend_blackout_min", "wknd=0", 0.0),
    ("weekend_blackout_min", "wknd=5", 5.0),
    ("weekend_blackout_min", "wknd=15", 15.0),
    ("weekend_blackout_min", "wknd=20", 20.0),
]

# Two knobs — only stacks we already saw help (higher min, tighter SL).
STACKS: list[tuple[str, str, dict]] = [
    ("min1300+sl800", "min+sl", {"min_spike_pts": 1300.0, "sl_pts": 800.0}),
    ("min1200+sl800", "min+sl", {"min_spike_pts": 1200.0, "sl_pts": 800.0}),
    ("min1400+sl800", "min+sl", {"min_spike_pts": 1400.0, "sl_pts": 800.0}),
]


def phase1_running() -> bool:
    me = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-fl", "run_fade_oat"], text=True)
    except subprocess.CalledProcessError:
        return False
    for line in out.splitlines():
        if "run_fade_oat_more" in line:
            continue
        if "run_fade_oat.py" not in line:
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if pid != me:
            return True
    return False


def wait_phase1() -> None:
    while phase1_running():
        log("phase 1 still running — waiting 45s")
        time.sleep(45)
    log("phase 1 finished — starting phase 2")


def load_base_row() -> dict | None:
    roots = sorted(DEFAULT_RESULTS.glob("fade_oat_20*"), reverse=True)
    for folder in roots:
        p = folder / "01_base.json"
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return None


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_oat_p2_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"phase 2 output → {out_dir}")
    log(f"queued {len(OAT)} OAT + {len(STACKS)} stacks = {len(OAT) + len(STACKS)}")

    wait_phase1()

    jobs: list[tuple[str, str, SpikeFadeJobParams]] = []
    for field, label, value in OAT:
        p = SpikeFadeJobParams(**asdict(BASE))
        setattr(p, field, value)
        jobs.append((label, field, p))
    for label, changed, overrides in STACKS:
        p = SpikeFadeJobParams(**asdict(BASE))
        for k, v in overrides.items():
            setattr(p, k, v)
        jobs.append((label, changed, p))

    rows: list[dict] = []
    base_row = load_base_row()
    if base_row:
        rows.append(base_row)

    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== p2 {i}/{n}  {label}  ({changed}) ===")
        t0 = time.time()
        try:
            result = execute(params)
        except Exception as e:
            log(f"FAILED {label}: {e}")
            traceback.print_exc()
            rows.append(
                {
                    "label": label,
                    "changed": changed,
                    "error": str(e),
                    "elapsed_sec": round(time.time() - t0, 1),
                }
            )
            write_summary(out_dir, rows)
            continue
        elapsed = round(time.time() - t0, 1)
        result["label"] = label
        result["changed"] = changed
        result["elapsed_sec"] = elapsed
        slim_r = slim(result)
        safe = label.replace("=", "_").replace("+", "_")
        (out_dir / f"{i:02d}_{safe}.json").write_text(
            json.dumps(slim_r, indent=2, default=str)
        )
        rows.append(slim_r)
        write_summary(out_dir, rows)
        log(
            f"    → trades={result.get('trades')} avg={result.get('avg_pts')} "
            f"PF={result.get('profit_factor')} sum={result.get('sum_pts')} "
            f"({elapsed}s)"
        )
        gc.collect()

    write_summary(out_dir, rows)
    log(f"phase 2 done. summary: {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
