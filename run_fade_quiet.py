#!/usr/bin/env python3
"""
Quiet-month spike-fade search.

Only months that printed ≤6 trades on the crisis combo (1100 / 3s / arm 700).
Goal: find a detect+exit setup that actually trades when gold is calm.

  caffeinate -dims nohup python -u run_fade_quiet.py >> results/fade_quiet.log 2>&1 &
"""

from __future__ import annotations

import calendar
import gc
import json
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

# Months with ≤6 trades on the 94k combo. Skip crisis / red violent months.
QUIET_YM = [
    (2025, 1),
    (2025, 2),
    (2025, 3),
    (2025, 4),
    (2025, 5),
    (2025, 6),
    (2025, 7),
    (2025, 8),
    (2025, 9),
    (2025, 11),
    (2025, 12),
    (2026, 5),
]


def quiet_chunks() -> list[tuple[str, str]]:
    out = []
    for y, m in QUIET_YM:
        a = f"{y:04d}-{m:02d}-01"
        if m == 12:
            b = f"{y + 1:04d}-01-01"
        else:
            b = f"{y:04d}-{m + 1:02d}-01"
        out.append((a, b))
    return out


# Starting guess for a calm tape (smaller / slower spikes).
BASE = SpikeFadeJobParams(
    symbol="XAUUSD",
    date_from="2025-01-01",
    date_to="2026-06-01",
    window_sec=5.0,
    min_spike_pts=600.0,
    tp_pct=0.0,
    sl_pct=0.0,
    tp_pts=1500.0,
    sl_pts=800.0,
    trail_pts=400.0,
    trail_arm_pts=0.0,
    confirm_pts=0.0,
    confirm_timeout_sec=5.0,
    max_hold_sec=240.0,
    cooldown_sec=15.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=6,
    force_download=False,
)


def jobs() -> list[tuple[str, str, SpikeFadeJobParams]]:
    out: list[tuple[str, str, SpikeFadeJobParams]] = [
        ("qbase", "quiet base win5/min600", BASE),
    ]

    def add(field: str, label: str, value) -> None:
        p = SpikeFadeJobParams(**asdict(BASE))
        setattr(p, field, value)
        out.append((label, field, p))

    # Detect: this is the whole point of quiet months
    for v in (300, 400, 500, 700, 800, 900, 1000, 1100):
        add("min_spike_pts", f"min={v}", float(v))
    for v in (2.8, 3.5, 4.0, 6.0, 8.0, 10.0, 15.0):
        add("window_sec", f"win={v}", float(v))

    # Exits around the quiet guess
    for v in (500, 600, 1000, 1200):
        add("sl_pts", f"sl={v}", float(v))
    for v in (250, 350, 500, 600):
        add("trail_pts", f"trail={v}", float(v))
    for v in (400, 600, 800):
        add("trail_arm_pts", f"arm={v}", float(v))
    for v in (1000, 2000, 2500):
        add("tp_pts", f"tp={v}", float(v))
    for v in (180, 320, 480):
        add("max_hold_sec", f"hold={v}", float(v))
    for v in (0.0, 2.0):
        add("lag_sec", f"lag={v}", float(v))
    for v in (0.0, 30.0):
        add("cooldown_sec", f"cd={v}", float(v))

    stacks = [
        ("min400+win8", {"min_spike_pts": 400.0, "window_sec": 8.0}),
        ("min500+win8", {"min_spike_pts": 500.0, "window_sec": 8.0}),
        ("min500+win10", {"min_spike_pts": 500.0, "window_sec": 10.0}),
        ("min700+win8", {"min_spike_pts": 700.0, "window_sec": 8.0}),
        ("min400+win5", {"min_spike_pts": 400.0, "window_sec": 5.0}),
        ("min800+win5", {"min_spike_pts": 800.0, "window_sec": 5.0}),
        ("min600+sl600", {"sl_pts": 600.0}),
        ("min500+sl600+win8", {"min_spike_pts": 500.0, "window_sec": 8.0, "sl_pts": 600.0}),
        ("min600+trail250", {"trail_pts": 250.0}),
        ("min400+tp1000+sl600", {"min_spike_pts": 400.0, "tp_pts": 1000.0, "sl_pts": 600.0}),
        ("crisis-ctrl", {
            "window_sec": 3.0,
            "min_spike_pts": 1100.0,
            "tp_pts": 3000.0,
            "sl_pts": 1000.0,
            "trail_pts": 500.0,
            "trail_arm_pts": 700.0,
            "max_hold_sec": 320.0,
            "cooldown_sec": 0.0,
        }),
    ]
    for label, ov in stacks:
        p = SpikeFadeJobParams(**asdict(BASE))
        for k, v in ov.items():
            setattr(p, k, v)
        out.append((label, "stack", p))
    return out


def main() -> int:
    chunks = quiet_chunks()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_quiet_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    job_list = jobs()
    log(f"quiet months: {len(chunks)}  jobs: {len(job_list)}")
    log(f"output → {out_dir}")
    (out_dir / "README.md").write_text(
        "Quiet-month only: "
        + ", ".join(f"{y}-{m:02d}" for y, m in QUIET_YM)
        + "\nSee fade_march_june_quiet_months.md for why March/June are excluded.\n"
    )

    rows: list[dict] = []
    n = len(job_list)
    for i, (label, changed, params) in enumerate(job_list, 1):
        log(f"=== q {i}/{n}  {label}  ({changed}) ===")
        t0 = time.time()
        try:
            result = execute(params, chunks=chunks)
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
        result["label"] = "base" if i == 1 else label
        result["changed"] = changed
        result["elapsed_sec"] = elapsed
        result["quiet_months"] = [f"{y}-{m:02d}" for y, m in QUIET_YM]
        slim_r = slim(result)
        slim_r["quiet_months"] = result["quiet_months"]
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)
        (out_dir / f"{i:03d}_{safe}.json").write_text(
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
    log(f"quiet sweep done. {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
