#!/usr/bin/env python3
"""
Download Dukascopy .bi5 tick hours to data/dukascopy (no tick decode).

Safe for a full year: one calendar month at a time, skip hours already cached.

  python download_ticks.py --symbol EURUSD --from 2025-01-01 --to 2026-01-01
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.dukascopy import (
    cache_range,
    month_windows,
    normalize_duka_symbol,
    parse_ymd,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def main() -> int:
    p = argparse.ArgumentParser(description="Cache Dukascopy tick hours month by month")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument("--cache", default=str(ROOT / "data" / "dukascopy"))
    p.add_argument(
        "--status",
        default="",
        help="JSON status file (default: data/dukascopy/<SYMBOL>_<from>_<to>_download.json)",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel hour downloads (keep low; Dukascopy 503s under load)",
    )
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    start = parse_ymd(args.date_from)
    end = parse_ymd(args.date_to)
    symbol = normalize_duka_symbol(args.symbol)
    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    windows = month_windows(start, end)
    if not windows:
        print("Empty date range.", flush=True)
        return 1

    stamp = f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
    status_path = (
        Path(args.status)
        if args.status
        else cache_dir / f"{symbol}_{stamp}_download.json"
    )

    totals = {"hours": 0, "cache": 0, "net": 0, "empty": 0}
    months: List[Dict[str, Any]] = []
    t0 = time.time()

    def write_status(*, phase: str, error: Optional[str] = None) -> None:
        payload = {
            "phase": phase,
            "symbol": symbol,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "cache_dir": str(cache_dir),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": round(time.time() - t0, 1),
            "months_done": len(months),
            "months_total": len(windows),
            "totals": totals,
            "months": months,
            "error": error,
        }
        tmp = status_path.with_suffix(status_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(status_path)

    print(
        f"[{_now()}] cache {symbol}  {start.date()} → {end.date()}  "
        f"({len(windows)} month windows) → {cache_dir}",
        flush=True,
    )
    write_status(phase="running")

    try:
        for i, (a, b) in enumerate(windows, start=1):
            label = a.strftime("%Y-%m")
            last_msg = ""

            def _prog(**kwargs) -> None:
                nonlocal last_msg
                msg = kwargs.get("message") or ""
                done = kwargs.get("hours_done") or 0
                total = kwargs.get("hours_total") or 0
                if msg and (done == total or (done and done % 48 == 0)):
                    if msg != last_msg:
                        last_msg = msg
                        print(f"  {label}  {msg}", flush=True)

            print(f"[{_now()}] month {i}/{len(windows)}  {label}  {a} → {b}", flush=True)
            mt0 = time.time()
            counts = cache_range(
                symbol,
                a,
                b,
                cache_dir=cache_dir,
                force=args.force,
                max_workers=args.workers,
                progress=_prog,
            )
            elapsed = time.time() - mt0
            rec = {
                "month": label,
                "from": a.isoformat(),
                "to": b.isoformat(),
                **counts,
                "elapsed_sec": round(elapsed, 1),
            }
            months.append(rec)
            for k in ("hours", "cache", "net", "empty"):
                totals[k] += counts[k]
            print(
                f"[{_now()}] month {label} done  "
                f"hours={counts['hours']} cache={counts['cache']} "
                f"net={counts['net']} empty={counts['empty']}  "
                f"{elapsed:.1f}s",
                flush=True,
            )
            write_status(phase="running")
    except Exception as e:
        write_status(phase="error", error=str(e))
        print(f"[{_now()}] FAILED: {e}", flush=True)
        raise

    write_status(phase="done")
    print(
        f"[{_now()}] DONE  hours={totals['hours']} cache={totals['cache']} "
        f"net={totals['net']} empty={totals['empty']}  "
        f"{time.time() - t0:.1f}s  status={status_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
