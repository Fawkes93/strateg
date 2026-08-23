# Spike fade — hot / quiet regime switch

Saved so this does not live only in chat. Companion to `FADE_RESEARCH_STATUS.md` (why one static combo fails) and `SPIKE_FADE_MT5_BOT_BRIEF.md` (how to port a *single* preset to MT5). This file is the **switcher**: how the live bot should pick a preset from the tape.

XAU **1 pt = $0.01**. At **0.01 lot**, 100 pts ≈ $1. Backtest fills are **mid** (live spread will be worse; quiet-day spread was ~60 pts).

---

## Goal

An edge that is real on some tapes and dead on others. The bot should **switch behaviour from data**, not run 1400/3s forever (idle most of 2025) or loosen detect just to stay busy (PF ~1.05–1.16, spread food).

Do **not** blend numbers. Do not walk window 3 → 60 or min 1400 → 800 as the day “feels quieter.” That invents a third, untested strategy every hour.

**Two frozen presets + a thermometer that never trades.** Flip a label. The next signal uses that block.

A third state, **STAND ASIDE**, exists because March / June 2026 *looked* hot (lots of spikes) and still lost. A two-state switch will fade those dumps and die.

---

## The two trading blocks

Start by changing **detect only**. Same exits on both sides so a flip does not also change how you get paid.

| | **HOT** | **QUIET** |
|---|---|---|
| When | several crisis-detects recently, two-way | thermometer asleep |
| Window | **3 s** | **60 s** |
| Min spike | **1400** | **800** |
| TP / SL | 3000 / 1500 | **same** |
| Trail / arm | 600 / 750 | **same** |
| Max hold | 250 s | **same** |
| Cooldown | 120 s | **same** |
| Lag | 1 s | **same** |
| Confirm | off | off |
| Extreme age | off (or 3 s later) | off (or 3 s later) |

Evidence:

- **HOT** = the violent Jan–Feb 2026 PF~3 family (`fade_heatmap_min1400.md`). Jan PF 2.70 / Feb PF 3.66 / combined **3.11** on 71 trades. Seed on Jan–Oct 2025: only **8** trades (1 May + 7 Oct), PF 2.78.
- **QUIET** = `win60 / min800` from `results/fade_quiet2025_20260816T150146`. Jan–Sep **263** trades (6.7/week), quiet sum **+36,262**, October **−9,638**. That October loss is a feature: when the tape heats up this preset is already wrong.

Later experiment (not v1): quiet frequency block `win 30 / min 400 / TP 750 / SL 750 / trail 400 / arm 400 / hold 400 / cd 30` (every 2025 month green, +89k, 3,462 tickets — spread will chew it). Keep it on the shelf until the detect-only switcher is proven.

---

## Thermometer (always on)

Keep a **separate** detector that **never opens a trade**:

- window **3 s**, min **1100** (we already have hourly counts in `fade_spike_rate.md`; trade HOT at **1400** so the first crisis tick is a bit larger than the meter tick)
- after each hit, suppress **3 s** so one spike is not counted 20 times

Store the last ~20 events:

```
{t, dir, spike_pts, retraced_300_in_10s}
```

**Retrace / snap-back:** from that event’s extreme, did mid come back **300 pts** the other way within **10 s**? Jan–Feb 2026 usually yes. March usually no.

Also keep **net mid change over the last 15 minutes**.

This meter must stay the **crisis** detect (1100 or 1400 / 3 s). Do **not** use the quiet 60 s / 800 bag as the meter — that bag is “busy” on any $4 drift. The crisis detect was **silent** in May 2026 (1 event all month) and **screaming** on 2026-01-29 15:00 UTC (121 events that hour).

| Tape | 1100-pt / 3 s detects |
|---|---|
| 2026-01 | 283 in 32 hours; median 2 / active hour; max 121 |
| 2026-02 | 213 in 57 hours; 22 hours with ≥3 |
| 2026-03 | 102 in 29 hours; median 1 — violent but one-way |
| 2026-05 | **1** all month |
| Calm 2025 hours | almost all **0** |

---

## States

```
QUIET  ──busy meter──►  HOT  ──no snap-back──►  STAND ASIDE
  ▲                      │                           │
  │                      │ 90 min silence            │ 90 min silence
  └──────────────────────┴───────────────────────────┘
                         │
                         └── snap-back recovers ──► HOT
```

Start **QUIET**.

### QUIET → HOT (any one)

- ≥ **2** thermometer hits in the last **30 minutes**, or
- ≥ **3** in the last **60 minutes**

The spike that trips the count may be traded **immediately on the HOT preset** (it already is a 1400 / 3 s). Do not also fire the 60 / 800 fade on the same spike.

