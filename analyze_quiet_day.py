#!/usr/bin/env python3
"""One-day quiet-tape autopsy. Not part of the overnight hunt."""

from __future__ import annotations

import math
import sys
from collections import deque
from datetime import datetime, timezone
from typing import List, Optional, Tuple

ROOT = __file__.rsplit("/", 1)[0]
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backtest.runner import load_ticks
from backtest.config import point_size

PS = point_size("XAU/USD")  # 0.01


def hour_utc(ts: datetime) -> int:
    return ts.hour


def scan_candidates(ticks, window_sec: float, min_pts: float, cooldown_sec: float = 30.0):
    """Same detect as spike_fade, but record extra features and forward path."""
    dq: deque = deque()
    win_hi = float("-inf")
    win_lo = float("inf")
    cool_until = 0.0
    out = []
    n = len(ticks)
    # also keep a longer history for pre-range / drift
    hist: deque = deque()  # (epoch, mid)
    hist_sec = 900.0

    for i, t in enumerate(ticks):
        ts = t.ts if t.ts.tzinfo else t.ts.replace(tzinfo=timezone.utc)
        epoch = ts.timestamp()
        px = t.mid
        spread_pts = t.spread / PS if PS else 0.0

        hist.append((epoch, px))
        while hist and hist[0][0] < epoch - hist_sec:
            hist.popleft()

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
            win_hi = max(prices)
            win_lo = min(prices)
        elif not dq:
            win_hi, win_lo = float("-inf"), float("inf")
            continue

        if epoch < cool_until or len(dq) < 2:
            continue
        ref_ts, ref = dq[0]
        last_ts, last = dq[-1]
        span = last_ts - ref_ts
        if span < min(0.4, window_sec * 0.25):
            continue
        up = (win_hi - ref) / PS
        down = (ref - win_lo) / PS
        if up >= down and up >= min_pts:
            spike_dir, spike_pts, extreme = "UP", up, win_hi
        elif down > up and down >= min_pts:
            spike_dir, spike_pts, extreme = "DOWN", down, win_lo
        else:
            continue

        # time of extreme (last tick that printed it)
        ext_ts = ref_ts
        for e, p in dq:
            if spike_dir == "UP" and abs(p - extreme) < 1e-12:
                ext_ts = e
            if spike_dir == "DOWN" and abs(p - extreme) < 1e-12:
                ext_ts = e
        extreme_age = epoch - ext_ts
        impulse_sec = max(1e-6, ext_ts - ref_ts)
        speed = spike_pts / impulse_sec

        # pre-range: the hist BEFORE the detect window
        pre_lo, pre_hi = None, None
        pre_from = cutoff - 60.0
        pre_to = cutoff
        for e, p in hist:
            if pre_from <= e < pre_to:
                if pre_lo is None or p < pre_lo:
                    pre_lo = p
                if pre_hi is None or p > pre_hi:
                    pre_hi = p
        pre60 = ((pre_hi - pre_lo) / PS) if pre_lo is not None else None

        pre_lo, pre_hi = None, None
        pre_from = cutoff - 30.0
        for e, p in hist:
            if pre_from <= e < pre_to:
                if pre_lo is None or p < pre_lo:
                    pre_lo = p
                if pre_hi is None or p > pre_hi:
                    pre_hi = p
        pre30 = ((pre_hi - pre_lo) / PS) if pre_lo is not None else None

        # net drift last 5 / 15 min (signed in spike direction)
        def drift(sec: float) -> Optional[float]:
            old = None
            for e, p in hist:
                if e <= epoch - sec:
                    old = p
                else:
                    break
            if old is None:
                return None
            raw = (px - old) / PS
            return raw if spike_dir == "UP" else -raw

        d5 = drift(300.0)
        d15 = drift(900.0)

        fade_side = "DOWN" if spike_dir == "UP" else "UP"
        entry = last
        # forward path
        fwd = []
        j = i + 1
        end_epoch = epoch + 320.0
        while j < n:
            tj = ticks[j]
            te = (tj.ts if tj.ts.tzinfo else tj.ts.replace(tzinfo=timezone.utc)).timestamp()
            if te > end_epoch:
                break
            fwd.append((te - epoch, tj.mid))
            j += 1

        def fav(mid: float) -> float:
            if fade_side == "UP":
                return (mid - entry) / PS
            return (entry - mid) / PS

        mfe = mae = 0.0
        t_mfe = t_mae = None
        at = {5: None, 15: None, 30: None, 60: None, 120: None, 250: None}
        hit_p600 = hit_m400 = None
        for dt, mid in fwd:
            f = fav(mid)
            if f > mfe:
                mfe = f
                t_mfe = dt
            if f < mae:
                mae = f
                t_mae = dt
            for k in at:
                if at[k] is None and dt >= k:
                    at[k] = f
            if hit_p600 is None and f >= 600:
                hit_p600 = dt
            if hit_m400 is None and f <= -400:
                hit_m400 = dt

        # first-touch: +600 vs -400 (quiet-sized targets)
        if hit_p600 is not None and (hit_m400 is None or hit_p600 <= hit_m400):
            first = "win600"
        elif hit_m400 is not None:
            first = "lose400"
        else:
            first = "neither"

        out.append(
            {
                "ts": ts.isoformat(),
                "hour": ts.hour,
                "spike_dir": spike_dir,
                "fade": fade_side,
                "spike": round(spike_pts, 1),
                "span": round(span, 3),
                "impulse_sec": round(impulse_sec, 3),
                "extreme_age": round(extreme_age, 3),
                "speed": round(speed, 1),
                "pre30": None if pre30 is None else round(pre30, 1),
                "pre60": None if pre60 is None else round(pre60, 1),
                "drift5": None if d5 is None else round(d5, 1),
                "drift15": None if d15 is None else round(d15, 1),
                "spread": round(spread_pts, 1),
                "mfe": round(mfe, 1),
                "mae": round(mae, 1),
                "t_mfe": None if t_mfe is None else round(t_mfe, 2),
                "first": first,
                "at30": None if at[30] is None else round(at[30], 1),
                "at60": None if at[60] is None else round(at[60], 1),
                "at250": None if at[250] is None else round(at[250], 1),
            }
        )
        cool_until = epoch + cooldown_sec
    return out


