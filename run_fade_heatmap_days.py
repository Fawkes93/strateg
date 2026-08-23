#!/usr/bin/env python3
"""Detect-only day lists for months that fired (min 1400 / 3s)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.runner import load_ticks
from run_fade_heatmap import detect_events
from run_fade_oat import log

MONTHS = [
    ("2025-04-01", "2025-05-01"),
    ("2025-05-01", "2025-06-01"),
    ("2025-10-01", "2025-11-01"),
    ("2025-12-01", "2026-01-01"),
    ("2026-01-01", "2026-02-01"),
    ("2026-02-01", "2026-03-01"),
    ("2026-03-01", "2026-04-01"),
    ("2026-04-01", "2026-05-01"),
    ("2026-06-01", "2026-07-01"),
    ("2026-07-01", "2026-08-01"),
]


def main() -> int:
    lines = []
    for a, b in MONTHS:
        log(f"days {a[:7]}")
        ticks = load_ticks(symbol="XAUUSD", date_from=a, date_to=b)
        ev = detect_events(ticks, 3.0, 1400.0)
        days = sorted(
            {
                datetime.fromtimestamp(e, tz=timezone.utc).strftime("%Y-%m-%d")
                for e in ev
            }
        )
        lines.append(f"- **{a[:7]}:** {', '.join(days) if days else '—'}")
        del ticks
    path = ROOT / "fade_heatmap_min1400_days.txt"
    path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
