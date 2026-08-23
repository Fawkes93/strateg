#!/usr/bin/env python3
"""
Download Dukascopy BTCUSD ticks for 2025 + 2026, then run spike-fade.

BTC point size is $0.01 (same as XAU): 100 pts ≈ $1, 10_000 pts = $100.
Dukascopy BTC mid-spread on a sample hour was ~$50 — mid fills are very
optimistic. Weekend forex blackout is off (crypto is 24/7).

  /Users/carauslivian/reaktor/.venv/bin/python3 -u run_fade_btc.py
  zsh start_btc.sh
"""

from __future__ import annotations

import gc
import json
import sys
import time
import traceback
from collections import defaultdict, deque
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, ROOT)

from backtest.config import point_size
from backtest.dukascopy import drop_cached_pack, normalize_duka_symbol
from backtest.runner import DEFAULT_RESULTS, _parse_range, load_ticks
from backtest.spike_fade_jobs import SpikeFadeJobParams, _month_chunks
from run_fade_oat import execute, log, slim

DATE_FROM = "2025-01-01"


def date_to() -> str:
    """First of next month, but at least through Aug 2026."""
    today = date.today()
    if today.month == 12:
        nxt = date(today.year + 1, 1, 1)
    else:
        nxt = date(today.year, today.month + 1, 1)
    floor = date(2026, 9, 1)
    return max(nxt, floor).isoformat()


def seed_params(date_to_s: str) -> SpikeFadeJobParams:
    # BTC-scaled "hot" first guess: fade a $100 rip in 3s.
    return SpikeFadeJobParams(
        symbol="BTCUSD",
        date_from=DATE_FROM,
        date_to=date_to_s,
        window_sec=3.0,
        min_spike_pts=10000.0,
        tp_pct=0.0,
        sl_pct=0.0,
        tp_pts=20000.0,
        sl_pts=10000.0,
        trail_pts=6000.0,
        trail_arm_pts=8000.0,
        confirm_pts=0.0,
        confirm_timeout_sec=5.0,
        max_hold_sec=250.0,
        cooldown_sec=30.0,
        weekend_blackout_min=0.0,
        lag_sec=1.0,
        workers=3,
        force_download=False,
    )


def _clone(base: SpikeFadeJobParams, overrides: dict) -> SpikeFadeJobParams:
    p = SpikeFadeJobParams(**asdict(base))
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


def job_list(base: SpikeFadeJobParams) -> list[tuple[str, str, SpikeFadeJobParams]]:
    out: list[tuple[str, str, SpikeFadeJobParams]] = [
        ("btc-hot", "BTC $100/3s first guess", base),
        (
            "xau-transplant",
            "gold HOT numbers on BTC (too small vs spread)",
            _clone(
                base,
                {
                    "window_sec": 3.0,
                    "min_spike_pts": 1400.0,
                    "tp_pts": 3000.0,
                    "sl_pts": 1500.0,
                    "trail_pts": 600.0,
                    "trail_arm_pts": 750.0,
                    "max_hold_sec": 250.0,
                    "cooldown_sec": 120.0,
                },
            ),
        ),
    ]

    def add(label: str, changed: str, **ov) -> None:
        out.append((label, changed, _clone(base, ov)))

    for v in (5000, 8000, 15000, 20000, 30000):
        add(f"min={v}", "min_spike_pts", min_spike_pts=float(v))
    for v in (5.0, 8.0, 15.0, 30.0, 60.0):
        add(f"win={v:g}", "window_sec", window_sec=float(v))
    add("sl=8000", "sl_pts", sl_pts=8000.0)
    add("sl=15000", "sl_pts", sl_pts=15000.0)
    add("trail=4000+arm=6000", "trail", trail_pts=4000.0, trail_arm_pts=6000.0)
    add("hold=400", "max_hold_sec", max_hold_sec=400.0)
    add("cd=0", "cooldown_sec", cooldown_sec=0.0)
    add("cd=120", "cooldown_sec", cooldown_sec=120.0)
    add(
        "win15+min8000",
        "stack",
        window_sec=15.0,
        min_spike_pts=8000.0,
    )
    add(
        "win30+min8000",
        "stack",
        window_sec=30.0,
        min_spike_pts=8000.0,
    )
    add(
        "win60+min8000",
        "stack",
        window_sec=60.0,
        min_spike_pts=8000.0,
    )
    add(
        "win3+min10000+tp15k+sl8k",
        "stack",
        window_sec=3.0,
        min_spike_pts=10000.0,
        tp_pts=15000.0,
        sl_pts=8000.0,
        trail_pts=5000.0,
        trail_arm_pts=7000.0,
    )
    add(
        "win8+min15000",
        "stack",
        window_sec=8.0,
        min_spike_pts=15000.0,
        tp_pts=25000.0,
        sl_pts=12000.0,
    )
    return out