### HOT → QUIET (only when the tape is dead)

- **0** thermometer hits in the last **90 minutes**

That gap is the hysteresis. Without it the bot flips every London lunch.

### HOT → STAND ASIDE (March / June trap)

Look at the last **5–8** thermometer hits:

- ≥ **70%** the same direction, **and**
- snap-back rate **< 40%**, **or** 15-minute drift already ≥ ~**1500 pts** the same way

Then: **no new fades**. Optional later: raise min to 1500 instead of flat off (that combo went green on March+June in the oneway hunt, +3,859 / PF 1.48 — not split by month). Do not yank a trade that is working; flatten only if you are already in a loser and you really want out.

### STAND ASIDE → HOT

Last 5 hits mixed **and** snap-back ≥ **50%**.

### STAND ASIDE → QUIET

Same 90-minute silence rule as HOT → QUIET.

---

## Live loop (sketch)

```
on each tick:
    update 3s bag + 60s bag
    if 1100/3s (or 1400) fires:
        record event + start 10s snap-back watch
        maybe promote QUIET → HOT
    update snap-back flags on recent events
    maybe HOT → STAND ASIDE / QUIET

    if in a position:
        manage with the preset stamped at entry
    elif STAND ASIDE or weekend blackout or spread too wide:
        do nothing
    elif HOT:
        detect 3 / 1400 → fade with HOT exits
    elif QUIET:
        detect 60 / 800 → fade with QUIET exits
```

Two deques, one enum (`quiet | hot | aside`), one `entry_preset` on the ticket.

Live extras on every new entry (not only on flips):

- skip if spread > ~**80–100 pts**
- weekend skip unchanged (Sun 22:00 UTC + 10 min)
- one trade at a time; cooldown of **that ticket’s** preset

---

## What must not happen

- **Don’t change window / min / SL on an open trade.** Finish with the preset you entered on. Next ticket uses the new block.
- **Don’t run both detects as two strategies.** One position. One preset. The 3 s bag is only a meter while QUIET.
- **Don’t interpolate.** `min = 1400 if hot else 800`. That’s it.
- **Don’t use clock time** (“after 16:00 use quiet”). April 2025 printed 121 of the 263 quiet `win60/min800` tickets. The meter already knows.
- **Don’t use the quiet detect as the meter.**
- **Don’t treat “many spikes” as HOT without snap-back.** That is March.

---

## Prove it before the bot

Replay the FSM on **2025-01-01 → 2026-08-01** as one backtest job. It is not done until all of these are true:

| Check | Pass if |
|---|---|
| Quiet 2025 / May 2026 | stays QUIET; does not flip HOT on a $4 drift |
| 2026-01-28 → 01-30 and February | goes HOT and stays there through the two-way tape |
| 2026-03 and 2026-06 | goes STAND ASIDE (or at least stops taking HOT fades), does not sit in HOT all month |
| Flip count | not dozens per day; hysteresis is working |
| PnL vs static | beats **always HOT** *and* **always QUIET** on the same range (mid fill first, then a 60–80 pt spread haircut) |

Log every flip: `{t, from, to, reason, n_30m, n_60m, snap_rate, drift_15m}`.

If the replay is not better than both static bots, the **thresholds** are wrong — not the idea. Tune the 2/30m, 3/60m, 90m silence, and 40% snap-back numbers on that replay. Do not add a third trading preset until this FSM clears.

---

## Suggested files when we implement

| Where | What |
|---|---|
| `backtest/spike_fade.py` | optional `regime` / two `FadeParams` + thermometer (or a thin wrapper) |
| `run_fade_regime.py` | 19-month FSM replay + flip log + PnL by state |
| Live MT5 bot | same enum + two param blocks in config; thermometer deque next to the trade deque |

Do not put this into `SPIKE_FADE_MT5_BOT_BRIEF.md` until the replay says the thresholds work.

---

## Pointers

| File | Why |
|---|---|
| `FADE_RESEARCH_STATUS.md` | why 94k is Jan–Feb, not a year |
| `fade_spike_rate.md` | 1100/3s detects per hour (the meter) |
| `fade_heatmap_min1400.md` | HOT preset monthly (Jan 2.70 / Feb 3.66 / Mar 0.50) |
| `fade_march_june_quiet_months.md` | why March is one-way, not quiet |
| `results/fade_quiet2025_20260816T150146/` | QUIET `win60/min800` and the 1/week hunt |
| `results/fade_age_20260816T175322/` | `max_extreme_age_sec` — optional later, not required for v1 |
| `SPIKE_FADE_MT5_BOT_BRIEF.md` | single-preset live port (today) |
