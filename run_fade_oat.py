#!/usr/bin/env python3
"""
One-at-a-time spike-fade confirmation around a baseline combo.

Waits until the UI fade job is idle (so we don't fight RAM), then walks
nearby params changing a single knob each run. Writes a comparison table.

  /Users/carauslivian/reaktor/.venv/bin/python3 run_fade_oat.py
"""

from __future__ import annotations

import gc
import json
import sys
import time
import traceback
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.dukascopy import drop_cached_pack, normalize_duka_symbol, reaktor_symbol
from backtest.runner import DEFAULT_RESULTS, _parse_range
from backtest.spike_fade import FadeParams, FadeTrade, summarize_fade
from backtest.spike_fade_jobs import (
    SpikeFadeJobParams,
    _job_index,
    _month_chunks,
    _run_month_job,
)

# Screenshot combo — 2025-01-01 → 2026-08-01, 386 trades, avg 150.9, PF 1.51
BASE = SpikeFadeJobParams(
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
    max_hold_sec=200.0,
    cooldown_sec=30.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
    workers=6,
    force_download=False,
)

# One knob at a time. Baseline is run first as "base".
NEIGHBORS: list[tuple[str, str, object]] = [
    ("min_spike_pts", "min=1000", 1000.0),
    ("min_spike_pts", "min=1200", 1200.0),
    ("min_spike_pts", "min=1300", 1300.0),
    ("sl_pts", "sl=800", 800.0),
    ("sl_pts", "sl=1200", 1200.0),
    ("sl_pts", "sl=1500", 1500.0),
    ("trail_pts", "trail=400", 400.0),
    ("trail_pts", "trail=600", 600.0),
    ("trail_pts", "trail=700", 700.0),
    ("max_hold_sec", "hold=160", 160.0),
    ("max_hold_sec", "hold=240", 240.0),
    ("window_sec", "win=2.5", 2.5),
    ("window_sec", "win=3.5", 3.5),
    ("lag_sec", "lag=0", 0.0),
    ("lag_sec", "lag=2", 2.0),
    ("tp_pts", "tp=2500", 2500.0),
    ("tp_pts", "tp=3500", 3500.0),
    ("cooldown_sec", "cd=15", 15.0),
    ("cooldown_sec", "cd=60", 60.0),
]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def wait_ui_idle() -> None:
    url = "http://127.0.0.1:8765/api/spike-fade"
    while True:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                st = json.loads(r.read().decode())
            if not st.get("running"):
                log("UI fade is idle — starting OAT")
                return
            phase = (st.get("progress") or {}).get("phase")
            msg = (st.get("progress") or {}).get("message") or ""
            log(f"UI fade still running ({phase}) {msg} — waiting 30s")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            log(f"webapp not reachable ({e}) — starting OAT anyway")
            return
        time.sleep(30)


def execute(params: SpikeFadeJobParams, chunks=None) -> dict:
    chunks = list(chunks) if chunks is not None else _month_chunks(
        params.date_from, params.date_to
    )
    if not chunks:
        raise RuntimeError("Empty date range")
    n_m = len(chunks)
    fp = FadeParams(
        window_sec=float(params.window_sec),
        min_spike_pts=float(params.min_spike_pts),
        tp_pts=float(params.tp_pts),
        sl_pts=float(params.sl_pts),
        tp_pct=float(params.tp_pct or 0.0),
        sl_pct=float(params.sl_pct or 0.0),
        trail_pts=float(params.trail_pts),
        trail_arm_pts=float(getattr(params, "trail_arm_pts", 0.0) or 0.0),
        confirm_pts=float(getattr(params, "confirm_pts", 0.0) or 0.0),
        confirm_timeout_sec=float(getattr(params, "confirm_timeout_sec", 5.0) or 5.0),
        max_extreme_age_sec=float(getattr(params, "max_extreme_age_sec", 0.0) or 0.0),
        max_hold_sec=float(params.max_hold_sec),
        cooldown_sec=float(params.cooldown_sec),
        weekend_blackout_min=float(params.weekend_blackout_min),
        lag_sec=float(params.lag_sec or 0.0),
    )
    fade_params = asdict(fp)
    workers = max(1, min(6, int(params.workers or 1)))
    all_rows: list[dict] = []
    total_ticks = 0
    errors: list[str] = []

    import multiprocessing as mp

    ctx = mp.get_context("spawn")
    payloads = [
        {
            "index": i,
            "date_from": a,
            "date_to": b,
            "symbol": params.symbol,
            "force_download": params.force_download,
            "fade_params": fade_params,
            "progress_q": None,
        }
        for i, (a, b) in enumerate(chunks)
    ]
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        futs = {pool.submit(_run_month_job, p): p for p in payloads}
        pending = set(futs)
        done_n = 0
        while pending:
            finished, pending = wait(pending, timeout=2.0, return_when=FIRST_COMPLETED)
            for fut in finished:
                out = fut.result()
                done_n += 1
                total_ticks += int(out.get("ticks") or 0)
                all_rows.extend(out.get("rows") or [])
                idx = _job_index(out, -1)
                label = f"{out.get('date_from')}→{out.get('date_to')}"
                if not out.get("ok") and out.get("error"):
                    errors.append(str(out["error"]))
                    log(f"    month fail {label}: {out['error']}")
                else:
                    ntr = len(out.get("rows") or [])
                    log(f"    {done_n}/{n_m} {label}  {ntr} trades")
    duka = normalize_duka_symbol(params.symbol)
    for a, b in chunks:
        start, end = _parse_range(a, b)
        drop_cached_pack(duka, start, end)
    gc.collect()

    fields = FadeTrade.__dataclass_fields__
    trades = [FadeTrade(**{k: r[k] for k in fields if k in r}) for r in all_rows]
    result = summarize_fade(
        trades, fp, symbol=reaktor_symbol(params.symbol), ticks=total_ticks
    )
    result["date_from"] = params.date_from
    result["date_to"] = params.date_to
    result["months"] = n_m
    if errors:
        result["errors"] = errors
    return result