def bucket(vals, edges):
    labels = []
    for i, e in enumerate(edges):
        if i == 0:
            labels.append(f"<{e:g}")
        else:
            labels.append(f"{edges[i-1]:g}–{e:g}")
    labels.append(f">={edges[-1]:g}")
    counts = [0] * (len(edges) + 1)
    wins = [0] * (len(edges) + 1)
    mfe_s = [0.0] * (len(edges) + 1)
    for v, win, mfe in vals:
        if v is None:
            continue
        idx = len(edges)
        for i, e in enumerate(edges):
            if v < e:
                idx = i
                break
        counts[idx] += 1
        wins[idx] += 1 if win else 0
        mfe_s[idx] += mfe
    lines = []
    for i, lab in enumerate(labels):
        if counts[i] == 0:
            continue
        wr = 100.0 * wins[i] / counts[i]
        lines.append(
            f"  {lab:>12}  n={counts[i]:3d}  win600={wr:5.1f}%  avgMFE={mfe_s[i]/counts[i]:6.0f}"
        )
    return lines


def report(day: str, ticks, specs: List[Tuple[float, float]]):
    print(f"\n{'='*72}")
    print(f"{day}  ticks={len(ticks):,}  first={ticks[0].ts}  last={ticks[-1].ts}")
    mids = [t.mid for t in ticks]
    day_range = (max(mids) - min(mids)) / PS
    print(f"day range {day_range:.0f} pts  ({min(mids):.2f}–{max(mids):.2f})")
    spreads = [(t.ask - t.bid) / PS for t in ticks[::50]]
    spreads.sort()
    print(
        f"spread pts p50={spreads[len(spreads)//2]:.0f}  "
        f"p90={spreads[int(len(spreads)*0.9)]:.0f}  "
        f"p99={spreads[int(len(spreads)*0.99)]:.0f}"
    )

    for win, mn in specs:
        ev = scan_candidates(ticks, win, mn, cooldown_sec=30.0)
        if not ev:
            print(f"\n-- win={win:g} min={mn:g}: 0 detects --")
            continue
        wins = sum(1 for e in ev if e["first"] == "win600")
        losses = sum(1 for e in ev if e["first"] == "lose400")
        neither = sum(1 for e in ev if e["first"] == "neither")
        avg_mfe = sum(e["mfe"] for e in ev) / len(ev)
        avg_mae = sum(e["mae"] for e in ev) / len(ev)
        print(
            f"\n-- win={win:g} min={mn:g}: n={len(ev)}  "
            f"+600 first={wins}  -400 first={losses}  neither={neither}  "
            f"avgMFE={avg_mfe:.0f} avgMAE={avg_mae:.0f}"
        )
        # hour
        by_h = {}
        for e in ev:
            by_h.setdefault(e["hour"], [0, 0])
            by_h[e["hour"]][0] += 1
            if e["first"] == "win600":
                by_h[e["hour"]][1] += 1
        busy = sorted(by_h.items(), key=lambda kv: -kv[1][0])[:6]
        print("  hours UTC (n/win600): " + ", ".join(f"{h}h {n}/{w}" for h, (n, w) in busy))

        print("  pre30 range (compression before the detect window):")
        print(
            "\n".join(
                bucket([(e["pre30"], e["first"] == "win600", e["mfe"]) for e in ev], [150, 250, 400, 700])
            )
            or "    (no pre30)"
        )
        print("  impulse speed (pts / sec to extreme):")
        print(
            "\n".join(
                bucket([(e["speed"], e["first"] == "win600", e["mfe"]) for e in ev], [20, 50, 100, 200])
            )
        )
        print("  15m drift in spike direction (pts):")
        print(
            "\n".join(
                bucket([(e["drift15"], e["first"] == "win600", e["mfe"]) for e in ev], [-200, 200, 600, 1500])
            )
        )
        print("  extreme age (sec):")
        print(
            "\n".join(
                bucket([(e["extreme_age"], e["first"] == "win600", e["mfe"]) for e in ev], [0.3, 1.0, 3.0, 8.0])
            )
        )

        # show a few examples
        ev_s = sorted(ev, key=lambda e: -e["mfe"])
        print("  best MFE:")
        for e in ev_s[:3]:
            print(
                f"    {e['ts'][11:19]} {e['spike_dir']:4} {e['spike']:.0f}pt  "
                f"spd={e['speed']:.0f} pre30={e['pre30']} d15={e['drift15']}  "
                f"MFE={e['mfe']:.0f} MAE={e['mae']:.0f} {e['first']}"
            )
        print("  worst MAE:")
        for e in sorted(ev, key=lambda e: e["mae"])[:3]:
            print(
                f"    {e['ts'][11:19]} {e['spike_dir']:4} {e['spike']:.0f}pt  "
                f"spd={e['speed']:.0f} pre30={e['pre30']} d15={e['drift15']}  "
                f"MFE={e['mfe']:.0f} MAE={e['mae']:.0f} {e['first']}"
            )


def main() -> int:
    days = sys.argv[1:] or ["2025-04-16", "2025-07-16"]
    specs = [
        (3.0, 400.0),
        (3.0, 800.0),
        (15.0, 400.0),
        (30.0, 400.0),
        (60.0, 400.0),
        (60.0, 600.0),
    ]
    for day in days:
        y, m, d = (int(x) for x in day.split("-"))
        nxt = f"{y:04d}-{m:02d}-{d+1:02d}" if d < 28 else None
        # compute next day safely
        from datetime import date, timedelta

        a = date(y, m, d)
        b = a + timedelta(days=1)
        date_from = a.isoformat()
        date_to = b.isoformat()
        print(f"\nloading {date_from} → {date_to} …", flush=True)
        ticks = load_ticks(symbol="XAUUSD", date_from=date_from, date_to=date_to)
        report(date_from, ticks, specs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
