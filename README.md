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

## Asia box tab

5-minute Fibonacci backtest. **Not** the Asia liquidity tab, and **not** Overnight break. Those are other strategies.

Engine `backtest/asia_box.py`. Form `web/asia_box.js` (injected tab). Saved runs `results/asia_box.sqlite`. Catalog http://127.0.0.1:8765/asia-box/results — click a trade for the chart.

Every hour below is **Europe/Chisinau**. Gold: 1 point = $0.01, so a 3000-point minimum box is $30. EURUSD and USDJPY use 0.1 pip per point; the form divides min range and shallow-near by 10 the first time you switch off gold.

**Day**

1. **01:00–06:00** the box high and low keep updating. Fib 0 is the extreme that printed later. Fib 1 is the other side.
2. **Before 03:30, watch only.** No setup may fill. The fib and the arm flags still update, so a reverse can arm at 02:00 and confirm on the first valid close at or after 03:30.
3. Shallow setups wait until **05:30**. EMA retest waits until **07:00**. No new entry at or after **10:00**. Open trades flatten at **13:30**.
4. One open trade. If it exits before 06:00 and the box has grown, a second box may trade.

**Three gates, on by default.** The Session rules card on the tab repeats them, and `GET /api/asia-box/setups` returns the same sentences in `rules[].body`. If a number changes, that sentence is the behavior of the next run. Read it instead of guessing.

| Gate | Default | What it does |
| --- | --- | --- |
| `trade_start_enabled` | 03:30 | No fill before this clock. The box still builds. |
| `continuation_trail` | 2 fib steps | Continuation starts at Fib .786. A new high (long) or new low (short) moves the stop that many steps toward Fib 1, and only tighter. The open trade keeps the fib from the fill. |
| `impulse_freeze` | 40% and 90 min | If the 5m that would fill has a high−low wider than 40% of the box, skip it and block every setup until 90 minutes after that candle **closes**. The box keeps extending during the wait. |

Fib steps walk this ladder toward the stop: `0, .236, .382, .5, .618, .786, 1, 1.618`. "2 steps behind" means the second level strictly past the price. **Fib 0 counts as a step.** A price through Fib 0 stops at **.236**. A price between Fib 0 and .236 stops at **.382**. That .236 stop looks like one step back inside the box. It is still 2.

EMA retest auto-stop uses the same count (`ema_retest_sl_steps`, default 2). The SL field showing 0.382 is used only when Auto is off. Set steps to 3 to put a through-Fib-0 stop at .382. Target stays Fib 0, or the second extension past 0 (−.382) when the fill is already through Fib 0.

**Six setups.** Continuation and the two shallows trade with the box. Reverse Confirm and Reverse EMA trade against it after a 5m **closes** through .786 (a wick does not count). EMA retest follows the 06:00 close versus the box midpoint, not the later-extreme label. Full text is `setups[]` on `/api/asia-box/setups`.

**Check these two mornings.** They are why the freeze exists. Both were catalog Run #14, `reverse_confirm` UP, and both stopped. The signal candle was the entry candle.

| Local morning | Signal candle (local) | Entry timestamp (UTC) | What happened | Box |
| --- | --- | --- | --- | --- |
| 2026-03-16 | 02:00–02:05 | `2026-03-16T00:05:00Z` | −2528 at the stop | 2678 pts, 46% of a 5847-pt box |
| 2026-04-06 | 05:15–05:20 | `2026-04-06T02:20:00Z` | −2998 at the stop | 2893 pts, 45% of a 6493-pt box |

March is also before 03:30, so the watch-only clock blocks it even without the freeze. April is after 03:30, so only the freeze blocks it. A later trade that same local date is allowed. Those two entry timestamps should be absent.

Restart `python webapp.py` if something is already listening on 8765. An old process does not have these rules. `GET /api/asia-box/setups` must contain `"id": "impulse_freeze"` before you trust a run.

