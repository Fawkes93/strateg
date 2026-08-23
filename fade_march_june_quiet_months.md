# Why March and June 2026 were bad — and quiet-month search

## March (76 trades, 39+/37−, **−10,798 pts**) — the important one

March was **not a quiet month**. It was still violent, but the violence was **one-way**.

After the Jan 29 record (~$5,595) and the late-Jan crash, March was gold’s **worst month since 2013** (~**12%** down). WisdomTree and others blamed **liquidity deleveraging + a real-yield shock**, not a change in central-bank buying.

On top of that:

- **US–Iran / Hormuz:** gold was supposed to rally as a haven. It **sold instead** (~$5,400 → below $4,400 over weeks). Dollar up, margin calls, ETFs/futures dumped.
- **~19 Mar:** 10-year yields ~**4.29%**, jobless claims firm, **Fed cuts priced out toward 2027**. Gold lost **$4,600**.
- **~22 Mar:** another air-pocket, **$4,400** given up.

Your fade needs a **$11 rip in 3 seconds that then comes back**. In a forced unwind the $11 spike is the start of the next $50, not a wick. SL 1000 keeps getting run. That’s why March still **fired a lot** (76) but went **coin-flip (51%)** and red.

Jan–Feb = two-way chaos (paid). March = **trend dump** (fade dies).

## June (10 trades, 3+/7−, **−6,472 pts**)

Fewer tickets, still ugly. Different tape: **correction / hawkish repricing**, not a flash crash.

- Early June data: inflation still high (~**4.2% CPI** cited), desks started pricing **Fed hikes**, not cuts.
- Stronger dollar + higher real yields → gold’s opportunity cost jumped.
- Prints through **$4,100 / $4,000** (first time under $4k since Nov 2025). ~**26%** off the Jan high.
- Geopolitical premium faded (ceasefire talk in some recaps). Profit-taking, ETF outflows.

Only **10** 1100-pt/3s events — and **7 lost**. Thin sample, same disease as March: the spikes were **continuation in a grind lower**, not snap-backs.

## Quiet months (≤6 trades on this combo)

These barely printed at all. The 1100 / 3s gate is too tight when gold is not in crisis:

| Month | n | + | − | sum |
|---|---:|---:|---:|---:|
| 2025-01,02,03,06,08 | 0 | | | 0 |
| 2025-04 | 2 | 1 | 1 | −387 |
| 2025-05 | 1 | 1 | 0 | +512 |
| 2025-07 | 1 | 0 | 1 | −1,000 |
| 2025-09 | 2 | 2 | 0 | +2,845 |
| 2025-11 | 2 | 1 | 1 | −649 |
| 2025-12 | 6 | 6 | 0 | +2,835 |
| 2026-05 | 1 | 1 | 0 | +693 |

**Not included in the quiet search:** 2026-01/02 (crisis), 03 (bad violent), 04 (27 trades), 06 (10, bad), 07 (14), 2025-10 (11).

A calm-month setup needs **smaller / slower spikes** (lower min, longer window). Optimizing that **on Jan–Feb 2026** would just rediscover the crisis combo.

Overnight runner: `run_fade_quiet.py` — only those 12 months, ~90 combos (detect grid + exit OAT).
