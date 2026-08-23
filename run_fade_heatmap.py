#!/usr/bin/env python3
"""Monthly heatmap: detects + days fired + win rate + sum for one fade combo."""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.config import point_size
from backtest.runner import DEFAULT_RESULTS, load_ticks
from backtest.spike_fade import FadeParams, _detect, run_spike_fade, to_utc
from backtest.spike_fade_jobs import _month_chunks
from run_fade_oat import log

DATE_FROM = "2025-01-01"
DATE_TO = "2026-08-01"

FP = FadeParams(
    window_sec=3.0,
    min_spike_pts=1400.0,
    tp_pts=3000.0,
    sl_pts=1500.0,
    tp_pct=0.0,
    sl_pct=0.0,
    trail_pts=600.0,
    trail_arm_pts=750.0,
    confirm_pts=0.0,
    max_hold_sec=250.0,
    cooldown_sec=120.0,
    weekend_blackout_min=10.0,
    lag_sec=1.0,
)


def detect_events(ticks, window_sec: float, min_pts: float) -> List[float]:
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
        cutoff = epoch - window_sec
        popped = False
        while dq and dq[0][0] < cutoff:
            dq.popleft()
            popped = True
        if popped and dq:
            prices = [p for _, p in dq]
            win_hi, win_lo = max(prices), min(prices)
        elif not dq:
            win_hi, win_lo = float("-inf"), float("inf")
        if epoch < suppress_until:
            continue
        if _detect(dq, ps, min_pts, window_sec, win_hi, win_lo) is None:
            continue
        events.append(epoch)
        suppress_until = epoch + window_sec
    return events


def _month_job(payload: Dict) -> Dict:
    a, b = payload["date_from"], payload["date_to"]
    ticks = load_ticks(symbol="XAUUSD", date_from=a, date_to=b)
    fade = run_spike_fade(ticks, symbol="XAUUSD", params=FP)
    ev = detect_events(ticks, FP.window_sec, FP.min_spike_pts)
    days = {datetime.fromtimestamp(e, tz=timezone.utc).strftime("%Y-%m-%d") for e in ev}
    rows = fade.get("rows") or []
    pos = sum(1 for r in rows if float(r.get("pts") or 0) > 1e-9)
    neg = sum(1 for r in rows if float(r.get("pts") or 0) < -1e-9)
    return {
        "month": a[:7],
        "date_from": a,
        "date_to": b,
        "ticks": len(ticks),
        "detects": len(ev),
        "days_fired": len(days),
        "days": sorted(days),
        "trades": fade.get("trades") or 0,
        "pos": pos,
        "neg": neg,
        "flat": (fade.get("trades") or 0) - pos - neg,
        "win_pct": fade.get("win_pct"),
        "avg_pts": fade.get("avg_pts"),
        "sum_pts": fade.get("sum_pts") or 0.0,
        "profit_factor": fade.get("profit_factor"),
        "sl_pct": fade.get("sl_pct"),
        "trail_pct": fade.get("trail_pct"),
        "timeout_pct": fade.get("timeout_pct"),
    }


def main() -> int:
    chunks = _month_chunks(DATE_FROM, DATE_TO)
    log(f"heatmap {DATE_FROM}→{DATE_TO}  {len(chunks)} months  min={FP.min_spike_pts} win={FP.window_sec}")
    payloads = [{"date_from": a, "date_to": b} for a, b in chunks]
    rows = []
    import multiprocessing as mp

    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=6, mp_context=ctx) as pool:
        futs = {pool.submit(_month_job, p): p for p in payloads}
        done = 0
        for fut in as_completed(futs):
            rec = fut.result()
            rows.append(rec)
            done += 1
            log(
                f"    {done}/{len(chunks)} {rec['month']}  "
                f"detects={rec['detects']} days={rec['days_fired']} "
                f"trades={rec['trades']} win={rec['win_pct']} sum={rec['sum_pts']}"
            )
    rows.sort(key=lambda r: r["month"])
    tot_d = sum(r["detects"] for r in rows)
    tot_t = sum(r["trades"] for r in rows)
    tot_p = sum(r["pos"] for r in rows)
    tot_n = sum(r["neg"] for r in rows)
    tot_s = sum(float(r["sum_pts"] or 0) for r in rows)
    win = round(100.0 * tot_p / tot_t, 1) if tot_t else None
    out = {
        "params": asdict(FP),
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "totals": {
            "detects": tot_d,
            "trades": tot_t,
            "pos": tot_p,
            "neg": tot_n,
            "win_pct": win,
            "sum_pts": round(tot_s, 1),
        },
        "months": rows,
    }
    js = DEFAULT_RESULTS / "fade_heatmap_min1400.json"
    js.write_text(json.dumps(out, indent=2, default=str))
    md = [
        "# Spike fade monthly heatmap",
        "",
        "window **3s** · min **1400** · TP **3000** · SL **1500** · trail **600** · "
        "arm **750** · hold **250s** · cd **120** · lag **1s**",
        f"Range `{DATE_FROM}` → `{DATE_TO}`. Detects = 1400-pt / 3s events "
        "(suppressed for 3s after each fire). Days fired = UTC days with ≥1 detect.",
        "",
        f"**Total:** {tot_t} trades · **+{tot_p}** / −{tot_n} · win {win}% · "
        f"detects {tot_d} · **sum {tot_s:,.1f}** pts",
        "",
        "| month | detects | days fired | trades | + | − | win% | avg | **sum** | PF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        md.append(
            f"| {r['month']} | {r['detects']} | {r['days_fired']} | {r['trades']} | "
            f"{r['pos']} | {r['neg']} | {r['win_pct'] if r['win_pct'] is not None else '—'} | "
            f"{r['avg_pts'] if r['avg_pts'] is not None else '—'} | "
            f"{float(r['sum_pts']):,.1f} | "
            f"{r['profit_factor'] if r['profit_factor'] is not None else '—'} |"
        )
    md.append("")
    md.append("Days that fired (UTC):")
    md.append("")
    for r in rows:
        days = ", ".join(r.get("days") or []) or "—"
        md.append(f"- **{r['month']}:** {days}")
    md_path = ROOT / "fade_heatmap_min1400.md"
    md_path.write_text("\n".join(md) + "\n")
    log(f"wrote {js} and {md_path}")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
