#!/usr/bin/env python3
"""
Offline research for Reaktor-style alerts on free Dukascopy ticks.

Does NOT touch the live Reaktor process (Telegram / Supabase / Render).

Default analysis mode = **forward** (same idea as Reaktor Performance tab):
  After each alert, over the next H hours:
    hit   = price moved ≥ T points in the alert direction
    clean = hit, and adverse excursion until that first hit stayed ≤ adverse_mult × T

Optional mode = **tp_sl** (broker-style first-touch race).

Examples (Performance-style):

  # +1000 pts within 6h, without −1000 first (clean)
  python run_backtest.py --from 2024-06-01 --to 2024-07-01 \\
      --hours 6 --threshold 1000 --engines candle,spike

  # Several T values like the dashboard
  python run_backtest.py --from 2024-06-01 --to 2024-07-01 \\
      --hours 6 --thresholds 200,500,1000,2000

  # Half-T adverse (like adverse_mult=0.5 script)
  python run_backtest.py --from 2024-06-03 --to 2024-06-06 \\
      --hours 6 --threshold 1000 --adverse-mult 0.5
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.dukascopy import download_range, parse_ymd, reaktor_symbol
from backtest.forward import multi_threshold_report, paths_for_threshold, summarize_forward
from backtest.replay import run_replay
from backtest.trades import simulate_trade, summarize as summarize_trades


def main() -> int:
    p = argparse.ArgumentParser(
        description="Dukascopy tick research for Reaktor-style alerts"
    )
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument(
        "--engines",
        default="candle,spike",
        help="candle = range live, spike",
    )
    p.add_argument(
        "--mode",
        choices=("forward", "tp_sl"),
        default="forward",
        help="forward = Performance-style excursions (default); tp_sl = TP/SL race",
    )
    # Forward mode
    p.add_argument(
        "--hours",
        type=float,
        default=6.0,
        help="Forward window hours (default 6, like 'within following 6 hours')",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Single T in points (e.g. 1000). Or use --thresholds",
    )
    p.add_argument(
        "--thresholds",
        default="100,200,500,1000,2000",
        help="Comma list of T values (ignored if --threshold set)",
    )
    p.add_argument(
        "--adverse-mult",
        type=float,
        default=1.0,
        help="Clean win if adverse until hit ≤ mult×T (1.0 = opp ≤ T; 0.5 = half T)",
    )
    p.add_argument(
        "--sl-manage",
        choices=("off", "be", "lock"),
        default="off",
        help="Factor-style: at ½T move SL to break-even (be) or lock +N pts (lock)",
    )
    p.add_argument(
        "--sl-lock-pts",
        type=float,
        default=100.0,
        help="Points locked in when --sl-manage lock (default 100)",
    )
    # TP/SL mode
    p.add_argument("--tp", type=float, default=None)
    p.add_argument("--sl", type=float, default=None)
    p.add_argument("--price-mode", choices=("spread", "mid"), default="spread")
    p.add_argument("--max-hold-hours", type=float, default=None)

    p.add_argument("--signal-price", choices=("mid", "bid", "ask"), default="mid")
    p.add_argument("--cache", default=str(ROOT / "data" / "dukascopy"))
    p.add_argument("--out", default=str(ROOT / "results"))
    p.add_argument("--force-download", action="store_true")
    p.add_argument(
        "--target-rate",
        type=float,
        default=55.0,
        help="Highlight if clean_rate (forward) or win_rate (tp_sl) ≥ this %%",
    )
    args = p.parse_args()

    start = parse_ymd(args.date_from)
    end = parse_ymd(args.date_to)
    symbol_duka = args.symbol
    symbol = reaktor_symbol(symbol_duka)
    engines = {e.strip() for e in args.engines.split(",") if e.strip()}
    cache_dir = Path(args.cache)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    window_sec = float(args.hours) * 3600.0

    if args.threshold is not None:
        thresholds = [float(args.threshold)]
    else:
        thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]

    print("=== Strateg (standalone research; live Reaktor untouched) ===")
    print(f"  symbol    {symbol_duka} → {symbol}")
    print(f"  window    {start.date()} → {end.date()} UTC")
    print(f"  engines   {sorted(engines)}")
    print(f"  mode      {args.mode}")
    if args.mode == "forward":
        print(
            f"  forward   next {args.hours:g}h | T={thresholds} | "
            f"clean if adv≤{args.adverse_mult:g}×T until hit"
        )
    else:
        print(f"  tp/sl     TP={args.tp} SL={args.sl} mode={args.price_mode}")
    print(f"  cache     {cache_dir}")
    print()

    print("1) Dukascopy ticks…")
    ticks = download_range(
        symbol_duka,
        start,
        end,
        cache_dir=cache_dir,
        force=args.force_download,
    )
    if not ticks:
        print("No ticks. Check dates / symbol / network.")
        return 1
    sample = ticks[len(ticks) // 2]
    print(
        f"   {len(ticks):,} ticks  {ticks[0].ts} → {ticks[-1].ts}\n"
        f"   sample mid={sample.mid:.5f} spread={sample.spread:.5f}"
    )
    print()

    print("2) Replay alerts (same logic family as Reaktor fire rules)…")
    replay = run_replay(
        ticks,
        symbol=symbol,
        engines=engines,
        price_field=args.signal_price,
    )
    by_kind = defaultdict(int)
    for a in replay.alerts:
        by_kind[a.kind] += 1
    print(
        f"   alerts={len(replay.alerts)}  "
        f"candles_completed={replay.candles_completed}"
    )
    for k, v in sorted(by_kind.items()):
        print(f"     {k}: {v}")
    if not replay.alerts:
        print("No alerts — lengthen range or lower floors in backtest/config.py")
        return 0
    print()

    tag_base = (
        f"{symbol_duka}_{args.date_from}_{args.date_to}_{args.mode}"
    ).replace(":", "")

    if args.mode == "forward":
        return _run_forward(
            args,
            ticks,
            replay,
            engines,
            thresholds,
            window_sec,
            out_dir,
            tag_base,
            symbol,
            symbol_duka,
            start,
            end,
        )

    return _run_tp_sl(
        args,
        ticks,
        replay,
        engines,
        out_dir,
        tag_base,
        symbol,
        symbol_duka,
        start,
        end,
    )


def _run_forward(
    args,
    ticks,
    replay,
    engines,
    thresholds,
    window_sec,
    out_dir,
    tag_base,
    symbol,
    symbol_duka,
    start,
    end,
) -> int:
    print(
        "3) Forward path (Performance-style on ticks)…\n"
        "   hit   = fav ≥ T within window\n"
        "   clean = hit AND adverse until that moment ≤ mult×T\n"
        f"   sl_manage = {args.sl_manage}"
        + (
            f" (lock {args.sl_lock_pts:g} pts at ½T)"
            if args.sl_manage == "lock"
            else (" (BE at ½T)" if args.sl_manage == "be" else "")
        )
        + "\n"
    )

    # Primary table: multi-T overall
    multi = multi_threshold_report(
        replay.alerts,
        replay.alert_tick_index,
        ticks,
        thresholds=thresholds,
        window_sec=window_sec,
        adverse_mult=args.adverse_mult,
        sl_manage=args.sl_manage,
        sl_manage_lock_pts=args.sl_lock_pts,
        price_field=args.signal_price,
    )

    print("=== Overall (all engines) ===")
    print(
        f"{'T':>8}  {'n':>5}  {'hit%':>7}  {'clean%':>8}  "
        f"{'clean|hit':>9}  {'avgFav':>7}  {'avgAdv':>7}"
    )
    for key in sorted(multi.keys(), key=lambda x: float(x)):
        s = multi[key]
        flag = ""
        cr = s.get("clean_rate_pct")
        if cr is not None and cr >= args.target_rate:
            flag = "  ✓"
        elif cr is not None:
            flag = ""
        print(
            f"{float(key):>8.0f}  {s['n']:>5}  "
            f"{_fmt_pct(s['hit_rate_pct']):>7}  "
            f"{_fmt_pct(s['clean_rate_pct']):>8}  "
            f"{_fmt_pct(s['clean_given_hit_pct']):>9}  "
            f"{s['avg_max_fav']:>7.0f}  {s['avg_max_adv']:>7.0f}{flag}"
        )

    # Per engine at each T
    for kind in sorted(engines):
        idxs = [
            (a, i)
            for a, i in zip(replay.alerts, replay.alert_tick_index)
            if a.kind == kind
        ]
        if not idxs:
            continue
        al = [x[0] for x in idxs]
        ix = [x[1] for x in idxs]
        sub = multi_threshold_report(
            al,
            ix,
            ticks,
            thresholds=thresholds,
            window_sec=window_sec,
            adverse_mult=args.adverse_mult,
            sl_manage=args.sl_manage,
            sl_manage_lock_pts=args.sl_lock_pts,
            price_field=args.signal_price,
        )
        print(f"\n=== Engine: {kind} ===")
        print(
            f"{'T':>8}  {'n':>5}  {'hit%':>7}  {'clean%':>8}  "
            f"{'clean|hit':>9}"
        )
        for key in sorted(sub.keys(), key=lambda x: float(x)):
            s = sub[key]
            print(
                f"{float(key):>8.0f}  {s['n']:>5}  "
                f"{_fmt_pct(s['hit_rate_pct']):>7}  "
                f"{_fmt_pct(s['clean_rate_pct']):>8}  "
                f"{_fmt_pct(s['clean_given_hit_pct']):>9}"
            )

    # Detail CSV for first / only threshold
    t0 = thresholds[0]
    paths = paths_for_threshold(
        replay.alerts,
        replay.alert_tick_index,
        ticks,
        threshold_pts=t0,
        window_sec=window_sec,
        adverse_mult=args.adverse_mult,
        sl_manage=args.sl_manage,
        sl_manage_lock_pts=args.sl_lock_pts,
        price_field=args.signal_price,
    )
    csv_path = out_dir / f"forward_{tag_base}_T{int(t0)}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "kind",
                "side",
                "alert_ts",
                "entry",
                "T",
                "adverse_limit",
                "hit",
                "clean",
                "first_touch",
                "max_fav",
                "max_adv",
                "max_adv_until_hit",
                "first_hit_sec",
                "meta_json",
            ]
        )
        for path in paths:
            a = path.alert
            w.writerow(
                [
                    a.kind,
                    a.side,
                    a.ts.isoformat(),
                    f"{a.price:.6f}",
                    path.threshold_pts,
                    path.adverse_limit_pts,
                    int(path.hit),
                    int(path.clean),
                    path.first_touch or "",
                    f"{path.max_fav_pts:.1f}",
                    f"{path.max_adv_pts:.1f}",
                    f"{path.max_adv_until_hit:.1f}",
                    f"{path.first_hit_sec:.1f}" if path.first_hit_sec is not None else "",
                    json.dumps(a.meta, default=str),
                ]
            )

    json_path = out_dir / f"summary_{tag_base}.json"
    payload = {
        "mode": "forward",
        "symbol": symbol,
        "duka_symbol": symbol_duka,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "hours": args.hours,
        "window_sec": window_sec,
        "adverse_mult": args.adverse_mult,
        "thresholds": thresholds,
        "engines": sorted(engines),
        "ticks": len(ticks),
        "alerts": len(replay.alerts),
        "overall": multi,
        "semantics": {
            "hit": "favorable excursion ≥ T within window",
            "clean": "hit and max adverse until first T ≤ adverse_mult × T",
            "note": (
                "Matches Reaktor Performance intent; path is tick-order accurate "
                "(live dashboard uses 15m bars)."
            ),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {csv_path}")
    print(f"Wrote {json_path}")
    print(
        f"\nTarget {args.target_rate:g}% refers to **clean_rate** "
        f"(fav T without adverse mult×T first)."
    )
    return 0


def _run_tp_sl(
    args,
    ticks,
    replay,
    engines,
    out_dir,
    tag_base,
    symbol,
    symbol_duka,
    start,
    end,
) -> int:
    if args.tp is None or args.sl is None:
        print("tp_sl mode requires --tp and --sl")
        return 2
    print("3) TP/SL first-touch simulation…")
    max_hold = (
        args.max_hold_hours * 3600.0 if args.max_hold_hours is not None else None
    )
    trades = [
        simulate_trade(
            alert,
            ticks,
            tp_pts=args.tp,
            sl_pts=args.sl,
            mode=args.price_mode,
            max_hold_sec=max_hold,
            start_index=idx,
        )
        for alert, idx in zip(replay.alerts, replay.alert_tick_index)
    ]
    overall = summarize_trades(trades)
    print()
    print("=== Results ===")
    _print_trade_summary("ALL", overall, args.target_rate)
    for kind in sorted(engines):
        sub = [t for t in trades if t.alert.kind == kind]
        if sub:
            _print_trade_summary(kind, summarize_trades(sub), args.target_rate)

    csv_path = out_dir / f"trades_{tag_base}_tp{int(args.tp)}_sl{int(args.sl)}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "kind",
                "side",
                "alert_ts",
                "entry",
                "tp",
                "sl",
                "outcome",
                "exit_price",
                "hold_sec",
                "win",
            ]
        )
        for t in trades:
            w.writerow(
                [
                    t.alert.kind,
                    t.side,
                    t.alert.ts.isoformat(),
                    f"{t.entry:.6f}",
                    f"{t.tp:.6f}",
                    f"{t.sl:.6f}",
                    t.outcome,
                    f"{t.exit_price:.6f}" if t.exit_price is not None else "",
                    f"{t.hold_sec:.1f}" if t.hold_sec is not None else "",
                    "" if t.win is None else int(t.win),
                ]
            )
    json_path = out_dir / f"summary_{tag_base}.json"
    json_path.write_text(
        json.dumps(
            {
                "mode": "tp_sl",
                "symbol": symbol,
                "tp": args.tp,
                "sl": args.sl,
                "overall": overall,
            },
            indent=2,
        )
    )
    print(f"\nWrote {csv_path}")
    return 0


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}%"


def _print_trade_summary(label: str, s: dict, target: float) -> None:
    flag = ""
    if s["closed"] > 0:
        flag = " ✓" if s["win_rate_pct"] >= target else ""
    print(
        f"  [{label}] closed={s['closed']}  W/L={s['wins']}/{s['losses']}  "
        f"win_rate={s['win_rate_pct']:.1f}%{flag}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
