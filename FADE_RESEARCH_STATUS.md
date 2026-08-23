# Spike fade research — where we are

Read this first if the chat was compacted. Project: **Strateg** (`/Users/carauslivian/strateg`), local Dukascopy tick backtester + FastAPI UI on `:8765`. Live MT5 bot is a *separate* Windows job (see `SPIKE_FADE_MT5_BOT_BRIEF.md`); this file is the **backtest** thread.

## North star (why we are running all these grids)

Find an **edge that is real in some tapes and dead in others**, then make the live bot **switch behaviour from data**, not from a fixed 1100/3s forever.

**Switcher plan (hot / quiet / stand aside):** `FADE_REGIME_SWITCH.md`.

Not “one combo for 19 months.” That 94k is almost entirely Jan–Feb 2026. A static EA will either:

- sit idle 10 months a year (1100/3s on quiet gold), or
- print junk if we loosen detect to stay busy (quiet-base: 226 trades, avg 25, PF 1.11).

**Product:** measure a few tape stats every N minutes → classify regime → apply a **preset** (or flatten / do not enter).

What we think *matters* (to confirm with spike-rate + more grids):

1. **How often** a 1100-pt / 3s spike happens (last 30–60 min, per hour).
2. **Whether those spikes snap back** (retrace 300+ pts within ~10s) vs keep going.
3. **Net drift** that hour (one-way March vs two-way Jan).
4. **Spread** at detect (live).

What probably does *not* need to be dynamic: TP (almost never hits), weekend skip, point size. Trail/arm/hold only after we know we are in the “hot two-way” bucket.

Regimes we are trying to prove:

| Regime | Tape | Bot |
|---|---|---|
| Quiet | ~0 crisis-detects / hour | **off** (do not lower min to invent trades) |
| Two-way hot | many detects, both ways, trails work | **94k-style** (or better Jan–Feb winner) |
| One-way hot | many detects, no snap-back, SL% blows out | **off** or confirm + longer cooldown |

The grids (quiet months vs Jan–Feb only vs March post-mortem) exist to **fit those presets**, not to find one magic row for the whole sample.

XAU **1 pt = $0.01**. At **0.01 lot**, 100 pts ≈ $1. Backtest fills are **mid** (live will be worse).

---

## Best sum so far (19 months: 2025-01-01 → 2026-08-01)

| window | min | TP | SL | trail | arm | hold | cd | lag | weekend | trades | avg | PF | **sum** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **3.0** | **1100** | 3000 | 1000 | 500 | **700** | **320** | **0** | 1 | 10 | 549 | 172 | 1.47 | **94,453** |
| 3.0 | 1100 | 3000 | 1000 | 500 | 700 | 200 | 0 | 1 | 10 | 549 | 167 | 1.46 | 91,794 |
| 2.8 | 1100 | 3000 | 1000 | 500 | 700 | 320 | 30 | 1 | 10 | 351 | 201 | 1.57 | 70,596 |

**94k is not a typical year.** Monthly file: `fade_sum_winner_monthly.md`

- **2026-01:** 218 trades, +60,205 (crisis melt-up + crash)
- **2026-02:** 178 trades, +33,600 (aftershock chop)
- **2026-03:** 76 trades, **−10,798** (one-way dump)
- **2026-06:** 10 trades, **−6,472** (hawkish grind)
- Most other months: **0–6 trades**

346 winners / 200 losers / 3 flat on the 94k combo.

---

## Why those months

**Jan–Feb 2026 — two-way violence (paid).** Gold ran to ~**$5,595** (29 Jan), then one of the worst 1–2 day gold crashes in decades (Warsh Fed-chair / dollar / leverage). $11 (1100 pt) / 3s spikes fire constantly and often snap back → trail/arm gets paid.

**March — still violent, wrong direction (lost).** Worst gold month since 2013 (~12% down). Real yields + dollar + Iran/Hormuz *failed* as a haven. Spikes **continue**, SL 1000 gets run. 51% win. See `fade_march_june_quiet_months.md`.

**June — thin + one-way (lost).** Hawkish repricing, gold through $4,100/$4,000. Only 10 tickets, 7 losers.

