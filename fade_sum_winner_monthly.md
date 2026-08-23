# Spike fade — sum-winner monthly breakdown

Saved 2026-08-14 so this does not live only in chat.

**Combo:** highest **sum** from the overnight grids  
window **3.0s** · min spike **1100** · TP **3000** · SL **1000** · trail **500** · **arm 700** · confirm **0** · hold **320s** · **cooldown 0** · weekend skip **10 min** · lag **1s**  
Range **2025-01-01 → 2026-08-01** (19 months). Mid fill (no live spread). 100 pts ≈ $1 at 0.01 lot.

Machine JSON: `results/fade_cd0_arm700_hold320_by_month.json`

## Totals

| trades | **+** | − | flat | win% | avg pts | PF | **sum pts** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 549 | **346** | 200 | 3 | 63.0 | 172.0 | 1.47 | **94,453** |

## Per month

Empty months (0 trades): 2025-01, 2025-02, 2025-03, 2025-06, 2025-08.

| Month | trades | **+** | − | flat | win% | sum pts |
|---|---:|---:|---:|---:|---:|---:|
| 2025-04 | 2 | 1 | 1 | 0 | 50.0 | −387 |
| 2025-05 | 1 | 1 | 0 | 0 | 100.0 | +512 |
| 2025-07 | 1 | 0 | 1 | 0 | 0.0 | −1,000 |
| 2025-09 | 2 | 2 | 0 | 0 | 100.0 | +2,845 |
| 2025-10 | 11 | 8 | 3 | 0 | 72.7 | +3,740 |
| 2025-11 | 2 | 1 | 1 | 0 | 50.0 | −649 |
| 2025-12 | 6 | 6 | 0 | 0 | 100.0 | +2,835 |
| **2026-01** | **218** | **137** | 80 | 1 | 62.8 | **+60,205** |
| **2026-02** | **178** | **119** | 57 | 2 | 66.9 | **+33,600** |
| 2026-03 | 76 | 39 | 37 | 0 | 51.3 | **−10,798** |
| 2026-04 | 27 | 20 | 7 | 0 | 74.1 | +10,307 |
| 2026-05 | 1 | 1 | 0 | 0 | 100.0 | +693 |
| 2026-06 | 10 | 3 | 7 | 0 | 30.0 | **−6,472** |
| 2026-07 | 14 | 8 | 6 | 0 | 57.1 | −978 |

## How to read it

- **2025 is almost dead** — 25 trades, small net.
- **Jan + Feb 2026 are the whole 94k** (396 of 549 trades).
- March and June gave a chunk back.
- This is **not** a steady ~19 trades/month. Two violent months plus a quiet rest of the sample.

## Same family, for comparison (not re-broken by month)

| combo | trades | avg | PF | sum |
|---|---:|---:|---:|---:|
| 3.0 / cd 0 / hold 200 / arm 700 | 549 | 167 | 1.46 | 91,794 |
| **3.0 / cd 0 / hold 320 / arm 700** | **549** | **172** | **1.47** | **94,453** |
| 2.8 / cd 30 / hold 320 / arm 700 | 351 | 201 | 1.57 | 70,596 |
