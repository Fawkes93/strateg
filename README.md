# Strateg — local forward research for Reaktor-style alerts

**100% local.** No Telegram, no Supabase, no Render. Does not touch the live Reaktor bot.

## Pipeline (yes, this is the idea)

```text
Dukascopy ticks (free)
        ↓
1) Generate alerts with duplicated Reaktor fire rules
   (range live + spike, floors in backtest/config.py)
        ↓
2) For each alert, walk the *same* tick stream forward
   → hit / clean rates (like Reaktor Performance page)
```

You are **not** reading live Supabase history. Alerts are produced offline, then scored on Dukascopy path data.

## Local web UI (recommended)

```bash
cd ~/strateg
source ~/reaktor/.venv/bin/activate   # Python 3.10+
pip install -r requirements.txt
python webapp.py
# → http://127.0.0.1:8765
```

Params similar to Performance: date range, look-ahead (6/12/24h), target T, opposite % of T, engines.  
Progress bar shows download → replay → forward scoring.

Default week in the UI: **2025-03-03 → 2025-03-10** (March week; change freely).


## Inverse FVG tab

Injected UI tab (`web/fvg.js`) for **Inverse FVG after a liquidity raid** (SSL/BSL → FVG → close through P → retrace into CE↔P).  
Candles: 15m from ticks; 30/60/240 via `backtest/aggregate.py` (ported from Reaktor).  
Scoring matches Research: look-ahead hours + T pts + opposite% hit/clean. Endpoints: `GET/POST /api/fvg`, `/api/fvg/run`, `/api/fvg/stop`.

Optional param **`entry_hours_utc`** (list of ints, or empty/omit = all hours): only fire an entry when the fill tick’s UTC hour is in the set.  
Optional param **`entry_weekdays`** (list of ints `0=Mon..6=Sun`, or empty/omit = all days): same filter on the fill tick’s UTC weekday (combinable with hours).  
Research example (not hardcoded): Monday + hours UTC 7–12 → clean ~67.6% (2025 May–Sep n=37) / ~63.6% (2026 Jun–Sep n=22) at T=100; Monday-only ~62% / ~59%. Re-check on **2025 and 2026** XAUUSD windows before treating any set as a default.  
Older hour-only note: May–Sep 2025 (589 trades, T=100) suggested `{4,15,17,19,22}` → 66% clean n=100, or expanded `{4,5,8,15,17,22}` → 62% n=148 — **example suggestions only**.

## CLI (same engine)

```bash
python run_backtest.py \
  --symbol XAUUSD \
  --from 2025-03-03 --to 2025-03-10 \
  --hours 6 \
  --thresholds 100,200,500,1000,2000 \
  --engines candle,spike
```

## Semantics

| Term | Meaning |
|------|---------|
| **hit** | Favorable ≥ **T** pts within look-ahead window |
| **clean** | hit **and** adverse until first touch of T ≤ **opp% × T** |

## Layout

```text
strateg/
├── webapp.py            # local FastAPI UI
├── web/                 # static UI
├── run_backtest.py      # CLI
├── backtest/
│   ├── config.py        # signal floors (edit for research)
│   ├── candles.py / range_live.py / spike.py
│   ├── dukascopy.py     # free bi5 download
│   ├── replay.py        # ticks → alerts
│   ├── forward.py       # hit / clean
│   └── jobs.py          # background job + progress
├── data/dukascopy/      # tick cache
└── results/             # JSON summaries
```