def decorate(result: dict) -> dict:
    rows = result.get("rows") or []
    by_month: dict[str, dict] = defaultdict(lambda: {"n": 0, "pos": 0, "neg": 0, "sum": 0.0})
    for t in rows:
        ts = str(t.get("entry_ts") or "")
        ym = ts[:7] if len(ts) >= 7 else "unknown"
        pts = float(t.get("pts") or 0.0)
        rec = by_month[ym]
        rec["n"] += 1
        rec["sum"] += pts
        if pts > 0:
            rec["pos"] += 1
        elif pts < 0:
            rec["neg"] += 1
    result["by_month"] = {
        k: {"n": v["n"], "pos": v["pos"], "neg": v["neg"], "sum": round(v["sum"], 1)}
        for k, v in sorted(by_month.items())
    }
    return result


def slim_b(result: dict) -> dict:
    out = slim(result)
    if "by_month" in result:
        out["by_month"] = result["by_month"]
    return out


def write_summary(out_dir: Path, rows: list[dict], date_to_s: str) -> None:
    path_json = out_dir / "summary.json"
    path_csv = out_dir / "summary.csv"
    path_md = out_dir / "summary.md"
    path_json.write_text(json.dumps(rows, indent=2, default=str))
    cols = [
        "label",
        "changed",
        "trades",
        "win_pct",
        "avg_pts",
        "sum_pts",
        "profit_factor",
        "tp_pct",
        "sl_pct",
        "trail_pct",
        "timeout_pct",
        "elapsed_sec",
    ]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join("" if r.get(c) is None else str(r.get(c)) for c in cols))
    path_csv.write_text("\n".join(lines) + "\n")

    ranked = sorted(
        [r for r in rows if r.get("sum_pts") is not None],
        key=lambda r: (
            float(r.get("profit_factor") or 0) >= 1.2,
            float(r.get("sum_pts") or 0),
        ),
        reverse=True,
    )
    md = [
        "# BTC spike fade",
        "",
        f"Range `{DATE_FROM}` → `{date_to_s}`. Symbol **BTCUSD**. "
        "1 pt = $0.01 (10_000 pts = $100). Weekend skip **off**. Mid fill, no live spread.",
        "",
        f"Jobs done: {len(rows)}.",
        "",
        "## Ranked by sum (PF≥1.2 preferred)",
        "",
        "| label | n | win% | avg | sum | PF | TP% | SL% | trail% | to% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in ranked:
        md.append(
            "| {label} | {trades} | {win_pct} | {avg_pts} | {sum_pts} | {profit_factor} | "
            "{tp_pct} | {sl_pct} | {trail_pct} | {timeout_pct} |".format(
                label=r.get("label"),
                trades=r.get("trades"),
                win_pct=r.get("win_pct"),
                avg_pts=r.get("avg_pts"),
                sum_pts=r.get("sum_pts"),
                profit_factor=r.get("profit_factor"),
                tp_pct=r.get("tp_pct"),
                sl_pct=r.get("sl_pct"),
                trail_pct=r.get("trail_pct"),
                timeout_pct=r.get("timeout_pct"),
            )
        )
    md += [
        "",
        "## All jobs (run order)",
        "",
        "| label | n | win% | avg | sum | PF |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        md.append(
            "| {label} | {trades} | {win_pct} | {avg_pts} | {sum_pts} | {profit_factor} |".format(
                label=r.get("label"),
                trades=r.get("trades"),
                win_pct=r.get("win_pct"),
                avg_pts=r.get("avg_pts"),
                sum_pts=r.get("sum_pts"),
                profit_factor=r.get("profit_factor"),
            )
        )
    path_md.write_text("\n".join(md) + "\n")


def probe_3s(ticks, n_sample: int = 400_000) -> None:
    """Cheap look at 3s ranges so the log says what 'min' means in dollars."""
    ps = point_size("BTC/USD")
    step = max(1, len(ticks) // n_sample)
    sample = ticks[::step]
    dq: deque = deque()
    ranges = []
    for t in sample:
        ts = t.ts.timestamp() if t.ts.tzinfo else t.ts.replace(tzinfo=timezone.utc).timestamp()
        px = t.mid
        dq.append((ts, px))
        while dq and dq[0][0] < ts - 3.0:
            dq.popleft()
        if len(dq) < 2:
            continue
        prices = [p for _, p in dq]
        ranges.append((max(prices) - min(prices)) / ps)
    if not ranges:
        log("probe: no 3s ranges")
        return
    ranges.sort()

    def pct(p: float) -> float:
        return ranges[min(len(ranges) - 1, int(p / 100.0 * len(ranges)))]

    log(
        f"probe 3s range pts (n={len(ranges)}): "
        f"p50={pct(50):.0f} (${pct(50)*ps:.1f})  "
        f"p90={pct(90):.0f} (${pct(90)*ps:.1f})  "
        f"p99={pct(99):.0f} (${pct(99)*ps:.1f})  "
        f"max={ranges[-1]:.0f} (${ranges[-1]*ps:.1f})"
    )


def download_months(chunks: list[tuple[str, str]]) -> None:
    duka = normalize_duka_symbol("BTCUSD")
    n = len(chunks)
    for i, (a, b) in enumerate(chunks, 1):
        log(f"download {i}/{n}  {a} → {b}")
        t0 = time.time()
        try:
            ticks = load_ticks(symbol="BTCUSD", date_from=a, date_to=b)
        except Exception as e:
            log(f"    FAIL {a}: {e}")
            traceback.print_exc()
            continue
        elapsed = time.time() - t0
        if ticks:
            mids = [t.mid for t in ticks[::50]]
            lo, hi = min(mids), max(mids)
            log(
                f"    {len(ticks):,} ticks  mid {lo:.1f}–{hi:.1f}  "
                f"day-range ${hi-lo:.1f}  ({elapsed:.0f}s)"
            )
            if i == 1 or a.startswith("2026-01"):
                probe_3s(ticks)
        else:
            log(f"    0 ticks ({elapsed:.0f}s)")
        start, end = _parse_range(a, b)
        drop_cached_pack(duka, start, end)
        del ticks
        gc.collect()


def main() -> int:
    date_to_s = date_to()
    chunks = _month_chunks(DATE_FROM, date_to_s)
    base = seed_params(date_to_s)
    jobs = job_list(base)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_btc_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"BTC fade · download {len(chunks)} months {DATE_FROM}→{date_to_s}")
    log(f"point_size={point_size('BTC/USD')}  jobs={len(jobs)}  → {out_dir}")
    (out_dir / "README.md").write_text(
        f"BTCUSD spike fade. {DATE_FROM} → {date_to_s}.\n"
        "1 pt = $0.01. Seed = win3 min10000 ($100) TP20000 SL10000 "
        "trail6000 arm8000 hold250 cd30 lag1 weekend-off.\n"
        "Phase 1 downloads bi5 + monthly tickpacks. Phase 2 runs fades.\n"
    )

    download_months(chunks)
    log(f"download done. starting {len(jobs)} fade jobs")

    rows: list[dict] = []
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== btc {i}/{n}  {label}  ({changed}) ===")
        t0 = time.time()
        try:
            result = decorate(execute(params))
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
            write_summary(out_dir, rows, date_to_s)
            continue
        elapsed = round(time.time() - t0, 1)
        result["label"] = label
        result["changed"] = changed
        result["elapsed_sec"] = elapsed
        slim_r = slim_b(result)
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)
        (out_dir / f"{i:03d}_{safe}.json").write_text(
            json.dumps(slim_r, indent=2, default=str)
        )
        rows.append(slim_r)
        write_summary(out_dir, rows, date_to_s)
        log(
            f"    → n={result.get('trades')} win={result.get('win_pct')} "
            f"PF={result.get('profit_factor')} sum={result.get('sum_pts')} "
            f"avg={result.get('avg_pts')} ({elapsed}s)"
        )
        gc.collect()

    write_summary(out_dir, rows, date_to_s)
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
    log(f"BTC fade done. {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
