#!/usr/bin/env python3
"""Jan–Feb 2026 only: hunt a better sum than ~94k (those two months *are* the 94k)."""

from __future__ import annotations

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

# 94k combo restricted to the two months that made the money.
BASE = SpikeFadeJobParams(
    symbol="XAUUSD",
    date_from="2026-01-01",
    date_to="2026-03-01",
    window_sec=3.0,
    min_spike_pts=1100.0,
    tp_pct=0.0,
    sl_pct=0.0,
    tp_pts=3000.0,
    sl_pts=1000.0,
    trail_pts=500.0,
    trail_arm_pts=700.0,
    confirm_pts=0.0,
    confirm_timeout_sec=5.0,
    max_hold_sec=320.0,
    cooldown_sec=0.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=6,
    force_download=False,
)


def job_list() -> list[tuple[str, str, SpikeFadeJobParams]]:
    out = [("jf-base", "94k combo on Jan–Feb only", BASE)]

    def add(field, label, value):
        p = SpikeFadeJobParams(**asdict(BASE))
        setattr(p, field, value)
        out.append((label, field, p))

    for v in (2.5, 2.8, 3.2, 3.5, 4.0, 5.0):
        add("window_sec", f"win={v}", float(v))
    for v in (800, 900, 1000, 1200, 1300, 1500):
        add("min_spike_pts", f"min={v}", float(v))
    for v in (200, 240, 280, 360, 420, 480, 600, 900):
        add("max_hold_sec", f"hold={v}", float(v))
    for v in (700, 800, 900, 1200):
        add("sl_pts", f"sl={v}", float(v))
    for v in (350, 400, 600):
        add("trail_pts", f"trail={v}", float(v))
    for v in (500, 600, 800, 1000):
        add("trail_arm_pts", f"arm={v}", float(v))
    for v in (15.0, 30.0):
        add("cooldown_sec", f"cd={v}", float(v))
    for v in (0.0, 2.0):
        add("lag_sec", f"lag={v}", float(v))

    stacks = [
        ("win28+hold320", {"window_sec": 2.8}),
        ("win28+min1000+hold320", {"window_sec": 2.8, "min_spike_pts": 1000.0}),
        ("min1000+hold400", {"min_spike_pts": 1000.0, "max_hold_sec": 400.0}),
        ("min1200+hold320", {"min_spike_pts": 1200.0}),
        ("sl800+hold400", {"sl_pts": 800.0, "max_hold_sec": 400.0}),
        ("win35+min1000", {"window_sec": 3.5, "min_spike_pts": 1000.0}),
        ("arm900+hold400", {"trail_arm_pts": 900.0, "max_hold_sec": 400.0}),
        ("win28+cd0+arm700", {"window_sec": 2.8, "cooldown_sec": 0.0}),
    ]
    for label, ov in stacks:
        p = SpikeFadeJobParams(**asdict(BASE))
        for k, v in ov.items():
            setattr(p, k, v)
        out.append((label, "stack", p))
    return out


def main() -> int:
    jobs = job_list()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_janfeb_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"Jan–Feb 2026 only · {len(jobs)} jobs → {out_dir}")

    rows: list[dict] = []
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== jf {i}/{n}  {label}  ({changed}) ===")
        t0 = time.time()
        try:
            result = execute(params)
        except Exception as e:
            log(f"FAILED {label}: {e}")
            traceback.print_exc()
            rows.append({"label": label, "changed": changed, "error": str(e)})
            write_summary(out_dir, rows)
            continue
        elapsed = round(time.time() - t0, 1)
        result["label"] = "base" if i == 1 else label
        result["changed"] = changed
        result["elapsed_sec"] = elapsed
        slim_r = slim(result)
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
    log(f"Jan–Feb done. {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
