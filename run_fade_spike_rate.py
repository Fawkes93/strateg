#!/usr/bin/env python3
"""Count 1100-pt / 3s spike *detections* per hour (not trades).

An open trade blocks new entries, so trade counts understate how busy the tape was.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, List, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.config import point_size
from backtest.runner import DEFAULT_RESULTS, load_ticks
from backtest.spike_fade import _detect, to_utc
from run_fade_oat import log

WINDOW = 3.0
MIN_PTS = 1100.0
MONTHS = [
    ("2026-01-01", "2026-02-01", "2026-01"),
    ("2026-02-01", "2026-03-01", "2026-02"),
    ("2026-03-01", "2026-04-01", "2026-03"),
    ("2026-05-01", "2026-06-01", "2026-05"),  # quiet contrast
]


def detect_times(ticks) -> List[float]:
    ps = point_size("XAU/USD")
    dq: Deque[Tuple[float, float]] = deque()
    win_hi, win_lo = float("-inf"), float("inf")
    suppress_until = 0.0
    events: List[float] = []
    for t in ticks:
        ts = t.ts if t.ts.tzinfo is not None else to_utc(t.ts)
        epoch = ts.timestamp()
        px = t.mid
        dq.append((epoch, px))
        if px > win_hi:
            win_hi = px
        if px < win_lo:
            win_lo = px
        cutoff = epoch - WINDOW
        popped = False
        while dq and dq[0][0] < cutoff:
            dq.popleft()
            popped = True
        if popped and dq:
            prices = [p for _, p in dq]
            win_hi = max(prices)
            win_lo = min(prices)
        elif not dq:
            win_hi, win_lo = float("-inf"), float("inf")
        if epoch < suppress_until:
            continue
        hit = _detect(dq, ps, MIN_PTS, WINDOW, win_hi, win_lo)
        if hit is None:
            continue
        events.append(epoch)
        suppress_until = epoch + WINDOW
    return events


def summarize(label: str, events: List[float]) -> dict:
    by_hour: dict[str, int] = defaultdict(int)
    by_day: dict[str, int] = defaultdict(int)
    for e in events:
        dt = datetime.fromtimestamp(e, tz=timezone.utc)
        by_hour[dt.strftime("%Y-%m-%d %H")] += 1
        by_day[dt.strftime("%Y-%m-%d")] += 1
    hour_counts = sorted(by_hour.values())
    day_counts = sorted(by_day.values())
    n_h = len(hour_counts)

    def pct(xs, p):
        if not xs:
            return 0
        i = min(len(xs) - 1, max(0, int(round((p / 100.0) * (len(xs) - 1)))))
        return xs[i]

    top_hours = sorted(by_hour.items(), key=lambda kv: -kv[1])[:8]
    top_days = sorted(by_day.items(), key=lambda kv: -kv[1])[:8]
    return {
        "month": label,
        "detects": len(events),
        "hours_with_detect": n_h,
        "days_with_detect": len(day_counts),
        "per_hour_among_active": {
            "mean": round(sum(hour_counts) / n_h, 2) if n_h else 0,
            "median": pct(hour_counts, 50),
            "p90": pct(hour_counts, 90),
            "max": hour_counts[-1] if hour_counts else 0,
        },
        "per_day_among_active": {
            "mean": round(sum(day_counts) / len(day_counts), 1) if day_counts else 0,
            "median": pct(day_counts, 50),
            "max": day_counts[-1] if day_counts else 0,
        },
        "top_hours": [{"hour_utc": h, "n": n} for h, n in top_hours],
        "top_days": [{"day": d, "n": n} for d, n in top_days],
        # hours with >= 3 / >= 5 detects — the “several per hour” bar
        "hours_ge_3": sum(1 for c in hour_counts if c >= 3),
        "hours_ge_5": sum(1 for c in hour_counts if c >= 5),
        "hours_ge_10": sum(1 for c in hour_counts if c >= 10),
    }


def main() -> int:
    out = {"window_sec": WINDOW, "min_spike_pts": MIN_PTS, "months": []}
    for a, b, label in MONTHS:
        log(f"spike-rate {label} {a}→{b}")
        ticks = load_ticks(symbol="XAUUSD", date_from=a, date_to=b)
        ev = detect_times(ticks)
        rec = summarize(label, ev)
        out["months"].append(rec)
        log(
            f"    {label}: {rec['detects']} detects · "
            f"active hours {rec['hours_with_detect']} · "
            f"median/p90/max per active hour "
            f"{rec['per_hour_among_active']['median']}/"
            f"{rec['per_hour_among_active']['p90']}/"
            f"{rec['per_hour_among_active']['max']} · "
            f"hours≥3 {rec['hours_ge_3']} ≥5 {rec['hours_ge_5']}"
        )
        del ticks
    path = DEFAULT_RESULTS / "fade_spike_rate.json"
    path.write_text(json.dumps(out, indent=2))
    md = ["# 1100-pt / 3s spike detections per hour (not trades)", ""]
    for rec in out["months"]:
        h = rec["per_hour_among_active"]
        md.append(f"## {rec['month']}")
        md.append(
            f"- detects **{rec['detects']}** in **{rec['hours_with_detect']}** UTC hours "
            f"({rec['days_with_detect']} days)"
        )
        md.append(
            f"- per *active* hour: median **{h['median']}**, p90 **{h['p90']}**, "
            f"max **{h['max']}**, mean {h['mean']}"
        )
        md.append(
            f"- hours with ≥3 / ≥5 / ≥10 detects: "
            f"{rec['hours_ge_3']} / {rec['hours_ge_5']} / {rec['hours_ge_10']}"
        )
        md.append("- busiest days: " + ", ".join(
            f"{x['day']} ({x['n']})" for x in rec["top_days"][:5]
        ))
        md.append("- busiest hours UTC: " + ", ".join(
            f"{x['hour_utc']} ({x['n']})" for x in rec["top_hours"][:5]
        ))
        md.append("")
    md_path = ROOT / "fade_spike_rate.md"
    md_path.write_text("\n".join(md))
    log(f"wrote {path} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
