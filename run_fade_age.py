#!/usr/bin/env python3
"""
Follow-up: max_extreme_age_sec on the quiet-2025 tape.

Waits for run_fade_quiet2025.py to finish, then runs the long-window
detects again with an age gate (only fade if the window high/low is fresh).

  /Users/carauslivian/reaktor/.venv/bin/python3 -u run_fade_age.py
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, ROOT)

from backtest.runner import DEFAULT_RESULTS
from run_fade_oat import execute, log
from run_fade_quiet2025 import SEED, _clone, decorate, slim_q, write_summary


def quiet2025_running() -> bool:
    me = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-fl", "run_fade_quiet2025"], text=True)
    except subprocess.CalledProcessError:
        return False
    for line in out.splitlines():
        if "run_fade_age" in line:
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if pid != me:
            return True
    return False


def job_list():
    stacks = [
        ("win30+min400+age1", {"window_sec": 30.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 1.0}),
        ("win30+min400+age2", {"window_sec": 30.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 2.0}),
        ("win30+min400+age3", {"window_sec": 30.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 3.0}),
        ("win60+min400+age2", {"window_sec": 60.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 2.0}),
        ("win60+min400+age3", {"window_sec": 60.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 3.0}),
        ("win60+min400+age5", {"window_sec": 60.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 5.0}),
        ("win15+min400+age2", {"window_sec": 15.0, "min_spike_pts": 400.0, "max_extreme_age_sec": 2.0}),
        (
            "win60+min400+small+age3",
            {
                "window_sec": 60.0,
                "min_spike_pts": 400.0,
                "max_extreme_age_sec": 3.0,
                "tp_pts": 600.0,
                "sl_pts": 400.0,
                "trail_pts": 300.0,
                "trail_arm_pts": 400.0,
                "max_hold_sec": 480.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win30+min500+age3",
            {"window_sec": 30.0, "min_spike_pts": 500.0, "max_extreme_age_sec": 3.0},
        ),
        (
            "win60+min500+age3",
            {"window_sec": 60.0, "min_spike_pts": 500.0, "max_extreme_age_sec": 3.0},
        ),
    ]
    return [(label, "age", _clone(ov)) for label, ov in stacks]


def main() -> int:
    while quiet2025_running():
        log("quiet-2025 still running — waiting 60s")
        time.sleep(60)

    jobs = job_list()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_age_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"extreme-age follow-up · {len(jobs)} jobs → {out_dir}")
    (out_dir / "README.md").write_text(
        "max_extreme_age_sec on Jan–Oct 2025.\n"
        "Same seed exits as the violent PF~3 preset unless the label says small.\n"
        "Compare to win30+min400 / win60+min400 from fade_quiet2025 (age=0).\n"
    )

    rows = []
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== age {i}/{n}  {label} ===")
        t0 = time.time()
        try:
            result = decorate(execute(params))
        except Exception as e:
            log(f"FAILED {label}: {e}")
            traceback.print_exc()
            rows.append({"label": label, "changed": changed, "error": str(e)})
            write_summary(out_dir, rows)
            continue
        elapsed = round(time.time() - t0, 1)
        result["label"] = label
        result["changed"] = changed
        result["elapsed_sec"] = elapsed
        slim_r = slim_q(result)
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)
        (out_dir / f"{i:03d}_{safe}.json").write_text(
            json.dumps(slim_r, indent=2, default=str)
        )
        rows.append(slim_r)
        write_summary(out_dir, rows)
        mark = "  *** 1/week ***" if slim_r.get("hit_1_per_week") else ""
        log(
            f"    → n={result.get('trades')} q={result.get('quiet_trades')} "
            f"q/wk={result.get('quiet_tpw')} PF={result.get('profit_factor')} "
            f"sum={result.get('sum_pts')}{mark} ({elapsed}s)"
        )
        gc.collect()

    write_summary(out_dir, rows)
    log(f"age follow-up done. {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
