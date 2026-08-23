#!/usr/bin/env python3
"""
Quiet-2025 frequency hunt.

Range: 2025-01-01 → 2025-11-01 (Jan through October).
Seed: the violent Jan/Feb 2026 PF~3 preset (min 1400 / 3s / TP3000 / SL1500).
That seed barely prints on calm 2025 tape. Goal: find a neighbor that does
**at least 1 trade per week on the quiet months (Jan–Sep)**.

October 2025 is included in the run (user asked through October) but scored
separately so a handful of Oct tickets cannot fake the 1/week target.

  /Users/carauslivian/reaktor/.venv/bin/python3 -u run_fade_quiet2025.py
  zsh start_quiet2025.sh
"""

from __future__ import annotations

import gc
import json
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.runner import DEFAULT_RESULTS
from backtest.spike_fade_jobs import SpikeFadeJobParams
from run_fade_oat import execute, log, slim

DATE_FROM = "2025-01-01"
DATE_TO = "2025-11-01"  # exclusive — through 31 Oct
QUIET_END = "2025-10-01"  # exclusive — Jan–Sep is the quiet core

DAYS_ALL = (date(2025, 11, 1) - date(2025, 1, 1)).days  # 304
DAYS_QUIET = (date(2025, 10, 1) - date(2025, 1, 1)).days  # 273
WEEKS_ALL = DAYS_ALL / 7.0
WEEKS_QUIET = DAYS_QUIET / 7.0

# Violent PF~3 preset that worked on Jan/Feb 2026.
SEED = SpikeFadeJobParams(
    symbol="XAUUSD",
    date_from=DATE_FROM,
    date_to=DATE_TO,
    window_sec=3.0,
    min_spike_pts=1400.0,
    tp_pct=0.0,
    sl_pct=0.0,
    tp_pts=3000.0,
    sl_pts=1500.0,
    trail_pts=600.0,
    trail_arm_pts=750.0,
    confirm_pts=0.0,
    confirm_timeout_sec=5.0,
    max_hold_sec=250.0,
    cooldown_sec=120.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=4,
    force_download=False,
)


def _clone(overrides: dict) -> SpikeFadeJobParams:
    p = SpikeFadeJobParams(**asdict(SEED))
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


