#!/usr/bin/env python3
"""
After quiet + (spike-rate + janfeb) finish:
  1) write an analysis
  2) run 3 targeted sets: busy refine, quiet last-chance, one-way (Mar+Jun)

Uses judgement rules baked in so this can run unattended.
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.runner import DEFAULT_RESULTS
from backtest.spike_fade_jobs import SpikeFadeJobParams
from run_fade_oat import execute, log, slim, write_summary
from run_fade_quiet import quiet_chunks

PY = sys.executable
RESULTS = DEFAULT_RESULTS

WINNER_94K = SpikeFadeJobParams(
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
)

QUIET_CHUNKS = quiet_chunks()
ONEWAY_CHUNKS = [
    ("2026-03-01", "2026-04-01"),
    ("2026-06-01", "2026-07-01"),
]


def still_running() -> bool:
    me = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-fl", "run_fade_"], text=True)
    except subprocess.CalledProcessError:
        return False
    blockers = (
        "run_fade_quiet.py",
        "run_fade_after_quiet.py",
        "run_fade_janfeb.py",
        "run_fade_spike_rate.py",
    )
    for line in out.splitlines():
        if "run_fade_followup" in line:
            continue
        if not any(b in line for b in blockers):
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if pid != me:
            return True
    return False


def latest_dir(prefix: str) -> Optional[Path]:
    cands = sorted(RESULTS.glob(prefix + "*"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def load_rows(folder: Optional[Path]) -> List[dict]:
    if not folder:
        return []
    p = folder / "summary.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except Exception:
        return []
    return [r for r in data if isinstance(r, dict) and r.get("sum_pts") is not None]


def pick_best(rows: List[dict], *, min_trades: int = 20) -> Optional[dict]:
    ok = [r for r in rows if int(r.get("trades") or 0) >= min_trades and not r.get("error")]
    if not ok:
        ok = [r for r in rows if not r.get("error") and r.get("sum_pts") is not None]
    if not ok:
        return None
    # Prefer sum, but require PF not garbage
    ranked = sorted(
        ok,
        key=lambda r: (
            float(r.get("profit_factor") or 0) >= 1.2,
            float(r.get("sum_pts") or 0),
            float(r.get("profit_factor") or 0),
        ),
        reverse=True,
    )
    return ranked[0]


def params_from_row(row: dict, date_from: str, date_to: str) -> SpikeFadeJobParams:
    p = row.get("params") or {}
    base = asdict(WINNER_94K)
    base["date_from"] = date_from
    base["date_to"] = date_to
    for k in list(base.keys()):
        if k in p and p[k] is not None and k not in ("date_from", "date_to", "symbol", "workers", "force_download"):
            base[k] = p[k]
    return SpikeFadeJobParams(**base)


def neighbors(seed: SpikeFadeJobParams, kind: str) -> List[Tuple[str, SpikeFadeJobParams]]:
    jobs: List[Tuple[str, SpikeFadeJobParams]] = [("seed", seed)]

    def add(label: str, **kw):
        d = asdict(seed)
        d.update(kw)
        jobs.append((label, SpikeFadeJobParams(**d)))

    if kind == "busy":
        add("win-0.2", window_sec=max(2.0, seed.window_sec - 0.2))
        add("win+0.2", window_sec=seed.window_sec + 0.2)
        add("win+0.5", window_sec=seed.window_sec + 0.5)
        add("min-100", min_spike_pts=max(600.0, seed.min_spike_pts - 100))
        add("min+100", min_spike_pts=seed.min_spike_pts + 100)
        add("min+200", min_spike_pts=seed.min_spike_pts + 200)
        add("hold-40", max_hold_sec=max(160.0, seed.max_hold_sec - 40))
        add("hold+80", max_hold_sec=seed.max_hold_sec + 80)
        add("hold+160", max_hold_sec=seed.max_hold_sec + 160)
        add("sl-200", sl_pts=max(500.0, seed.sl_pts - 200))
        add("sl+200", sl_pts=seed.sl_pts + 200)
        add("arm-200", trail_arm_pts=max(0.0, (seed.trail_arm_pts or 0) - 200))
        add("arm+200", trail_arm_pts=(seed.trail_arm_pts or 700) + 200)
        add("cd30", cooldown_sec=30.0)
        add("lag0", lag_sec=0.0)
    elif kind == "quiet":
        add("min-100", min_spike_pts=max(300.0, seed.min_spike_pts - 100))
        add("min+100", min_spike_pts=seed.min_spike_pts + 100)
        add("min+200", min_spike_pts=seed.min_spike_pts + 200)
        add("win-1", window_sec=max(2.5, seed.window_sec - 1.0))
        add("win+2", window_sec=seed.window_sec + 2.0)
        add("sl-200", sl_pts=max(400.0, seed.sl_pts - 200))
        add("trail-100", trail_pts=max(200.0, seed.trail_pts - 100))
        add("hold+80", max_hold_sec=seed.max_hold_sec + 80)
        add("cd30", cooldown_sec=30.0)
        add("lag0", lag_sec=0.0)
    elif kind == "oneway":
        add("c100", confirm_pts=100.0)
        add("c150", confirm_pts=150.0)
        add("c200", confirm_pts=200.0)
        add("c300", confirm_pts=300.0)
        add("c400", confirm_pts=400.0)
        add("cd30", cooldown_sec=30.0)
        add("cd60", cooldown_sec=60.0)
        add("cd90", cooldown_sec=90.0)
        add("c200+cd30", confirm_pts=200.0, cooldown_sec=30.0)
        add("c200+cd60", confirm_pts=200.0, cooldown_sec=60.0)
        add("c300+cd30", confirm_pts=300.0, cooldown_sec=30.0)
        add("min1300", min_spike_pts=1300.0)
        add("min1500", min_spike_pts=1500.0)
        add("sl1200", sl_pts=1200.0)
        add("sl800", sl_pts=800.0)
    return jobs


def quiet_last_chance() -> List[Tuple[str, SpikeFadeJobParams]]:
    """If quiet grid found no edge: last try near crisis detect, slightly looser."""
    jobs = []
    for win in (3.0, 3.5, 4.0, 5.0):
        for mn in (800, 900, 1000, 1100):
            p = SpikeFadeJobParams(**asdict(WINNER_94K))
            p.date_from = "2025-01-01"
            p.date_to = "2026-06-01"
            p.window_sec = float(win)
            p.min_spike_pts = float(mn)
            p.confirm_pts = 0.0
            jobs.append((f"lc-win{win}-min{mn}", p))
    return jobs


def run_set(
    name: str,
    jobs: List[Tuple[str, SpikeFadeJobParams]],
    chunks: Optional[List[Tuple[str, str]]],
    date_from: str,
    date_to: str,
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = RESULTS / f"fade_{name}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"SET {name}: {len(jobs)} jobs → {out_dir}")
    rows: List[dict] = []
    n = len(jobs)
    for i, (label, params) in enumerate(jobs, 1):
        params.date_from = date_from
        params.date_to = date_to
        params.workers = 6
        log(f"=== {name} {i}/{n}  {label} ===")
        t0 = time.time()
        try:
            result = execute(params, chunks=chunks)
        except Exception as e:
            log(f"FAILED {label}: {e}")
            traceback.print_exc()
            rows.append({"label": label, "error": str(e)})
            write_summary(out_dir, rows)
            continue
        elapsed = round(time.time() - t0, 1)
        result["label"] = "base" if i == 1 else label
        result["changed"] = name
        result["elapsed_sec"] = elapsed
        slim_r = slim(result)
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)
        (out_dir / f"{i:03d}_{safe}.json").write_text(
            json.dumps(slim_r, indent=2, default=str)
        )
        rows.append(slim_r)
        write_summary(out_dir, rows)
        log(
            f"    → n={result.get('trades')} avg={result.get('avg_pts')} "
            f"PF={result.get('profit_factor')} sum={result.get('sum_pts')} ({elapsed}s)"
        )
        gc.collect()
    write_summary(out_dir, rows)
    log(f"SET {name} done → {out_dir / 'summary.md'}")
    return out_dir


def write_analysis(
    quiet_rows: List[dict],
    jf_rows: List[dict],
    rate: Optional[dict],
    q_best: Optional[dict],
    jf_best: Optional[dict],
    plan: str,
) -> Path:
    path = ROOT / "fade_followup_analysis.md"
    lines = [
        "# Follow-up analysis (auto)",
        "",
        f"Written {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Jan–Feb hunt (busy)",
    ]
    if jf_best:
        lines.append(
            f"Best: **{jf_best.get('label')}** n={jf_best.get('trades')} "
            f"avg={jf_best.get('avg_pts')} PF={jf_best.get('profit_factor')} "
            f"sum={jf_best.get('sum_pts')}"
        )
        lines.append(f"params: `{json.dumps(jf_best.get('params') or {}, default=str)}`")
    else:
        lines.append("No Jan–Feb summary yet — using 94k seed.")
    lines += ["", "## Quiet months"]
    if q_best:
        pf = float(q_best.get("profit_factor") or 0)
        n = int(q_best.get("trades") or 0)
        lines.append(
            f"Best: **{q_best.get('label')}** n={n} avg={q_best.get('avg_pts')} "
            f"PF={pf} sum={q_best.get('sum_pts')}"
        )
        if pf < 1.25 or n < 30:
            lines.append("Judgement: **no usable quiet edge** (PF<1.25 or thin). Last-chance near 1100/3s only.")
        else:
            lines.append("Judgement: refine around this seed.")
    else:
        lines.append("No quiet summary.")
    lines += ["", "## Spike rate (activity meter)"]
    if rate and rate.get("months"):
        for m in rate["months"]:
            h = m.get("per_hour_among_active") or {}
            lines.append(
                f"- **{m.get('month')}**: {m.get('detects')} detects, "
                f"active hours {m.get('hours_with_detect')}, "
                f"median/p90/max per active hour {h.get('median')}/{h.get('p90')}/{h.get('max')}, "
                f"hours≥3/5/10 = {m.get('hours_ge_3')}/{m.get('hours_ge_5')}/{m.get('hours_ge_10')}"
            )
    else:
        lines.append("fade_spike_rate.json not found.")
    lines += ["", "## Plan for the next 3 sets", "", plan]
    path.write_text("\n".join(lines) + "\n")
    log(f"analysis → {path}")
    return path


def main() -> int:
    while still_running():
        log("waiting for quiet + after_quiet (spike-rate, janfeb)…")
        time.sleep(45)
    log("prior pipelines idle — analysing")

    q_dir = latest_dir("fade_quiet_")
    jf_dir = latest_dir("fade_janfeb_")
    q_rows = load_rows(q_dir)
    jf_rows = load_rows(jf_dir)
    rate = None
    rp = RESULTS / "fade_spike_rate.json"
    if rp.exists():
        try:
            rate = json.loads(rp.read_text())
        except Exception:
            rate = None

    jf_best = pick_best(jf_rows, min_trades=80)
    q_best = pick_best(q_rows, min_trades=30)
    q_pf = float((q_best or {}).get("profit_factor") or 0)
    q_n = int((q_best or {}).get("trades") or 0)
    quiet_has_edge = q_best is not None and q_pf >= 1.25 and q_n >= 30

    plan = (
        "1. **Busy** — neighbors around Jan–Feb winner (or 94k seed).\n"
        "2. **Quiet** — "
        + (
            "neighbors around quiet winner.\n"
            if quiet_has_edge
            else "no edge found; last-chance grid min 800–1100 × win 3–5s only.\n"
        )
        + "3. **One-way** — March+June only, 94k detect + confirm/cd (do not loosen min).\n"
    )
    write_analysis(q_rows, jf_rows, rate, q_best, jf_best, plan)

    # --- set 1 busy ---
    if jf_best:
        seed = params_from_row(jf_best, "2026-01-01", "2026-03-01")
    else:
        seed = WINNER_94K
    run_set(
        "busy2",
        neighbors(seed, "busy"),
        chunks=None,
        date_from="2026-01-01",
        date_to="2026-03-01",
    )

    # --- set 2 quiet ---
    if quiet_has_edge:
        qseed = params_from_row(q_best, "2025-01-01", "2026-06-01")
        qjobs = neighbors(qseed, "quiet")
    else:
        qjobs = quiet_last_chance()
    run_set(
        "quiet2",
        qjobs,
        chunks=QUIET_CHUNKS,
        date_from="2025-01-01",
        date_to="2026-06-01",
    )

    # --- set 3 one-way March+June ---
    ow_seed = SpikeFadeJobParams(**asdict(WINNER_94K))
    ow_seed.date_from = "2026-03-01"
    ow_seed.date_to = "2026-07-01"
    run_set(
        "oneway",
        neighbors(ow_seed, "oneway"),
        chunks=ONEWAY_CHUNKS,
        date_from="2026-03-01",
        date_to="2026-07-01",
    )

    log("all 3 follow-up sets done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
