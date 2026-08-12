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
