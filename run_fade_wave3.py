#!/usr/bin/env python3
"""
Wave 3: new-best base (window 2.8) + confirm bounce + split trail arm.

Detached overnight. One change at a time, plus a few labeled stacks.
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
from run_fade_oat import execute, log, slim, write_summary

# Screenshot / OAT winner: win 2.8 · min 1100 · TP 3000 · SL 1000 · trail 500 · lag 1
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
    trail_arm_pts=0.0,
    confirm_pts=0.0,
    confirm_timeout_sec=5.0,
    max_hold_sec=200.0,
    cooldown_sec=30.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=6,
    force_download=False,
)

OAT: list[tuple[str, str, object]] = [
    ("confirm_pts", "confirm=50", 50.0),
    ("confirm_pts", "confirm=100", 100.0),
    ("confirm_pts", "confirm=150", 150.0),
    ("confirm_pts", "confirm=200", 200.0),
    ("confirm_pts", "confirm=300", 300.0),
    ("confirm_pts", "confirm=400", 400.0),
    ("confirm_pts", "confirm=500", 500.0),
    ("trail_arm_pts", "arm=300", 300.0),
    ("trail_arm_pts", "arm=400", 400.0),
    ("trail_arm_pts", "arm=600", 600.0),
    ("trail_arm_pts", "arm=700", 700.0),
    ("trail_arm_pts", "arm=800", 800.0),
    ("trail_arm_pts", "arm=1000", 1000.0),
    ("trail_arm_pts", "arm=1200", 1200.0),
    ("min_spike_pts", "min=1150", 1150.0),
    ("min_spike_pts", "min=1300", 1300.0),
    ("min_spike_pts", "min=1350", 1350.0),
    ("min_spike_pts", "min=1400", 1400.0),
    ("min_spike_pts", "min=1500", 1500.0),
    ("sl_pts", "sl=700", 700.0),
    ("sl_pts", "sl=800", 800.0),
    ("sl_pts", "sl=900", 900.0),
    ("trail_pts", "trail=350", 350.0),
    ("trail_pts", "trail=400", 400.0),
    ("trail_pts", "trail=600", 600.0),
    ("window_sec", "win=2.6", 2.6),
    ("window_sec", "win=2.9", 2.9),
    ("window_sec", "win=3.0", 3.0),
    ("tp_pts", "tp=3500", 3500.0),
    ("cooldown_sec", "cd=0", 0.0),
    ("confirm_timeout_sec", "ctime=3", 3.0),
    ("confirm_timeout_sec", "ctime=8", 8.0),
]

STACKS: list[tuple[str, str, dict]] = [
    ("c200+min1350", "confirm+min", {"confirm_pts": 200.0, "min_spike_pts": 1350.0}),
    ("c200+sl800", "confirm+sl", {"confirm_pts": 200.0, "sl_pts": 800.0}),
    ("c150+min1300", "confirm+min", {"confirm_pts": 150.0, "min_spike_pts": 1300.0}),
    ("arm700+c200", "arm+confirm", {"trail_arm_pts": 700.0, "confirm_pts": 200.0}),
    ("min1350+sl800", "min+sl", {"min_spike_pts": 1350.0, "sl_pts": 800.0}),
    ("min1500+c200", "min+confirm", {"min_spike_pts": 1500.0, "confirm_pts": 200.0}),
    ("min1350+arm700", "min+arm", {"min_spike_pts": 1350.0, "trail_arm_pts": 700.0}),
    ("c200+trail350", "confirm+trail", {"confirm_pts": 200.0, "trail_pts": 350.0}),
]


def other_sweeps_running() -> bool:
    me = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-fl", "run_fade"], text=True)
    except subprocess.CalledProcessError:
        return False
    for line in out.splitlines():
        if "run_fade_wave3" in line:
            continue
        if "run_fade_oat" not in line and "run_fade_wave" not in line:
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if pid != me:
            return True
    return False


def wait_idle() -> None:
    while other_sweeps_running():
        log("another fade sweep still running — waiting 45s")
        time.sleep(45)
    log("starting wave 3")


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_oat_w3_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    n_jobs = 1 + len(OAT) + len(STACKS)
    log(f"wave 3 output → {out_dir}")
    log(f"queued base + {len(OAT)} OAT + {len(STACKS)} stacks = {n_jobs}")
    wait_idle()

    jobs: list[tuple[str, str, SpikeFadeJobParams]] = [
        ("base", "window 2.8 screenshot combo", BASE),
    ]
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
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== w3 {i}/{n}  {label}  ({changed}) ===")
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
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)
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
    log(f"wave 3 done. summary: {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
