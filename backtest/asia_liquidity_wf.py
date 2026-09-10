"""Walk-forward folds for Dual-Mode Asia Liquidity (report only, no fit)."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from backtest.asia_liquidity import AsiaLiqParams, AsiaLiqTrade, summarize_asia_liq


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + int(months)
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def walk_forward_folds(
    start: date,
    end: date,
    *,
    train_months: int = 18,
    test_months: int = 6,
) -> List[Dict[str, date]]:
    """Rolling 18m train / 6m test. Test starts where train ends (no leak)."""
    if end <= start:
        return []
    folds: List[Dict[str, date]] = []
    train_from = start
    while True:
        train_to = _add_months(train_from, train_months)
        test_to = _add_months(train_to, test_months)
        if train_to >= end:
            break
        if test_to > end:
            test_to = end
        if train_to >= test_to:
            break
        folds.append(
            {
                "train_from": train_from,
                "train_to": train_to,
                "test_from": train_to,
                "test_to": test_to,
            }
        )
        train_from = _add_months(train_from, test_months)
        if train_from >= end:
            break
    return folds


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def slice_rows(
    rows: Sequence[Dict[str, Any]],
    start: date,
    end: date,
) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        d = _as_date(r.get("local_date"))
        if d is None:
            continue
        if start <= d < end:
            out.append(r)
    return out


def fold_stats(
    result: Dict[str, Any],
    *,
    train_months: int = 18,
    test_months: int = 6,
) -> List[Dict[str, Any]]:
    """Slice an already-run result into train/test folds (no re-download)."""
    rows = result.get("rows") or []
    if not rows:
        return []
    dates = [_as_date(r.get("local_date")) for r in rows]
    dates = [d for d in dates if d is not None]
    if not dates:
        return []
    start, end = min(dates), max(dates) + timedelta(days=1)
    params = result.get("params") or {}
    try:
        p = AsiaLiqParams(**{k: v for k, v in params.items() if k in AsiaLiqParams.__dataclass_fields__})
    except TypeError:
        p = AsiaLiqParams()
    symbol = result.get("symbol") or "XAU/USD"
    folds = walk_forward_folds(start, end, train_months=train_months, test_months=test_months)
    out: List[Dict[str, Any]] = []
    fields = AsiaLiqTrade.__dataclass_fields__
    for fold in folds:
        train_rows = slice_rows(rows, fold["train_from"], fold["train_to"])
        test_rows = slice_rows(rows, fold["test_from"], fold["test_to"])

        def as_trades(rs: List[Dict[str, Any]]) -> List[AsiaLiqTrade]:
            trades: List[AsiaLiqTrade] = []
            for r in rs:
                try:
                    trades.append(AsiaLiqTrade(**{k: r[k] for k in fields if k in r}))
                except TypeError:
                    continue
            return trades

        train_sum = summarize_asia_liq(as_trades(train_rows), [], p, symbol=symbol, ticks=0)
        test_sum = summarize_asia_liq(as_trades(test_rows), [], p, symbol=symbol, ticks=0)
        out.append(
            {
                "train_from": fold["train_from"].isoformat(),
                "train_to": fold["train_to"].isoformat(),
                "test_from": fold["test_from"].isoformat(),
                "test_to": fold["test_to"].isoformat(),
                "train": {
                    "trades": train_sum.get("trades"),
                    "win_pct": train_sum.get("win_pct"),
                    "profit_factor": train_sum.get("profit_factor"),
                    "avg_r": train_sum.get("avg_r"),
                    "sum_r": train_sum.get("sum_r"),
                    "by_mode": train_sum.get("by_mode"),
                },
                "test": {
                    "trades": test_sum.get("trades"),
                    "win_pct": test_sum.get("win_pct"),
                    "profit_factor": test_sum.get("profit_factor"),
                    "avg_r": test_sum.get("avg_r"),
                    "sum_r": test_sum.get("sum_r"),
                    "by_mode": test_sum.get("by_mode"),
                },
            }
        )
    return out


def print_report(folds: Sequence[Dict[str, Any]]) -> None:
    if not folds:
        print("No walk-forward folds (need a longer date range).")
        return
    print("Walk-forward (fixed rules, no fit)  train 18m / test 6m")
    print(f"{'train':<23} {'test':<23} {'trN':>5} {'trPF':>6} {'trR':>7} {'teN':>5} {'tePF':>6} {'teR':>7}")
    for f in folds:
        tr, te = f["train"], f["test"]
        print(
            f"{f['train_from']}→{f['train_to']:<10} "
            f"{f['test_from']}→{f['test_to']:<10} "
            f"{tr.get('trades') or 0:5} {tr.get('profit_factor') or 0:6} "
            f"{tr.get('avg_r') or 0:7} {te.get('trades') or 0:5} "
            f"{te.get('profit_factor') or 0:6} {te.get('avg_r') or 0:7}"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Print walk-forward folds from a saved asia_liquidity JSON")
    ap.add_argument("result_json", nargs="?", help="results/asialiq_*.json")
    ap.add_argument("--from", dest="date_from", default=None)
    ap.add_argument("--to", dest="date_to", default=None)
    ap.add_argument("--train-months", type=int, default=18)
    ap.add_argument("--test-months", type=int, default=6)
    args = ap.parse_args(argv)
    if args.result_json:
        blob = json.loads(open(args.result_json, encoding="utf-8").read())
        folds = fold_stats(
            blob, train_months=args.train_months, test_months=args.test_months
        )
        print_report(folds)
        return 0
    if args.date_from and args.date_to:
        folds = walk_forward_folds(
            date.fromisoformat(args.date_from),
            date.fromisoformat(args.date_to),
            train_months=args.train_months,
            test_months=args.test_months,
        )
        for f in folds:
            print(
                f"train {f['train_from']} → {f['train_to']}  "
                f"test {f['test_from']} → {f['test_to']}"
            )
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