**Quiet months — detect never fires** at 1100/3s. Lowering min to “make” trades looks like PF ~1.1 (first quiet-base print). Do **not** loosen detect just to stay busy.

---

## Activity meter (to refine after spike-rate job)

Classifier uses the **crisis detect** (1100 pts / 3s) as a thermometer, not a second strategy.

| Regime | Idea | Preset |
|---|---|---|
| Quiet | almost no 1100/3s events | **don’t trade** (or keep 1100/3s and accept 0–6/month) |
| Two-way hot | many 1100/3s, both ways, trails working | **94k combo** |
| One-way hot | many 1100/3s, no snap-back, SL% exploding | **off** or add **confirm** + longer cd |

“Several / hour” was a guess. **Next job** (`run_fade_spike_rate.py`) counts raw 1100/3s **detections per hour** for Jan, Feb, Mar 2026 (and a quiet month) so we can put real numbers on Feb vs March. Trades ≠ spikes (an open 320s hold blocks new entries).

---

## Sweeps

| Wave | What | Status / folder |
|---|---|---|
| OAT 1+2 | one-knob around 3s/1100 screenshot | done `results/fade_oat_*` |
| Wave 3 | 2.8 window + confirm + arm | done `results/fade_oat_w3_*` |
| Arm700 holds | hold 200–360… (aborted after 360) | 320 won that slice |
| cd0+arm700 | 3s/1100/arm700/cd0 hold 200 & 320 | done — **94k** |
| 2.8 cd30 | hold 200 & 320 | done — 70.6k |
| **Quiet months** | 12 thin months, looser detect | **running** `results/fade_quiet_20260814T195929` · log `results/fade_quiet.log` |
| **Spike rate** | hourly 1100/3s counts Jan–Mar (+ May) | **queued** after quiet |
| **Jan–Feb only** | beat ~94k on the two months that made it | **queued** after spike rate |

---

## Queued after quiet finishes

1. `run_fade_spike_rate.py` → `results/fade_spike_rate.json` + prints hourly stats  
2. `run_fade_janfeb.py` → only **2026-01-01 → 2026-03-01**, ~44 jobs around the 94k combo (window, min, hold, SL, trail, arm, cd, lag)

Pipeline: `run_fade_after_quiet.py` then `run_fade_followup.py`

**Follow-up (unattended, after those finish):** analyses quiet + Jan–Feb + spike-rate → `fade_followup_analysis.md`, then 3 sets:

1. **busy2** — neighbors around Jan–Feb winner (window/min/hold/SL/arm)
2. **quiet2** — refine quiet winner if PF≥1.25; else last-chance min 800–1100 × win 3–5s only
3. **oneway** — March+June only, 94k detect + confirm/cd (do not loosen min)

Log: `results/fade_followup.log`

**2025-only hunt (target sum ≥ 20k):** `run_fade_2025.py`  
Seed = user’s calm-year best (min 1000 / win 3 / TP 750 / SL 750 / trail 500 / arm 500 / hold 250 / cd 30 / lag 1 → 29 trades, PF 2.37, sum 6603).  
~80 jobs, `2025-01-01` → `2026-01-01` only (no Jan–Feb 2026 crisis). Longer windows, lower min, smaller TP, longer hold.  
Log: `results/fade_2025.log`

---

## Live bot (other PC)

`SPIKE_FADE_MT5_BOT_BRIEF.md` — clone patient-scalper MT5 wiring, not recovery. Defaults were the old screenshot; **update to 94k list if they go live**. `DRY_RUN=True`. `MT5_PATH` picks the terminal.

---

## Key code

- Logic: `backtest/spike_fade.py` (`confirm_pts`, `trail_arm_pts`)
- Jobs/UI: `backtest/spike_fade_jobs.py`, `webapp.py`, `web/spike_fade.js`
- Runners: `run_fade_oat.py` (`execute`), `run_fade_quiet.py`, `run_fade_janfeb.py`, `run_fade_spike_rate.py`

Do not optimize quiet months on Jan–Feb data. Do not treat 94k as a 19-month run-rate.