```bash
# date_to is exclusive. This window includes both mornings.
curl -s -X POST http://127.0.0.1:8765/api/asia-box/run \
  -H 'content-type: application/json' \
  -d '{"symbol":"XAUUSD","date_from":"2026-03-01","date_to":"2026-04-08","timezone":"Europe/Chisinau"}'
# poll GET /api/asia-box until running is false
```

On the result, `freezes[]` is every skipped signal (`local_date`, `until`, `setup`, `candle_pts`, `box_pts`). A continuation row stores the starting stop in `extras.sl_initial` and the stop at exit in `sl`. They differ when the trail moved. The chart titles that line "SL trailed".

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_asia_box_rules.py -q
```

**Min range.** Default is a fixed point floor (`min_range_pts`, 3000). Switch `min_range_mode` to `pct_price` and the floor is `min_range_bps` times the box midpoint. `0.014` means 1.4%: at a $2500 mid that is 3500 points, at a $2000 mid it is 2800. The percent is not scaled when you switch to EURUSD or USDJPY. The fixed point floor is.

`tests/test_asia_box.py` turns the three session gates off in its helper so the older tests stay about setup geometry.


## Asia liquidity tab

Injected tab (`web/asia_liquidity.js`) for the **Dual-Mode Asia Liquidity Engine** — not the Asia box fib tab above, and not Overnight break.

Overnight break is Bucharest-local Asia + EMA/higher-close pullback, pts, no partials.  
This tab locks a session box and then takes **one** of two plays:

- **Mode A** — continuation: 15m close through the box with body/range quality and 4H EMA50.
- **Mode B** — sweep and reclaim: London takes stops beyond the box, then closes back inside (optional confirm bar).

Never both on the same symbol the same day. Score **profit factor, average R, max DD**, and the Mode A vs Mode B split — not win rate first. If Mode B is near zero EV, disable it.

**Box lock**

- Default: Asia `00:00–07:00 UTC`, frozen at 07:00 UTC.
- Alternate: Asia `00:00–07:00 Europe/Chisinau` (Moldova 07:00 = **04:00 UTC in summer**, **05:00 UTC in winter**). Execution still uses London UTC hours (signals 07:00–11:00 UTC, flatten 16:00 UTC) so a Moldova lock waits for London.

**Filters (skip the day):** box height vs ATR(14, 15m), 20-session compression, gold news calendar (`backtest/xau_news_days.json`), optional spread stub. Live news veto belongs in Reaktor (it already pings a news API).

**Run**

```bash
python webapp.py
# → Asia liquidity tab · GET/POST /api/asia-liquidity, /run, /stop
```

Walk-forward (same fixed rules, no fit) is attached to each saved JSON. From a result file:

```bash
python -m backtest.asia_liquidity_wf results/asialiq_XAUUSD_….json
```

**Live stub** (deterministic JSON signal, no AI direction):

```bash
python live_signal.py --symbol XAUUSD --timezone UTC candles.json
python live_signal.py --symbol XAUUSD --timezone Europe/Chisinau candles.json
```

**TradingView** second opinion: `pine/dual_mode_asia_liquidity.pine` (Pine 15m ≠ Dukascopy mids).

**Forward into Reaktor**

1. Confirm Mode A vs Mode B expectancy on the same years/symbols as the live Overnight bot.
2. Keep only the mode/market that adds R.
3. Wire `live_signal.py` JSON `{symbol, mode, side, entry, stop, tp1, tp2, size, reason}` to a webhook.
4. Leave news blackout to Reaktor’s news API; do not add oscillators.

## Impulse fork tab

Injected tab (`web/impulse_fork.js`) — **not** an Asia box. Classify a 3s gold blast: snapback → fade; hold then 50% retrace → join; three one-way blasts → stand aside. News days allowed. Optional skip 07:00–10:00 UTC so live Asia owns London morning.

Judge PF / avg R / max DD and the Fade vs Join split. Kill Join if its PF &lt; 1. Kill the book if combined PF &lt; 1.2.

```bash
# GET/POST /api/impulse-fork, /run, /stop
```

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