def slim(result: dict) -> dict:
    keep = (
        "kind",
        "symbol",
        "params",
        "date_from",
        "date_to",
        "months",
        "ticks",
        "trades",
        "wins",
        "losses",
        "scratches",
        "win_pct",
        "tp_n",
        "tp_pct",
        "sl_n",
        "sl_pct",
        "trail_n",
        "trail_pct",
        "timeout_n",
        "timeout_pct",
        "avg_pts",
        "sum_pts",
        "profit_factor",
        "errors",
        "label",
        "changed",
        "elapsed_sec",
    )
    return {k: result[k] for k in keep if k in result}


def write_summary(out_dir: Path, rows: list[dict]) -> None:
    base = next((r for r in rows if r.get("label") == "base"), None)
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
        lines.append(
            ",".join("" if r.get(c) is None else str(r.get(c)) for c in cols)
        )
    path_csv.write_text("\n".join(lines) + "\n")

    md = [
        "# Spike fade OAT confirmation",
        "",
        f"Range `{BASE.date_from}` → `{BASE.date_to}`. One param at a time vs base.",
        "",
        "| label | trades | win% | avg | sum | PF | TP% | SL% | trail% | to% | vs avg | vs PF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    b_avg = (base or {}).get("avg_pts")
    b_pf = (base or {}).get("profit_factor")
    for r in rows:
        d_avg = (
            round(r["avg_pts"] - b_avg, 1)
            if b_avg is not None and r.get("avg_pts") is not None
            else ""
        )
        d_pf = (
            round(r["profit_factor"] - b_pf, 2)
            if b_pf is not None and r.get("profit_factor") is not None
            else ""
        )
        md.append(
            "| {label} | {trades} | {win_pct} | {avg_pts} | {sum_pts} | {profit_factor} | "
            "{tp_pct} | {sl_pct} | {trail_pct} | {timeout_pct} | {d_avg} | {d_pf} |".format(
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
                d_avg=d_avg,
                d_pf=d_pf,
            )
        )
    path_md.write_text("\n".join(md) + "\n")


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = DEFAULT_RESULTS / f"fade_oat_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    # tee-ish: also write a log file
    log(f"output → {out_dir}")

    wait_ui_idle()

    jobs: list[tuple[str, str, SpikeFadeJobParams]] = [
        ("base", "baseline screenshot combo", BASE),
    ]
    for field, label, value in NEIGHBORS:
        p = SpikeFadeJobParams(**asdict(BASE))
        setattr(p, field, value)
        jobs.append((label, field, p))

    rows: list[dict] = []
    n = len(jobs)
    for i, (label, changed, params) in enumerate(jobs, 1):
        log(f"=== {i}/{n}  {label}  ({changed}) ===")
        t0 = time.time()
        try:
            result = execute(params)
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
        slim_r = slim(result)
        (out_dir / f"{i:02d}_{label.replace('=', '_')}.json").write_text(
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
    log(f"done. summary: {out_dir / 'summary.md'}")
    log_path.write_text("")  # placeholder if we later tee
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
