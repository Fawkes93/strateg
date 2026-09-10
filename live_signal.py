#!/usr/bin/env python3
"""
Deterministic Dual-Mode Asia Liquidity signal stub.

Reads closed 15m candles (JSON array or CSV) and prints one JSON object:
  {symbol, mode, side, entry, stop, tp1, tp2, size, reason, r_distance, flatten_utc}

No AI direction. Wire later to Reaktor / a broker webhook.
Live news veto belongs in Reaktor (it already pings a news API) — pass
news_windows here only if you want a local skip.

Usage:
  python live_signal.py --symbol XAUUSD candles.json
  python live_signal.py --symbol XAUUSD --csv candles.csv
  python live_signal.py --timezone Europe/Chisinau candles.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from backtest.asia_liquidity import AsiaLiqParams, signal_from_candles
from backtest.candles import Candle, to_utc


def _parse_time(val: Any) -> datetime:
    if isinstance(val, datetime):
        return to_utc(val)
    s = str(val).replace("Z", "+00:00")
    return to_utc(datetime.fromisoformat(s))


def candles_from_rows(rows: Sequence[Dict[str, Any]]) -> List[Candle]:
    out: List[Candle] = []
    for r in rows:
        ot = _parse_time(r.get("open_time") or r.get("time") or r.get("timestamp"))
        ct = r.get("close_time")
        close_time = _parse_time(ct) if ct else ot + timedelta(minutes=15)
        closed = r.get("is_closed")
        if closed is None:
            closed = True
        out.append(
            Candle(
                open_time=ot,
                close_time=close_time,
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                is_closed=bool(closed),
            )
        )
    out.sort(key=lambda c: c.open_time)
    return out


def load_json(path: Path) -> List[Dict[str, Any]]:
    blob = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(blob, dict):
        blob = blob.get("candles") or blob.get("rows") or blob.get("data") or []
    if not isinstance(blob, list):
        raise ValueError("JSON must be a list of OHLC rows")
    return blob


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def emit_signal(
    candles: Sequence[Candle],
    *,
    symbol: str = "XAUUSD",
    params: Optional[AsiaLiqParams] = None,
    asof: Optional[datetime] = None,
    spread: Optional[float] = None,
    equity: float = 1_000.0,
) -> Dict[str, Any]:
    return signal_from_candles(
        candles,
        symbol=symbol,
        params=params,
        asof=asof,
        spread=spread,
        equity=equity,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Asia liquidity live signal (deterministic)")
    ap.add_argument("path", nargs="?", help="JSON or CSV of 15m OHLC")
    ap.add_argument("--csv", dest="csv_path", default=None)
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--timezone", default="UTC", help="UTC or Europe/Chisinau (Moldova 07:00 lock)")
    ap.add_argument("--exec-timezone", default="UTC")
    ap.add_argument("--risk-pct", type=float, default=0.5)
    ap.add_argument("--equity", type=float, default=1_000.0)
    ap.add_argument("--spread", type=float, default=None)
    ap.add_argument("--asof", default=None, help="ISO UTC; default = last closed bar")
    args = ap.parse_args(argv)

    path = Path(args.csv_path or args.path or "")
    if not path or not path.exists():
        ap.print_help()
        return 2
    rows = load_csv(path) if args.csv_path or path.suffix.lower() == ".csv" else load_json(path)
    candles = candles_from_rows(rows)
    asof = to_utc(datetime.fromisoformat(args.asof.replace("Z", "+00:00"))) if args.asof else None
    params = AsiaLiqParams(
        timezone=args.timezone,
        exec_timezone=args.exec_timezone,
        risk_pct=args.risk_pct,
        start_equity=args.equity,
        news_mode="off",
        spread_filter=False,
    )
    out = emit_signal(
        candles,
        symbol=args.symbol,
        params=params,
        asof=asof,
        spread=args.spread,
        equity=args.equity,
    )
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
