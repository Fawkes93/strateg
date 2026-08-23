#!/usr/bin/env python3
"""
2025 only — hunt ≥20k sum around the user's best calm-year combo
(29 trades, PF 2.37, sum 6603: min 1000 / win 3 / TP 750 / SL 750 / trail 500 / arm 500 / hold 250 / cd 30 / lag 1).

Longer windows + lower min to get more tickets without the 2026 crisis months.
"""

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

BASE = SpikeFadeJobParams(
    symbol="XAUUSD",
    date_from="2025-01-01",
    date_to="2026-01-01",
    window_sec=3.0,
    min_spike_pts=1000.0,
    tp_pct=0.0,
    sl_pct=0.0,
    tp_pts=750.0,
    sl_pts=750.0,
    trail_pts=500.0,
    trail_arm_pts=500.0,
    confirm_pts=0.0,
    confirm_timeout_sec=5.0,
    max_hold_sec=250.0,
    cooldown_sec=30.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=4,
    force_download=False,
)


def job_list():
    out = [("y25-base", "screenshot 2025 combo", BASE)]

    def add(field, label, value):
        p = SpikeFadeJobParams(**asdict(BASE))
        setattr(p, field, value)
        out.append((label, field, p))

    for v in (4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0):
        add("window_sec", f"win={v}", float(v))
    for v in (500, 600, 700, 800, 900, 1100):
        add("min_spike_pts", f"min={v}", float(v))
    for v in (400, 500, 600, 1000, 1200):
        add("tp_pts", f"tp={v}", float(v))
    for v in (500, 600, 1000, 1200):
        add("sl_pts", f"sl={v}", float(v))
    for v in (300, 400, 600, 750):
        add("trail_pts", f"trail={v}", float(v))
    for v in (0.0, 400, 700, 800):
        add("trail_arm_pts", f"arm={v}", float(v))
    for v in (180, 320, 400, 500, 600, 900):
        add("max_hold_sec", f"hold={v}", float(v))
    for v in (0.0, 15.0, 60.0, 90.0):
        add("cooldown_sec", f"cd={v}", float(v))
    for v in (0.0, 2.0):
        add("lag_sec", f"lag={v}", float(v))

    stacks = [
        ("win8+min700", {"window_sec": 8.0, "min_spike_pts": 700.0}),
        ("win8+min600", {"window_sec": 8.0, "min_spike_pts": 600.0}),
        ("win10+min600", {"window_sec": 10.0, "min_spike_pts": 600.0}),
        ("win10+min800", {"window_sec": 10.0, "min_spike_pts": 800.0}),
        ("win5+min700", {"window_sec": 5.0, "min_spike_pts": 700.0}),
        ("win5+min800", {"window_sec": 5.0, "min_spike_pts": 800.0}),
        ("win8+min700+tp500", {"window_sec": 8.0, "min_spike_pts": 700.0, "tp_pts": 500.0}),
        ("win8+min700+hold400", {"window_sec": 8.0, "min_spike_pts": 700.0, "max_hold_sec": 400.0}),
        ("win10+min500", {"window_sec": 10.0, "min_spike_pts": 500.0}),
        ("win6+min800+cd0", {"window_sec": 6.0, "min_spike_pts": 800.0, "cooldown_sec": 0.0}),
        ("win8+min700+sl600", {"window_sec": 8.0, "min_spike_pts": 700.0, "sl_pts": 600.0}),
        ("win12+min600", {"window_sec": 12.0, "min_spike_pts": 600.0}),
        ("win15+min700", {"window_sec": 15.0, "min_spike_pts": 700.0}),
        ("win8+min800+hold500", {"window_sec": 8.0, "min_spike_pts": 800.0, "max_hold_sec": 500.0}),
        ("min700+tp500+hold400", {"min_spike_pts": 700.0, "tp_pts": 500.0, "max_hold_sec": 400.0}),
        ("win8+min600+tp600", {"window_sec": 8.0, "min_spike_pts": 600.0, "tp_pts": 600.0}),
        ("win5+min600+cd0", {"window_sec": 5.0, "min_spike_pts": 600.0, "cooldown_sec": 0.0}),
        ("win8+min700+arm400", {"window_sec": 8.0, "min_spike_pts": 700.0, "trail_arm_pts": 400.0}),
        ("win10+min700+trail400", {"window_sec": 10.0, "min_spike_pts": 700.0, "trail_pts": 400.0}),
        ("win6+min700+sl500", {"window_sec": 6.0, "min_spike_pts": 700.0, "sl_pts": 500.0}),
        ("win8+min900", {"window_sec": 8.0, "min_spike_pts": 900.0}),
        ("win4+min700", {"window_sec": 4.0, "min_spike_pts": 700.0}),
        ("win5+min500", {"window_sec": 5.0, "min_spike_pts": 500.0}),
        ("win10+min700+cd15", {"window_sec": 10.0, "min_spike_pts": 700.0, "cooldown_sec": 15.0}),
        ("win8+min600+hold600", {"window_sec": 8.0, "min_spike_pts": 600.0, "max_hold_sec": 600.0}),
        ("win8+min800+tp400", {"window_sec": 8.0, "min_spike_pts": 800.0, "tp_pts": 400.0}),
        ("win10+min700+tp750", {"window_sec": 10.0, "min_spike_pts": 700.0}),
        ("win15+min500", {"window_sec": 15.0, "min_spike_pts": 500.0}),
        ("win12+min800", {"window_sec": 12.0, "min_spike_pts": 800.0}),
        ("win5+min700+cd0", {"window_sec": 5.0, "min_spike_pts": 700.0, "cooldown_sec": 0.0}),
        ("win8+min700+hold600", {"window_sec": 8.0, "min_spike_pts": 700.0, "max_hold_sec": 600.0}),
        ("win8+min700+tp500+sl500", {"window_sec": 8.0, "min_spike_pts": 700.0, "tp_pts": 500.0, "sl_pts": 500.0}),
        ("win8+min700+lag0", {"window_sec": 8.0, "min_spike_pts": 700.0, "lag_sec": 0.0}),
        ("win10+min600+hold480", {"window_sec": 10.0, "min_spike_pts": 600.0, "max_hold_sec": 480.0}),
        ("win8+min700+cd0", {"window_sec": 8.0, "min_spike_pts": 700.0, "cooldown_sec": 0.0}),
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
    out_dir = DEFAULT_RESULTS / f"fade_2025_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"2025-only hunt (≥20k sum) · {len(jobs)} jobs → {out_dir}")
    (out_dir / "README.md").write_text(
        "2025-01-01 → 2026-01-01 only. Seed = UI combo sum 6603 / PF 2.37.\n"
        "Target: sum ≥ 20_000 pts for the calendar year.\n"
    )

    rows = []
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== y25 {i}/{n}  {label}  ({changed}) ===")
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
        hit = float(result.get("sum_pts") or 0) >= 20000
        log(
            f"    → n={result.get('trades')} avg={result.get('avg_pts')} "
            f"PF={result.get('profit_factor')} sum={result.get('sum_pts')}"
            f"{'  *** ≥20k ***' if hit else ''} ({elapsed}s)"
        )
        gc.collect()

    write_summary(out_dir, rows)
    best = max(
        (r for r in rows if r.get("sum_pts") is not None),
        key=lambda r: float(r["sum_pts"]),
        default=None,
    )
    if best:
        log(
            f"best sum {best.get('sum_pts')}  {best.get('label')}  "
            f"n={best.get('trades')} PF={best.get('profit_factor')}"
        )
    log(f"2025 hunt done. {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