def job_list() -> list[tuple[str, str, SpikeFadeJobParams]]:
    out: list[tuple[str, str, SpikeFadeJobParams]] = [
        ("seed", "violent PF~3 control", SEED),
    ]

    def oat(field: str, label: str, value) -> None:
        out.append((label, field, _clone({field: value})))

    # --- set 1: detect only (this is what creates tickets) ---
    for v in (5.0, 8.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0):
        oat("window_sec", f"win={v:g}", float(v))
    for v in (300, 400, 500, 600, 700, 800, 1000, 1100):
        oat("min_spike_pts", f"min={v}", float(v))

    # --- set 2: long window × lower min (the actual quiet microscope) ---
    detect_stacks = [
        ("win60+min400", {"window_sec": 60.0, "min_spike_pts": 400.0}),
        ("win60+min500", {"window_sec": 60.0, "min_spike_pts": 500.0}),
        ("win60+min600", {"window_sec": 60.0, "min_spike_pts": 600.0}),
        ("win60+min800", {"window_sec": 60.0, "min_spike_pts": 800.0}),
        ("win45+min400", {"window_sec": 45.0, "min_spike_pts": 400.0}),
        ("win45+min500", {"window_sec": 45.0, "min_spike_pts": 500.0}),
        ("win30+min400", {"window_sec": 30.0, "min_spike_pts": 400.0}),
        ("win30+min500", {"window_sec": 30.0, "min_spike_pts": 500.0}),
        ("win30+min600", {"window_sec": 30.0, "min_spike_pts": 600.0}),
        ("win20+min400", {"window_sec": 20.0, "min_spike_pts": 400.0}),
        ("win15+min400", {"window_sec": 15.0, "min_spike_pts": 400.0}),
        ("win15+min500", {"window_sec": 15.0, "min_spike_pts": 500.0}),
        ("win10+min400", {"window_sec": 10.0, "min_spike_pts": 400.0}),
        ("win8+min400", {"window_sec": 8.0, "min_spike_pts": 400.0}),
        ("win5+min400", {"window_sec": 5.0, "min_spike_pts": 400.0}),
        ("win5+min600", {"window_sec": 5.0, "min_spike_pts": 600.0}),
    ]
    for label, ov in detect_stacks:
        out.append((label, "detect", _clone(ov)))

    # --- set 3: same loose detect + smaller exits / more hold ---
    combo_stacks = [
        (
            "win60+min400+tp800+sl500",
            {
                "window_sec": 60.0,
                "min_spike_pts": 400.0,
                "tp_pts": 800.0,
                "sl_pts": 500.0,
            },
        ),
        (
            "win60+min400+small+hold480",
            {
                "window_sec": 60.0,
                "min_spike_pts": 400.0,
                "tp_pts": 600.0,
                "sl_pts": 400.0,
                "trail_pts": 300.0,
                "trail_arm_pts": 400.0,
                "max_hold_sec": 480.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win60+min500+tp1000+sl600",
            {
                "window_sec": 60.0,
                "min_spike_pts": 500.0,
                "tp_pts": 1000.0,
                "sl_pts": 600.0,
                "trail_pts": 400.0,
                "trail_arm_pts": 500.0,
            },
        ),
        (
            "win60+min300+tiny",
            {
                "window_sec": 60.0,
                "min_spike_pts": 300.0,
                "tp_pts": 500.0,
                "sl_pts": 400.0,
                "trail_pts": 250.0,
                "trail_arm_pts": 300.0,
                "max_hold_sec": 600.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win30+min400+tp600+sl400",
            {
                "window_sec": 30.0,
                "min_spike_pts": 400.0,
                "tp_pts": 600.0,
                "sl_pts": 400.0,
                "trail_pts": 300.0,
                "trail_arm_pts": 400.0,
            },
        ),
        (
            "win30+min500+tp800+sl500+hold400",
            {
                "window_sec": 30.0,
                "min_spike_pts": 500.0,
                "tp_pts": 800.0,
                "sl_pts": 500.0,
                "trail_pts": 400.0,
                "trail_arm_pts": 500.0,
                "max_hold_sec": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win30+min400+hold600",
            {
                "window_sec": 30.0,
                "min_spike_pts": 400.0,
                "max_hold_sec": 600.0,
            },
        ),
        (
            "win15+min400+tp800+sl500+hold400",
            {
                "window_sec": 15.0,
                "min_spike_pts": 400.0,
                "tp_pts": 800.0,
                "sl_pts": 500.0,
                "trail_pts": 400.0,
                "trail_arm_pts": 500.0,
                "max_hold_sec": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win15+min400+cd30",
            {
                "window_sec": 15.0,
                "min_spike_pts": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win15+min400+cd0",
            {
                "window_sec": 15.0,
                "min_spike_pts": 400.0,
                "cooldown_sec": 0.0,
            },
        ),
        (
            "win10+min400+tp600+sl400",
            {
                "window_sec": 10.0,
                "min_spike_pts": 400.0,
                "tp_pts": 600.0,
                "sl_pts": 400.0,
                "trail_pts": 300.0,
                "trail_arm_pts": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win8+min400+tp750+sl500",
            {
                "window_sec": 8.0,
                "min_spike_pts": 400.0,
                "tp_pts": 750.0,
                "sl_pts": 500.0,
                "trail_pts": 400.0,
                "trail_arm_pts": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win15+min500+y25exits",
            {
                "window_sec": 15.0,
                "min_spike_pts": 500.0,
                "tp_pts": 750.0,
                "sl_pts": 750.0,
                "trail_pts": 500.0,
                "trail_arm_pts": 500.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win30+min400+y25exits",
            {
                "window_sec": 30.0,
                "min_spike_pts": 400.0,
                "tp_pts": 750.0,
                "sl_pts": 750.0,
                "trail_pts": 400.0,
                "trail_arm_pts": 400.0,
                "max_hold_sec": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win60+min400+cd30",
            {
                "window_sec": 60.0,
                "min_spike_pts": 400.0,
                "cooldown_sec": 30.0,
            },
        ),
        (
            "win60+min500+hold600",
            {
                "window_sec": 60.0,
                "min_spike_pts": 500.0,
                "max_hold_sec": 600.0,
            },
        ),
    ]
    for label, ov in combo_stacks:
        out.append((label, "combo", _clone(ov)))
    return out


def decorate(result: dict) -> dict:
    """Add trades/week and Jan–Sep vs October split. Drops bulky rows after."""
    rows = result.get("rows") or []
    by_month: dict[str, dict] = defaultdict(lambda: {"n": 0, "pos": 0, "neg": 0, "sum": 0.0})
    quiet_n = 0
    quiet_sum = 0.0
    quiet_pos = 0
    oct_n = 0
    oct_sum = 0.0
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
        if ts.startswith("2025-10"):
            oct_n += 1
            oct_sum += pts
        elif ts[:10] < QUIET_END:
            quiet_n += 1
            quiet_sum += pts
            if pts > 0:
                quiet_pos += 1

    n = int(result.get("trades") or 0)
    tpw = round(n / WEEKS_ALL, 2) if WEEKS_ALL else 0.0
    q_tpw = round(quiet_n / WEEKS_QUIET, 2) if WEEKS_QUIET else 0.0
    result["weeks"] = round(WEEKS_ALL, 2)
    result["quiet_weeks"] = round(WEEKS_QUIET, 2)
    result["trades_per_week"] = tpw
    result["quiet_trades"] = quiet_n
    result["quiet_sum"] = round(quiet_sum, 1)
    result["quiet_win_pct"] = round(100.0 * quiet_pos / quiet_n, 1) if quiet_n else None
    result["quiet_tpw"] = q_tpw
    result["oct_trades"] = oct_n
    result["oct_sum"] = round(oct_sum, 1)
    result["hit_1_per_week"] = bool(q_tpw + 1e-12 >= 1.0)
    result["by_month"] = {
        k: {
            "n": v["n"],
            "pos": v["pos"],
            "neg": v["neg"],
            "sum": round(v["sum"], 1),
        }
        for k, v in sorted(by_month.items())
    }
    return result


def slim_q(result: dict) -> dict:
    extra = (
        "weeks",
        "quiet_weeks",
        "trades_per_week",
        "quiet_trades",
        "quiet_sum",
        "quiet_win_pct",
        "quiet_tpw",
        "oct_trades",
        "oct_sum",
        "hit_1_per_week",
        "by_month",
    )
    out = slim(result)
    for k in extra:
        if k in result:
            out[k] = result[k]
    return out


def write_summary(out_dir: Path, rows: list[dict]) -> None:
    path_json = out_dir / "summary.json"
    path_csv = out_dir / "summary.csv"
    path_md = out_dir / "summary.md"
    path_json.write_text(json.dumps(rows, indent=2, default=str))

    cols = [
        "label",
        "changed",
        "trades",
        "trades_per_week",
        "quiet_trades",
        "quiet_tpw",
        "hit_1_per_week",
        "oct_trades",
        "win_pct",
        "avg_pts",
        "sum_pts",
        "quiet_sum",
        "profit_factor",
        "elapsed_sec",
    ]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join("" if r.get(c) is None else str(r.get(c)) for c in cols))
    path_csv.write_text("\n".join(lines) + "\n")

    hits = [r for r in rows if r.get("hit_1_per_week") and r.get("sum_pts") is not None]
    hits_sorted = sorted(
        hits,
        key=lambda r: (
            float(r.get("profit_factor") or 0) >= 1.15,
            float(r.get("quiet_sum") or 0),
            float(r.get("profit_factor") or 0),
        ),
        reverse=True,
    )

    md = [
        "# Quiet 2025 frequency hunt",
        "",
        f"Range `{DATE_FROM}` → `{DATE_TO}` ({DAYS_ALL} days, **{WEEKS_ALL:.1f} weeks**).",
        f"Quiet core Jan–Sep = {DAYS_QUIET} days, **{WEEKS_QUIET:.1f} weeks**. "
        "Need **≥39 Jan–Sep trades** for 1/week.",
        "",
        "Seed: window **3** · min **1400** · TP **3000** · SL **1500** · trail **600** · "
        "arm **750** · hold **250** · cd **120** · lag **1**.",
        "",
        f"Jobs done: {len(rows)}. Hits (quiet ≥1/week): **{len(hits)}**.",
        "",
    ]
    if hits_sorted:
        md += [
            "## Hits — quiet ≥ 1 trade/week",
            "",
            "| label | n | /wk | quiet n | quiet/wk | Oct n | win% | PF | sum | quiet sum |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in hits_sorted:
            md.append(
                "| {label} | {trades} | {trades_per_week} | {quiet_trades} | {quiet_tpw} | "
                "{oct_trades} | {win_pct} | {profit_factor} | {sum_pts} | {quiet_sum} |".format(
                    label=r.get("label"),
                    trades=r.get("trades"),
                    trades_per_week=r.get("trades_per_week"),
                    quiet_trades=r.get("quiet_trades"),
                    quiet_tpw=r.get("quiet_tpw"),
                    oct_trades=r.get("oct_trades"),
                    win_pct=r.get("win_pct"),
                    profit_factor=r.get("profit_factor"),
                    sum_pts=r.get("sum_pts"),
                    quiet_sum=r.get("quiet_sum"),
                )
            )
        md.append("")

    md += [
        "## All jobs",
        "",
        "| label | n | /wk | quiet n | quiet/wk | hit | Oct | win% | avg | sum | PF |",
        "|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        hit = "YES" if r.get("hit_1_per_week") else ""
        md.append(
            "| {label} | {trades} | {trades_per_week} | {quiet_trades} | {quiet_tpw} | "
            "{hit} | {oct_trades} | {win_pct} | {avg_pts} | {sum_pts} | {profit_factor} |".format(
                label=r.get("label"),
                trades=r.get("trades"),
                trades_per_week=r.get("trades_per_week"),
                quiet_trades=r.get("quiet_trades"),
                quiet_tpw=r.get("quiet_tpw"),
                hit=hit,
                oct_trades=r.get("oct_trades"),
                win_pct=r.get("win_pct"),
                avg_pts=r.get("avg_pts"),
                sum_pts=r.get("sum_pts"),
                profit_factor=r.get("profit_factor"),
            )
        )
    path_md.write_text("\n".join(md) + "\n")


def main() -> int:
    jobs = job_list()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_quiet2025_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"quiet-2025 hunt · {len(jobs)} jobs · {DATE_FROM} → {DATE_TO} → {out_dir}")
    log(
        f"target: ≥1 trade/week on Jan–Sep "
        f"({WEEKS_QUIET:.1f} weeks ⇒ ≥{int(WEEKS_QUIET)} trades)"
    )
    (out_dir / "README.md").write_text(
        "Quiet-2025 frequency hunt.\n"
        f"Range {DATE_FROM} → {DATE_TO}. Seed = violent PF~3 "
        "(win3 min1400 TP3000 SL1500 trail600 arm750 hold250 cd120 lag1).\n"
        f"Success: quiet (Jan–Sep) trades / {WEEKS_QUIET:.1f} weeks ≥ 1.0.\n"
        "October is scored separately so it cannot fake the target.\n"
    )

    rows: list[dict] = []
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== q25 {i}/{n}  {label}  ({changed}) ===")
        t0 = time.time()
        try:
            result = execute(params)
            result = decorate(result)
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
            f"q/wk={result.get('quiet_tpw')} Oct={result.get('oct_trades')} "
            f"PF={result.get('profit_factor')} sum={result.get('sum_pts')}"
            f"{mark} ({elapsed}s)"
        )
        gc.collect()

    write_summary(out_dir, rows)
    hits = [r for r in rows if r.get("hit_1_per_week")]
    log(f"quiet-2025 done. hits={len(hits)}/{len(rows)}  {out_dir / 'summary.md'}")
    if hits:
        best = max(
            hits,
            key=lambda r: (
                float(r.get("profit_factor") or 0) >= 1.15,
                float(r.get("quiet_sum") or 0),
            ),
        )
        log(
            f"best hit {best.get('label')}  quiet n={best.get('quiet_trades')} "
            f"q/wk={best.get('quiet_tpw')} PF={best.get('profit_factor')} "
            f"quiet sum={best.get('quiet_sum')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
