# Strateg research sweep log

Living log of backtest/sweep attempts toward durable ≥58–60% clean (or strong win%/PF) at **meaningful size** (T≥500–1000 / real TP-SL — not T=100 mirages). Validate on **both 2025 and 2026** when something looks good. Overnight/asia_breakout is **out of scope** (live edge already in reaktor config).

## How to append
Add a new `### YYYY-MM-DD — <engine> <short label>` block under ## Runs (newest first). Include: window, key params, n trades, headline metrics, result path if known, **Conclusion** (keep / variant / dead end / OOS miss).

## Runs

### 2026-09-07 — session_clock flatten=14 (IN PROGRESS)
- **Window:** 2026-06 → 2026-09
- **Params:** min_range_usd=15, min_body=200, sl_floor=500, flatten_hour=14
- **n / metrics:** unknown finish as of 2026-09-07 ~07:14 Europe/Chisinau — still running
- **Result path:** unknown
- **Conclusion:** IN PROGRESS — status unknown if finished; follow up before starting another session-clock variant

### 2026-09-06 — session_clock looser OOS 2025-06→09
- **Window:** 2025-06 → 2025-09
- **Params:** min_range=10, min_body=100, sl_floor=500, flatten=12
- **n / metrics:** 35 trades, 42.9% wins (15W/11L/9BE), +2061 pts, PF 1.32
- **Conclusion:** OOS still miss vs 2026 59%

### 2026-09-06 — session_clock UI baseline OOS 2025-06→09
- **Window:** 2025-06 → 2025-09
- **Params:** min_range=15, min_body=200, sl_floor=500, flatten=12 (tight UI baseline)
- **n / metrics:** 10 trades (55 no_defining_bar), 40% wins, +1139 pts, PF 2.14
- **Conclusion:** not durable; calm 2025 starved

### 2026-09-06 — session_clock UI baseline 2026-06→09
- **Window:** 2026-06 → 2026-09
- **Params:** min_range=15, min_body=200, sl_floor=500, flatten=12 (same tight filters)
- **n / metrics:** 66 trades, 59.1% wins (39W/16L/11BE), +28.9k pts, PF 2.54
- **Conclusion:** first ≥58% at real size this loop; needs OOS (failed on 2025)

### 2026-09-06 — micro hold/tp_frac final
- **Window:** 2026-06 → 2026-09
- **Params:** session=all, hold=60, tp_frac=0.35, burst 100–300
- **n / metrics:** 51 trades, 29.4% wins, −1745 pts, PF 0.32
- **Conclusion:** dead end; micro family exhausted

### 2026-09-06 — micro asia_core UI seed
- **n / metrics:** 14 trades, 21.4% wins, −779 pts, PF 0.20
- **Conclusion:** dead end

### 2026-09-06 — micro quiet UI seed
- **n / metrics:** 69 trades, 33.3% wins, −2438 pts, PF 0.37
- **Conclusion:** dead end

### 2026-09-06 — micro UI-default burst 100–300
- **n / metrics:** 358 trades, 31.6% wins, −13.4k pts, PF 0.36
- **Conclusion:** dead end

### 2026-09-06 — micro wide-burst 200–800
- **Params:** TP/SL 500, hold=60, cd=30, burst 200–800
- **n / metrics:** 532 trades, 41.7% wins, −28.5k pts, PF 0.46
- **Conclusion:** dead end

### 2026-09-06 — cooloff default 2026-06→09
- **Window:** 2026-06 → 2026-09
- **Params:** min_run=5, min_range=500, reverse=0.30, TP/SL=1000
- **n / metrics:** 497 trades, 47.1% wins, −30.6k pts, PF 0.88
- **Conclusion:** dead end

### 2026-09-06 — Research Sweep batch 18 runs (range+spike lean)
- **Window:** 2026-06 / 07 / 08
- **Params:** lean T500–2000 grid (candle/spike)
- **n / metrics:** no durable ≥58%; best candle 56.3%@T500 n=87 (Aug only); spike July small-n mirage
- **Result path:** `batch_XAUUSD_20260906T182140Z_3e42c472.json`
- **Conclusion:** dead end for lean grid

### 2026-09-06 — spike_fade 2025 calm seed
- **Params:** min=1000, TP/SL=750
- **n / metrics:** 3 trades, 66.7% wins, −340 pts, PF 0.69
- **Conclusion:** dead/thin

### 2026-09-06 — spike_fade HOT 1400 2026-06→09
- **Window:** 2026-06 → 2026-09
- **Params:** HOT min≈1400
- **n / metrics:** 11 trades, 54.5% wins, −5323 pts, PF 0.4
- **Conclusion:** dead end

### 2026-09-06 — spike_fade 94k 2025-05→09
- **Window:** 2025-05 → 2025-09
- **n / metrics:** 2 trades, 50% wins, −602 pts, PF 0.46
- **Conclusion:** dead end

### 2026-09-06 — spike_fade 94k 2026-06→09
- **Window:** 2026-06 → 2026-09
- **n / metrics:** 39 trades, 51.3% wins, −3375 pts, PF 0.81
- **Conclusion:** OOS miss vs Jan–Feb crisis

### 2026-09-06 — IFVG Mon+London UTC 7–12
- **Params:** Monday + entry hours UTC 7–12
- **n / metrics:** looks good only at T=100; at T≥500 ~55%; T=1000 ~50–56%
- **Conclusion:** tiny-T mirage, not tradeable at meaningful size

### — overnight / asia_breakout
- **Conclusion:** out of scope (reaktor asia_breakout live edge already in config)

## Status / next

- **session_clock:** 2026 UI baseline hit ≥58% at real size (66 trades, 59.1%, PF 2.54) but **failed 2025 OOS** (tight starved; looser still 42.9% / PF 1.32).
- **In flight:** flatten=14 variant on 2026-06→09 (as of 2026-09-07 ~07:14 Europe/Chisinau) — confirm finish before new session-clock arms.
- **If session dies:** next richer Research Sweep on **spike_neo** / **impulse_retrace** (not another lean candle/spike T grid or micro/cooloff/spike_fade rehash).
- **Do not re-run blindly:** micro family, cooloff default, lean batch 18, spike_fade 94k/HOT/calm, IFVG at T=100, overnight.
