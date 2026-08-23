#!/usr/bin/env python3
"""Re-run the sum-winner and print +/− trades per month."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.runner import DEFAULT_RESULTS
from backtest.spike_fade_jobs import SpikeFadeJobParams
from run_fade_oat import execute, log

PARAMS = SpikeFadeJobParams(
    symbol="XAUUSD",
    date_from="2025-01-01",
    date_to="2026-08-01",
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
)


def main() -> int:
    log("re-running sum winner for monthly breakdown…")
    res = execute(PARAMS)
    rows = res.get("rows") or []
    by = defaultdict(
        lambda: {"n": 0, "pos": 0, "neg": 0, "flat": 0, "sum": 0.0}
    )
    for t in rows:
        k = str(t.get("entry_ts") or "unknown")[:7]
        pts = float(t.get("pts") or 0)
        by[k]["n"] += 1
        by[k]["sum"] += pts
        if pts > 1e-9:
            by[k]["pos"] += 1
        elif pts < -1e-9:
            by[k]["neg"] += 1
        else:
            by[k]["flat"] += 1

    pos = sum(1 for t in rows if float(t.get("pts") or 0) > 1e-9)
    neg = sum(1 for t in rows if float(t.get("pts") or 0) < -1e-9)
    flat = len(rows) - pos - neg
    out = {
        "params": asdict(PARAMS),
        "totals": {
            "trades": len(rows),
            "positive": pos,
            "negative": neg,
            "flat": flat,
            "sum_pts": res.get("sum_pts"),
            "avg_pts": res.get("avg_pts"),
            "win_pct": res.get("win_pct"),
            "profit_factor": res.get("profit_factor"),
        },
        "by_month": {k: by[k] for k in sorted(by)},
    }
    path = DEFAULT_RESULTS / "fade_cd0_arm700_hold320_by_month.json"
    path.write_text(json.dumps(out, indent=2, default=str))
    log(f"wrote {path}")
    print(
        f"\nTOTAL  n={len(rows)}  +{pos}  -{neg}  flat={flat}  "
        f"win%={res.get('win_pct')}  sum={res.get('sum_pts')}"
    )
    print(f"{'month':8} {'n':>4} {'pos':>4} {'neg':>4} {'flat':>4} {'win%':>6} {'sum':>10}")
    for k in sorted(by):
        m = by[k]
        wp = 100.0 * m["pos"] / m["n"] if m["n"] else 0
        print(
            f"{k:8} {m['n']:4} {m['pos']:4} {m['neg']:4} {m['flat']:4} "
            f"{wp:5.1f}% {m['sum']:10.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
