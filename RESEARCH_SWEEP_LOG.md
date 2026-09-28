# Strateg research sweep log

Living log of backtest/sweep attempts toward durable ≥58–60% clean (or strong win%/PF) at **meaningful size** (T≥500–1000 / real TP-SL — not T=100 mirages). Validate on **both 2025 and 2026** when something looks good. Overnight/asia_breakout is **out of scope** (live edge already in reaktor config).

## How to append
Add a new `### YYYY-MM-DD — <engine> <short label>` block under ## Runs (newest first). Include: window, key params, n trades, headline metrics, result path if known, **Conclusion** (keep / variant / dead end / OOS miss).

## Runs

## EURUSD Asia overnight

### 2026-09-26 ~15:35 Europe/Bucharest EURUSD 5m SHORT_DENSIFY (36 cells) - REJECT/PARK (short PF clean but pts-thin; no tick)

- Grid: results/overnight_5m_grid_EURUSD_20260926T123454Z.json (+ .csv) | tag EURUSD_ASIA_SHORT_DENSIFY | helper results/_asia_stage/eurusd_asia_short_densify_5m_grid.py | local ProcessPool workers=2 | candles_5m | window 2025-01->2026-09.
- Fixed seed: SL80/TP120 | min Asia/break 40/40 | asia0-6 | ema30 | resume_closes=8 | rcap120 | flat21 | trail off | timeout market | wait_from_break | pullback required | near_box outside N6 D100. Axes: side_short x wait {8,10,12,13,15} x TP {100,120,140,160,200,240,280}; one BOTH seed comparison.
- Top by pts: BOTH seed wait10/TP120 +2240.0 PF1.8 n77 (reference only); best short-only short_w10_tp280 +1760.0 PF2.1 n32; short_w13_tp120 +1600.0 PF2.538 n35; short_w15_tp160 +1600.0 PF2.25 n34; short_w12_tp280 +1600.0 PF1.909 n34.
- Top by PF: short_w13_tp100 PF2.727 / +1520 n35; short_w15_tp100 PF2.614 / +1420 n34; short_w13_tp120 PF2.538 / +1600 n35; short_w15_tp120 PF2.423 / +1480 n34; short_w10_tp100 PF2.386 / +1220 n32.
- Notes: Short-only PF>=2 cells exist, including prior hints (w13xTP120, TP280), but all remain below the soft pts bar. 0 cells clear PF>=2.0 and pts>=1920 (prefer >=2240); best short pts +1760.
- Tick-worthy? NO. No tick-confirm and no promotion. New champ: none; both-side seed remains +2240/PF1.8/n77 reference.
- Conclusion: PARK/REJECT SHORT_DENSIFY. No blockers after rerun; API was idle and untouched, XAU jobs were not touched, no reaktor edit, no git push. Next short thesis would need a pts lift, not another PF-only thin cell.


### 2026-09-25 ~19:39 Europe/Bucharest EURUSD 5m SIDE_STRUCT (32 cells) — **REJECT/PARK** (short PF>=2 pts-thin; entry-path dead; no tick)

- **Grid:** results/overnight_5m_grid_EURUSD_20260925T161018Z.json (+ .csv) · tag EURUSD_ASIA_SIDE_STRUCT · helper results/_asia_stage/eurusd_asia_side_struct_5m_grid.py · seed NEARBOX **rc8** champ wait10 · SL80/TP120 · ma40/mb40 · asia0-6 · ema30 · wait10 · resume_closes=8 · rcap120 · flat21 · trail off · timeout market · wfb · pb required · nb outside N6 D100 · side both · candles_5m · workers=2 · window 2025-01→2026-09 · trail off throughout.
- **Axes:** SEED both · side_long/short · short×TP{100,140,160,180,200,240,280,320} · short×wait{8,12,13,15}@tp120 + wait{8,12,13}@tp160 · short×SL refine · long×TP light · entry-path reopen (wick_on · higher_close_off · wfb_false · pb_optional · wick_short_tp160).
- **SEED_both_rc8:** n77 · win54.5% · **+2240.0** · **PF 1.8** — exact match prior champ (no regression).
- **Top5 by pts:** SEED / higher_close_off **+2240** PF**1.8** n77 (inert =SEED); **short_tp280** **+1760** PF**2.1** n32; short_tp320 **+1649** PF**1.982** n32; **short_w13_tp120** **+1600** PF**2.538** n35.
- **Top5 by PF:** **short_w13_tp120** PF **2.538** / **+1600** n35; short_w15_tp120 **2.423**/+1480 n34; short_tp100 **2.386**/+1220 n32; side_short **2.192**/+1240 n32; short_w12_tp120 **2.143**/+1280 n34.
- **Notes:** Side_short is the real edge (PF≥~2 across many cells) but **pts-thin** vs both-side champ (+2240). Closest PF≥2 pts: short_tp280 +1760 (still **≪1920**). Best PF short_w13_tp120 +1600. Long side weak (best +1000 PF1.57; long_tp200 negative). Entry-path: higher_close_off =SEED; wick_on / wfb_false / pb_optional / wick_short all dilute or collapse. **0** cells with PF≥~2.0 AND pts≥~1920 (prefer ≥2240).
- **vs champ +2240/1.8:** no pts+PF co-lift; do **not** promote (short cells cut trade count ~half and lose absolute pts).
- **Tick-worthy?** **NO** — soft tick bar unmet (need PF≥~2.0 with pts≥~1920). Prefer not to burn shared overnight on pts-thin shorts.
- **Conclusion:** **REJECT** for tick-confirm / **PARK** open batch. SIDE_STRUCT + entry-path reopen both exhausted under tick bar. Champ unchanged: wait10 · SL80/TP120 · ma40/mb40 · asia0-6 · ema30 · wait10 · **rc8** · rcap120 · flat21 · trail off · timeout market · wfb · pb required · nb outside N6 D100 · side both · **+2240 / PF1.8 / n77** (not tick-confirmed).
- **Next:** only with new thesis (e.g. short_w13 densify seeking pts≥1920 via SL/TP/asia/resume on short-only, or Igor steer) or accept PARK FX overnight. No reaktor / no push. Shared overnight idle (last XAU R_tick done); left alone this fire.


### 2026-09-25 ~19:08 Europe/Bucharest EURUSD 5m RESUME_DEEPEN (21 cells) — **PARK** (resume plateau under PF2; no tick)

- **Grid:** results/overnight_5m_grid_EURUSD_20260925T160726Z.json (+ .csv) · tag EURUSD_ASIA_RESUME_DEEPEN · helper results/_asia_stage/eurusd_asia_resume_deepen_5m_grid.py · seed NEARBOX **rc8** champ wait10 · SL80/TP120 · ma40/mb40 · asia0-6 · ema30 · wait10 · **resume_closes=8** · rcap120 · flat21 · trail off · timeout market · wfb · pb required · nb outside N6 D100 · side both · candles_5m · workers=2 · window 2025-01→2026-09 · trail off throughout.
- **Axes (resume family FIXED champ):** SEED rc8/rcap120 · resume_closes ∈ {6,7,9,10,12} @ rcap120 · resume_max_break_pts ∈ {80,100,150,180,200} @ rc8 · combos rc7×{100,150} · rc9×{100,150} · rc10×150 · skip_late sls3 / sls7 / sls5_asia180 · asia_end5 · flat22 (~21 thoughtful).
- **SEED_rc8_rcap120:** n77 · win54.5% · **+2240.0** · **PF 1.8** — exact match NEARBOX rc8 champ (no regression).
- **Top5 by pts:** SEED / flat22 / rc9 / rc10 / rc12 / rc9_rcap100 / rc9_rcap150 / rc10_rcap150 / rcap80/100/150/180/200 — all **+2240** PF**1.8** n77 (13-way inert cluster =SEED). Next: rc6/rc7 (+combos) **+2160** PF**1.75** n78 (prior-champ level).
- **Top5 by PF:** **sls3** PF **1.828** / **+2120** n71 (mild PF lift, pts −120 vs SEED); then SEED-tied cluster **1.8**/+2240. Best non-filter PF still 1.8.
- **Notes:** Resume family **fully plateaued**: rc≥8 inert (=SEED); all rcap @ rc8 inert; rc×rcap combos with rc≥9 inert; rc6/7 regress to prior +2160/1.75. skip_late: sls3 slight PF↑ but pts↓; sls7 dilutes (+2080/1.605 n89); sls5_asia180 same pts PF↓1.737 n82. asia_end5 collapses (+320/1.105). flat22 inert. **0** cells PF≥~2.0; **0** with PF≥~2.0 AND pts≥~1920 (prefer ≥2240).
- **Tick-worthy?** **NO** — do not kick tick-confirm.
- **Conclusion:** **PARK** resume/near-box/SLTP densify on this wait10·sl80/tp120 shape. 5m screen stuck at PF≈1.8 / +2240; only rc6→8 ever lifted, further resume deepen is dead. Champ remains wait10 · SL80/TP120 · ma40/mb40 · asia0-6 · ema30 · wait10 · **rc8** · rcap120 · flat21 · trail off · timeout market · wfb · pb required · nb outside N6 D100 · side both · **+2240 / PF1.8 / n77**.
- **Next family (suggested):** (1) **side / session structure** — side_short alone had PF2.0/+1280 n32 (pts-thin); hunt short×TP or short×wait with pts≥1920; (2) **entry-path** reopen with wick/close_inside / higher_close off / wait_from_break false on rc8 seed; (3) **asia window / flatten** deeper only if paired with new edge (asia_end5 alone died); (4) else accept PARK FX overnight until new thesis. No reaktor / no push. Shared overnight / XAU left alone.

### 2026-09-25 ~19:04 Europe/Bucharest EURUSD 5m NEARBOX_REFINE (25 cells) — **REJECT** (plateau; mild rc8 lift, no tick bar)

- **Grid:** results/overnight_5m_grid_EURUSD_20260925T160417Z.json (+ .csv) · tag EURUSD_ASIA_NEARBOX_REFINE · helper results/_asia_stage/eurusd_asia_nearbox_refine_5m_grid.py · seed WAIT10_RISK champ **sl80/tp120** wait10 shape FIXED (ma40/mb40 asia0-6 ema30 wait10 rc6 flat21 trail off timeout market wait_from_break pullback required near_box outside N6 D100 side both) · candles_5m · workers=2 · window 2025-01→2026-09 · trail off throughout.
- **Axes (near_box family + light resume):** SEED · N∈{0,4,5,7,8,10} @ D100 outside (0=off) · D∈{50,80,120,150,200} @ N6 outside · trend off/breakout @ N6 D100 · combos N5/7×D80/120 · N8 D150 · N4 D80 · N5/7 D100 breakout · resume rc4/rc8 · rcap80 (~25 thoughtful, not full N×D×trend cartesian).
- **SEED_N6_D100_out:** n78 · win53.8% · **+2160.0** · **PF 1.75** — exact match prior TP120 densify champ (no regression).
- **Top5 by pts:** **rc8 +2240** PF**1.8** n77 (dPts **+80** / dPF **+0.05** vs SEED); SEED / N7_D100_out / N8_D100_out / N6_D80_out / N7_D80_out / rcap80 all **+2160** PF**1.75** n78 (near-box N6–8 · D80–100 inert =SEED; rcap80 inert).
- **Top5 by PF:** same order — rc8 **1.8**/+2240; then SEED-tied cluster **1.75**/+2160. Best non-rc PF still 1.75.
- **Notes:** Near-box **plateau**: N7/N8 @ D100 and D80 @ N6 =SEED; N4/N5 mildly dilute (+2040–2080); N0_off / D50 cut to +1960; wider D120/150/200 dilute hard (n↑ PF↓, worst N8_D150 +1200 PF1.278). trend_off / breakout slightly worse than outside. Resume: **rc8** sole lift; rc4 hurts (+1520/1.432); rcap80 =SEED. **0** cells PF≥~2.0; **0** with PF≥~2.0 AND pts≥~1920 (prefer ≥2160).
- **vs prior champ sl80_tp120 +2160/1.75:** only rc8 improves (+80 pts / +0.05 PF) — incremental, still **≪ soft floor ~2.0**.
- **Tick-worthy?** **NO** — best PF **1.8 < ~2.0** despite pts 2240 ≥2160. Prefer non-trail (all non-trail here).
- **Conclusion:** **REJECT** for tick-confirm. Near-box N/D/trend exhausted around champ — flat plateau with one light resume_closes=8 nudge. Not KEEP / not tick.
- **Next:** if continue EURUSD Asia 5m: deepen **resume** around rc8 (rc7/9 · rcap100/150 · rc8×N6 D100) or orthogonal **asia_end 5/7 · flatten 18/22 · skip_late_short** light; else park until new thesis (side_short already PF≥2 but pts-thin). No reaktor / no push. XAU overnight / EURUSD download_ticks left alone (local ProcessPool only; no XAU grid running at start).

### 2026-09-25 ~19:02 Europe/Bucharest EURUSD 5m TP120_DENSIFY (26 cells) — **REJECT** (SEED holds; short PF>=2 pts-thin)

- **Grid:** results/overnight_5m_grid_EURUSD_20260925T160158Z.json (+ .csv) · tag EURUSD_ASIA_TP120_DENSIFY · helper results/_asia_stage/eurusd_asia_tp120_densify_5m_grid.py · seed WAIT10_RISK champ **sl80/tp120** wait10 shape (ma40/mb40 asia0-6 ema30 wait10 rc6 flat21 trail off timeout market wait_from_break pullback required near_box outside N6 D100 side both) · candles_5m · workers=2 · window 2025-01→2026-09 · trail off throughout.
- **Axes:** (A) densify SL∈{70,80,90,100}×TP∈{100..160} thoughtful ~13 incl. SEED · (B) side_short × TP{120,140,160,180,200} on SL80 + SL70/90 × TP160/180 (~8) · (C) side_long on champ + prior tp160 · (D) ma30/50 · mb30 nudge on champ.
- **SEED_sl80_tp120:** n78 · win53.8% · **+2160.0** · **PF 1.75** — exact match prior WAIT10_RISK champ (no regression).
- **Top5 by pts:** SEED / ma30_mb40 / ma50_mb40 all **+2160** PF**1.75** n78 (ma30/50 inert =SEED); sl100_tp120 +2100 PF1.636; sl90_tp120 +2010 PF1.638. Nearby TP densify: sl80_tp130 +1950/1.625; sl80_tp110 +1930/1.689; sl80_tp100 +1860/1.705; sl80_tp160 +1920/1.545 — **none beat SEED pts**.
- **Top5 by PF:** short_sl80_tp120 **2.192**/+1240 n32; short_sl80_tp160 **2.0**/+1280 n32; short_sl80_tp140 1.983/+1180; short_sl80_tp200 1.944/+1360 (best short pts, still ≪1920); short_sl90_tp160 1.778/+1120.
- **Notes:** Side short keeps PF≈2 mirage but **all short cells pts ≤1360 ≪ champ +2160 / soft ≥1920** (n32 thin). long_sl80_tp120 +920 PF1.5; long_sl80_tp160 +640 PF1.286 — long dilutes. ma40_mb30 dilutes (n104 +680 PF1.144). Wider SL at TP120 (90/100) close on pts but lower PF. **0** non-trail cells with PF≥~2.0 **and** pts≥~1920.
- **vs prior champ sl80_tp120 +2160/1.75:** densify flat — SEED remains pts champ; no lift.
- **Tick-worthy?** **NO** — shorts with PF≥2 fail pts bar (max +1360); SEED PF1.75 < ~2.0. Prefer non-trail (none candidate).
- **Conclusion:** **REJECT** for tick-confirm. TP120 neighborhood exhausted on wait10 book; short-bias cannot clear pts≥~1920 at PF≥2. Not KEEP / not tick.
- **Next:** park densify; optional orthogonal (near_box D/N · asia_end · resume · flatten) or abandon EURUSD Asia 5m until new thesis. No reaktor / no push. XAU overnight / EURUSD download_ticks left alone (local ProcessPool only).

### 2026-09-25 ~18:59 Europe/Bucharest EURUSD 5m WAIT10_RISK (24 cells) — **REJECT** (mild SLTP lift, no tick bar)

- **Grid:** results/overnight_5m_grid_EURUSD_20260925T155748Z.json (+ .csv) · tag EURUSD_ASIA_WAIT10_RISK · helper results/_asia_stage/eurusd_asia_wait10_risk_5m_grid.py · seed ENTRY_STRUCT/WAIT_EMA_PB champ **wait10** shape (sl80/tp160 ma40/mb40 asia0-6 ema30 wait10 rc6 flat21 trail off timeout market wait_from_break pullback required near_box outside N6 D100) · candles_5m · workers=2 · window 2025-01→2026-09 · structure FIXED wait10.
- **Axes:** thoughtful denser SL/TP (~15 incl. SEED; ratios ~1:1–1:2.5, not full cartesian) · side_filter long/short on champ · break_on_wick true · one_trade_per_day false · light trail/be 4 cells (arm80/100/120 · trail40/50 · be80+trail) — **5m trail overpromises; do not tick-confirm trail champs**.
- **SEED_sl80_tp160:** n78 · win43.6% · **+1920.0** · **PF 1.545** — exact match prior champ (no regression).
- **Top5 by pts:** sl80_tp120 **+2160** PF**1.75** n78 (dPts **+240** / dPF **+0.205** vs SEED); SEED / otp_false both +1920 PF1.545; sl120_tp120 +1920 PF1.516 n78 win60.3%; sl100_tp160 +1820 PF1.444.
- **Top5 by PF:** side_short **2.0**/+1280 n32 win50%; sl80_tp120 **1.75**/+2160; SEED / otp_false / sl60_tp120 all 1.545.
- **Notes:** Tighter TP on champ SL (sl80_tp120 1:1.5) is the only pts+PF lift; wider TP (200/240) and most other SLTP dilute. otp_false inert (=SEED). wick_true dilutes (n120 +720 PF1.117). side_long weak (+640 PF1.286); side_short hits **PF 2.0** but pts only **+1280 ≪ +1920** (n32 — sample thin). Trail cells: best trail_arm120_t50 +1483 PF1.515 / trail_arm100_t40 +1429 PF1.541 — neither beats SEED pts; win% inflated (53–61%) typical of 5m trail optimism. Only 1 cell negative (sl120_tp240 −184.5 PF0.97). **0** non-trail cells with PF≥2.0 **and** pts≥champ.
- **vs prior champ wait10 +1920/1.545:** best non-trail = sl80_tp120 **+2160/1.75** — incremental, still **≪ soft floor ~2.0 / ~2.5**.
- **Tick-worthy?** **NO** — side_short PF=2.0 fails pts bar (1280 < 1920); sl80_tp120 PF1.75 < ~2.0. No trail tick either (policy + overpromise).
- **Conclusion:** **REJECT** for tick-confirm. Risk/filter refine on fixed wait10 yields one mild tighter-TP champ (sl80/tp120) and a thin short-only PF=2 mirage; not KEEP / not tick.
- **Next:** optional deepen around sl80_tp120 (TP 110–140 · SL 70–90 · maybe short-bias combo) or orthogonal filters (near_box D/N · asia_end · resume); else park EURUSD Asia 5m until better thesis. No reaktor / no push. XAU overnight / tick download left alone (EURUSD download_ticks + webapp still running; no XAU grid touched).

### 2026-09-25 ~18:55 Europe/Bucharest EURUSD 5m WAIT_EMA_PB deepen (32 cells) — **REJECT** (no lift vs wait10)
- **Grid:** results/overnight_5m_grid_EURUSD_20260925T155256Z.json (+ .csv) · tag EURUSD_ASIA_WAIT_EMA_PB · helper results/_asia_stage/eurusd_asia_wait_ema_pb_5m_grid.py · seed ENTRY_STRUCT champ **wait10** shape (sl80/tp160 ma40/mb40 asia0-6 ema30 wait10 rc6 flat21 trail off timeout market wait_from_break pullback required near_box outside N6 D100) · candles_5m · workers=2 · window 2025-01→2026-09 · side both · otp true.
- **Axes (dense deepen):** wait {8,9,10,11,12,13,14} · ema {18,21,24,28,30,34} · pb required vs preferred · wait_from_break T/F on wait8/10 (+ wait10_ema21) · wait×ema (8/10/11/12 × 18/21/24) · wait×pb_pref · wait10_ema21 × both pb · flat18 on wait10 / wait10_ema21.
- **SEED_wait10:** n78 · win43.6% · **+1920.0** · **PF 1.545** — exact match to prior ENTRY_STRUCT champ (no regression).
- **Top5 by pts:** SEED_wait10 **+1920** PF**1.545** n78; wait10_flat18 +1920 PF1.545 n78 (=SEED; flat18 inert); wait8_pb_pref +1680 PF1.189 n177; ema34 +1600 PF1.476 n73; ema21 / wait10_ema21 / wait10_ema21_pb_req / wait10_ema21_flat18 all +1600 PF1.294 n112.
- **Top5 by PF:** SEED_wait10 **1.545**/+1920; wait10_flat18 1.545/+1920; ema34 1.476/+1600; wait8 1.442/+1520; wait10_wfbF / wait8_wfbF 1.407/+880 n46.
- **Notes:** **30/32** cells sum_pts>0 and PF≥1.0 (only pb_preferred and wait10_pb_pref −80 PF0.991). **0** cells PF≥2.0; only **2** at PF≥1.5 (both =SEED shape). Dense wait 9/11/12/13/14 and ema18/24/28 never beat wait10. Preferred pullback on wait10 **hurts** (dilutes to ~0 PF / negative); wait8_pb_pref still positive but PF≪SEED. wait_from_break false keeps PF~1.4 but cuts pts (~880). Cross wait×ema (esp. wait10_ema21) matches prior ENTRY_STRUCT combo — no new edge. flat18 no-op on this book.
- **vs prior champ wait10 +1920/1.545:** **no cell improved** pts or PF. Deepen is flat / slightly worse off-seed.
- **Conclusion:** **REJECT** for tick-confirm — best still **PF 1.545 ≪ ~2.0 / soft ~2.5**. WAIT×EMA×PB densify exhausted on this SL80/TP160 ma40/mb40 seed; structure plateau.
- **Next:** try orthogonal axes (side split long/short · wick_on · asia_end5/7 light · near_box D/N · resume/rcap · or abandon XAU-KEEP candle-count port for EURUSD). Tick only if PF≥~2.0 with strong pts. No reaktor / no push. Shared overnight / tick download left alone.


### 2026-09-25 ~18:52 Europe/Bucharest EURUSD 5m ENTRY_STRUCT (27 cells) — **REJECT** (progress vs prior)
- **Grid:** results/overnight_5m_grid_EURUSD_20260925T154946Z.json (+ .csv) · tag EURUSD_ASIA_ENTRY_STRUCT · helper results/_asia_stage/eurusd_asia_entry_struct_5m_grid.py · seed less-bad FX_KNOBS **sl80/tp160 + ma40/mb40** · candles_5m · workers=2 · window 2025-01→2026-09 · timeout market · trail off · near_box outside N=6 D=100 · side both.
- **Risk/distance fixed:** SL80/TP160 · min_asia40 · mb40 · trail off · timeout market. Alt cells: sl100_tp160 · nb_D80.
- **Axes (one family + few combos):** pullback required vs preferred · wait_from_break T/F · wait {8,10,13,16} · ema {21,28,30,34} · asia_end {5,6,7} (+ start1) · flatten {18,21,22} · mbc {8,12,15} · resume rc4/8 + rcap80 · otp T/F · near_box outside/off/breakout · combos pb_pref_wait8 / ema21_wait10 / asia_end5_flat18.
- **SEED cell:** n98 · win38.8% · **+1280.0** · **PF 1.267** — already flips prior FX_KNOBS best (sl80_tp160 −320 PF0.959 on baseline structure) via ma40/mb40 book.
- **Top5 by pts:** wait10 **+1920.0** PF**1.545** n78 (dPts **+2240** / dPF **+0.586** vs prior best −320/0.959); ema21 +1680 PF1.273 n126; pb_pref_wait8 +1680 PF1.189 n177; ema21_wait10 +1600 PF1.294 n112; wait8 +1520 PF1.442 n74.
- **Top5 by PF:** wait10 **1.545**/+1920; wait_from_break_false 1.481/+1040 n47; wait8 1.442/+1520; ema21_wait10 1.294/+1600; flat18 1.293/+1380.9.
- **Notes:** **26/27** cells sum_pts>0 and PF≥1.0 (only asia_end7 −480 PF0.921 loses). Shorter wait (8–10) is the cleanest lift; ema21 helps pts; preferred pullback raises n but dilutes PF; asia_end5/7 and mbc8 hurt or dilute; flat18 mild pts; nb_breakout mild; otp/rc/nb_off/flat22 mostly =SEED. Best PF still **1.545** — well below soft floor ~2 / ~2.5.
- **Conclusion:** **REJECT** for tick-confirm — no cell near PF≥~2.0 despite first positive EURUSD Asia 5m edge. Structure (esp. wait10 / wait8 / ema21) is the right axis vs more SLTP-only.
- **Next:** deepen wait×ema×pullback on this seed (wait9–11 · ema18–24 · preferred+wait10 · maybe wait10+ema21+flat18 combo) and/or side split / wick_on light screen. Tick only if PF≥~2.0 with strong pts. No reaktor / no push. Shared overnight left alone (XAU R_tick still running).


### 2026-09-25 ~18:47 Europe/Bucharest EURUSD 5m FX_KNOBS_DIST_SLTP (25 cells) — **REJECT**
- **Grid:** results/overnight_5m_grid_EURUSD_20260925T154640Z.json (+ .csv) · tag EURUSD_ASIA_FX_KNOBS_DIST_SLTP · helper results/_asia_stage/eurusd_asia_fx_knobs_5m_grid.py · seed BASELINE run 20260925T152932Z_3da9c675 · candles_5m · workers=2 · window 2025-01→2026-09.
- **Structure fixed:** asia0-6 · ema30 · wait13 · rc6 · flat21 · trail off · timeout market · wait_from_break · pullback required · near_box outside N=6 · side both · sls5/220 · cap120.
- **Axes:** distance one-knob (min_asia in {20,40,50,80}; mb in {10,30,40}; near_box in {50,80,150,200}) + 4 thoughtful combos + SL/TP on seed (SL in {80,100,120,150} x selected TP ~1:1.5-1:2.5).
- **Baseline cell:** n145 · win24.8% · **-2442.5** · **PF 0.775** (matches overnight BASELINE).
- **Top5 by pts:** sl80_tp160 -320.0 PF0.959 (dPts **+2122.5** / dPF **+0.184**); sl100_tp160 -331.2 PF0.963; mb40 -491.2 PF0.930 n98; ma80_mb40_nb200 -559.2 PF0.932; sl100_tp200 -1171.2 PF0.883.
- **Top5 by PF:** sl100_tp160 0.963; sl80_tp160 0.959; ma80_mb40_nb200 0.932; mb40 0.930; sl100_tp200 0.883.
- **Notes:** min_asia 20-50 inert (=baseline); ma80 slightly worse. Higher mb helps most among distance (mb40). near_box alone mostly worse. Tighter books (TP160) cut losses most but still lose. **Zero** cells with sum_pts>0 or PF>=1.0 (let alone >=1.5 / >=2.0).
- **Conclusion:** **REJECT** — no positive edge; not tick-worthy. Best still PF<1 / negative pts. Do **not** kick tick-confirm.
- **Next:** rethink structure for EURUSD (entry path / pullback / asia window / side split / wick) rather than more FX-distance/SLTP on this losing seed; or abandon XAU-KEEP candle-count port. No reaktor / no push. Shared overnight left alone (was busy with XAU R_tick).

### 2026-09-25 ~18:29 Europe/Bucharest EURUSD 5m BASELINE (asia0-6 · ema30 · wait13 · rc6 · cap120 · flat21 · min_asia30 · mb±20 · SL100/TP240 · sls5/220 · near_box outside N=6 D=100 · trail off · timeout market · wait_from_break · pullback required)
- **Window:** 2025-01-01 → 2026-09-01 · `data_source=candles_5m` · workers=2 · point_size=1e-5 (10 pts = 1 pip)
- **Result:** n=145 · win=24.8% · sum_pts=-2442.5 · PF=0.78 · exits={'tp': 35, 'sl': 108, 'flatten': 2}
- **Result path:** `C:\Users\user\strateg\results\overnight_EURUSD_2025-01-01_2026-09-01_20260925T152932Z_3da9c675.json`
- **Conclusion:** BASELINE — first EURUSD 5m overnight screen on XAU-KEEP candle-count knobs with FX-scaled pts (SL100/TP240 ≈ XAU SL1000/TP2400 /10).
- **Next sweep:** vary min_asia_range_pts / min_break / near_box_pts / SL-TP around 80–120 / 200–300; keep trail off; confirm on ticks if 5m PF looks real.

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

### 2026-09-09 Asia best-seed baseline Feb 2023
- **Window:** 2023-02-01 → 2023-03-01
- **Params:** reaktor live seed SL2000/TP2000 flatten22 trail asia 3000/cap1800/trail400; Asia 1–7 Bucharest; min_asia_range 300; break ±200; max_break 15; break_on_wick false; pullback preferred; ema 23; max_wait 11; timeout market; use_higher_close false; skip_late_short 7/3000; one_trade_per_day; side both; workers=2
- **n / metrics:** 11 trades, 45.5% wins, −5180 pts, PF 0.34; exits sl3/flatten5/trail3; avg_win +537.5 avg_loss −1311.2
- **Feb month:** 2023-02 same as overall (single month)
- **Result:** 
esults/overnight_XAUUSD_2023-02-01_2023-03-01_20260908T233834Z_d888270a.json
- **Conclusion:** Feb 2023 is a clear loss month on best seed — baseline for loss-cut variants. Next: Feb 2024 baseline same seed.

### 2026-09-09 Asia best-seed baseline Feb 2024
- **Window:** 2024-02-01 → 2024-03-01
- **Params:** reaktor live seed SL2000/TP2000 flatten22 trail asia 3000/cap1800/trail400; Asia 1–7 Bucharest; min_asia_range 300; break ±200; max_break 15; break_on_wick false; pullback preferred; ema 23; max_wait 11; timeout market; use_higher_close false; skip_late_short 7/3000; one_trade_per_day; side both; workers=2
- **n / metrics:** 7 trades, 57.1% wins, −1319.2 pts, PF 0.63; exits trail4/flatten2/sl1; avg_win +559.8 avg_loss −1186.1
- **Feb month:** 2024-02 same as overall (single month)
- **Result:** results/overnight_XAUUSD_2024-02-01_2024-03-01_20260909T000138Z_96d115c9.json
- **Conclusion:** Feb 2024 milder than Feb 2023 (−1.3k vs −5.2k) but still red. Losses: flatten −846.5 / SL −2000 / flatten residual. Next: SL1500 (one-knob) on Feb 2023 vs SL2000 baseline.
### 2026-09-09 Asia SL1500 one-knob Feb 2023 (vs SL2000 baseline)
- **Window:** 2023-02-01 → 2023-03-01
- **Params:** same best-seed except **sl_fixed_pts=1500** (was 2000); TP2000 flatten22 trail asia 3000/cap1800/trail400; workers=2
- **n / metrics:** 11 trades, 45.5% wins, −3680 pts, PF 0.42; exits sl3/flatten5/trail3; avg_win +537.5 avg_loss −1061.2
- **vs SL2000 baseline same window:** 11t 45.5% −5180 PF0.34 → **same wins, −1500 pts less loss** (avg_loss −1311 → −1061); still red month
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T003301Z_50721039.json
- **Conclusion:** SL1500 is a clear loss-asymmetric win on Feb 2023 (preserves win% / n, cuts SL hits). Next: SL1500 on Feb 2024 vs SL2000 Feb 2024 baseline (−1319 PF0.63).

### 2026-09-09 Asia SL1500 one-knob Feb 2024 (vs SL2000 baseline)
- **Window:** 2024-02-01 – 2024-03-01
- **Params:** same best-seed except **sl_fixed_pts=1500** (was 2000); TP2000 flatten22 trail asia 3000/cap1800/trail400; workers=2
- **n / metrics:** 7 trades, 57.1% wins, −819.2 pts, PF 0.73; exits trail4/flatten2/sl1; avg_win +559.8 avg_loss −1019.4
- **vs SL2000 baseline same window:** 7t 57.1% −1319 PF0.63 → **same wins, −500 pts less loss** (avg_loss −1186 → −1019); still red month
- **Feb month:** 2024-02 same as overall
- **Result:** results/overnight_XAUUSD_2024-02-01_2024-03-01_20260909T013143Z_4d55872e.json
- **Conclusion:** SL1500 also loss-asymmetric on Feb 2024 (preserves win%/n). Combined with Feb 2023, prefer SL1500. Next: flatten_hour=20 + SL1500 on Feb 2023 vs baselines.


### 2026-09-09 Asia flatten20+SL1500 Feb 2023 (vs SL1500/flatten22)
- **Window:** 2023-02-01 – 2023-03-01
- **Params:** same preferred SL1500 seed except **flatten_hour=20** (was 22); trail asia 3000/cap1800/trail400; workers=2
- **n / metrics:** 11 trades, 36.4% wins, −4304 pts, PF 0.38; exits sl3/flatten5/trail3; avg_win +666.2 avg_loss −995.5
- **vs SL1500/flatten22 same window:** 11t 45.5% −3680 PF0.42 → **worse**: win% −9.1pp (hurt wins), sum −624 pts more loss
- **vs SL2000/flatten22 baseline:** still better on SL alone but flatten20 undoes that edge
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T021342Z_4a43138d.json
- **Conclusion:** Reject flatten_hour=20 (loss-asymmetric fail — cuts wins). Keep flatten22. Next: trail_arm_cap_pts=1500 (was 1800) + SL1500 flatten22 on Feb 2023.


### 2026-09-09 Asia trail_arm_cap=1500+SL1500 Feb 2023 (vs SL1500/cap1800)
- **Window:** 2023-02-01 — 2023-03-01
- **Params:** preferred SL1500/flatten22 seed except **trail_arm_cap_pts=1500** (was 1800); trail asia 3000/trail400; workers=2
- **n / metrics:** 11 trades, 45.5% wins, −3680 pts, PF 0.42; exits sl3/flatten5/trail3; avg_win +537.5 avg_loss −1061.2
- **vs SL1500/cap1800 same window:** 11t 45.5% −3680 PF0.42 → **identical** (no Feb trade hit the 1500–1800 cap band)
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T032552Z_8ea871af.json
- **Conclusion:** Reject trail_arm_cap=1500 as a no-op on Feb 2023 (neither helps nor hurts). Keep cap1800. Next: trail_pts=300 (tighter) + SL1500 flatten22 on Feb 2023 vs SL1500/trail400.


### 2026-09-09 Asia trail_pts=300+SL1500 Feb 2023 (vs SL1500/trail400)
- **Window:** 2023-02-01 - 2023-03-01
- **Params:** preferred SL1500/flatten22/cap1800 seed except **trail_pts=300** (was 400); trail asia 3000; workers=2
- **n / metrics:** 11 trades, 45.5% wins, -3721 pts, PF 0.42; exits sl3/flatten5/trail3; avg_win +529.3 avg_loss -1061.2
- **vs SL1500/trail400 same window:** 11t 45.5% -3680 PF0.42 -> **slightly worse** (-41 pts; avg_win 537.5 -> 529.3)
- **vs SL2000 baseline:** still better on SL alone; tighter trail does not help Feb
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T041607Z_6b86415a.json
- **Conclusion:** Reject trail_pts=300 (mild win-side haircut, no loss cut). Keep trail400. Next: max_hold_hours=10 + SL1500 flatten22 trail400 on Feb 2023 vs SL1500/hold14.


### 2026-09-09 Asia max_hold=10+SL1500 Feb 2023 (vs SL1500/hold14)
- **Window:** 2023-02-01 - 2023-03-01
- **Params:** preferred SL1500/flatten22/cap1800/trail400 seed except **max_hold_hours=10** (was 14); trail asia 3000; workers=2
- **n / metrics:** 11 trades, 36.4% wins, -4385.4 pts, PF 0.37; exits sl3/flatten5/trail3; avg_win +644.6 avg_loss -994.8
- **vs SL1500/hold14 same window:** 11t 45.5% -3680 PF0.42 -> **worse**: win% -9.1pp (hurt wins), sum -705 pts more loss
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T052031Z_536f779c.json
- **Conclusion:** Reject max_hold=10 (loss-asymmetric fail — cuts wins). Keep hold14. Next: skip_late_short_wait=5 (was 7) + SL1500 flatten22 hold14 on Feb 2023 vs SL1500 baseline.


### 2026-09-09 Asia skip_late_wait=5+SL1500 Feb 2023 (vs SL1500 wait=7)
- **Window:** 2023-02-01 - 2023-03-01
- **Params:** preferred SL1500/flatten22/hold14/trail400 except **skip_late_short_wait=5** (was 7); workers=2
- **n / metrics:** 11 trades, 45.5% wins, -3680 pts, PF 0.42
- **vs SL1500 wait=7:** identical (no-op on this Feb)
- **Conclusion:** Reject skip_late=5 as no-op. Keep wait=7. Next: news_mode=filter + SL1500 on Feb 2023.


### 2026-09-09 Asia news_mode=filter+SL1500 Feb 2023 (vs SL1500 news=off)
- **Window:** 2023-02-01 - 2023-03-01
- **Params:** preferred SL1500/flatten22/hold14/trail400 except **news_mode=filter** (news_set=scheduled); workers=2
- **n / metrics:** 10 trades, 40.0% wins, -4480.5 pts, PF 0.30; exits sl3/flatten5/trail2; avg_win +471.7 avg_loss -1061.2
- **vs SL1500 news=off same window:** 11t 45.5% -3680 PF0.42 -> **worse**: n -1, win% -5.5pp (hurt wins), sum -800 pts more loss; skipped 3 news_day
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T071122Z_a0e45c32.json
- **Conclusion:** Reject news_mode=filter (loss-asymmetric fail — cuts wins). Keep news=off. Keeper remains SL1500. Next: SL1250 (further tighten) + flatten22 hold14 trail400 on Feb 2023 vs SL1500.


### 2026-09-09 Asia SL1250 one-knob Feb 2023 (vs SL1500)
- **Window:** 2023-02-01 - 2023-03-01
- **Params:** preferred SL1500 seed except **sl_fixed_pts=1250** (was 1500); TP2000 flatten22 hold14 trail asia 3000/cap1800/trail400; news=off; workers=2
- **n / metrics:** 11 trades, 45.5% wins, -3455.5 pts, PF 0.44; exits sl4/flatten4/trail3; avg_win +537.5 avg_loss -1023.8
- **vs SL1500 same window:** 11t 45.5% -3680 PF0.42 -> mild improve: same wins, -224.5 pts less loss, PF 0.42->0.44; but SL exits 3->4 (one flatten became SL)
- **vs SL2000 baseline:** still better on SL alone (-3455 vs -5180)
- **Feb month:** 2023-02 same as overall
- **Result:** results/overnight_XAUUSD_2023-02-01_2023-03-01_20260909T072415Z_ffaf6bdf.json
- **Conclusion:** Mild loss-asymmetric on Feb 2023 only — do NOT promote keeper yet. Need Feb 2024 confirm before preferring SL1250 over SL1500 (SL1200 previously hurt 2026Q1). Next when overnight idle: SL1250 on Feb 2024 vs SL1500 Feb 2024 (-819 PF0.73). Rejected on Feb 2023 so far: flatten20, trail_arm_cap1500, trail_pts300, max_hold10, skip_late5, news_filter. Pending: SL1250 Feb 2024.

### 2026-09-09 Asia 2024+ UI-mistaken baseline (NOT true live) — archived
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** mostly reaktor live seed BUT **max_break_candles_after=8** (live=15) and **trail_arm_pts=400** (live=3000); trail_arm_mode=asia cap1800 trail400; SL/TP fixed 2000; flatten22; pullback preferred; timeout market; ema23; max_wait11; skip_late 7/3000; max_hold14
- **n / metrics:** 223 trades, 67.3% wins, +90048.3 pts, PF 1.75; avg_win +1399.2 avg_loss -1641.5
- **exits:** {'flatten': 34, 'trail': 77, 'sl': 52, 'tp': 60}
- **by_month:** 2024-01: 7t 57.1% +1177 PF1.81; 2024-02: 2t 50.0% -1466 PF0.27; 2024-03: 5t 80.0% +808 PF1.67; 2024-04: 3t 66.7% +252 PF1.13; 2024-05: 7t 71.4% +1363 PF1.34; 2024-06: 5t 60.0% -2167 PF0.46; 2024-07: 6t 66.7% +3406 PF2.43; 2024-08: 7t 42.9% -1860 PF0.67; 2024-09: 8t 75.0% +1672 PF1.49; 2024-10: 12t 58.3% -1515 PF0.79; 2024-11: 8t 62.5% +2046 PF1.6; 2024-12: 4t 25.0% -4239 PF0.12; 2025-01: 9t 88.9% +5886 PF30.58; 2025-02: 9t 77.8% +7378 PF2.84; 2025-03: 5t 100.0% +3489 PFNone; 2025-04: 4t 100.0% +6166 PFNone; 2025-05: 8t 100.0% +13834 PFNone; 2025-06: 5t 60.0% +2855 PF2.16; 2025-07: 7t 71.4% +5062 PF2.89; 2025-08: 7t 42.9% -807 PF0.86; 2025-09: 8t 37.5% -3768 PF0.5; 2025-10: 7t 71.4% +4054 PF2.01; 2025-11: 8t 50.0% -1716 PF0.79; 2025-12: 9t 55.6% +1474 PF1.18; 2026-01: 9t 55.6% +499 PF1.06; 2026-02: 8t 87.5% +12000 PF7.0; 2026-03: 7t 85.7% +9489 PF5.74; 2026-04: 6t 66.7% +4000 PF2.0; 2026-05: 10t 80.0% +8872 PF3.22; 2026-06: 8t 37.5% -4597 PF0.54; 2026-07: 6t 66.7% +3422 PF1.86; 2026-08: 7t 85.7% +9524 PF5.76; 2026-09: 2t 100.0% +3458 PFNone
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T101752Z_21c2f179.json
- **Conclusion:** Mistaken UI seed — do **not** treat as live baseline. True live (max_break=15, trail_arm_pts=3000) kicked immediately after; log that when it finishes as **2024+ reaktor live baseline (correct)**.

### 2026-09-09 Asia 2024+ near-live miss (trail_arm=3500 — NOT exact true live) — archived
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** almost reaktor live seed BUT **trail_arm_pts=3500** (live=3000); max_break=15; trail_arm_mode=asia cap1800 trail400; SL/TP fixed 2000; flatten22; pullback preferred; timeout market; ema23; max_wait11; skip_late 7/3000; max_hold14; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +211040.1 pts, PF 2.36; avg +587.9 avg_win +1383.0 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten50 / trail143 / sl68 / tp98
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60% +1684 PF1.26; 2024-05 12t 75% +4857 PF2.2; 2024-06 8t 75% −498 PF0.88; 2024-07 13t 84.6% +10989 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 14t 78.6% +7428 PF2.65; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90% +13834 PF7.92; 2025-06 10t 70% +5631 PF1.94; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1793 PF1.18; 2025-12 10t 80% +10789 PF3.7; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8969 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T112059Z_fe64da35.json
- **Conclusion:** Near-live miss (trail_arm 3500≠3000) — do **not** treat as live baseline. Exact true live (max_break=15, trail_arm_pts=3000, workers=4) kicked immediately after ~15:22 Europe/Bucharest; when that finishes: ping Igor + append as **2024+ reaktor live baseline (correct)**, then new-knob sweeps (SL1500, timeout_max_ema_dist/timeout_min_break, sl_cap_pts, week2_mode+trend_efficiency_min, trail/flatten).


### 2026-09-09 Asia **2024+ reaktor live baseline (correct)**
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact reaktor GitHub ASIA_BREAKOUT_CONFIG XAU — asia 1–7; min_asia_range 300; break ±200; **max_break_candles_after=15**; pullback preferred; ema 23; max_wait 11; timeout market; use_higher_close false; resume 1; skip_late 7/3000; sl fixed **2000**; tp fixed 2000; trail_arm_mode=asia **trail_arm_pts=3000** trail_arm_cap=1800 trail_pts=400; max_hold 14; flatten 22; one_trade_per_day; side both; break_on_wick false; wait_from_break false; new knobs 0/off; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +211040.1 pts, PF 2.36; avg +587.9 avg_win +1383.0 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten50 / trail143 / sl68 / tp98
- **entries:** ema_touch 137 / timeout_market 222
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60% +1684 PF1.26; 2024-05 12t 75% +4857 PF2.2; 2024-06 8t 75% −498 PF0.88; 2024-07 13t 84.6% +10989 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 14t 78.6% +7428 PF2.65; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90% +13834 PF7.92; 2025-06 10t 70% +5631 PF1.94; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1793 PF1.18; 2025-12 10t 80% +10789 PF3.7; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8969 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T124024Z_83e24a6d.json
- **Note:** Identical aggregates vs near-live miss (trail_arm=3500) — trail arm 3000↔3500 was a no-op on this window (no trade differentiated in that band).
- **Conclusion:** This is the **correct 2024+ reaktor live baseline**. Next new-knob sweeps on same window: SL1500, then timeout_max_ema_dist/timeout_min_break, sl_cap_pts, week2_mode+trend_efficiency_min, trail/flatten.

### 2026-09-09 Asia SL1500 one-knob 2024+ (vs live SL2000 baseline) — REJECT
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **sl_fixed_pts=1500** (was 2000); TP2000; max_break=15; trail asia 3000/cap1800/trail400; flatten22 hold14; timeout market; new knobs 0/off; workers=4
- **n / metrics:** 359 trades, 69.1% wins (248W/111L), +189643.7 pts, PF 2.25; avg +528.3 avg_win +1374.6 avg_loss −1362.6; trail_armed 228/63.5%; skipped 336
- **exits:** sl96 / flatten36 / trail137 / tp90
- **entries:** ema_touch 137 / timeout_market 222
- **vs live SL2000 baseline same window:** 359t 73.8% +211040.1 PF2.36 → **worse**: same n, win% −4.7pp (265→248 wins), sum −21396 pts, PF −0.11; SL exits 68→96, flatten 50→36, tp 98→90 (tighter SL converts winners/flatten into SL hits)
- **by_month (compact):** 2024-01 11t 72.7% +3181 PF2.56; 2024-02 7t 57.1% −819 PF0.73; 2024-03 9t 88.9% +3608 PF3.41; 2024-04 10t 60% +2249 PF1.37; 2024-05 12t 75% +4410 PF1.98; 2024-06 8t 75% +502 PF1.17; 2024-07 13t 84.6% +11489 PF6.54; 2024-08 13t 61.5% +4102 PF1.79; 2024-09 10t 80% +4061 PF2.85; 2024-10 14t 71.4% +2485 PF1.41; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +1594 PF1.45; 2025-01 13t 84.6% +5746 PF2.92; 2025-02 13t 69.2% +9503 PF2.58; 2025-03 14t 71.4% +5452 PF1.91; 2025-04 9t 66.7% +4536 PF2.01; 2025-05 10t 90% +14334 PF10.56; 2025-06 10t 70% +7131 PF2.58; 2025-07 11t 63.6% +7157 PF2.79; 2025-08 8t 75% +6156 PF3.05; 2025-09 13t 53.8% +4374 PF1.69; 2025-10 14t 85.7% +17937 PF6.98; 2025-11 12t 33.3% −4550 PF0.62; 2025-12 10t 60% +5475 PF1.91; 2026-01 14t 57.1% +4515 PF1.5; 2026-02 9t 77.8% +9579 PF4.19; 2026-03 12t 58.3% +5411 PF1.72; 2026-04 12t 58.3% +5978 PF1.8; 2026-05 15t 80% +16507 PF4.67; 2026-06 10t 60% +5105 PF1.85; 2026-07 12t 50% +1374 PF1.15; 2026-08 9t 77.8% +9969 PF4.32; 2026-09 5t 80% +5534 PF4.69
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T132957Z_6352dd42.json
- **Conclusion:** **Reject SL1500 on full 2024+ window.** Feb loss-month cut does not generalize — overall win% and PnL both drop vs live SL2000. Keeper remains **live SL2000**. Next: timeout_max_ema_dist_pts=300 one-knob on same window (live seed).


### 2026-09-09 Asia timeout_max_ema_dist=300 one-knob 2024+ (vs live baseline) — REJECT
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **timeout_max_ema_dist_pts=300** (was 0/off); SL/TP 2000; max_break=15; trail asia 3000/cap1800/trail400; flatten22 hold14; timeout_min_break=0; workers=4
- **n / metrics:** 202 trades, 71.8% wins (145W/57L), +94841.0 pts, PF 2.01; avg +469.5 avg_win +1298.8 avg_loss −1640.1; trail_armed 133/65.8%; skipped 493
- **exits:** flatten30 / trail81 / sl40 / tp51
- **entries:** ema_touch 137 / timeout_market 65 (baseline had timeout_market 222 — filter cut ~157 timeout fills via no_pullback_timeout)
- **vs live baseline same window:** 359t 73.8% +211040.1 PF2.36 → **worse**: n −157, win% −2.0pp, sum −116199 pts, PF −0.35
- **by_month (compact):** 2024-01 9t 77.8% +3583 PF3.83; 2024-02 6t 50% −1681 PF0.53; 2024-03 5t 100% +2008; 2024-04 4t 75% +1644 PF1.82; 2024-05 8t 75% +3046 PF2.01; 2024-06 6t 66.7% −1332 PF0.67; 2024-07 10t 90% +9978 PF18.36; 2024-08 10t 60% +1358 PF1.26; 2024-09 5t 80% +416 PF1.21; 2024-10 11t 63.6% −1055 PF0.85; 2024-11 4t 75% +2452 PF3.38; 2024-12 5t 60% −225 PF0.94; 2025-01 12t 100% +11312; 2025-02 8t 62.5% +3300 PF1.55; 2025-03 6t 66.7% +78 PF1.02; 2025-04 3t 66.7% +12 PF1.01; 2025-05 5t 80% +5432 PF3.72; 2025-06 1t 0% −2000; 2025-07 8t 62.5% +4385 PF2.47; 2025-08 5t 80% +4838 PF4.32; 2025-09 9t 44.4% −1176 PF0.82; 2025-10 7t 85.7% +8407 PF5.2; 2025-11 7t 57.1% +1470 PF1.24; 2025-12 5t 60% +2000 PF1.5; 2026-01 6t 83.3% +6039 PF4.02; 2026-02 6t 83.3% +6579 PF4.29; 2026-03 3t 66.7% +2000 PF2.0; 2026-04 4t 50% 0 PF1.0; 2026-05 6t 100% +10401; 2026-06 6t 66.7% +3572 PF1.89; 2026-07 6t 50% 0 PF1.0; 2026-08 4t 75% +4000 PF3.0; 2026-09 2t 100% +4000
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T150141Z_bbc2c7b2.json
- **Conclusion:** **Reject timeout_max_ema_dist=300.** Filters away profitable timeout_market volume; win% and total PnL both drop vs live. Keeper remains live (timeout filters off). Next: timeout_min_break_pts=400 one-knob same window (live seed).


### 2026-09-09 Asia mistaken trail_arm=off/0 ablation 2024+ (vs live baseline) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** intended live seed BUT **trail_arm_mode=fixed trail_arm_pts=0** (live=asia/3000); also **wait_from_break=true** (live=false); timeout_min_break=0; timeout_max_ema=0; SL/TP 2000; max_break=15; trail_pts=400 cap1800; flatten22 hold14; workers=3
- **n / metrics:** 350 trades, 68.9% wins (241W/109L), +241970.0 pts, PF 2.48; avg +691.3 avg_win +1684.0 avg_loss -1503.4; trail_armed 0/0.0%; skipped 345
- **exits:** {"flatten":98,"tp":185,"sl":67}
- **entries:** {"ema_touch":189,"timeout_market":161}
- **vs live baseline same window:** 359t 73.8% +211040.1 PF2.36 → **mixed**: n −9, win% −4.9pp (hurt), sum +30930 pts / PF +0.12 (higher raw PnL because TP fills replace trail locks); trail never armed
- **by_month (compact):** 2024-01 11t 63.6% +2225 PF2.09; 2024-02 7t 28.6% -4758 PF0.09; 2024-03 9t 66.7% +5716 PF2.79; 2024-04 10t 60.0% +904 PF1.14; 2024-05 12t 66.7% +8777 PF3.05; 2024-06 7t 57.1% +1234 PF1.23; 2024-07 13t 76.9% +12667 PF5.14; 2024-08 13t 46.2% -636 PF0.92; 2024-09 10t 60.0% +6999 PF2.4; 2024-10 13t 61.5% -83 PF0.99; 2024-11 9t 55.6% +1276 PF1.26; 2024-12 8t 50.0% +1531 PF1.35; 2025-01 11t 100.0% +14186 PFNone; 2025-02 13t 69.2% +10793 PF2.66; 2025-03 13t 69.2% +8831 PF3.08; 2025-04 9t 77.8% +8607 PF3.15; 2025-05 10t 90.0% +13650 PF7.82; 2025-06 9t 77.8% +8753 PF3.19; 2025-07 11t 72.7% +11362 PF4.8; 2025-08 7t 85.7% +5532 PF4.8; 2025-09 13t 53.8% +3880 PF1.46; 2025-10 13t 69.2% +10000 PF2.25; 2025-11 12t 58.3% +4186 PF1.48; 2025-12 10t 70.0% +8339 PF2.47; 2026-01 14t 78.6% +16000 PF3.67; 2026-02 9t 77.8% +10000 PF3.5; 2026-03 12t 58.3% +4000 PF1.4; 2026-04 12t 66.7% +8000 PF2.0; 2026-05 15t 93.3% +26000 PF14.0; 2026-06 10t 80.0% +12000 PF4.0; 2026-07 11t 54.5% +2000 PF1.2; 2026-08 9t 77.8% +10000 PF3.5; 2026-09 5t 100.0% +10000 PFNone
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260909T172225Z_78a8804c.json
- **Conclusion:** **Do not promote trail_arm=off.** Win% drop vs live is decisive for a clean edge; PnL/PF bump is mostly TP-vs-trail accounting and run also had wait_from_break=true (confound). Keeper remains **live trail asia 3000**. Next: correct **timeout_min_break_pts=400** one-knob (true live seed: trail asia 3000, wait_from_break false, workers=4).

### 2026-09-09 Asia timeout_min_break_pts=400 one-knob 2024+ (vs live baseline) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **timeout_min_break_pts=400** (was 0/off); trail asia 3000/cap1800/trail400; wait_from_break false; max_break 15; SL/TP fixed 2000; flatten22 hold14; timeout_max_ema=0; workers=4
- **n / metrics:** 214 trades, 75.7% wins (162W/52L), +145638.1 pts, PF 2.63; avg +680.6 avg_win +1449.5 avg_loss −1714.9; trail_armed 148/69.2%; skipped 481
- **exits:** flatten27 / trail79 / sl40 / tp68
- **entries:** ema_touch 137 / timeout_market 77 (baseline timeout_market 222 — filter cut ~145 timeout fills via no_pullback_timeout; ema_touch unchanged)
- **vs live baseline same window:** 359t 73.8% +211040.1 PF2.36 → **mixed quality, worse absolute**: n −145 (−40%), win% +1.9pp, PF +0.27, sum −65402 pts (−31%); cleaner on remaining trades but loses too much timeout-market volume
- **by_month (compact):** 2024-01 8t 75% +2076 PF2.64; 2024-02 0t; 2024-03 4t 100% +1695; 2024-04 5t 40% −1675 PF0.63; 2024-05 6t 66.7% +461 PF1.15; 2024-06 4t 50% −2633 PF0.34; 2024-07 5t 80% +4094 PF8.12; 2024-08 9t 55.6% −72 PF0.99; 2024-09 5t 100% +4416; 2024-10 7t 71.4% −495 PF0.88; 2024-11 5t 80% +3623 PF4.51; 2024-12 4t 50% −2225 PF0.40; 2025-01 9t 100% +8746; 2025-02 7t 85.7% +7503 PF4.75; 2025-03 8t 100% +7808; 2025-04 6t 66.7% +2012 PF1.50; 2025-05 5t 100% +9509; 2025-06 6t 66.7% +3432 PF1.86; 2025-07 4t 75% +4722 PF15.71; 2025-08 5t 80% +5331 PF4.66; 2025-09 8t 62.5% +4858 PF2.19; 2025-10 10t 80% +9883 PF3.47; 2025-11 10t 60% +2920 PF1.37; 2025-12 5t 60% +2000 PF1.50; 2026-01 8t 75% +6039 PF2.51; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 10t 80% +10442 PF3.61; 2026-04 8t 75% +7478 PF2.87; 2026-05 9t 88.9% +11954 PF6.98; 2026-06 9t 77.8% +9105 PF3.28; 2026-07 7t 57.1% +952 PF1.16; 2026-08 5t 80% +5524 PF3.76; 2026-09 4t 100% +7576
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T181310Z_715a7963.json
- **Conclusion:** **Do not promote timeout_min_break=400 over live.** PF/win% improve but absolute PnL and trade count drop hard (same ema_touch book, starved timeouts). Keeper remains **live (timeout filters off)**. Next: **sl_cap_pts** probe — note `sl_cap` only applies when `sl_mode != fixed`, so kick live seed with **sl_mode=asia_opposite + sl_cap_pts=2000** (cap at live fixed distance); then week2_mode+trend_efficiency_min, trail/flatten.


### 2026-09-09 Asia sl_mode=asia_opposite + sl_cap_pts=2000 2024+ (vs live fixed SL2000) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** live reaktor seed except **sl_mode=asia_opposite + sl_cap_pts=2000** (live=sl_mode=fixed / sl_cap=0; sl_cap only applies off fixed); trail asia 3000/cap1800/trail400; wait_from_break false; max_break 15; TP fixed 2000; flatten22 hold14; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 69.6% wins (250W/109L), +197807.8 pts, PF 2.28; avg +551.0 avg_win +1407.2 avg_loss −1412.7; trail_armed 229/63.8%; skipped 336
- **exits:** sl93 / trail131 / flatten38 / tp97
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live baseline same window:** 359t 73.8% +211040.1 PF2.36 → **worse**: same n, win% −4.2pp (265→250 wins), sum −13232 pts, PF −0.08; SL exits 68→93 (asia_opposite widens some SLs even with cap2000, converts winners)
- **by_month (compact):** 2024-01 11t 63.6% +2438 PF2.01; 2024-02 7t 57.1% +118 PF1.06; 2024-03 9t 88.9% +4478 PF8.11; 2024-04 10t 50.0% +935 PF1.16; 2024-05 12t 66.7% +3444 PF1.8; 2024-06 8t 75.0% +1638 PF1.88; 2024-07 13t 76.9% +9934 PF4.74; 2024-08 13t 53.8% +1840 PF1.28; 2024-09 10t 60.0% +1498 PF1.49; 2024-10 14t 57.1% +1839 PF1.32; 2024-11 9t 66.7% +4464 PF3.33; 2024-12 8t 62.5% +2415 PF1.9; 2025-01 13t 92.3% +9153 PF6.75; 2025-02 13t 69.2% +10906 PF3.37; 2025-03 14t 71.4% +5480 PF1.98; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 10t 70.0% +6184 PF2.14; 2025-07 11t 63.6% +6743 PF2.53; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1793 PF1.18; 2025-12 10t 70.0% +8034 PF2.48; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80.0% +11340 PF4.01; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8968 PF3.24; 2026-09 5t 80.0% +5419 PF4.36
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T194057Z_f5707355.json
- **Conclusion:** **Reject asia_opposite+sl_cap=2000.** Same trade count as live fixed SL2000 but win% and PnL both drop; cap does not beat fixed. Keeper remains **live sl_mode=fixed SL2000 (sl_cap unused)**. Next: **week2_mode=filter + trend_efficiency_min=0.35** (live seed, workers=4) same window; then trail/flatten.


### 2026-09-09 Asia week2_mode=filter + trend_efficiency_min=0.35 2024+ (vs live baseline) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** live reaktor seed except **week2_mode=filter + trend_efficiency_min=0.35** (live=week2 off / 0); trend_flat_pts=1500 trend_sessions=10; trail asia 3000/cap1800/trail400; wait_from_break false; max_break 15; SL/TP fixed 2000; flatten22 hold14; timeout knobs 0; workers=4
- **n / metrics:** 300 trades, 74.0% wins (222W/78L), +174527.2 pts, PF 2.39; avg +581.8 avg_win +1352.9 avg_loss −1613.0; trail_armed 201/67.0%; skipped 395
- **exits:** flatten46 / trail123 / sl54 / tp77
- **entries:** ema_touch 116 / timeout_market 184
- **skip_reasons:** no_break 318 / seasonal_bias 64 / late_short 12 / asia_too_small 1 (seasonal_bias=week2 filter cuts)
- **vs live baseline same window:** 359t 73.8% +211040.1 PF2.36 → **worse absolute**: n −59 (−16%), win% +0.2pp, PF +0.03, sum −36513 pts (−17%); filter removes ~59 trades via seasonal_bias without lifting expectancy enough
- **by_month (compact):** 2024-01 9t 66.7% +1476 PF1.89; 2024-02 7t 57.1% -1319 PF0.63; 2024-03 7t 100.0% +4802; 2024-04 7t 71.4% +4125 PF2.61; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% -498 PF0.88; 2024-07 10t 80.0% +6185 PF3.4; 2024-08 12t 58.3% +2417 PF1.44; 2024-09 8t 87.5% +3826 PF2.91; 2024-10 12t 66.7% -1191 PF0.83; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 7t 71.4% +2907 PF2.32; 2025-01 10t 100.0% +9006; 2025-02 9t 77.8% +8861 PF3.22; 2025-03 12t 75.0% +4643 PF2.03; 2025-04 7t 85.7% +7036 PF4.52; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 9t 66.7% +4321 PF1.72; 2025-07 10t 70.0% +7326 PF3.45; 2025-08 6t 83.3% +4287 PF3.94; 2025-09 10t 60.0% +4374 PF2.0; 2025-10 11t 90.9% +15431 PF8.72; 2025-11 9t 44.4% -2550 PF0.75; 2025-12 9t 77.8% +8789 PF3.2; 2026-01 12t 66.7% +5515 PF1.69; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 9t 66.7% +4952 PF1.83; 2026-04 9t 55.6% +1478 PF1.18; 2026-05 13t 84.6% +14442 PF4.61; 2026-06 8t 75.0% +7105 PF2.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 4t 75.0% +4000 PF3.0; 2026-09 4t 100.0% +7576
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T203930Z_8bbda6ad.json
- **Conclusion:** **Reject week2_mode=filter @ trend_efficiency_min=0.35.** Near-flat win%/PF but loses trade count and absolute PnL. Keeper remains **live (week2 off)**. Next: trail/flatten probes on live seed — start **flatten_hour=20** one-knob (live=22).

### 2026-09-10 Asia flatten_hour=20 one-knob 2024+ (vs live flatten22) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **flatten_hour=20** (live=22); trail asia 3000/cap1800/trail400; wait_from_break false; max_break 15; SL/TP fixed 2000; max_hold14; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 72.4% wins (260W/99L), +205309.5 pts, PF 2.32; avg +571.9 avg_win +1386.7 avg_loss −1568.0; trail_armed 238/66.3%; skipped 336
- **exits:** flatten58 / trail138 / sl66 / tp97
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live flatten22 baseline same window:** 359t 73.8% +211040.1 PF2.36 → **worse**: same n, win% −1.4pp (265→260), sum −5730.6 pts, PF −0.04; flatten exits 50→58 (earlier flatten converts some winners)
- **by_month (compact):** 2024-01 11t 63.6% +3338 PF2.93; 2024-02 7t 57.1% −1128 PF0.66; 2024-03 9t 88.9% +3598 PF2.8; 2024-04 10t 60% +1229 PF1.18; 2024-05 12t 75% +4299 PF1.95; 2024-06 8t 75% −616 PF0.85; 2024-07 13t 76.9% +9981 PF5.98; 2024-08 13t 61.5% +3551 PF1.61; 2024-09 10t 80% +4224 PF3.07; 2024-10 14t 64.3% +945 PF1.13; 2024-11 9t 88.9% +6138 PF8.8; 2024-12 8t 62.5% +808 PF1.19; 2025-01 13t 100% +12064; 2025-02 13t 69.2% +7126 PF1.94; 2025-03 14t 71.4% +5712 PF2.24; 2025-04 9t 55.6% +2269 PF1.37; 2025-05 10t 90% +13834 PF7.92; 2025-06 10t 70% +5945 PF1.99; 2025-07 11t 72.7% +9254 PF4.02; 2025-08 8t 87.5% +8034 PF7.54; 2025-09 13t 46.2% +2777 PF1.36; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1574 PF1.16; 2025-12 10t 80% +9481 PF3.37; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8969 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T214859Z_0718b931.json
- **Conclusion:** **Reject flatten_hour=20.** Same trade count as live flatten22 but win% and PnL both drop mildly (earlier flatten hurts). Keeper remains **live flatten_hour=22**. Next: trail probes on live seed — start **trail_pts=500** (live=400); then trail_arm_pts=2500.



### 2026-09-10 Asia trail_pts=500 one-knob 2024+ (vs live trail400) — NEAR-FLAT MILD+ / do not promote alone
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **trail_pts=500** (live=400); trail_arm asia 3000/cap1800; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +213044.3 pts, PF 2.37; avg +593.4 avg_win +1390.6 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten53 / trail128 / sl68 / tp110
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live trail400 baseline same window:** 359t 73.8% +211040.1 PF2.36 → **near-flat mild+**: same n, same win%, sum +2004 pts, PF +0.01; slightly more trail/tp vs flatten mix — noise-scale edge, not a clear promote
- **by_month (compact):** 2024-01 11t 72.7% +3430 PF3.06; 2024-02 7t 57.1% −1564 PF0.56; 2024-03 9t 88.9% +2807 PF2.4; 2024-04 10t 60% +1184 PF1.18; 2024-05 12t 75% +5628 PF2.39; 2024-06 8t 75% +583 PF1.15; 2024-07 13t 84.6% +10489 PF5.07; 2024-08 13t 61.5% +3529 PF1.64; 2024-09 10t 80% +6731 PF3.49; 2024-10 14t 71.4% +1639 PF1.23; 2024-11 9t 77.8% +5161 PF5.03; 2024-12 8t 62.5% +1164 PF1.28; 2025-01 13t 100% +12266; 2025-02 13t 69.2% +8358 PF2.2; 2025-03 14t 78.6% +6790 PF2.5; 2025-04 9t 66.7% +3431 PF1.57; 2025-05 10t 90% +13434 PF7.72; 2025-06 10t 70% +5531 PF1.92; 2025-07 11t 72.7% +9159 PF4.06; 2025-08 8t 87.5% +7336 PF6.04; 2025-09 13t 53.8% +2723 PF1.33; 2025-10 14t 85.7% +16337 PF5.08; 2025-11 12t 58.3% +1593 PF1.16; 2025-12 10t 80% +10589 PF3.65; 2026-01 14t 57.1% +2132 PF1.18; 2026-02 9t 77.8% +8279 PF3.07; 2026-03 12t 66.7% +6142 PF1.77; 2026-04 12t 66.7% +7378 PF1.92; 2026-05 15t 86.7% +18391 PF5.6; 2026-06 10t 80% +11472 PF3.87; 2026-07 12t 58.3% +3323 PF1.33; 2026-08 9t 77.8% +8769 PF3.19; 2026-09 5t 100% +8834
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T222230Z_c68542a3.json
- **Conclusion:** **Do not promote trail_pts=500 alone.** Identical win%/n vs live; +~2k pts / +0.01 PF is noise-scale. Keeper remains **live trail_pts=400** (optional soft alternate). Next: **trail_arm_pts=2500** one-knob (live seed trail_pts=400, workers=4).




### 2026-09-10 Asia trail_arm_pts=2500 one-knob 2024-01	o2026-10 (vs live trail_arm=3000)
- **Window:** 2024-01-01 – 2026-10-01
- **Params:** true live seed except **trail_arm_pts=2500** (was 3000); trail asia, trail_pts=400, flatten22, wait_from_break false, max_break 15, week2 off, workers=4
- **n / metrics:** 359 trades, 73.8% wins, +211040 pts, PF 2.36; exits flatten50/trail143/sl68/tp98; avg_win +1383.0 avg_loss −1653.8; trail_armed 242 (67.4%)
- **vs live baseline (trail_arm=3000):** 359t 73.8% +211040 PF2.36 → **identical** (no-op on this window)
- **by_month:** 2024-01 11t 72.7% +3556; 2024-02 7t 57.1% −1319; 2024-03 9t 88.9% +3108; 2024-04 10t 60.0% +1684; 2024-05 12t 75.0% +4857; 2024-06 8t 75.0% −498; 2024-07 13t 84.6% +10989; 2024-08 13t 61.5% +3781; 2024-09 10t 80.0% +3561; 2024-10 14t 71.4% +1446; 2024-11 9t 77.8% +5561; 2024-12 8t 62.5% +907; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558; 2025-03 14t 78.6% +7428; 2025-04 9t 66.7% +3036; 2025-05 10t 90.0% +13834; 2025-06 10t 70.0% +5631; 2025-07 11t 72.7% +9326; 2025-08 8t 87.5% +7736; 2025-09 13t 53.8% +2374; 2025-10 14t 85.7% +16937; 2025-11 12t 58.3% +1793; 2025-12 10t 80.0% +10789; 2026-01 14t 57.1% +1515; 2026-02 9t 77.8% +8579; 2026-03 12t 66.7% +6442; 2026-04 12t 66.7% +7478; 2026-05 15t 86.7% +18442; 2026-06 10t 80.0% +11105; 2026-07 12t 58.3% +2374; 2026-08 9t 77.8% +8969; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260909T232719Z_c371521a.json
- **Conclusion:** REJECT / do not promote (identical to live). Keep trail_arm_pts=3000. Next: trail_arm_pts=3500 one-knob same window.


### 2026-09-10 Asia trail_arm_pts=3500 one-knob 2024-01→2026-10 (vs live trail_arm=3000)
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** true live seed except **trail_arm_pts=3500** (was 3000); trail asia, trail_pts=400, flatten22, wait_from_break false, max_break 15, week2 off, workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +211040.1 pts, PF 2.36; avg +587.9 avg_win +1383.0 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten50 / trail143 / sl68 / tp98
- **entries:** ema_touch 137 / timeout_market 222
- **vs live baseline (trail_arm=3000):** 359t 73.8% +211040 PF2.36 → **identical** (no-op on this window; same as prior near-live miss at 3500)
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60.0% +1684 PF1.26; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% −498 PF0.88; 2024-07 13t 84.6% +10989 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 14t 78.6% +7428 PF2.65; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 10t 70.0% +5631 PF1.94; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1793 PF1.18; 2025-12 10t 80.0% +10789 PF3.7; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80.0% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8969 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T004821Z_8e331a9a.json
- **Conclusion:** REJECT / do not promote (identical to live). Keep trail_arm_pts=3000. Trail-arm band 2500–3500 is flat on 2024+. Next: **max_hold_hours=12** one-knob (live=14; trail_pts=450 deferred — 500 already near-flat mild+).



### 2026-09-10 Asia max_hold_hours=12 one-knob 2024+ (vs live hold14) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **max_hold_hours=12** (live=14); trail asia 3000/cap1800/trail400; flatten22; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 73.5% wins (264W/95L), +209705.7 pts, PF 2.35; avg +584.1 avg_win +1380.8 avg_loss −1629.7; trail_armed 241/67.1%; skipped 336
- **exits:** flatten52 / trail141 / sl68 / tp98
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live hold14 baseline same window:** 359t 73.8% +211040 PF2.36 → **mild worse**: same n, win% −0.3pp (265→264), sum −1334 pts, PF −0.01; flatten exits 50→52 (earlier max-hold converts a thin slice of winners)
- **by_month (compact):** 2024-01 11t 72.7% +3756 PF3.25; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3252 PF2.63; 2024-04 10t 60.0% +1684 PF1.26; 2024-05 12t 75.0% +4963 PF2.26; 2024-06 8t 75.0% −385 PF0.9; 2024-07 13t 84.6% +11235 PF5.82; 2024-08 13t 61.5% +3840 PF1.7; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1111 PF1.16; 2024-11 9t 77.8% +5976 PF7.0; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +7745 PF2.12; 2025-03 14t 78.6% +6483 PF2.44; 2025-04 9t 66.7% +3048 PF1.51; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 10t 70.0% +5573 PF1.93; 2025-07 11t 72.7% +9199 PF3.95; 2025-08 8t 87.5% +7846 PF6.82; 2025-09 13t 46.2% +2102 PF1.25; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1602 PF1.16; 2025-12 10t 80.0% +10789 PF3.7; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80.0% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8969 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T014246Z_d168d3c3.json
- **Conclusion:** **Reject max_hold_hours=12.** Same trade count as live hold14 but win% and PnL both slip mildly (earlier hold cutoff). Keeper remains **live max_hold_hours=14**. Next: **max_hold_hours=16** one-knob (bracket live=14; trail_pts=450 still deferred).


### 2026-09-10 Asia max_hold_hours=16 one-knob 2024+ (vs live hold14) — NEAR-FLAT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **max_hold_hours=16** (live=14); trail asia 3000/cap1800/trail400; flatten22; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +211403.6 pts, PF 2.36; avg +588.9 avg_win +1384.4 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten50 / trail143 / sl68 / tp98
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live hold14 baseline same window:** 359t 73.8% +211040 PF2.36 → **near-flat**: same n, same win%, same PF, sum +363.5 pts (noise-scale); exit mix identical to live
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60.0% +1684 PF1.26; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% −498 PF0.88; 2024-07 13t 84.6% +10988 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +5560 PF5.34; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 14t 78.6% +7428 PF2.65; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 10t 70.0% +5631 PF1.94; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +2157 PF1.22; 2025-12 10t 80.0% +10789 PF3.7; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80.0% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8968 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T022432Z_a81f99c9.json
- **Conclusion:** **Do not promote max_hold_hours=16.** Identical n/win%/PF vs live hold14; +~0.4k pts is noise. Hold band 12–16: 12 mild worse, 14 live, 16 flat. Keeper remains **live max_hold_hours=14**. Next: **trail_pts=450** one-knob (bracket live=400 vs prior 500 near-flat mild+).

### 2026-09-10 Asia trail_pts=450 one-knob 2024+ (vs live trail400) — NEAR-FLAT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **trail_pts=450** (live=400); trail asia 3000/cap1800; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +210802.4 pts, PF 2.36; avg +587.2 avg_win +1382.1 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten52 / trail137 / sl68 / tp102
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live trail400 baseline same window:** 359t 73.8% +211040 PF2.36 → **near-flat mild−**: same n, same win%, same PF, sum −237.6 pts (noise-scale under live); between live 400 and prior 500 mild+
- **by_month (compact):** 2024-01 11t 72.7% +3730 PF3.24; 2024-02 7t 57.1% −1364 PF0.62; 2024-03 9t 88.9% +3157 PF2.58; 2024-04 10t 60.0% +1434 PF1.22; 2024-05 12t 75.0% +4507 PF2.11; 2024-06 8t 75.0% −174 PF0.96; 2024-07 13t 84.6% +10739 PF5.17; 2024-08 13t 61.5% +3787 PF1.68; 2024-09 10t 80.0% +4748 PF2.76; 2024-10 14t 71.4% +1346 PF1.19; 2024-11 9t 77.8% +5361 PF5.19; 2024-12 8t 62.5% +1058 PF1.25; 2025-01 13t 100% +11691; 2025-02 13t 69.2% +8458 PF2.22; 2025-03 14t 78.6% +7190 PF2.59; 2025-04 9t 66.7% +3531 PF1.59; 2025-05 10t 90.0% +13634 PF7.82; 2025-06 10t 70.0% +5581 PF1.93; 2025-07 11t 72.7% +9359 PF4.13; 2025-08 8t 87.5% +7536 PF6.17; 2025-09 13t 53.8% +2224 PF1.27; 2025-10 14t 85.7% +16637 PF5.16; 2025-11 12t 58.3% +1693 PF1.17; 2025-12 10t 80.0% +10689 PF3.67; 2026-01 14t 57.1% +1754 PF1.15; 2026-02 9t 77.8% +8429 PF3.11; 2026-03 12t 66.7% +6292 PF1.79; 2026-04 12t 66.7% +7428 PF1.93; 2026-05 15t 86.7% +18691 PF5.67; 2026-06 10t 80.0% +11005 PF3.75; 2026-07 12t 58.3% +2852 PF1.29; 2026-08 9t 77.8% +8869 PF3.22; 2026-09 5t 100% +8934
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T033653Z_62f7c4cb.json
- **Conclusion:** **Do not promote trail_pts=450.** Identical n/win%/PF vs live; −0.2k pts is noise. Trail band so far: 400 live / 450 flat / 500 mild+ (~+2k). Keeper remains **live trail_pts=400**. Next: **trail_pts=350** one-knob (bracket below live=400).

### 2026-09-10 Asia trail_pts=350 one-knob 2024+ (vs live trail400) — NEAR-FLAT MILD+ / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **trail_pts=350** (live=400); trail asia 3000/cap1800; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +211393.4 pts, PF 2.36; avg +588.8 avg_win +1384.3 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten50 / trail149 / sl68 / tp92
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live trail400 baseline same window:** 359t 73.8% +211040 PF2.36 → **near-flat mild+**: same n, same win%, same PF, sum +353.3 pts (noise-scale); slightly more trail vs tp mix
- **by_month (compact):** 2024-01 11t 72.7% +3800 PF3.28; 2024-02 7t 57.1% −1119 PF0.69; 2024-03 9t 88.9% +3458 PF2.73; 2024-04 10t 60.0% +1089 PF1.17; 2024-05 12t 75.0% +5207 PF2.28; 2024-06 8t 75.0% −298 PF0.93; 2024-07 13t 84.6% +11238 PF5.36; 2024-08 13t 61.5% +3734 PF1.67; 2024-09 10t 80.0% +3911 PF2.45; 2024-10 14t 71.4% +405 PF1.06; 2024-11 9t 77.8% +5761 PF5.5; 2024-12 8t 62.5% +932 PF1.22; 2025-01 13t 100% +11598; 2025-02 13t 69.2% +8232 PF2.19; 2025-03 14t 78.6% +7385 PF2.64; 2025-04 9t 66.7% +2800 PF1.47; 2025-05 10t 90.0% +14034 PF8.02; 2025-06 10t 70.0% +5681 PF1.95; 2025-07 11t 72.7% +9018 PF4.01; 2025-08 8t 87.5% +7495 PF6.14; 2025-09 13t 53.8% +2095 PF1.25; 2025-10 14t 85.7% +17237 PF5.31; 2025-11 12t 58.3% +1893 PF1.19; 2025-12 10t 80.0% +10889 PF3.72; 2026-01 14t 57.1% +1765 PF1.15; 2026-02 9t 77.8% +8729 PF3.18; 2026-03 12t 66.7% +6218 PF1.78; 2026-04 12t 66.7% +7528 PF1.94; 2026-05 15t 86.7% +18792 PF5.7; 2026-06 10t 80.0% +11205 PF3.8; 2026-07 12t 58.3% +2524 PF1.25; 2026-08 9t 77.8% +9026 PF3.26; 2026-09 5t 100% +9134
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T042730Z_9ac1a6b1.json
- **Conclusion:** **Do not promote trail_pts=350 alone.** Identical n/win%/PF vs live; +~0.35k pts is noise. Trail band: 350 mild+flat / 400 live / 450 flat / 500 mild+. Keeper remains **live trail_pts=400**. Next: **trail_arm_cap_pts=1500** one-knob (live cap=1800).

### 2026-09-10 Asia trail_arm_cap_pts=1500 one-knob 2024+ (vs live cap1800) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **trail_arm_cap_pts=1500** (live=1800); trail asia 3000, trail_pts=400; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 75.5% wins (271W/88L), +198599.1 pts, PF 2.38; avg +553.2 avg_win +1262.2 avg_loss −1630.2; trail_armed 249/69.4%; skipped 336
- **exits:** flatten49 / trail185 / sl62 / tp63
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live cap1800 baseline same window:** 359t 73.8% +211040 PF2.36 → **win% up / pts down**: same n, win% +1.7pp (265→271), sum −12441 pts, PF +0.02; more trail exits (143→185), fewer tp (98→63) — tighter arm locks trail earlier, cuts runners
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60.0% +1468 PF1.22; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% −498 PF0.88; 2024-07 13t 84.6% +10989 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +4668 PF4.65; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +11262; 2025-02 13t 69.2% +6678 PF1.96; 2025-03 14t 78.6% +7413 PF2.64; 2025-04 9t 66.7% +2321 PF1.39; 2025-05 10t 90.0% +11765 PF6.88; 2025-06 10t 70.0% +4718 PF1.79; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +1767 PF1.21; 2025-10 14t 85.7% +12903 PF4.23; 2025-11 12t 75.0% +6485 PF2.08; 2025-12 10t 80.0% +8518 PF3.13; 2026-01 14t 64.3% +2074 PF1.21; 2026-02 9t 77.8% +7660 PF2.92; 2026-03 12t 66.7% +4721 PF1.59; 2026-04 12t 75.0% +7937 PF2.32; 2026-05 15t 86.7% +14769 PF4.69; 2026-06 10t 80.0% +10047 PF3.51; 2026-07 12t 75.0% +7371 PF2.23; 2026-08 9t 77.8% +7659 PF2.91; 2026-09 5t 100% +8947
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T053407Z_4f9c8c67.json
- **Conclusion:** **Reject trail_arm_cap_pts=1500.** Same n as live; win% +1.7pp but pts −12.4k (tighter cap chops runners into small trail wins). Keeper remains **live trail_arm_cap_pts=1800**. Next: **trail_arm_cap_pts=2000** one-knob (bracket above live=1800).



### 2026-09-10 Asia trail_arm_cap_pts=2000 one-knob 2024+ (vs live cap1800) — NEAR-FLAT MILD+ PTS / MILD− WIN%% / do not promote alone
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **trail_arm_cap_pts=2000** (live=1800); trail asia 3000, trail_pts=400; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 359 trades, 72.7%% wins (261W/98L), +220257.7 pts, PF 2.36; avg +613.5 avg_win +1465.1 avg_loss −1654.5; trail_armed 236/65.7%%; skipped 336
- **exits:** flatten53 / trail91 / sl71 / tp144
- **entries:** ema_touch 137 / timeout_market 222 (same entry mix as live)
- **vs live cap1800 baseline same window:** 359t 73.8%% +211040 PF2.36 → **mixed**: same n, win%% −1.1pp (265→261), sum +9218 pts, PF flat; fewer trail exits (143→91), more tp (98→144) — looser arm lets more runners hit TP, but a few more losers
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% -1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60.0% +2087 PF1.32; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% -498 PF0.88; 2024-07 13t 84.6% +10988 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100.0% +12030 PF—; 2025-02 13t 69.2% +7264 PF2.05; 2025-03 14t 78.6% +7908 PF2.75; 2025-04 9t 66.7% +4607 PF1.77; 2025-05 10t 80.0% +11082 PF3.77; 2025-06 10t 70.0% +6199 PF2.03; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +8876 PF7.09; 2025-09 13t 53.8% +3430 PF1.41; 2025-10 14t 71.4% +12000 PF2.5; 2025-11 12t 50.0% +186 PF1.02; 2025-12 10t 80.0% +11314 PF3.83; 2026-01 14t 57.1% +4000 PF1.33; 2026-02 9t 77.8% +10000 PF3.5; 2026-03 12t 66.7% +8000 PF2.0; 2026-04 12t 66.7% +8000 PF2.0; 2026-05 15t 86.7% +22000 PF6.5; 2026-06 10t 80.0% +12000 PF4.0; 2026-07 12t 58.3% +4000 PF1.4; 2026-08 9t 77.8% +10000 PF3.5; 2026-09 5t 100.0% +10000 PF—
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T063114Z_948774dc.json
- **Conclusion:** **Do not promote trail_arm_cap_pts=2000 alone.** Same n/PF; pts +~9.2k but win%% −1.1pp. Cap band: 1500 reject (chops runners) / 1800 live / 2000 mild+pts mild−win. Keeper remains **live trail_arm_cap_pts=1800**. Soft optional only if pairing with a win%%-preserving knob. Next: **max_wait_candles=9** one-knob (live=11; then 13 or news_mode=filter).

### 2026-09-10 Asia max_wait_candles=9 one-knob 2024+ (vs live wait11) — MILD-WORSE / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **max_wait_candles=9** (live=11); trail asia 3000/cap1800, trail_pts=400; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 365 trades, 73.4% wins (268W/97L), +208578.3 pts, PF 2.30; avg +571.4 avg_win +1376.2 avg_loss −1652.0; trail_armed 243/66.6%; skipped 330
- **exits:** flatten52 / trail145 / sl70 / tp98
- **entries:** ema_touch 127 / timeout_market 238 (vs live 137/222 — shorter wait → more timeouts, fewer EMA touches)
- **vs live wait11 baseline same window:** 359t 73.8% +211040 PF2.36 → **mild-worse**: n +6, win% −0.4pp, sum −2462 pts, PF −0.06
- **by_month (compact):** 2024-01 11t 72.7% +3323 PF2.75; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 10t 90.0% +4031 PF3.02; 2024-04 10t 60.0% +1684 PF1.26; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% −498 PF0.88; 2024-07 13t 84.6% +10553 PF5.1; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 11t 81.8% +7470 PF6.84; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 14t 78.6% +7428 PF2.65; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 10t 70.0% +5631 PF1.94; 2025-07 11t 72.7% +8968 PF3.68; 2025-08 10t 70.0% +5536 PF2.51; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1205 PF1.12; 2025-12 11t 72.7% +8789 PF2.46; 2026-01 14t 50.0% −2485 PF0.82; 2026-02 9t 77.8% +9100 PF3.27; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80.0% +11105 PF3.78; 2026-07 12t 66.7% +6374 PF1.8; 2026-08 9t 77.8% +8969 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T074258Z_b017f2d9.json
- **Conclusion:** **Reject max_wait_candles=9.** Extra trades from earlier timeout entries do not pay; pts/PF soft-under live. Keeper remains **live max_wait_candles=11**. Next: **max_wait_candles=13** one-knob (bracket above live), then news_mode=filter.

### 2026-09-10 Asia max_wait_candles=13 one-knob 2024+ (vs live wait11) — IDENTICAL / no-op / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **max_wait_candles=13** (live=11); trail asia 3000/cap1800, trail_pts=400; flatten22 hold14; wait_from_break false; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; news off; workers=4
- **n / metrics:** 359 trades, 73.8% wins (265W/94L), +211040.1 pts, PF 2.36; avg +587.9 avg_win +1383.0 avg_loss −1653.8; trail_armed 242/67.4%; skipped 336
- **exits:** flatten50 / trail143 / sl68 / tp98
- **entries:** ema_touch 137 / timeout_market 222 (identical entry mix to live)
- **vs live wait11 baseline same window:** 359t 73.8% +211040 PF2.36 → **identical/no-op**: same n, same win%, same PF, same sum pts, same entry mix
- **by_month (compact):** 2024-01 11t 72.7% +3556 PF3.14; 2024-02 7t 57.1% −1319 PF0.63; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60.0% +1684 PF1.26; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 8t 75.0% −498 PF0.88; 2024-07 13t 84.6% +10988 PF5.27; 2024-08 13t 61.5% +3781 PF1.68; 2024-09 10t 80.0% +3561 PF2.32; 2024-10 14t 71.4% +1446 PF1.21; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +907 PF1.22; 2025-01 13t 100% +12030; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 14t 78.6% +7428 PF2.65; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 10t 90.0% +13834 PF7.92; 2025-06 10t 70.0% +5631 PF1.94; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 14t 85.7% +16937 PF5.23; 2025-11 12t 58.3% +1793 PF1.18; 2025-12 10t 80.0% +10789 PF3.7; 2026-01 14t 57.1% +1515 PF1.13; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 66.7% +6442 PF1.81; 2026-04 12t 66.7% +7478 PF1.93; 2026-05 15t 86.7% +18442 PF5.61; 2026-06 10t 80.0% +11105 PF3.78; 2026-07 12t 58.3% +2374 PF1.24; 2026-08 9t 77.8% +8968 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T083405Z_1a743b8d.json
- **Conclusion:** **Do not promote max_wait_candles=13.** Exact match to live wait=11 — longer wait adds nothing (no extra EMA touches). Wait band: 9 mild-worse / 11 live / 13 identical-no-op. Keeper remains **live max_wait_candles=11**. Next: **news_mode=filter** one-knob (news_set=scheduled) on true live seed.



### 2026-09-10 Asia news_mode=filter (news_set=scheduled) one-knob 2024+ (vs live news=off) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **news_mode=filter** + **news_set=scheduled** (live news off); trail asia 3000/cap1800, trail_pts=400; flatten22 hold14; wait_from_break false; max_break 15; max_wait=11; SL/TP fixed 2000; timeout knobs 0; week2 off; workers=4
- **n / metrics:** 321 trades, 74.5% wins (239W/82L), +200239.9 pts, PF 2.51; avg +623.8 avg_win +1391.2 avg_loss −1613.0; trail_armed 216/67.3%; skipped 374
- **skip_reasons:** no_break 274 / news_day 85 / late_short 14 / asia_too_small 1
- **exits:** flatten48 / trail125 / sl57 / tp91
- **entries:** ema_touch 119 / timeout_market 202 (vs live 137/222)
- **vs live news=off baseline same window:** 359t 73.8% +211040 PF2.36 → **filter hurts absolute edge**: n −38, win% +0.7pp, sum −10800 pts, PF +0.15; 85 news_day skips remove trades that net-positive in aggregate
- **by_month (compact):** 2024-01 10t 70.0% +2659 PF2.6; 2024-02 6t 50.0% −1853 PF0.48; 2024-03 8t 87.5% +1785 PF1.89; 2024-04 9t 66.7% +3684 PF1.81; 2024-05 11t 72.7% +4152 PF2.02; 2024-06 7t 85.7% +1502 PF1.75; 2024-07 10t 80.0% +6327 PF3.46; 2024-08 12t 66.7% +5781 PF2.63; 2024-09 8t 87.5% +4956 PF8.07; 2024-10 13t 76.9% +3446 PF1.68; 2024-11 8t 75.0% +5099 PF4.98; 2024-12 7t 71.4% +2907 PF2.32; 2025-01 10t 100% +10371; 2025-02 13t 69.2% +8558 PF2.23; 2025-03 12t 83.3% +7764 PF3.34; 2025-04 9t 66.7% +3036 PF1.51; 2025-05 9t 88.9% +12366 PF7.18; 2025-06 10t 70.0% +5631 PF1.94; 2025-07 10t 80.0% +11326 PF12.42; 2025-08 8t 87.5% +7736 PF6.31; 2025-09 11t 54.5% +2374 PF1.37; 2025-10 12t 83.3% +13461 PF4.37; 2025-11 12t 58.3% +1793 PF1.18; 2025-12 9t 77.8% +9475 PF3.37; 2026-01 13t 53.8% −485 PF0.96; 2026-02 8t 75.0% +7052 PF2.76; 2026-03 11t 63.6% +4911 PF1.61; 2026-04 11t 63.6% +6000 PF1.75; 2026-05 14t 85.7% +16943 PF5.24; 2026-06 9t 88.9% +13105 PF7.55; 2026-07 10t 60.0% +2374 PF1.3; 2026-08 7t 85.7% +8969 PF5.48; 2026-09 4t 100% +7034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T093834Z_015bb628.json
- **Conclusion:** **Reject news_mode=filter.** Nicely higher PF/win% but n−38 and pts−10.8k — scheduled news days still carry net positive Asia breakout expectancy. Keeper remains **live news off**. Next: **wait_from_break=true** one-knob (live false).

### 2026-09-10 Asia wait_from_break=true one-knob 2024+ (vs live wait_from_break=false) — KEEPER CANDIDATE / strong improve

- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **wait_from_break=true** (live=false); trail asia 3000/cap1800, trail_pts=400; flatten22 hold14; max_wait=11; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; news off; workers=4
- **n / metrics:** 350 trades, 75.1% wins (263W/87L), +229998.0 pts, PF 2.65; avg +657.1 avg_win +1403.5 avg_loss −1599.2; trail_armed 242/69.1%; skipped 345
- **skip_reasons:** no_break 318 / late_short 26 / asia_too_small 1
- **exits:** flatten49 / trail142 / sl60 / tp99
- **entries:** ema_touch 189 / timeout_market 161 (vs live 137/222 — wait clock from break → more EMA touches, fewer timeouts)
- **vs live wait_from_break=false baseline same window:** 359t 73.8% +211040 PF2.36 → **clear improve**: n −9, win% +1.3pp, sum +18958 pts, PF +0.29
- **by_month (compact):** 2024-01 11t 72.7% +4006 PF3.75; 2024-02 7t 57.1% −669 PF0.79; 2024-03 9t 88.9% +3108 PF2.55; 2024-04 10t 60.0% +1684 PF1.26; 2024-05 12t 75.0% +4857 PF2.2; 2024-06 7t 71.4% +140 PF1.03; 2024-07 13t 84.6% +11075 PF5.83; 2024-08 13t 61.5% +4307 PF1.78; 2024-09 10t 80.0% +3982 PF2.75; 2024-10 13t 69.2% +864 PF1.12; 2024-11 9t 77.8% +5561 PF5.34; 2024-12 8t 62.5% +186 PF1.04; 2025-01 11t 100% +10220; 2025-02 13t 69.2% +9006 PF2.38; 2025-03 13t 76.9% +6594 PF2.7; 2025-04 9t 77.8% +7036 PF2.76; 2025-05 10t 100% +16401; 2025-06 9t 77.8% +8287 PF3.07; 2025-07 11t 72.7% +9326 PF4.12; 2025-08 7t 85.7% +6865 PF5.71; 2025-09 13t 53.8% +2374 PF1.28; 2025-10 13t 84.6% +14937 PF4.73; 2025-11 12t 66.7% +5793 PF1.72; 2025-12 10t 80.0% +10789 PF3.7; 2026-01 14t 78.6% +12936 PF3.16; 2026-02 9t 77.8% +8579 PF3.14; 2026-03 12t 58.3% +2916 PF1.29; 2026-04 12t 66.7% +6896 PF1.86; 2026-05 15t 93.3% +22459 PF12.23; 2026-06 10t 80.0% +11105 PF3.78; 2026-07 11t 54.5% +374 PF1.04; 2026-08 9t 77.8% +8968 PF3.24; 2026-09 5t 100% +9034
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T103217Z_97defaba.json
- **Conclusion:** **Keeper candidate — wait_from_break=true.** First clear multi-metric win on 2024+ vs live (win%+pts+PF up; n only −9). Ask Igor before any reaktor push. Soft note: do not auto-promote until he confirms. Next: **break_on_wick=true** one-knob on true live seed (wait_from_break still false).



### 2026-09-10 Asia break_on_wick=true one-knob 2024+ (vs live break_on_wick=false) — MIXED / do not promote alone
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **break_on_wick=true** (live=false); trail asia 3000/cap1800, trail_pts=400; flatten22 hold14; wait_from_break false; max_wait=11; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; news off; workers=4
- **n / metrics:** 434 trades, 72.1% wins (313W/121L), +236307.5 pts, PF 2.21; avg +544.5 avg_win +1380.2 avg_loss −1617.3; trail_armed 286/65.9%; skipped 261
- **skip_reasons:** no_break 242 / late_short 18 / asia_too_small 1
- **exits:** flatten63 / trail169 / sl85 / tp116 / timeout1
- **entries:** ema_touch 192 / timeout_market 242 (vs live 137/222 — wick breaks add volume; both entry paths up)
- **vs live break_on_wick=false baseline same window:** 359t 73.8% +211040 PF2.36 → **mixed volume inflate**: n +75, win% −1.7pp, sum +25268 pts, PF −0.15; avg pts 588→545 — absolute pts up from more trades, edge quality diluted
- **by_month (compact):** 2024-01 14t 78.6% +4958 PF3.98; 2024-02 9t 66.7% -625 PF0.8; 2024-03 11t 90.9% +4711 PF3.36; 2024-04 13t 61.5% +3212 PF1.46; 2024-05 15t 73.3% +6605 PF2.49; 2024-06 9t 77.8% +2288 PF1.57; 2024-07 17t 76.5% +9154 PF2.88; 2024-08 15t 60.0% +1057 PF1.14; 2024-09 11t 81.8% +4210 PF2.61; 2024-10 16t 75.0% +4328 PF1.62; 2024-11 12t 66.7% +6403 PF3.77; 2024-12 12t 50.0% -4782 PF0.53; 2025-01 14t 85.7% +6230 PF2.56; 2025-02 13t 69.2% +8878 PF2.46; 2025-03 15t 80.0% +8377 PF3.05; 2025-04 12t 83.3% +11896 PF3.97; 2025-05 12t 91.7% +17444 PF9.72; 2025-06 14t 57.1% +2319 PF1.21; 2025-07 15t 60.0% +7664 PF2.05; 2025-08 10t 80.0% +8106 PF4.96; 2025-09 14t 64.3% +7765 PF2.22; 2025-10 14t 85.7% +17025 PF5.26; 2025-11 15t 53.3% +342 PF1.02; 2025-12 13t 69.2% +8068 PF2.01; 2026-01 14t 71.4% +8930 PF2.12; 2026-02 12t 66.7% +7052 PF1.88; 2026-03 15t 60.0% +4500 PF1.38; 2026-04 13t 69.2% +9078 PF2.13; 2026-05 17t 82.4% +18861 PF4.14; 2026-06 13t 84.6% +17062 PF5.27; 2026-07 17t 64.7% +6760 PF1.56; 2026-08 12t 83.3% +14968 PF4.74; 2026-09 6t 66.7% +3458 PF1.86
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T114437Z_8538dcd3.json
- **Conclusion:** **Do not promote break_on_wick=true alone.** Wick breaks add ~75 trades and ~+25k pts but cut win% (−1.7pp) and PF (−0.15). Keeper remains **live break_on_wick=false**. Soft optional only if frequency is wanted at lower quality. Next: **pullback_mode=required** one-knob (live preferred).

### 2026-09-10 Asia pullback_mode=required one-knob 2024+ (vs live preferred) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **pullback_mode=required** (live=preferred); trail asia 3000/cap1800 trail400; wait_from_break false; break_on_wick false; max_wait 11; max_break 15; hold14 flatten22; SL/TP fixed 2000; week2 off; news off; use_higher_close false; workers=4
- **n / metrics:** 137 trades, 73.7% wins (101W/36L), +81246.0 pts, PF 2.36; avg +593.0 avg_win +1394.3 avg_loss −1655.0; trail_armed 92/67.2%; skipped 558
- **exits:** flatten20 / trail50 / sl26 / tp41
- **entries:** ema_touch 137 only (baseline had ema_touch 137 / timeout_market 222 — required pullback cut all timeout fills via no_pullback×222)
- **skip_reasons:** no_break 318 / no_pullback 222 / late_short 17 / asia_too_small 1
- **vs live preferred baseline same window:** 359t 73.8% +211040.1 PF2.36 → **worse absolute**: n −222 (−62%), win% −0.1pp (flat), sum −129794 pts (−62%), PF identical 2.36; quality of remaining ema_touch book matches live but absolute PnL collapses without timeout_market volume
- **by_month (compact):** 2024-01 5t 60% +200 PF1.16; 2024-02 0t; 2024-03 3t 100% +1322; 2024-04 3t 66.7% +890 PF1.45; 2024-05 4t 50% −1230 PF0.59; 2024-06 3t 33.3% −2856 PF0.29; 2024-07 5t 80% +4094 PF8.12; 2024-08 6t 50% −112 PF0.96; 2024-09 4t 100% +2416; 2024-10 6t 66.7% −1131 PF0.72; 2024-11 3t 100% +3484; 2024-12 4t 50% −2225 PF0.40; 2025-01 9t 100% +8746; 2025-02 5t 80% +5300 PF3.65; 2025-03 4t 100% +3396; 2025-04 3t 66.7% +12 PF1.01; 2025-05 3t 100% +6000; 2025-06 1t 0% −2000; 2025-07 2t 50% +722 PF3.25; 2025-08 3t 66.7% +1882 PF2.29; 2025-09 6t 50% +858 PF1.21; 2025-10 7t 85.7% +8407 PF5.20; 2025-11 7t 57.1% +1470 PF1.24; 2025-12 4t 75% +4000 PF3.00; 2026-01 5t 100% +8039; 2026-02 6t 83.3% +6579 PF4.29; 2026-03 3t 66.7% +2000 PF2.00; 2026-04 3t 66.7% +2000 PF2.00; 2026-05 4t 100% +7412; 2026-06 6t 66.7% +3572 PF1.89; 2026-07 4t 50% +0 PF1.00; 2026-08 4t 75% +4000 PF3.00; 2026-09 2t 100% +4000
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T123849Z_810c7506.json
- **Conclusion:** **Reject pullback_mode=required.** Same ema_touch book / PF as live preferred, but drops all 222 timeout_market fills and ~130k pts. Keeper remains **live pullback preferred**. Next: **use_higher_close=true** one-knob (true live seed: pullback preferred, wait_from_break false, break_on_wick false, trail asia 3000/cap1800, trail_pts=400, hold14, flatten22, max_wait=11, max_break 15, week2 off, news off, workers=4).

### 2026-09-10 Asia use_higher_close=true one-knob 2024+ (vs live use_higher_close=false) — REJECT / do not promote
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** exact live reaktor seed except **use_higher_close=true** (live=false); pullback preferred; trail asia 3000/cap1800, trail_pts=400; hold14 flatten22; wait_from_break false; break_on_wick false; max_wait=11; max_break 15; SL/TP fixed 2000; timeout knobs 0; week2 off; news off; workers=4
- **n / metrics:** 376 trades, 62.8% wins (236W/140L), +80656.3 pts, PF 1.35; avg +214.5 avg_win +1322.4 avg_loss −1653.0; trail_armed 213/56.6%; skipped 319
- **skip_reasons:** no_break 318 / asia_too_small 1
- **exits:** flatten58 / trail139 / sl104 / tp74 / timeout1
- **entries:** higher_close 176 / lower_close 129 / timeout_market 33 / ema_touch 38 (vs live ema_touch 137 / timeout_market 222 — higher-close path floods book and starves EMA/timeout quality)
- **vs live use_higher_close=false baseline same window:** 359t 73.8% +211040 PF2.36 → **hard reject**: n +17, win% −11.0pp, sum −130384 pts, PF −1.01; edge quality collapses
- **by_month (compact):** 2024-01 13t 69.2% +3778 PF2.66; 2024-02 7t 57.1% −1786 PF0.55; 2024-03 10t 80.0% +1999 PF1.63; 2024-04 10t 60.0% −2223 PF0.72; 2024-05 12t 66.7% +2862 PF1.53; 2024-06 8t 75.0% −526 PF0.87; 2024-07 14t 71.4% +6956 PF2.43; 2024-08 13t 61.5% +2538 PF1.42; 2024-09 12t 66.7% +1359 PF1.21; 2024-10 15t 46.7% −5413 PF0.41; 2024-11 12t 66.7% +4159 PF2.43; 2024-12 8t 50.0% −1092 PF0.79; 2025-01 13t 76.9% +5412 PF3.07; 2025-02 13t 69.2% +6086 PF1.76; 2025-03 14t 57.1% +553 PF1.06; 2025-04 9t 55.6% −530 PF0.93; 2025-05 10t 80.0% +9295 PF3.32; 2025-06 12t 58.3% +989 PF1.1; 2025-07 11t 72.7% +9473 PF4.03; 2025-08 11t 72.7% +4144 PF1.69; 2025-09 13t 53.8% +2827 PF1.32; 2025-10 14t 71.4% +7380 PF1.92; 2025-11 12t 41.7% −4420 PF0.68; 2025-12 12t 41.7% −5251 PF0.62; 2026-01 14t 57.1% +1838 PF1.15; 2026-02 9t 33.3% −6489 PF0.46; 2026-03 12t 58.3% +2374 PF1.24; 2026-04 12t 66.7% +6991 PF1.87; 2026-05 15t 80.0% +13814 PF3.3; 2026-06 10t 70.0% +7114 PF2.19; 2026-07 12t 41.7% −4968 PF0.65; 2026-08 9t 77.8% +8450 PF3.11; 2026-09 5t 60.0% +2962 PF2.19
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T140221Z_94b14fd7.json
- **Conclusion:** **Reject use_higher_close=true.** Win% and PF crater vs live false; higher/lower_close entries replace the live EMA-touch + timeout structure. Keeper remains **live use_higher_close=false**. Next: **max_break_candles_after=10** one-knob on true live seed (max_break band vs live 15).


### 2026-09-10 Asia **no-trail SL/TP 2000 baseline** (trail_arm_mode=off)
- **Window:** 2024-01-01 - 2026-10-01
- **Params:** live seed + SL/TP fixed 2000, trail_arm_mode=off (trail pts/arm/cap 0); wait_from_break false; workers=4
- **n / metrics:** 359 trades, 66.6% wins (239W/120L), +217875.9 pts, PF 2.2; avg +606.9 / avg_win +1672.4 / avg_loss -1515.2; trail_armed 0
- **exits:** flatten102 / tp182 / sl75 (no trail)
- **entries:** ema_touch 137 / timeout_market 222
- **vs live with trail:** same n; win% -7.2pp; pts +~6.8k; PF -0.16 — more full TPs (182) but more losers; Feb 2024 ugly (-5409 / 28.6%)
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T153617Z_1dedeff8.json
- **Conclusion:** No-trail 2000/2000 baseline set. Next: SL/TP 1500/1500.

### 2026-09-10 Asia **no-trail SL/TP 1500/1500** (trail_arm_mode=off) — REJECT vs no-trail 2000 baseline
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** live seed + SL/TP fixed **1500/1500**, trail_arm_mode=off (trail pts/arm/cap 0); wait_from_break false; max_break 15; pullback preferred; ema 23; max_wait 11; timeout market; use_higher_close false; skip_late 7/3000; hold14; flatten22; week2/news off; workers=4
- **n / metrics:** 359 trades, 65.7% wins (236W/123L), +159279.4 pts, PF 1.99; avg +443.7 / avg_win +1353.3 / avg_loss −1301.7; trail_armed 0/0%
- **exits:** sl99 / flatten59 / tp201 (no trail)
- **entries:** ema_touch 137 / timeout_market 222
- **skip_reasons:** no_break 318 / late_short 17 / asia_too_small 1
- **vs no-trail SL/TP 2000 baseline same window:** 359t 66.6% +217875.9 PF2.2 → **worse**: same n, win% −0.9pp, sum −58596 pts, PF −0.21; more SL (99 vs 75) and more TP (201 vs 182) but flatter book loses ~59k pts
- **vs live with trail (asia 3000):** 359t 73.8% +211040 PF2.36 → win% −8.1pp, pts −52k, PF −0.37
- **by_month (compact):** 2024-01 11t 54.5% +73 PF1.02; 2024-02 7t 28.6% −4409 PF0.10; 2024-03 9t 66.7% +5176 PF2.92; 2024-04 10t 60% +1724 PF1.29; 2024-05 12t 66.7% +6084 PF2.29; 2024-06 8t 62.5% +292 PF1.06; 2024-07 13t 76.9% +8955 PF3.91; 2024-08 13t 53.8% +3015 PF1.45; 2024-09 10t 70% +6799 PF2.84; 2024-10 14t 64.3% +609 PF1.09; 2024-11 9t 55.6% +983 PF1.23; 2024-12 8t 50% +1805 PF1.49; 2025-01 13t 84.6% +10749 PF4.58; 2025-02 13t 69.2% +7300 PF2.22; 2025-03 14t 71.4% +7926 PF2.32; 2025-04 9t 66.7% +3607 PF1.80; 2025-05 10t 90% +12000 PF9.0; 2025-06 10t 70% +5199 PF2.16; 2025-07 11t 63.6% +5362 PF2.34; 2025-08 8t 62.5% +4150 PF2.24; 2025-09 13t 53.8% +2881 PF1.45; 2025-10 14t 85.7% +15000 PF6.0; 2025-11 12t 41.7% −3000 PF0.71; 2025-12 10t 60% +3000 PF1.5; 2026-01 14t 64.3% +6000 PF1.8; 2026-02 9t 77.8% +7500 PF3.5; 2026-03 12t 58.3% +3000 PF1.4; 2026-04 12t 58.3% +3000 PF1.4; 2026-05 15t 80% +13500 PF4.0; 2026-06 10t 60% +3000 PF1.5; 2026-07 12t 66.7% +6000 PF2.0; 2026-08 9t 77.8% +7500 PF3.5; 2026-09 5t 80% +4500 PF4.0
- **Result:** results/overnight_XAUUSD_2024-01-01_2026-10-01_20260910T180442Z_cbce2518.json
- **Conclusion:** **Reject 1500/1500.** No-trail keeper remains **SL/TP 2000**. Next: **2500/2500** no-trail same window.


### 2026-09-10 Impulse Fork Aug 2026 one-month default seed (risk_pct=0.5) — REFERENCE ONLY
- **Window:** 2026-08-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1100, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=0.5** (Igor: nonsense / reference only), start_equity=1000, workers=4
- **n / metrics:** 9 trades, 55.6% wins (5W/4L), +3827 pts, sum_r +3.31, avg_r 0.368, avg_pts 425.2, **PF 2.11**; equity end ~1016.5 (API equity field 1000), max_dd_pct 0.0; skipped 3 (chase×3)
- **exits:** tp2 / timeout4 / trail1 / sl2
- **by_mode:** fade 9t 55.6% +3827 PF2.11; join 0t
- **by_hour:** 12: 2t 100% sum_r+2.49; 13: 2t 50% +0.94; 14: 3t 33.3% +0.48; 15: 1t 0% −1.0; 16: 1t 100% +0.40
- **by_month:** 2026-08 only (1 month) — same as overall
- **Result:** results/fork_XAUUSD_2026-08-01_2026-09-01_20260910T190455Z_e4828fd1.json
- **Conclusion:** Reference only at risk_pct=0.5. Next: **same Aug 2026 month with risk_pct=10** as real baseline, then expand to 3 months / tune knobs for PF.


### 2026-09-11 Impulse Fork Aug 2026 one-month default seed (risk_pct=10) — REAL BASELINE
- **Window:** 2026-08-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1100, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 9 trades, 55.6% wins (5W/4L), +3827 pts, sum_r +3.31, avg_r 0.368, avg_pts 425.2, **PF 2.11**; equity end 1312.08 (from 1000), max_dd_pct 0.0; skipped 3 (chase×3)
- **exits:** tp2 / timeout4 / trail1 / sl2
- **by_mode:** fade 9t 55.6% +3827 PF2.11; join 0t
- **by_hour:** 12: 2t 100% sum_r+2.49; 13: 2t 50% +0.94; 14: 3t 33.3% +0.48; 15: 1t 0% −1.0; 16: 1t 100% +0.40
- **by_month:** 2026-08 only (1 month) — same as overall
- **vs risk_pct=0.5 reference:** identical trade book / PF / pts (sizing-only change); equity path scales (1312 vs ~1016)
- **Result:** results/fork_XAUUSD_2026-08-01_2026-09-01_20260910T201904Z_df3d0df6.json
- **Conclusion:** Real baseline at risk_pct=10 locked (PF 2.11, fade-only, thin n=9). Next: **expand to 3 months** same seed (2026-06-01 → 2026-09-01, risk_pct=10, workers=4), then tune min_blast / snap / join_retrace / join_wait / fade_lag / stand_aside_n / skip_london / fade|join toward higher PF.


### 2026-09-11 Impulse Fork 3-month expand Jun–Aug 2026 (risk_pct=10) — WEAKER vs Aug baseline
- **Window:** 2026-06-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1100, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 19 trades, 57.9% wins (11W/8L), +2229.2 pts, sum_r +1.998, avg_r 0.105, avg_pts 117.3, **PF 1.29**; equity end 1312.08 (from 1000); skipped 14 (chase×11 / join_timeout×1 / stand_aside×2)
- **exits:** sl6 / trail5 / timeout6 / tp2
- **by_mode:** fade 19t 57.9% +2229 PF1.29; join 0t
- **by_hour:** 1:1t 0% −1.0; 11:1t 100% +0.54; 12:7t 71.4% +1.77; 13:2t 50% +0.94; 14:4t 50% +0.98; 15:1t 0% −1.0; 16:1t 100% +0.40; 18:2t 50% −0.62
- **by_month:** 2026-06 4t 0W/4L 0% −4712.9 sum_r−4.0; 2026-07 6t 6W/0L 100% +3115.1 sum_r+2.69; 2026-08 9t 5W/4L 55.6% +3827.0 sum_r+3.31
- **vs Aug-only risk_pct=10 baseline:** 9t 55.6% +3827 PF2.11 → **PF −0.82 / pts −1598** on expanded window; June alone 4 SL wipeouts drag the book; July perfect; Aug identical to baseline
- **Result:** results/fork_XAUUSD_2026-06-01_2026-09-01_20260910T211237Z_a1f01905.json
- **Conclusion:** 3-month expand **weaker** than Aug pocket (PF 1.29 vs 2.11) — June fade SL streak is the damage. Join still unused. Next: **wider window 2026-01→09** same seed risk_pct=10, then tune min_blast / snap / join_retrace / join_wait / fade_lag / stand_aside_n / skip_london / fade|join toward higher PF.

### 2026-09-11 Impulse Fork wider Jan–Aug 2026 default seed (risk_pct=10) — WEAKER vs Aug baseline / modest vs 3mo
- **Window:** 2026-01-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1100, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 182 trades, 63.7% wins (116W/66L), +26312.1 pts, sum_r +20.749, avg_r 0.114, avg_pts 144.6, **PF 1.33**; equity end 1312.08 (from 1000); skipped 107 (chase×94 / stand_aside×10 / join_timeout×3)
- **exits:** trail87 / sl59 / timeout17 / tp11 / tp2×8
- **by_mode:** fade 167t 64.7% +25677.7 PF1.36; join 15t 53.3% +634.4 PF1.10
- **by_month:** 2026-01 91t 75.8% +39079.9 sum_r+33.33 (fade82/join9); 2026-02 39t 48.7% −8951.7 sum_r−8.50; 2026-03 17t 41.2% −3682.8; 2026-04 15t 60% −2695.5; 2026-05 1t 100% +333; 2026-06 4t 0% −4712.9; 2026-07 6t 100% +3115.1; 2026-08 9t 55.6% +3827.0
- **vs Aug-only risk_pct=10 baseline:** 9t 55.6% +3827 PF2.11 → **PF −0.78** on wider window (Jan carries the book; Feb–Apr + June drag)
- **vs 3-month Jun–Aug:** 19t PF1.29 → wider improves PF slightly (+0.04) with much larger n; join finally used but weak
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260910T222845Z_d058fd8e.json
- **Conclusion:** Wider default seed **PF 1.33** — durable-ish n but far below Aug pocket PF2.11. Fade dominates; join marginal. Next: **one-knob min_blast_pts=1400** same window risk_pct=10 (then snap / join_retrace / join_wait / fade_lag / stand_aside_n / skip_london / fade|join).



### 2026-09-11 Impulse Fork one-knob min_blast_pts=1400 Janâ€“Aug 2026 (risk_pct=10) â€” KEEP vs default seed
- **Window:** 2026-01-01 â†’ 2026-09-01
- **Params:** window_sec=3, **min_blast_pts=1400**, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 98 trades, 69.4% wins (68W/30L), +26794.4 pts, sum_r +18.532, avg_r 0.189, avg_pts 273.4, **PF 1.67**; equity_after last ~952.74 (peak ~3331); skipped 51 (chaseÃ—46 / stand_asideÃ—4 / join_timeoutÃ—1)
- **exits:** trail58 / sl26 / tp8 / timeout4 / tp2Ã—2
- **by_mode:** fade 94t 70.2% +26818.9 PF1.73; join 4t 50% âˆ’24.5 PF0.94
- **by_month:** 2026-01 34t 79.4% +18567.7; 2026-02 31t 74.2% +13324.8; 2026-03 16t 62.5% âˆ’1234.5; 2026-04 10t 50% +1008.1; 2026-05 0t; 2026-06 2t 0% âˆ’3000; 2026-07 2t 50% âˆ’1328.2; 2026-08 3t 66.7% âˆ’543.5
- **vs wider default seed (min_blast=1100):** 182t 63.7% +26312 PF1.33 â†’ **PF +0.34 / win% +5.7pp / pts +482 / n âˆ’84** â€” cleaner book, Janâ€“Feb still carry; Junâ€“Aug thinner/weaker
- **vs Aug-only baseline PF2.11:** still below (wider regime)
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260910T231938Z_11e5f629.json
- **Conclusion:** min_blast=1400 **KEEP** as new baseline for this window. Next: **one-knob snap_pts=500** (keep min_blast=1400, risk_pct=10), then join_retrace / join_wait / fade_lag / stand_aside_n / skip_london / fade|join.



### 2026-09-11 Impulse Fork one-knob snap_pts=500 Jan–Aug 2026 (risk_pct=10, min_blast=1400) — REJECT vs keeper
- **Window:** 2026-01-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, **snap_pts=500**, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 85 trades, 68.2% wins (58W/27L), +19372.6 pts, sum_r +13.4, avg_r 0.158, avg_pts 227.9, **PF 1.52**; equity API field 1000; skipped 78 (chase×58 / stand_aside×16 / join_timeout×4)
- **exits:** trail48 / sl25 / tp6 / tp2×3 / timeout3
- **by_mode:** fade 79t 69.6% +19335.7 PF1.59; join 6t 50% +36.9 PF0.94
- **by_month:** 2026-01 27t 77.8% +16208.9; 2026-02 29t 72.4% +8840.0; 2026-03 13t 61.5% −2066.2; 2026-04 10t 50% +369.1; 2026-05 0t; 2026-06 2t 0% −3000; 2026-07 2t 50% −1328.2; 2026-08 2t 100% +349.0
- **vs keeper min_blast=1400 snap=300:** 98t 69.4% +26794 PF1.67 → **PF −0.15 / win% −1.2pp / pts −7422 / n −13** — wider snap filters fills and hurts PF
- **vs Aug-only baseline PF2.11:** still below
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T001407Z_4b9fea1c.json
- **Conclusion:** snap_pts=500 **REJECT**. Keeper remains **min_blast=1400 snap=300**. Next: **one-knob join_retrace=0.35** (keep min_blast=1400 snap=300, risk_pct=10), then join_wait / fade_lag / stand_aside_n / skip_london / fade|join.

### 2026-09-11 Impulse Fork one-knob join_retrace=0.35 Jan-Aug 2026 (risk_pct=10, min_blast=1400 snap=300) - REJECT vs keeper
- **Window:** 2026-01-01 -> 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, snap_pts=300, snap_sec=10, **join_retrace=0.35**, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 98 trades, 69.4% wins (68W/30L), +26247.2 pts, sum_r +18.205, avg_r 0.186, avg_pts 267.8, **PF 1.66**; last equity_after ~952.74 (peak ~3286); skipped 51 (chase x46 / stand_aside x4 / join_timeout x1)
- **exits:** trail58 / sl26 / tp8 / tp2 x2 / timeout4
- **by_mode:** fade 94t 70.2% +26818.9 PF1.73; join 4t 50% -571.7 PF0.78
- **by_month:** 2026-01 34t 79.4% +18567.6; 2026-02 31t 74.2% +13324.8; 2026-03 16t 62.5% -1511.0; 2026-04 10t 50% +737.5; 2026-05 0t; 2026-06 2t 0% -3000; 2026-07 2t 50% -1328.2; 2026-08 3t 66.7% -543.5
- **vs keeper min_blast=1400 snap=300 join_retrace=0.5:** 98t 69.4% +26794 PF1.67 -> **PF -0.01 / pts -547 / same n** - fade book identical; join slightly worse (PF0.78 vs 0.94)
- **vs Aug-only baseline PF2.11:** still below
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T012944Z_3e21bb3e.json
- **Conclusion:** join_retrace=0.35 **REJECT**. Keeper remains **min_blast=1400 snap=300 join_retrace=0.5**. Next: **one-knob join_wait_sec=60** (keep keeper knobs, risk_pct=10), then fade_lag / stand_aside_n / skip_london / fade|join.


### 2026-09-11 Impulse Fork one-knob join_wait_sec=60 Jan–Aug 2026 (risk_pct=10, keeper knobs) — REJECT vs keeper (identical book)
- **Window:** 2026-01-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, snap_pts=300, snap_sec=10, join_retrace=0.5, **join_wait_sec=60**, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 98 trades, 69.4% wins (68W/30L), +26794.4 pts, sum_r +18.532, avg_r 0.189, avg_pts 273.4, **PF 1.67**; equity_after last ~952.74; skipped 51 (chase×46 / stand_aside×4 / join_timeout×1)
- **exits:** trail58 / sl26 / tp8 / tp2×2 / timeout4
- **by_mode:** fade 94t 70.2% +26818.9 PF1.73; join 4t 50% −24.5 PF0.94
- **by_month:** 2026-01 34t 79.4% +18567.7; 2026-02 31t 74.2% +13324.8; 2026-03 16t 62.5% −1234.5; 2026-04 10t 50% +1008.1; 2026-05 0t; 2026-06 2t 0% −3000; 2026-07 2t 50% −1328.2; 2026-08 3t 66.7% −543.5
- **vs keeper min_blast=1400 snap=300 join_retrace=0.5 join_wait=90:** 98t 69.4% +26794 PF1.67 → **identical trade book / PF / pts / n** — shorter join wait did not change fills on this window
- **vs Aug-only baseline PF2.11:** still below
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T022207Z_55675ae6.json
- **Conclusion:** join_wait_sec=60 **REJECT** (noop vs 90). Keeper remains **min_blast=1400 snap=300 join_retrace=0.5 join_wait=90**. Next: **one-knob fade_lag_sec=0** (keep keeper knobs, risk_pct=10), then stand_aside_n / skip_london / fade|join.

### 2026-09-11 Impulse Fork one-knob fade_lag_sec=0 Jan-Aug 2026 (risk_pct=10, keeper knobs) - REJECT vs keeper
- **Window:** 2026-01-01 -> 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, **fade_lag_sec=0**, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 100 trades, 69.0% wins (69W/31L), +24470.4 pts, sum_r +17.01, avg_r 0.17, avg_pts 244.7, **PF 1.60**; last equity_after 856.66 (peak 2539.65); skipped 52 (chase x47 / stand_aside x4 / join_timeout x1)
- **exits:** trail59 / sl27 / tp8 / tp2 x2 / timeout4
- **by_mode:** fade 96t 69.8% +24494.9 PF1.65; join 4t 50% -24.5 PF0.94
- **by_month:** 2026-01 34t 76.5% +13609.0; 2026-02 33t 75.8% +15669.5; 2026-03 16t 75.0% +798.7; 2026-04 10t 40.0% +550.9; 2026-05 0t; 2026-06 2t 0% -3000; 2026-07 2t 50% -1110.2; 2026-08 3t 33.3% -2047.5
- **vs keeper min_blast=1400 snap=300 join_retrace=0.5 join_wait=90 fade_lag=1:** 98t 69.4% +26794 PF1.67 -> **PF -0.07 / win% -0.4pp / pts -2324 / n +2** - slightly worse; join unchanged PF0.94
- **vs Aug-only baseline PF2.11:** still below
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T031238Z_8facd78b.json
- **Conclusion:** fade_lag_sec=0 **REJECT**. Keeper remains **min_blast=1400 snap=300 join_retrace=0.5 join_wait=90 fade_lag=1**. Next: **one-knob stand_aside_n=5** (keep keeper knobs, risk_pct=10), then skip_london / fade|join.

### 2026-09-11 Impulse Fork one-knob stand_aside_n=5 Janâ€“Aug 2026 (risk_pct=10, keeper knobs) â€” REJECT vs keeper (identical book)
- **Window:** 2026-01-01 â†’ 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, **stand_aside_n=5**, skip_london_utc=true, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 98 trades, 69.4% wins (68W/30L), +26794.4 pts, sum_r +18.532, avg_r 0.189, avg_pts 273.4, **PF 1.67**; equity_after last ~952.74 (peak ~3331.79); skipped 47 (chaseÃ—46 / join_timeoutÃ—1; stand_asideÃ—0)
- **exits:** trail58 / sl26 / tp8 / tp2Ã—2 / timeout4
- **by_mode:** fade 94t 70.2% +26818.9 PF1.73; join 4t 50% âˆ’24.5 PF0.94
- **by_month:** 2026-01 34t 79.4% +18567.7; 2026-02 31t 74.2% +13324.8; 2026-03 16t 62.5% âˆ’1234.5; 2026-04 10t 50% +1008.1; 2026-05 0t; 2026-06 2t 0% âˆ’3000; 2026-07 2t 50% âˆ’1328.2; 2026-08 3t 66.7% âˆ’543.5
- **vs keeper min_blast=1400 snap=300 join_retrace=0.5 join_wait=90 fade_lag=1 stand_aside_n=3:** 98t 69.4% +26794 PF1.67 â†’ **identical trade book / PF / pts / n** â€” n=5 never fired stand_aside on this window (0 skips vs keeperâ€™s 4)
- **vs Aug-only baseline PF2.11:** still below
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T041707Z_66a8c43c.json
- **Conclusion:** stand_aside_n=5 **REJECT** (noop vs 3). Keeper remains **min_blast=1400 snap=300 join_retrace=0.5 join_wait=90 fade_lag=1 stand_aside_n=3**. Next: **one-knob skip_london_utc=false** (keep keeper knobs, risk_pct=10), then fade|join toggles.


### 2026-09-11 Impulse Fork one-knob skip_london_utc=false Jan–Aug 2026 (risk_pct=10, keeper knobs) — REJECT vs keeper
- **Window:** 2026-01-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, fade_lag_sec=1, fade+join+stand_aside on, stand_aside_n=3, **skip_london_utc=false**, **risk_pct=10**, start_equity=1000, workers=4
- **n / metrics:** 104 trades, 68.3% wins (71W/33L), +24551.1 pts, sum_r +16.322, avg_r 0.157, avg_pts 236.1, **PF 1.53**; equity_after last ~952.74 (peak ~2727); skipped 53 (chase×48 / stand_aside×4 / join_timeout×1)
- **exits:** trail61 / sl29 / tp8 / tp2×2 / timeout4
- **by_mode:** fade 98t 70.4% +26477.6 PF1.69; join 6t 33.3% −1926.5 PF0.47
- **by_month:** 2026-01 37t 75.7% +16822.6; 2026-02 34t 73.5% +12826.6; 2026-03 16t 62.5% −1234.5; 2026-04 10t 50% +1008.1; 2026-05 0t; 2026-06 2t 0% −3000; 2026-07 2t 50% −1328.2; 2026-08 3t 66.7% −543.5
- **vs keeper min_blast=1400 snap=300 join_retrace=0.5 join_wait=90 fade_lag=1 stand_aside_n=3 skip_london=true:** 98t 69.4% +26794 PF1.67 → **PF −0.14 / win% −1.1pp / pts −2243 / n +6** — London fills add weak join (PF0.47) and dilute fade PF (1.69 vs 1.73)
- **vs Aug-only baseline PF2.11:** still below
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T051912Z_47a06f58.json
- **Conclusion:** skip_london_utc=false **REJECT**. Keeper remains **skip_london_utc=true** (plus min_blast=1400 snap=300 join_retrace=0.5 join_wait=90 fade_lag=1 stand_aside_n=3). Next: **one-knob join_enabled=false** (fade-only; keep keeper knobs, risk_pct=10), then join-only / other fade|join toggles if needed.


### 2026-09-11 Impulse Fork join_enabled=false (fade-only) — **KEEP for PF**
- Window 2026-01-01 - 2026-09-01; keeper detection knobs + risk_pct=10; join off
- 95t 70.5% +? pts PF **1.74** vs prior keeper join-on PF1.67
- Result: results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T061350Z_c0ede8b5.json
- Conclusion: Prefer fade-only for PF. Next: fade_sl_cap and other fade risk knobs (in flight fade_sl_cap=1200 still on join=true — after that re-baseline fade-only + fade risk).


### 2026-09-11 Impulse Fork one-knob fade_sl_cap_pts=1200 Jan–Aug 2026 (risk_pct=10, join=true side-note) — REJECT vs join-on
- **Window:** 2026-01-01 → 2026-09-01
- **Params:** window_sec=3, min_blast_pts=1400, snap_pts=300, snap_sec=10, join_retrace=0.5, join_wait_sec=90, chase_ext=0.5, fade_lag_sec=1, fade_sl_pct=100, **fade_sl_cap_pts=1200**, fade_tp_pct=200, fade_tp_cap=3000, fade_trail=600, fade_trail_arm=750, fade_hold=250, cooldown=30, daily_halt=1.5, weekly_halt=4, fade+join+stand_aside on, stand_aside_n=3, skip_london_utc=true, **join_enabled=true**, **risk_pct=10**, workers=4
- **n / metrics:** 98 trades, 64.3% wins (63W/35L), +23187.7 pts, sum_r +19.228, avg_r 0.196, avg_pts 236.6, **PF 1.58**; skipped 51 (chase×46 / stand_aside×4 / join_timeout×1)
- **exits:** sl31 / trail53 / tp8 / tp2×2 / timeout4
- **by_mode:** fade 94t 64.9% +23212.2 PF1.62; join 4t 50% −24.5 PF0.94
- **by_month:** 2026-01 34t 73.5% +16229.4 PF2.50; 2026-02 31t 71.0% +13300.1 PF2.28; 2026-03 16t 56.2% −2287.3 PF0.67; 2026-04 10t 50% +1514.7 PF1.31; 2026-05 0t; 2026-06 2t 0% −2400; 2026-07 2t 0% −1028.2 PF0.14; 2026-08 3t 0% −2141 PF0.11
- **vs prior join-on keeper (fade_sl_cap=1500):** 98t 69.4% +26794 PF1.67 → **PF −0.09 / win% −5.1pp / pts −3607 / same n** — tighter SL cap cuts winners harder than losers
- **vs fade-only keeper PF1.74:** side-note only (this run still had join on); re-testing same knob on fade-only next
- **Result:** results/fork_XAUUSD_2026-01-01_2026-09-01_20260911T070920Z_0a0feff9.json
- **Conclusion:** fade_sl_cap_pts=1200 on join=true **REJECT**. Keeper remains **fade-only PF1.74** (fade_sl_cap=1500). Next: **same fade_sl_cap=1200 on fade-only** (join_enabled=false), then fade_sl_cap 1000/1800 + fade_sl_pct.


### 2026-09-11 Asia overnight reference A (PF seed) vs B (points-max trail)
Igor-provided same-window references (354 trades, same entries: timeout_worst 178 / ema_touch 176; skipped 341).

**A — seed keeper (trail off, SL/TP 2000)** — prefer for edge quality / PF
- Params: wait_from_break=true, timeout_action=worst, max_wait=10, trail_arm_mode=off, SL2000 TP2000, flatten22, pullback preferred, max_break15
- **354t · 71.5% (253W/101L) · +292939 pts · PF 3.03**; avg +827.5 / win +1727 / loss −1425
- exits: flatten96 / **tp200** / sl58 · trail_armed 0

**B — points-max reference (trail on, TP5000)** — more pts, thinner PF/win%
- Params: same entry seed + trail_arm_mode=fixed trail_arm_pts=2500 trail_arm_cap=1750 trail_pts=500, TP5000 (SL2000)
- **354t · 68.4% (242W/112L) · +319856 pts · PF 2.96**; avg +903.5 / win +1995 / loss −1454
- exits: flatten120 / **trail165** / sl67 / **tp2** · trail_armed 169 (47.7%)
- Δ vs A: win% −3.1pp, PF −0.07, pts **+27k (~+9%)**; almost no true TPs

**Conclusion:** Keep A as overnight sweep seed. Use B as trail/points benchmark; only promote trail variants that beat A on PF (or clearly lift 2025+ expectancy without wrecking PF). Mind wild XAU from 2025+.

### 2026-09-11 Asia SEED KEEPER A baseline verify (wait_from_break+timeout_worst max_wait10 trail off SL/TP2000) — KEEP / matches ref
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; trail_arm_mode=off; SL/TP fixed 2000; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 71.5% wins (253W/101L), +292938.6 pts, **PF 3.03**; avg +827.5 avg_win +1726.9 avg_loss -1425.4; trail_armed 0/0.0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten96 / tp200 / sl58 — TP-heavy
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +3420 PF2.67; 2024-02 7t 28.6% -3882 PF0.17; 2024-03 9t 66.7% +6321 PF3.14; 2024-04 10t 60.0% +1408 PF1.23; 2024-05 12t 66.7% +9829 PF3.46; 2024-06 7t 57.1% +1286 PF1.24; 2024-07 13t 76.9% +12762 PF5.18; 2024-08 13t 46.2% +1545 PF1.20; 2024-09 10t 60.0% +7076 PF2.44; 2024-10 13t 61.5% +452 PF1.06; 2024-11 9t 55.6% +2415 PF1.56; 2024-12 8t 50.0% +1682 PF1.41; 2025-01 13t 92.3% +15974 PF—; 2025-02 13t 69.2% +12192 PF3.39; 2025-03 13t 76.9% +12163 PF4.31; 2025-04 9t 88.9% +12607 PF7.30; 2025-05 10t 90.0% +14568 PF8.28; 2025-06 9t 77.8% +8835 PF3.21; 2025-07 11t 72.7% +11975 PF5.71; 2025-08 8t 75.0% +3532 PF2.02; 2025-09 13t 61.5% +4923 PF1.61; 2025-10 13t 76.9% +14000 PF3.33; 2025-11 12t 66.7% +9313 PF2.39; 2025-12 10t 70.0% +8542 PF2.57; 2026-01 14t 92.9% +24000 PF13.00; 2026-02 9t 77.8% +10000 PF3.50; 2026-03 12t 66.7% +8000 PF2.00; 2026-04 12t 75.0% +12000 PF3.00; 2026-05 15t 93.3% +26000 PF14.00; 2026-06 10t 80.0% +12000 PF4.00; 2026-07 12t 66.7% +8000 PF2.00; 2026-08 9t 77.8% +10000 PF3.50; 2026-09 5t 100.0% +10000 PF—
- **regime rollups:** 2024 122t 59.0% +44314; 2025+ 232t 78.0% +248624; 2026 98t 80.6% +120000
- **vs A reference:** 354t 71.5% +293k PF3.03 → **identical** (354t 71.5% +292939 PF3.03; TP-heavy exits)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T080346Z_77369d17.json
- **Conclusion:** **KEEP — seed A baseline verified on Lenovo.** Confirmed Igor PF~3.03 book. Next: **one-knob SL/TP 1500/1500** (trail still off, keep A entry seed), then 2500/2500 / asymmetric SL1500×TP2000 / SL2000×TP2500, then trail_arm combos vs A and B. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob SL/TP 1500/1500 (trail off, seed A entry) — REJECT vs A
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; trail_arm_mode=off; **SL/TP fixed 1500**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 72.9% wins (258W/96L), +242427.6 pts, **PF 3.04**; avg +684.8 avg_win +1400.3 avg_loss -1238.0; trail_armed 0/0.0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten49 / tp231 / sl74 — TP-heavy (tighter TP)
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +2117 PF1.64; 2024-02 7t 28.6% -3409 PF0.19; 2024-03 9t 66.7% +5654 PF3.30; 2024-04 10t 60.0% +3163 PF1.68; 2024-05 12t 66.7% +7472 PF2.65; 2024-06 7t 57.1% +690 PF1.15; 2024-07 13t 84.6% +12932 PF7.23; 2024-08 13t 69.2% +9157 PF3.56; 2024-09 10t 70.0% +7220 PF3.20; 2024-10 13t 61.5% +1022 PF1.17; 2024-11 9t 66.7% +4074 PF2.29; 2024-12 8t 50.0% +2166 PF1.63; 2025-01 13t 84.6% +11204 PF4.73; 2025-02 13t 69.2% +8293 PF2.66; 2025-03 13t 84.6% +12545 PF6.75; 2025-04 9t 77.8% +6607 PF3.20; 2025-05 10t 90.0% +12000 PF9.00; 2025-06 9t 77.8% +7392 PF3.46; 2025-07 11t 72.7% +8683 PF3.62; 2025-08 8t 75.0% +5031 PF2.68; 2025-09 13t 69.2% +8915 PF2.94; 2025-10 13t 92.3% +16500 PF12.00; 2025-11 12t 50.0% +0 PF1.00; 2025-12 10t 70.0% +6000 PF2.33; 2026-01 14t 85.7% +15000 PF6.00; 2026-02 9t 77.8% +7500 PF3.50; 2026-03 12t 75.0% +9000 PF3.00; 2026-04 12t 66.7% +6000 PF2.00; 2026-05 15t 93.3% +19500 PF14.00; 2026-06 10t 80.0% +9000 PF4.00; 2026-07 12t 75.0% +9000 PF3.00; 2026-08 9t 77.8% +7500 PF3.50; 2026-09 5t 80.0% +4500 PF4.00
- **regime rollups:** 2024 122t 63.9% +52259; 2025+ 232t 77.6% +190169; 2026 98t 79.6% +87000
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +1.4pp / pts −50511 / PF +0.01** — PF flat noise; expectancy and pts crushed (avg_win capped ~1400 vs ~1727); 2025+ pts −58k vs A
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T085803Z_1b065d7d.json
- **Conclusion:** **REJECT — keep seed A SL/TP 2000.** Tighter fixed exits do not improve edge quality. Next: **one-knob SL/TP 2500/2500** (trail still off, keep A entry seed), then asymmetric SL1500×TP2000 / SL2000×TP2500, then trail_arm combos vs A and B. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob SL/TP 2500/2500 (trail off, seed A entry) — REJECT vs A
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; trail_arm_mode=off; **SL/TP fixed 2500**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 70.9% wins (251W/103L), +327024.0 pts, **PF 2.93**; avg +923.8 avg_win +1978.3 avg_loss -1645.8; trail_armed 0/0.0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten128 / tp173 / sl53 — more flatten, fewer TP hits vs A
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +3434 PF2.68; 2024-02 7t 28.6% -4382 PF0.16; 2024-03 9t 66.7% +4638 PF2.34; 2024-04 10t 60.0% +2675 PF1.42; 2024-05 12t 66.7% +11538 PF3.56; 2024-06 7t 57.1% +1382 PF1.22; 2024-07 13t 76.9% +15557 PF6.09; 2024-08 13t 53.8% +2755 PF1.41; 2024-09 10t 60.0% +9505 PF3.12; 2024-10 13t 61.5% +505 PF1.06; 2024-11 9t 55.6% +1743 PF1.36; 2024-12 8t 50.0% +731 PF1.16; 2025-01 13t 92.3% +14793 PF—; 2025-02 13t 69.2% +12477 PF3.04; 2025-03 13t 76.9% +12046 PF7.27; 2025-04 9t 77.8% +10607 PF3.12; 2025-05 10t 90.0% +15925 PF7.37; 2025-06 9t 77.8% +11406 PF3.90; 2025-07 11t 72.7% +14975 PF5.93; 2025-08 8t 62.5% +1384 PF1.30; 2025-09 13t 69.2% +7147 PF1.94; 2025-10 13t 69.2% +12500 PF2.25; 2025-11 12t 58.3% +4691 PF1.44; 2025-12 10t 70.0% +9729 PF2.51; 2026-01 14t 85.7% +24263 PF5.85; 2026-02 9t 77.8% +12500 PF3.50; 2026-03 12t 75.0% +15000 PF3.00; 2026-04 12t 83.3% +20000 PF5.00; 2026-05 15t 93.3% +32500 PF14.00; 2026-06 10t 80.0% +15000 PF4.00; 2026-07 12t 58.3% +5000 PF1.40; 2026-08 9t 77.8% +12500 PF3.50; 2026-09 5t 100.0% +12500 PF—
- **regime rollups:** 2024 122t 59.8% +50081; 2025+ 232t 76.7% +276943; 2026 98t 80.6% +149263
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% −0.6pp / pts +34085 / PF −0.10** — pts up from wider targets but PF and win% worse; 2025+ pts +28k vs A yet overall edge quality slips
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T092358Z_6376269b.json
- **Conclusion:** **REJECT — keep seed A SL/TP 2000.** Wider fixed exits buy points at the cost of PF. Next: **one-knob asymmetric SL1500×TP2000** (trail still off, keep A entry seed), then SL2000×TP2500, then trail_arm combos vs A and B. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob asymmetric SL1500×TP2000 (trail off, seed A entry) — REJECT vs A
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; trail_arm_mode=off; **SL1500 / TP2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 68.4% wins (242W/112L), +279132.5 pts, **PF 3.03**; avg +788.5 avg_win +1720.4 avg_loss -1225.1; trail_armed 0/0.0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten80 / tp190 / sl84 — still TP-heavy; more SL than A
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +2135 PF1.64; 2024-02 7t 28.6% -3409 PF0.19; 2024-03 9t 66.7% +6821 PF3.78; 2024-04 10t 60.0% +2908 PF1.63; 2024-05 12t 66.7% +9301 PF3.05; 2024-06 7t 57.1% +2190 PF1.49; 2024-07 13t 76.9% +12978 PF5.57; 2024-08 13t 46.2% +2366 PF1.34; 2024-09 10t 60.0% +8076 PF3.06; 2024-10 13t 61.5% +1952 PF1.32; 2024-11 9t 55.6% +3121 PF1.87; 2024-12 8t 50.0% +2368 PF1.69; 2025-01 13t 84.6% +11040 PF4.68; 2025-02 13t 69.2% +12293 PF3.46; 2025-03 13t 76.9% +12663 PF4.98; 2025-04 9t 77.8% +9607 PF4.20; 2025-05 10t 80.0% +13000 PF5.33; 2025-06 9t 77.8% +9835 PF4.28; 2025-07 11t 63.6% +8975 PF3.53; 2025-08 8t 75.0% +3989 PF2.33; 2025-09 13t 61.5% +6923 PF2.14; 2025-10 13t 76.9% +15500 PF4.44; 2025-11 12t 50.0% +3000 PF1.33; 2025-12 10t 60.0% +6000 PF2.00; 2026-01 14t 85.7% +21000 PF8.00; 2026-02 9t 77.8% +11000 PF4.67; 2026-03 12t 66.7% +10000 PF2.67; 2026-04 12t 66.7% +10000 PF2.67; 2026-05 15t 93.3% +26500 PF18.67; 2026-06 10t 80.0% +13000 PF5.33; 2026-07 12t 58.3% +6500 PF1.87; 2026-08 9t 77.8% +11000 PF4.67; 2026-09 5t 80.0% +6500 PF5.33
- **regime rollups:** 2024 122t 59.0% +50808; 2025+ 232t 73.3% +228324; 2026 98t 76.5% +115500
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% −3.1pp / pts −13806 / PF 0.00** — PF flat but win% and expectancy worse; tighter SL adds 26 SL exits vs A’s 58→84; 2025+ pts −20k / win% −4.7pp vs A
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T101049Z_d333c0cd.json
- **Conclusion:** **REJECT — keep seed A SL/TP 2000.** Asymmetric tighter SL does not help PF and hurts win%/pts (esp. 2025+). Next: **one-knob asymmetric SL2000×TP2500** (trail still off, keep A entry seed), then trail_arm combos vs A and B. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob asymmetric SL2000×TP2500 (trail off, seed A entry) — REJECT vs A
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; trail_arm_mode=off; **SL2000 / TP2500**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 68.4% wins (242W/112L), +319743.7 pts, **PF 2.96**; avg +903.2 avg_win +1994.2 avg_loss -1454.1; trail_armed 0/0.0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten118 / tp169 / sl67 — more flatten, fewer TP vs A; still no trail
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +3434 PF2.68; 2024-02 7t 28.6% -3882 PF0.17; 2024-03 9t 66.7% +5138 PF2.74; 2024-04 10t 60.0% +2908 PF1.47; 2024-05 12t 66.7% +12038 PF4.01; 2024-06 7t 57.1% +2382 PF1.44; 2024-07 13t 76.9% +15557 PF6.09; 2024-08 13t 46.2% +1345 PF1.17; 2024-09 10t 60.0% +9056 PF2.84; 2024-10 13t 61.5% +1452 PF1.19; 2024-11 9t 55.6% +2243 PF1.52; 2024-12 8t 50.0% +1231 PF1.30; 2025-01 13t 92.3% +14793 PF—; 2025-02 13t 69.2% +13477 PF3.64; 2025-03 13t 69.2% +9643 PF3.46; 2025-04 9t 77.8% +11607 PF3.90; 2025-05 10t 80.0% +14068 PF4.52; 2025-06 9t 77.8% +11335 PF3.83; 2025-07 11t 72.7% +15475 PF7.09; 2025-08 8t 62.5% +1884 PF1.46; 2025-09 13t 61.5% +5640 PF1.70; 2025-10 13t 69.2% +14500 PF2.81; 2025-11 12t 50.0% +2191 PF1.21; 2025-12 10t 70.0% +10729 PF2.97; 2026-01 14t 71.4% +17000 PF3.12; 2026-02 9t 77.8% +13500 PF4.38; 2026-03 12t 66.7% +12000 PF2.50; 2026-04 12t 75.0% +16500 PF3.75; 2026-05 15t 93.3% +33000 PF17.50; 2026-06 10t 80.0% +16000 PF5.00; 2026-07 12t 58.3% +7500 PF1.75; 2026-08 9t 77.8% +13500 PF4.38; 2026-09 5t 100.0% +12500 PF—
- **regime rollups:** 2024 122t 59.0% +52902; 2025+ 232t 73.3% +266841; 2026 98t 76.5% +141500
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% −3.1pp / pts +26805 / PF −0.07** — pts up (incl. 2025+ +18k) but PF/win% worse; headline rhymes with REF B (68.4% +320k PF2.96) without trail
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T105722Z_adf46d01.json
- **Conclusion:** **REJECT — keep seed A SL/TP 2000.** Wider TP buys points at PF cost (same pattern as 2500/2500). SL/TP fixed grid done. Next: **REF B trail verify** (seed A entry + trail_arm_mode=fixed arm=2500 cap=1750 trail=500 TP=5000 SL2000), then other trail_arm one-knobs vs A/B. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia REF B trail verify (seed A entry + fixed arm2500/cap1750/trail500 TP5000 SL2000) — REJECT promote / KEEP as points-max ref
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=2500 cap=1750 trail=500**; **SL2000 / TP5000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 68.4% wins (242W/112L), +319855.8 pts, **PF 2.96**; avg +903.5 avg_win +1994.7 avg_loss -1454.1; trail_armed 169/47.7%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten120 / **trail165** / sl67 / **tp2** — trail-heavy, almost no true TP
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +3097 PF2.51; 2024-02 7t 28.6% -3882 PF0.17; 2024-03 9t 66.7% +4968 PF2.68; 2024-04 10t 60.0% +1828 PF1.30; 2024-05 12t 66.7% +11942 PF3.99; 2024-06 7t 57.1% +1645 PF1.30; 2024-07 13t 76.9% +15581 PF6.10; 2024-08 13t 46.2% +506 PF1.07; 2024-09 10t 60.0% +7695 PF2.56; 2024-10 13t 61.5% +1700 PF1.22; 2024-11 9t 55.6% +1956 PF1.46; 2024-12 8t 50.0% +1101 PF1.27; 2025-01 13t 92.3% +14667 PF—; 2025-02 13t 69.2% +12687 PF3.48; 2025-03 13t 69.2% +10038 PF3.56; 2025-04 9t 77.8% +11830 PF3.96; 2025-05 10t 80.0% +14083 PF4.52; 2025-06 9t 77.8% +11307 PF3.83; 2025-07 11t 72.7% +13606 PF6.36; 2025-08 8t 62.5% +1082 PF1.26; 2025-09 13t 61.5% +5107 PF1.63; 2025-10 13t 69.2% +14097 PF2.76; 2025-11 12t 50.0% +4834 PF1.45; 2025-12 10t 70.0% +11998 PF3.20; 2026-01 14t 71.4% +16129 PF3.02; 2026-02 9t 77.8% +14913 PF4.73; 2026-03 12t 66.7% +12489 PF2.56; 2026-04 12t 75.0% +17454 PF3.91; 2026-05 15t 93.3% +32221 PF17.11; 2026-06 10t 80.0% +15254 PF4.81; 2026-07 12t 58.3% +10104 PF2.01; 2026-08 9t 77.8% +12583 PF4.15; 2026-09 5t 100.0% +15236 PF—
- **regime rollups:** 2024 122t 59.0% +48137; 2025+ 232t 73.3% +271719; 2026 98t 76.5% +146384
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% −3.1pp / pts +26917 / PF −0.07** — 2025+ pts +23k but win% −4.7pp vs A
- **vs Igor B reference:** 354t 68.4% +319856 PF2.96 → **identical** (trail165 / tp2 / trail_armed 169)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T113538Z_4d50c4ac.json
- **Conclusion:** **REJECT as promotion over A — KEEP B only as points-max reference.** Matches Igor B; more pts / thinner PF+win%; trail substitutes for TP. Next: **one-knob trail on A’s TP2000** (same fixed arm2500/cap1750/trail500, SL2000 TP2000) to isolate trail vs A without TP5000 confound; then arm/trail_pts knobs. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail-on A TP2000 (fixed arm2500/cap1750/trail500 SL/TP2000) — REJECT / near-noop vs A
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=2500 cap=1750 trail=500**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 71.5% wins (253W/101L), +292938.6 pts, **PF 3.03**; avg +827.5 avg_win +1726.9 avg_loss -1425.4; trail_armed 2/0.6%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten96 / tp200 / sl58 — TP-heavy; trail never meaningfully engages
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +3420 PF2.67; 2024-02 7t 28.6% -3882 PF0.17; 2024-03 9t 66.7% +6321 PF3.14; 2024-04 10t 60.0% +1408 PF1.23; 2024-05 12t 66.7% +9829 PF3.46; 2024-06 7t 57.1% +1286 PF1.24; 2024-07 13t 76.9% +12762 PF5.18; 2024-08 13t 46.2% +1545 PF1.20; 2024-09 10t 60.0% +7076 PF2.44; 2024-10 13t 61.5% +452 PF1.06; 2024-11 9t 55.6% +2415 PF1.56; 2024-12 8t 50.0% +1682 PF1.41; 2025-01 13t 92.3% +15974 PF—; 2025-02 13t 69.2% +12192 PF3.39; 2025-03 13t 76.9% +12163 PF4.31; 2025-04 9t 88.9% +12607 PF7.30; 2025-05 10t 90.0% +14568 PF8.28; 2025-06 9t 77.8% +8835 PF3.21; 2025-07 11t 72.7% +11975 PF5.71; 2025-08 8t 75.0% +3532 PF2.02; 2025-09 13t 61.5% +4923 PF1.61; 2025-10 13t 76.9% +14000 PF3.33; 2025-11 12t 66.7% +9313 PF2.39; 2025-12 10t 70.0% +8542 PF2.57; 2026-01 14t 92.9% +24000 PF13.00; 2026-02 9t 77.8% +10000 PF3.50; 2026-03 12t 66.7% +8000 PF2.00; 2026-04 12t 75.0% +12000 PF3.00; 2026-05 15t 93.3% +26000 PF14.00; 2026-06 10t 80.0% +12000 PF4.00; 2026-07 12t 66.7% +8000 PF2.00; 2026-08 9t 77.8% +10000 PF3.50; 2026-09 5t 100.0% +10000 PF—
- **regime rollups:** 2024 122t 59.0% +44314; 2025+ 232t 78.0% +248624; 2026 98t 80.6% +120000
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% 0 / pts −0.4 / PF 0.00** — book identical; arm=2500 > TP2000 so trail almost never arms (2/354)
- **Result:** C:\\Users\\user\\strateg\\results\\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T115514Z_2e9bb17b.json
- **Conclusion:** **REJECT — near-noop.** Trail cannot engage before fixed TP2000 when arm=2500. Keeper remains A trail off SL/TP2000. Next: **one-knob trail_arm_pts=1500** (keep fixed/cap1750/trail500 SL/TP2000) so trail can arm before TP; then arm=1000 / trail_pts knobs. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail_arm_pts=1500 (fixed/cap1750/trail500 SL/TP2000, seed A entry) — KEEP / provisional promote vs A (PF+win%)
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1500 cap=1750 trail=500**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 77.1% wins (273W/81L), +274049.0 pts, **PF 3.35**; avg +774.1 avg_win +1430.2 avg_loss -1437.0; trail_armed 245/69.2%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten64 / **trail145** / tp98 / sl47 — mixed trail+TP (not B-style trail-only)
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +3375 PF2.65; 2024-02 7t 28.6% -3882 PF0.17; 2024-03 9t 66.7% +5712 PF2.93; 2024-04 10t 60.0% +1922 PF1.31; 2024-05 12t 66.7% +6721 PF2.68; 2024-06 7t 57.1% +688 PF1.13; 2024-07 13t 84.6% +12803 PF6.59; 2024-08 13t 69.2% +8015 PF3.36; 2024-09 10t 70.0% +6463 PF2.51; 2024-10 13t 61.5% +452 PF1.06; 2024-11 9t 66.7% +1928 PF1.50; 2024-12 8t 50.0% +1291 PF1.31; 2025-01 13t 100.0% +16447 PF—; 2025-02 13t 69.2% +9440 PF2.85; 2025-03 13t 84.6% +12733 PF5.75; 2025-04 9t 88.9% +10329 PF6.16; 2025-05 10t 100.0% +14650 PF—; 2025-06 9t 77.8% +6137 PF2.53; 2025-07 11t 81.8% +9802 PF5.23; 2025-08 8t 75.0% +4738 PF2.37; 2025-09 13t 69.2% +6942 PF2.14; 2025-10 13t 92.3% +15755 PF8.88; 2025-11 12t 83.3% +11176 PF3.79; 2025-12 10t 90.0% +12771 PF7.39; 2026-01 14t 92.9% +17769 PF9.88; 2026-02 9t 77.8% +8016 PF3.00; 2026-03 12t 75.0% +8002 PF2.33; 2026-04 12t 75.0% +8230 PF2.37; 2026-05 15t 93.3% +18113 PF10.06; 2026-06 10t 80.0% +9422 PF3.36; 2026-07 12t 83.3% +10655 PF3.66; 2026-08 9t 77.8% +8165 PF3.04; 2026-09 5t 100.0% +9266 PF—
- **regime rollups:** 2024 122t 63.9% +45487; 2025+ 232t 84.1% +228562; 2026 98t 83.7% +97640
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +5.6pp / pts −18890 / PF +0.32** — PF and win% clear wins; pts give back ~19k (trail clips some runners); 2025+ win% +6.1pp / pts −20k vs A; still 98 TP so not REF-B trail-only
- **vs REF B (arm2500 TP5000):** 354t 68.4% +320k PF2.96 → better PF/win%, fewer pts; healthier exit mix (trail145/tp98 vs trail165/tp2)
- **Result:** C:\\Users\\user\\strateg\\results\\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T125808Z_50ec6c6b.json
- **Conclusion:** **KEEP / provisional promote for PF+clean expectancy over A.** Arm=1500 lets trail engage before TP2000 and lifts PF 3.03→3.35 and win% 71.5→77.1 without B’s TP starvation. Pts −19k is the tradeoff. Next: **one-knob trail_arm_pts=1000** (same fixed/cap1750/trail500 SL/TP2000) then trail_pts knobs. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail_arm_pts=1000 (fixed/cap1750/trail500 SL/TP2000, seed A entry) - KEEP / provisional PF promote vs A and arm1500
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1000 cap=1750 trail=500**; **SL/TP fixed 2000**; asia 1-7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 84.2% wins (298W/56L), +213543.7 pts, **PF 3.64**; avg +603.2 avg_win +988.2 avg_loss -1445.4; trail_armed 288/81.4%; skipped 341 (no_breakx318, late_shortx22, asia_too_smallx1)
- **exits:** flatten36 / **trail247** / tp39 / sl32 - trail-heavy (still some TP, not B-style TP≈0)
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 72.7% +4823 PF4.29; 2024-02 7t 42.9% -2471 PF0.47; 2024-03 9t 77.8% +3160 PF2.09; 2024-04 10t 90.0% +5574 PF3.79; 2024-05 12t 83.3% +8432 PF5.28; 2024-06 7t 71.4% -76 PF0.98; 2024-07 13t 84.6% +7477 PF4.26; 2024-08 13t 69.2% +5260 PF2.55; 2024-09 10t 80.0% +7566 PF4.32; 2024-10 13t 76.9% +1754 PF1.37; 2024-11 9t 88.9% +6336 PF39.51; 2024-12 8t 62.5% +198 PF1.05; 2025-01 13t 100.0% +11454 PF-; 2025-02 13t 76.9% +7058 PF2.57; 2025-03 13t 84.6% +6793 PF3.53; 2025-04 9t 88.9% +4220 PF3.11; 2025-05 10t 100.0% +10877 PF-; 2025-06 9t 88.9% +6197 PF4.10; 2025-07 11t 81.8% +7136 PF4.08; 2025-08 8t 87.5% +6486 PF5.45; 2025-09 13t 76.9% +4843 PF2.19; 2025-10 13t 92.3% +12936 PF7.47; 2025-11 12t 83.3% +4400 PF2.10; 2025-12 10t 90.0% +6250 PF4.13; 2026-01 14t 100.0% +14814 PF-; 2026-02 9t 88.9% +9050 PF5.53; 2026-03 12t 83.3% +8744 PF3.19; 2026-04 12t 83.3% +6156 PF2.54; 2026-05 15t 100.0% +13048 PF-; 2026-06 10t 90.0% +9251 PF5.63; 2026-07 12t 83.3% +6034 PF2.51; 2026-08 9t 77.8% +3678 PF1.92; 2026-09 5t 100.0% +6086 PF-
- **regime rollups:** 2024 122t 76.2% +48033; 2025+ 232t 88.4% +165511; 2026 98t 89.8% +76862
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +12.7pp / pts -79395 / PF +0.61** - strongest PF+win% lift so far; pts give back ~79k (avg_win ~988 vs A's ~1727); 2025+ win% 88.4 vs 78.0 / pts -83k vs A
- **vs arm=1500 provisional:** 354t 77.1% +274049 PF3.35 → **win% +7.1pp / pts -60505 / PF +0.29** - better PF/clean rate, steeper pts haircut; exits more trail-heavy (247/39 tp vs 145/98)
- **vs REF B:** better PF/win%, far fewer pts; healthier than B's TP starvation but still trail-dominant
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T135436Z_a9699af8.json
- **Conclusion:** **KEEP / provisional PF promote over A and arm1500.** Prefer PF/clean expectancy per focus; arm=1000 is new PF champ (3.64 / 84.2%) with known pts cost. Seed A remains the points/TP-heavy reference; arm1500 stays the balanced PF+pts middle. Next: **one-knob trail_pts=400** on arm=1000 (same fixed/cap1750 SL/TP2000), then trail_pts=600 / arm=1250 if needed. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail_pts=400 on arm=1000 (fixed/cap1750 SL/TP2000, seed A entry) — REJECT / near-flat mild− vs PF keeper
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1000 cap=1750 trail=400**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 84.2% wins (298W/56L), +211717.7 pts, **PF 3.62**; avg +598.1 avg_win +982.1 avg_loss -1445.4; trail_armed 288/81.4%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten35 / **trail263** / tp24 / sl32 — more trail / fewer TP than trail=500 keeper
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 72.7% +5423 PF4.70; 2024-02 7t 42.9% -2326 PF0.50; 2024-03 9t 77.8% +3753 PF2.29; 2024-04 10t 90.0% +6261 PF4.13; 2024-05 12t 83.3% +7861 PF4.99; 2024-06 7t 71.4% -200 PF0.95; 2024-07 13t 84.6% +6400 PF3.79; 2024-08 13t 69.2% +4978 PF2.47; 2024-09 10t 80.0% +6831 PF4.00; 2024-10 13t 76.9% +1591 PF1.33; 2024-11 9t 88.9% +6870 PF42.76; 2024-12 8t 62.5% +42 PF1.01; 2025-01 13t 100.0% +11483 PF—; 2025-02 13t 76.9% +6117 PF2.36; 2025-03 13t 84.6% +7573 PF3.83; 2025-04 9t 88.9% +4920 PF3.46; 2025-05 10t 100.0% +11577 PF—; 2025-06 9t 88.9% +6052 PF4.03; 2025-07 11t 81.8% +7434 PF4.21; 2025-08 8t 87.5% +6629 PF5.55; 2025-09 13t 76.9% +5294 PF2.30; 2025-10 13t 92.3% +11538 PF6.77; 2025-11 12t 83.3% +5036 PF2.26; 2025-12 10t 90.0% +5260 PF3.63; 2026-01 14t 100.0% +13133 PF—; 2026-02 9t 88.9% +9550 PF5.78; 2026-03 12t 83.3% +8027 PF3.01; 2026-04 12t 83.3% +6956 PF2.74; 2026-05 15t 100.0% +13126 PF—; 2026-06 10t 90.0% +8809 PF5.40; 2026-07 12t 83.3% +6430 PF2.61; 2026-08 9t 77.8% +2952 PF1.74; 2026-09 5t 100.0% +6338 PF—
- **regime rollups:** 2024 122t 76.2% +47482; 2025+ 232t 88.4% +164236; 2026 98t 89.8% +75323
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +12.7pp / pts −81221 / PF +0.59** — still beats A on PF/win%; pts giveback larger than trail=500
- **vs PF keeper (arm=1000 trail=500):** 354t 84.2% +213544 PF3.64 → **n 0 / win% 0 / pts −1826 / PF −0.02** — same win%; slightly worse PF+pts (tighter trail clips more)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T144154Z_ad0b555e.json
- **Conclusion:** **REJECT — keep PF keeper arm=1000 trail=500.** trail_pts=400 is near-flat mild− vs keeper (PF 3.62 vs 3.64, −1.8k pts). Trail wins ≠ full TP (263 trail / 24 TP). Next: **one-knob trail_pts=600** (same fixed arm=1000/cap1750 SL/TP2000) to bracket above keeper, then trail_arm_cap knobs. Weight 2025+ wild swings. Ask before any reaktor push.

﻿### 2026-09-11 Asia one-knob trail_pts=600 on arm=1000 (fixed/cap1750 SL/TP2000, seed A entry) — KEEP / provisional PF promote vs trail=500 keeper
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1000 cap=1750 trail=600**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 84.2% wins (298W/56L), +219079.4 pts, **PF 3.71**; avg +618.9 avg_win +1006.8 avg_loss -1445.4; trail_armed 288/81.4%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten37 / **trail227** / tp58 / sl32 — looser trail than 500 → more TP (58 vs 39), fewer trail exits (227 vs 247)
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 72.7% +4223 PF3.88; 2024-02 7t 42.9% -2771 PF0.41; 2024-03 9t 77.8% +3804 PF2.31; 2024-04 10t 90.0% +4674 PF3.34; 2024-05 12t 83.3% +8517 PF5.32; 2024-06 7t 71.4% +222 PF1.06; 2024-07 13t 84.6% +7745 PF4.38; 2024-08 13t 69.2% +6226 PF2.83; 2024-09 10t 80.0% +7054 PF4.09; 2024-10 13t 76.9% +1054 PF1.22; 2024-11 9t 88.9% +5970 PF37.29; 2024-12 8t 62.5% +1488 PF1.38; 2025-01 13t 100.0% +13585 PF—; 2025-02 13t 76.9% +6358 PF2.41; 2025-03 13t 84.6% +7867 PF3.93; 2025-04 9t 88.9% +4658 PF3.33; 2025-05 10t 100.0% +11775 PF—; 2025-06 9t 88.9% +5594 PF3.80; 2025-07 11t 81.8% +7229 PF4.12; 2025-08 8t 87.5% +5986 PF5.11; 2025-09 13t 76.9% +4013 PF1.98; 2025-10 13t 92.3% +14160 PF8.08; 2025-11 12t 83.3% +4159 PF2.04; 2025-12 10t 90.0% +6885 PF4.44; 2026-01 14t 100.0% +16465 PF—; 2026-02 9t 88.9% +9177 PF5.59; 2026-03 12t 83.3% +9720 PF3.43; 2026-04 12t 83.3% +5480 PF2.37; 2026-05 15t 100.0% +11938 PF—; 2026-06 10t 90.0% +10013 PF6.01; 2026-07 12t 83.3% +6380 PF2.59; 2026-08 9t 77.8% +3648 PF1.91; 2026-09 5t 100.0% +5786 PF—
- **regime rollups:** 2024 122t 76.2% +48204; 2025+ 232t 88.4% +170875; 2026 98t 89.8% +78606
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +12.7pp / pts −73860 / PF +0.68** — clear PF/win% win; pts tradeoff smaller than trail=500 (−74k vs −79k)
- **vs prior PF keeper (arm=1000 trail=500):** 354t 84.2% +213544 PF3.64 → **n 0 / win% 0 / pts +5535 / PF +0.07** — same win%; better PF and more pts (looser trail lets more reach TP); 2025+ pts +6.6k same 88.4% win
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T155315Z_62bfb5e9.json
- **Conclusion:** **KEEP / provisional PF promote — new keeper arm=1000 trail=600 PF3.71 / 84.2% / +219k.** Beats trail=500 on both PF and pts with same win%. Trail wins ≠ full TP (227 trail / 58 TP). Next: **one-knob trail_arm_cap_pts=1500** (same fixed arm=1000 trail=600 SL/TP2000), then cap=2000 / trail_pts=700. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail_arm_cap_pts=1500 on arm=1000/trail=600 (fixed SL/TP2000, seed A entry) — REJECT / near-noop vs PF keeper
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1000 cap=1500 trail=600**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 84.2% wins (298W/56L), +219079.4 pts, **PF 3.71**; avg +618.9 avg_win +1006.8 avg_loss -1445.4; trail_armed 288/81.4%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten37 / **trail227** / tp58 / sl32 — identical mix to cap=1750 keeper
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 72.7% +4223 PF3.88; 2024-02 7t 42.9% -2771 PF0.41; 2024-03 9t 77.8% +3804 PF2.31; 2024-04 10t 90.0% +4674 PF3.34; 2024-05 12t 83.3% +8517 PF5.32; 2024-06 7t 71.4% +222 PF1.06; 2024-07 13t 84.6% +7745 PF4.38; 2024-08 13t 69.2% +6226 PF2.83; 2024-09 10t 80.0% +7054 PF4.09; 2024-10 13t 76.9% +1054 PF1.22; 2024-11 9t 88.9% +5970 PF37.29; 2024-12 8t 62.5% +1488 PF1.38; 2025-01 13t 100.0% +13585 PF—; 2025-02 13t 76.9% +6358 PF2.41; 2025-03 13t 84.6% +7867 PF3.93; 2025-04 9t 88.9% +4658 PF3.33; 2025-05 10t 100.0% +11775 PF—; 2025-06 9t 88.9% +5594 PF3.80; 2025-07 11t 81.8% +7229 PF4.12; 2025-08 8t 87.5% +5986 PF5.11; 2025-09 13t 76.9% +4013 PF1.98; 2025-10 13t 92.3% +14160 PF8.08; 2025-11 12t 83.3% +4159 PF2.04; 2025-12 10t 90.0% +6885 PF4.44; 2026-01 14t 100.0% +16465 PF—; 2026-02 9t 88.9% +9177 PF5.59; 2026-03 12t 83.3% +9720 PF3.43; 2026-04 12t 83.3% +5480 PF2.37; 2026-05 15t 100.0% +11938 PF—; 2026-06 10t 90.0% +10013 PF6.01; 2026-07 12t 83.3% +6380 PF2.59; 2026-08 9t 77.8% +3648 PF1.91; 2026-09 5t 100.0% +5786 PF—
- **regime rollups:** 2024 122t 76.2% +48204; 2025+ 232t 88.4% +170875; 2026 98t 89.8% +78606
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +12.7pp / pts −73860 / PF +0.68** — still beats A on PF/win%; pts tradeoff unchanged vs keeper
- **vs PF keeper (arm=1000 cap=1750 trail=600):** 354t 84.2% +219079 PF3.71 → **identical** (n/win%/pts/PF/exits/trail_armed) — cap 1500↔1750 does not bind under arm=1000 trail=600 TP2000
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T162854Z_e933e38a.json
- **Conclusion:** **REJECT — near-noop.** Keep PF keeper **arm=1000 cap=1750 trail=600** (PF3.71 / 84.2% / +219k). Tightening cap to 1500 changes nothing here. Next: **one-knob trail_arm_cap_pts=2000** (same fixed arm=1000 trail=600 SL/TP2000), then trail_pts=700. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail_arm_cap_pts=2000 on arm=1000/trail=600 (fixed SL/TP2000, seed A entry) - REJECT / near-noop vs PF keeper
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1000 cap=2000 trail=600**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 84.2% wins (298W/56L), +219079.4 pts, **PF 3.71**; avg +618.9 avg_win +1006.8 avg_loss -1445.4; trail_armed 288/81.4%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten37 / **trail227** / tp58 / sl32 - identical mix to cap=1750 keeper
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 72.7% +4223 PF3.88; 2024-02 7t 42.9% -2771 PF0.41; 2024-03 9t 77.8% +3804 PF2.31; 2024-04 10t 90.0% +4674 PF3.34; 2024-05 12t 83.3% +8517 PF5.32; 2024-06 7t 71.4% +222 PF1.06; 2024-07 13t 84.6% +7745 PF4.38; 2024-08 13t 69.2% +6226 PF2.83; 2024-09 10t 80.0% +7054 PF4.09; 2024-10 13t 76.9% +1054 PF1.22; 2024-11 9t 88.9% +5970 PF37.29; 2024-12 8t 62.5% +1488 PF1.38; 2025-01 13t 100.0% +13585 PF-; 2025-02 13t 76.9% +6358 PF2.41; 2025-03 13t 84.6% +7867 PF3.93; 2025-04 9t 88.9% +4658 PF3.33; 2025-05 10t 100.0% +11775 PF-; 2025-06 9t 88.9% +5594 PF3.80; 2025-07 11t 81.8% +7229 PF4.12; 2025-08 8t 87.5% +5986 PF5.11; 2025-09 13t 76.9% +4013 PF1.98; 2025-10 13t 92.3% +14160 PF8.08; 2025-11 12t 83.3% +4159 PF2.04; 2025-12 10t 90.0% +6885 PF4.44; 2026-01 14t 100.0% +16465 PF-; 2026-02 9t 88.9% +9177 PF5.59; 2026-03 12t 83.3% +9720 PF3.43; 2026-04 12t 83.3% +5480 PF2.37; 2026-05 15t 100.0% +11938 PF-; 2026-06 10t 90.0% +10013 PF6.01; 2026-07 12t 83.3% +6380 PF2.59; 2026-08 9t 77.8% +3648 PF1.91; 2026-09 5t 100.0% +5786 PF-
- **regime rollups:** 2024 122t 76.2% +48204; 2025+ 232t 88.4% +170875; 2026 98t 89.8% +78606
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +12.7pp / pts −73860 / PF +0.68** - still beats A on PF/win%; pts tradeoff unchanged vs keeper
- **vs PF keeper (arm=1000 cap=1750 trail=600):** 354t 84.2% +219079 PF3.71 → **identical** (n/win%/pts/PF/exits/trail_armed) - widening cap 1750→2000 also does not bind under arm=1000 trail=600 TP2000
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T165945Z_beec9b0b.json
- **Conclusion:** **REJECT - near-noop.** Cap knob exhausted for this arm/trail/TP stack (1500 and 2000 both identical to keeper 1750). Keep PF keeper **arm=1000 cap=1750 trail=600** (PF3.71 / 84.2% / +219k). Next: **one-knob trail_pts=700** (same fixed arm=1000/cap1750 SL/TP2000), then maybe arm=1250. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 Asia one-knob trail_pts=700 on arm=1000 (fixed/cap1750 SL/TP2000, seed A entry) — KEEP / provisional PF promote vs trail=600
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=worst; max_wait=10; **trail_arm_mode=fixed arm=1000 cap=1750 trail=700**; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 84.2% wins (298W/56L), +225054.5 pts, **PF 3.78**; avg +635.7 avg_win +1026.8 avg_loss -1445.4; trail_armed 288/81.4%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten38 / **trail207** / tp77 / sl32 — looser trail than 600 → fewer trail exits / more TP (227→207 trail, 58→77 TP)
- **entries:** timeout_worst 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 72.7% +3623 PF3.47; 2024-02 7t 42.9% -2942 PF0.37; 2024-03 9t 77.8% +6331 PF3.18; 2024-04 10t 90.0% +5872 PF3.94; 2024-05 12t 83.3% +7717 PF4.91; 2024-06 7t 71.4% +1395 PF1.35; 2024-07 13t 84.6% +7010 PF4.06; 2024-08 13t 69.2% +7336 PF3.16; 2024-09 10t 80.0% +6454 PF3.83; 2024-10 13t 76.9% +354 PF1.07; 2024-11 9t 88.9% +5170 PF32.43; 2024-12 8t 62.5% +1188 PF1.30; 2025-01 13t 100.0% +12685 PF—; 2025-02 13t 76.9% +9736 PF3.16; 2025-03 13t 84.6% +7654 PF3.86; 2025-04 9t 88.9% +5605 PF3.80; 2025-05 10t 100.0% +12138 PF—; 2025-06 9t 88.9% +5165 PF3.58; 2025-07 11t 81.8% +8995 PF4.88; 2025-08 8t 87.5% +5486 PF4.77; 2025-09 13t 76.9% +3855 PF1.94; 2025-10 13t 92.3% +14919 PF8.46; 2025-11 12t 83.3% +4568 PF2.14; 2025-12 10t 90.0% +7934 PF4.97; 2026-01 14t 100.0% +15565 PF—; 2026-02 9t 88.9% +9080 PF5.54; 2026-03 12t 83.3% +9195 PF3.30; 2026-04 12t 83.3% +6606 PF2.65; 2026-05 15t 100.0% +11358 PF—; 2026-06 10t 90.0% +9413 PF5.71; 2026-07 12t 83.3% +6956 PF2.74; 2026-08 9t 77.8% +3148 PF1.79; 2026-09 5t 100.0% +5486 PF—
- **regime rollups:** 2024 122t 76.2% +49507; 2025+ 232t 88.4% +175548; 2026 98t 89.8% +76807
- **vs A (SL/TP2000 trail off):** 354t 71.5% +292939 PF3.03 → **n 0 / win% +12.7pp / pts −67884 / PF +0.75** — still beats A on PF/win%; pts giveback smaller than trail=600 (−68k vs −74k)
- **vs PF keeper (arm=1000 cap=1750 trail=600):** 354t 84.2% +219079 PF3.71 → **n 0 / win% 0 / pts +5975 / PF +0.07** — same win%; PF and pts both up (looser trail lets more runners reach TP)
- **Result:** C:\\Users\\user\\strateg\\results\\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T172727Z_d392d41b.json
- **Conclusion:** **KEEP / provisional promote for PF over trail=600.** New PF keeper **arm=1000 cap=1750 trail=700** (PF3.78 / 84.2% / +225k). Trail band: 400 mild− / 500 PF3.64 / 600 PF3.71 / **700 PF3.78**. Trail wins ≠ full TP (207 trail / 77 TP). Next: **one-knob trail_pts=800** (same fixed arm=1000/cap1750 SL/TP2000), then arm=1250 if 800 plateaus. Weight 2025+ wild swings. Ask before any reaktor push.

### 2026-09-11 **INVALIDATE all timeout_action=worst Asia results**
Igor: worst has a bug. Drop A/B PF trail ladder built on worst (PF~3.03–3.78 etc.). **Restart** with same seed but **timeout_action=market**. New baseline in flight: wait_from_break=true, max_wait=10, trail off, SL/TP2000, market timeout, 2024-01→2026-10.


### 2026-09-11 Asia MARKET trail-off baseline SL/TP2000 (wait_from_break, max_wait=10) — KEEP as new market seed A_m
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL/TP fixed 2000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 68.9% wins (244W/110L), +246216.3 pts, **PF 2.49**; avg +695.5 avg_win +1684.3 avg_loss -1497.7; trail_armed 0/0.0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten100 / tp187 / sl67 — TP-heavy, no trail
- **entries:** timeout_market 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +1992 PF1.88; 2024-02 7t 28.6% -4758 PF0.09; 2024-03 9t 66.7% +5716 PF2.79; 2024-04 10t 60.0% +904 PF1.14; 2024-05 12t 66.7% +8777 PF3.05; 2024-06 7t 57.1% +1234 PF1.23; 2024-07 13t 76.9% +12667 PF5.14; 2024-08 13t 46.2% -636 PF0.92; 2024-09 10t 60.0% +6999 PF2.40; 2024-10 13t 61.5% -83 PF0.99; 2024-11 9t 55.6% +1276 PF1.26; 2024-12 8t 50.0% +1321 PF1.30; 2025-01 13t 92.3% +15232 PF53.45; 2025-02 13t 69.2% +10793 PF2.66; 2025-03 13t 69.2% +8831 PF3.08; 2025-04 9t 77.8% +8607 PF3.15; 2025-05 10t 90.0% +13650 PF7.82; 2025-06 9t 77.8% +8753 PF3.19; 2025-07 11t 72.7% +11004 PF4.28; 2025-08 8t 75.0% +3532 PF2.02; 2025-09 13t 53.8% +3880 PF1.46; 2025-10 13t 76.9% +14000 PF3.33; 2025-11 12t 50.0% +186 PF1.02; 2025-12 10t 70.0% +8339 PF2.47; 2026-01 14t 78.6% +16000 PF3.67; 2026-02 9t 77.8% +10000 PF3.50; 2026-03 12t 58.3% +4000 PF1.40; 2026-04 12t 66.7% +8000 PF2.00; 2026-05 15t 93.3% +26000 PF14.00; 2026-06 10t 80.0% +12000 PF4.00; 2026-07 12t 66.7% +8000 PF2.00; 2026-08 9t 77.8% +10000 PF3.50; 2026-09 5t 100.0% +10000 PF—
- **regime rollups:** 2024 122t 59.0% +35409; 2025+ 232t 74.1% +210808; 2026 98t 76.5% +104000
- **Note:** Discarded all prior timeout_action=worst ladder (bug). This is the **new market baseline** — do not compare to worst A PF3.03.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T182632Z_a2828638.json
- **Conclusion:** **KEEP as market seed A_m** (trail off, SL/TP2000, timeout=market). Next: **one-knob SL/TP 1500/1500** (trail still off, market timeout), then 2500/2500 → asymmetric SL1500×TP2000 / SL2000×TP2500 → trail_arm combos. Prefer PF; report pts. Weight 2025+. Ask before any reaktor push.

### 2026-09-11 Asia MARKET one-knob SL/TP 1500/1500 (trail off, seed A_m entry) — REJECT vs A_m
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL/TP fixed 1500**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 68.1% wins (241W/113L), +182567.6 pts, **PF 2.26**; avg +515.7 avg_win +1360.5 avg_loss -1285.9; trail_armed 0/0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten57 / tp207 / sl90
- **entries:** timeout_market 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +524 PF1.16; 2024-02 7t 28.6% -3758 PF0.11; 2024-03 9t 66.7% +5176 PF2.92; 2024-04 10t 60.0% +1724 PF1.29; 2024-05 12t 66.7% +6084 PF2.29; 2024-06 7t 57.1% +690 PF1.15; 2024-07 13t 84.6% +11459 PF6.52; 2024-08 13t 61.5% +6015 PF2.15; 2024-09 10t 70.0% +7220 PF3.20; 2024-10 13t 61.5% +27 PF1.00; 2024-11 9t 55.6% +982 PF1.23; 2024-12 8t 50.0% +1805 PF1.49; 2025-01 13t 84.6% +10749 PF4.58; 2025-02 13t 69.2% +8293 PF2.66; 2025-03 13t 69.2% +7245 PF2.40; 2025-04 9t 77.8% +6607 PF3.20; 2025-05 10t 90.0% +12000 PF9.00; 2025-06 9t 77.8% +7310 PF3.44; 2025-07 11t 63.6% +5004 PF2.15; 2025-08 8t 75.0% +5031 PF2.68; 2025-09 13t 53.8% +2880 PF1.45; 2025-10 13t 92.3% +16500 PF12.00; 2025-11 12t 41.7% -3000 PF0.71; 2025-12 10t 60.0% +3000 PF1.50; 2026-01 14t 78.6% +12000 PF3.67; 2026-02 9t 77.8% +7500 PF3.50; 2026-03 12t 58.3% +3000 PF1.40; 2026-04 12t 58.3% +3000 PF1.40; 2026-05 15t 86.7% +16500 PF6.50; 2026-06 10t 60.0% +3000 PF1.50; 2026-07 12t 66.7% +6000 PF2.00; 2026-08 9t 77.8% +7500 PF3.50; 2026-09 5t 80.0% +4500 PF4.00
- **regime rollups:** 2024 122t 62.3% +37948; 2025+ 232t 71.1% +144620; 2026 98t 71.4% +63000
- **vs A_m (SL/TP2000 trail off, market):** 354t 68.9% +246216 PF2.49 → **n 0 / win% −0.8pp / pts −63648 / PF −0.23** — 2025+ pts −66k / win% −3.0pp vs A_m; tighter exits add SL 67→90 and cut pts hard
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T190917Z_14bf1bcf.json
- **Conclusion:** **REJECT — keep market seed A_m SL/TP 2000.** Tighter 1500/1500 hurts PF and pts (esp. 2025+). Next: **one-knob SL/TP 2500/2500** (trail still off, timeout=market), then asymmetric SL1500×TP2000 / SL2000×TP2500, then trail_arm. Prefer PF; report pts. Weight 2025+. Ask before any reaktor push.

### 2026-09-11 Asia MARKET one-knob SL/TP 2500/2500 (trail off, seed A_m entry) - REJECT vs A_m
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL/TP fixed 2500**; asia 1-7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 68.1% wins (241W/113L), +267026.7 pts, **PF 2.39**; avg +754.3 avg_win +1903.0 avg_loss -1695.5; trail_armed 0/0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten136 / tp157 / sl61 - wider exits: fewer TP (187→157), more flatten (100→136), fewer SL (67→61)
- **entries:** timeout_market 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 63.6% +933 PF1.41; 2024-02 7t 28.6% -5066 PF0.09; 2024-03 9t 66.7% +4002 PF2.08; 2024-04 10t 60.0% +904 PF1.11; 2024-05 12t 66.7% +10304 PF3.15; 2024-06 7t 57.1% +457 PF1.07; 2024-07 13t 76.9% +14549 PF5.76; 2024-08 13t 53.8% +2274 PF1.33; 2024-09 10t 60.0% +8555 PF2.88; 2024-10 13t 61.5% -29 PF1.0; 2024-11 9t 55.6% +550 PF1.1; 2024-12 8t 50.0% +296 PF1.06; 2025-01 13t 92.3% +14051 PF49.39; 2025-02 13t 69.2% +9597 PF2.5; 2025-03 13t 76.9% +11212 PF5.97; 2025-04 9t 66.7% +5607 PF1.75; 2025-05 10t 90.0% +14436 PF6.77; 2025-06 9t 77.8% +11324 PF3.88; 2025-07 11t 54.5% +8456 PF2.92; 2025-08 8t 62.5% -444 PF0.9; 2025-09 13t 61.5% +6105 PF1.78; 2025-10 13t 69.2% +12500 PF2.25; 2025-11 12t 50.0% +2666 PF1.25; 2025-12 10t 70.0% +9526 PF2.43; 2026-01 14t 64.3% +9263 PF1.74; 2026-02 9t 77.8% +12500 PF3.5; 2026-03 12t 66.7% +10000 PF2.0; 2026-04 12t 83.3% +20000 PF5.0; 2026-05 15t 93.3% +32500 PF14.0; 2026-06 10t 80.0% +15000 PF4.0; 2026-07 12t 58.3% +5000 PF1.4; 2026-08 9t 66.7% +7500 PF2.0; 2026-09 5t 100.0% +12500 PF-
- **regime rollups:** 2024 122t 59.8% +37727; 2025+ 232t 72.4% +229299; 2026 98t 75.5% +124263
- **vs A_m (SL/TP2000 trail off, market):** 354t 68.9% +246216 PF2.49 → **n 0 / win% -0.8pp / pts +20811 / PF -0.10** - 2025+ pts +18k / win% -1.7pp vs A_m; wider exits buy points at PF+win% cost (Prefer PF → reject)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T192852Z_c8401aab.json
- **Conclusion:** **REJECT - keep market seed A_m SL/TP 2000.** Wider 2500/2500 buys pts (+21k) but loses PF/win%. Next: **one-knob asymmetric SL1500×TP2000** (trail still off, timeout=market), then SL2000×TP2500, then trail_arm. Prefer PF; report pts. Weight 2025+. Ask before any reaktor push.


### 2026-09-11 Asia MARKET one-knob asymmetric SL1000xTP4000 (trail off, seed A_m entry / Igor ask) - REJECT vs A_m
- **Window:** 2024-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; asia 1-7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 354 trades, 46.9% wins (166W/188L), +210770.6 pts, **PF 2.19**; avg +595.4 avg_win +2336.7 avg_loss -942.1; trail_armed 0/0%; skipped 341 (no_break×318, late_short×22, asia_too_small×1)
- **exits:** flatten119 / tp61 / sl173 / timeout1 — tight SL floods stops (67→173), TP collapses (187→61)
- **entries:** timeout_market 178, ema_touch 176
- **by_month (compact):** 2024-01 11t 54.5% -548 PF0.84; 2024-02 7t 28.6% -3042 PF0.13; 2024-03 9t 55.6% 1508 PF1.46; 2024-04 10t 40.0% 1482 PF1.25; 2024-05 12t 58.3% 7873 PF2.86; 2024-06 7t 42.9% 1132 PF1.28; 2024-07 13t 69.2% 12431 PF4.11; 2024-08 13t 30.8% 703 PF1.09; 2024-09 10t 60.0% 10904 PF4.32; 2024-10 13t 46.2% 1708 PF1.24; 2024-11 9t 44.4% 2117 PF1.5; 2024-12 8t 50.0% 2460 PF1.91; 2025-01 13t 76.9% 8001 PF3.67; 2025-02 13t 61.5% 6996 PF2.4; 2025-03 13t 46.2% 1809 PF1.26; 2025-04 9t 44.4% 11000 PF3.2; 2025-05 10t 40.0% 5452 PF1.91; 2025-06 9t 66.7% 8920 PF3.97; 2025-07 11t 45.5% 4038 PF1.89; 2025-08 8t 50.0% -651 PF0.84; 2025-09 13t 46.2% 6759 PF1.97; 2025-10 13t 38.5% 10310 PF2.29; 2025-11 12t 16.7% -2000 PF0.8; 2025-12 10t 30.0% 3788 PF1.54; 2026-01 14t 21.4% 1000 PF1.09; 2026-02 9t 66.7% 21000 PF8.0; 2026-03 12t 50.0% 18000 PF4.0; 2026-04 12t 41.7% 11177 PF2.6; 2026-05 15t 60.0% 27216 PF5.54; 2026-06 10t 30.0% 5000 PF1.71; 2026-07 12t 25.0% 1924 PF1.23; 2026-08 9t 55.6% 16000 PF5.0; 2026-09 5t 60.0% 6305 PF4.15
- **regime rollups:** 2024 122t 49.2% +38727; 2025+ 232t 45.7% +172044; 2026 98t 43.9% +107621
- **vs A_m (SL/TP2000 trail off, market):** 354t 68.9% +246216 PF2.49 → **n 0 / win% -22.0pp / pts -35446 / PF -0.30** — 2025+ win% 45.7 vs 74.1 (−28.4pp) / pts −38764; R:R 1:4 starves win% and still loses PF/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2024-01-01_2026-10-01_20260911T200616Z_7d5dd83d.json
- **Conclusion:** **REJECT - keep market seed A_m SL/TP 2000.** Igor's SL1000/TP4000 ask fails hard on win%/PF (esp. 2025+). Next: **asymmetric SL2000×TP2500** (trail still off, timeout=market), then trail_arm sweeps. Prefer PF; report pts. Weight 2025+. Ask before any reaktor push.


### 2026-09-12 Asia MARKET 2025+ baseline SL1000/TP4000 (trail off, seed A_m entry / Igor research base) - REJECT vs A_m 2025+
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; asia 1-7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 232 trades, 45.7% wins (106W/126L), +172043.5 pts, **PF 2.39**; avg +741.6 avg_win +2791.6 avg_loss -983.1; trail_armed 0/0%; skipped 204 (no_break×194, late_short×10)
- **exits:** flatten51 / tp57 / sl123 / timeout1 — tight SL floods stops
- **entries:** timeout_market 116, ema_touch 116
- **by_month (compact):** 2025-01 13t 76.9% +8001 PF3.67; 2025-02 13t 61.5% +6996 PF2.4; 2025-03 13t 46.2% +1809 PF1.26; 2025-04 9t 44.4% +11000 PF3.2; 2025-05 10t 40.0% +5452 PF1.91; 2025-06 9t 66.7% +8920 PF3.97; 2025-07 11t 45.5% +4038 PF1.89; 2025-08 8t 50.0% -651 PF0.84; 2025-09 13t 46.2% +6759 PF1.97; 2025-10 13t 38.5% +10310 PF2.29; 2025-11 12t 16.7% -2000 PF0.8; 2025-12 10t 30.0% +3788 PF1.54; 2026-01 14t 21.4% +1000 PF1.09; 2026-02 9t 66.7% +21000 PF8.0; 2026-03 12t 50.0% +18000 PF4.0; 2026-04 12t 41.7% +11177 PF2.6; 2026-05 15t 60.0% +27216 PF5.54; 2026-06 10t 30.0% +5000 PF1.71; 2026-07 12t 25.0% +1924 PF1.23; 2026-08 9t 55.6% +16000 PF5.0; 2026-09 5t 60.0% +6305 PF4.15
- **regime rollups:** 2025+ 232t 45.7% +172044; 2026 98t 43.9% +107621
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → **n 0 / win% -28.4pp / pts -38764** — matches full-window 1000/4000's 2025+ slice; R:R 1:4 still starves win% vs A_m
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260911T211502Z_019cad6f.json
- **Conclusion:** **REJECT vs A_m 2025+.** Keep using SL1000/TP4000 as research base for entry knobs only (Igor lock). Next: **one-knob skip_late_short_wait=0** (off) on same 2025+ window / SL1000 TP4000 / timeout=market. Then asia_start/end, max_wait, max_break_after. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob skip_late_short_wait=0 on SL1000/TP4000 (2025+, seed A_m entry) — REJECT vs 2025+ base
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; asia 1–7; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; **skip_late_short_wait=0** (off; was 7/3000); flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 242 trades, 45.0% wins (109W/133L), +167041.3 pts, **PF 2.28**; avg +690.3 avg_win +2733.1 avg_loss −984.0; trail_armed 0/0%; skipped 194 (no_break×194 — late_short×0 vs base×10)
- **exits:** flatten54 / tp57 / sl130 / timeout1 — same TP count as base; +10 late-short fills mostly stop out (SL 123→130)
- **entries:** timeout_market 116, ema_touch 126 (base 116/116 — +10 ema_touch from unblocked late shorts)
- **by_month (compact):** 2025-01 13t 76.9% +8001 PF3.67; 2025-02 13t 61.5% +6996 PF2.4; 2025-03 14t 50.0% +1957 PF1.28; 2025-04 9t 44.4% +11000 PF3.2; 2025-05 10t 40.0% +5452 PF1.91; 2025-06 12t 50.0% +5920 PF1.99; 2025-07 11t 45.5% +4038 PF1.89; 2025-08 11t 54.5% +199 PF1.04; 2025-09 13t 46.2% +6759 PF1.97; 2025-10 14t 35.7% +9310 PF2.03; 2025-11 12t 16.7% −2000 PF0.8; 2025-12 12t 25.0% +1788 PF1.2; 2026-01 14t 21.4% +1000 PF1.09; 2026-02 9t 66.7% +21000 PF8; 2026-03 12t 50.0% +18000 PF4; 2026-04 12t 41.7% +11177 PF2.6; 2026-05 15t 60.0% +27216 PF5.54; 2026-06 10t 30.0% +5000 PF1.71; 2026-07 12t 25.0% +1924 PF1.23; 2026-08 9t 55.6% +16000 PF5; 2026-09 5t 60.0% +6305 PF4.15
- **regime rollups:** 2025+ 242t 45.0% +167041; 2026 98t 43.9% +107622 (months with +10 late shorts: Mar/Jun/Aug/Oct/Dec 2025)
- **vs 2025+ SL1000/TP4000 base (skip_late=7):** 232t 45.7% +172044 PF2.39 → **n +10 / win% −0.7pp / pts −5003 / PF −0.11** — unblocking late shorts adds low-quality fills
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260911T220224Z_6fd5e6a7.json
- **Conclusion:** **REJECT — keep skip_late=7 on research base.** Turning skip_late off hurts PF/pts. Next: **one-knob asia_start_hour=0** (keep end=7, restore skip_late=7, SL1000/TP4000 trail off, timeout=market, 2025+). Then asia_end / max_wait / max_break_after. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob asia_start_hour=0 (end=7) on SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs 2025+ base
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 0-7** (was 1-7); min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 229 trades, 45.9% wins (105W/124L), +170043.5 pts, **PF 2.40**; avg +742.5 avg_win +2780.1 avg_loss -982.8; trail_armed 0/0%; skipped 207 (no_break×197, late_short×10)
- **exits:** flatten51 / tp56 / sl121 / timeout1
- **entries:** timeout_market 115, ema_touch 114 (base 116/116)
- **by_month (compact):** 2025-01 13t 76.9% +8001 PF3.67; 2025-02 13t 61.5% +6996 PF2.4; 2025-03 13t 46.2% +1809 PF1.26; 2025-04 9t 44.4% +11000 PF3.2; 2025-05 10t 40.0% +5452 PF1.91; 2025-06 9t 66.7% +8920 PF3.97; 2025-07 11t 45.5% +4038 PF1.89; 2025-08 8t 50.0% -651 PF0.84; 2025-09 13t 46.2% +6759 PF1.97; 2025-10 13t 38.5% +10310 PF2.29; 2025-11 12t 16.7% -2000 PF0.8; 2025-12 10t 30.0% +3788 PF1.54; 2026-01 14t 21.4% +1000 PF1.09; 2026-02 9t 66.7% +21000 PF8; 2026-03 9t 55.6% +16000 PF5; 2026-04 12t 41.7% +11177 PF2.6; 2026-05 15t 60.0% +27216 PF5.54; 2026-06 10t 30.0% +5000 PF1.71; 2026-07 12t 25.0% +1924 PF1.23; 2026-08 9t 55.6% +16000 PF5; 2026-09 5t 60.0% +6305 PF4.15
- **regime rollups:** 2025+ 229t 45.9% +170044; 2026 95t 44.2% +104621 (Mar 2026 n 12→9)
- **vs 2025+ SL1000/TP4000 base (asia 1-7):** 232t 45.7% +172044 PF2.39 → **n -3 / win% +0.2pp / pts -2000 / PF +0.01** — near-flat; starting Asia at 00:00 does not help
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260911T222522Z_a3d62f96.json
- **Conclusion:** **REJECT - keep asia 1-7 on research base.** Earlier Asia window is a no-op/mild pts loss. Next: **one-knob asia_end_hour=6** (restore start=1, SL1000/TP4000 trail off, timeout=market, 2025+). Then end=8 / max_wait / max_break_after. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob asia_end_hour=6 (start=1) on SL1000/TP4000 (2025+, seed A_m entry) - KEEP vs 2025+ base
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6** (was 1-7); min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 222 trades, 45.9% wins (102W/120L), +186867.7 pts, **PF 2.59**; avg +841.7 avg_win +2984.5 avg_loss -979.6; trail_armed 0/0%; skipped 214 ({"no_break":202,"late_short":12})
- **exits:** {"flatten":44,"sl":116,"tp":61,"timeout":1}
- **entries:** {"timeout_market":116,"ema_touch":106}
- **by_month (compact):** 2025-01 12t 75.0% +7390 PF3.46; 2025-02 12t 66.7% +10763 PF3.69; 2025-03 9t 66.7% +5967 PF2.99; 2025-04 10t 40.0% +10000 PF2.67; 2025-05 11t 36.4% +5785 PF1.83; 2025-06 9t 44.4% +7265 PF2.45; 2025-07 11t 45.5% +4482 PF1.92; 2025-08 7t 28.6% -800 PF0.78; 2025-09 14t 35.7% +1013 PF1.11; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 15.4% -3000 PF0.73; 2025-12 9t 33.3% +6000 PF2.0; 2026-01 11t 27.3% +4000 PF1.5; 2026-02 10t 60.0% +20000 PF6.0; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 33.3% +6000 PF2.0; 2026-05 14t 64.3% +28216 PF6.64; 2026-06 11t 54.5% +16735 PF4.35; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 66.7% +21000 PF8.0; 2026-09 4t 25.0% -2695 PF0.1
- **regime rollups:** 2025+ 222t 45.9% +186868; 2026 92t 46.7% +110002
- **vs 2025+ SL1000/TP4000 base (asia 1-7):** 232t 45.7% +172044 PF2.39 → **n -10 / win% +0.2pp / pts +14824 / PF +0.20** - shorter Asia (end 06:00) lifts PF/pts; fewer fills but better quality
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts (research-base only KEEP, not A_m challenger)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260911T225219Z_513791c6.json
- **Conclusion:** **KEEP asia 1-6 as research-base window for SL1000/TP4000 track** (prefer PF). Still use A_m (SL/TP2000) as live benchmark. Next: **one-knob asia_end_hour=8** (start=1, skip_late=7, SL1000/TP4000 trail off, timeout=market, 2025+) then max_wait / max_break_after. Prefer PF; report pts. Ask before any reaktor push.


### 2026-09-12 Asia MARKET one-knob asia_end_hour=8 (start=1) on SL1000/TP4000 (2025+, seed A_m entry) — REJECT vs asia_end=6 research base
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-8** (was 1-7 / research keep 1-6); min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **Result:** 220t 42.7% (94W/126L) +148275 pts PF**2.23**; exits flatten47/sl119/tp53/timeout1; entries timeout_market122/ema_touch98; trail_armed 0
- **vs 2025+ SL1000/TP4000 base (asia 1-7):** 232t 45.7% +172044 PF2.39 → **n −12 / win% −3.0pp / pts −23769 / PF −0.16**
- **vs asia_end=6 KEEP (asia 1-6):** 222t 45.9% +186868 PF2.59 → **n −2 / win% −3.2pp / pts −38593 / PF −0.36**
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Conclusion:** **REJECT — keep asia 1-6 as research-base window.** Longer Asia session dilutes PF/win%/pts. Next: **one-knob max_wait_candles=8** on asia 1-6 / SL1000 TP4000 / timeout=market / 2025+, then max_wait=12 / max_break_after. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob max_wait_candles=8 on asia 1-6 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs asia_end=6 research base
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=8** (was 10); trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 226 trades, 43.8% wins (99W/127L), +164713.1 pts, **PF 2.32**; avg +728.8 avg_win +2926.0 avg_loss -983.9; trail_armed 0/0%; skipped 210 (no_break×202, late_short×8)
- **exits:** flatten43 / tp58 / sl124 / timeout1
- **entries:** timeout_market 143, ema_touch 83 (asia1-6 keep 116/106)
- **regime rollups:** 2025+ 226t 43.8% +164713; 2026 93t 43.0% +94002
- **vs asia_end=6 KEEP (max_wait=10):** 222t 45.9% +186868 PF2.59 → **n +4 / win% -2.1pp / pts -22155 / PF -0.27** — shorter wait floods timeout_market fills and hurts quality
- **vs 2025+ SL1000/TP4000 base (asia 1-7 max_wait=10):** 232t 45.7% +172044 PF2.39 → **n -6 / win% -1.9pp / pts -7331 / PF -0.07**
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260911T235004Z_73e4202a.json
- **Conclusion:** **REJECT - keep max_wait=10 on asia 1-6 research base.** Shorter wait hurts PF/win%/pts. Next: **one-knob max_wait_candles=12** on asia 1-6 / SL1000 TP4000 / timeout=market / 2025+, then max_break_after. Prefer PF; report pts. Ask before any reaktor push.


### 2026-09-12 Asia MARKET one-knob max_wait_candles=12 on asia 1-6 / SL1000/TP4000 (2025+, seed A_m entry) - KEEP vs asia_end=6 research base
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=12** (was 10); trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 218 trades, 47.2% wins (103W/115L), +196143.3 pts, **PF 2.73**; avg +899.7 avg_win +3005.7 avg_loss -986.5; trail_armed 0/0%; skipped 218 (no_breakx202, late_shortx16)
- **exits:** flatten43 / tp62 / sl112 / timeout1
- **entries:** timeout_market 100, ema_touch 118 (asia1-6 keep max_wait10: 116/106 — longer wait shifts toward ema_touch)
- **by_month (compact):** 2025-01 11t 72.7% +6054 PF3.02; 2025-02 12t 66.7% +11509 PF3.88; 2025-03 9t 66.7% +5967 PF2.99; 2025-04 10t 40.0% +10000 PF2.67; 2025-05 11t 45.5% +8552 PF2.43; 2025-06 9t 44.4% +7265 PF2.45; 2025-07 11t 45.5% +4482 PF1.92; 2025-08 5t 40.0% +300 PF1.12; 2025-09 13t 38.5% +2013 PF1.25; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 23.1% +2000 PF1.2; 2025-12 9t 33.3% +6000 PF2.0; 2026-01 11t 27.3% +4000 PF1.5; 2026-02 10t 50.0% +15000 PF4.0; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 33.3% +6000 PF2.0; 2026-05 14t 71.4% +33216 PF9.3; 2026-06 11t 54.5% +16735 PF4.35; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 66.7% +21000 PF8.0; 2026-09 4t 25.0% -2695 PF0.1
- **regime rollups:** 2025+ 218t 47.2% +196143; 2026 92t 46.7% +110002 (2026 unchanged vs max_wait10 KEEP — lift is 2025 quality)
- **vs asia_end=6 KEEP (max_wait=10):** 222t 45.9% +186868 PF2.59 → **n -4 / win% +1.3pp / pts +9275 / PF +0.14** — longer wait cuts timeout_market floods and lifts PF/win%/pts
- **vs 2025+ SL1000/TP4000 base (asia 1-7 max_wait=10):** 232t 45.7% +172044 PF2.39 → **n -14 / win% +1.5pp / pts +24099 / PF +0.34**
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts (research-base KEEP only, not A_m challenger)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T001834Z_c932b6b7.json
- **Conclusion:** **KEEP max_wait=12 on asia 1-6 research base** (prefer PF). New research KEEP: asia 1-6 / max_wait=12 / SL1000 TP4000 / skip_late=7 / trail off / timeout=market → 218t 47.2% +196143 PF2.73. Next: **one-knob max_break_candles_after=10** (was 15) on that KEEP, then other entry knobs. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob max_break_candles_after=10 on asia 1-6 / max_wait=12 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs max_wait=12 KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=10** (was 15); pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 150 trades, 50.0% wins (75W/75L), +155088.5 pts, **PF 3.10**; avg +1033.9 avg_win +3053.3 avg_loss -985.5; trail_armed 0/0%; skipped 286 (no_break×272, late_short×14)
- **exits:** flatten30 / tp46 / sl73 / timeout1
- **entries:** timeout_market 73, ema_touch 77 (KEEP max_break15: 100/118 — tighter break window cuts both)
- **regime rollups:** 2025+ 150t 50.0% +155089; (2026 subset in by_month ×9)
- **vs max_wait=12 KEEP (max_break=15):** 218t 47.2% +196143 PF2.73 → **n -68 / win% +2.8pp / pts -41055 / PF +0.37** — PF inflates by thinning late-break fills; absolute pts crater
- **vs asia_end=6 KEEP (max_wait=10 max_break=15):** 222t 45.9% +186868 PF2.59 → **n -72 / win% +4.1pp / pts -31779 / PF +0.51**
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts / thinner book
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T004338Z_5bc2bd42.json
- **Conclusion:** **REJECT - keep max_break=15 on asia 1-6 / max_wait=12 research KEEP.** Tighter break window is a false PF upgrade (selection bias). Next: **one-knob max_break_candles_after=20** (looser side) on KEEP max_wait=12 / asia 1-6 / SL1000 TP4000 / timeout=market / 2025+, then other entry knobs. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob max_break_candles_after=20 on asia 1-6 / max_wait=12 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs max_wait=12 KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=20** (was 15); pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 262 trades, 45.8% wins (120W/142L), +217143.7 pts, **PF 2.55**; avg +828.8 avg_win +2979.9 avg_loss -989.1; trail_armed 0/0%; skipped 174 (no_break×153, late_short×21)
- **exits:** flatten50 / tp72 / sl139 / timeout1
- **entries:** timeout_market 121, ema_touch 141 (KEEP max_break15: 100/118 — looser break window adds both)
- **by_month (compact):** 2025-01 11t 72.7% +6054 PF3.02; 2025-02 13t 61.5% +10509 PF3.1; 2025-03 17t 47.1% +3745 PF1.42; 2025-04 12t 33.3% +8000 PF2; 2025-05 12t 50.0% +10238 PF2.71; 2025-06 12t 41.7% +6708 PF1.96; 2025-07 13t 46.2% +3835 PF1.65; 2025-08 8t 50.0% +39 PF1.01; 2025-09 15t 40.0% +5013 PF1.56; 2025-10 16t 50.0% +24000 PF4; 2025-11 14t 21.4% +1000 PF1.09; 2025-12 11t 36.4% +9000 PF2.29; 2026-01 14t 21.4% +1000 PF1.09; 2026-02 10t 50.0% +15000 PF4; 2026-03 13t 46.2% +17000 PF3.43; 2026-04 14t 35.7% +11000 PF2.22; 2026-05 16t 68.8% +36216 PF8.24; 2026-06 11t 54.5% +16735 PF4.35; 2026-07 15t 40.0% +10746 PF2.19; 2026-08 10t 60.0% +20000 PF6; 2026-09 5t 40.0% +1305 PF1.44
- **regime rollups:** 2025+ 262t 45.8% +217144; 2026 108t ~45.4% ~+129002
- **vs max_wait=12 KEEP (max_break=15):** 218t 47.2% +196143 PF2.73 → **n +44 / win% -1.4pp / pts +21001 / PF -0.18** — looser break adds fills/pts but dilutes PF/win%
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win% (pts near-flat vs A_m 2025+)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T012106Z_ad276aee.json
- **Conclusion:** **REJECT - keep max_break=15 on asia 1-6 / max_wait=12 research KEEP.** Prefer PF (2.55 < 2.73). max_break band done (10 REJECT / 15 KEEP / 20 REJECT). Next: **one-knob min_asia_range_pts=400** (was 300) on KEEP, then min_break_pts / break_on_wick / pullback_mode / ema_period / use_higher_close / resume_closes. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob min_asia_range_pts=400 on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; **min_asia 400** (was 300); break ≥200; **max_break=15**; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 218 trades, 47.2% wins (103W/115L), +196143.3 pts, **PF 2.73**; avg +899.7 avg_win +3005.7 avg_loss -986.5; trail_armed 0/0%; skipped 218 (no_breakx202, late_shortx15, asia_too_smallx1)
- **exits:** flatten43 / tp62 / sl112 / timeout1
- **entries:** timeout_market 100, ema_touch 118
- **vs max_wait=12 KEEP (min_asia=300 max_break=15):** 218t 47.2% +196143 PF2.73 → **identical book** (n/win%/pts/PF unchanged; only +1 asia_too_small skip)
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T015120Z_293ca3ed.json
- **Conclusion:** **REJECT - keep min_asia_range=300 on asia 1-6 / max_wait=12 / max_break=15 research KEEP.** Raising floor to 400 is a no-op. Next: **one-knob min_asia_range_pts=200** (looser band) on KEEP, then min_break_pts / break_on_wick / pullback_mode / ema_period / use_higher_close / resume_closes. Prefer PF; report pts. Ask before any reaktor push.

## 2026-09-12 ~05:37 Europe/Chisinau — Asia one-knob min_asia_range_pts=200 (looser)

**REJECT** (identical no-op) on KEEP seed asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 trail off / skip_late=7 / timeout=market / wait_from_break / 2025-01→2026-10:
- **218t 47.2% +196143 PF2.73** — identical to KEEP min_asia=300 (skip_reasons: no_break 202, late_short 16; no asia_too_small)
- vs A_m 2025+: still weaker on win%/pts (A_m ~74% / +211k)

**KEEP remains min_asia=300.** min_asia band done: 200 REJECT identical / 300 KEEP / 400 REJECT identical.

**Kicked next:** one-knob **min_break_pts=300** (above+below; was 200) on same KEEP; verified running timeout=market workers=4.

Rejected so far on this track: 1500/1500, 2500/2500, SL1000×TP4000 as A_m challenger, skip_late=0, asia_start=0, asia_end=8, max_wait=8, max_break=10, max_break=20, min_asia_range=400, min_asia_range=200.



### 2026-09-12 Asia MARKET one-knob min_break_pts=300 on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; **break ≥300** (was 200); **max_break=15**; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 201 trades, 48.3% wins (97W/104L), +180965.0 pts, **PF 2.77**; avg +900.3 avg_win +2921.8 avg_loss -985.1; trail_armed 0/0%; skipped 235 (no_breakx223, late_shortx12)
- **exits:** flatten43 / tp56 / sl101 / timeout1
- **entries:** timeout_market 94, ema_touch 107 (KEEP break200: 100/118 — tighter break floor cuts both)
- **vs max_wait=12 KEEP (min_break=200):** 218t 47.2% +196143 PF2.73 → **n −17 / win% +1.1pp / pts −15178 / PF +0.04** — tiny PF bump with thinner book and worse pts (false PF upgrade)
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T024938Z_bc88948b.json
- **Conclusion:** **REJECT - keep min_break=200 on asia 1-6 / max_wait=12 / max_break=15 research KEEP.** Prefer pts over negligible PF. Next: **one-knob min_break_pts=100** (looser side) on KEEP, then break_on_wick / pullback_mode / ema_period / use_higher_close / resume_closes. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob min_break_pts=100 on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; **break ±100** (was 200); **max_break=15**; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 235 trades, 46.4% wins (109W/126L), +206822.8 pts, **PF 2.66**; avg +880.1 avg_win +3037.1 avg_loss -985.9; trail_armed 0/0%; skipped 201 (no_break×181, late_short×20)
- **exits:** flatten45 / tp67 / sl122 / timeout1
- **entries:** timeout_market 110, ema_touch 125 (KEEP break200: 100/118 — looser break adds both)
- **vs max_wait=12 KEEP (min_break=200):** 218t 47.2% +196143 PF2.73 → **n +17 / win% −0.8pp / pts +10680 / PF −0.07** — more fills/pts but worse win%/PF
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T031304Z_3a424604.json
- **Conclusion:** **REJECT - keep min_break=200 on asia 1-6 / max_wait=12 / max_break=15 research KEEP.** Prefer PF (2.66 < 2.73). min_break band done (100 REJECT / 200 KEEP / 300 REJECT false-PF). Next: **one-knob break_on_wick=true** (was false) on KEEP, then pullback_mode / ema_period / use_higher_close / resume_closes. Prefer PF; report pts. Ask before any reaktor push.



### 2026-09-12 Asia break_on_wick=true (market SL1000/TP4000 asia1-6 max_wait12)
- Window: 2025-01-01 → 2026-10-01; timeout_action=market; trail off; asia 1-6; skip_late=7; max_wait=12; max_break=15; min_asia=300; min_break=200; pullback=preferred; workers=4
- Result: **264t 45.5% +224883 PF2.59** (exits sl139/flatten49/tp75/timeout1; entries timeout_market111/ema_touch153; skip no_break151/late_short21)
- vs KEEP (wick=false): 218t 47.2% +196143 PF2.73 → n+46 / win%−1.7pp / pts+28.7k / PF−0.14
- vs A_m 2025+: 232t 74.1% +210808 (still weaker on win%/pts quality)
- **REJECT** (prefer PF). KEEP remains break_on_wick=false.
- Next: one-knob pullback_mode=required (was preferred).

### 2026-09-12 Asia MARKET one-knob pullback_mode=required on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; **pullback_mode=required** (was preferred); ema 23; skip_late 7/3000; flatten 22; hold 14; break_on_wick false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 118 trades, 40.7% wins (48W/70L), +67749.6 pts, **PF 1.97**; avg +574.1 avg_win +2861.3 avg_loss −994.2; trail_armed 0/0%; skipped 318 (no_break×202, no_pullback×100, late_short×16)
- **exits:** flatten21 / tp28 / sl69
- **entries:** ema_touch 118 only (KEEP preferred: timeout_market 100 / ema_touch 118 — required cuts all timeout fills via no_pullback×100)
- **by_month (compact):** 2025-01 8t 75% +3039 PF2.52; 2025-02 5t 80% +6993 PF7.99; 2025-03 6t 50% +1522 PF1.51; 2025-04 3t 33.3% +2000 PF2; 2025-05 5t 60% +4552 PF3.28; 2025-06 3t 0% −3000; 2025-07 3t 33.3% +230 PF1.11; 2025-08 4t 25% −2201 PF0.15; 2025-09 7t 28.6% −1337 PF0.73; 2025-10 7t 57.1% +13000 PF5.33; 2025-11 9t 22.2% +1000 PF1.14; 2025-12 5t 0% −5000; 2026-01 7t 14.3% −2000 PF0.67; 2026-02 6t 66.7% +14000 PF8; 2026-03 6t 16.7% −1000 PF0.8; 2026-04 5t 20% 0 PF1; 2026-05 8t 62.5% +14216 PF5.74; 2026-06 7t 42.9% +5735 PF2.43; 2026-07 8t 25% +2000 PF1.33; 2026-08 5t 80% +15000 PF16; 2026-09 1t 0% −1000
- **regime rollups:** 2025+ 118t 40.7% +67750; 2026 53t 39.6% +46951
- **vs max_wait=12 KEEP (pullback preferred):** 218t 47.2% +196143 PF2.73 → **n −100 / win% −6.5pp / pts −128393 / PF −0.76** — collapses absolute book by dropping timeout_market fills
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → far worse on win%/pts/PF
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T041331Z_c935e9bb.json
- **Conclusion:** **REJECT — keep pullback_mode=preferred on asia 1-6 / max_wait=12 / max_break=15 research KEEP.** Prefer PF (1.97 << 2.73). Next: **one-knob pullback_mode=off**, then ema_period / use_higher_close / resume_closes. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob ema_period=14 on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=14** (was 23); skip_late 7/3000; flatten 22; hold 14; break_on_wick false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 220 trades, 42.3% wins (93W/127L), +150921.3 pts, **PF 2.21**; avg +686.0 avg_win +2962.3 avg_loss -980.9; trail_armed 0/0%; skipped 216 (no_break×202, late_short×14)
- **exits:** flatten40 / tp56 / sl123 / timeout1
- **entries:** timeout_market 61, ema_touch 159 (KEEP ema23: timeout_market 100 / ema_touch 118 — faster EMA shifts toward more ema_touch, fewer timeout fills)
- **vs max_wait=12 KEEP (ema=23):** 218t 47.2% +196143 PF2.73 → **n +2 / win% −4.9pp / pts −45222 / PF −0.52** — worse on PF, win%, and pts
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still far worse on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T052052Z_3e9c6c7e.json
- **Conclusion:** **REJECT — keep ema_period=23 on asia 1-6 / max_wait=12 / max_break=15 research KEEP.** Prefer PF (2.21 << 2.73). Next: **one-knob ema_period=34** (other side of 23), then use_higher_close / resume_closes. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob ema_period=34 on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - KEEP vs prior KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=34** (was 23); skip_late 7/3000; flatten 22; hold 14; break_on_wick false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 219 trades, 48.4% wins (106W/113L), +204670.2 pts, **PF 2.84**; avg +934.6 avg_win +2981.6 avg_loss -985.7; trail_armed 0/0%; skipped 217 (no_break×202, late_short×15)
- **exits:** flatten45 / tp63 / sl110 / timeout1
- **entries:** timeout_market 130, ema_touch 89 (prior KEEP ema23: timeout_market 100 / ema_touch 118 — slower EMA shifts toward more timeout fills)
- **vs prior max_wait=12 KEEP (ema=23):** 218t 47.2% +196143 PF2.73 → **n +1 / win% +1.2pp / pts +8527 / PF +0.11** — improves PF, win%, and pts
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still weaker on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T054535Z_c181d0b9.json
- **Conclusion:** **KEEP — promote ema_period=34** on asia 1-6 / max_wait=12 / max_break=15 research KEEP (219t 48.4% +204670 **PF2.84**). ema_period band done (14 REJECT / 23 prior / 34 KEEP). Next: **one-knob use_higher_close=true** (was false) on new KEEP, then resume_closes. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob use_higher_close=true on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 ema=34 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=34**; skip_late 7/3000; flatten 22; hold 14; break_on_wick false; **use_higher_close=true** (was false); resume_closes=1; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 234 trades, 33.3% wins (78W/156L), +61158.3 pts, **PF 1.40**; avg +261.4 avg_win +2758.4 avg_loss -987.1; trail_armed 0/0%; skipped 202 (no_break×202)
- **exits:** flatten40 / tp40 / sl153 / timeout1
- **entries:** lower_close 95, higher_close 117, ema_touch 22 (KEEP uhc=false: timeout_market 130 / ema_touch 89 — uhc floods higher/lower_close and starves timeout/ema structure)
- **by_month (compact):** 2025-01 13t 76.9% +6808 PF3.27; 2025-02 12t 41.7% +1357 PF1.19; 2025-03 9t 33.3% +639 PF1.12; 2025-04 10t 50.0% +15000 PF4.0; 2025-05 13t 23.1% -274 PF0.97; 2025-06 12t 41.7% +5928 PF1.85; 2025-07 11t 45.5% +2796 PF1.52; 2025-08 8t 25.0% -2925 PF0.51; 2025-09 14t 28.6% -3006 PF0.7; 2025-10 14t 42.9% +14310 PF2.79; 2025-11 13t 7.7% -8000 PF0.33; 2025-12 11t 27.3% +4000 PF1.5; 2026-01 11t 18.2% -1000 PF0.89; 2026-02 10t 0.0% -10000 PF0.0; 2026-03 11t 9.1% -6000 PF0.4; 2026-04 9t 22.2% +1000 PF1.14; 2026-05 14t 57.1% +23231 PF4.87; 2026-06 12t 33.3% +3613 PF1.45; 2026-07 14t 14.3% -8837 PF0.26; 2026-08 9t 66.7% +21000 PF8.0; 2026-09 4t 25.0% +1517 PF1.61
- **vs KEEP (uhc=false, ema=34):** 219t 48.4% +204670 PF2.84 → **n +15 / win% −15.1pp / pts −143512 / PF −1.44** — hard reject; entry mix collapses
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → far worse on win%/pts/PF
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T061614Z_601a621c.json
- **Conclusion:** **REJECT — keep use_higher_close=false** on asia 1-6 / max_wait=12 / max_break=15 / ema=34 research KEEP. Prefer PF (1.40 << 2.84). Next: **one-knob resume_closes=2** (baseline=1) on KEEP, then remaining entry knobs. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob resume_closes=2 on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 ema=34 (2025+, seed A_m entry) - REJECT / identical vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=34**; skip_late 7/3000; flatten 22; hold 14; break_on_wick false; use_higher_close false; **resume_closes=2** (was 1); one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 219 trades, 48.4% wins (106W/113L), +204670.2 pts, **PF 2.84**; avg +934.6 avg_win +2981.6 avg_loss -985.7; trail_armed 0/0%; skipped 217 (no_break×202, late_short×15)
- **exits:** flatten45 / tp63 / sl110 / timeout1
- **entries:** timeout_market 130, ema_touch 89
- **vs KEEP (resume_closes=1, ema=34):** 219t 48.4% +204670 PF2.84 → **identical book** (n/win%/pts/PF/exits/entries)
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still weaker on win%/pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T064512Z_dcb02ce2.json
- **Conclusion:** **REJECT — keep resume_closes=1** on asia 1-6 / max_wait=12 / max_break=15 / ema=34 research KEEP. Raising to 2 is a no-op. Next: **one-knob pullback_mode=off** (deferred; was preferred) on KEEP, then wait_from_break=false / remaining entry knobs. Prefer PF; report pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob pullback_mode=off on asia 1-6 / max_wait=12 / max_break=15 / SL1000/TP4000 ema=34 (2025+, seed A_m entry) - REJECT (redundant retest)
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=12; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; wick=false; **pullback=off** (was preferred); **ema=34**; use_higher_close=false; resume_closes=1; skip_late=7; workers=4
- **n / metrics:** 234 trades, 31.6% wins (74W/160L), +55753.2 pts, **PF 1.36**; exits flatten36/sl155/tp42/timeout1; entries **break_close 234** (no ema/timeout)
- **vs KEEP (pullback preferred, ema=34):** 219t 48.4% +204670 PF2.84 → **n +15 / win% −15.1pp / pts −149k / PF −1.48**
- **Note:** Mistaken re-kick after resume_closes=2; Igor queue says skip redundant pullback=off (already hard-rejected on ema=23 seed). Same absolute book as prior pullback=off.
- **Result:** `C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T071929Z_a02c1cb7.json`
- **Conclusion:** **REJECT - keep pullback_mode=preferred.** Next per Igor queue: **one-knob max_wait_candles=13** (vs wait12 KEEP) on ema=34 KEEP seed.

### 2026-09-12 Asia MARKET one-knob max_wait_candles=13 on asia 1-6 / max_wait=12 KEEP / max_break=15 / SL1000/TP4000 ema=34 (2025+, seed A_m entry) - KEEP vs wait12
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=13** (was 12); trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=34**; skip_late 7/3000; flatten 22; hold 14; break_on_wick false; use_higher_close false; resume_closes=1; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 218 trades, 49.5% wins (108W/110L), +213846.8 pts, **PF 2.97**; avg +980.9 avg_win +2983.6 avg_loss -985.3; trail_armed 0/0%; skipped 218
- **exits:** flatten46 / tp64 / sl107 / timeout1
- **entries:** timeout_market 126, ema_touch 92 (wait12 KEEP: timeout_market 130 / ema_touch 89); skipped 218 (no_breakx202, late_shortx16)
- **vs KEEP (max_wait=12, ema=34):** 219t 48.4% +204670 PF2.84 → **n −1 / win% +1.1pp / pts +9177 / PF +0.13** — improves PF and pts (primary score); mild n dip
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → still weaker on win%; pts now slightly ahead of A_m 2025+ sum (+213.8k vs +210.8k) but win% far lower — not an A_m challenger on quality
- **Result:** `C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T075440Z_365b6ca5.json`
- **Conclusion:** **KEEP — promote max_wait_candles=13** on asia 1-6 / max_break=15 / ema=34 research KEEP (218t 49.5% +213847 **PF2.97**). Next per Igor queue: **EMA grid one-knob starting ema_period=9** (then 10/14/18/20; keep 34 as champ until beaten) on wait=13 KEEP. Prefer PF+pts. Ask before any reaktor push.

﻿### 2026-09-12 Asia MARKET one-knob ema_period=9 on asia 1-6 / max_wait=13 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=13**; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=9** (was 34); skip_late 7/3000; flatten 22; hold 14; break_on_wick false; use_higher_close false; resume_closes=1; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 225 trades, 33.8% wins (76W/149L), +69813.9 pts, **PF 1.48**; avg +310.3 avg_win +2842.1 avg_loss −981.1; trail_armed 0/0%; skipped 211 (no_break×202, late_short×9)
- **exits:** flatten39 / tp41 / sl145
- **entries:** timeout_market 21, ema_touch 204 (KEEP ema34: timeout_market 126 / ema_touch 92 — fast EMA floods ema_touch, starves timeout fills)
- **by_month (compact):** 2025-01 12t 66.7% +3231 PF1.81; 2025-02 10t 50.0% +8048 PF2.93; 2025-03 9t 55.6% +2883 PF1.72; 2025-04 8t 50.0% +12000 PF4.00; 2025-05 13t 23.1% +212 PF1.02; 2025-06 9t 33.3% +41 PF1.01; 2025-07 11t 45.5% +5416 PF2.34; 2025-08 8t 37.5% −2049 PF0.59; 2025-09 13t 23.1% −4320 PF0.57; 2025-10 14t 35.7% +9463 PF2.05; 2025-11 13t 23.1% +2000 PF1.20; 2025-12 11t 27.3% +2274 PF1.28; 2026-01 11t 18.2% −1000 PF0.89; 2026-02 10t 10.0% −5000 PF0.44; 2026-03 11t 27.3% +4000 PF1.50; 2026-04 9t 33.3% +4409 PF1.73; 2026-05 14t 42.9% +16000 PF3.00; 2026-06 12t 41.7% +10756 PF2.54; 2026-07 14t 7.1% −10552 PF0.19; 2026-08 9t 55.6% +16000 PF5.00; 2026-09 4t 0.0% −4000 PF0.00
- **vs KEEP (max_wait=13, ema=34):** 218t 49.5% +213847 PF2.97 → **n +7 / win% −15.7pp / pts −144033 / PF −1.49** — hard reject on PF+pts
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → far worse on win%/pts/PF
- **Result:** `C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T082755Z_efa3a4c7.json`
- **Conclusion:** **REJECT — keep ema_period=34** on asia 1-6 / max_wait=13 / max_break=15 research KEEP. Prefer PF+pts (1.48 << 2.97). Next per Igor queue: **one-knob ema_period=10** (grid 9 REJECT / 10 next / 14 / 18 / 20; 34 remains champ). Prefer PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia MARKET one-knob ema_period=10 on asia 1-6 / max_wait=13 / max_break=15 / SL1000/TP4000 (2025+, seed A_m entry) - REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01 (21 months)
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=13**; trail_arm_mode=off; **SL fixed 1000 / TP fixed 4000**; **asia 1-6**; min_asia 300; break ±200; **max_break=15**; pullback preferred; **ema_period=10** (was 34); skip_late 7/3000; flatten 22; hold 14; break_on_wick false; use_higher_close false; resume_closes=1; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 223 trades, 36.8% wins (82W/141L), +98885.9 pts, **PF 1.72**; avg +443.4 avg_win +2889.6 avg_loss −979.2; trail_armed 0/0%; skipped 213 (no_break×202, late_short×11)
- **exits:** flatten41 / tp45 / sl137
- **entries:** timeout_market 26, ema_touch 197 (KEEP ema34: timeout_market 126 / ema_touch 92 — fast EMA floods ema_touch, starves timeout fills)
- **by_month (compact):** 2025-01 12t 66.7% +3367 PF1.84; 2025-02 10t 50.0% +8025 PF2.94; 2025-03 9t 55.6% +2399 PF1.60; 2025-04 8t 50.0% +12000 PF4.00; 2025-05 12t 25.0% +1296 PF1.14; 2025-06 8t 25.0% −921 PF0.85; 2025-07 11t 45.5% +5572 PF2.42; 2025-08 8t 37.5% −2382 PF0.52; 2025-09 13t 23.1% −4240 PF0.58; 2025-10 14t 42.9% +13162 PF2.65; 2025-11 13t 38.5% +10178 PF2.27; 2025-12 11t 27.3% +2346 PF1.29; 2026-01 11t 18.2% −1000 PF0.89; 2026-02 10t 10.0% −5000 PF0.44; 2026-03 11t 36.4% +9000 PF2.29; 2026-04 9t 33.3% +4504 PF1.75; 2026-05 14t 50.0% +21000 PF4.00; 2026-06 12t 41.7% +10835 PF2.55; 2026-07 14t 21.4% −3254 PF0.70; 2026-08 9t 55.6% +16000 PF5.00; 2026-09 4t 0.0% −4000 PF0.00
- **vs KEEP (max_wait=13, ema=34):** 218t 49.5% +213847 PF2.97 → **n +5 / win% −12.7pp / pts −114961 / PF −1.25** — hard reject on PF+pts
- **vs A_m 2025+ (SL/TP2000 trail off, market):** 232t 74.1% +210808 → far worse on win%/pts/PF
- **Result:** `C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T085537Z_5d78dc58.json`
- **Conclusion:** **REJECT — keep ema_period=34** on asia 1-6 / max_wait=13 / max_break=15 research KEEP. Prefer PF+pts (1.72 << 2.97). Next per Igor queue: **one-knob ema_period=14** (grid 9 REJECT / 10 REJECT / 14 next / 18 / 20; 34 remains champ). Prefer PF+pts. Ask before any reaktor push.


### 2026-09-12 Asia one-knob ema_period=14 (wait13 KEEP seed) — REJECT vs ema=34
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=13; trail_arm_mode=off; **SL1000 / TP4000**; asia 1–6; min_asia 300; break ±200; **max_break 15 LOCKED**; pullback preferred; wick false; **ema_period=14** (was 34 KEEP); skip_late 7/3000; use_higher_close false; resume_closes 1; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 219 trades, 42.5% wins (93W/126L), +151459.5 pts, **PF 2.22**; avg +691.6 avg_win +2962.3 avg_loss -984.4; trail_armed 0/0.0%; skipped 217 (no_break×202, late_short×15)
- **exits:** sl123 / flatten39 / tp56 / timeout1
- **entries:** timeout_market 55, ema_touch 164 (vs KEEP timeout 126 / ema_touch 92 — faster EMA floods touch fills)
- **by_month (compact):** 2025-01 11t 63.6% +2655 PF1.66; 2025-02 11t 54.5% +8912 PF3.21; 2025-03 9t 66.7% +5190 PF2.73; 2025-04 9t 55.6% +16000 PF5.00; 2025-05 12t 41.7% +5032 PF1.72; 2025-06 9t 33.3% +3315 PF1.55; 2025-07 10t 50.0% +4909 PF2.14; 2025-08 7t 42.9% -771 PF0.79; 2025-09 12t 25.0% -3046 PF0.66; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 30.8% +5598 PF1.62; 2025-12 11t 27.3% +4000 PF1.50; 2026-01 11t 18.2% -1000 PF0.89; 2026-02 10t 20.0% +0 PF1.00; 2026-03 11t 36.4% +9000 PF2.29; 2026-04 9t 22.2% +1000 PF1.14; 2026-05 14t 57.1% +26000 PF5.33; 2026-06 11t 54.5% +16616 PF4.32; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 66.7% +21000 PF8.00; 2026-09 4t 50.0% +2305 PF2.15
- **vs KEEP (max_wait=13 ema=34):** 218t 49.5% +213847 PF2.97 → **n +1 / win% −7.0pp / pts −62387 / PF −0.75**
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T093443Z_aca4a730.json
- **Conclusion:** **REJECT — keep ema=34.** Faster EMA floods ema_touch and starves timeout_market. Grid so far: 9 REJECT / 10 REJECT / **14 REJECT** / 18 next / 20. Next: **one-knob ema_period=18** on wait13 KEEP seed. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob ema_period=18 (wait13 KEEP seed, was 34) — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=13; **max_break=15 LOCKED**; trail off; **SL1000 / TP4000**; asia **1–6**; min_asia 300; break ±200; wick=false; pullback preferred; **ema 18**; skip_late 7; use_higher_close=false; resume_closes=1; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 217 trades, 46.1% wins (100W/117L), +177354.1 pts, **PF 2.53**; avg +817.3 avg_win +2932.8 avg_loss -990.8; trail_armed 0
- **exits:** flatten43 / tp58 / sl115 / timeout1
- **entries:** timeout_market 76, ema_touch 141
- **skipped:** 219 (no_break×202, late_short×17)
- **by_month (compact):** 2025-01 11t 72.7% +5676 PF2.89; 2025-02 11t 72.7% +11758 PF4.92; 2025-03 9t 66.7% +5606 PF2.87; 2025-04 9t 44.4% +11000 PF3.20; 2025-05 11t 45.5% +5784 PF1.96; 2025-06 10t 40.0% +7024 PF2.17; 2025-07 10t 50.0% +5078 PF2.18; 2025-08 5t 40.0% +226 PF1.09; 2025-09 13t 38.5% +1319 PF1.16; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 23.1% +2000 PF1.20; 2025-12 10t 30.0% +5000 PF1.71; 2026-01 11t 18.2% −1000 PF0.89; 2026-02 10t 40.0% +10000 PF2.67; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 22.2% +1000 PF1.14; 2026-05 14t 64.3% +28158 PF6.63; 2026-06 11t 54.5% +16675 PF4.33; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 66.7% +21000 PF8.00; 2026-09 4t 50.0% +2305 PF2.15
- **vs KEEP wait13 ema34:** 218t 49.5% +213847 PF2.97 → **n −1 / win% −3.4pp / pts −36.5k / PF −0.44**; ema_touch flood 141 vs 92, timeout starved 76 vs 126
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T095154Z_abfae1ea.json
- **Conclusion:** **REJECT.** Shorter EMA still floods ema_touch and loses PF+pts vs champ 34. Grid so far: 9/10/14/18 REJECT; 34 remains champ. Next: **one-knob ema_period=20**, then use_higher_close true/false on best EMA. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob ema_period=20 (wait13 KEEP seed, was 34) — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=13; **max_break=15 LOCKED**; trail off; **SL1000 / TP4000**; asia **1–6**; min_asia 300; break ±200; wick=false; pullback preferred; **ema 20**; skip_late 7; use_higher_close=false; resume_closes=1; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 218 trades, 46.3% wins (101W/117L), +181965.9 pts, **PF 2.58**; avg +834.7 avg_win +2945.2 avg_loss -987.2; trail_armed 0
- **exits:** flatten44 / tp59 / sl114 / timeout1
- **entries:** timeout_market 84, ema_touch 134 (KEEP ema34: timeout 126 / ema_touch 92)
- **skipped:** 218 (no_break×202, late_short×16)
- **by_month (compact):** 2025-01 11t 72.7% +5813 PF2.94; 2025-02 12t 66.7% +10896 PF3.72; 2025-03 9t 66.7% +5798 PF2.93; 2025-04 9t 44.4% +11000 PF3.20; 2025-05 11t 45.5% +6047 PF2.01; 2025-06 10t 40.0% +6265 PF2.04; 2025-07 11t 45.5% +4421 PF1.91; 2025-08 5t 40.0% +218 PF1.08; 2025-09 13t 38.5% +1602 PF1.20; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 23.1% +2000 PF1.20; 2025-12 9t 33.3% +6000 PF2.00; 2026-01 11t 18.2% −1000 PF0.89; 2026-02 10t 40.0% +10000 PF2.67; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 33.3% +6000 PF2.00; 2026-05 14t 64.3% +28158 PF6.63; 2026-06 11t 54.5% +16698 PF4.34; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 66.7% +21000 PF8.00; 2026-09 4t 50.0% +2305 PF2.15
- **vs KEEP wait13 ema34:** 218t 49.5% +213847 PF2.97 → **n 0 / win% −3.2pp / pts −31881 / PF −0.39**; milder than 9–18 but still loses PF+pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T120954Z_ad135b10.json
- **Conclusion:** **REJECT.** EMA grid complete: 9/10/14/18/20 all REJECT; **34 remains champ**. Next per Igor queue: **use_higher_close=true** (retest on wait13/ema34 KEEP even if prior reject on wait12), then **use_higher_close=false** confirm. Score PF+pts. Ask before any reaktor push.


### 2026-09-12 Asia one-knob use_higher_close=true (wait13/ema34 KEEP seed, was false) — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=13; **max_break=15 LOCKED**; trail off; **SL1000 / TP4000**; asia **1–6**; min_asia 300; break ±200; wick=false; pullback preferred; **ema 34**; skip_late 7; **use_higher_close=true** (retest on wait13 KEEP); resume_closes=1; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 234 trades, 33.3% wins (78W/156L), +61158.3 pts, **PF 1.40**; avg +261.4 avg_win +2758.4 avg_loss -987.1; trail_armed 0
- **exits:** flatten40 / sl153 / tp40 / timeout1
- **entries:** lower_close 95, higher_close 117, ema_touch 22 (KEEP wait13 ema34: timeout_market 126 / ema_touch 92 — higher/lower_close flood starves timeout/ema)
- **skipped:** no_breakx202
- **by_month (compact):** 2025-01 13t 76.9% +6808 PF3.27; 2025-02 12t 41.7% +1357 PF1.19; 2025-03 9t 33.3% +639 PF1.12; 2025-04 10t 50.0% +15000 PF4.00; 2025-05 13t 23.1% -274 PF0.97; 2025-06 12t 41.7% +5928 PF1.85; 2025-07 11t 45.5% +2796 PF1.52; 2025-08 8t 25.0% -2925 PF0.51; 2025-09 14t 28.6% -3006 PF0.70; 2025-10 14t 42.9% +14310 PF2.79; 2025-11 13t 7.7% -8000 PF0.33; 2025-12 11t 27.3% +4000 PF1.50; 2026-01 11t 18.2% -1000 PF0.89; 2026-02 10t 0.0% -10000 PF0.00; 2026-03 11t 9.1% -6000 PF0.40; 2026-04 9t 22.2% +1000 PF1.14; 2026-05 14t 57.1% +23231 PF4.87; 2026-06 12t 33.3% +3613 PF1.45; 2026-07 14t 14.3% -8837 PF0.26; 2026-08 9t 66.7% +21000 PF8.00; 2026-09 4t 25.0% +1517 PF1.61
- **vs KEEP wait13 ema34 use_higher_close=false:** 218t 49.5% +213847 PF2.97 → **n +16 / win% -16.2pp / pts -152689 / PF -1.57**
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T123726Z_da9df9a6.json
- **Conclusion:** **REJECT — keep use_higher_close=false.** Same hard miss as wait12 retest (PF1.40 << 2.97). Igor queue item 4: still need **use_higher_close=false** confirm on wait13/ema34 KEEP. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia use_higher_close=false confirm (wait13/ema34 KEEP seed) — KEEP confirmed
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=13; **max_break=15 LOCKED**; trail off; **SL1000 / TP4000**; asia **1–6**; min_asia 300; break ±200; wick=false; pullback preferred; **ema 34**; skip_late 7; **use_higher_close=false** (confirm); resume_closes=1; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 218 trades, 49.5% wins (108W/110L), +213846.8 pts, **PF 2.97**; avg +980.9 avg_win +2983.6 avg_loss -985.3; trail_armed 0
- **exits:** flatten46 / tp64 / sl107 / timeout1
- **entries:** timeout_market 126, ema_touch 92
- **skipped:** 218 (no_break×202, late_short×16)
- **vs KEEP wait13 ema34:** identical within rounding (218t 49.5% +213847 PF2.97) → **n 0 / win% 0 / pts ~0 / PF 0**
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T125742Z_56a3cdba.json
- **Conclusion:** **KEEP confirmed — use_higher_close=false.** Igor queue items 1–4 done (max_break=15 locked; max_wait=13 KEEP; EMA 9/10/14/18/20 all REJECT vs 34; higher_close true REJECT / false KEEP). **Queue idle** pending next Igor knobs (dynamic 12m-avg TP/SL / Tuesday higher-lower-close gate). No next kick. Score PF+pts. Ask before any reaktor push.


### 2026-09-12 Asia one-knob ema_period=30 (wait13 KEEP seed, was 34) — KEEP / promote
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=13; trail_arm_mode=off; **SL1000 / TP4000**; asia **1-6**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; wick false; **ema_period=30** (was 34); skip_late 7/3000; use_higher_close false; resume_closes 1; flatten 22; hold 14; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 217 trades, 50.2% wins (109W/108L), +219949.8 pts, **PF 3.07**; avg +1013.6 avg_win +2993.9 avg_loss -985.1; trail_armed 0; skipped 219 (no_break×202, late_short×17)
- **exits:** sl105 / flatten46 / tp65 / timeout1
- **entries:** timeout_market 116, ema_touch 101 (prior KEEP ema34: timeout 126 / ema_touch 92)
- **vs KEEP wait13 ema34:** 218t 49.5% +213847 PF2.97 → **n −1 / win% +0.7pp / pts +6103 / PF +0.10** — not a thin-book mirage (n≈same)
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T152905Z_5191ac50.json
- **Conclusion:** **KEEP / promote — new research KEEP ema_period=30** (PF3.07 / +219950). Prior ema34 demoted. Grid: lower EMA 9/10/14/18/20 REJECT; **30 KEEP**; next **one-knob ema_period=32**, then 40. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob ema_period=32 (was 30 KEEP) — KEEP / promote
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** asia 1–6; max_break=15 LOCKED; max_wait=13; **ema_period=32**; min_asia 300; min_break ±200; wick=false; pullback preferred; skip_late=7; use_higher_close=false; resume_closes=1; wait_from_break=true; **timeout_action=market**; SL1000/TP4000 trail off; workers=4
- **n / metrics:** 217 trades, 50.7% wins (110W/107L), +224604.5 pts, **PF 3.13**; avg +1035.0 avg_win +2999.7 avg_loss −984.7; trail_armed 0/0.0%; skipped 219 (no_break×202, late_short×17)
- **exits:** sl104 / flatten46 / tp66 / timeout1
- **entries:** timeout_market 121 / ema_touch 96
- **by_month (compact):** 2025-01 11t 81.8% +8799 PF5.4; 2025-02 11t 63.6% +10798 PF3.7; 2025-03 8t 75.0% +6524 PF4.26; 2025-04 9t 55.6% +12831 PF4.21; 2025-05 11t 36.4% +6040 PF1.86; 2025-06 10t 60.0% +9843 PF3.46; 2025-07 11t 45.5% +4658 PF1.96; 2025-08 5t 40.0% +456 PF1.18; 2025-09 13t 38.5% +2528 PF1.32; 2025-10 13t 61.5% +27000 PF6.4; 2025-11 13t 23.1% +2000 PF1.2; 2025-12 9t 55.6% +16000 PF5.0; 2026-01 11t 45.5% +14000 PF3.33; 2026-02 10t 50.0% +15000 PF4.0; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 44.4% +9177 PF2.84; 2026-05 14t 71.4% +33232 PF9.31; 2026-06 12t 50.0% +15668 PF3.61; 2026-07 13t 38.5% +7746 PF1.97; 2026-08 9t 44.4% +11000 PF3.2; 2026-09 4t 25.0% -2695 PF0.1
- **regime rollups:** 2025 124t ~52.4% +107477; 2026 93t ~48.4% +117127; 2025+ 217t ~50.7% +224604
- **vs prior KEEP ema=30:** 217t 50.2% +219950 PF3.07 → **n 0 / win% +0.5pp / pts +4655 / PF +0.06** — not thin-book
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T154834Z_f51ed9d7.json
- **Conclusion:** **KEEP / promote ema=32 over 30.** New research KEEP: ema=32 (asia 1-6 / max_wait=13 / max_break=15). Next: one-knob **ema_period=40**, then ema=36; pick EMA winner by PF+pts; then asia_end=7; then max_wait {10,12,13}.

### 2026-09-12 Asia one-knob ema_period=40 (was 32 KEEP) — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** asia 1–6; max_break=15 LOCKED; max_wait=13; **ema_period=40**; min_asia 300; min_break ±200; wick=false; pullback preferred; skip_late=7; use_higher_close=false; resume_closes=1; wait_from_break=true; **timeout_action=market**; SL1000/TP4000 trail off; workers=4
- **n / metrics:** 221 trades, 45.2% wins (100W/121L), +172984.9 pts, **PF 2.45**; avg +782.7 avg_win +2923.5 avg_loss -986.5; trail_armed 0/0.0%; skipped 215 (no_break×202, late_short×13)
- **exits:** sl118 / flatten46 / tp56 / timeout1
- **entries:** timeout_market 138 / ema_touch 83 (KEEP ema32: timeout 121 / ema_touch 96)
- **by_month (compact):** 2025-01 12t 75.0% +7684 PF3.56; 2025-02 11t 63.6% +10973 PF3.74; 2025-03 8t 75.0% +6818 PF4.41; 2025-04 9t 44.4% +11000 PF3.20; 2025-05 12t 33.3% +3690 PF1.46; 2025-06 10t 60.0% +9942 PF3.49; 2025-07 11t 45.5% +4747 PF1.98; 2025-08 6t 33.3% -544 PF0.84; 2025-09 13t 38.5% +2562 PF1.32; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 23.1% +2000 PF1.20; 2025-12 10t 40.0% +10000 PF2.67; 2026-01 11t 36.4% +9000 PF2.29; 2026-02 10t 40.0% +10000 PF2.67; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 44.4% +9177 PF2.84; 2026-05 14t 64.3% +28307 PF6.66; 2026-06 12t 41.7% +10578 PF2.51; 2026-07 13t 23.1% -2254 PF0.77; 2026-08 9t 33.3% +6000 PF2.00; 2026-09 4t 25.0% -2695 PF0.10
- **vs KEEP ema=32:** 217t 50.7% +224605 PF3.13 → **n +4 / win% −5.5pp / pts −51620 / PF −0.68** — not thin-book; slower EMA loses PF+pts hard
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T161756Z_eff90012.json
- **Conclusion:** **REJECT — keep ema=32.** Grid so far: 9–20 REJECT; 30 demoted by 32; **32 KEEP**; 40 REJECT; next **one-knob ema_period=36**, then pick EMA winner by PF+pts; then asia_end=7; then max_wait {10,12,13}. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob ema_period=36 (was 32 KEEP) — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** asia 1–6; max_break=15 LOCKED; max_wait=13; **ema_period=36**; min_asia 300; min_break ±200; wick=false; pullback preferred; skip_late=7; use_higher_close=false; resume_closes=1; wait_from_break=true; **timeout_action=market**; SL1000/TP4000 trail off; workers=4
- **n / metrics:** 221 trades, 47.1% wins (104W/117L), +190829.8 pts, **PF 2.65**; avg +863.5 avg_win +2944.3 avg_loss -986.2; trail_armed 0/0.0%; skipped 215 (no_break×202, late_short×13)
- **exits:** sl114 / flatten46 / tp60 / timeout1
- **entries:** timeout_market 132 / ema_touch 89 (KEEP ema32: timeout 121 / ema_touch 96)
- **by_month (compact):** 2025-01 12t 83.3% +9677 PF5.84; 2025-02 11t 63.6% +10904 PF3.73; 2025-03 8t 75.0% +6678 PF4.34; 2025-04 9t 44.4% +11000 PF3.20; 2025-05 12t 33.3% +5081 PF1.64; 2025-06 10t 60.0% +9888 PF3.47; 2025-07 11t 45.5% +4705 PF1.97; 2025-08 6t 33.3% -585 PF0.83; 2025-09 13t 38.5% +2385 PF1.30; 2025-10 13t 53.8% +22000 PF4.67; 2025-11 13t 23.1% +2000 PF1.20; 2025-12 10t 50.0% +15000 PF4.00; 2026-01 11t 36.4% +9000 PF2.29; 2026-02 10t 40.0% +10000 PF2.67; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 44.4% +9177 PF2.84; 2026-05 14t 64.3% +28267 PF6.65; 2026-06 12t 41.7% +10602 PF2.51; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 44.4% +11000 PF3.20; 2026-09 4t 25.0% -2695 PF0.10
- **vs KEEP ema=32:** 217t 50.7% +224605 PF3.13 → **n +4 / win% −3.6pp / pts −33775 / PF −0.48** — not thin-book; mid-band EMA loses PF+pts
- **Result:** C:\\Users\\user\\strateg\\results\\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T164454Z_ff83ff5f.json
- **Conclusion:** **REJECT — keep ema=32.** EMA grid closed: 9–20 REJECT; 30 demoted by 32; **32 KEEP / EMA winner**; 34 demoted; 36 REJECT; 40 REJECT. Next: **one-knob asia_end_hour=7** (asia 1–7) on ema=32 KEEP seed; then max_wait {10,12,13}. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob asia_end_hour=7 (asia 1-7 on ema=32 KEEP) — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** asia **1–7**; max_break=15 LOCKED; max_wait=13; **ema_period=32**; min_asia 300; min_break ±200; wick=false; pullback preferred; skip_late=7; use_higher_close=false; resume_closes=1; wait_from_break=true; **timeout_action=market**; SL1000/TP4000 trail off; workers=4
- **n / metrics:** 226 trades, 48.2% wins (109W/117L), +198480.4 pts, **PF 2.75**; avg +878.2 avg_win +2858.9 avg_loss -967.0; trail_armed 0/0.0%; skipped 210 (no_break×194, late_short×16)
- **exits:** flatten52 / sl112 / tp61 / timeout1
- **entries:** timeout_market 122 / ema_touch 104 (KEEP asia1-6: timeout 121 / ema_touch 96)
- **by_month (compact):** 2025-01 11t 90.9% +10429 PF11.43; 2025-02 11t 63.6% +8253 PF3.06; 2025-03 13t 46.2% +2020 PF1.32; 2025-04 9t 66.7% +17831 PF6.94; 2025-05 10t 40.0% +7686 PF2.28; 2025-06 9t 66.7% +8262 PF3.75; 2025-07 11t 45.5% +4214 PF1.93; 2025-08 7t 57.1% +1689 PF1.72; 2025-09 13t 46.2% +7054 PF2.01; 2025-10 13t 38.5% +10310 PF2.29; 2025-11 12t 25.0% +3000 PF1.33; 2025-12 10t 50.0% +13788 PF3.76; 2026-01 14t 42.9% +16000 PF3.00; 2026-02 9t 55.6% +16000 PF5.00; 2026-03 12t 41.7% +13000 PF2.86; 2026-04 12t 41.7% +11177 PF2.60; 2026-05 15t 66.7% +32232 PF7.45; 2026-06 10t 30.0% +5000 PF1.71; 2026-07 11t 27.3% +3232 PF1.46; 2026-08 9t 33.3% +6000 PF2.00; 2026-09 5t 40.0% +1305 PF1.44
- **vs KEEP asia 1–6 ema=32:** 217t 50.7% +224605 PF3.13 → **n +9 / win% −2.5pp / pts −26125 / PF −0.38** — not thin-book; wider Asia window loses PF+pts
- **Result:** C:\\Users\\user\\strateg\\results\\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T171918Z_7e3a6991.json
- **Conclusion:** **REJECT — keep asia 1–6.** Asia-window winner remains **1–6** on ema=32. Next: **one-knob max_wait_candles=10** (then 12, then re-check 13) on asia 1–6 / ema=32 KEEP seed. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob max_wait=10 (was 13 KEEP) on asia 1–6 / ema=32 — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=market; **max_wait=10**; trail_arm_mode=off; SL1000/TP4000; asia **1–6**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; **ema=32**; skip_late 7; wick=false; use_higher_close=false; resume_closes=1; workers=4
- **n / metrics:** 224 trades, 46.4% wins (104W/120L), +190938.2 pts, **PF 2.63**; skipped 212
- **exits:** {'flatten': 45, 'sl': 116, 'tp': 62, 'timeout': 1}
- **entries:** timeout_market 147 / ema_touch 77
- **by_month (compact):** 2025-01 12t 83.3% +10136 PF6.07; 2025-02 11t 54.5% +8401 PF2.68; 2025-03 9t 66.7% +5524 PF2.84; 2025-04 10t 50.0% +11831 PF3.37; 2025-05 11t 36.4% +6040 PF1.86; 2025-06 10t 60.0% +9843 PF3.46; 2025-07 11t 45.5% +4658 PF1.96; 2025-08 7t 28.6% -644 PF0.82; 2025-09 14t 28.6% -2801 PF0.72; 2025-10 13t 61.5% +27000 PF6.4; 2025-11 13t 15.4% -3000 PF0.73; 2025-12 10t 50.0% +15000 PF4.0; 2026-01 11t 36.4% +9000 PF2.29; 2026-02 10t 50.0% +15000 PF4.0; 2026-03 11t 45.5% +14000 PF3.33; 2026-04 9t 33.3% +6000 PF2.0; 2026-05 14t 64.3% +28232 PF6.65; 2026-06 12t 50.0% +15668 PF3.61; 2026-07 13t 30.8% +2746 PF1.31; 2026-08 9t 44.4% +11000 PF3.2; 2026-09 4t 25.0% -2695 PF0.1
- **vs KEEP max_wait=13 ema=32 asia 1–6:** 217t 50.7% +224605 PF3.13 → **n +7 / win% -4.3pp / pts -33667 / PF -0.50** — not thin-book; shorter wait loses PF+pts
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T175754Z_c064be01.json
- **Conclusion:** **REJECT — keep max_wait=13.** Next: **one-knob max_wait_candles=12** on asia 1–6 / ema=32, then re-check 13; then max_wait {10,12,13} on asia 1–7. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia one-knob max_wait=12 (was 13 KEEP) on asia 1–6 / ema=32 — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=market; **max_wait=12**; trail_arm_mode=off; SL1000/TP4000; asia **1–6**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; **ema=32**; skip_late 7; wick=false; use_higher_close=false; resume_closes=1; workers=4
- **n / metrics:** 218 trades, 49.5% wins (108W/110L), +215427.9 pts, **PF 2.99**; skipped 218
- **exits:** {'sl': 107, 'flatten': 45, 'tp': 65, 'timeout': 1}
- **entries:** timeout_market 125 / ema_touch 93
- **by_month (compact):** 2025-01 11t 81.8% +8799 PF5.4 · 2025-02 11t 63.6% +10798 PF3.7 · 2025-03 8t 75.0% +6524 PF4.26 · 2025-04 10t 50.0% +11831 PF3.37 · 2025-05 11t 36.4% +6040 PF1.86 · 2025-06 10t 60.0% +9843 PF3.46 · 2025-07 11t 45.5% +4658 PF1.96 · 2025-08 5t 40.0% +456 PF1.18 · 2025-09 13t 38.5% +2528 PF1.32 · 2025-10 13t 61.5% +27000 PF6.4 · 2025-11 13t 23.1% +2000 PF1.2 · 2025-12 9t 55.6% +16000 PF5.0 · 2026-01 11t 45.5% +14000 PF3.33 · 2026-02 10t 50.0% +15000 PF4.0 · 2026-03 11t 45.5% +14000 PF3.33 · 2026-04 9t 33.3% +6000 PF2.0 · 2026-05 14t 71.4% +33232 PF9.31 · 2026-06 12t 50.0% +15668 PF3.61 · 2026-07 13t 30.8% +2746 PF1.31 · 2026-08 9t 44.4% +11000 PF3.2 · 2026-09 4t 25.0% -2695 PF0.1
- **vs KEEP max_wait=13 ema=32 asia 1–6:** 217t 50.7% +224605 PF3.13 → **n +1 / win% -1.2pp / pts -9177 / PF -0.14** — not thin-book; wait12 loses PF+pts vs wait13
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T182253Z_3fdc0549.json
- **Conclusion:** **REJECT — keep max_wait=13.** Next: **re-check max_wait_candles=13** on asia 1–6 / ema=32 (apples-to-apples), then max_wait {10,12,13} on asia 1–7. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia re-check max_wait=13 on asia 1–6 / ema=32 — KEEP / confirms
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=market; **max_wait=13**; trail_arm_mode=off; SL1000/TP4000; asia **1–6**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; **ema=32**; skip_late 7; wick=false; use_higher_close=false; resume_closes=1; workers=4
- **n / metrics:** 217 trades, 50.7% wins (110W/107L), +224604.5 pts, **PF 3.13**; skipped 219
- **exits:** {'sl': 104, 'flatten': 46, 'tp': 66, 'timeout': 1}
- **entries:** timeout_market 121 / ema_touch 96
- **by_month (compact):** 2025-01 11t 81.8% +8799 PF5.4 · 2025-02 11t 63.6% +10798 PF3.7 · 2025-03 8t 75.0% +6524 PF4.26 · 2025-04 9t 55.6% +12831 PF4.21 · 2025-05 11t 36.4% +6040 PF1.86 · 2025-06 10t 60.0% +9843 PF3.46 · 2025-07 11t 45.5% +4658 PF1.96 · 2025-08 5t 40.0% +456 PF1.18 · 2025-09 13t 38.5% +2528 PF1.32 · 2025-10 13t 61.5% +27000 PF6.4 · 2025-11 13t 23.1% +2000 PF1.2 · 2025-12 9t 55.6% +16000 PF5.0 · 2026-01 11t 45.5% +14000 PF3.33 · 2026-02 10t 50.0% +15000 PF4.0 · 2026-03 11t 45.5% +14000 PF3.33 · 2026-04 9t 44.4% +9177 PF2.84 · 2026-05 14t 71.4% +33232 PF9.31 · 2026-06 12t 50.0% +15668 PF3.61 · 2026-07 13t 38.5% +7746 PF1.97 · 2026-08 9t 44.4% +11000 PF3.2 · 2026-09 4t 25.0% -2695 PF0.1
- **vs KEEP max_wait=13 ema=32 asia 1–6:** 217t 50.7% +224605 PF3.13 → **n +0 / win% +0.0pp / pts -0 / PF +0.00** — not thin-book; re-check matches KEEP within rounding
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T184850Z_fcd8d81f.json
- **Conclusion:** **KEEP / confirms max_wait=13.** Asia 1–6 wait grid done (10 REJECT PF2.63; 12 REJECT PF2.99; 13 KEEP PF3.13). Next: max_wait {10,12,13} on asia **1–7** / ema=32. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia max_wait=10 on asia 1–7 / ema=32 — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=market; **max_wait=10**; trail_arm_mode=off; SL1000/TP4000; asia **1–7**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; **ema=32**; skip_late 7; wick=false; use_higher_close=false; resume_closes=1; workers=4
- **n / metrics:** 232 trades, 45.7% wins (106W/126L), +177420.3 pts, **PF 2.45**; skipped 204
- **exits:** {'flatten': 52, 'sl': 121, 'tp': 58, 'timeout': 1}
- **entries:** timeout_market 151 / ema_touch 81
- **by_month (compact):** 2025-01 13t 84.6% +10766 PF6.38 · 2025-02 11t 54.5% +5856 PF2.17 · 2025-03 13t 46.2% +2020 PF1.32 · 2025-04 9t 66.7% +17831 PF6.94 · 2025-05 10t 40.0% +7686 PF2.28 · 2025-06 9t 66.7% +8262 PF3.75 · 2025-07 11t 45.5% +4214 PF1.93 · 2025-08 9t 44.4% -311 PF0.93 · 2025-09 13t 46.2% +7054 PF2.01 · 2025-10 13t 38.5% +10310 PF2.29 · 2025-11 12t 16.7% -2000 PF0.8 · 2025-12 11t 45.5% +12788 PF3.13 · 2026-01 14t 35.7% +11000 PF2.22 · 2026-02 9t 55.6% +16000 PF5.0 · 2026-03 12t 41.7% +13000 PF2.86 · 2026-04 12t 41.7% +11177 PF2.6 · 2026-05 15t 60.0% +27232 PF5.54 · 2026-06 10t 30.0% +5000 PF1.71 · 2026-07 12t 25.0% +2232 PF1.28 · 2026-08 9t 33.3% +6000 PF2.0 · 2026-09 5t 40.0% +1305 PF1.44
- **vs KEEP max_wait=13 ema=32 asia 1–6:** 217t 50.7% +224605 PF3.13 → **n +15 / win% -5.0pp / pts -47185 / PF -0.68** — not thin-book
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T191539Z_e94cf018.json
- **Conclusion:** **REJECT max_wait=10 on asia 1–7.** Worse PF+pts vs KEEP. Asia 1–7 wait grid: 10 REJECT PF2.45; next 12 then 13. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia max_wait=12 on asia 1–7 / ema=32 — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=market; **max_wait=12**; trail_arm_mode=off; SL1000/TP4000; asia **1–7**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; **ema=32**; skip_late 7; wick=false; use_higher_close=false; resume_closes=1; workers=4
- **n / metrics:** 226 trades, 47.8% wins (108W/118L), +193480.4 pts, **PF 2.7**; skipped 210
- **exits:** {'flatten': 52, 'sl': 113, 'tp': 60, 'timeout': 1}
- **entries:** timeout_market 127 / ema_touch 99
- **by_month (compact):** 2025-01 11t 90.9% +10429 PF11.43 · 2025-02 11t 63.6% +8253 PF3.06 · 2025-03 13t 46.2% +2020 PF1.32 · 2025-04 9t 66.7% +17831 PF6.94 · 2025-05 10t 40.0% +7686 PF2.28 · 2025-06 9t 66.7% +8262 PF3.75 · 2025-07 11t 45.5% +4214 PF1.93 · 2025-08 7t 57.1% +1689 PF1.72 · 2025-09 13t 46.2% +7054 PF2.01 · 2025-10 13t 38.5% +10310 PF2.29 · 2025-11 12t 25.0% +3000 PF1.33 · 2025-12 10t 50.0% +13788 PF3.76 · 2026-01 14t 35.7% +11000 PF2.22 · 2026-02 9t 55.6% +16000 PF5.0 · 2026-03 12t 41.7% +13000 PF2.86 · 2026-04 12t 41.7% +11177 PF2.6 · 2026-05 15t 66.7% +32232 PF7.45 · 2026-06 10t 30.0% +5000 PF1.71 · 2026-07 11t 27.3% +3232 PF1.46 · 2026-08 9t 33.3% +6000 PF2.0 · 2026-09 5t 40.0% +1305 PF1.44
- **vs KEEP max_wait=13 ema=32 asia 1–6:** 217t 50.7% +224605 PF3.13 → **n +9 / win% -2.9pp / pts -31125 / PF -0.43** — not thin-book
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T194252Z_b53b93ab.json
- **Conclusion:** **REJECT max_wait=12 on asia 1–7.** Worse PF+pts vs KEEP. Asia 1–7 wait grid: 10 REJECT PF2.45; 12 REJECT PF2.7; next 13. Score PF+pts. Ask before any reaktor push.

### 2026-09-12 Asia max_wait=13 on asia 1–7 / ema=32 — REJECT
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; timeout_action=market; **max_wait=13**; trail_arm_mode=off; SL1000/TP4000; asia **1–7**; min_asia 300; break ±200; **max_break=15 LOCKED**; pullback preferred; **ema=32**; skip_late 7; wick=false; use_higher_close=false; resume_closes=1; workers=4
- **n / metrics:** 226 trades, 48.2% wins (109W/117L), +198480.4 pts, **PF 2.75**; skipped 210
- **exits:** {'flatten': 52, 'sl': 112, 'tp': 61, 'timeout': 1}
- **entries:** timeout_market 122 / ema_touch 104
- **by_month (compact):** 2025-01 11t 90.9% +10429 PF11.43 · 2025-02 11t 63.6% +8253 PF3.06 · 2025-03 13t 46.2% +2020 PF1.32 · 2025-04 9t 66.7% +17831 PF6.94 · 2025-05 10t 40.0% +7686 PF2.28 · 2025-06 9t 66.7% +8262 PF3.75 · 2025-07 11t 45.5% +4214 PF1.93 · 2025-08 7t 57.1% +1689 PF1.72 · 2025-09 13t 46.2% +7054 PF2.01 · 2025-10 13t 38.5% +10310 PF2.29 · 2025-11 12t 25.0% +3000 PF1.33 · 2025-12 10t 50.0% +13789 PF3.76 · 2026-01 14t 42.9% +16000 PF3.0 · 2026-02 9t 55.6% +16000 PF5.0 · 2026-03 12t 41.7% +13000 PF2.86 · 2026-04 12t 41.7% +11177 PF2.6 · 2026-05 15t 66.7% +32232 PF7.45 · 2026-06 10t 30.0% +5000 PF1.71 · 2026-07 11t 27.3% +3232 PF1.46 · 2026-08 9t 33.3% +6000 PF2.0 · 2026-09 5t 40.0% +1305 PF1.44
- **vs KEEP max_wait=13 ema=32 asia 1–6:** 217t 50.7% +224605 PF3.13 → **n +9 / win% -2.5pp / pts -26125 / PF -0.38** — not thin-book
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260912T202359Z_971012ce.json
- **Conclusion:** **REJECT max_wait=13 on asia 1–7.** Worse PF+pts vs KEEP (matches prior one-knob asia 1–7 wait13 REJECT PF2.75). Asia 1–7 wait grid closed: 10 REJECT PF2.45; 12 REJECT PF2.70; 13 REJECT PF2.75.

### 2026-09-12 Asia max_wait × asia-window 6-cell winner — KEEP remains asia 1–6 / wait13 / ema=32
- **Grid (2025-01→2026-10, SL1000/TP4000 trail off, timeout=market, max_break=15, ema=32):**
  - asia **1–6** wait10 REJECT **PF2.63**; wait12 REJECT **PF2.99**; wait13 KEEP **217t 50.7% +224605 PF3.13**
  - asia **1–7** wait10 REJECT **PF2.45**; wait12 REJECT **226t 47.8% +193480 PF2.70**; wait13 REJECT **226t 48.2% +198480 PF2.75**
- **Overall winner by PF+pts:** **KEEP** asia **1–6** / max_wait=**13** / ema=**32** (PF3.13 / +224605). All five other cells lose on both PF and pts. Not thin-book.
- **Next (await Igor):** dynamic 12m-avg TP/SL / Tuesday higher-lower gate. Idle until those knobs are specified. Ask before any reaktor push.

### 2026-09-14 14:18 Asia RESET — discard all prior overnight results (bugs)
- New track: **2025-01 → 2026-10**, score **PF first**, prefer ~**1:1.5 RR**, avoid tiny 500/500.
- Seed A0 kicked: SL**2000**/TP**3000** (1:1.5), asia 1–6, max_wait=10, ema=23, max_break=15, wait_from_break=true, timeout=market, trail off, pullback preferred, skip_late 7/3000, flatten 22, workers=4.
- Next after A0: SL/TP ladder at 1:1.5 (1500/2250, 2500/3750, 1000/1500), then wait/ema/asia one-knobs on best PF seed.

### 2026-09-14 Asia RESET seed A0 SL2000/TP3000 (trail off, market, asia 1–6) — BASELINE / fresh track
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL2000 / TP3000** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 222 trades, 57.7% wins (128W/94L), +130717.6 pts, **PF 1.78**; avg +588.8 avg_win +2337.8 avg_loss -1792.8; trail_armed 0/0%
- **exits:** flatten58 / tp84 / sl80
- **entries:** timeout_market 116, ema_touch 106
- **skipped:** 214 (no_break×202, late_short×12)
- **by_month (compact):** 2025-01 12t 91.7% +11755 PF36.25; 2025-02 12t 75.0% +6942 PF2.16; 2025-03 9t 77.8% +8294 PF6.32; 2025-04 10t 70.0% +14211 PF4.23; 2025-05 11t 63.6% +6114 PF1.76; 2025-06 9t 66.7% +6924 PF2.15; 2025-07 11t 45.5% +4253 PF1.55; 2025-08 7t 28.6% -2477 PF0.49; 2025-09 14t 42.9% -7155 PF0.49; 2025-10 13t 61.5% +14000 PF2.40; 2025-11 13t 46.2% +4465 PF1.35; 2025-12 9t 55.6% +3964 PF1.50; 2026-01 11t 45.5% +3000 PF1.25; 2026-02 10t 40.0% +0 PF1.00; 2026-03 11t 45.5% +3000 PF1.25; 2026-04 9t 55.6% +5196 PF1.65; 2026-05 14t 78.6% +27000 PF5.50; 2026-06 11t 54.5% +8000 PF1.80; 2026-07 13t 30.8% -5767 PF0.66; 2026-08 9t 66.7% +12000 PF3.00; 2026-09 4t 75.0% +7000 PF4.50
- **regime rollups:** 2025 130t 60.8% +71289; 2026 92t 53.3% +59428
- **Note:** RESET 2026-09-14 — all pre-reset Asia results INVALID. This is the **fresh-track baseline A0**. Score PF first.
- **Result:** C:\\Users\\user\\strateg\\results\\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T112903Z_bdde252f.json
- **Conclusion:** **KEEP as A0 baseline.** Next: one-knob **SL1500/TP2250** (~1:1.5), then 2500/3750, then 1000/1500 (skip if PF collapses). Promote best PF. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob SL1500/TP2250 (trail off, market, asia 1–6) — vs A0
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 222 trades, 56.8% wins (126W/96L), +111761.0 pts, **PF 1.82**; avg 503.4 avg_win 1969.2 avg_loss -1420.4; trail_armed 0/0.0%
- **exits:** flatten31 / tp103 / sl88
- **entries:** timeout_market 116, ema_touch 106
- **skipped:** 214 (no_break×202, late_short×12)
- **by_month (compact):** 2025-01 12t 83.3% +10336 PF4.45; 2025-02 12t 75.0% +9759 PF3.17; 2025-03 9t 66.7% +3626 PF1.83; 2025-04 10t 60.0% +6961 PF2.42; 2025-05 11t 54.5% +4618 PF1.62; 2025-06 9t 66.7% +9000 PF3.00; 2025-07 11t 36.4% -997 PF0.87; 2025-08 7t 42.9% +1158 PF1.31; 2025-09 14t 50.0% -951 PF0.90; 2025-10 13t 61.5% +10500 PF2.40; 2025-11 13t 38.5% -750 PF0.94; 2025-12 9t 55.6% +5250 PF1.88; 2026-01 11t 72.7% +13500 PF4.00; 2026-02 10t 40.0% +0 PF1.00; 2026-03 11t 36.4% -1500 PF0.86; 2026-04 9t 44.4% +1500 PF1.20; 2026-05 14t 85.7% +24000 PF9.00; 2026-06 11t 63.6% +9750 PF2.62; 2026-07 13t 38.5% -750 PF0.94; 2026-08 9t 66.7% +9000 PF3.00; 2026-09 4t 25.0% -2250 PF0.50
- **regime rollups:** 2025 130t 57.7% +58511; 2026 92t 55.4% +53250
- **vs A0 SL2000/TP3000:** 222t same n; win% -0.9pp; pts -18957; PF +0.04 (A0 was 222t 57.7% +130718 PF1.78)
- **Note:** RESET 2026-09-14 fresh track. Score PF first.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T121229Z_72e87dd0.json
- **Conclusion:** **MILD PF KEEP candidate** over A0 (PF 1.82 vs 1.78, dPF +0.04; pts +111761 vs +130718 -18957; win% 56.8 vs 57.7 -0.9pp). Current PF-best pending rest of SL/TP ladder. Next: one-knob **SL2500/TP3750** (~1:1.5), then 1000/1500. Promote best PF. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob SL2500/TP3750 (trail off, market, asia 1–6) — vs PF-best
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL2500 / TP3750** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 222 trades, 57.7% wins (128W/94L), +112727.0 pts, **PF 1.55**; avg 507.8 avg_win 2478.4 avg_loss -2175.7; trail_armed 0/0.0%
- **exits:** flatten83 / tp62 / sl76 / timeout1
- **entries:** timeout_market 116, ema_touch 106
- **skipped:** 214 (no_break 202, late_short 12)
- **by_month (compact):** 2025-01 12t 91.7% +11755 PF36.25 · 2025-02 12t 75.0% +4591 PF1.61 · 2025-03 9t 77.8% +6580 PF5.22 · 2025-04 10t 70.0% +14916 PF3.76 · 2025-05 11t 63.6% +727 PF1.07 · 2025-06 9t 77.8% +7850 PF2.87 · 2025-07 11t 45.5% +2443 PF1.3 · 2025-08 7t 28.6% -2977 PF0.44 · 2025-09 14t 50.0% -5284 PF0.61 · 2025-10 13t 53.8% +9861 PF1.66 · 2025-11 13t 53.8% +11465 PF1.87 · 2025-12 9t 55.6% +2612 PF1.26 · 2026-01 11t 36.4% -4487 PF0.74 · 2026-02 10t 50.0% +6250 PF1.5 · 2026-03 11t 36.4% -2500 PF0.86 · 2026-04 9t 66.7% +10096 PF2.35 · 2026-05 14t 71.4% +24966 PF3.5 · 2026-06 11t 45.5% -1029 PF0.93 · 2026-07 13t 30.8% -7517 PF0.64 · 2026-08 9t 66.7% +15000 PF3.0 · 2026-09 4t 75.0% +7410 PF4.78
- **regime rollups:** 2025 130t 62.3% +64539; 2026 92t 51.1% +48188
- **vs PF-best SL1500/TP2250:** 222t same n; win% +0.9pp; pts +966; PF -0.27 (best was 222t 56.8% +111761 PF1.82)
- **Note:** RESET 2026-09-14 fresh track. Score PF first.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T135157Z_f416c103.json
- **Conclusion:** **REJECT SL2500/TP3750.** Worse PF vs SL1500/TP2250 (1.55 vs 1.82). Next was already queued: **SL1000/TP1500**. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob SL1000/TP1500 (trail off, market, asia 1–6) — vs PF-best
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1000 / TP1500** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 222 trades, 50.5% wins (112W/110L), +53003.3 pts, **PF 1.48**; avg 238.8 avg_win 1451.7 avg_loss -996.3; trail_armed 0/0.0%
- **exits:** flatten8 / tp105 / sl109
- **entries:** timeout_market 116, ema_touch 106
- **skipped:** 214 (no_break 202, late_short 12)
- **by_month (compact):** 2025-01 12t 75.0% +7634 PF3.54 · 2025-02 12t 66.7% +7800 PF2.95 · 2025-03 9t 44.4% +1000 PF1.2 · 2025-04 10t 50.0% +2500 PF1.5 · 2025-05 11t 72.7% +9000 PF4.0 · 2025-06 9t 33.3% -1500 PF0.75 · 2025-07 11t 54.5% +4000 PF1.8 · 2025-08 7t 42.9% +908 PF1.25 · 2025-09 14t 35.7% -3838 PF0.57 · 2025-10 13t 61.5% +7000 PF2.4 · 2025-11 13t 38.5% -500 PF0.94 · 2025-12 9t 55.6% +3500 PF1.88 · 2026-01 11t 63.6% +6500 PF2.62 · 2026-02 10t 40.0% +0 PF1.0 · 2026-03 11t 36.4% -1000 PF0.86 · 2026-04 9t 33.3% -1500 PF0.75 · 2026-05 14t 64.3% +8500 PF2.7 · 2026-06 11t 54.5% +4000 PF1.8 · 2026-07 13t 30.8% -3000 PF0.67 · 2026-08 9t 66.7% +6000 PF3.0 · 2026-09 4t 0.0% -4000 PF0.0
- **regime rollups:** 2025 130t 53.1% +37503; 2026 92t 46.7% +15500
- **vs PF-best SL1500/TP2250:** 222t same n; win% -6.3pp; pts -58758; PF -0.34 (best was 222t 56.8% +111761 PF1.82)
- **Note:** RESET 2026-09-14 fresh track. Score PF first. Avoid tiny 500/500; 1000/1500 already collapses PF.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T142324Z_c0d88dc0.json
- **Conclusion:** **REJECT SL1000/TP1500** (PF collapse 1.48). SL/TP ladder CLOSED.

### 2026-09-14 Asia RESET SL/TP ladder winner — KEEP SL1500/TP2250
- **Ladder (2025-01→2026-10, asia 1–6, max_wait=10, ema=23, max_break=15, trail off, timeout=market):**
  - A0 SL2000/TP3000 BASELINE **222t 57.7% +130718 PF1.78**
  - SL1500/TP2250 **KEEP 222t 56.8% +111761 PF1.82**
  - SL2500/TP3750 REJECT **222t 57.7% +112727 PF1.55**
  - SL1000/TP1500 REJECT **222t 50.5% +53003 PF1.48**
- **Overall winner by PF:** **SL1500/TP2250** (PF1.82). A0 keeps best pts but loses on PF.
- **Next:** one-knob **max_wait {8,10,12,13}** on SL1500/TP2250 (max_wait=10 already known = KEEP seed). Kick max_wait=8 first. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob max_wait=8 (SL1500/TP2250 seed) — REJECT vs wait10
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=8**; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 226 trades, 53.1% wins (120W/106L), +83159.8 pts, **PF 1.54**; avg 368.0 avg_win 1977.1 avg_loss -1453.7; trail_armed 0/0.0%
- **exits:** flatten28 / tp98 / sl100
- **entries:** timeout_market 143, ema_touch 83
- **skipped:** 210 (no_break×202, late_short×8)
- **by_month (compact):** 2025-01 13t 84.6% +10030 PF4.34; 2025-02 12t 75.0% +12770 PF3.84; 2025-03 9t 66.7% +3313 PF1.76; 2025-04 10t 50.0% +2107 PF1.28; 2025-05 11t 54.5% +4898 PF1.65; 2025-06 9t 66.7% +9000 PF3.00; 2025-07 11t 45.5% +1793 PF1.24; 2025-08 8t 37.5% -662 PF0.88; 2025-09 14t 35.7% -6590 PF0.46; 2025-10 13t 61.5% +10500 PF2.40; 2025-11 13t 30.8% -4500 PF0.67; 2025-12 10t 50.0% +3750 PF1.50; 2026-01 11t 36.4% -1500 PF0.86; 2026-02 10t 30.0% -3750 PF0.64; 2026-03 11t 45.5% +2250 PF1.25; 2026-04 9t 44.4% +1500 PF1.20; 2026-05 14t 71.4% +16500 PF3.75; 2026-06 12t 75.0% +15750 PF4.50; 2026-07 13t 38.5% -750 PF0.94; 2026-08 9t 66.7% +9000 PF3.00; 2026-09 4t 25.0% -2250 PF0.50
- **regime rollups:** 2025 133t 54.9% +46410; 2026 93t 50.5% +36750
- **vs PF-best wait10 SL1500/TP2250:** 222t 56.8% +111761 PF1.82 → **n +4 / win% -3.7pp / pts -28601 / PF -0.28** — shorter wait floods timeout_market (143 vs 116) and cuts PF
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T144534Z_e3c19428.json
- **Conclusion:** **REJECT max_wait=8.** Keep wait10 PF-best (PF1.82). Next: one-knob **max_wait=12**, then 13. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob max_wait=12 (SL1500/TP2250 seed) — REJECT vs wait10
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=12**; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 218 trades, 55.0% wins (120W/98L), +93647.0 pts, **PF 1.65**; avg 429.6 avg_win 1974.9 avg_loss -1462.6; trail_armed 0/0.0%
- **exits:** {'sl': 93, 'tp': 99, 'flatten': 26}
- **entries:** {'timeout_market': 100, 'ema_touch': 118}
- **skipped:** 218 ({'no_break': 202, 'late_short': 16})
- **by_month (compact):** 2025-01 11t 81.8% +8753 PF3.92; 2025-02 12t 75.0% +13427 PF3.98; 2025-03 9t 77.8% +4852 PF2.69; 2025-04 10t 60.0% +5857 PF1.98; 2025-05 11t 54.5% +4011 PF1.53; 2025-06 9t 66.7% +9000 PF3.00; 2025-07 11t 45.5% -858 PF0.89; 2025-08 5t 60.0% +2799 PF2.34; 2025-09 13t 46.2% +542 PF1.06; 2025-10 13t 61.5% +10500 PF2.40; 2025-11 13t 38.5% -1236 PF0.90; 2025-12 9t 55.6% +5250 PF1.88; 2026-01 11t 54.5% +6000 PF1.80; 2026-02 10t 50.0% +3750 PF1.50; 2026-03 11t 36.4% -1500 PF0.86; 2026-04 9t 22.2% -6000 PF0.43; 2026-05 14t 78.6% +20250 PF5.50; 2026-06 11t 63.6% +9750 PF2.62; 2026-07 13t 30.8% -4500 PF0.67; 2026-08 9t 55.6% +5250 PF1.88; 2026-09 4t 25.0% -2250 PF0.50
- **regime rollups:** 2025 126t 59.5% +62897; 2026 92t 48.9% +30750
- **vs PF-best wait10 SL1500/TP2250:** 222t 56.8% +111761 PF1.82 → **n -4 / win% -1.8pp / pts -18114 / PF -0.17**
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T154513Z_52230b3e.json
- **Conclusion:** **REJECT max_wait=12.** Keep wait10 PF-best (PF1.82). Next: one-knob **max_wait=13**, then ema {20,23,28,32}. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob max_wait=13 (SL1500/TP2250 seed) — REJECT vs wait10
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; **max_wait=13**; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; ema 23; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 217 trades, 55.8% wins (121W/96L), +105684.7 pts, **PF 1.77**; avg 487.0 avg_win 2005.5 avg_loss -1426.9; trail_armed 0/0.0%
- **exits:** {'sl': 88, 'tp': 101, 'flatten': 27, 'timeout': 1}
- **entries:** {'timeout_market': 95, 'ema_touch': 122}
- **skipped:** 219 ({'no_break': 202, 'late_short': 17})
- **by_month (compact):** 2025-01 11t 81.8% +7938 PF3.65; 2025-02 12t 75.0% +13562 PF4.01; 2025-03 9t 77.8% +5025 PF2.75; 2025-04 9t 66.7% +7357 PF2.63; 2025-05 11t 54.5% +4145 PF1.55; 2025-06 9t 66.7% +9000 PF3.00; 2025-07 11t 27.3% -1285 PF0.84; 2025-08 5t 60.0% +2799 PF2.34; 2025-09 13t 46.2% +481 PF1.05; 2025-10 13t 61.5% +9563 PF2.28; 2025-11 13t 30.8% -4500 PF0.67; 2025-12 9t 55.6% +5250 PF1.88; 2026-01 11t 54.5% +6000 PF1.80; 2026-02 10t 40.0% +0 PF1.00; 2026-03 11t 45.5% +2250 PF1.25; 2026-04 9t 33.3% -2250 PF0.75; 2026-05 14t 78.6% +20250 PF5.50; 2026-06 11t 54.5% +6000 PF1.80; 2026-07 13t 38.5% -750 PF0.94; 2026-08 9t 77.8% +12750 PF5.25; 2026-09 4t 50.0% +2099 PF1.87
- **regime rollups:** 2025 125t 57.6% +59336; 2026 92t 53.3% +46349
- **vs PF-best wait10 SL1500/TP2250:** 222t 56.8% +111761 PF1.82 → **n -5 / win% -1.0pp / pts -6076 / PF -0.05**
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T164438Z_a77fead9.json
- **Conclusion:** **REJECT max_wait=13.** Keep wait10 PF-best (PF1.82).

### 2026-09-14 Asia RESET max_wait ladder winner — KEEP max_wait=10 (SL1500/TP2250)
- **Ladder (2025-01→2026-10, asia 1–6, SL1500/TP2250, ema=23, max_break=15, trail off, timeout=market):**
  - max_wait=8 REJECT **226t 53.1% +83160 PF1.54**
  - max_wait=10 KEEP **222t 56.8% +111761 PF1.82**
  - max_wait=12 REJECT **218t 55.0% +93647 PF1.65**
  - max_wait=13 REJECT **217t 55.8% +105685 PF1.77**
- **Overall wait winner by PF:** **max_wait=10** (PF1.82).
- **Next:** one-knob **ema {20,23,28,32}** on SL1500/TP2250 wait10 (ema=23 already known). Kick ema=20 first. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob preferred ema=20 (SL1500/TP2250 wait10) — REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; **ema 20**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 223 trades, 56.1% wins (125W/98L), +105549.2 pts, **PF 1.76**; avg 473.3 avg_win 1961.4 avg_loss -1424.8; trail_armed 0/0.0%
- **exits:** {'flatten': 30, 'sl': 91, 'tp': 102}
- **entries:** {'timeout_market': 107, 'ema_touch': 116}
- **skipped:** 213 (no_break 202, late_short 11)
- **by_month (compact):** 2025-01 12t 83.3% +10134 PF4.38 · 2025-02 12t 75.0% +9679 PF3.15 · 2025-03 9t 66.7% +3338 PF1.74 · 2025-04 10t 60.0% +6888 PF2.41 · 2025-05 11t 54.5% +4618 PF1.62 · 2025-06 10t 60.0% +7500 PF2.25 · 2025-07 11t 36.4% -997 PF0.87 · 2025-08 7t 42.9% +1077 PF1.28 · 2025-09 14t 50.0% -1188 PF0.87 · 2025-10 13t 61.5% +10500 PF2.40 · 2025-11 13t 38.5% -750 PF0.94 · 2025-12 9t 55.6% +5250 PF1.88 · 2026-01 11t 54.5% +6000 PF1.80 · 2026-02 10t 40.0% +0 PF1.00 · 2026-03 11t 45.5% +2250 PF1.25 · 2026-04 9t 44.4% +1500 PF1.20 · 2026-05 14t 85.7% +24000 PF9.00 · 2026-06 11t 63.6% +9750 PF2.62 · 2026-07 13t 38.5% -750 PF0.94 · 2026-08 9t 66.7% +9000 PF3.00 · 2026-09 4t 25.0% -2250 PF0.50
- **regime rollups:** 2025 131t 57.3% +56049; 2026 92t 54.3% +49500
- **vs PF-best wait10 SL1500/TP2250 ema23:** 222t 56.8% +111761 PF1.82 → **n +1 / win% -0.7pp / pts -6212 / PF -0.06**
- **Note:** RESET 2026-09-14 fresh track. Score PF first.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T184620Z_42b58681.json
- **Conclusion:** **REJECT ema=20** vs KEEP ema23 (PF 1.76 vs 1.82). Keep ema23 PF-best. Next: preferred **ema=28**, then 32. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob preferred ema=28 (SL1500/TP2250 wait10) — PROMOTE vs KEEP
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; **ema 28**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 224 trades, 56.7% wins (127W/97L), +113628.1 pts, **PF 1.83**; avg 507.3 avg_win 1979.1 avg_loss -1419.7; trail_armed 0/0.0%
- **exits:** {'flatten': 32, 'sl': 88, 'tp': 104}
- **entries:** {'timeout_market': 133, 'ema_touch': 91}
- **skipped:** 212 (no_break 202, late_short 10)
- **by_month (compact):** 2025-01 12t 83.3% +10571 PF4.52 · 2025-02 12t 75.0% +9873 PF3.19 · 2025-03 9t 66.7% +3836 PF1.88 · 2025-04 10t 60.0% +7088 PF2.45 · 2025-05 11t 63.6% +8368 PF2.39 · 2025-06 10t 70.0% +11250 PF3.50 · 2025-07 11t 36.4% -997 PF0.87 · 2025-08 7t 42.9% +1355 PF1.38 · 2025-09 14t 50.0% -716 PF0.92 · 2025-10 13t 61.5% +10500 PF2.40 · 2025-11 13t 46.2% +3000 PF1.29 · 2025-12 9t 44.4% +1500 PF1.20 · 2026-01 11t 72.7% +13500 PF4.00 · 2026-02 10t 30.0% -3750 PF0.64 · 2026-03 11t 36.4% -1500 PF0.86 · 2026-04 9t 44.4% +1500 PF1.20 · 2026-05 14t 85.7% +24000 PF9.00 · 2026-06 12t 66.7% +12000 PF3.00 · 2026-07 13t 38.5% -750 PF0.94 · 2026-08 9t 55.6% +5250 PF1.88 · 2026-09 4t 25.0% -2250 PF0.50
- **regime rollups:** 2025 131t 58.8% +65628; 2026 93t 53.8% +48000
- **vs PF-best wait10 SL1500/TP2250 ema23:** 222t 56.8% +111761 PF1.82 → **n +2 / win% -0.1pp / pts +1867 / PF +0.01**
- **Note:** RESET 2026-09-14 fresh track. Score PF first.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T210050Z_227b5e9a.json
- **Conclusion:** **PROMOTE ema=28** over KEEP ema23 (PF 1.83 vs 1.82). New PF-best ema28. Next: preferred **ema=32**, then pullback required ladder. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob preferred ema=32 (SL1500/TP2250 wait10) — REJECT vs KEEP
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; pullback preferred; **ema 32**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 224 trades, 55.4% wins (124W/100L), +103064.5 pts, **PF 1.72**; avg 460.1 avg_win 1978.1 avg_loss -1422.2; trail_armed 0/0.0%
- **exits:** {'flatten': 30, 'sl': 92, 'tp': 102}
- **entries:** {'timeout_market': 147, 'ema_touch': 77}
- **skipped:** 212 (no_break 202, late_short 10)
- **by_month (compact):** 2025-01 12t 91.7% +14812 PF10.87 · 2025-02 11t 72.7% +7444 PF2.65 · 2025-03 9t 66.7% +3998 PF1.92 · 2025-04 10t 60.0% +7185 PF2.47 · 2025-05 11t 54.5% +4618 PF1.62 · 2025-06 10t 70.0% +11250 PF3.50 · 2025-07 11t 36.4% -997 PF0.87 · 2025-08 7t 42.9% +1314 PF1.36 · 2025-09 14t 50.0% -560 PF0.94 · 2025-10 13t 69.2% +14250 PF3.38 · 2025-11 13t 46.2% +3000 PF1.29 · 2025-12 10t 40.0% +0 PF1.00 · 2026-01 11t 63.6% +9750 PF2.62 · 2026-02 10t 30.0% -3750 PF0.64 · 2026-03 11t 36.4% -1500 PF0.86 · 2026-04 9t 44.4% +1500 PF1.20 · 2026-05 14t 78.6% +20250 PF5.50 · 2026-06 12t 66.7% +12000 PF3.00 · 2026-07 13t 30.8% -4500 PF0.67 · 2026-08 9t 55.6% +5250 PF1.88 · 2026-09 4t 25.0% -2250 PF0.50
- **regime rollups:** 2025 131t 58.8% +66314; 2026 93t 50.5% +36750
- **vs PF-best preferred ema28 KEEP:** 224t 56.7% +113628 PF1.83 → **n +0 / win% -1.3pp / pts -10564 / PF -0.11**
- **Note:** RESET 2026-09-14 fresh track. Score PF first. preferred ema ladder CLOSED: ema20 REJECT PF1.76; ema23 PF1.82; **ema28 KEEP PF1.83**; ema32 REJECT PF1.72.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T212522Z_dd11daf5.json
- **Conclusion:** **REJECT ema=32** vs KEEP ema28 (PF 1.72 vs 1.83). Preferred-EMA ladder done; KEEP ema=28. Next: **pullback_mode=required** × ema {23, 28, 32} (kick required+ema23 first). Ask before any reaktor push.

### 2026-09-14 Asia RESET preferred-EMA ladder winner — KEEP ema=28 (SL1500/TP2250 wait10)
- **Ladder (2025-01→2026-10, asia 1–6, SL1500/TP2250, max_wait=10, max_break=15, trail off, timeout=market, pullback preferred):**
  - ema=20 REJECT **223t 56.1% +105549 PF1.76**
  - ema=23 **222t 56.8% +111761 PF1.82**
  - ema=28 KEEP **224t 56.7% +113628 PF1.83**
  - ema=32 REJECT **224t 55.4% +103064 PF1.72**
- **Overall preferred-EMA winner by PF:** **ema=28** (PF1.83).
- **Next:** one-knob **pullback_mode=required** × ema {23, 28, 32} on SL1500/TP2250 wait10 (skip ema20). Compare PF vs preferred KEEP. Ask before any reaktor push.

### 2026-09-14 Asia RESET one-knob pullback_mode=required x ema=23 (SL1500/TP2250 wait10) — PROMOTE on PF vs preferred KEEP
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; **pullback required**; **ema 23**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 106 trades, 60.4% wins (64W/42L), +65457.9 pts, **PF 2.08**; avg 617.5 avg_win 1968.8 avg_loss -1441.5; trail_armed 0/0.0%
- **exits:** {'tp': 52, 'flatten': 15, 'sl': 39}
- **entries:** {'ema_touch': 106} (timeout_market starved — no_pullback cuts timeouts)
- **skipped:** 330 (no_break 202, no_pullback 116, late_short 12)
- **by_month (compact):** 2025-01 8t 87.5% +7155 PF5.77; 2025-02 4t 75.0% +4300 PF3.87; 2025-03 6t 83.3% +5211 PF4.81; 2025-04 3t 66.7% +1357 PF1.90; 2025-05 4t 50.0% +1500 PF1.50; 2025-06 3t 66.7% +3000 PF3.00; 2025-07 1t 100.0% +2250; 2025-08 4t 50.0% +549 PF1.26; 2025-09 6t 50.0% +1886 PF1.61; 2025-10 7t 71.4% +8250 PF3.75; 2025-11 8t 25.0% -4500 PF0.50; 2025-12 5t 40.0% +0 PF1.00; 2026-01 7t 71.4% +8250 PF3.75; 2026-02 5t 80.0% +7500 PF6.00; 2026-03 5t 40.0% +0 PF1.00; 2026-04 5t 20.0% -3750 PF0.38; 2026-05 6t 83.3% +9750 PF7.50; 2026-06 7t 71.4% +8250 PF3.75; 2026-07 6t 33.3% -1500 PF0.75; 2026-08 5t 80.0% +7500 PF6.00; 2026-09 1t 0.0% -1500 PF0.00
- **regime rollups:** 2025 59t 61.0% +30958; 2026 47t 59.6% +34500
- **vs preferred KEEP ema28:** 224t 56.7% +113628 PF1.83 → **n -118 / win% +3.7pp / pts -48170 / PF +0.25**
- **Note:** RESET 2026-09-14 fresh track. Score PF first. required cuts ~half the book (no_pullback x116) and all timeout_market entries.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T223759Z_73662444.json
- **Conclusion:** **PROMOTE on PF** (2.08 > 1.83 preferred KEEP). New overall PF-best while required ladder continues. Caveat: pts and n drop sharply. Next: required × **ema=28**, then 32. Ask before any reaktor push.

### 2026-09-15 Asia RESET one-knob pullback_mode=required × ema=28 (SL1500/TP2250 wait10) — PROMOTE on PF vs required KEEP
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; **pullback required**; **ema 28**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 91 trades, 62.6% wins (57W/34L), +61397.2 pts, **PF 2.23**; avg 674.7 avg_win 1951.3 avg_loss -1465.6; trail_armed 0/0.0%
- **exits:** {'tp': 45, 'flatten': 15, 'sl': 31}
- **entries:** {'ema_touch': 91} (timeout_market starved — no_pullback cuts timeouts)
- **skipped:** 345 (no_break 202, no_pullback 133, late_short 10)
- **by_month (compact):** 2025-01 8t 87.5% +7390 PF5.93 · 2025-02 4t 75.0% +4414 PF3.94 · 2025-03 6t 83.3% +5421 PF4.97 · 2025-04 2t 100.0% +2984 PF— · 2025-05 4t 75.0% +5250 PF4.50 · 2025-06 3t 66.7% +3000 PF3.00 · 2025-07 1t 100.0% +2250 PF— · 2025-08 4t 50.0% +746 PF1.38 · 2025-09 4t 50.0% -58 PF0.98 · 2025-10 6t 66.7% +6000 PF3.00 · 2025-11 7t 42.9% +750 PF1.12 · 2025-12 4t 25.0% -2250 PF0.50 · 2026-01 7t 71.4% +8250 PF3.75 · 2026-02 3t 66.7% +3000 PF3.00 · 2026-03 4t 50.0% +1500 PF1.50 · 2026-04 4t 0.0% -6000 PF0.00 · 2026-05 5t 80.0% +7500 PF6.00 · 2026-06 6t 66.7% +6000 PF3.00 · 2026-07 4t 50.0% +1500 PF1.50 · 2026-08 4t 75.0% +5250 PF4.50 · 2026-09 1t 0.0% -1500 PF0.00
- **regime rollups:** 2025 53t 66.0% +35897; 2026 38t 57.9% +25500
- **vs required KEEP ema23:** 106t 60.4% +65458 PF2.08 → **n -15 / win% +2.2pp / pts -4061 / PF +0.15**
- **vs preferred KEEP:** preferred ema28 224t +113628 PF1.83
- **Note:** RESET 2026-09-14 fresh track. Score PF first. Thin-book caveat continues.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T233518Z_b810972a.json
- **Conclusion:** **PROMOTE required×ema=28** over KEEP required×ema23 (PF 2.23 vs 2.08). Next: required × **ema=32**. Ask before any reaktor push.

### 2026-09-15 Asia RESET one-knob pullback_mode=required × ema=32 (SL1500/TP2250 wait10) — REJECT vs required KEEP
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–6**; min_asia 300; break ±200; max_break 15; **pullback required**; **ema 32**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 77 trades, 62.3% wins (48W/29L), +50349.1 pts, **PF 2.19**; avg 653.9 avg_win 1931.0 avg_loss -1459.9; trail_armed 0/0.0%
- **exits:** {'tp': 38, 'flatten': 12, 'sl': 27}
- **entries:** {'ema_touch': 77} (timeout_market starved — no_pullback cuts timeouts)
- **skipped:** 359 (no_break 202, no_pullback 147, late_short 10)
- **by_month (compact):** 2025-01 8t 100.0% +11631 PF— · 2025-02 2t 50.0% +750 PF1.50 · 2025-03 5t 80.0% +3332 PF3.50 · 2025-04 2t 100.0% +3081 PF— · 2025-05 3t 66.7% +3000 PF3.00 · 2025-06 3t 66.7% +3000 PF3.00 · 2025-07 1t 100.0% +2250 PF— · 2025-08 3t 66.7% +2205 PF5.37 · 2025-09 4t 50.0% +99 PF1.03 · 2025-10 6t 83.3% +9750 PF7.50 · 2025-11 6t 33.3% -1500 PF0.75 · 2025-12 4t 25.0% -2250 PF0.50 · 2026-01 3t 100.0% +6750 PF— · 2026-02 3t 66.7% +3000 PF3.00 · 2026-03 3t 33.3% -750 PF0.75 · 2026-04 4t 0.0% -6000 PF0.00 · 2026-05 4t 75.0% +5250 PF4.50 · 2026-06 6t 66.7% +6000 PF3.00 · 2026-07 3t 33.3% -750 PF0.75 · 2026-08 3t 66.7% +3000 PF3.00 · 2026-09 1t 0.0% -1500 PF0.00
- **regime rollups:** 2025 47t 68.1% +35349; 2026 30t 53.3% +15000
- **vs required KEEP ema28:** 91t 62.6% +61397 PF2.23 → **n -14 / win% -0.3pp / pts -11048 / PF -0.04**
- **vs preferred KEEP:** preferred ema28 224t +113628 PF1.83
- **Note:** RESET 2026-09-14 fresh track. Score PF first. Thin-book caveat continues (n=77).
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260914T235149Z_f586e951.json
- **Conclusion:** **REJECT required×ema=32** vs KEEP required ema28 (PF 2.19 vs 2.23). Next: asia end **6 vs 7** on overall best (required ema28). Ask before any reaktor push.

### 2026-09-15 Asia RESET one-knob asia_end=7 (required×ema=28 SL1500/TP2250 wait10) — REJECT vs KEEP end=6
- **Window:** 2025-01-01 → 2026-10-01
- **Params:** wait_from_break=true; **timeout_action=market**; max_wait=10; trail_arm_mode=off; **SL1500 / TP2250** (~1:1.5); asia **1–7**; min_asia 300; break ≥200; max_break 15; **pullback required**; **ema 28**; skip_late 7/3000; flatten 22; hold 14; use_higher_close=false; one_trade_per_day; side both; week2/news off; workers=4
- **n / metrics:** 97 trades, 60.8% wins (59W/38L), +54160.1 pts, **PF 1.99**; avg 558.4 avg_win 1849.8 avg_loss -1446.7; trail_armed 0/0.0%
- **exits:** {'tp': 43, 'flatten': 19, 'sl': 35}
- **entries:** {'ema_touch': 97} (timeout_market starved — no_pullback cuts timeouts)
- **skipped:** 339 (no_break 194, no_pullback 136, late_short 9)
- **by_month (compact):** 2025-01 9t 88.9% +8014 PF6.34 · 2025-02 6t 66.7% +6248 PF4.26 · 2025-03 7t 71.4% +4657 PF3.19 · 2025-04 3t 66.7% +1484 PF1.99 · 2025-05 3t 66.7% +3000 PF3.00 · 2025-06 4t 50.0% +775 PF1.26 · 2025-07 1t 100.0% +2250 · 2025-08 4t 75.0% +1911 PF2.34 · 2025-09 6t 66.7% +1821 PF1.61 · 2025-10 6t 50.0% +2250 PF1.50 · 2025-11 5t 40.0% +0 PF1.00 · 2025-12 3t 33.3% -750 PF0.75 · 2026-01 8t 62.5% +6750 PF2.50 · 2026-02 4t 50.0% +1500 PF1.50 · 2026-03 5t 60.0% +3750 PF2.25 · 2026-04 4t 25.0% -2250 PF0.50 · 2026-05 6t 83.3% +9750 PF7.50 · 2026-06 5t 60.0% +3750 PF2.25 · 2026-07 3t 33.3% -750 PF0.75 · 2026-08 4t 50.0% +1500 PF1.50 · 2026-09 1t 0.0% -1500 PF0.00
- **regime rollups:** 2025 57t 64.9% +31660; 2026 40t 55.0% +22500
- **vs required KEEP asia 1–6 ema28:** 91t 62.6% +61397 PF2.23 → **n +6 / win% -1.8pp / pts -7237 / PF -0.24**
- **vs preferred KEEP:** preferred ema28 224t +113628 PF1.83
- **Note:** RESET 2026-09-14 fresh track. Score PF first. Verified timeout=market + wait_from_break=true + max_break=15.
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-10-01_20260915T001351Z_c3d497ae.json
- **Conclusion:** **REJECT asia_end=7** vs KEEP end=6 (PF 1.99 vs 2.23). KEEP stays required×ema=28 asia **1–6**. Queue empty — await Igor steer / trail probes. Ask before any reaktor push.

### 2026-09-15 16:04 Asia new-knob batch start
- Exploring: be_arm_pts, resume_max_break_pts, timeout_min_pullback_pts, tp_mode=m12 / sl_mode=m12_frac.
- Seed: preferred ema28 SL1500/TP2250 wait10 asia1-6 market wait_from_break (224t +113628 PF1.83).
- First kick: be_arm_pts=750.


### 2026-09-15 ~17:17 Europe/Bucharest Asia 5m grid FINISHED (Igor new baseline seed)
- **Grid:** `overnight_5m_grid_20260915T133628Z.json` window 2025-01-01→2026-09-01 data=candles_5m n_cells=42 seed=`igor_required_ema23_wait12_rc4_sl1000_tp2000`
- **Baseline:** required, ema=23, wait=12, wait_from_break=true, timeout=market, use_higher_close=true, resume_closes=4, skip_late=0, SL1000/TP2000, trail off, asia 1–6, max_break=15
- **SEED 5m:** n=178 PF=1.8 pts=71839.2 win=48.9%
- **Top10 by PF:**
  1. `ema32_wait13` PF=2.034 pts=79348.6 n=163 win=52.1% ov={'ema_period': 32, 'max_wait_candles': 13}
  2. `ema28_wait13` PF=1.992 pts=82079.5 n=173 win=51.4% ov={'ema_period': 28, 'max_wait_candles': 13}
  3. `ema28_wait12` PF=1.992 pts=79079.5 n=167 win=51.5% ov={'ema_period': 28, 'max_wait_candles': 12}
  4. `ema32_wait12` PF=1.955 pts=71348.6 n=156 win=51.3% ov={'ema_period': 32, 'max_wait_candles': 12}
  5. `ema28_wait10` PF=1.907 pts=63279.3 n=143 win=50.3% ov={'ema_period': 28, 'max_wait_candles': 10}
  6. `sl1200_tp1800` PF=1.905 pts=80701.1 n=178 win=56.7% ov={'sl_fixed_pts': 1200.0, 'tp_fixed_pts': 1800.0}
  7. `ema32_wait10` PF=1.896 pts=57080.5 n=131 win=50.4% ov={'ema_period': 32, 'max_wait_candles': 10}
  8. `resume_cap_250` PF=1.86 pts=57244.5 n=136 win=50.7% ov={'resume_max_break_pts': 250.0}
  9. `resume_cap_400` PF=1.853 pts=57839.2 n=138 win=50.0% ov={'resume_max_break_pts': 400.0}
  10. `resume_closes_6` PF=1.845 pts=58392.8 n=140 win=50.0% ov={'resume_closes': 6}
- **Top10 by pts:**
  1. `tp_m12_sl_m12_1_2` PF=1.595 pts=105434.2 n=178 win=44.4% ov={'tp_mode': 'm12', 'sl_mode': 'm12_frac', 'sl_m12_frac': 0.5}
  2. `tp_m12_sl_m12_1_3` PF=1.569 pts=101412.0 n=178 win=43.3% ov={'tp_mode': 'm12', 'sl_mode': 'm12_frac', 'sl_m12_frac': 0.3333333333333333}
  3. `sl1500_tp2250` PF=1.75 pts=84714.7 n=178 win=55.1% ov={'sl_fixed_pts': 1500.0, 'tp_fixed_pts': 2250.0}
  4. `tp_m12_sl1000` PF=1.692 pts=83181.8 n=178 win=31.5% ov={'tp_mode': 'm12', 'sl_mode': 'fixed', 'sl_fixed_pts': 1000.0}
  5. `ema28_wait13` PF=1.992 pts=82079.5 n=173 win=51.4% ov={'ema_period': 28, 'max_wait_candles': 13}
  6. `sl1200_tp1800` PF=1.905 pts=80701.1 n=178 win=56.7% ov={'sl_fixed_pts': 1200.0, 'tp_fixed_pts': 1800.0}
  7. `ema32_wait13` PF=2.034 pts=79348.6 n=163 win=52.1% ov={'ema_period': 32, 'max_wait_candles': 13}
  8. `ema28_wait12` PF=1.992 pts=79079.5 n=167 win=51.5% ov={'ema_period': 28, 'max_wait_candles': 12}
  9. `sl1000_tp2500` PF=1.759 pts=74180.6 n=178 win=44.4% ov={'sl_fixed_pts': 1000.0, 'tp_fixed_pts': 2500.0}
  10. `SEED` PF=1.8 pts=71839.2 n=178 win=48.9% ov={}
- **Tick confirm queue (data_source=ticks):** `ema32_wait13`, `ema28_wait13`, `ema28_wait12`
- **Next:** tick-confirm top3; then 5m follow-up grids around winners (BE / resume_cap / resume_closes on ema32_wait13 & ema28_wait13 bases). Ask before any reaktor push.



### 2026-09-15 ~17:45 Europe/Bucharest Asia TICK CONFIRM #1 `ema32_wait13` â€” CONFIRMS 5m screen
- **Window:** 2025-01-01 â†’ 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=32; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=4; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1â€“6; max_break=15; min_asia 300; break Â±200; wick=false; flatten 22; hold 14
- **n / metrics:** 163 trades, 52.1% wins (85W/78L), +79393.0 pts, **PF 2.04**; avg 487.1 avg_win 1836.4 avg_loss -983.4
- **exits:** {'tp': 73, 'sl': 76, 'flatten': 14}
- **entries:** {'ema_touch': 103, 'higher_close': 33, 'lower_close': 27}
- **skipped:** 266 (no_break 199, no_pullback 67)
- **vs 5m screen:** n 163 / PF 2.034 / pts 79348.6 / win 52.1% â†’ ticks n0 / PF +0.006 / pts +44.4 / win 0pp â€” **CONFIRMED**
- **regime rollups:** 2025 100t 53.0% +46393; 2026 63t 50.8% +33000
- **by_month (compact):** 2025-01 12t 83.3% +12546 PF11.46 Â· 2025-02 8t 75.0% +9397 PF5.70 Â· 2025-03 7t 57.1% +3675 PF2.23 Â· 2025-04 9t 66.7% +7831 PF3.61 Â· 2025-05 7t 57.1% +5000 PF2.67 Â· 2025-06 8t 50.0% +4000 PF2.00 Â· 2025-07 6t 16.7% -3000 PF0.40 Â· 2025-08 6t 50.0% +95 PF1.04 Â· 2025-09 7t 42.9% +849 PF1.21 Â· 2025-10 12t 50.0% +6000 PF2.00 Â· 2025-11 10t 30.0% -1000 PF0.86 Â· 2025-12 8t 37.5% +1000 PF1.20 Â· 2026-01 9t 66.7% +9000 PF4.00 Â· 2026-02 5t 60.0% +4000 PF3.00 Â· 2026-03 7t 28.6% -1000 PF0.80 Â· 2026-04 8t 25.0% -2000 PF0.67 Â· 2026-05 9t 77.8% +12000 PF7.00 Â· 2026-06 8t 50.0% +4000 PF2.00 Â· 2026-07 11t 45.5% +4000 PF1.67 Â· 2026-08 6t 50.0% +3000 PF2.00
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T144527Z_57d0a0e3.json
- **Conclusion:** **TICK CONFIRMS** ema32_wait13 vs 5m. Next: tick #2 `ema28_wait13`, then `ema28_wait12`. Follow-up 5m grid still held until tick queue clears. Ask before any reaktor push.




### 2026-09-15 ~18:53 Europe/Bucharest Asia TICK CONFIRM #2 `ema28_wait13` — CONFIRMS 5m screen
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=28; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=4; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 173 trades, 52.0% wins (90W/83L), +85108.2 pts, **PF 2.04**; avg 492.0 avg_win 1853.8 avg_loss -984.7
- **exits:** {'flatten': 13, 'tp': 79, 'sl': 81}
- **entries:** {'ema_touch': 115, 'higher_close': 33, 'lower_close': 25}
- **skipped:** 256 (no_break 199, no_pullback 57)
- **vs 5m screen:** n 173 / PF 1.992 / pts 82079.5 / win 51.4% → ticks n0 / PF +0.048 / pts +3028.7 / win +0.6pp — **CONFIRMED**
- **regime rollups:** 2025 105t 50.5% +42108; 2026 68t 54.4% +43000
- **by_month (compact):** 2025-01 12t 75.0% +9391 PF5.27 · 2025-02 9t 77.8% +11414 PF6.71 · 2025-03 7t 57.1% +3571 PF2.19 · 2025-04 9t 55.6% +6000 PF2.5 · 2025-05 8t 62.5% +7000 PF3.33 · 2025-06 8t 50.0% +4000 PF2.0 · 2025-07 6t 16.7% -3000 PF0.4 · 2025-08 7t 42.9% -959 PF0.73 · 2025-09 8t 25.0% -3308 PF0.45 · 2025-10 12t 50.0% +6000 PF2.0 · 2025-11 11t 36.4% +1000 PF1.14 · 2025-12 8t 37.5% +1000 PF1.2 · 2026-01 10t 70.0% +11000 PF4.67 · 2026-02 6t 66.7% +6000 PF4.0 · 2026-03 8t 37.5% +1000 PF1.2 · 2026-04 8t 25.0% -2000 PF0.67 · 2026-05 9t 88.9% +15000 PF16.0 · 2026-06 8t 50.0% +4000 PF2.0 · 2026-07 12t 41.7% +3000 PF1.43 · 2026-08 7t 57.1% +5000 PF2.67
- **Result:** results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T154904Z_1e7e5cb7.json
- **Conclusion:** **TICK CONFIRMS** ema28_wait13 vs 5m (ticks slightly better on pts/PF). Next: tick #3 `ema28_wait12`. Follow-up 5m grid still held until tick queue clears. Ask before any reaktor push.



### 2026-09-15 ~20:29 Europe/Chisinau Asia TICK CONFIRM #3 `ema28_wait12` — CONFIRMS 5m screen
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=28; max_wait=12; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=4; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 167 trades, 52.1% wins (87W/80L), +82108.2 pts, **PF 2.04**; avg 491.7 avg_win 1848.7 avg_loss -984.1
- **exits:** {'flatten': 13, 'tp': 76, 'sl': 78}
- **entries:** {'ema_touch': 112, 'higher_close': 31, 'lower_close': 24}
- **skipped:** 262 (no_break 199, no_pullback 63)
- **vs 5m screen:** n 167 / PF 1.992 / pts 79079.5 / win 51.5% → ticks n0 / PF +0.048 / pts +3028.7 / win +0.6pp — **CONFIRMED**
- **regime rollups:** 2025 104t 50.0% +40108.2; 2026 63t 55.6% +42000.0
- **by_month (compact):** 2025-01 12t 75.0% +9391 PF5.27 · 2025-02 9t 77.8% +11414 PF6.71 · 2025-03 7t 57.1% +3571 PF2.19 · 2025-04 8t 50.0% +4000 PF2.0 · 2025-05 8t 62.5% +7000 PF3.33 · 2025-06 8t 50.0% +4000 PF2.0 · 2025-07 6t 16.7% -3000 PF0.4 · 2025-08 7t 42.9% -959 PF0.73 · 2025-09 8t 25.0% -3308 PF0.45 · 2025-10 12t 50.0% +6000 PF2.0 · 2025-11 11t 36.4% +1000 PF1.14 · 2025-12 8t 37.5% +1000 PF1.2 · 2026-01 8t 75.0% +10000 PF6.0 · 2026-02 6t 66.7% +6000 PF4.0 · 2026-03 8t 37.5% +1000 PF1.2 · 2026-04 6t 16.7% -3000 PF0.4 · 2026-05 9t 88.9% +15000 PF16.0 · 2026-06 8t 50.0% +4000 PF2.0 · 2026-07 11t 45.5% +4000 PF1.67 · 2026-08 7t 57.1% +5000 PF2.67
- **Result:** results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T161950Z_1ce9d5dd.json
- **Conclusion:** **TICK CONFIRMS** ema28_wait12 vs 5m (ticks slightly better on pts/PF). Tick queue complete (all 3 CONFIRMED). Next: launch follow-up 5m grid around ema32_wait13 & ema28_wait13 (BE / resume_cap / resume_closes). Ask before any reaktor push.



### 2026-09-15 ~20:33 Europe/Chisinau Asia FOLLOW-UP 5m grid FINISHED (BE/cap/rc around tick-confirmed winners)
- **Grid:** `overnight_5m_grid_20260915T173245Z.json` window 2025-01-01→2026-09-01 data=candles_5m n_cells=30 base=`ema32_wait13` (+ e28w13 pocket)
- **Baseline for cells:** required, ema=32, wait=13, wait_from_break=true, timeout=market, use_higher_close=true, resume_closes=4, skip_late=0, SL1000/TP2000, trail off, asia 1–6, max_break=15
- **SEED_e32w13 5m:** n=163 PF=2.034 pts=79348.6 win=52.1%
- **e28w13 5m:** n=173 PF=1.992 pts=82079.5 win=51.4%
- **Top10 by PF:**
  1. `e32_rc_6` PF=2.478 pts=73902.2 n=120 win=57.5% ov={'resume_closes': 6}
  2. `e32_cap_250` PF=2.439 pts=69807.4 n=116 win=57.8% ov={'resume_max_break_pts': 250.0}
  3. `e32_cap_150` PF=2.418 pts=68791.2 n=115 win=57.4% ov={'resume_max_break_pts': 150.0}
  4. `e32_cap_400` PF=2.367 pts=69348.6 n=119 win=56.3% ov={'resume_max_break_pts': 400.0}
  5. `e28_cap_250` PF=2.366 pts=74512.8 n=127 win=56.7% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_max_break_pts': 250.0}
  6. `e28_rc_6` PF=2.362 pts=77633.1 n=132 win=56.1% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_closes': 6}
  7. `e28_cap_400` PF=2.306 pts=74079.5 n=130 win=55.4% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_max_break_pts': 400.0}
  8. `e32_rc_5` PF=2.238 pts=74105.3 n=135 win=54.8% ov={'resume_closes': 5}
  9. `e28_rc_5` PF=2.164 pts=77836.2 n=147 win=53.7% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_closes': 5}
  10. `e32_cap_600` PF=2.158 pts=63348.6 n=122 win=54.1% ov={'resume_max_break_pts': 600.0}
- **Top10 by pts:**
  1. `e28w13` PF=1.992 pts=82079.5 n=173 win=51.4% ov={'ema_period': 28, 'max_wait_candles': 13}
  2. `SEED_e32w13` PF=2.034 pts=79348.6 n=163 win=52.1% ov={}
  3. `e28_rc_5` PF=2.164 pts=77836.2 n=147 win=53.7% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_closes': 5}
  4. `e28_rc_6` PF=2.362 pts=77633.1 n=132 win=56.1% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_closes': 6}
  5. `e28_cap_250` PF=2.366 pts=74512.8 n=127 win=56.7% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_max_break_pts': 250.0}
  6. `e32_rc_3` PF=1.705 pts=74141.5 n=203 win=47.3% ov={'resume_closes': 3}
  7. `e32_rc_5` PF=2.238 pts=74105.3 n=135 win=54.8% ov={'resume_closes': 5}
  8. `e28_cap_400` PF=2.306 pts=74079.5 n=130 win=55.4% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_max_break_pts': 400.0}
  9. `e32_rc_6` PF=2.478 pts=73902.2 n=120 win=57.5% ov={'resume_closes': 6}
  10. `e28_rc_3` PF=1.689 pts=73857.0 n=206 win=47.1% ov={'ema_period': 28, 'max_wait_candles': 13, 'resume_closes': 3}
- **Read:** BE arms crush PF (e32_be_400 PF0.54). **resume_closes=6** and **resume_max_break_pts 150–400** lift PF a lot on thinner books (n~115–132 vs 163). Pts leaders remain uncapped e28w13 / SEED.
- **Tick confirm queue (data_source=ticks):** `e32_rc_6`, `e32_cap_250`, `e32_cap_150`
- **Next:** tick-confirm top3 PF; then decide KEEP among confirmed. Ask before any reaktor push.



### 2026-09-15 ~21:08 Europe/Chisinau Asia TICK CONFIRM #1 `e32_rc_6` — CONFIRMS 5m screen
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=32; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=6; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14; resume_max_break_pts=0
- **n / metrics:** 120 trades, 56.7% wins (68W/52L), +70950.2 pts, **PF 2.39**; avg 591.3 avg_win 1793.1 avg_loss -980.4
- **exits:** {'flatten': 14, 'tp': 56, 'sl': 50}
- **entries:** {'ema_touch': 111, 'higher_close': 9}
- **skipped:** 309 (no_break 199, no_pullback 110)
- **vs 5m screen:** n 120 / PF 2.478 / pts 73902.2 / win 57.5% → ticks n+0 / PF -0.088 / pts -2952.0 / win -0.8pp — **CONFIRMED**
- **regime rollups:** 2025 76t 57.9% +42950.2; 2026 44t 54.5% +28000.0
- **by_month (compact):** 2025-01 12t 83.3% +12103 PF9.2 · 2025-02 5t 80.0% +6397 PF7.4 · 2025-03 6t 66.7% +4675 PF3.34 · 2025-04 5t 100.0% +8831 PFNone · 2025-05 5t 60.0% +4000 PF3.0 · 2025-06 5t 40.0% +1000 PF1.33 · 2025-07 3t 33.3% +0 PF1.0 · 2025-08 6t 50.0% +95 PF1.04 · 2025-09 7t 57.1% +3849 PF2.28 · 2025-10 8t 62.5% +7000 PF3.33 · 2025-11 8t 25.0% -2000 PF0.67 · 2025-12 6t 16.7% -3000 PF0.4 · 2026-01 7t 85.7% +11000 PF12.0 · 2026-02 4t 75.0% +5000 PF6.0 · 2026-03 4t 25.0% -1000 PF0.67 · 2026-04 5t 20.0% -2000 PF0.5 · 2026-05 6t 83.3% +9000 PF10.0 · 2026-06 6t 50.0% +3000 PF2.0 · 2026-07 8t 37.5% +1000 PF1.2 · 2026-08 4t 50.0% +2000 PF2.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T175450Z_eba70ad6.json
- **Conclusion:** **TICK CONFIRMS** e32_rc_6 vs 5m (ticks slightly softer PF/pts but still strong). Next: tick #2 `e32_cap_250`, then `e32_cap_150`. Ask before any reaktor push.



### 2026-09-15 ~21:38 Europe/Chisinau Asia TICK CONFIRM #2 `e32_cap_250` — CONFIRMS 5m screen
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=32; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=4; resume_max_break_pts=250; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 116 trades, 56.9% wins (66W/50L), +66859.0 pts, **PF 2.35**; avg 576.4 avg_win 1763.1 avg_loss -990.1
- **exits:** {'flatten': 14, 'tp': 53, 'sl': 49}
- **entries:** {'ema_touch': 110, 'higher_close': 3, 'lower_close': 3}
- **skipped:** 313 (no_break 199, no_pullback 114)
- **vs 5m screen:** n 116 / PF 2.439 / pts 69807.4 / win 57.8% → ticks n+0 / PF -0.089 / pts -2948.4 / win -0.9pp — **CONFIRMED**
- **regime rollups:** 2025 73t 58.9% +40859.0; 2026 43t 53.5% +26000.0
- **by_month (compact):** 2025-01 11t 90.9% +11012 PF12.01 · 2025-02 5t 80.0% +6397 PF7.4 · 2025-03 6t 66.7% +4675 PF3.34 · 2025-04 4t 100.0% +6831 PFNone · 2025-05 6t 66.7% +6000 PF4.0 · 2025-06 5t 40.0% +1000 PF1.33 · 2025-07 2t 50.0% +1000 PF2.0 · 2025-08 6t 50.0% +95 PF1.04 · 2025-09 7t 42.9% +849 PF1.21 · 2025-10 7t 71.4% +8000 PF5.0 · 2025-11 8t 25.0% -2000 PF0.67 · 2025-12 6t 16.7% -3000 PF0.4 · 2026-01 6t 83.3% +9000 PF10.0 · 2026-02 4t 75.0% +5000 PF6.0 · 2026-03 4t 25.0% -1000 PF0.67 · 2026-04 5t 20.0% -2000 PF0.5 · 2026-05 7t 71.4% +8000 PF5.0 · 2026-06 6t 50.0% +3000 PF2.0 · 2026-07 8t 37.5% +1000 PF1.2 · 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T183240Z_3fe1d3a3.json
- **Conclusion:** **TICK CONFIRMS** e32_cap_250 vs 5m (ticks slightly softer). Next: tick #3 `e32_cap_150`. Ask before any reaktor push.



### 2026-09-15 ~22:23 Europe/Chisinau Asia TICK CONFIRM #3 `e32_cap_150` — CONFIRMS 5m screen
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=32; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=4; resume_max_break_pts=150; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 115 trades, 56.5% wins (65W/50L), +65843.8 pts, **PF 2.33**; avg 572.6 avg_win 1774.6 avg_loss -990.1
- **exits:** {'flatten': 13, 'tp': 53, 'sl': 49}
- **entries:** {'ema_touch': 111, 'lower_close': 3, 'higher_close': 1}
- **skipped:** 314 (no_break 199, no_pullback 115)
- **vs 5m screen:** n 115 / PF 2.418 / pts 68791.2 / win 57.4% → ticks n+0 / PF -0.088 / pts -2947.4 / win -0.9pp — **CONFIRMED**
- **regime rollups:** 2025 72t 58.3% +39843.8; 2026 43t 53.5% +26000.0
- **by_month (compact):** 2025-01 10t 90.0% +9997 PF11.0 · 2025-02 5t 80.0% +6397 PF7.4 · 2025-03 6t 66.7% +4675 PF3.34 · 2025-04 4t 100.0% +6831 PFNone · 2025-05 6t 66.7% +6000 PF4.0 · 2025-06 5t 40.0% +1000 PF1.33 · 2025-07 2t 50.0% +1000 PF2.0 · 2025-08 6t 50.0% +95 PF1.04 · 2025-09 7t 42.9% +849 PF1.21 · 2025-10 7t 71.4% +8000 PF5.0 · 2025-11 8t 25.0% -2000 PF0.67 · 2025-12 6t 16.7% -3000 PF0.4 · 2026-01 6t 83.3% +9000 PF10.0 · 2026-02 4t 75.0% +5000 PF6.0 · 2026-03 4t 25.0% -1000 PF0.67 · 2026-04 5t 20.0% -2000 PF0.5 · 2026-05 7t 71.4% +8000 PF5.0 · 2026-06 6t 50.0% +3000 PF2.0 · 2026-07 8t 37.5% +1000 PF1.2 · 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T190341Z_bfee5200.json
- **Conclusion:** **TICK CONFIRMS** e32_cap_150 vs 5m (ticks slightly softer). Follow-up tick queue complete. **STOP auto-ticking.** Primary KEEP: `e32_rc_6` (ticks PF2.39/+71k n120). Volume KEEP: `ema28_wait13` (PF2.04/+85k n173). Next: expand 5m grid (rc×cap combos + nearby ema/wait; skip BE). Ask before any reaktor push.



### 2026-09-15 ~22:29 Europe/Chisinau Asia EXPAND 5m grid FINISHED (rc×cap + nearby ema/wait; no BE)
- **Grid:** `overnight_5m_grid_20260915T192844Z.json` window 2025-01-01→2026-09-01 data=candles_5m n_cells=52
- **Baseline:** required, ema=32, wait=13, wait_from_break=true, timeout=market, uhc=true, resume_closes=4, skip_late=0, SL1000/TP2000, trail off, asia 1–6
- **Prior tick-confirmed anchors:** e32_rc_6 PF2.39/+71k; e32_cap_250 PF2.35/+67k; e32_cap_150 PF2.33/+66k; volume e28w13 ~PF2.04/+85k
- **Top10 by PF:**
  1. `e32_rc5_cap400` PF=2.498 pts=69700.9 n=113 win=58.4% ov={'resume_closes': 5, 'resume_max_break_pts': 400.0}
  2. `e32_rc6_cap400` PF=2.497 pts=69643.5 n=113 win=58.4% ov={'resume_closes': 6, 'resume_max_break_pts': 400.0}
  3. `e30w13_rc6` PF=2.491 pts=77566.2 n=125 win=57.6% ov={'ema_period': 30, 'max_wait_candles': 13, 'resume_closes': 6}
  4. `e32_rc5_cap100` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 5, 'resume_max_break_pts': 100.0}
  5. `e32_rc5_cap250` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 5, 'resume_max_break_pts': 250.0}
  6. `e32_rc5_cap150` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 5, 'resume_max_break_pts': 150.0}
  7. `e32_rc6_cap100` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 6, 'resume_max_break_pts': 100.0}
  8. `e32_rc6_cap250` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 6, 'resume_max_break_pts': 250.0}
  9. `e32_rc6_cap150` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 6, 'resume_max_break_pts': 150.0}
  10. `e32_rc7_cap100` PF=2.479 pts=68791.2 n=112 win=58.0% ov={'resume_closes': 7, 'resume_max_break_pts': 100.0}
- **Top10 by pts:**
  1. `e30w13` PF=2.081 pts=84012.6 n=167 win=52.7% ov={'ema_period': 30, 'max_wait_candles': 13}
  2. `e28w13` PF=1.992 pts=82079.5 n=173 win=51.4% ov={'ema_period': 28, 'max_wait_candles': 13}
  3. `e30w14` PF=2.004 pts=82012.6 n=172 win=51.7% ov={'ema_period': 30, 'max_wait_candles': 14}
  4. `e28w14_rc6` PF=2.349 pts=79633.1 n=136 win=55.9% ov={'ema_period': 28, 'max_wait_candles': 14, 'resume_closes': 6}
  5. `SEED_e32w13` PF=2.034 pts=79348.6 n=163 win=52.1% ov={}
  6. `e30w12` PF=2.03 pts=78012.6 n=161 win=52.2% ov={'ema_period': 30, 'max_wait_candles': 12}
  7. `e30w13_rc6` PF=2.491 pts=77566.2 n=125 win=57.6% ov={'ema_period': 30, 'max_wait_candles': 13, 'resume_closes': 6}
  8. `e34w13` PF=2.011 pts=77536.2 n=162 win=51.9% ov={'ema_period': 34, 'max_wait_candles': 13}
  9. `e28w14_cap250` PF=2.353 pts=76512.8 n=131 win=56.5% ov={'ema_period': 28, 'max_wait_candles': 14, 'resume_max_break_pts': 250.0}
  10. `e32w14_rc6` PF=2.46 pts=75902.2 n=124 win=57.3% ov={'max_wait_candles': 14, 'resume_closes': 6}
- **Read:** Many rc×cap combos collapse to same book (cap often non-binding once rc≥5). New PF edge `e32_rc5_cap400` PF2.498. Best PF+pts tradeoff among NEW: `e30w13_rc6` (and runner `e32w14_rc6`).
- **KEEP / tick queue (1–2 only, data_source=ticks):** `e30w13_rc6`, `e32w14_rc6`
- **Next:** tick-confirm those only; STOP auto-ticking rest. Ask before any reaktor push.



### 2026-09-15 ~23:08 Europe/Chisinau Asia TICK CONFIRM #1 `e30w13_rc6` — CONFIRMS 5m screen
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=30; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=6; resume_max_break_pts=0; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 125 trades, 57.6% wins (72W/53L), +77599.8 pts, **PF 2.49**; avg 620.8 avg_win 1800.1 avg_loss -981.3
- **exits:** {'flatten': 14, 'tp': 60, 'sl': 51}
- **entries:** {'ema_touch': 116, 'higher_close': 9}
- **skipped:** 304 (no_break 199, no_pullback 105)
- **vs 5m screen:** n 125 / PF 2.491 / pts 77566.2 / win 57.6% → ticks n+0 / PF -0.001 / pts +33.6 / win +0.0pp — **CONFIRMED**
- **regime rollups:** 2025 77t 55.8% +38599.8; 2026 48t 60.4% +39000.0
- **by_month (compact):** 2025-01 12t 83.3% +12036 PF9.15 · 2025-02 6t 83.3% +8365 PF9.37 · 2025-03 6t 66.7% +4626 PF3.31 · 2025-04 5t 100.0% +8786 PFNone · 2025-05 5t 60.0% +4000 PF3.0 · 2025-06 5t 40.0% +1000 PF1.33 · 2025-07 3t 33.3% +0 PF1.0 · 2025-08 6t 50.0% +37 PF1.01 · 2025-09 7t 42.9% +750 PF1.19 · 2025-10 8t 62.5% +7000 PF3.33 · 2025-11 8t 25.0% -2000 PF0.67 · 2025-12 6t 0.0% -6000 PF0.0 · 2026-01 8t 100.0% +16000 PFNone · 2026-02 5t 80.0% +7000 PF8.0 · 2026-03 4t 25.0% -1000 PF0.67 · 2026-04 5t 20.0% -2000 PF0.5 · 2026-05 7t 85.7% +11000 PF12.0 · 2026-06 6t 50.0% +3000 PF2.0 · 2026-07 9t 44.4% +3000 PF1.6 · 2026-08 4t 50.0% +2000 PF2.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T195428Z_c8a62bc9.json
- **Conclusion:** **TICK CONFIRMS** primary KEEP `e30w13_rc6` almost 1:1 with 5m (PF2.49 / +77.6k / n125). Runner `e32_rc5_cap400` kicked for ticks. STOP auto-ticking rest. Ask before any reaktor push.


### Asia overnight tick confirm — `e32_rc5_cap400` (runner) — 2026-09-15 ~23:45 Europe/Chisinau
- **Status:** CONFIRMED (ticks slightly softer vs 5m; primary KEEP unchanged `e30w13_rc6`)
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=32 · wait=13 · wait_from_break · timeout=market · uhc · rc=5 · resume_max_break_pts=400 · SL1000/TP2000 · trail off
- **Ticks:** 113t · 57.5% wins · +66756.0 pts · **PF 2.41**
- **vs 5m screen:** PF2.498/+69700.9 n113 win58.4% → ΔPF -0.088 · Δpts -2944.9 · Δwin -0.9pp
- **By year:** 2025 71t 59.2% +39756 · 2026 42t 54.8% +27000
- **Months:** 2025-01 11t 90.9% +10909 PF11.91 · 2025-02 4t 75.0% +4397 PF5.4 · 2025-03 6t 66.7% +4675 PF3.34 · 2025-04 4t 100.0% +6831 PFNone · 2025-05 5t 60.0% +4000 PF3.0 · 2025-06 5t 40.0% +1000 PF1.33 · 2025-07 2t 50.0% +1000 PF2.0 · 2025-08 6t 50.0% +95 PF1.04 · 2025-09 7t 57.1% +3849 PF2.28 · 2025-10 7t 71.4% +8000 PF5.0 · 2025-11 8t 25.0% -2000 PF0.67 · 2025-12 6t 16.7% -3000 PF0.4 · 2026-01 6t 83.3% +9000 PF10.0 · 2026-02 4t 75.0% +5000 PF6.0 · 2026-03 4t 25.0% -1000 PF0.67 · 2026-04 5t 20.0% -2000 PF0.5 · 2026-05 6t 83.3% +9000 PF10.0 · 2026-06 6t 50.0% +3000 PF2.0 · 2026-07 8t 37.5% +1000 PF1.2 · 2026-08 3t 66.7% +3000 PF4.0
- **Skips:** no_break 199, no_pullback 117
- **Run:** `20260915T203326Z_cc55b259` · result `overnight_XAUUSD_2025-01-01_2026-09-01_20260915T203326Z_cc55b259.json`
- **Policy:** STOP auto-ticking rest of leaderboard. Next: expand 5m grid around KEEP `e30w13_rc6` (nearby ema/wait/rc/cap; no BE).

### Asia overnight 5m expand grid — `overnight_5m_grid_20260915T204825Z` — 2026-09-15 ~23:49 Europe/Chisinau
- **Cells:** 59 (EXPAND_V2 around KEEP e30w13_rc6; no BE)
- **Top by PF:** `e30w13_rc5_cap600` 2.53/+74769.3, `e30w13_rc5_cap400` 2.511/+73352.2, `e30w13_rc6_cap400` 2.51/+73294.8, `e31w13_rc6` 2.505/+76736.0, `e32_rc5_cap400` 2.498/+69700.9
- **Top by pts:** `e30w13_rc4` 2.081/+84012.6, `e28w13` 1.992/+82079.5, `e30w14_rc4` 2.004/+82012.6, `e28w14_rc6` 2.349/+79633.1, `SEED_e32w13` 2.034/+79348.6
- **Primary KEEP candidate:** `e31w13_rc6` PF=2.505 pts=76736.0 n=123 win=57.7% ov={'ema_period': 31, 'max_wait_candles': 13, 'resume_closes': 6}
- **Runner-up:** `e30w13_rc5_cap600` PF=2.53 pts=74769.3 n=119 win=58.0% ov={'ema_period': 30, 'max_wait_candles': 13, 'resume_closes': 5, 'resume_max_break_pts': 600.0}
- **Note:** SL/TP probes on KEEP weakened (tp2500 PF2.08; sl1200/tp2400 PF2.11; sl800/tp1600 PF1.67). Prior tick KEEP `e30w13_rc6` remains baseline (ticks PF2.49/+77600). Policy: tick-confirm only these 1–2; STOP auto-ticking rest.


### 2026-09-16 ~00:55 Europe/Chisinau Asia TICK CONFIRM `e31w13_rc6` (expand_v2 primary) — softer vs KEEP
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=31; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=6; resume_max_break_pts=0; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 123 trades, 56.9% wins (70W/53L), +73775.9 pts, **PF 2.42**; avg 599.8 avg_win 1796.8 avg_loss -981.1
- **exits:** {'flatten': 14, 'tp': 58, 'sl': 51}
- **entries:** {'ema_touch': 114, 'higher_close': 9}
- **skipped:** 306 (no_break 199, no_pullback 107)
- **vs 5m screen:** n 123 / PF 2.505 / pts 76736.0 / win 57.7% → ticks n+0 / PF -0.085 / pts -2960.1 / win -0.8pp — **CONFIRMED**
- **vs KEEP `e30w13_rc6` ticks:** PF2.49/+77600 n125 → this run PF2.42/+73776 n123 — **NOT a new champ** (ΔPF -0.070, Δpts -3824.1)
- **regime rollups:** 2025 76t 56.6% +39775.9; 2026 47t 57.4% +34000.0
- **by_month (compact):** 2025-01 12t 83.3% +12070 PF9.18 | 2025-02 5t 80.0% +6378 PF7.38 | 2025-03 6t 66.7% +4646 PF3.32 | 2025-04 5t 100.0% +8812 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 3t 33.3% +0 PF1.0 | 2025-08 6t 50.0% +71 PF1.03 | 2025-09 7t 42.9% +799 PF1.2 | 2025-10 8t 62.5% +7000 PF3.33 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 16.7% -3000 PF0.4 | 2026-01 8t 87.5% +13000 PF14.0 | 2026-02 4t 75.0% +5000 PF6.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 4t 50.0% +2000 PF2.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T213405Z_319501cc.json
- **Conclusion:** Tick confirms 5m screen but softer than KEEP `e30w13_rc6` (PF2.49/+77.6k). **KEEP remains `e30w13_rc6`.** Runner `e30w13_rc5_cap600` tick kicked (workers=1). STOP auto-ticking rest. Ask before any reaktor push.


### 2026-09-16 ~01:45 Europe/Chisinau Asia TICK CONFIRM `e30w13_rc5_cap600` (expand_v2 runner) — NEW high-PF KEEP
- **Window:** 2025-01-01 → 2026-09-01
- **data_source:** ticks (156702498 ticks)
- **Params:** pullback=required; ema=30; max_wait=13; wait_from_break=true; timeout=market; use_higher_close=true; resume_closes=5; resume_max_break_pts=600; skip_late=0; SL1000/TP2000 fixed; trail=off; asia 1–6; max_break=15; min_asia 300; break ±200; wick=false; flatten 22; hold 14
- **n / metrics:** 119 trades, 58.0% wins (69W/50L), +74805.8 pts, **PF 2.53**; avg 628.6 avg_win 1792.3 avg_loss -977.3
- **exits:** {'flatten': 14, 'tp': 57, 'sl': 48}
- **entries:** {'ema_touch': 116, 'higher_close': 3}
- **skipped:** 310 (no_break 199, no_pullback 111)
- **vs 5m screen:** n 119 / PF 2.53 / pts 74769.3 / win 58.0% → ticks n+0 / PF +0.0 / pts +36.5 / win +0.0pp — **CONFIRMED** (near-exact match)
- **vs volume KEEP `e30w13_rc6` ticks:** PF2.49/+77600 n125 → this run PF2.53/+74806 n119 — **NEW high-PF CHAMP** (ΔPF +0.040, Δpts -2794.2)
- **regime rollups:** 2025 73t 56.2% +36805.8; 2026 46t 60.9% +38000.0
- **by_month (compact):** 2025-01 12t 83.3% +12242 PF10.19 | 2025-02 5t 80.0% +6365 PF7.37 | 2025-03 6t 66.7% +4626 PF3.31 | 2025-04 4t 100.0% +6786 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 2t 50.0% +1000 PF2.0 | 2025-08 6t 50.0% +37 PF1.01 | 2025-09 7t 42.9% +750 PF1.19 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 0.0% -6000 PF0.0 | 2026-01 7t 100.0% +14000 PFNone | 2026-02 5t 80.0% +7000 PF8.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T221736Z_0ce639ae.json
- **Conclusion:** Tick confirms 5m screen almost 1:1. **High-PF KEEP → `e30w13_rc5_cap600`** (PF2.53). Volume baseline remains `e30w13_rc6` (PF2.49/+77600). STOP auto-ticking rest. Launch EXPAND_V3 rc5/cap600 5m pocket next. Ask before any reaktor push.


### 2026-09-16 ~01:45 Europe/Chisinau Asia EXPAND_V3_RC5_CAP600_POCKET 5m grid started
- **Trigger:** runner tick `e30w13_rc5_cap600` CONFIRMED as high-PF KEEP (119t 58% +74806 PF2.53)
- **Script:** `scripts/overnight_5m_grid.py` workers=4 candles_5m; pid 9968; ~124 cells
- **Pocket:** new caps 450–1000 × rc4/5/6; ema28–32 × wait12–14 × rc5/6 × cap500/600/700; soft SL/TP on KEEP; wait stretch on KEEP. Skip BE.
- **Policy:** screen on 5m only; after finish pick 1 primary + optional runner-up for ticks. STOP auto-ticking whole leaderboard.
- **Volume baseline:** still `e30w13_rc6` (ticks PF2.49/+77.6k)


### 2026-09-16 ~01:50 Europe/Chisinau Asia EXPAND_V3_RC5_CAP600_POCKET 5m grid finished
- **Window:** 2025-01-01 → 2026-09-01; candles_5m; workers=4; **124 cells**; file `overnight_5m_grid_20260915T224748Z.json`
- **Top by PF:**
  - `e30w13_rc6_cap1000`: PF 2.603 / +78566.2 / n121 / 58.7%
  - `e30w13_rc6_cap800`: PF 2.562 / +76566.2 / n120 / 58.3%
  - `e30w13_rc6_cap900`: PF 2.562 / +76566.2 / n120 / 58.3%
  - `e31w13_rc5_cap600`: PF 2.545 / +73939.1 / n117 / 58.1%
  - `KEEP_e30w13_rc5_cap600`: PF 2.53 / +74769.3 / n119 / 58.0%
  - `e30w13_rc5_cap550`: PF 2.53 / +74769.3 / n119 / 58.0%
  - `e30w13_rc5_cap600`: PF 2.53 / +74769.3 / n119 / 58.0%
  - `e30w13_rc5_cap600_sl1000_tp2000`: PF 2.53 / +74769.3 / n119 / 58.0%
- **Top by pts:**
  - `e30w13_rc6_cap1000`: +78566.2 / PF 2.603 / n121
  - `VOL_e30w13_rc6`: +77566.2 / PF 2.491 / n125
  - `e28w14_rc5_cap600`: +76836.2 / PF 2.375 / n130
  - `e31w13_rc6`: +76736.0 / PF 2.505 / n123
  - `e30w13_rc6_cap800`: +76566.2 / PF 2.562 / n120
  - `e30w13_rc6_cap900`: +76566.2 / PF 2.562 / n120
- **Primary KEEP candidate (5m):** `e30w13_rc6_cap1000` PF 2.603 / +78566.2 / n121 / 58.7%
- **Runner-up:** `e31w13_rc5_cap600` PF 2.545 / +73939.1
- **Prior high-PF KEEP (ticks):** `e30w13_rc5_cap600` PF2.53/+74806 — still confirmed; new 5m leaders need tick confirm
- **Tick queue:** only primary+runner (1–2). Primary tick kicked (workers=1). **STOP auto-ticking rest.**
- **Note:** `e30w13_rc6_cap800/900/1000` ladder dominates PF; soft SL/TP variants on rc5/cap600 died (TP2500/SL800 etc). Ask before any reaktor push.



### 2026-09-16 ~02:10 Europe/Chisinau Asia TICK CONFIRM primary `e30w13_rc6_cap1000` — **NEW KEEP CHAMP**
- **Status:** CONFIRMED (near-exact vs 5m) · **NEW primary KEEP** (beats high-PF `e30w13_rc5_cap600` and volume `e30w13_rc6`)
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1000 · SL1000/TP2000 · trail off
- **Ticks:** 121t · 58.7% wins (71W/50L) · +78599.8 pts · **PF 2.6** · avg 649.6 avg_win 1797.3 avg_loss -980.2
- **exits:** {'flatten': 14, 'tp': 59, 'sl': 48} · **entries:** {'ema_touch': 116, 'higher_close': 5}
- **skipped:** 308 (no_break 199, no_pullback 109)
- **vs 5m screen:** n121 / PF 2.603 / pts 78566.2 / win 58.7% → ticks Δn +0 / ΔPF -0.003 / Δpts +33.6 / Δwin +0.0pp — **CONFIRMED** (near-exact)
- **vs high-PF KEEP `e30w13_rc5_cap600` ticks:** PF2.53/+74806 n119 → this PF2.6/+78600 n121 — **NEW CHAMP** (ΔPF +0.070, Δpts +3794.0)
- **vs volume KEEP `e30w13_rc6` ticks:** PF2.49/+77600 n125 → this PF2.6/+78600 n121 — **beats volume** (ΔPF +0.110, Δpts +999.8)
- **regime rollups:** 2025 75t 57.3% +40600; 2026 46t 60.9% +38000
- **by_month (compact):** 2025-01 12t 83.3% +12036 PF9.15 | 2025-02 6t 83.3% +8365 PF9.37 | 2025-03 6t 66.7% +4626 PF3.31 | 2025-04 5t 100.0% +8786 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 2t 50.0% +1000 PF2.0 | 2025-08 6t 50.0% +37 PF1.01 | 2025-09 7t 42.9% +750 PF1.19 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 0.0% -6000 PF0.0 | 2026-01 7t 100.0% +14000 PFNone | 2026-02 5t 80.0% +7000 PF8.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260915T231000Z_702d9145.json
- **Conclusion:** Tick confirms 5m almost 1:1. **Primary KEEP → `e30w13_rc6_cap1000`** (PF2.6/+78600 n121 win58.7%). Prior high-PF `e30w13_rc5_cap600` demoted to secondary. Runner `e31w13_rc5_cap600` tick kicked (workers=1). STOP auto-ticking rest. Hold 5m grid until runner finishes. Ask before any reaktor push.

## Asia tick confirm — e31w13_rc5_cap600 (runner) — 2026-09-16 ~02:37 Europe/Chisinau
- **data_source=ticks** window 2025-01→2026-09 | run `20260915T233250Z_b14d21eb`
- **117t / 57.3% / +70981.9 pts / PF2.45** — status **CONFIRMED**
- vs 5m screen: PF2.545/+73939.1 n117 win58.1% → ΔPF -0.095 / Δpts -2957.2 / Δwin -0.8
- vs primary KEEP `e30w13_rc6_cap1000` ticks PF2.6/+78599.8: **does not beat** (softer)
- 2025 roll: 72t 56.9% +37981.9 | 2026 roll: 45t 57.8% +33000.0
- skips: no_break 199, no_pullback 113
- by_month: 2025-01 12t 83.3% +12276 PF10.21 | 2025-02 4t 75.0% +4378 PF5.38 | 2025-03 6t 66.7% +4646 PF3.32 | 2025-04 4t 100.0% +6812 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 2t 50.0% +1000 PF2.0 | 2025-08 6t 50.0% +71 PF1.03 | 2025-09 7t 42.9% +799 PF1.2 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 16.7% -3000 PF0.4 | 2026-01 7t 85.7% +11000 PF12.0 | 2026-02 4t 75.0% +5000 PF6.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 3t 66.7% +3000 PF4.0
- Policy: STOP auto-ticking whole leaderboard. Next: EXPAND_V4 5m grid around `e30w13_rc6_cap1000` (caps≥1000, nearby ema/wait/rc, soft SL/TP; no BE).


### 2026-09-16 ~03:08 Europe/Chisinau Asia EXPAND_V4_RC6_CAP1000_POCKET 5m grid finished
- **Grid:** `overnight_5m_grid_20260915T234100Z.json` · data_source=candles_5m · cells=283 · workers=4
- **Anchor KEEP (ticks):** `e30w13_rc6_cap1000` PF2.6/+78600 n121 (5m PF2.603/+78566)
- **Top by PF:**
  - `e30w13_rc6_cap1000_mb250`: PF 2.662 / +74033.6 / n111 / 59.5%
  - `e31w13_rc6_cap1000`: PF 2.62 / +77736.0 / n119 / 58.8%
  - `KEEP_e30w13_rc6_cap1000`: PF 2.603 / +78566.2 / n121 / 58.7%
  - `e30w13_rc6_cap1000`: PF 2.603 / +78566.2 / n121 / 58.7%
  - `e30w13_rc6_cap1000_sl1000_tp2000`: PF 2.603 / +78566.2 / n121 / 58.7%
  - `e30w13_rc6_cap1000_mb200`: PF 2.603 / +78566.2 / n121 / 58.7%
  - `e30w13_rc6_cap1000_ar200`: PF 2.603 / +78566.2 / n121 / 58.7%
  - `e30w13_rc6_cap1000_ar300`: PF 2.603 / +78566.2 / n121 / 58.7%
- **Top by pts:**
  - `e28w14_rc6_cap1000`: PF 2.439 / +80633.1 / n132 / 56.8%
  - `e28w14_rc6_cap1200`: PF 2.397 / +79633.1 / n133 / 56.4%
  - `e28w14_rc6_cap1500`: PF 2.397 / +79633.1 / n133 / 56.4%
  - `e28w14_rc5_cap1200`: PF 2.362 / +78836.2 / n134 / 56.0%
  - `e31w14_rc6_cap1000`: PF 2.544 / +78736.0 / n124 / 58.1%
  - `e28w13_rc6_cap1000`: PF 2.456 / +78633.1 / n128 / 57.0%
- **Primary KEEP candidate (tick queue):** `e31w13_rc6_cap1000` 5m PF2.62/+77736.0 n119 win58.8% · score 23.10
- **Runner-up (optional tick):** `e30w13_rc6_cap1000_mb250` 5m PF2.662/+74033.6 n111
- **vs KEEP 5m:** primary ΔPF +0.017 / Δpts -830.2; runner ΔPF +0.059 / Δpts -4532.6
- **Action:** Kicked primary tick `e31w13_rc6_cap1000` (workers=1). STOP auto-ticking rest. Ask before any reaktor push.


### 2026-09-16 ~03:36 Europe/Chisinau Asia TICK CONFIRM primary `e31w13_rc6_cap1000` — **REJECT vs KEEP**
- **Status:** CONFIRMED (ticks softer vs 5m) · **REJECT** — does not beat KEEP `e30w13_rc6_cap1000`
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=31 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1000 · SL1000/TP2000 · trail off
- **Ticks:** 119t · 58.0% wins · +74775.9 pts · **PF 2.53**
- **exits:** {'flatten': 14, 'tp': 57, 'sl': 48} · **entries:** {'ema_touch': 114, 'higher_close': 5}
- **skipped:** no_break 199, no_pullback 111
- **vs 5m screen:** PF2.62/+77736.0 n119 win58.8% → ΔPF -0.090 · Δpts -2960.1 · Δwin -0.8pp
- **vs KEEP `e30w13_rc6_cap1000` ticks:** PF2.6/+78599.8 n121 win58.7% → ΔPF -0.070 · Δpts -3823.9 · Δn -2
- **regime rollups:** 2025 74t 58.1% +41776; 2026 45t 57.8% +33000
- **by_month (compact):** 2025-01 12t 83.3% +12070 PF9.18 | 2025-02 5t 80.0% +6378 PF7.38 | 2025-03 6t 66.7% +4646 PF3.32 | 2025-04 5t 100.0% +8812 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 2t 50.0% +1000 PF2.0 | 2025-08 6t 50.0% +71 PF1.03 | 2025-09 7t 42.9% +799 PF1.2 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 16.7% -3000 PF0.4 | 2026-01 7t 85.7% +11000 PF12.0 | 2026-02 4t 75.0% +5000 PF6.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T003224Z_ee04651a.json
- **Conclusion:** **REJECT `e31w13_rc6_cap1000`**. Primary KEEP remains **`e30w13_rc6_cap1000`** (ticks PF2.6/+78600 n121 win58.7%). Runner `e30w13_rc6_cap1000_mb250` tick **SKIPPED** (stop_auto_tick; primary not a new champ / worse PF+pts). Next: **EXPAND_V5** 5m grid around KEEP pocket (finer caps, fill-path mb/ar/max_break, hold/flatten; no BE). Ask before any reaktor push.


### 2026-09-16 ~03:36 Europe/Chisinau Asia EXPAND_V5_KEEP_POCKET_FINE 5m grid started
- **Trigger:** `e31w13_rc6_cap1000` tick REJECT vs KEEP `e30w13_rc6_cap1000` (ticks PF2.53/+74776 n119 vs KEEP PF2.6/+78600)
- **Script:** `scripts/overnight_5m_grid.py` workers=4 candles_5m; pid 9820; ~95 cells
- **Pocket:** finer caps 950–1250 × e30/e31 × rc5–7; fill-path mb/ar/max_break; hold/flatten; mb250×caps; soft SL/TP; e28/29 pts-leader rc6/7. Skip BE. No full V4 re-run.
- **Policy:** screen on 5m only; after finish pick 1 primary + optional runner-up for ticks. STOP auto-ticking whole leaderboard.
- **KEEP unchanged:** `e30w13_rc6_cap1000` ticks PF2.6/+78600 n121 win58.7%


### 2026-09-16 ~03:41 Europe/Chisinau Asia EXPAND_V5_KEEP_POCKET_FINE 5m grid finished
- **Grid:** `overnight_5m_grid_20260916T004008Z.json` · data_source=candles_5m · cells=95 · workers=4
- **Anchor KEEP (ticks):** `e30w13_rc6_cap1000` PF2.6/+78600 n121 (5m PF2.603/+78566.2)
- **Top by PF:**
  - `e30w13_rc6_cap1000_mb275`: PF 2.678 / +73033.6 / n109 / 59.6%
  - `e30w13_rc6_cap1000_mbc12`: PF 2.674 / +65288.9 / n98 / 59.2%
  - `V4TOP_e30w13_rc6_cap1000_mb250`: PF 2.662 / +74033.6 / n111 / 59.5%
  - `e30w13_rc6_cap1000_mb250`: PF 2.662 / +74033.6 / n111 / 59.5%
  - `e30w13_rc6_cap1100_mb250`: PF 2.662 / +74033.6 / n111 / 59.5%
  - `e30w13_rc6_cap1200_mb250`: PF 2.662 / +74033.6 / n111 / 59.5%
  - `e30w13_rc6_cap1500_mb250`: PF 2.662 / +74033.6 / n111 / 59.5%
  - `e31w13_rc6_cap1000_mb275`: PF 2.651 / +70186.4 / n106 / 59.4%
- **Top by pts:**
  - `e30w13_rc6_cap1000_sl1100_tp2200`: PF 2.52 / +81773.5 / n121 / 58.7%
  - `e28w14_rc6_cap1000`: PF 2.439 / +80633.1 / n132 / 56.8%
  - `e30w13_rc6_cap1000_flat23`: PF 2.65 / +80344.4 / n121 / 58.7%
  - `e30w13_rc6_cap1000_mbc20`: PF 2.253 / +80228.3 / n145 / 55.2%
  - `e30w13_rc6_cap1000_sl1000_tp2200`: PF 2.572 / +80173.5 / n121 / 57.0%
  - `e28w14_rc6_cap1200`: PF 2.397 / +79633.1 / n133 / 56.4%
  - `e30w13_rc6_cap1000_mbc18`: PF 2.343 / +79228.3 / n137 / 56.2%
  - `e31w14_rc6_cap1000`: PF 2.544 / +78736.0 / n124 / 58.1%
- **Primary KEEP candidate (tick queue):** `e30w13_rc6_cap1000_flat23` PF=2.65 pts=80344.4 n=121 win=58.7%
- **Runner-up (optional tick):** `e30w13_rc6_cap1000_mb275` PF=2.678 pts=73033.6 n=109 win=59.6%
- **vs KEEP 5m:** primary ΔPF +0.047 / Δpts +1778.2; runner ΔPF +0.075 / Δpts -5532.6
- **Action:** Kick primary tick only (workers=1). STOP auto-ticking rest. Ask before any reaktor push.


### 2026-09-16 ~04:11 Europe/Chisinau Asia TICK CONFIRM primary `e30w13_rc6_cap1000_flat23` — **NEW KEEP CHAMP**
- **Status:** CONFIRMED (near-exact vs 5m) · **PROMOTE** — beats OLD KEEP `e30w13_rc6_cap1000`
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1000 · **flatten_hour=23** · SL1000/TP2000 · trail off
- **Ticks:** 121t · 58.7% wins · +80495.8 pts · **PF 2.65**
- **exits:** {'flatten': 14, 'tp': 59, 'sl': 48} · **entries:** {'ema_touch': 116, 'higher_close': 5}
- **skipped:** no_break 199, no_pullback 109
- **vs 5m screen:** PF2.65/+80344.4 n121 win58.7% → ΔPF +0.000 · Δpts +151.4 · Δwin +0.0pp — **CONFIRMED** (near-exact)
- **vs OLD KEEP `e30w13_rc6_cap1000` ticks:** PF2.6/+78599.8 n121 win58.7% → ΔPF +0.050 · Δpts +1896.0 · Δn +0
- **regime rollups:** 2025 75t 57.3% +42496; 2026 46t 60.9% +38000
- **by_month (compact):** 2025-01 12t 83.3% +12944 PF9.77 | 2025-02 6t 83.3% +8518 PF9.52 | 2025-03 6t 66.7% +5273 PF3.64 | 2025-04 5t 100.0% +8602 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 2t 50.0% +1000 PF2.0 | 2025-08 6t 50.0% +409 PF1.18 | 2025-09 7t 42.9% +750 PF1.19 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 0.0% -6000 PF0.0 | 2026-01 7t 100.0% +14000 PFNone | 2026-02 5t 80.0% +7000 PF8.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T010433Z_d60f71d8.json
- **Conclusion:** **NEW primary KEEP → `e30w13_rc6_cap1000_flat23`** (ticks PF2.65/+80496 n121 win58.7%). OLD `e30w13_rc6_cap1000` demoted (ticks PF2.6/+78600). Runner `e30w13_rc6_cap1000_mb275` tick **SKIPPED** (stop_auto_tick; expand around new flatten=23 pocket). Next: **EXPAND_V6** 5m grid around flat23. Ask before any reaktor push.


### 2026-09-16 ~04:11 Europe/Chisinau Asia EXPAND_V6_FLAT23_POCKET 5m grid started
- **Trigger:** `e30w13_rc6_cap1000_flat23` tick **PROMOTE** — NEW KEEP (ticks PF2.65/+80496 n121 vs OLD `e30w13_rc6_cap1000` PF2.6/+78600)
- **Script:** `scripts/overnight_5m_grid.py` workers=4 candles_5m; pid 4360; ~155 cells
- **Pocket:** flatten=23 anchor × hold/flatten soft, light ema/wait/rc/cap, fill-path mb/ar/mbc, soft SL/TP. Skip BE. No full V4/V5 re-run.
- **Policy:** screen on 5m only; after finish pick 1 primary + optional runner-up for ticks. STOP auto-ticking whole leaderboard.
- **NEW KEEP:** `e30w13_rc6_cap1000_flat23` ticks PF2.65/+80496 n121 win58.7%


### 2026-09-16 ~04:16 Europe/Chisinau Asia EXPAND_V6_FLAT23_POCKET 5m grid finished
- **Grid:** `overnight_5m_grid_20260916T011517Z.json` · data_source=candles_5m · cells=154 · workers=4
- **Anchor KEEP (ticks):** `e30w13_rc6_cap1000_flat23` PF2.65/+80496 n121 (5m PF2.65/+80344.4)
- **Top by PF:**
  - `V5RUN_e30w13_rc6_cap1000_mb275_flat23`: PF 2.719 / +74289.6 / n109 / 59.6%
  - `e30w13_rc6_cap1000_flat23_mb275`: PF 2.719 / +74289.6 / n109 / 59.6%
  - `e30w13_rc6_cap1000_flat23_mbc12`: PF 2.717 / +66432.3 / n98 / 59.2%
  - `e30w13_rc6_cap1000_flat23_mb250`: PF 2.703 / +75289.6 / n111 / 59.5%
  - `e31w13_rc6_cap1000_flat23`: PF 2.667 / +79514.1 / n119 / 58.8%
  - `e30w13_rc6_cap1000_flat23_hold16`: PF 2.655 / +80592.4 / n121 / 58.7%
  - `e30w13_rc6_cap1000_flat23_hold18`: PF 2.655 / +80592.4 / n121 / 58.7%
  - `KEEP_e30w13_rc6_cap1000_flat23`: PF 2.65 / +80344.4 / n121 / 58.7%
- **Top by pts:**
  - `e30w13_rc6_cap1000_flat23_sl1100_tp2200`: PF 2.561 / +83529.7 / n121 / 58.7%
  - `e30w13_rc6_cap1000_flat23_mbc20`: PF 2.306 / +83167.0 / n145 / 55.2%
  - `e28w14_rc6_cap1000_flat23`: PF 2.48 / +82425.3 / n132 / 56.8%
  - `e30w13_rc6_cap1000_flat23_mbc18`: PF 2.4 / +82167.0 / n137 / 56.2%
  - `e30w13_rc6_cap1000_flat23_sl1000_tp2200`: PF 2.616 / +81929.7 / n121 / 57.0%
  - `e30w13_rc6_cap1000_flat23_sl1100_tp2000`: PF 2.594 / +81744.4 / n121 / 60.3%
  - `e28w14_rc6_cap1200_flat23`: PF 2.436 / +81425.3 / n133 / 56.4%
  - `e30w13_rc6_cap1000_flat23_hold16`: PF 2.655 / +80592.4 / n121 / 58.7%
- **Primary KEEP candidate (tick queue):** `e31w13_rc6_cap1000_flat23` PF=2.667 pts=79514.1 n=119 win=58.8%
- **Runner-up (optional tick):** `e30w13_rc6_cap1000_flat23_mb275` PF=2.719 pts=74289.6 n=109
- **vs KEEP 5m:** primary ΔPF +0.017 / Δpts -830.3; runner ΔPF +0.069 / Δpts -6054.8
- **Action:** Kick primary tick only (workers=1). STOP auto-ticking rest. Ask before any reaktor push.


### 2026-09-16 ~04:37 Europe/Chisinau Asia TICK CONFIRM primary `e31w13_rc6_cap1000_flat23` — **REJECT**
- **Status:** CONFIRMED (softer vs 5m) · **REJECT** — does not beat KEEP `e30w13_rc6_cap1000_flat23`
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=31 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1000 · flatten_hour=23 · SL1000/TP2000 · trail off
- **Ticks:** 119t · 58.0% wins · +76671.9 pts · **PF 2.57**
- **exits:** {'flatten': 14, 'tp': 57, 'sl': 48} · **entries:** {'ema_touch': 114, 'higher_close': 5}
- **skipped:** no_break 199, no_pullback 111
- **vs 5m screen:** PF2.667/+79514.1 n119 win58.8% → ΔPF -0.097 · Δpts -2842.2 · Δwin -0.8pp — softer
- **vs KEEP `e30w13_rc6_cap1000_flat23` ticks:** PF2.65/+80495.8 n121 win58.7% → ΔPF -0.080 · Δpts -3823.9 · Δn -2
- **regime rollups:** 2025 74t 58.1% +43672; 2026 45t 57.8% +33000
- **by_month (compact):** 2025-01 12t 83.3% +12978 PF9.79 | 2025-02 5t 80.0% +6532 PF7.53 | 2025-03 6t 66.7% +5292 PF3.65 | 2025-04 5t 100.0% +8628 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 5t 40.0% +1000 PF1.33 | 2025-07 2t 50.0% +1000 PF2.0 | 2025-08 6t 50.0% +444 PF1.2 | 2025-09 7t 42.9% +799 PF1.2 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 25.0% -2000 PF0.67 | 2025-12 6t 16.7% -3000 PF0.4 | 2026-01 7t 85.7% +11000 PF12.0 | 2026-02 4t 75.0% +5000 PF6.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 7t 85.7% +11000 PF12.0 | 2026-06 6t 50.0% +3000 PF2.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 3t 66.7% +3000 PF4.0
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T013924Z_12a36b0d.json
- **Conclusion:** KEEP remains `e30w13_rc6_cap1000_flat23` (ticks PF2.65/+80496 n121 win58.7%). Challenger `e31w13_rc6_cap1000_flat23` rejected. Runner `e30w13_rc6_cap1000_flat23_mb275` tick **running** (only remaining of 1–2 queue). STOP auto-ticking leaderboard. No new 5m grid while runner ticks. Ask before any reaktor push.


### 2026-09-16 ~05:08 Europe/Chisinau Asia TICK CONFIRM runner `e30w13_rc6_cap1000_flat23_mb275` — **PROMOTE (NEW KEEP)**
- **Status:** CONFIRMED (matches 5m) → **PROMOTE** — beats OLD KEEP `e30w13_rc6_cap1000_flat23` on PF rule (ΔPF +0.070 > +0.02)
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1000 · flatten_hour=23 · **min_break=275** · SL1000/TP2000 · trail off
- **Ticks:** 109t · 59.6% wins · +74440.3 pts · **PF 2.72**
- **exits:** {'flatten': 12, 'tp': 54, 'sl': 43} · **entries:** {'ema_touch': 105, 'higher_close': 4}
- **skipped:** no_break 216, no_pullback 104
- **vs 5m screen:** PF2.719/+74289.6 n109 win59.6% → ΔPF +0.001 · Δpts +150.7 · Δwin +0.0pp — confirmed flat
- **vs OLD KEEP `e30w13_rc6_cap1000_flat23` ticks:** PF2.65/+80495.8 n121 win58.7% → ΔPF +0.070 · Δpts -6055.5 · Δn -12 · thinner but higher PF
- **regime rollups:** 2025 69t 59.4% +42440; 2026 40t 60.0% +32000
- **by_month (compact):** 2025-01 11t 90.9% +12346 PF13.35 | 2025-02 5t 80.0% +6518 PF7.52 | 2025-03 5t 80.0% +6273 PF7.27 | 2025-04 4t 100.0% +6602 PFNone | 2025-05 5t 60.0% +4000 PF3.0 | 2025-06 6t 50.0% +3000 PF2.0 | 2025-07 3t 33.3% +0 PF1.0 | 2025-08 5t 40.0% -48 PF0.98 | 2025-09 6t 50.0% +1750 PF1.58 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 7t 28.6% -1000 PF0.8 | 2025-12 5t 0.0% -5000 PF0.0 | 2026-01 5t 100.0% +10000 PFNone | 2026-02 5t 80.0% +7000 PF8.0 | 2026-03 4t 25.0% -1000 PF0.67 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 6t 83.3% +9000 PF10.0 | 2026-06 5t 60.0% +4000 PF3.0 | 2026-07 9t 44.4% +3000 PF1.6 | 2026-08 1t 100.0% +2000 PFNone
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T020202Z_6e94a214.json
- **Conclusion:** **NEW KEEP** `e30w13_rc6_cap1000_flat23_mb275` (ticks PF2.72/+74440 n109 win59.6%). OLD `e30w13_rc6_cap1000_flat23` demoted (still volume baseline). STOP auto-ticking. Kick EXPAND_V7 5m grid around mb275 pocket. Ask before any reaktor push.


### 2026-09-16 ~05:32 Europe/Chisinau Asia EXPAND_V7 5m SCORE + tick kick
- **Grid:** overnight_5m_grid_20260916T021159Z.json finished 161/161 cells · data_source=candles_5m · workers=4 (pid 12740 done ~05:12)
- **Current KEEP (ticks):** e30w13_rc6_cap1000_flat23_mb275 · 109t · 59.6% · +74440 · **PF 2.72**
- **TOP PF (5m):** e30w13_rc6_cap1000_mb275_flat23_mbc12 PF3.008/+64707 n87, e28w13_rc6_cap1200_flat23_mb275 PF2.768/+81727 n117, e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200 PF2.766/+78075 n109, e30w13_rc6_cap1200_flat23_mb275 PF2.750/+75651 n110, e28w13_rc6_cap1000_flat23_mb275 PF2.738/+80366 n116
- **Notable thin:** e30w13_rc6_cap1000_mb275_flat23_mbc12 PF3.008/+64707 n87 win62.1% — **not ticking** (thinner vs KEEP)
- **PRIMARY KEEP candidate (tick NOW workers=1):** e28w13_rc6_cap1200_flat23_mb275 5m PF2.768/+81727 n117 win59.8% (ΔPF +0.049 Δpts +7437 vs KEEP 5m)
- **RUNNER (queued, not auto):** e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200 5m PF2.766/+78075 n109 win58.7% (TP2200 fill-path)
- **Policy:** STOP auto-tick whole leaderboard; tick only these 1–2
- **Kick response:** {'ok': True, 'message': 'Overnight break started'}


### 2026-09-16 ~06:12 Europe/Chisinau Asia TICK CONFIRM primary `e28w13_rc6_cap1200_flat23_mb275` — **REJECT**
- **Status:** CONFIRMED (softer vs 5m) · **REJECT** — does not beat KEEP `e30w13_rc6_cap1000_flat23_mb275`
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=28 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1200 · flatten_hour=23 · min_break=275 · SL1000/TP2000 · trail off
- **Ticks:** 117t · 59.0% wins · +78941.7 pts · **PF 2.67**
- **exits:** {'flatten': 12, 'tp': 58, 'sl': 47} · **entries:** {'ema_touch': 112, 'higher_close': 5}
- **skipped:** no_break 216, no_pullback 96
- **vs 5m screen:** PF2.768/+81726.6 n117 win59.8% → ΔPF -0.098 · Δpts -2784.9 · Δwin -0.8pp — softer vs 5m
- **vs KEEP `e30w13_rc6_cap1000_flat23_mb275` ticks:** PF2.72/+74440.3 n109 win59.6% → ΔPF -0.050 · Δpts +4501.4 · Δn +8
- **regime rollups:** 2025 74t 59.5% +46942; 2026 43t 58.1% +32000
- **by_month (compact):** 2025-01 11t 81.8% +9281 PF5.64 | 2025-02 6t 83.3% +7798 PF8.8 | 2025-03 5t 80.0% +6218 PF7.22 | 2025-04 4t 75.0% +5000 PF6.0 | 2025-05 6t 66.7% +6000 PF4.0 | 2025-06 6t 50.0% +3000 PF2.0 | 2025-07 3t 33.3% +0 PF1.0 | 2025-08 7t 42.9% +952 PF1.3 | 2025-09 6t 50.0% +1692 PF1.56 | 2025-10 7t 71.4% +8000 PF5.0 | 2025-11 8t 37.5% +1000 PF1.2 | 2025-12 5t 20.0% -2000 PF0.5 | 2026-01 5t 100.0% +10000 PFNone | 2026-02 5t 60.0% +4000 PF3.0 | 2026-03 6t 50.0% +3000 PF2.0 | 2026-04 5t 20.0% -2000 PF0.5 | 2026-05 6t 83.3% +9000 PF10.0 | 2026-06 5t 60.0% +4000 PF3.0 | 2026-07 9t 33.3% +0 PF1.0 | 2026-08 2t 100.0% +4000 PFNone
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T025721Z_47c706d1.json
- **Conclusion:** KEEP remains `e30w13_rc6_cap1000_flat23_mb275` (ticks PF2.72/+74440 n109 win59.6%). Challenger `e28w13_rc6_cap1200_flat23_mb275` rejected. Runner `e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200` tick **running** (only remaining of 1–2 queue). STOP auto-ticking leaderboard. No new 5m grid while runner ticks. Ask before any reaktor push.


### 2026-09-16 ~06:42 GTB Daylight Time Asia TICK CONFIRM runner `e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200` — **PROMOTE (NEW KEEP)**
- **Status:** CONFIRMED (matches 5m) → **PROMOTE** — beats OLD KEEP `e30w13_rc6_cap1000_flat23_mb275` on PF rule (ΔPF +0.050 > +0.02)
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1000 · flatten_hour=23 · min_break=275 · **SL1000/TP2200** · trail off
- **Ticks:** 109t · 58.7% wins · +78196.6 pts · **PF 2.77**
- **exits:** {'flatten': 14, 'tp': 51, 'sl': 44} · **entries:** {'ema_touch': 105, 'higher_close': 4}
- **skipped:** no_break 216, no_pullback 104
- **vs 5m screen:** PF2.766/+78074.9 n109 win58.7% → ΔPF +0.004 · Δpts +121.7 · Δwin +0.0pp — confirmed
- **vs OLD KEEP `e30w13_rc6_cap1000_flat23_mb275` ticks:** PF2.72/+74440.3 n109 win59.6% → ΔPF +0.05 · Δpts +3756.3 · Δn +0
- **regime rollups:** 2025 69t 58.0% +41396.6; 2026 40t 60.0% +36800.0
- **by_month (compact):** 2025-01 11t 90.9% +13146 PF14.15 | 2025-02 5t 80.0% +7118 PF8.12 | 2025-03 5t 80.0% +5155 PF6.16 | 2025-04 4t 75.0% +1876 PF2.88 | 2025-05 5t 60.0% +4600 PF3.3 | 2025-06 6t 50.0% +3600 PF2.2 | 2025-07 3t 33.3% +200 PF1.1 | 2025-08 5t 40.0% +152 PF1.07 | 2025-09 6t 50.0% +2150 PF1.72 | 2025-10 7t 71.4% +9000 PF5.5 | 2025-11 7t 28.6% -600 PF0.88 | 2025-12 5t 0.0% -5000 PF0.0 | 2026-01 5t 100.0% +11000 PFNone | 2026-02 5t 80.0% +7800 PF8.8 | 2026-03 4t 25.0% -800 PF0.73 | 2026-04 5t 20.0% -1800 PF0.55 | 2026-05 6t 83.3% +10000 PF11.0 | 2026-06 5t 60.0% +4600 PF3.3 | 2026-07 9t 44.4% +3800 PF1.76 | 2026-08 1t 100.0% +2200 PFNone
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T033823Z_5b3b1ac0.json
- **Conclusion:** **NEW KEEP** `e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200` (ticks PF2.77/+78197 n109 win58.7%). OLD `e30w13_rc6_cap1000_flat23_mb275` demoted (still volume-ish baseline). STOP auto-ticking. Kicked EXPAND_V8 5m grid around TP2200 pocket (pid 2884, workers=4, ~159 cells). Ask before any reaktor push.

- **Note:** first EXPAND_V8 launch used system Python (missing tzdata) and aborted; relaunched with `.venv\Scripts\python.exe` pid 12268 workers=4, cells=159 — healthy cells streaming.


### 2026-09-16 ~07:07 GTB Daylight Time Asia EXPAND_V8 5m SCORE + tick kick
- **Grid:** overnight_5m_grid_20260916T034241Z.json finished 159/159 cells · data_source=candles_5m · workers=4 (pid 12268 done ~06:43)
- **Current KEEP (ticks):** e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200 · 109t · 58.7% · +78197 · **PF 2.77**
- **TOP PF (5m):**
  - e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200_mbc12: PF 3.169 / +69892.3 / n87 / 62.1%
  - e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
  - e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200_hold16: PF 2.771 / +78322.9 / n109 / 58.7%
  - e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200_hold18: PF 2.771 / +78322.9 / n109 / 58.7%
  - KEEP_e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200: PF 2.766 / +78074.9 / n109 / 58.7%
  - e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200: PF 2.766 / +78074.9 / n109 / 58.7%
  - e30w13_rc6_cap1000_flat23_mb270_sl1000_tp2200: PF 2.766 / +78074.9 / n109 / 58.7%
  - e30w13_rc6_cap1000_flat23_mb275_sl1000_tp2200: PF 2.766 / +78074.9 / n109 / 58.7%
- **TOP pts (5m):**
  - e28w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.726 / +83264.1 / n117 / 58.1%
  - e28w14_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.610 / +82464.1 / n121 / 57.0%
  - e28w13_rc6_cap1000_flat23_mb275_sl1000_tp2200: PF 2.698 / +81903.0 / n116 / 57.8%
  - e28w14_rc6_cap1000_flat23_mb275_sl1000_tp2200: PF 2.583 / +81103.0 / n120 / 56.7%
  - OLD_e30w13_rc6_cap1000_flat23: PF 2.650 / +80344.4 / n121 / 58.7%
  - e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
  - e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200_mbc20: PF 2.387 / +79364.9 / n131 / 55.7%
  - e30w13_rc6_cap1000_flat23_mb250_sl1000_tp2200: PF 2.753 / +79274.9 / n111 / 58.6%
- **Notable thin:** e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200_mbc12 PF3.169/+69892.3 n87 win62.1% — **not ticking** (thinner vs KEEP)
- **PRIMARY KEEP candidate (tick NOW workers=1):** e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200 5m PF2.796/+79436.0 n110 win59.1% (ΔPF +0.030 Δpts +1361.1 vs KEEP 5m)
- **RUNNER:** none (hold16/18 only ΔPF +0.005; e28 pts-leaders ΔPF ≤ -0.04 — skip)
- **Policy:** STOP auto-tick whole leaderboard; tick only this 1
- **Kick response:** {'ok': True, 'message': 'Overnight break started'}



### 2026-09-16 ~07:40 GTB Daylight Time Asia TICK CONFIRM primary `e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200` — **PROMOTE (NEW KEEP)**
- **Status:** CONFIRMED (matches 5m) → **PROMOTE** — beats OLD KEEP `e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200` on PF rule (ΔPF +0.030 > +0.02)
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=**1200** · flatten_hour=23 · min_break=275 · SL1000/TP2200 · trail off
- **Ticks:** 110t · 59.1% wins · +79549.3 pts · **PF 2.80**
- **exits:** {'flatten': 15, 'tp': 51, 'sl': 44} · **entries:** {'ema_touch': 105, 'higher_close': 5}
- **skipped:** no_break 216, no_pullback 103
- **vs 5m screen:** PF2.796/+79436.0 n110 win59.1% → ΔPF +0.004 · Δpts +113.3 · Δwin +0.0pp — confirmed
- **vs OLD KEEP `e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200` ticks:** PF2.77/+78196.6 n109 win58.7% → ΔPF +0.030 · Δpts +1352.7 · Δn +1
- **regime rollups:** 2025 70t 58.6% +42749.3; 2026 40t 60.0% +36800.0
- **by_month (compact):** 2025-01 11t 90.9% +13146 PF14.15 | 2025-02 6t 83.3% +8471 PF9.47 | 2025-03 5t 80.0% +5155 PF6.16 | 2025-04 4t 75.0% +1876 PF2.88 | 2025-05 5t 60.0% +4600 PF3.3 | 2025-06 6t 50.0% +3600 PF2.2 | 2025-07 3t 33.3% +200 PF1.1 | 2025-08 5t 40.0% +152 PF1.07 | 2025-09 6t 50.0% +2150 PF1.72 | 2025-10 7t 71.4% +9000 PF5.5 | 2025-11 7t 28.6% -600 PF0.88 | 2025-12 5t 0.0% -5000 PF0.0 | 2026-01 5t 100.0% +11000 PFNone | 2026-02 5t 80.0% +7800 PF8.8 | 2026-03 4t 25.0% -800 PF0.73 | 2026-04 5t 20.0% -1800 PF0.55 | 2026-05 6t 83.3% +10000 PF11.0 | 2026-06 5t 60.0% +4600 PF3.3 | 2026-07 9t 44.4% +3800 PF1.76 | 2026-08 1t 100.0% +2200 PFNone
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T042738Z_d7c5c486.json
- **Conclusion:** **NEW KEEP** `e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200` (ticks PF2.80/+79549 n110 win59.1%). OLD `e30w13_rc6_cap1000_mb275_flat23_sl1000_tp2200` demoted. STOP auto-ticking. Kick EXPAND_V9 5m grid around cap1200 pocket. Ask before any reaktor push.


### 2026-09-16 ~07:42 GTB Daylight Time Asia EXPAND_V9 5m SCORE (no tick)
- **Grid:** overnight_5m_grid_20260916T044051Z.json finished 163/163 cells · data_source=candles_5m · workers=4 (pid 12388 done)
- **Current KEEP (ticks):** e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200 · 110t · 59.1% · +79549 · **PF 2.80**
- **TOP PF (5m):**
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_mbc12: PF 3.211 / +71253.4 / n88 / 62.5%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_hold16: PF 2.802 / +79684.0 / n110 / 59.1%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_hold18: PF 2.802 / +79684.0 / n110 / 59.1%
  - KEEP_e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
  - e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
  - e30w13_rc6_cap1300_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
  - e30w13_rc6_cap1400_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
  - e30w13_rc6_cap1500_flat23_mb275_sl1000_tp2200: PF 2.796 / +79436.0 / n110 / 59.1%
- **TOP pts (5m):**
  - e28w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.726 / +83264.1 / n117 / 58.1%
  - e28w13_rc6_cap1400_flat23_mb275_sl1000_tp2200: PF 2.726 / +83264.1 / n117 / 58.1%
  - e28w14_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.610 / +82464.1 / n121 / 57.0%
  - e28w14_rc6_cap1400_flat23_mb275_sl1000_tp2200: PF 2.610 / +82464.1 / n121 / 57.0%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_mbc20: PF 2.411 / +80726.0 / n132 / 56.1%
  - OLD_e30w13_rc6_cap1000_flat23: PF 2.650 / +80344.4 / n121 / 58.7%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_hold16: PF 2.802 / +79684.0 / n110 / 59.1%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_hold18: PF 2.802 / +79684.0 / n110 / 59.1%
- **Notable thin:** e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_mbc12 PF3.211/+71253.4 n88 win62.5% — **not ticking** (thinner vs KEEP)
- **PRIMARY:** e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_hold16 5m PF2.802/+79684.0 (ΔPF +0.006) — **not ticking** (edge too small)
- **RUNNER:** none
- **Policy:** STOP auto-tick whole leaderboard; tick only 1–2 finals
- **Kick response:** none (no tick)

### 2026-09-16 ~15:20 Europe/Bucharest Asia EXPAND_V10_KEEP_FILLPATH kick
- **API:** online (health ok); overnight idle (prior KEEP tick done); no finishing tick to score this fire
- **Current KEEP (ticks):** `e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200` · 110t · 59.1% · +79549 · **PF 2.80**
- **Prior:** EXPAND_V9 scored earlier — no tick (hold16 ΔPF +0.006; edges thin/tiny); stop_auto_tick held
- **New grid:** EXPAND_V10_KEEP_FILLPATH via `scripts/overnight_5m_grid.py --workers 4` · window 2025-01-01→2026-09-01 · candles_5m · **113 cells** · pid **6140**
- **Axes (new vs V9):** timeout_max_ema_dist / timeout_min_break / timeout_min_pullback (+combos); skip_late_short; SL:TP≈1:1.5 family; e28/e32 volume×cap250/1000/1200; asia_end 5/6/7; ar; week2 filter×te; sl_cap. Skip BE. No full V9 re-run.
- **Early stream (healthy):** KEEP 5m PF2.796/+79436 n110; OLD cap1000_tp2200 PF2.766/+78075; ted* identical to KEEP so far (timeout filter may be inert on this seed)
- **Policy:** STOP auto-tick whole leaderboard; after V10 finishes score top PF/pts → tick only 1–2 KEEP candidates if ΔPF meaningful
- **Tick confirm this fire:** none
- Ask before any reaktor push.


### 2026-09-16 ~15:22 Europe/Bucharest Asia EXPAND_V10 5m SCORE + tick kick
- **Grid:** overnight_5m_grid_20260916T121929Z.json finished 113/113 cells · data_source=candles_5m · workers=4 (pid 6140 done ~15:20)
- **Current KEEP (ticks):** e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200 · 110t · 59.1% · +79549 · **PF 2.80**
- **TOP PF (5m):**
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_4000: PF 3.584 / +72920.3 / n81 / 64.2%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls7_4000: PF 3.331 / +72770.0 / n86 / 62.8%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_3000: PF 3.309 / +76720.3 / n90 / 62.2%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_w2f_te30: PF 3.203 / +66586.8 / n82 / 62.2%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_w2f_te25: PF 3.187 / +63408.5 / n78 / 62.8%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2000: PF 3.074 / +77186.8 / n97 / 60.8%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls7_3000: PF 3.053 / +74370.0 / n94 / 60.6%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_w2f_te40: PF 3.027 / +69351.5 / n90 / 61.1%
  - e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls7_2000: PF 3.010 / +76836.5 / n99 / 60.6%
  - KEEP: PF 2.796 / +79436.0 / n110 / 59.1%
- **TOP pts (5m):**
  - e28w13_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.726 / +83264.1 / n117 / 58.1%
  - e28w14_rc6_cap1200_flat23_mb275_sl1000_tp2200: PF 2.610 / +82464.1 / n121 / 57.0%
  - e28w13_rc6_cap1000_flat23_mb275_sl1000_tp2200: PF 2.698 / +81903.0 / n116 / 57.8%
  - e30w13_rc6_cap1200_mb275_flat23_sl1300_tp2200: PF 2.617 / +81153.0 / n110 / 62.7%
  - e28w14_rc6_cap1000_flat23_mb275_sl1000_tp2200: PF 2.583 / +81103.0 / n120 / 56.7%
- **Notable thin / skip:** sls*_4000 and w2f_te* n78–86 (and most n<90) — **not ticking** (thinner vs KEEP n110; same policy as mbc12)
- **Inert:** timeout_max_ema_dist / timeout_min_break / timeout_min_pullback / sl_cap / asia_end identical or worse vs KEEP on this seed
- **SL:TP≈1:1.5:** all worse PF than KEEP on same n110 (e.g. sl1100/tp1650 PF2.30; sl1200/tp1800 PF2.45)
- **e28 pts-leaders:** ΔPF ≤ -0.07 — skip (prior e28 tick REJECT pattern)
- **PRIMARY KEEP candidate (tick NOW workers=1):** e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_**sls5_2000** 5m PF3.074/+77186.8 n97 win60.8% (fill-path skip_late_short; ΔPF +0.278 vs KEEP 5m; closest volume among high-PF)
- **RUNNER (queued next fire, not auto):** e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_**sls7_2000** 5m PF3.010/+76836.5 n99 win60.6%
- **Policy:** STOP auto-tick whole leaderboard; tick only these 1–2 fill-path finals
- **Kick response:** {'ok': True, 'message': 'Overnight break started'} (ticks downloading; sls=5/2000)



### 2026-09-16 ~15:56 Europe/Bucharest Asia TICK CONFIRM primary `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2000` — **PROMOTE (NEW KEEP)**
- **Status:** CONFIRMED (matches 5m) → **PROMOTE** — beats OLD KEEP `e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200` on PF primary (ΔPF +0.28 >> +0.02)
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1200 · flatten_hour=23 · min_break=275 · SL1000/TP2200 · trail off · **skip_late_short wait=5 / asia_pts=2000** · sl_cap=2000
- **Ticks:** 97t · 60.8% wins · +77281.1 pts · **PF 3.08**
- **exits:** {'tp': 48, 'flatten': 12, 'sl': 37} · **entries:** {'ema_touch': 92, 'higher_close': 5}
- **skipped:** no_break 216, no_pullback 103, late_short 13 (total 332)
- **vs 5m screen:** PF3.074/+77186.8 n97 win60.8% → ΔPF +0.006 · Δpts +94.3 · Δwin +0.0pp — confirmed
- **vs OLD KEEP ticks PF2.80/+79549 n110:** ΔPF **+0.28** · Δpts −2267.9 · Δn −13 · Δwin +1.7pp — PF champ; pts slightly thinner on fewer trades (filter cut 13)
- **regime rollups:** 2025 57t 61.4% +40481.1; 2026 40t 60.0% +36800.0
- **by_month (compact):** 2025-01 9t 88.9% +10651 PF11.65 | 2025-02 5t 80.0% +6271 PF7.27 | 2025-03 4t 75.0% +2955 PF3.96 | 2025-04 4t 75.0% +1876 PF2.88 | 2025-05 4t 75.0% +5600 PF6.6 | 2025-06 4t 75.0% +5600 PF6.6 | 2025-07 3t 33.3% +200 PF1.1 | 2025-08 2t 50.0% +1979 PF9.96 | 2025-09 5t 40.0% −51 PF0.98 | 2025-10 6t 83.3% +10000 PF11.0 | 2025-11 7t 28.6% −600 PF0.88 | 2025-12 4t 0.0% −4000 PF0.0 | 2026-01 5t 100.0% +11000 PFNone | 2026-02 5t 80.0% +7800 PF8.8 | 2026-03 4t 25.0% −800 PF0.73 | 2026-04 5t 20.0% −1800 PF0.55 | 2026-05 6t 83.3% +10000 PF11.0 | 2026-06 5t 60.0% +4600 PF3.3 | 2026-07 9t 44.4% +3800 PF1.76 | 2026-08 1t 100.0% +2200 PFNone
- **Result:** C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T124552Z_9d22b539.json
- **Conclusion:** **NEW KEEP** `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2000` (ticks **PF3.08/+77281 n97** win60.8%). OLD `e30w13_rc6_cap1200_flat23_mb275_sl1000_tp2200` demoted (still volume/pts reference). STOP auto-ticking. Queue runner tick **sls7_2000** (5m PF3.010/+76836.5 n99) as 2nd of 1–2 fill-path finals. Ask before any reaktor push.



### 2026-09-16 ~15:56 Europe/Bucharest Asia TICK kick runner sls7_2000
- **After:** NEW KEEP sls5_2000 scored (ticks PF3.08/+77281 n97); stop_auto_tick held
- **Kick:** e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_**sls7_2000** ticks workers=1 (skip_late_short wait=7 / asia_pts=2000); window 2025-01-01	o2026-09-01
- **Kick response:** {ok: True, message: Overnight break started}; phase=download early
- **Policy:** 2nd of 1-2 fill-path finals only; no full leaderboard auto-tick; no new 5m grid this fire
- Ask before any reaktor push.

### 2026-09-16 ~18:03 Europe/Bucharest Asia TICK CONFIRM runner `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls7_2000` — **REJECT**
- **Status:** CONFIRMED vs 5m screen → **REJECT** — does not beat NEW KEEP `sls5_2000` on PF primary
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia 1–6 · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1200 · flatten_hour=23 · min_break=275 · SL1000/TP2200 · trail off · **skip_late_short wait=7 / asia_pts=2000** · sl_cap=2000
- **Ticks:** 99t · 60.6% wins · +76938.6 pts · **PF 3.01**
- **exits:** {'tp': 48, 'flatten': 13, 'sl': 38} · **entries:** {'ema_touch': 94, 'higher_close': 5}
- **skipped:** no_break 216, no_pullback 103, late_short 11 (total 330)
- **Timing:** started 2026-09-16T12:56:00Z · finished 2026-09-16T13:20:32Z
- **vs 5m screen:** PF3.010/+76836.5 n99 win60.6% → ΔPF ~0 · Δpts +102 · confirmed
- **vs KEEP ticks `sls5_2000` PF3.08/+77281 n97:** ΔPF **−0.07** · Δpts −2342.5 · Δn +2 · Δwin −0.2pp — worse PF and pts
- **Conclusion:** KEEP unchanged `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2000` (ticks **PF3.08/+77281 n97**). Runner sls7_2000 demoted. Both fill-path finals done. STOP auto-tick. Next: EXPAND_V11_SLS5_POCKET 5m denser skip_late_short + light neighbors on KEEP+sls5. Ask before any reaktor push.

### 2026-09-16 ~18:03 Europe/Bucharest Asia EXPAND_V11_SLS5_POCKET kick
- **API:** online; overnight idle after runner sls7_2000 tick REJECT (KEEP stays sls5_2000 ticks PF3.08/+77281 n97)
- **New grid:** EXPAND_V11_SLS5_POCKET via `scripts/overnight_5m_grid.py --workers 4` · window 2025-01-01→2026-09-01 · candles_5m · **58 cells** · pid **14936**
- **Axes:** dense skip_late_short wait∈{3,4,5,6,8} × asia∈{1200,1500,1800,2000,2200,2500} on KEEP pocket; light neighbors on KEEP+sls5 (flatten 22/23/24, mb 250–325, wait 11–14, ema 28–32, rc×cap). Skip BE / V10-inert redo.
- **Policy:** STOP auto-tick; after V11 finishes score top PF/pts → tick only 1–2 KEEP candidates if ΔPF meaningful vs KEEP
- **Tick confirm this fire:** none (runner already scored REJECT)
- Ask before any reaktor push.


### 2026-09-16 19:28 EXPAND_ASIA_MB_WICK_TOP3 5m done (84 cells)
- Grid: overnight_5m_grid_20260916T162230Z.json
- Winner: **KEEP_sls5 asia 0-6** 5m PF **3.159** / +78187 n96 (vs BASE asia1-6 PF3.074). Tick confirm kicked.
- Min-break: mb250 ~PF3.096 near BASE; higher mb hurts.
- Wick ON: more pts but PF drops to ~2.66 — REJECT for PF goal.
- Later asia ends (7–10) collapse hard.



### 2026-09-16 ~21:31 Europe/Bucharest Asia TICK CONFIRM `KEEP_sls5 asia0-6` (run `20260916T165227Z_adfae225`) — **PROMOTE (NEW KEEP)**
- **Status:** CONFIRMED vs 5m screen → **PROMOTE** — beats prior KEEP `sls5_2000` asia1-6 on PF primary
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia **0–6** · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1200 · flatten_hour=23 · min_break=275 · SL1000/TP2200 · trail off · **skip_late_short wait=5 / asia_pts=2000** · sl_cap=2000 · wick=off
- **Ticks:** 96t · 61.5% wins · +78281.1 pts · **PF 3.16**
- **exits:** {'tp': 48, 'flatten': 12, 'sl': 36} · **entries:** {'ema_touch': 91, 'higher_close': 5}
- **skipped:** {'no_break': 218, 'late_short': 13, 'no_pullback': 102} (total 333)
- **Timing:** finished 2026-09-16T16:52:27.387580+00:00
- **vs 5m screen:** PF3.159/+78186.8 n96 → ΔPF +0.001 · Δpts +94.3 — confirmed
- **vs OLD KEEP ticks `sls5_2000` asia1-6 PF3.08/+77281.1 n97:** ΔPF **+0.08** · Δpts +1000.0 · Δn -1 — PF champ; slightly fewer trades
- **regime rollups:** 2025 57t 61.4% +40481.2; 2026 39t 61.5% +37800.1
- **by_month (compact):** 2025-01 9t 88.9% +10651 | 2025-02 5t 80.0% +6270 | 2025-03 4t 75.0% +2955 | 2025-04 4t 75.0% +1876 | 2025-05 4t 75.0% +5600 | 2025-06 4t 75.0% +5600 | 2025-07 3t 33.3% +200 | 2025-08 2t 50.0% +1979 | 2025-09 5t 40.0% -50 | 2025-10 6t 83.3% +10000 | 2025-11 7t 28.6% -600 | 2025-12 4t 0.0% -4000 | 2026-01 5t 100.0% +11000 | 2026-02 5t 80.0% +7800 | 2026-03 3t 33.3% +200 | 2026-04 5t 20.0% -1800 | 2026-05 6t 83.3% +10000 | 2026-06 5t 60.0% +4600 | 2026-07 9t 44.4% +3800 | 2026-08 1t 100.0% +2200
- **Result:** `C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T165227Z_adfae225.json`
- **Conclusion:** **NEW KEEP** `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2000` with **asia 0–6** (ticks **PF3.16/+78281 n96** win61.5%). Prior asia1-6 sls5 demoted. STOP auto-tick.

### 2026-09-16 ~21:31 Europe/Bucharest Asia EXPAND_V11_SLS5_POCKET 5m scored (58 cells) — pending fill-path
- **Grid:** `overnight_5m_grid_20260916T150711Z.json` (asia1-6 KEEP pocket; finished earlier ~18:07)
- **TOP5 (5m PF):**
  - `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls4_2200`: 5m PF3.311/+76786.8 n91 win62.6%
  - `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls4_2500`: 5m PF3.311/+76786.8 n91 win62.6%
  - `KEEP_sls5_2000_w11`: 5m PF3.31/+72120.3 n85 win62.4%
  - `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2200`: 5m PF3.248/+79186.8 n95 win62.1%
  - `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls5_2500`: 5m PF3.248/+79186.8 n95 win62.1%
- **Note:** V11 tops sit on asia **1–6**; NEW KEEP is asia **0–6**. Best screened challenger = `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls4_2200` 5m PF3.311/+76786.8 n91 (ΔPF vs NEW KEEP 5m asia0-6 PF3.159 ≈ +0.152).
- **Tick:** kicked `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls4_2200` ticks workers=1 (asia1-6 + sls4/2200); response={'ok': True, 'message': 'Overnight break started'}
- **Policy:** STOP auto-tick; this is the single fill-path runner after asia0-6 promote. Ask before reaktor push.



### 2026-09-17 ~17:59 Europe/Bucharest Asia TICK CONFIRM `sls4_2200` asia1-6 (run `20260916T190125Z_7d206323`) — **PROMOTE (NEW KEEP)**
- **Status:** CONFIRMED vs 5m screen → **PROMOTE** — beats prior KEEP `sls5_2000` asia0-6 on PF primary
- **Window:** 2025-01-01 → 2026-09-01 · data_source=ticks · workers=1
- **Params:** asia **1–6** · ema=30 · wait=13 · wait_from_break · timeout=market · uhc · rc=6 · resume_max_break_pts=1200 · flatten_hour=23 · min_break=275 · SL1000/TP2200 · trail off · **skip_late_short wait=4 / asia_pts=2200** · sl_cap=2000 · wick=off · max_break=15 · pullback=required
- **Ticks:** 91t · 62.6% wins · +76881.1 pts · **PF 3.31**
- **exits:** {"tp": 46, "flatten": 12, "sl": 33} · **entries:** {"ema_touch": 86, "higher_close": 5}
- **skipped:** {"no_break": 216, "late_short": 19, "no_pullback": 103} (total 338)
- **Timing:** started 2026-09-16T18:35:42Z · finished 2026-09-16T19:01:25.245795+00:00
- **vs 5m screen:** PF3.311/+76786.8 n91 → ΔPF −0.001 · Δpts +94.3 — confirmed
- **vs OLD KEEP ticks `sls5_2000` asia0-6 PF3.16/+78281.1 n96:** ΔPF **+0.15** · Δpts −1400.0 · Δn −5 — PF champ; thinner book
- **regime rollups:** 2025 52t 63.5% +39081.1; 2026 39t 61.5% +37800.0
- **by_month (compact):** 2025-01 8t 100.0% +11651 | 2025-02 3t 100.0% +5071 | 2025-03 4t 75.0% +2955 | 2025-04 4t 75.0% +1876 | 2025-05 4t 75.0% +5600 | 2025-06 4t 75.0% +5600 | 2025-07 3t 33.3% +200 | 2025-08 1t 0.0% -221 | 2025-09 4t 50.0% +950 | 2025-10 6t 83.3% +10000 | 2025-11 7t 28.6% -600 | 2025-12 4t 0.0% -4000 | 2026-01 5t 100.0% +11000 | 2026-02 5t 80.0% +7800 | 2026-03 4t 25.0% -800 | 2026-04 5t 20.0% -1800 | 2026-05 6t 83.3% +10000 | 2026-06 4t 75.0% +5600 | 2026-07 9t 44.4% +3800 | 2026-08 1t 100.0% +2200
- **Result:** `C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260916T190125Z_7d206323.json`
- **Conclusion:** **NEW KEEP** `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls4_2200` with **asia 1–6** (ticks **PF3.31/+76881 n91** win62.6%). Prior asia0-6 sls5 demoted on PF. STOP auto-tick; no further V11 runners (sls4_2500 5m duplicate; stop_auto_tick). Ask before reaktor push.


### 2026-09-17 ~18:32 Europe/Bucharest Asia EXPAND TRAIL_NEAR_TP_THEN_LARGER_TP 5m scored (52 cells)
- **Grid:** `overnight_5m_grid_20260917T152445Z.json` · tag `TRAIL_NEAR_TP_THEN_LARGER_TP` · seed `sls4_2200_asia1-6` (KEEP ticks PF3.31) · goal more pts with PF>=3 · candles_5m
- **Baseline:** `WINNER_BASE_trail_off` 5m PF **3.311** / +76786.8 n91
- **TOP by PF (5m):**
  - `tp2200_arm2000_tr200`: PF **3.802** / +90299 n91 win63.7% (ΔPF **+0.49** vs BASE)
  - `tp2400_arm2000_tr200`: PF **3.802** / +90299 n91 (duplicate metrics; higher TP same path)
  - `tp2400/2500/2600_arm2200_tr200`: PF **3.700** / +89693 n91
- **TOP PF>=3 by pts:** `tp2600_arm2400_tr200` PF3.585 / +91062 n91
- **Trail-off TP bump alone:** tp2400 PF3.234; tp2500 PF2.928 (REJECT); tp2600 PF3.021 — trail is doing the work, not larger fixed TP
- **Note:** trail arm near TP + tight trail (200) inflates PF/pts via partial locks; treat as trail-class challenger vs full-TP KEEP
- **Tick confirm:** kicked **only** `tp2200_arm2000_tr200` (workers=1, ticks, 2025-01→2026-09) — PF champ, same TP as KEEP. Pending runner if promotes: `tp2600_arm2400_tr200` (pts champ). Skip duplicate tp2400_arm2000_tr200.
- **Policy:** STOP auto-tick after this kick. Ask before reaktor push.

### 2026-09-17 ~19:25 Europe/Bucharest Asia TRAIL tp2200_arm2000_tr200 tick REJECT
- **Run:** `20260917T160655Z_684c49bc` · ticks 2025-01→2026-09 · seed KEEP `sls4_2200 asia1-6` + trail arm2000/tr200 (5m screen PF3.802/+90299)
- **Ticks:** PF **3.33** / +75162 n91 win63.7% (exits trail31/fl10/tp18/sl32; trail_armed 49/53.8%; avg_win 1851 / avg_loss −976)
- **vs KEEP** trail-off `sls4_2200 asia1-6` ticks PF3.31/+76881 n91: ΔPF **+0.02**, Δpts **−1720** — 5m edge collapsed; pts worse
- **Conclusion:** **REJECT** trail upgrade. KEEP unchanged `e30w13_rc6_cap1200_mb275_flat23_sl1000_tp2200_sls4_2200` asia **1-6** ticks PF3.31/+76881. Skip pending pts-champ `tp2600_arm2400_tr200` (PF champ did not promote). STOP auto-tick; no new 5m grid this fire. Ask before reaktor push.


### 2026-09-21 CROSS_ASIA0_SIDE_SPLIT (5m) — asia 0–6 × KEEP lineage + side_filter
Window 2025-01-01→2026-09-01. Base = KEEP (asia1–6, ema30, wait13, rc6, cap1200, flat23, mb275, SL1000/TP2200, sls4/2200).

| name | n | win% | sum_pts | PF |
|------|---|------|---------|-----|
| asia0_6_sls4_2200_side_short | 32 | 65.6 | 33066.5 | **4.006** |
| KEEP_side_short | 33 | 63.6 | 32066.5 | 3.672 |
| asia0_6_KEEP_mb250 | 90 | 63.3 | 78625.7 | **3.440** |
| asia0_6_sls4_2200 | 90 | 63.3 | 77786.8 | **3.414** |
| asia0_6_KEEP_cap1000 | 89 | 62.9 | 76425.7 | 3.372 |
| asia0_6_sls3_2200 | 89 | 62.9 | 75586.8 | 3.346 |
| asia0_6_sls5_2200 | 94 | 62.8 | **80186.8** | 3.343 |
| KEEP_asia1_6_sls4_2200 | 91 | 62.6 | 76786.8 | 3.311 |
| REF_asia0_6_sls5_2000 | 96 | 61.5 | 78186.8 | 3.159 |
| KEEP / asia0_6 / REF side_long | 58 | 62.1 | 44720.3 | 3.107 |
| asia1_5_sls4_2200 | 89 | 56.2 | 60538.5 | 2.612 REJECT |
| asia0_7_sls4_2200 | 98 | 56.1 | 62004.1 | 2.469 REJECT |

**Conclusions**
- Cross-breed works: **asia 0–6 + KEEP (sls4/2200)** beats asia1–6 KEEP on 5m (PF 3.41 vs 3.31, similar pts).
- Best both-side PF: **asia0–6 + mb250** (PF 3.44 / +78.6k). Most pts both-side: **asia0–6 + sls5/2200** (+80.2k / PF 3.34).
- Side split: **shorts carry higher PF** (~3.7–4.0) but ~half the sample (n≈32–38) and ~33k pts; longs ~58 trades / PF 3.11 / +44.7k. Combined still better for total pts.
- asia 1–5 and 0–7 rejected.
- Next: tick-confirm asia0_6_KEEP_mb250 and asia0_6_sls4_2200 (and maybe sls5/2200 for pts).


### 2026-09-21 near-box timeout probe (5m, KEEP seed, close-only gate)
Idea: on required-mode `no_pullback` timeout, if last N wait **closes** stay within D pts of asia_high (UP) / asia_low (DOWN), take fill (`near_box_timeout`) instead of skip.
Pool: 103 no_pullback skips on KEEP (n=91 traded).

| N | D | n | near fills | PF | sum_pts | vs KEEP |
|---|---|---|------------|-----|---------|--------|
| — | off | 91 | 0 | **3.311** | 76787 | baseline |
| 5 | 500 | 95 | 4 | 3.248 | 79187 | +4 trades, PF↓ |
| 10 | 500 | 93 | 2 | 3.279 | 77987 | tiny |
| 10 | 800 | 104 | 13 | **3.063** | **82987** | only ≥3 PF with +13 trades |
| 5 | 800 | 109 | 18 | 2.836 | 81187 | PF break |
| 5 | 1000 | 117 | 26 | 2.658 | 81633 | REJECT |
| 5 | 1500+ | 131+ | 40+ | ≤2.32 | ~78–79k | REJECT |

**Conclusion:** hugging the box edge at D=500 barely adds trades. Loosening to D=800 / N=10 adds ~13 trades and keeps PF≈3.06 / +83k — interesting but not a free lunch. Wider bands wreck PF. Side-filter still rejected (trade count). Code on branch `feat/near-box-timeout` (not pushed).

### 2026-09-21 ~09:01 Europe/Bucharest Asia TICK CONFIRM `asia0-6 + sls4/2200` (run `20260921T055117Z_3c14cf2d`) — **PROMOTE (NEW KEEP)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb275**, SL1000/TP2200, **sls4/2200**, trail off, timeout market, wait_from_break, pullback required, side both.
- **Result:** n90 · win63.3% · **+77881** · **PF 3.42** (avg +865 / win +1932 / loss −976).
- **vs OLD KEEP ticks asia1–6 sls4/2200 PF3.31/+76881 n91:** ΔPF **+0.11** · Δpts **+1000** · Δn −1 — PF champ; slightly thinner book.
- **vs 5m screen asia0_6_sls4_2200 PF3.414/+77787:** tick holds (PF 3.42 / +77.9k).
- **Conclusion:** **NEW KEEP** = asia **0–6** + KEEP lineage (ema30 wait13 rc6 cap1200 flat23 mb275 SL1000/TP2200 sls4/2200). Prior asia1–6 demoted on PF.
- **Next:** tick-confirm **asia0-6 + mb250** (5m best both-side PF3.44/+78.6k). No side-split ticks. near-box still awaiting Igor direction (not pushed).


### 2026-09-21 near-box D=1000 + trend gate (5m, asia0–6 KEEP seed)
Seed: asia0–6 sls4/2200 mb275 (5m PF3.41/+77.8k n90). D fixed 1000.

| trend | N | n | near | PF | pts |
|-------|---|---|------|-----|-----|
| off | 5 | 116 | 26 | 2.714 | 82633 |
| off | 10 | 108 | 18 | 2.902 | 82187 |
| closes_dir | * | 90 | 0 | 3.414 | 77787 | too strict |
| net_ext | 10 | 102 | 12 | 3.085 | 81787 |
| outside | 7 | 106 | 16 | 3.042 | **84187** |
| **breakout** | **7/10** | **100** | **10** | **3.108** | 80587 |

breakout = net_ext AND still outside by min_break. Best PF among grown books. outside N=7 best pts at PF≥3.
Also: tick asia0–6+mb250 finished PF**3.44**/+78728 n90 — new PF champ vs sls4/2200 tick PF3.42.


### 2026-09-21 ~09:42 Europe/Bucharest Asia TICK CONFIRM sia0-6 + mb250 (run 20260921T062707Z_d85ff30d) — **PROMOTE (NEW KEEP / PF champ)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb250**, SL1000/TP2200, **sls4/2200**, trail off, timeout market, wait_from_break, pullback required, side both. data_source=ticks.
- **Result:** n90 · win63.3% · **+78728** · **PF 3.44** (avg +875 / win +1946 / loss −976). trail_armed 0.
- **vs prior tick KEEP asia0–6 sls4/2200 mb275 PF3.42/+77881 n90** (run 20260921T055117Z_3c14cf2d): ΔPF **+0.02** · Δpts **+847** · same n — new PF champ.
- **vs OLD asia1–6 sls4/2200 ticks PF3.31/+76881 n91:** ΔPF **+0.13** · Δpts **+1847** · Δn −1.
- **vs 5m screen asia0_6_KEEP_mb250 PF3.440/+78626:** tick holds exactly (PF 3.44 / +78.7k).
- **Conclusion:** **NEW KEEP** = asia **0–6** + mb**250** + KEEP lineage (ema30 wait13 rc6 cap1200 flat23 SL1000/TP2200 sls4/2200). Prior asia0–6 mb275 demoted on PF (still strong runner).
- **Next:** stop_auto_tick. Optional later: tick pts-runner asia0–6+sls5/2200 (5m +80.2k PF3.34) only if Igor asks. near-box still awaiting Igor (branch feat/near-box-timeout, not pushed). No side-split ticks.
### 2026-09-23 ~08:17 Europe/Bucharest — Asia KEEP tuning RESUMED (pts maximize / soft PF≥~2)

- **KEEP unchanged:** asia0-6+mb250 ticks `20260921T062707Z_d85ff30d` PF3.44/+78728 n90.
- **Goal:** grow sum_pts (aim ~2× ≈ +157k+, more better); soft PF floor ~2.0 (prefer ≥2.5). stop_auto_tick cleared.
- **Batch B IN FLIGHT (confirmed):** KEEP + skip_late_short_wait=5 / 2200, ticks, workers=2, window 2025-01→2026-09. Started 08:13 EEST; ~43% replay / 35 trades at 08:17 check.
- **Queue:** `results/_asia_queue_20260923.json` — after B: A near-box (gate on Lenovo feat) → C volume → D TP/trail.
- No reaktor / no push.


### 2026-09-23 ~09:25 Europe/Bucharest Asia TICK CONFIRM Batch B asia0-6 + sls5/2200 (run 20260923T053333Z_82819ad0) — PROMOTE (NEW KEEP / pts champ)
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb250**, SL1000/TP2200, **sls5/2200**, trail off, timeout market, wait_from_break, pullback required, side both. data_source=ticks. workers=2.
- **Result:** n94 · win62.8% · **+81128** · **PF 3.37** (avg +863 / win +1955 / loss −978). trail_armed 0. finished 2026-09-23T05:33Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T053333Z_82819ad0.json`.
- **vs prior KEEP ticks asia0–6 mb250 sls4/2200 PF3.44/+78728 n90** (run 20260921T062707Z_d85ff30d): ΔPF **−0.07** · Δpts **+2400** · Δn **+4** — pts lift at still-strong PF (goal = maximize pts, soft floor ≥~2.5).
- **vs 5m screen asia0-6+sls5/2200 ~+80.2k PF3.34:** tick holds / slightly better pts (+81.1k PF3.37).
- **Conclusion:** **NEW KEEP** = asia **0–6** + mb**250** + **sls5/2200** + KEEP lineage (ema30 wait13 rc6 cap1200 flat23 SL1000/TP2200). Prior sls4/2200 demoted on pts (still PF runner at 3.44).
- **Next:** Batch A tick-confirm near-box pts champ from 2026-09-21 5m (outside N=7 D=1000, +84.2k PF3.04) on NEW KEEP seed (ticks, workers=2). Then C volume / D TP-trail if needed. No reaktor / no push.


### 2026-09-23 ~10:26 Europe/Bucharest Asia TICK CONFIRM Batch A near-box outside N=7 D=1000 on KEEP sls5 (run `20260923T065659Z_4f318ec1`) — **PROMOTE (NEW KEEP / pts champ)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb250**, SL1000/TP2200, **sls5/2200**, **near_box_bars=7 / near_box_pts=1000 / near_box_trend=outside**, trail off, timeout market, wait_from_break, pullback required, side both. data_source=ticks. workers=2.
- **Result:** n110 · win60.0% · **+87528** · **PF 3.03** (avg +796 / win +1981 / loss −982). exits tp56 / flatten11 / sl43. finished 2026-09-23T06:56Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T065659Z_4f318ec1.json`.
- **vs prior KEEP ticks asia0–6 mb250 sls5/2200 (no near-box) PF3.37/+81128 n94** (run 20260923T053333Z_82819ad0): ΔPF **−0.34** · Δpts **+6400** · Δn **+16** — meaningful pts lift at PF still ≥2.5 (goal = maximize pts, soft floor ~2.5).
- **vs 5m near-box outside N7 D1000 ~+84.2k PF3.04 (2026-09-21):** tick holds / slightly better pts (+87.5k PF3.03).
- **Conclusion:** **NEW KEEP** = prior sls5 KEEP **+ near-box outside N=7 D=1000**. Prior no-near-box demoted on pts (still stronger PF at 3.37).
- **Next:** Batch C volume expand 5m screen on NEW KEEP seed (mb200–250 × wait11/13/15 × pullback preferred/required + max_break 18/20); then D TP/trail if needed. No reaktor / no push.


### 2026-09-23 ~10:31 Europe/Bucharest Asia Batch C VOLUME_EXPAND_C_KEEP_NB 5m (20 cells) — REJECT for KEEP
- **Grid:** `overnight_5m_grid_20260923T073107Z.json` · tag `VOLUME_EXPAND_C_KEEP_NB` · seed NEW KEEP (near-box outside N7 D1000 + sls5/2200) · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP:** n110 · PF **3.023** · **+87426** (matches ticks ~PF3.03/+87528).
- **Preferred pullback (pts champs, PF soft):** `mb250_w11_pref` PF **2.047** / +102192 n199; `mb200_w11_pref` PF1.96 / +101863 n212; `mb225_w11_pref` PF1.993 / +100903 — Δpts ~+14–15k vs KEEP but **PF≪2.5** (at soft floor ~2.0). Do **not** promote.
- **Required looser mb/wait:** best `mb200_w13_requ` PF2.586 / +82420 n122 — **worse pts and PF** vs KEEP. max_break 18/20 also worse (PF~2.2).
- **Conclusion:** Volume expand does not beat KEEP under PF≥~2.5. Preferred = volume inflate / PF dilute. KEEP unchanged.
- **Next:** Batch D TP/trail 5m re-screen on NEW KEEP (prior trail champs + TP bumps); then E hold/flatten if D stalls.


### 2026-09-23 ~10:34 Europe/Bucharest Asia Batch D TP_TRAIL_D_KEEP_NB 5m (16 cells) — interesting; tick-confirm pts champ
- **Grid:** `overnight_5m_grid_20260923T073415Z.json` · tag `TP_TRAIL_D_KEEP_NB` · seed NEW KEEP near-box · candles_5m · workers=2.
- **Baseline KEEP 5m:** n110 · PF **3.023** · **+87426**.
- **Pts champs (trail on, PF holds):** `tp2600_arm2400_tr200` / `tp2800_arm2400_tr200` PF **3.264** / **+102363** (Δpts **+14937**, ΔPF **+0.24**); `tp2600_arm2200_tr200` PF3.317 / +100145; `tp2200_arm2000_tr200` PF **3.35** / +99217.
- **TP-only trail-off:** `tp2400_trail_off` PF3.002 / +90537 (mild pts lift); larger TP alone (2600–3300) **worse** pts/PF.
- **Note:** prior trail tick on old asia1-6 seed **REJECTED** (2026-09-17). Re-testing on NEW KEEP because seed changed (asia0-6 + near-box + sls5).
- **Next:** overnight **tick-confirm** pts champ `tp2600_arm2400_tr200` (workers=2). If promotes, optional runner `tp2200_arm2000_tr200` (PF champ) or `tp2400_trail_off`. Else E hold/flatten.


### 2026-09-23 ~10:51 Europe/Bucharest Asia TICK CONFIRM Batch D tp2600_arm2400_tr200 on KEEP+near-box (run `20260923T074837Z_9946b2f7`) — **PROMOTE (NEW KEEP / thin pts)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb250**, SL1000/**TP2600**, **sls5/2200**, **near_box outside N=7 D=1000**, **trail_arm 2400 / trail 200**, timeout market, wait_from_break, pullback required, side both. workers=2. data_source=ticks.
- **Result:** n110 · win58.2% · **+89314.6** · **PF 2.98** (avg +812 / win +2102 / loss −983). exits trail37 / flatten14 / sl45 / tp14. trail_armed 51 (46.4%). finished 2026-09-23T07:48Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T074837Z_9946b2f7.json`.
- **vs prior KEEP ticks** near-box + trail-off TP2200 PF3.03/+87528.4 n110 (run 20260923T065659Z_4f318ec1): ΔPF **-0.05** · Δpts **+1786.2** · n same — thin pts lift at PF still ≥2.5 (goal = maximize pts).
- **vs 5m screen** tp2600_arm2400_tr200 PF3.264/+102363: tick **under-delivers** (~+89.3k PF2.98; trail locks dominate, only 14 full TP) — same pattern as prior trail tick rejects on old seed, but still beats trail-off KEEP on pts.
- **Conclusion:** **NEW KEEP** = prior near-box KEEP **+ trail tp2600/arm2400/tr200**. Prior trail-off demoted on pts (still stronger PF at 3.03).
- **Next:** D_runner tick-confirm 5m PF champ `tp2200_arm2000_tr200` (workers=2). If not better, optional `tp2400_trail_off` then Batch E hold/flatten. No reaktor / no push.


### 2026-09-23 ~11:23 Europe/Bucharest Asia TICK CONFIRM D_runner tp2200_arm2000_tr200 on KEEP+near-box (run `20260923T080829Z_45e9cea5`) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb250**, SL1000/**TP2200**, **sls5/2200**, **near_box outside N=7 D=1000**, **trail_arm 2000 / trail 200**, timeout market, wait_from_break, pullback required, side both. workers=2. data_source=ticks.
- **Result:** n110 · win60.9% · **+83681.6** · **PF 2.98** (avg +760.7 / win +1879.1 / loss −981.9). exits trail38 / flatten9 / sl42 / tp21. trail_armed 59 (53.6%). entries ema_touch89 / higher_close5 / near_box_timeout16. finished 2026-09-23T08:08Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T080829Z_45e9cea5.json`.
- **vs CURRENT KEEP** tp2600_arm2400_tr200 ticks PF2.98/+89314.6 n110 (run 20260923T074837Z_9946b2f7): ΔPF **0.00** · Δpts **−5633** · n same — worse pts, no promote.
- **vs 5m screen** tp2200_arm2000_tr200 PF3.35/+99217: tick **under-delivers** (~+83.7k PF2.98; trail38/tp21) — same trail-overpromise pattern.
- **Conclusion:** KEEP unchanged (tp2600/arm2400/tr200 + near-box + sls5). D_runner (5m PF champ) rejects on ticks.
- **Next:** tick-confirm `tp2400_trail_off` (5m mild pts lift PF3.00/+90537). If not better → Batch E hold/flatten expand. No reaktor / no push.


### 2026-09-23 ~11:55 Europe/Bucharest Asia TICK CONFIRM D_alt tp2400_trail_off on KEEP+near-box (run `20260923T084050Z_e1182ce9`) — **PROMOTE (NEW KEEP / pts+PF)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, flat23, **mb250**, SL1000/**TP2400**, **sls5/2200**, **near_box outside N=7 D=1000**, **trail off**, timeout market, wait_from_break, pullback required, side both. workers=2. data_source=ticks.
- **Result:** n110 · win58.2% · **+90624.3** · **PF 3.00** (avg +823.9 / win +2122.6 / loss −983.1). exits tp51 / flatten14 / sl45. trail_armed 0. entries ema_touch89 / higher_close5 / near_box_timeout16. finished 2026-09-23T08:40Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T084050Z_e1182ce9.json`.
- **vs CURRENT KEEP** tp2600_arm2400_tr200 ticks PF2.98/+89314.6 n110 (run 20260923T074837Z_9946b2f7): ΔPF **+0.02** · Δpts **+1309.7** · n same — mild pts+PF lift; cleaner exits (tp51 vs trail37/tp14).
- **vs prior trail-off near-box TP2200** PF3.03/+87528.4 n110 (run 20260923T065659Z_4f318ec1): ΔPF **−0.03** · Δpts **+3095.9** · n same — pts champ among trail-off.
- **vs 5m screen** tp2400_trail_off PF3.002/+90537: tick **matches** (~+90.6k PF3.00).
- **Conclusion:** **NEW KEEP** = near-box + sls5 + **TP2400 trail-off**. Prior trail KEEP demoted (still close on pts; worse PF and trail-lock exits). D lineage: trail overpromises on 5m; trail-off TP bump wins on ticks.
- **Next:** Batch E 5m HOLD_FLATTEN_E_KEEP_TP2400 (19 cells: max_hold 10–24 × flatten 20/21/22/23/0) on NEW KEEP seed. Then tick-confirm any PF≥~2.8 pts lift. No reaktor / no push.



### 2026-09-23 ~12:34 Europe/Bucharest Asia Batch E HOLD_FLATTEN_E_KEEP_TP2400 5m (19 cells) — mild flat21 edge; tick-confirm
- **Grid:** `overnight_5m_grid_20260923T090034Z.json` · tag `HOLD_FLATTEN_E_KEEP_TP2400` · seed NEW KEEP tp2400 trail-off + near-box outside N7 D1000 + sls5/2200 · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (`KEEP_tp2400_flat23_hold14`): n110 · PF **3.002** · **+90536.7** (matches ticks ~PF3.00/+90624).
- **Champ:** `flat21_hold14` (and flat21 hold16/18/20 identical) PF **3.049** / **+91240.7** n110 win59.1% — ΔPF **+0.047** · Δpts **+704** vs 5m KEEP. Only override that matters: **flatten_hour=21** (max_hold 14–20 inert at flat21).
- **Other:** flat23 longer hold (16–24) tiny +160 pts PF3.008; flat22 worse pts; flat20/flat0 reject (flat0 n=0).
- **Conclusion:** Hold/flatten expand mostly inert; early flatten 21 is a thin but clean PF+pts lift at PF≥2.8. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `flatten_hour=21` on KEEP seed (workers=2). If promotes → optional F; else F seasonal/week2/side only if still stalling toward ~157k pts goal. No reaktor / no push.

### 2026-09-23 ~12:50 Europe/Bucharest Asia TICK CONFIRM E_tick flatten_hour=21 on KEEP+near-box TP2400 (run 20260923T094807Z_cbd8dd4a) — **PROMOTE (NEW KEEP / pts+PF)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, SL1000/**TP2400**, **sls5/2200**, **near_box outside N=7 D=1000**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks.
- **Result:** n110 · win59.1% · **+91328.3** · **PF 3.05** (avg +830.3 / win +2090.1 / loss −989.5). exits tp51 / flatten15 / sl44. trail_armed 0. entries ema_touch89 / higher_close5 / near_box_timeout16. finished 2026-09-23T09:48Z UTC. saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T094807Z_cbd8dd4a.json.
- **vs CURRENT KEEP** tp2400 trail-off flat23 ticks PF3.00/+90624.3 n110 (run 20260923T084050Z_e1182ce9): ΔPF **+0.05** · Δpts **+704** · n same — thin but clean PF+pts lift; matches 5m flat21_hold14 screen (PF3.049/+91241).
- **Conclusion:** **NEW KEEP** = prior KEEP with **flatten_hour=21** (was 23). max_hold still 14 (inert at flat21 on 5m). Hold/flatten expand done.
- **Next:** Batch F 5m SEASONAL_WEEK2_SIDE_F on NEW KEEP (side long/short diagnostic; seasonal/week2 filter|tag; light combos). Prefer combined sides for total pts. Tick-confirm only PF≥~2.8 pts lifts. Still ~91k vs ~157k goal — F is the stall path. No reaktor / no push.

### 2026-09-23 ~13:28 Europe/Bucharest Asia Batch F SEASONAL_WEEK2_SIDE_F_KEEP_FLAT21 5m (18 cells) — REJECT for KEEP
- **Grid:** `overnight_5m_grid_20260923T095545Z.json` · tag `SEASONAL_WEEK2_SIDE_F_KEEP_FLAT21` · seed NEW KEEP flat21 + TP2400 trail-off + near-box outside N7 D1000 + sls5/2200 · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (`KEEP_flat21_both`): n110 · PF **3.049** · **+91240.7** (matches ticks ~PF3.05/+91328).
- **Pts-only volume joins (PF dilute — do not promote):** `seasonal_join_week2_filter` PF **1.79** / +98152 n238; `seasonal_filter_join` PF **2.024** / +93423 n187 — Δpts +2–7k vs KEEP but **PF≪2.5** (at/under soft floor ~2.0). Same pattern as Batch C preferred volume.
- **Quality filters (PF up, pts down):** `week2_filter_eff25` PF **4.065** / +82747 n81; `week2_filter_eff45` PF3.427 / +86218; plain `week2_filter` PF3.387 / +82418 — worse total pts vs KEEP.
- **Tags inert:** seasonal_tag / week2_tag identical to KEEP.
- **Side split:** short PF3.64 / +42.3k n41; long PF2.72 / +48.9k n69 — prefer **combined** for total pts (instruction). Side+filter combos do not beat KEEP total pts at PF≥~2.8.
- **Conclusion:** Batch F does not beat KEEP under PF≥~2.5 with pts lift. KEEP unchanged (flat21 · TP2400 · near-box N7 D1000 · sls5/2200). Plan A–F stall at ~91k vs ~157k goal.
- **Next:** Batch G 5m NEARBOX_REFINE_G on CURRENT KEEP (N×D×trend; A only tick-confirmed one cell from older seed). Tick-confirm only PF≥~2.8 pts lifts. No reaktor / no push.

### 2026-09-23 ~13:32 Europe/Bucharest Asia Batch G NEARBOX_REFINE_G_KEEP_FLAT21 5m (37 cells) — tick-confirm pts champ
- **Grid:** `overnight_5m_grid_20260923T103135Z.json` · tag `NEARBOX_REFINE_G_KEEP_FLAT21` · seed CURRENT KEEP flat21 TP2400 trail-off + sls5 · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (`KEEP_N7_D1000_outside`): n110 · PF **3.049** · **+91240.7**.
- **Champ:** `N6_D1000_outside` PF **3.061** / **+93815.2** n113 win59.3% — ΔPF **+0.012** · Δpts **+2574.5** · Δn +3 vs KEEP. Holds PF≥2.8 with meaningful pts lift.
- **PF runner:** `N6_D1000_breakout` PF **3.212** / +91841 n106 — milder pts (+600) higher PF.
- **Also:** `N5_D1000_outside` PF2.932 / +91815 n115 — pts lift but PF softer. D=1200 outside cells dilute PF (~2.7–2.9). nearbox_off worse pts (+82.7k PF3.26).
- **Conclusion:** Narrow N from 7→6 at D=1000 outside looks like a clean volume/pts edge on 5m. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `near_box_bars=6 / near_box_pts=1000 / near_box_trend=outside` on KEEP seed (workers=2). Optional runner N6 breakout if champ rejects. No reaktor / no push.
### 2026-09-23 ~13:48 Europe/Bucharest Asia TICK CONFIRM G_tick N6_D1000_outside on KEEP flat21 TP2400 (run `20260923T104721Z_f4c07636`) — **PROMOTE (NEW KEEP / pts+PF)**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, SL1000/**TP2400**, **sls5/2200**, **near_box outside N=6 D=1000**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks.
- **Result:** n113 · win59.3% · **+93898.8** · **PF 3.06** (avg +831 / win +2081 / loss −989.7). exits tp52 / flatten16 / sl45. trail_armed 0. entries ema_touch89 / higher_close5 / near_box_timeout19. finished 2026-09-23T10:47Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T104721Z_f4c07636.json`.
- **vs CURRENT KEEP** N7 D1000 outside flat21 ticks PF3.05/+91328.3 n110 (run 20260923T094807Z_cbd8dd4a): ΔPF **+0.01** · Δpts **+2570.5** · Δn **+3** — meaningful pts lift at PF≥2.8; matches 5m N6_D1000_outside screen (PF3.061/+93815).
- **Conclusion:** **NEW KEEP** = prior KEEP with **near_box_bars=6** (was 7). G near-box refine promotes on ticks.
- **Next:** Skip G_runner (champ promoted). Batch H 5m TIMEOUT_SLTP_H on NEW KEEP (timeout_max_ema_dist / timeout_min_break / SL:TP ≈1:1.5+ rescale). Tick-confirm only PF≥~2.8 pts lifts. Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-23 ~14:23 Europe/Bucharest Asia Batch H TIMEOUT_SLTP_H_KEEP_N6 5m (30 cells) — REJECT for KEEP / no tick
- **Grid:** 
esults/overnight_5m_grid_20260923T105415Z.json · tag TIMEOUT_SLTP_H_KEEP_N6 · seed NEW KEEP ticks 20260923T104721Z_f4c07636 (asia0-6 mb250 sls5/2200 near_box outside N6 D1000 TP2400 trail_off flat21) · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (KEEP_N6_D1000_outside_sl1000_tp2400): n113 · PF **3.061** · **+93815.2** (matches ticks ~PF3.06/+93899).
- **Timeout gates INERT:** all 	imeout_max_ema_dist 200–1000, 	imeout_min_break 100–500, 	imeout_min_pullback 50–200, and ema+minbreak combos identical to KEEP (n/PF/pts unchanged).
- **SL:TP rescale:** only pts-over-KEEP cell is sl1600_tp2400 PF **2.726** / **+97454.3** n113 win67.3% (Δpts **+3639** ΔPF **−0.335**) — PF below tick-confirm bar ~2.8 (meets soft ≥2.5 only). sl1200_tp2400 PF2.765/+90486 worse pts; sl1000_tp2000 PF3.124/+88209 higher PF but −5.6k pts; larger TP 2800/3000 dilute; smaller SL800 reject (PF~1.8–1.9).
- **Conclusion:** Batch H does not beat KEEP under PF≥~2.8 with pts lift. Timeout knobs dead on this seed. KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · sls5 ticks PF3.06/+93899).
- **Next:** Batch I 5m ENTRY_WAIT_RC_CAP_I on CURRENT KEEP (max_wait / ema / max_break / resume_closes / resume_cap / min_asia / mb± + denser SL@TP2400 1100–1500). Tick-confirm only PF≥~2.8 pts lifts; optional later H_runner sl1600_tp2400 if still stalling (PF2.73 soft≥2.5 pts-only). Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-23 ~14:28 Europe/Bucharest Asia Batch I ENTRY_WAIT_RC_CAP_I_KEEP_N6 5m (38 cells) — tick-confirm SL champ
- **Grid:** 
esults/overnight_5m_grid_20260923T112856Z.json · tag ENTRY_WAIT_RC_CAP_I_KEEP_N6 · seed CURRENT KEEP ticks 20260923T104721Z_f4c07636 · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP:** n113 · PF **3.061** · **+93815.2**.
- **Entry/wait/ema/rc/mb/min_asia:** no PF≥~2.8 pts lift vs KEEP. Longer wait / looser max_break / ema≠30 / mb≠250 all cut pts or dilute PF. cap≥1000 and min_asia 200–400 inert (=KEEP).
- **Denser SL@TP2400:** champ sl1300_tp2400 PF **2.870** / **+96220.8** n113 win63.7% (Δpts **+2406** ΔPF **−0.191**) — clears tick bar ~2.8. Runners sl1500 PF2.685/+94477 and sl1400 PF2.750/+94277 (pts up, PF <2.8). sl1100 milder pts under KEEP; sl1200 still worse pts (same as H).
- **Conclusion:** Structure knobs exhausted on this seed; SL 1300 @ TP2400 is the only clean 5m pts+PF≥~2.8 candidate. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** sl_fixed_pts=1300 / 	p_fixed_pts=2400 on KEEP seed (workers=2). If promotes → optional runners sl1400/sl1600; else consider H_runner sl1600 (PF2.73 soft≥2.5) or stall path. Still ~94k vs ~157k. No reaktor / no push.

### 2026-09-23 ~14:58 Europe/Bucharest Asia TICK CONFIRM I_tick sl1300_tp2400 on KEEP N6 flat21 (run `20260923T114342Z_00124a3c`) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1300/TP2400**, **sls5/2200**, **near_box outside N=6 D=1000**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks.
- **Result:** n113 · win62.8% · **+92616.1** · **PF 2.76** (avg +819.6 / win +2047.6 / loss −1256.2). exits tp54 / flatten20 / sl39. trail_armed 0. entries ema_touch89 / higher_close5 / near_box_timeout19. finished 2026-09-23T11:43Z UTC. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260923T114342Z_00124a3c.json`.
- **vs CURRENT KEEP** SL1000/TP2400 N6 ticks PF3.06/+93898.8 n113 (run 20260923T104721Z_f4c07636): ΔPF **-0.3** · Δpts **-1282.7** · n same — worse pts and PF; no promote.
- **vs 5m screen** sl1300_tp2400 PF2.870/+96220.8: tick **under-delivers** (~+92.6k PF2.76; more flatten20 / larger avg loss −1256 vs KEEP −990).
- **Conclusion:** KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5). Skip optional runners sl1400/sl1600 (5m PF <2.8 and denser-SL already under-delivered on ticks).
- **Next:** Batch J 5m BE_TRAIL_OTD_J on CURRENT KEEP (be_arm · light trail retest on N6 seed · one_trade_per_day=false volume · asia end 5/7 diagnostic). Tick-confirm only PF≥~2.8 pts lifts. Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~11:50 Europe/Bucharest Asia Batch J BE_TRAIL_OTD_J_KEEP_N6 5m (21 cells) — tick-confirm trail pts champ
- **Context:** Prior Batch J crash `overnight_5m_grid_20260923T115859Z.json` (all 21 cells process-pool terminated when Lenovo went offline ~17:09 2026-09-24). Lenovo back online this fire; API healthy; overnight/batch idle. Re-ran `scripts/_be_trail_otd_J_20260923.py --workers 2`.
- **Grid:** `overnight_5m_grid_20260925T085428Z.json` · tag `BE_TRAIL_OTD_J_KEEP_N6` · seed CURRENT KEEP ticks 20260923T104721Z_f4c07636 (asia0-6 mb250 sls5/2200 near_box outside N6 D1000 TP2400 trail_off flat21) · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (`KEEP_N6_baseline`): n113 · PF **3.061** · **+93815.2** (matches ticks ~PF3.06/+93899).
- **Pts champ:** `tr_tp2600_arm2400_tr200` (= `tr_tp2800_arm2400_tr200`) PF **3.316** / **+105465.5** n113 win59.3% — ΔPF **+0.255** · Δpts **+11650** vs KEEP.
- **PF champ:** `tr_tp2400_arm2000_tr200` PF **3.516** / **+104483.9** n113 win62.8% — ΔPF **+0.455** · Δpts **+10669**.
- **Also trail:** `tr_tp2600_arm2200_tr200` PF3.371/+103225; `tr_tp2400_arm1800_tr150` PF3.278/+92313 (worse pts than KEEP).
- **be_arm alone:** all cut pts vs KEEP (best be2000 PF3.223/+92323). be+trail combos worse than trail alone.
- **otd_false:** inert (=KEEP). otd_false_mb275 mild pts cut. asia0_5 / asia0_7 / asia0_7_otd reject (PF~2.0–2.4). asia1_6 mild pts cut PF2.995.
- **Conclusion:** Trail retest on N6 seed is the only 5m PF≥~2.8 pts-lift family. **Caution:** prior Batch D trail ticks under-delivered vs 5m (trail locks). Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `tp2600_arm2400_tr200` on CURRENT KEEP seed (workers=2). Optional runner `tp2400_arm2000_tr200` if champ rejects. Else Batch K stall path. Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~12:54 Europe/Bucharest Asia TICK CONFIRM J_tick tp2600_arm2400_tr200 on KEEP N6 flat21 (run \20260925T092441Z_fa45240d\) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, SL1000/**TP2600**, **sls5/2200**, **near_box outside N=6 D=1000**, **trail arm2400/tr200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks.
- **Result:** n113 · win59.3% · **+92413.6** · **PF 3.03** (avg +817.8 / win +2058.8 / loss −989.7). exits trail38 / flatten16 / sl45 / tp14. trail_armed 52 (46%). finished 2026-09-25T09:24Z UTC. saved esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T092441Z_fa45240d.json\.
- **vs CURRENT KEEP** trail-off TP2400 N6 ticks PF3.06/+93898.8 n113 (run 20260923T104721Z_f4c07636): ΔPF **-0.03** · Δpts **-1485.2** · n same — worse pts and slight PF drop; no promote.
- **vs 5m screen** tr_tp2600_arm2400_tr200 PF3.316/+105465.5: tick **under-delivers** (~+92.4k PF3.03; trail locks 38 vs tp14) — same Batch D trail pattern.
- **Conclusion:** KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5 · trail off). Champ trail cell rejected on ticks.
- **Next:** overnight **tick-confirm** optional runner \	p2400_arm2000_tr200\ (5m PF champ PF3.516/+104484). If rejects → Batch K stall path. Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~13:20 Europe/Bucharest Asia TICK CONFIRM J_runner tp2400_arm2000_tr200 on KEEP N6 flat21 (run `20260925T100817Z_31186ed4`) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, SL1000/**TP2400**, **sls5/2200**, **near_box outside N=6 D=1000**, **trail arm2000/tr200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T09:54Z finished 10:08Z UTC.
- **Result:** n113 · PF **3.14** · **+88819.2** · win62.8% · exits trail53 / flatten11 / sl41 / tp8 · trail_armed 61 (54%).
- **vs CURRENT KEEP** trail-off TP2400 N6 ticks PF3.06/+93898.8 n113 (run 20260923T104721Z_f4c07636): ΔPF **+0.08** · Δpts **−5079.6** · n same — higher PF but meaningful pts drop; no promote.
- **vs 5m screen** tr_tp2400_arm2000_tr200 PF3.516/+104484: tick **under-delivers** (~+88.8k; trail53/tp8 locks).
- **Conclusion:** KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5 · trail off). Batch J trail lineage closed (champ + runner both tick-reject).
- **Next:** Batch K 5m `PREF_TIGHT_NEWS_K_KEEP_N6` (pullback preferred + tight mb/min_asia/timeout/near-box gates + news filter/tag). Tick-confirm only PF≥~2.8 pts lifts. Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~13:25 Europe/Bucharest Asia Batch K PREF_TIGHT_NEWS_K_KEEP_N6 5m (24 cells) — REJECT for KEEP / no tick
- **Grid:** `overnight_5m_grid_20260925T102452Z.json` · tag `PREF_TIGHT_NEWS_K_KEEP_N6` · seed CURRENT KEEP ticks 20260923T104721Z_f4c07636 · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (`KEEP_N6_baseline`): n113 · PF **3.061** · **+93815.2**.
- **Pts champs (PF dilute — do not tick):** `pref_tminbreak300` PF **2.109** / **+102588.6** n185; `pref_mb275` PF2.027/+102288 n196; bare `pref_alone` / near-box / minasia400 inert clones PF1.992/+100764 n198 — same Batch C pattern (preferred volume ≈+7–9k pts at PF~2.0 soft floor only).
- **Quality / news:** `news_filter` PF2.974/+83969 n104 (pts cut); `news_tag` inert (=KEEP); `req_news_filter_mb300` PF2.919/+79694; `pref_tema400` best quality-ish preferred PF2.635/+92415 (under KEEP pts, PF<2.8).
- **Zero cells** with PF≥~2.8 and pts > KEEP.
- **Conclusion:** Preferred+tight gates / news do not beat KEEP under tick bar. KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5 · trail off · ticks PF3.06/+93899).
- **Next:** Batch L overnight **tick-confirm** deferred soft-floor `sl1600_tp2400` (Batch H 5m PF2.726/+97454; soft ≥2.5 pts-only). If rejects → new axes. Still ~94k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~13:42 Europe/Bucharest Asia TICK CONFIRM L H_runner sl1600_tp2400 on KEEP N6 flat21 (run 20260925T104008Z_1dc69c54) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1600/TP2400**, **sls5/2200**, **near_box outside N=6 D=1000**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T10:25Z finished 10:40Z UTC.
- **Result:** n113 · win66.4% · **+93547.2** · **PF 2.61** (avg +827.9 / win +2021.4 / loss −1527.9). exits tp56 / flatten22 / sl35. trail_armed 0. entries ema_touch89 / higher_close5 / near_box_timeout19. saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T104008Z_1dc69c54.json.
- **vs CURRENT KEEP** SL1000/TP2400 N6 ticks PF3.06/+93898.8 n113 (run 20260923T104721Z_f4c07636): ΔPF **−0.45** · Δpts **−351.6** · n same — soft ≥2.5 met but pts slightly down and PF much weaker; no promote.
- **vs 5m screen** sl1600_tp2400 PF2.726/+97454: tick **under-delivers** (~+93.5k PF2.61; larger avg loss −1528 vs KEEP −990; more flatten22 / sl35).
- **Conclusion:** KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5 · trail off). Soft-floor H_runner closed. Plan A–L stall at ~94k vs ~157k goal.
- **Next:** Batch M 5m RISK_HOLD_M_KEEP_N6 (larger 1:1.5 books · asia_opposite/range risk modes · hold/flatten re-sweep on N6 · entry-path toggles). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 with meaningful pts). Still ~94k vs ~157k. No reaktor / no push.

### 2026-09-25 ~13:46 Europe/Bucharest Asia Batch M RISK_HOLD_M_KEEP_N6 5m (35 cells) — soft≥2.5 pts champ for tick
- **Grid:** overnight_5m_grid_20260925T104629Z.json · tag RISK_HOLD_M_KEEP_N6 · seed CURRENT KEEP ticks 20260923T104721Z_f4c07636 · candles_5m · workers=2 · window 2025-01→2026-09. Axes: larger 1:1.5 books · asia_opposite/range risk modes · hold/flatten re-sweep on N6 · entry-path toggles.
- **Baseline 5m KEEP** (KEEP_N6_baseline): n113 · PF **3.061** · **+93815.2**.
- **Pts champs (PF dilute <2.5 — do not tick first):** sl_range1_tp_range2 PF **2.321** / **+109271.1** n113 — Δpts **+15456** but PF under prefer ≥2.5 (soft-floor-only).
- **Soft ≥2.5 pts lifts:** wick_on (= close_inside_ok twin) PF **2.657** / **+106951.0** n148 — ΔPF **−0.404** · Δpts **+13136** · Δn +35; sl_asia_opp_tp2400 PF **2.698** / **+99332.5** n113 — Δpts **+5517**.
- **Zero cells** with PF≥~2.8 and pts > KEEP. Larger fixed books (sl1700–2200) and hold/sls/ema_tf/no_higher_close all ≤ KEEP pts or inert.
- **Conclusion:** Structure/hold path still stalled at PF≥2.8; soft≥2.5 volume via wick break is the cleanest new edge. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** reak_on_wick=true on CURRENT KEEP seed (workers=2). Optional runner sl_mode=asia_opposite tp2400 if wick rejects. Still ~94k vs ~157k. No reaktor / no push.

### 2026-09-25 ~14:21 Europe/Bucharest Asia TICK CONFIRM M_tick wick_on break_on_wick on KEEP N6 flat21 (run `20260925T110231Z_9c0ea27e`) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1000/TP2400**, **sls5/2200**, **near_box outside N=6 D=1000**, **break_on_wick=true**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T10:47Z finished 11:02Z UTC.
- **Result:** n148 · win56.8% · **+110427.0** · **PF 2.74** (avg +746.1 / win +2070.9 / loss −992.6). exits tp67 / flatten18 / sl63. trail_armed 0. entries ema_touch118 / higher_close6 / near_box_timeout24. skipped 281 (no_break167 / no_pullback95 / late_short19). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T110231Z_9c0ea27e.json`.
- **vs PRIOR KEEP** close-outside N6 ticks PF3.06/+93898.8 n113 (run 20260923T104721Z_f4c07636): ΔPF **-0.32** · Δpts **+16528.2** · Δn **+35** — meaningful pts lift at soft PF≥2.5; **PROMOTE**.
- **vs 5m screen** wick_on PF2.657/+106951 n148: tick **matches/slightly beats** (~+110.4k PF2.74; same n148).
- **Conclusion:** NEW KEEP = N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5 · **wick_on** · trail off · ticks PF2.74/+110427.0 n148. Still ~110k vs ~157k goal.
- **Next:** overnight **tick-confirm** M_runner `sl_mode=asia_opposite` on NEW KEEP wick seed (Batch M soft≥2.5 runner PF2.698/+99333 on old seed; test combo). If rejects → Batch N 5m SEASON_SIDE_N on wick KEEP. No reaktor / no push.

### 2026-09-25 ~14:44 Europe/Bucharest Asia TICK CONFIRM M_runner asia_opposite on KEEP wick (run `20260925T113556Z_a701334f`) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL asia_opposite / TP2400**, **sls5/2200**, **near_box outside N=6 D=1000**, **break_on_wick=true**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T11:21Z finished 11:35Z UTC.
- **Result:** n148 · win64.2% · **+112215.8** · **PF 2.32** (avg +758.2). exits tp75 / flatten24 / sl49. trail_armed 0. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T113556Z_a701334f.json`.
- **vs CURRENT KEEP** wick_on fixed SL1000/TP2400 N6 ticks PF2.74/+110427 n148 (run 20260925T110231Z_9c0ea27e): ΔPF **-0.42** · Δpts **+1788.8** · n same — tiny pts lift but PF drops below prefer ≥2.5 (soft-floor-only 2.32); no promote.
- **vs 5m screen** sl_asia_opp_tp2400 PF2.698/+99333 on prior close-outside seed: wick+asia_opp combo on ticks = more pts than 5m asia_opp alone but weaker PF than wick KEEP.
- **Conclusion:** KEEP unchanged (N6 D1000 outside · TP2400 · flat21 · SL1000 · sls5 · **wick_on** · trail off · ticks PF2.74/+110427 n148). Batch M closed (wick promote; asia_opp runner reject).
- **Next:** Batch N 5m `SEASON_SIDE_N_KEEP_WICK` (seasonal/week2/side on wick KEEP; prefer combined). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 with meaningful pts). Still ~110k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~14:46 Europe/Bucharest Asia Batch N SEASON_SIDE_N_KEEP_WICK 5m (21 cells) — REJECT for KEEP / no tick
- **Grid:** `overnight_5m_grid_20260925T114513Z.json` · tag `SEASON_SIDE_N_KEEP_WICK` · seed CURRENT KEEP ticks 20260925T110231Z_9c0ea27e (wick_on N6 D1000 TP2400) · candles_5m · workers=2 · window 2025-01→2026-09.
- **Baseline 5m KEEP** (`KEEP_wick_both`): n148 · PF **2.657** · **+106951.0** (matches prior wick 5m).
- **Pts champs (PF dilute — do not tick):** `seasonal_filter_join` PF **2.139** / **+110720.7** n204; `seasonal_join_week2_filter` PF **1.899** / **+107250.1** n236 — soft-floor-only / below soft floor.
- **Quality filters:** `week2_filter_eff25` PF **3.039** / **+87679** (pts cut); other week2/seasonal filters cut pts vs KEEP. Tags inert (=KEEP). Side splits thin (long +57.7k / short +49.3k) — prefer combined.
- **Zero cells** with PF≥~2.8 and pts > KEEP.
- **Conclusion:** Seasonal/week2/side on wick seed matches Batch F pattern. KEEP unchanged (wick_on N6 ticks PF2.74/+110427 n148).
- **Next:** Batch O 5m `WICK_VOL_TP_O_KEEP_WICK` (near-box N/D refine + fixed TP expand trail-off + mild mb/wait required on wick KEEP). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 meaningful pts). Still ~110k vs ~157k. No reaktor / no push.
### 2026-09-25 ~15:15 Europe/Bucharest Asia Batch O WICK_VOL_TP_O_KEEP_WICK 5m (25 cells) — soft≥2.5 pts champ for tick
- **Grid:** `overnight_5m_grid_20260925T114835Z.json` · tag `WICK_VOL_TP_O_KEEP_WICK` · seed CURRENT KEEP ticks 20260925T110231Z_9c0ea27e (wick_on N6 D1000 TP2400) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: near-box N/D refine · fixed TP expand trail-off · mild mb/wait required.
- **Baseline 5m KEEP** (`KEEP_wick_baseline`): n148 · PF **2.657** · **+106951.0** (matches prior wick 5m).
- **Soft ≥2.5 pts lifts:** `tp3600_trail_off` PF **2.534** / **+112825.3** n148 — ΔPF **−0.123** · Δpts **+5874** (largest soft≥2.5 pts lift); `mb275_w13_req` PF **2.717** / **+109101.2** n148 — ΔPF **+0.06** · Δpts **+2150**; `nb_N6_D1000_off` PF **2.511** / **+111854.5** n164 — Δpts **+4904** (near-box off volume).
- **PF≥~2.8 pts lift (only):** `nb_N6_D1000_breakout` PF **2.848** / **+108151.0** n140 — ΔPF **+0.191** · Δpts **+1200** (mild).
- **Reject / dilute:** larger TP 2600–3200 under KEEP pts or PF≪2.5; N5/N7/D1200 outside cut pts; mb200/225 dilute.
- **Conclusion:** Soft≥2.5 TP expand is the cleanest pts edge on wick seed; PF≥2.8 only mild breakout refine. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `tp_fixed_pts=3600` trail-off on CURRENT KEEP wick seed (workers=2). Optional runners `mb275_w13_req` then `nb_N6_D1000_breakout` if champ rejects. Still ~110k vs ~157k goal. No reaktor / no push.
### 2026-09-25 ~15:46 Europe/Bucharest Asia TICK CONFIRM O_tick tp3600_trail_off on KEEP wick (run `20260925T123202Z_567943d0`) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1000/TP3600**, **sls5/2200**, **near_box outside N=6 D=1000**, **break_on_wick=true**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T12:18Z finished 12:32Z UTC.
- **Result:** n148 · win50.7% · **+117532.8** · **PF 2.62** (avg +794.1 / win +2534.1 / loss −993.5). exits tp41 / flatten35 / sl72. trail_armed 0. entries ema_touch118 / higher_close6 / near_box_timeout24. skipped 281 (no_break167 / no_pullback95 / late_short19). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T123202Z_567943d0.json`.
- **vs PRIOR KEEP** wick_on TP2400 N6 ticks PF2.74/+110427 n148 (run 20260925T110231Z_9c0ea27e): ΔPF **−0.12** · Δpts **+7105.8** · n same — meaningful pts lift at soft PF≥2.5; **PROMOTE**.
- **vs 5m screen** tp3600_trail_off PF2.534/+112825 n148: tick **beats** (~+117.5k PF2.62; more flatten35 vs prior KEEP flatten18; larger avg win +2534).
- **Conclusion:** NEW KEEP = N6 D1000 outside · **TP3600** · flat21 · SL1000 · sls5 · **wick_on** · trail off · ticks PF2.62/+117532.8 n148. Still ~118k vs ~157k goal. Skip O runners mb275/breakout on old seed (re-test under Batch P on NEW KEEP).
- **Next:** Batch P 5m `HOLD_TP_P_KEEP_TP3600` (hold/flatten expand · further TP trail-off · denser SL @ TP3600 · mild mb/near-box on NEW KEEP). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 meaningful pts). No reaktor / no push.

### 2026-09-25 ~16:21 Europe/Bucharest Asia Batch P HOLD_TP_P_KEEP_TP3600 5m (32 cells) — soft≥2.5 pts champ for tick
- **Grid:** `overnight_5m_grid_20260925T125041Z.json` · tag `HOLD_TP_P_KEEP_TP3600` · seed CURRENT KEEP ticks 20260925T123202Z_567943d0 (wick_on N6 D1000 TP3600 flat21) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: hold/flatten expand · further TP trail-off · denser SL @ TP3600 · mild mb/near-box.
- **Baseline 5m KEEP** (`KEEP_tp3600_baseline`): n148 · PF **2.534** · **+112825.3**.
- **Soft ≥2.5 pts lifts:** `tp4000_trail_off` PF **2.619** / **+120691.3** n148 — ΔPF **+0.085** · Δpts **+7866** (largest soft≥2.5 pts lift); `tp3800_trail_off` PF **2.606** / **+118091.3** — Δpts **+5266**; `tp4200_trail_off` PF **2.565** / **+118209.5** — Δpts **+5384**; `nb_N6_D1000_breakout` PF **2.695** / **+114465.8** — Δpts **+1641**; `flat23_hold14` PF **2.549** / **+113851.2** — mild.
- **Reject / dilute:** denser SL 1200–2400 @ TP3600 PF~2.05–2.21 (soft-floor-only / below prefer); `nb_N6_D1000_off` PF2.393; mb275/w15 dilute; flat0 cells n=0; hold12/16/18/20/24 mostly inert vs baseline.
- **Zero cells** with PF≥~2.8 and pts > KEEP.
- **Conclusion:** Further TP expand on TP3600 wick KEEP is the cleanest soft≥2.5 pts edge; hold/flatten and denser SL do not help under prefer≥2.5. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `tp_fixed_pts=4000` trail-off on CURRENT KEEP TP3600 seed (workers=2). Optional runners tp3800 then tp4200 if champ rejects. Still ~118k vs ~157k goal. No reaktor / no push.


### 2026-09-25 ~16:52 Europe/Bucharest Asia TICK CONFIRM P_tick tp4000_trail_off on KEEP TP3600 (run `20260925T133834Z_7a6b8116`) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1000/TP4000**, **sls5/2200**, **near_box outside N=6 D=1000**, **break_on_wick=true**, **trail off**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T13:24Z finished 13:38Z UTC.
- **Result:** n148 · win50.0% · **+125799.5** · **PF 2.71** (avg +850.0 / win +2693.6 / loss −993.6). exits tp38 / flatten37 / sl73. trail_armed 0. entries ema_touch118 / higher_close6 / near_box_timeout24. skipped 281. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T133834Z_7a6b8116.json`.
- **vs PRIOR KEEP** wick_on TP3600 N6 ticks PF2.62/+117532.8 n148 (run 20260925T123202Z_567943d0): ΔPF **+0.09** · Δpts **+8266.7** · n same — meaningful pts lift and PF up at soft ≥2.5; **PROMOTE**.
- **vs 5m screen** tp4000_trail_off PF2.619/+120691 n148: tick **beats** (~+125.8k PF2.71; more flatten37 vs prior KEEP flatten35; larger avg win +2694).
- **Conclusion:** NEW KEEP = N6 D1000 outside · **TP4000** · flat21 · SL1000 · sls5 · **wick_on** · trail off · ticks PF2.71/+125799.5 n148. Still ~126k vs ~157k goal. Skip P runners tp3800/tp4200 on old seed (re-test under Batch Q on NEW KEEP).
- **Next:** Batch Q 5m `TP_TRAIL_VOL_Q_KEEP_TP4000` (further TP trail-off · trail-near-TP · mild mb/near-box · light flatten · soft 1:1.5 books on NEW KEEP). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 meaningful pts). No reaktor / no push.


### 2026-09-25 ~17:14 Europe/Bucharest Asia Batch Q TP_TRAIL_VOL_Q_KEEP_TP4000 5m (31 cells) — soft≥2.5 pts champ for tick
- **Grid:** `overnight_5m_grid_20260925T135649Z.json` · tag `TP_TRAIL_VOL_Q_KEEP_TP4000` · seed CURRENT KEEP ticks 20260925T133834Z_7a6b8116 (wick_on N6 D1000 TP4000 flat21) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: further TP trail-off · trail-near-TP · mild mb/near-box · light flatten · soft 1:1.5 books.
- **Baseline 5m KEEP** (`KEEP_tp4000_baseline`): n148 · PF **2.619** · **+120691.3**.
- **Soft ≥2.5 pts lifts (trail-near-TP):** `tr_tp4800_arm4000_tr200` / `tr_tp4500_arm4000_tr200` PF **2.772** / **+132093.1** n148 — ΔPF **+0.153** · Δpts **+11402** (tied largest; identical 5m); `tr_tp4000_arm3800_tr200` PF **2.753** / **+128877** — Δpts **+8186**; `tr_tp5000_arm4200_tr200` PF **2.702** / **+128544** — Δpts **+7853**.
- **Other soft ≥2.5 mild:** `nb_N6_D1000_breakout` PF **2.797** / **+123153** (PF≥~2.8 mild pts); `mb225_w13_req` PF **2.555** / **+123539**; `flat23_hold14` PF **2.646** / **+122593**; `tr_tp4000_arm3600_tr200` PF **2.663** / **+122303**.
- **Reject / dilute:** further trail-off-only TP 4200–5600 under KEEP pts or PF≪ prefer; denser SL 1200/1333 soft-floor-only; `sl1500_tp4500` PF **1.932**; `nb_N6_D1000_off` PF **2.483** soft-floor-only; mb275/w15 dilute.
- **Zero cells** with trail-off TP>4000 beating KEEP on both PF and pts.
- **Conclusion:** Trail-near-TP (arm≈4000, trail200, TP 4500–4800) is the cleanest soft≥2.5 pts edge on TP4000 wick KEEP. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `Q_tick tr_tp4800_arm4000_tr200` (tp4800 · arm4000 · trail200) on CURRENT KEEP TP4000 seed (workers=2) — started 2026-09-25T14:14Z UTC. Optional runners `tr_tp4000_arm3800_tr200` then `tr_tp5000_arm4200_tr200` if champ rejects. Still ~126k vs ~157k goal. No reaktor / no push.


### 2026-09-25 ~17:41 Europe/Bucharest Asia TICK CONFIRM Q_tick tr_tp4800_arm4000_tr200 on KEEP TP4000 (run `20260925T143120Z_5cdb5840`) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1000/TP4800**, **sls5/2200**, **near_box outside N=6 D=1000**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T14:17Z finished 14:31Z UTC.
- **Result:** n148 · win50.0% · **+128025.8** · **PF 2.74** (avg +865.0 / win +2723.7 / loss −993.6). exits tp1 / flatten37 / sl73 / trail37. trail_armed 38 (25.7%). entries ema_touch118 / higher_close6 / near_box_timeout24. skipped 281 (no_break167 / no_pullback95 / late_short19). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T143120Z_5cdb5840.json`.
- **vs PRIOR KEEP** wick_on TP4000 trail-off N6 ticks PF2.71/+125799.5 n148 (run 20260925T133834Z_7a6b8116): ΔPF **+0.03** · Δpts **+2226.3** · n same — pts lift and PF up at soft ≥2.5; **PROMOTE**.
- **vs 5m screen** tr_tp4800_arm4000_tr200 PF2.772/+132093 n148: tick **underdelivers some pts** (~+128.0k PF2.74; trail37 / tp1 vs 5m optimism) but still beats KEEP.
- **Conclusion:** NEW KEEP = N6 D1000 outside · **TP4800** · flat21 · SL1000 · sls5 · **wick_on** · **trail arm4000/tr200** · ticks PF2.74/+128025.8 n148. Still ~128k vs ~157k goal. Skip Q runners arm3800/tp5000 on old seed (re-test under Batch R on NEW KEEP).
- **Next:** Batch R 5m `HOLD_TRAIL_R_KEEP_TR4800` (trail refine · hold/flatten expand · mild mb/near-box · soft 1:1.5 on NEW KEEP). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 meaningful pts). No reaktor / no push.


### 2026-09-25 ~18:14 Europe/Bucharest Asia Batch R HOLD_TRAIL_R_KEEP_TR4800 5m (34 cells) — soft≥2.5 pts champ for tick
- **Grid:** overnight_5m_grid_20260925T144530Z.json · tag HOLD_TRAIL_R_KEEP_TR4800 · seed CURRENT KEEP ticks 20260925T143120Z_5cdb5840 (wick_on N6 D1000 TP4800 trail arm4000/tr200 flat21) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: trail refine · hold/flatten expand · mild mb/near-box · soft 1:1.5 books.
- **Baseline 5m KEEP** (KEEP_tr4800_baseline): n148 · PF **2.772** · **+132093.1**.
- **Soft ≥2.5 pts lifts:** 
b_N6_D1000_off PF **2.664** / **+141464.6** n164 — ΔPF **−0.108** · Δpts **+9371.5** (largest soft≥2.5 pts lift); mb225_w13_req PF **2.696** / **+134731.8** n156 — Δpts **+2638.7**; 
b_N6_D1000_breakout PF **2.963** / **+134554.3** n140 — ΔPF **+0.191** · Δpts **+2461.2** (also PF≥~2.8); lat23_hold14 PF **2.799** / **+133994.8** — Δpts **+1901.7**; 	r_tp4800_arm4000_tr150 PF **2.797** / **+133943.1** — Δpts **+1850**; lat23_hold18 PF **2.798** / **+133925.1**.
- **PF≥~2.8 pts lifts:** breakout (above); flat23_hold14/18; tr150 (all mild vs soft pts champ).
- **Reject / dilute / inert:** further trail arm/TP tweaks mostly =KEEP or cut pts (arm4200/tr300/tr400/arm3600); trail-off TP4800/5200 PF2.385/2.204; denser SL 1200/1333 soft-floor-only; N5/N7/D800 outside under KEEP pts; mb275/w15 dilute; hold16/18/20 inert (=KEEP).
- **Conclusion:** Near-box off is the cleanest soft≥2.5 pts edge on trail KEEP; breakout is the cleanest PF≥~2.8 refine. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** R_tick nb_N6_D1000_off (near_box_trend=off) on CURRENT KEEP trail seed (workers=2) when overnight IDLE. Optional runners mb225_w13_req then 
b_N6_D1000_breakout / lat23_hold14 / 	r150 if champ rejects. **Blocked this fire:** overnight RUNNING symbol=EURUSD candles_5m ~93.7% (started 2026-09-25T15:03Z UTC) — left alone (not hung; Igor may own it). Still ~128k ticks KEEP vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~18:44 Europe/Bucharest Asia R_tick nb_N6_D1000_off kicked (overnight was IDLE)
- **Prior blocker cleared:** finished overnight was EURUSD candles_5m run `20260925T152932Z_3da9c675` PF0.78/−2442.5 n145 — **not XAU Asia KEEP**; ignored (no score vs KEEP).
- **Kicked:** R_tick `nb_N6_D1000_off` ticks workers=2 started 2026-09-25T15:44Z UTC — CURRENT KEEP trail seed (asia0–6 · ema30 · wait13 · rc6 · cap1200 · flat21 · mb250 · SL1000/TP4800 · sls5/2200 · near_box N=6 D=1000 · **near_box_trend=off** · wick_on · trail arm4000/tr200 · timeout market · wait_from_break · pullback required) vs KEEP ticks PF2.74/+128025.8 n148 (run 20260925T143120Z_5cdb5840).
- **Next:** score R_tick when finished vs KEEP; if reject → runners mb225_w13_req then nb_N6_D1000_breakout / flat23_hold14 / tr150. Still ~128k vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~19:19 Europe/Bucharest Asia TICK CONFIRM R_tick nb_N6_D1000_off on KEEP trail (run 20260925T155938Z_d2ff55aa) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb250**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T15:44Z finished 15:59Z UTC.
- **Result:** n164 · win48.2% · **+134918.2** · **PF 2.61** (avg +822.7 / win +2771.4 / loss −988.5). exits flatten40 / sl83 / trail39 / tp2. trail_armed 41 (25.0%). entries ema_touch118 / higher_close6 / near_box_timeout40. skipped 265 (no_break167 / no_pullback79 / late_short19). saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T155938Z_d2ff55aa.json.
- **vs PRIOR KEEP** wick_on outside N6 trail tp4800 ticks PF2.74/+128025.8 n148 (run 20260925T143120Z_5cdb5840): ΔPF **−0.13** · Δpts **+6892.4** · n **+16** — meaningful pts lift at soft PF≥2.5; **PROMOTE**.
- **vs 5m screen** nb_N6_D1000_off PF2.664/+141464.6 n164: tick **underdelivers some pts** (~+134.9k PF2.61) but still beats KEEP; volume from near_box_timeout 40 vs prior 24.
- **Conclusion:** NEW KEEP = N6 D1000 · **near_box_trend=off** · **TP4800** · flat21 · SL1000 · sls5 · **wick_on** · **trail arm4000/tr200** · ticks PF2.61/+134918.2 n164. Still ~135k vs ~157k goal. Skip R runners mb225/breakout/flat23/tr150 on old outside seed (re-test under Batch S on NEW KEEP).
- **Next:** Batch S 5m VOL_HOLD_S_KEEP_NBOFF (volume expand mb/wait/max_break/pullback · hold/flatten · trail refine · soft 1:1.5 on NEW KEEP near_box=off). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 meaningful pts). No reaktor / no push.


### 2026-09-25 ~19:41 Europe/Bucharest Asia Batch S VOL_HOLD_S_KEEP_NBOFF 5m (37 cells) — soft≥2.5 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T162327Z.json` · tag `VOL_HOLD_S_KEEP_NBOFF` · seed CURRENT KEEP ticks `20260925T155938Z_d2ff55aa` (near_box_trend=off N6 D1000 TP4800 trail arm4000/tr200 flat21 mb250) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: volume expand mb/wait/max_break/pullback · near-box N/D refine · hold/flatten · trail refine · soft 1:1.5 books.
- **Baseline 5m KEEP** (`KEEP_nboff_baseline`): n164 · PF **2.664** · **+141464.6**.
- **Soft ≥2.5 pts lifts:** `mb200_w13_req` PF **2.552** / **+144203.0** n177 — ΔPF **−0.112** · Δpts **+2738.4** (largest soft≥2.5 pts); `mb225_w13_req` PF **2.603** / **+144103.3** n172 — Δpts **+2638.7**; `tr_tp4800_arm4000_tr150` PF **2.687** / **+143464.6** n164 — Δpts **+2000**.
- **High pts but soft-floor-only (PF≪2.5 prefer):** `pullback_preferred` PF **2.256** / **+172775.3** n243; `mb225_w13_preferred` PF **2.2** / **+172106.5** n251 — defer unless soft≥2.5 path stalls.
- **PF≥~2.8 but no pts lift vs baseline:** `nb_N6_D1000_breakout` PF **2.963** / **+134554.3** n140 (pts below KEEP 5m); `nb_N6_D1000_outside` PF **2.772** / **+132093.1**.
- **Reject / dilute / inert:** wait 11/12/15 and max_break18/20 dilute PF or pts; N5/N7/D800/D1200 under or ~KEEP; flatten/hold mostly inert (=KEEP); denser SL 1200/1333 soft-floor-only; trail-off TP4800 PF2.301; arm3800/4200/tr300 cut pts vs tr150.
- **Conclusion:** Looser mb200 (then mb225) is the cleanest soft≥2.5 pts edge on near_box=off trail KEEP; tr150 is a mild trail refine. Do **not** promote on 5m alone. Prefer-mode volume is pts-rich but PF ~2.2–2.26 — hold for later if mb path fails.
- **Next:** overnight **tick-confirm** `S_tick mb200_w13_req` (min_break 200/200) on CURRENT KEEP near_box=off trail seed (workers=2). Optional runners mb225_w13_req then tr150 if champ rejects. Still ~135k ticks KEEP vs ~157k goal. No reaktor / no push.



### 2026-09-25 ~20:12 Europe/Bucharest Asia TICK CONFIRM S_tick mb200_w13_req on KEEP near_box=off trail (run `20260925T165846Z_750e86cc`) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb200**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T16:45Z finished 16:58Z UTC.
- **Result:** n177 · win47.5% · **+139320.6** · **PF 2.52** (avg +787.1 / win +2752.7 / loss −988.3). exits flatten44 / sl90 / trail41 / tp2. trail_armed 43 (24.3%). entries ema_touch126 / higher_close7 / near_box_timeout44. skipped 252 (no_break156 / no_pullback79 / late_short17). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T165846Z_750e86cc.json`.
- **vs PRIOR KEEP** near_box=off trail tp4800 mb250 ticks PF2.61/+134918.2 n164 (run 20260925T155938Z_d2ff55aa): ΔPF **−0.09** · Δpts **+4402.4** · n **+13** — meaningful pts lift at soft PF≥2.5; **PROMOTE**.
- **vs 5m screen** mb200_w13_req PF2.552/+144203 n177: tick **underdelivers some pts** (~+139.3k PF2.52) but still beats KEEP.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb200** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail arm4000/tr200 · ticks PF2.52/+139320.6 n177. Still ~139k vs ~157k goal. Skip S runners mb225/tr150 on old mb250 seed (re-test under Batch T on NEW KEEP).
- **Next:** Batch T 5m `HOLD_TRAIL_T_KEEP_MB200` (hold/flatten expand · trail refine · mild volume around mb200 · soft 1:1.5 · near-box refine on NEW KEEP). Tick-confirm only PF≥~2.8 pts lifts (or soft ≥2.5 meaningful pts). Prefer-mode volume still deferred (PF~2.2 on 5m). No reaktor / no push.

### 2026-09-25 ~20:16 Europe/Bucharest Asia Batch T HOLD_TRAIL_T_KEEP_MB200 5m (43 cells) — soft≥2.5 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T171600Z.json` · tag `HOLD_TRAIL_T_KEEP_MB200` · seed CURRENT KEEP ticks `20260925T165846Z_750e86cc` (mb200 near_box=off N6 D1000 TP4800 trail arm4000/tr200 flat21) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: hold/flatten · trail refine · mild volume · near-box · soft 1:1.5. Note: `flat24_hold14` errored (hour must be 0..23).
- **Baseline 5m KEEP** (`KEEP_mb200_baseline`): n177 · PF **2.552** · **+144203.0**.
- **Soft ≥2.5 pts lifts:** `tr_tp4800_arm4000_tr100` PF **2.597** / **+148403.0** n177 — ΔPF **+0.045** · Δpts **+4200** (largest soft≥2.5); `tr_tp4800_arm4000_tr150` PF **2.575** / **+146303.0** — Δpts **+2100**; `mb175_w13_req` PF **2.503** / **+145643.0** — Δpts **+1440**; `flat23_hold14` PF **2.558** / **+144923.2** — mild Δpts **+720**; flat23_hold16/18 mild.
- **High pts but soft-floor-only (PF≪2.5 prefer):** `pullback_preferred` PF **2.156** / **+170334.3** n256 — still deferred.
- **PF≥~2.8 pts lifts:** none (best PF refine `nb_N6_D1000_breakout` PF **2.741** / **+133011** under KEEP pts).
- **Reject / dilute / inert:** denser SL 1200/1333/1500 soft-floor-only or under; trail-off TP4800/5200 cut; mb225/250 under or ~KEEP; wait12/14/15 dilute; max_break12/18/20 dilute; N5/N7/D800/D1200 under or mild; hold12/16/18/20 mostly inert.
- **Conclusion:** Tighter trail (tr100 then tr150) is the cleanest soft≥2.5 pts edge on mb200 KEEP. Do **not** promote on 5m alone. Prefer-mode still deferred.
- **Next:** overnight **tick-confirm** `T_tick tr_tp4800_arm4000_tr100` (trail_pts=100) on CURRENT KEEP mb200 seed (workers=2). Optional runners tr150 then mb175_w13_req / flat23_hold14 if champ rejects. Still ~139k ticks KEEP vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~20:41 Europe/Bucharest Asia TICK CONFIRM T_tick tr_tp4800_arm4000_tr100 on KEEP mb200 (run `20260925T173113Z_6b40d45c`) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb200**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail100**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T17:17Z finished 17:31Z UTC.
- **Result:** n177 · win47.5% · **+138184.2** · **PF 2.5** (avg +780.7 / win +2739.2 / loss -988.3). exits flatten44 / sl90 / trail42 / tp1. trail_armed 43 (24.3%). entries ema_touch126 / higher_close7 / near_box_timeout44. skipped 252 (no_break156 / no_pullback79 / late_short17). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T173113Z_6b40d45c.json`.
- **vs CURRENT KEEP** mb200 near_box=off trail tp4800 arm4000/tr200 ticks PF2.52/+139320.6 n177 (run `20260925T165846Z_750e86cc`): ΔPF **-0.02** · Δpts **-1136.4** · n **+0** — no pts lift; **REJECT**.
- **vs 5m screen** tr_tp4800_arm4000_tr100 PF2.597/+148403 n177: tick **underdelivers** (~+138.2k PF2.50); trail locks slightly worse than KEEP tr200 (trail42/tp1 vs KEEP trail41/tp2).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb200** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail **arm4000/tr200** · ticks PF2.52/+139320.6 n177. Still ~139k vs ~157k goal.
- **Next:** overnight tick-confirm `T_runner tr_tp4800_arm4000_tr150` (trail_pts=150) on CURRENT KEEP mb200 seed (workers=2). Then mb175_w13_req / flat23_hold14 if reject. Prefer-mode volume still deferred. No reaktor / no push.


### 2026-09-25 ~21:21 Europe/Bucharest Asia TICK CONFIRM T_runner tr_tp4800_arm4000_tr150 on KEEP mb200 (run 20260925T175720Z_b28d0952) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb200**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail150**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T17:43Z finished 17:57Z UTC.
- **Result:** n177 · win47.5% · **+138186.1** · **PF 2.5** (avg +780.7 / win +2739.2 / loss −988.3). exits flatten44 / sl90 / trail41 / tp2. trail_armed 43 (24.3%). entries ema_touch126 / higher_close7 / near_box_timeout44. skipped 252 (no_break156 / no_pullback79 / late_short17). saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T175720Z_b28d0952.json.
- **vs CURRENT KEEP** mb200 near_box=off trail tp4800 arm4000/tr200 ticks PF2.52/+139320.6 n177 (run 20260925T165846Z_750e86cc): ΔPF **-0.02** · Δpts **-1134.5** · n **+0** — no pts lift; **REJECT**.
- **vs 5m screen** tr_tp4800_arm4000_tr150 PF2.575/+146303 n177: tick **underdelivers** (~+138.2k PF2.50); nearly identical to rejected tr100.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb200** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail **arm4000/tr200** · ticks PF2.52/+139320.6 n177. Still ~139k vs ~157k goal. Trail tighten (tr100/tr150) closed on ticks.
- **Next:** overnight tick-confirm T_runner mb175_w13_req (min_break 175/175, trail KEEP tr200) on CURRENT KEEP mb200 seed (workers=2). Then flat23_hold14 if reject. Prefer-mode volume still deferred. No reaktor / no push.

### 2026-09-25 ~21:52 Europe/Bucharest Asia TICK CONFIRM T_runner mb175_w13_req on KEEP mb200 (run `20260925T183520Z_052f1311`) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb175**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. finished 18:35Z UTC.
- **Result:** n183 · win47.0% · **+140780.6** · **PF 2.47** (avg +769.3 / win +2752.2 / loss −988.7). exits flatten45 / sl94 / trail42 / tp2. trail_armed 44 (24.0%). entries ema_touch130 / higher_close7 / near_box_timeout46. skipped 246 (no_break149 / no_pullback80 / late_short17). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T183520Z_052f1311.json`.
- **vs CURRENT KEEP** mb200 near_box=off trail tp4800 arm4000/tr200 ticks PF2.52/+139320.6 n177 (run `20260925T165846Z_750e86cc`): ΔPF **-0.05** · Δpts **+1460.0** · Δn **+6** — mild pts lift but PF under soft ≥2.5; **REJECT**.
- **vs 5m screen** mb175_w13_req PF2.503/+145643: tick underdelivers (~+140.8k PF2.47).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb200** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail **arm4000/tr200** · ticks PF2.52/+139320.6 n177. Still ~139k vs ~157k goal. Trail tighten + mb175 closed on ticks.
- **Next:** overnight tick-confirm `T_runner flat23_hold14` (flatten_hour=23, max_hold=14, trail KEEP tr200, mb200) on CURRENT KEEP seed (workers=2). If reject → Batch U 5m (prefer-mode volume still deferred unless soft≥2.5 path stalls). No reaktor / no push.


### 2026-09-25 ~22:19 Europe/Bucharest Asia TICK CONFIRM T_runner flat23_hold14 on KEEP mb200 (run 20260925T190633Z_4ea1aaec) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat23**, **mb200**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, pullback required, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T18:52Z finished 19:06Z UTC.
- **Result:** n177 · win46.3% · **+139928.9** · **PF 2.52** (avg +790.6 / win +2828.9 / loss −968.9). exits flatten43 / sl91 / trail41 / tp2. trail_armed 43 (24.3%). entries ema_touch126 / higher_close7 / near_box_timeout44. skipped 252 (no_break156 / no_pullback79 / late_short17). saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T190633Z_4ea1aaec.json.
- **vs CURRENT KEEP** mb200 near_box=off trail tp4800 arm4000/tr200 flat21 ticks PF2.52/+139320.6 n177 (run 20260925T165846Z_750e86cc): ΔPF **0.0** · Δpts **+608.3** · n **+0** — thin pts only (~0.4%); not meaningful; win% −1.2pp; **REJECT**.
- **vs 5m screen** flat23_hold14 PF2.558/+144923: tick underdelivers (~+139.9k PF2.52); matches mild 5m Δpts.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb200** · **TP4800** · **flat21** · SL1000 · sls5 · wick_on · trail **arm4000/tr200** · ticks PF2.52/+139320.6 n177. Still ~139k vs ~157k goal. Batch T soft≥2.5 tick runners all closed (tr100/tr150/mb175/flat23).
- **Next:** Batch U 5m PREF_VOL_U_KEEP_MB200 (prefer-mode volume stall path — soft≥2.5 path stalled). Seek PF≥~2.0 pts lifts / any soft≥2.5 recoveries on prefer lineage. No reaktor / no push.

### 2026-09-25 ~22:22 Europe/Bucharest Asia Batch U PREF_VOL_U_KEEP_MB200 5m (43 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T192051Z.json` · tag `PREF_VOL_U_KEEP_MB200` · seed CURRENT KEEP ticks `20260925T165846Z_750e86cc` (mb200 near_box=off N6 D1000 TP4800 trail arm4000/tr200 flat21) · candles_5m · workers=2 · window 2025-01→2026-09. Soft≥2.5 Batch T runners closed → prefer-mode stall path.
- **Baseline 5m KEEP** (`KEEP_mb200_baseline`): n177 · PF **2.552** · **+144203.0**.
- **Soft ≥2.5 pts lifts:** none (prefer dilutes PF; only `pref_timeout_ema200` PF **2.599** / **+139766.4** n163 under baseline pts).
- **Soft ≥2.0 pts champ:** `pref_mb275` PF **2.32** / **+178919.8** n242 — ΔPF **−0.232** · Δpts **+34716.8** (ties `pref_mb275_minasia400` / `pref_mb275_nb_breakout` — minasia/nb_breakout inert). Runners: `pref_tr100` PF2.193/+175834; `pref_mb250` PF2.256/+172775; `pref_alone` PF2.156/+170334.
- **Reject / dilute / inert:** minasia alone = pref_alone; near-box N/D refine = pref_alone; news_skip/side splits cut or dilute; denser SL under; timeout_ema200 PF≥2.5 but pts below KEEP 5m.
- **Conclusion:** Prefer + **mb275** is the cleanest soft≥2.0 high-pts edge (~+179k vs ~144k 5m KEEP; PF2.32 above soft floor ~2.0, under prefer ≥2.5). Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `U_tick pref_mb275` (pullback preferred · min_break 275/275 · else KEEP) workers=2. Optional runners pref_tr100 / pref_mb250 if champ rejects. Still ~139k ticks KEEP vs ~157k goal. No reaktor / no push.

### 2026-09-25 ~22:48 Europe/Bucharest Asia TICK CONFIRM U_tick pref_mb275 on KEEP mb200 (run `20260925T193550Z_8cdcadd4`) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T19:22Z finished 19:35Z UTC.
- **Result:** n242 · win43.8% · **+165482.4** · **PF 2.23** (avg +683.8 / win +2829.9 / loss -988.8). exits flatten54 / sl133 / trail53 / tp2. trail_armed 55 (22.7%). entries ema_touch117 / higher_close6 / timeout_market119. skipped 187 ({'no_break': 169, 'late_short': 18}). saved `C:/Users/user/strateg/results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T193550Z_8cdcadd4.json`.
- **vs PRIOR KEEP** mb200 near_box=off trail tp4800 required ticks PF2.52/+139320.6 n177 (run `20260925T165846Z_750e86cc`): ΔPF **-0.29** · Δpts **+26161.8** · n **+65** — hits ~157k+ pts goal (+165.5k) at soft PF floor ≥~2.0 (Batch U stall path); under prefer ≥2.5 but meaningful tradeoff; **PROMOTE**.
- **vs 5m screen** pref_mb275 PF2.32/+178919.8 n242: tick underdelivers some pts (~+165.5k PF2.23) but still clears goal and prior KEEP by a wide margin.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail arm4000/tr200 · **pullback preferred** · ticks PF2.23/+165482.4 n242. Pts goal met; next recover PF toward ≥2.5 without giving back the pts lift.
- **Next:** Batch V 5m `PF_RECOVER_V_KEEP_PREF_MB275` (trail/flatten/near-box/soft 1:1.5/mild volume on NEW KEEP prefer+mb275). Tick-confirm only soft≥2.0 pts lifts or PF≥~2.5 recoveries that hold ≥~157k pts. Optional U runners pref_mb250/pref_tr100 deferred (weaker 5m than champ). No reaktor / no push.


### 2026-09-25 ~23:22 Europe/Bucharest Asia Batch V PF_RECOVER_V_KEEP_PREF_MB275 5m (39 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T194802Z.json` · tag `PF_RECOVER_V_KEEP_PREF_MB275` · seed NEW KEEP ticks `20260925T193550Z_8cdcadd4` (prefer+mb275 near_box=off N6 D1000 TP4800 trail arm4000/tr200 flat21 PF2.23/+165482.4) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: trail refine · flatten/hold · near-box · soft 1:1.5 · mild volume · max_break/wait · timeout gates · sls · pullback_required.
- **Baseline 5m KEEP** (`KEEP_pref_mb275_baseline`): n242 · PF **2.32** · **+178919.8**.
- **Soft ≥2.0 pts lifts:** `tr100` PF **2.36** / **+184319.8** n242 — ΔPF **+0.04** · Δpts **+5400** (largest); `maxbreak18` PF **2.211** / **+183487.9** n266 — Δpts **+4568** (PF under baseline); `tr150` PF **2.34** / **+181619.8** — Δpts **+2700**; `sls4_2200` PF **2.355** / **+180919.8** — Δpts **+2000**; `flat23_hold14` PF **2.322** / **+180635** — Δpts **+1715**; `mb260` PF **2.339** / **+180046** — Δpts **+1126**.
- **PF ≥~2.5 recoveries:** `timeout_ema200` PF **2.797** / **+139340** n149; `pullback_required` PF **2.662** / **+139634** n163 — both **under** ~157k pts floor; do **not** tick-confirm (would give back the U pts lift).
- **Reject / dilute / inert:** near-box N/D/trend = baseline (inert on prefer seed); hold16/18 inert; denser SL 1200/1333/1500 soft-floor dilute or under; trail-off / arm3600 / tp5200 / mb250/300 / w12/15 cut pts; maxbreak12 lifts PF to 2.391 but pts −17.5k.
- **Conclusion:** Tight trail `tr100` is the cleanest soft≥2.0 pts+PF refine on prefer+mb275 KEEP. No PF≥2.5 recovery that holds ≥~157k. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `V_tick tr100` (trail_pts=100, else KEEP prefer+mb275) workers=2. Optional runners tr150 then sls4_2200 / flat23_hold14 / mb260 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-25 ~23:48 Europe/Bucharest Asia TICK CONFIRM V_tick tr100 on KEEP prefer+mb275 (run 20260925T203539Z_f43f271e) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail100**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T20:22Z finished 20:35Z UTC.
- **Result:** n242 · win43.8% · **+164384.0** · **PF 2.22** (avg +679.3 / win +2819.5 / loss −988.8). exits flatten54 / sl133 / trail54 / tp1. trail_armed 55 (22.7%). entries ema_touch117 / higher_close6 / timeout_market119. skipped 187 (no_break169 / late_short18). saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T203539Z_f43f271e.json.
- **vs CURRENT KEEP** prefer+mb275 near_box=off trail tp4800 arm4000/tr200 flat21 ticks PF2.23/+165482.4 n242 (run 20260925T193550Z_8cdcadd4): ΔPF **-0.01** · Δpts **-1098.4** · n **+0** — no pts lift; slight PF dip; **REJECT**.
- **vs 5m screen** tr100 PF2.36/+184319.8 n242: tick **underdelivers** (~+164.4k PF2.22); trail locks slightly worse than KEEP tr200 (trail54/tp1 vs KEEP trail53/tp2).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail **arm4000/tr200** · **pullback preferred** · ticks PF2.23/+165482.4 n242. Pts goal still met (~165.5k); tight trail does not recover PF on ticks.
- **Next:** overnight tick-confirm V_runner tr150 (trail_pts=150, else KEEP prefer+mb275) workers=2. Then sls4_2200 / flat23_hold14 / mb260 if reject. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.
### 2026-09-26 ~00:23 Europe/Bucharest Asia TICK CONFIRM V_runner tr150 on KEEP prefer+mb275 (run 20260925T210448Z_d961041d) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls5/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail150**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T20:51Z finished 21:04Z UTC.
- **Result:** n242 · win43.8% · **+164681.5** · **PF 2.22** (avg +680.5 / win +2822.3 / loss -988.8). exits flatten54 / sl133 / trail53 / tp2. trail_armed 55 (22.7%). entries ema_touch117 / higher_close6 / timeout_market119. skipped 187 (no_break169 / late_short18). saved C:\Users\user\strateg\results\overnight_XAUUSD_2025-01-01_2026-09-01_20260925T210448Z_d961041d.json.
- **vs CURRENT KEEP** prefer+mb275 near_box=off trail tp4800 arm4000/tr200 flat21 ticks PF2.23/+165482.4 n242 (run 20260925T193550Z_8cdcadd4): ΔPF **-0.01** · Δpts **-800.9** · n **+0** — no pts lift; slight PF dip; **REJECT**.
- **vs 5m screen** tr150 PF2.34/+181619.8 n242: tick **underdelivers** (~+164.7k PF2.22); nearly identical to rejected tr100.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · sls5 · wick_on · trail **arm4000/tr200** · **pullback preferred** · ticks PF2.23/+165482.4 n242. Pts goal still met (~165.5k). Trail tighten (tr100/tr150) closed on ticks under prefer+mb275.
- **Next:** overnight tick-confirm V_runner sls4_2200 (skip_late_short_wait=4, asia_pts=2200, else KEEP prefer+mb275 trail tr200) workers=2. Then flat23_hold14 / mb260 if reject. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.


### 2026-09-26 ~00:47 Europe/Bucharest Asia TICK CONFIRM V_runner sls4_2200 on KEEP prefer+mb275 (run 20260925T213636Z_5dfe3133) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, ema30, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls4/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T21:23Z finished 21:36Z UTC.
- **Result:** n240 · win44.2% · **+167482.4** · **PF 2.26** (avg +697.8 / win +2829.9 / loss -988.7). exits flatten54 / sl131 / trail53 / tp2. trail_armed 55 (22.9%). entries ema_touch115 / higher_close6 / timeout_market119. skipped 189 (no_break169 / late_short20). saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T213636Z_5dfe3133.json.
- **vs PRIOR KEEP** prefer+mb275 near_box=off trail tp4800 arm4000/tr200 **sls5** flat21 ticks PF2.23/+165482.4 n242 (run 20260925T193550Z_8cdcadd4): ΔPF **+0.03** · Δpts **+2000.0** · Δn **−2** — soft ≥2.0 pts lift holding >>157k; slight PF improve; **PROMOTE**.
- **vs 5m screen** sls4_2200 PF2.355/+180919.8: tick underdelivers some pts (~+167.5k PF2.26) but still clears prior KEEP; late_short skips 20 vs KEEP 18.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · **sls4** · wick_on · trail arm4000/tr200 · **pullback preferred** · ticks PF2.26/+167482.4 n240. Pts goal still met (~167.5k); continue PF recover toward ≥2.5 without giving back ≥~157k.
- **Next:** Batch W 5m PTS_PF_W_KEEP_SLS4 on NEW KEEP prefer+mb275+sls4 (hold/flatten · mb refine · EMA · soft 1:1.5 · TP/arm · cap/rc · timeout soft · sls refine · week2 mild). Tick-confirm soft≥2.0 pts lifts or PF≥~2.5 recoveries that hold ≥~157k. Deferred V runners flat23/mb260 folded into W. No reaktor / no push.

### 2026-09-26 ~01:21 Europe/Bucharest Asia Batch W PTS_PF_W_KEEP_SLS4 5m (50 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T215122Z.json` · tag `PTS_PF_W_KEEP_SLS4` · seed NEW KEEP ticks `20260925T213636Z_5dfe3133` (prefer+mb275+sls4 N6 D1000 trail arm4000/tr200 flat21 TP4800 PF2.26/+167482.4 n240) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: hold/flatten · mb · EMA · soft 1:1.5 · TP/arm · cap/rc · timeout soft · sls refine · week2/seasonal mild · max_break/wait.
- **Baseline 5m KEEP** (`KEEP_sls4_baseline`): n240 · PF **2.355** · **+180919.8**.
- **Soft ≥2.0 pts lifts:** `ema32` PF **2.426** / **+188890.2** n241 — ΔPF **+0.071** · Δpts **+7970.4** (ov ema_period=32); `maxbreak16` PF **2.33** / **+185560.5** n250 — ΔPF **-0.025** · Δpts **+4640.7** (max_break=16); `maxbreak18` PF **2.241** / **+185487.9** n264 — ΔPF **-0.114** · Δpts **+4568.1** (max_break=18); `sls3_2200` PF **2.391** / **+182919.8** n238 — ΔPF **+0.036** · Δpts **+2000.0** (sls3/2200); `flat23_hold14` PF **2.356** / **+182635.0** n240 — ΔPF **+0.001** · Δpts **+1715.2** (flat23); `flat23_hold16` PF **2.356** / **+182565.3** n240 — ΔPF **+0.001** · Δpts **+1645.5** (flat23+hold16); `mb260` PF **2.356** / **+181046.0** n240 — ΔPF **+0.001** · Δpts **+126.2** (mb260 thin).
- **PF ≥~2.5 recoveries:** `timeout_ema400` PF **2.631** / **+144374.0** n168 — ΔPF **+0.276** · Δpts **-36545.8**; `timeout_ema300` PF **2.7** / **+141978.1** n160 — ΔPF **+0.345** · Δpts **-38941.7** — all under ~157k pts floor; do **not** tick-confirm.
- **Reject / dilute / inert:** minasia/cap/week2_tag/seasonal_tag/hold16–18 alone = baseline; denser SL / shorter wait / ema28/36 / mb250/280/300 / arm extremes cut pts; seasonal_filter PF2.459/+166293 under baseline pts; week2_filter cuts heavily.
- **Conclusion:** `ema32` is the cleanest soft≥2.0 pts+PF refine on NEW KEEP sls4 (both ΔPF and Δpts up on 5m). Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `W_tick ema32` (ema_period=32, else KEEP prefer+mb275+sls4) workers=2. Optional runners maxbreak16 then sls3_2200 / flat23_hold14 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~01:44 Europe/Bucharest Asia TICK CONFIRM W_tick ema32 on KEEP prefer+mb275+sls4 (run 20260925T223522Z_a0a8fc1a) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls4/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T22:21:54Z finished 2026-09-25T22:35:22Z.
- **Result:** n241 · win44.4% · **+172203.4** · **PF 2.3** (avg +714.5 / win +2847.3 / loss -988.5). exits flatten54 / sl131 / trail53 / tp3. trail_armed 56 (23.2%). entries ema_touch110 / higher_close6 / timeout_market125. skipped 188 (no_break169 / late_short19). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T223522Z_a0a8fc1a.json`.
- **vs PRIOR KEEP** prefer+mb275+sls4 **ema30** trail tp4800 arm4000/tr200 flat21 ticks PF2.26/+167482.4 n240 (run 20260925T213636Z_5dfe3133): ΔPF **+0.04** · Δpts **+4721.0** · Δn **+1** — meaningful pts lift at soft ≥2.0 holding >>157k; slight PF improve; **PROMOTE**.
- **vs 5m screen** ema32 PF2.426/+188890.2 n241: tick underdelivers some pts (~+172.2k PF2.30) but still clears prior KEEP; more timeout_market entries (125 vs prior ~119) and +1 trade.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · **sls4** · wick_on · trail arm4000/tr200 · **pullback preferred** · **ema32** · ticks PF2.3/+172203.4 n241. Pts goal still met (~172.2k); continue PF recover toward ≥2.5 without giving back ≥~157k.
- **Next:** Batch X 5m `PTS_PF_X_KEEP_EMA32` on NEW KEEP ema32 (deferred W runners maxbreak/sls3/flat23 + hold/mb/trail/soft 1:1.5/timeout/near-box). Tick-confirm soft≥2.0 pts lifts or PF≥~2.5 recoveries that hold ≥~157k. No reaktor / no push.

### 2026-09-26 ~01:45 Europe/Bucharest Asia Batch X PTS_PF_X_KEEP_EMA32 5m (47 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T224440Z.json` · tag `PTS_PF_X_KEEP_EMA32` · seed NEW KEEP ticks `20260925T223522Z_a0a8fc1a` (prefer+mb275+sls4 **ema32** N6 D1000 trail arm4000/tr200 flat21 TP4800 PF2.3/+172203.4 n241) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: deferred W runners · hold/flatten · mb · trail · soft 1:1.5 · timeout · near-box · cap/rc · week2/seasonal mild.
- **Baseline 5m KEEP** (`KEEP_ema32_baseline`): n241 · PF **2.426** · **+188890.2**.
- **Soft ≥2.0 pts lifts:** `tr100` PF **2.468** / **+194490.2** n241 — ΔPF **+0.042** · Δpts **+5600.0**; `maxbreak16` PF **2.381** / **+192678.1** n252 — ΔPF **-0.045** · Δpts **+3787.9**; `maxbreak18` PF **2.288** / **+192616.0** n266 — ΔPF **-0.138** · Δpts **+3725.8**; `tr150` PF **2.447** / **+191690.2** n241 — ΔPF **+0.021** · Δpts **+2800.0**; `sls3_2200` PF **2.463** / **+190890.2** n239 — ΔPF **+0.037** · Δpts **+2000.0**; `maxbreak20` PF **2.196** / **+190762.3** n278 — ΔPF **-0.23** · Δpts **+1872.1**; `flat23_hold14` PF **2.426** / **+190557.2** n241 — ΔPF **+0.0** · Δpts **+1667.0**; `flat23_hold16` PF **2.426** / **+190535.5** n241 — ΔPF **+0.0** · Δpts **+1645.3**; `mb260` PF **2.445** / **+190016.4** n240 — ΔPF **+0.019** · Δpts **+1126.2**.
- **PF ≥~2.5 recoveries:** `timeout_ema400` PF **2.78** / **+152200.4** n166 — ΔPF **+0.354** · Δpts **-36689.8**; `timeout_ema500` PF **2.556** / **+144703.9** n174 — ΔPF **+0.13** · Δpts **-44186.3** — all under ~157k pts floor; do **not** tick-confirm.
- **Reject / dilute / inert:** near-box N/D/trend + timeout_minbreak100 + week2/seasonal_tag + hold16/18 alone = baseline; denser SL 1200/1333 cut under ~157k; tp5200/arm3800 dilute; ema34/36 / mb250/280/300 / cap1000 / rc5/7 cut or mild under; maxbreak20 PF 2.196 soft-floor-only.
- **Conclusion:** `tr100` is the cleanest soft≥2.0 pts+PF refine on NEW KEEP ema32 (both ΔPF and Δpts up on 5m). Do **not** promote on 5m alone. Note: prior prefer+mb275 ema30 tr100/tr150 rejected on ticks — re-check under ema32.
- **Next:** overnight **tick-confirm** `X_tick tr100` (trail_pts=100, else KEEP prefer+mb275+sls4+ema32) workers=2. Optional runners maxbreak16 then tr150 / sls3_2200 / flat23_hold14 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~02:20 Europe/Bucharest Asia TICK CONFIRM X_tick tr100 on KEEP prefer+mb275+sls4+ema32 (run 20260925T225930Z_43654168) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls4/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **trail arm4000 / trail100**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T22:45Z finished 22:59Z UTC.
- **Result:** n241 · win44.4% · **+171651.7** · **PF 2.3** (avg +712.2 / win +2842.1 / loss −988.5). exits flatten54 / sl131 / trail55 / tp1. trail_armed 56 (23.2%). entries ema_touch110 / higher_close6 / timeout_market125. skipped 188 (no_break169 / late_short19). saved results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T225930Z_43654168.json.
- **vs CURRENT KEEP** prefer+mb275+sls4 **ema32** trail tp4800 arm4000/tr200 flat21 ticks PF2.3/+172203.4 n241 (run 20260925T223522Z_a0a8fc1a): ΔPF **0.0** · Δpts **-551.7** · Δn **0** — no pts lift; PF flat; **REJECT**.
- **vs 5m screen** tr100 PF2.468/+194490.2 n241: tick **underdelivers** (~+171.7k PF2.3); trail locks slightly worse than KEEP tr200 (trail55/tp1 vs KEEP trail53/tp3). Mirrors prior ema30 tr100 reject pattern.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · **sls4** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · ticks PF2.3/+172203.4 n241. Pts goal still met (~172.2k); tight trail does not lift under ema32 on ticks.
- **Next:** overnight tick-confirm X_runner maxbreak16 (max_break_candles_after=16, else KEEP prefer+mb275+sls4+ema32 trail tr200) workers=2. Then tr150 / sls3_2200 / flat23_hold14 if reject. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~02:41 Europe/Bucharest Asia TICK CONFIRM X_runner maxbreak16 on KEEP prefer+mb275+sls4+ema32 (run 20260925T233333Z_dcc7e635) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls4/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-25T23:20:01Z finished 2026-09-25T23:33:33Z UTC.
- **Result:** n252 · win44.0% · **+175816.3** · **PF 2.26** (avg +697.7 / win +2840.3 / loss -989.0). exits flatten56 / sl138 / trail55 / tp3. trail_armed 58 (23.0%). entries ema_touch115 / higher_close6 / timeout_market131. skipped 177 (no_break157 / late_short20). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260925T233333Z_dcc7e635.json`.
- **vs PRIOR KEEP** prefer+mb275+sls4 **ema32** trail tp4800 arm4000/tr200 **max_break=15** flat21 ticks PF2.30/+172203.4 n241 (run 20260925T223522Z_a0a8fc1a): ΔPF **-0.04** · Δpts **+3612.9** · Δn **+11** — meaningful pts lift at soft ≥~2.0 holding >>157k; slight PF dip still above soft floor; **PROMOTE**.
- **vs 5m screen** maxbreak16 PF2.381/+192678.1 n252: tick underdelivers some pts (~+175.8k PF2.26) but still clears prior KEEP; more timeout_market entries (131 vs 125) and +11 trades.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · **sls4** · wick_on · trail arm4000/tr200 · **pullback preferred** · **ema32** · **max_break=16** · ticks PF2.26/+175816.3 n252. Pts goal still met (~175.8k); continue PF recover toward ≥2.5 without giving back ≥~157k.
- **Next:** Batch Y 5m `PTS_PF_Y_KEEP_MB16` on NEW KEEP maxbreak16 (deferred X runners tr150/sls3/flat23 + hold/mb/trail/soft 1:1.5/timeout/near-box; skip tr100 — twice rejected on ticks). Tick-confirm soft≥2.0 pts lifts or PF≥~2.5 recoveries that hold ≥~157k. No reaktor / no push.

### 2026-09-26 ~03:16 Europe/Bucharest Asia Batch Y PTS_PF_Y_KEEP_MB16 5m (49 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260925T234405Z.json` · tag `PTS_PF_Y_KEEP_MB16` · seed NEW KEEP ticks `20260925T233333Z_dcc7e635` (prefer+mb275+sls4 **ema32 maxbreak16** N6 D1000 trail arm4000/tr200 flat21 TP4800 PF2.26/+175816.3 n252) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: maxbreak controls · deferred X runners (skip tr100) · hold/flatten · mb · trail · soft 1:1.5 · timeout · near-box · cap/rc · week2/seasonal mild.
- **Baseline 5m KEEP** (`KEEP_mb16_baseline`): n252 · PF **2.381** · **+192678.1**.
- **Soft ≥2.0 pts lifts:** `tr150` PF **2.402** / **+195578.1** n252 — ΔPF **+0.021** · Δpts **+2900.0**; `sls3_2200` PF **2.416** / **+194678.1** n250 — ΔPF **+0.035** · Δpts **+2000.0**; `flat23_hold14` PF **2.382** / **+194452.6** n252 — ΔPF **+0.001** · Δpts **+1774.5**; `flat23_hold16` PF **2.382** / **+194430.9** n252 — ΔPF **+0.001** · Δpts **+1752.8**; `mb260` PF **2.399** / **+193804.3** n251 — ΔPF **+0.018** · Δpts **+1126.2**.
- **PF ≥~2.5 recoveries:** none holding ≥~157k; under-floor: `timeout_ema400` PF 2.671/+152892.3 n175 — do **not** tick-confirm under-floor PF≥2.5 cells.
- **Reject / dilute / inert:** near-box N/D/trend + timeout_minbreak100 + week2/seasonal_tag + hold16/18 alone + sls4_2500 ≈ baseline; denser SL 1200/1333 and ema36 under soft floor; tp5200/arm3600 dilute; maxbreak20/22 PF soft-floor-only; w12/w15 cut pts.
- **Conclusion:** `tr150` is the cleanest soft≥2.0 pts+PF refine on NEW KEEP maxbreak16 (Δpts **+2900.0** · ΔPF **+0.021** on 5m). Runners `sls3_2200` / `flat23_hold14` / `mb260`. Do **not** promote on 5m alone. Note: prior tr150 lineages mixed on ticks — re-check under maxbreak16.
- **Next:** overnight **tick-confirm** `Y_tick tr150` (trail_pts=150, else KEEP prefer+mb275+sls4+ema32+maxbreak16) workers=2. Optional runners sls3_2200 then flat23_hold14 / mb260 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~03:51 Europe/Bucharest Asia TICK CONFIRM Y_tick tr150 on KEEP prefer+mb275+sls4+ema32+maxbreak16 (run 20260926T003021Z_1dfeddce) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls4/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail150**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. finished 2026-09-26T00:30:21.163299+00:00.
- **Result:** n252 · win44.0% · **+175428.7** · **PF 2.26** (avg +696.1 / win +2836.8 / loss -989.0). exits flatten56 / sl138 / trail56 / tp2. trail_armed 58 (23.0%). entries ema_touch115 / higher_close6 / timeout_market131. skipped 177 (no_break157 / late_short20). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T003021Z_1dfeddce.json`.
- **vs CURRENT KEEP** prefer+mb275+sls4 **ema32 maxbreak16** trail tp4800 arm4000/tr200 flat21 ticks PF2.26/+175816.3 n252 (run 20260925T233333Z_dcc7e635): ΔPF **+0.0** · Δpts **-387.6** · Δn **+0** — no pts lift; PF flat; **REJECT**.
- **vs 5m screen** tr150 PF2.402/+195578.1 n252: tick **underdelivers** (~+175428.7 PF2.26); trail locks slightly worse than KEEP tr200 (trail56/tp2 vs KEEP trail55/tp3). Continues prior tr150 reject pattern under maxbreak16.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · **sls4** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · ticks PF2.26/+175816.3 n252. Pts goal still met (~175816.3); tight trail does not lift under maxbreak16 on ticks.
- **Next:** overnight tick-confirm Y_runner sls3_2200 (skip_late_short_wait=3, asia_pts=2200, else KEEP prefer+mb275+sls4+ema32+maxbreak16 trail tr200) workers=2. Then flat23_hold14 / mb260 if reject. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~04:14 Europe/Bucharest Asia TICK CONFIRM Y_runner sls3_2200 on KEEP prefer+mb275+sls4+ema32+maxbreak16 (run 20260926T010532Z_f0fa11de) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat21**, **mb275**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. finished 2026-09-26T01:05:32.586021+00:00.
- **Result:** n250 · win44.4% · **+177816.3** · **PF 2.29** (avg +711.3 / win +2840.3 / loss -988.9). exits flatten56 / sl136 / trail55 / tp3. trail_armed 58 (23.2%). entries ema_touch113 / higher_close6 / timeout_market131. skipped 179 (no_break157 / late_short22). saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T010532Z_f0fa11de.json.
- **vs PRIOR KEEP** prefer+mb275+**sls4** ema32 maxbreak16 trail tp4800 arm4000/tr200 flat21 ticks PF2.26/+175816.3 n252 (run 20260925T233333Z_dcc7e635): ΔPF **+0.03** · Δpts **+2000.0** · Δn **−2** — meaningful pts lift with PF up; **PROMOTE**.
- **vs 5m screen** sls3_2200 PF2.416/+194678.1 n250: tick **matches direction** (~+177816.3 PF2.29); Δpts on ticks equals 5m Δpts (+2000).
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · flat21 · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · ticks PF2.29/+177816.3 n250. Pts goal still met (~177.8k); late-short gate loosened to wait=3 lifts volume/pts without PF damage.
- **Next:** Batch Z 5m PTS_PF_Z_KEEP_SLS3 on NEW KEEP sls3 (deferred Y runners flat23_hold14/mb260 + hold/mb/trail/soft 1:1.5/timeout/near-box; sls4 control; skip tr150 — rejected under maxbreak16). Tick-confirm soft≥2.0 pts lifts or PF≥~2.5 recoveries that hold ≥~157k. No reaktor / no push.

### 2026-09-26 ~04:50 Europe/Bucharest Asia Batch Z PTS_PF_Z_KEEP_SLS3 5m (50 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T011636Z.json` · tag `PTS_PF_Z_KEEP_SLS3` · seed NEW KEEP ticks `20260926T010532Z_f0fa11de` (prefer+mb275+**sls3** **ema32 maxbreak16** N6 D1000 trail arm4000/tr200 flat21 TP4800 PF2.29/+177816.3 n250) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: late-short around sls3 · deferred Y runners flat23/mb (skip tr150) · hold/mb · maxbreak/EMA/wait · trail/arm (skip tr150) · soft 1:1.5/TP · timeout/near-box/resume · week2/seasonal mild.
- **Baseline 5m KEEP** (`KEEP_sls3_baseline`): n250 · PF **2.416** · **+194678.1**.
- **Soft ≥2.0 pts lifts:** `flat23_hold14` PF **2.417** / **+196452.6** n250 — ΔPF **+0.001** · Δpts **+1774.5**; `flat23_hold16` PF **2.417** / **+196430.9** n250 — ΔPF **+0.001** · Δpts **+1752.8**; `tr180` PF **2.424** / **+195838.1** n250 — ΔPF **+0.008** · Δpts **+1160.0**; `mb260` PF **2.417** / **+194804.3** n250 — ΔPF **+0.001** · Δpts **+126.2**.
- **PF ≥~2.5 recoveries holding ≥~157k:** `maxbreak14` PF 2.516/+189475.8.
- **Under-floor PF≥2.5 (do NOT tick):** `timeout_ema400` PF 2.73/+154892.3; `timeout_ema500` PF 2.519/+147395.8.
- **Reject / dilute / inert:** inert=`flat21_hold16`, `flat21_hold18`, `mb265`, `timeout_minbreak100`, `nb_N5_D1000`, `nb_N6_D800`, `nb_N7_D1000`, `nb_N6_D1200`, `nb_breakout`, `cap1400`, `seasonal_tag`, `week2_tag`; dilute=sls4_2200_control PF2.381/+192678.1 dpts-2000.0; sls2_2200 PF2.404/+191583.4 dpts-3094.7; sls3_2000 PF2.381/+192678.1 dpts-2000.0; sls3_2500 PF2.388/+190870.4 dpts-3807.7; sls5_2200 PF2.364/+191678.1 dpts-3000.0; flat22_hold14 PF2.396/+193607.3 dpts-1070.8; mb250 PF2.335/+187533.6 dpts-7144.5; mb280 PF2.351/+187098.9 dpts-7579.2; under_soft=ema36 PF1.963/+141987.5; sl1333_tp4000 PF1.918/+154673.8. Skip tr150/tr100 (already rejected on ticks under maxbreak16 lineage).
- **Conclusion:** `flat23_hold14` is the cleanest soft≥2.0 pts+PF refine on NEW KEEP sls3 (Δpts **+1774.5** · ΔPF **+0.001** on 5m). Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `Z_tick flat23_hold14` (flatten_hour=23, else KEEP prefer+mb275+sls3+ema32+maxbreak16) workers=2. Optional runners flat23_hold16 / tr180 / mb260 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.


### 2026-09-26 ~05:18 Europe/Bucharest Asia TICK CONFIRM Z_tick flat23_hold14 on KEEP prefer+mb275+sls3+ema32+maxbreak16 (run 20260926T020406Z_0f6e1462) — **NEW KEEP**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. finished 2026-09-26T02:04:06.911791+00:00.
- **Result:** n250 · win43.6% · **+179437.7** · **PF 2.29** (avg +717.8 / win +2918.2 / loss -983.3). exits flatten53 / sl138 / trail56 / tp3. trail_armed 59 (23.6%). entries ema_touch113 / higher_close6 / timeout_market131. skipped 179 (no_break157 / late_short22). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T020406Z_0f6e1462.json`.
- **vs PRIOR KEEP** prefer+mb275+sls3 ema32 maxbreak16 trail tp4800 arm4000/tr200 **flat21** ticks PF2.29/+177816.3 n250 (run 20260926T010532Z_f0fa11de): ΔPF **+0.0** · Δpts **+1621.4** · Δn **+0** — meaningful pts lift, PF holds soft ≥~2.0; **PROMOTE**.
- **vs 5m screen** flat23_hold14 PF2.417/+196452.6 n250: tick **matches direction** (~+179437.7 PF2.29); Δpts +1621.4 on ticks vs +1774.5 on 5m.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250. Pts goal still met (~179.4k); later flatten captures residual trail/tp without PF damage.
- **Next:** Batch AA 5m PTS_PF_AA_KEEP_FLAT23 on NEW KEEP flat23 (deferred Z runners tr180/mb260/flat23_hold16 + hold/flatten refine · mb · trail/arm skip tr100/tr150 · soft 1:1.5 · timeout soft · near-box N/D · resume/cap/rc · wait/maxbreak mild · week2/seasonal mild · sls4 control). Tick-confirm soft≥2.0 pts lifts or PF≥~2.5 recoveries that hold ≥~157k. No reaktor / no push.

### 2026-09-26 ~05:24 Europe/Bucharest Asia Batch AA PTS_PF_AA_KEEP_FLAT23 5m (49 cells) - soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T022313Z.json` · tag `PTS_PF_AA_KEEP_FLAT23` · seed NEW KEEP ticks `20260926T020406Z_0f6e1462` (prefer+mb275+**sls3** **ema32 maxbreak16** **flat23** N6 D1000 trail arm4000/tr200 TP4800 PF2.29/+179437.7 n250) · candles_5m · workers=2 · window 2025-01–2026-09. Axes: deferred Z runners tr180/mb260/flat23_hold16 · hold/flatten refine · mb · trail/arm (skip tr100/tr150) · soft 1:1.5 · timeout soft · near-box N/D · resume/cap/rc · wait/maxbreak mild · week2/seasonal mild · sls4 control. Error cell: `flat24_hold14` (hour must be in 0..23).
- **Baseline 5m KEEP** (`KEEP_flat23_baseline`): n250 · PF **2.417** · **+196452.6**.
- **Soft ≥2.0 pts lifts:** `tr180` PF **2.425** / **+197632.6** n250 — ΔPF **+0.008** · Δpts **+1180.0**; `maxbreak18` PF **2.325** / **+196988.1** n264 — ΔPF **-0.092** · Δpts **+535.5**; `mb260` PF **2.418** / **+196578.9** n250 — ΔPF **+0.001** · Δpts **+126.3**.
- **PF ≥~2.5 recoveries holding ≥~157k:** `maxbreak15_control` PF 2.463/+192557.2 n239; `maxbreak14` PF 2.527/+191910.3 n230 (pts below 5m KEEP baseline — not soft pts lifts; optional PF-recovery only if needed later).
- **Under-floor PF≥2.5 (do NOT tick):** `timeout_ema400` PF 2.744/+156071.7; `timeout_ema500` PF 2.519/+148071.7.
- **Reject / dilute / inert:** inert=`mb265`, `mb270`, `timeout_minbreak100`, `timeout_minbreak150`, `nb_N5_D1000`, `nb_N7_D1000`, `nb_N6_D800`, `nb_N6_D1200`, `nb_breakout`, `cap1400`, `week2_tag`, `seasonal_tag`; dilute=`sl1333_tp4000` PF1.912/+153718.9 dpts-42733.7; `sl1200_tp3600` PF2.013/+156473.0 dpts-39979.6; `w12` PF2.248/+175348.8 dpts-21103.8; `arm3600_tr200` PF2.279/+176131.2 dpts-20321.4; `mb300` PF2.289/+180046.4 dpts-16406.2; `arm4400_tr200` PF2.275/+181840.2 dpts-14612.4; `sl1000_tp5200` PF2.275/+181840.2 dpts-14612.4; `arm3800_tr200` PF2.348/+186853.9 dpts-9598.7; `sl1000_tp4500` PF2.348/+186853.9 dpts-9598.7; `tr180_arm3800` PF2.356/+188053.9 dpts-8398.7; `mb250` PF2.337/+189308.2 dpts-7144.4; `mb280` PF2.357/+189516.9 dpts-6935.7; +16 more; under_soft=`sl1333_tp4000` PF1.912/+153718.9 dpts-42733.7. Skip tr150/tr100 (already rejected on ticks under maxbreak16 lineage).
- **Conclusion:** `tr180` is the cleanest soft≥2.0 pts+PF refine on NEW KEEP flat23 (Δpts **+1180.0** · ΔPF **+0.008** on 5m). Runners: `maxbreak18`, `mb260`. Do **not** promote on 5m alone. Skip tr100/tr150 (already rejected on ticks under maxbreak16 lineage).
- **Next:** overnight **tick-confirm** `AA_tick tr180` (trail_pts=180.0, else KEEP prefer+mb275+sls3+ema32+maxbreak16+flat23) workers=2. Optional runners maxbreak18 / mb260 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~05:49 Europe/Bucharest Asia TICK CONFIRM AA_tick tr180 on KEEP prefer+mb275+sls3+ema32+maxbreak16+flat23 (run 20260926T024054Z_b0266cd9) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail180**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-26T02:27:06Z finished 2026-09-26T02:40:54Z UTC.
- **Result:** n250 · win43.6% · **+178929.4** · **PF 2.29** (avg +715.7 / win +2913.5 / loss -983.3). exits flatten53 / sl138 / trail57 / tp2. trail_armed 59 (23.6%). entries ema_touch113 / higher_close6 / timeout_market131. skipped 179 (no_break157 / late_short22). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T024054Z_b0266cd9.json`.
- **vs CURRENT KEEP** prefer+mb275+sls3 ema32 maxbreak16 flat23 trail tp4800 arm4000/**tr200** ticks PF2.29/+179437.7 n250 (run 20260926T020406Z_0f6e1462): ΔPF **0.0** · Δpts **-508.3** · Δn **0** — no pts lift; PF flat; **REJECT**.
- **vs 5m screen** tr180 PF2.425/+197632.6 n250: tick **underdelivers** (~+178929.4 PF2.29); trail locks slightly worse than KEEP tr200 (trail57/tp2 vs KEEP trail56/tp3). Same reject pattern as tr100/tr150 under this lineage.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250. Pts goal still met (~179.4k); tighter trail does not lift under flat23 on ticks.
- **Next:** overnight tick-confirm AA_runner maxbreak18 (max_break_candles_after=18, else KEEP prefer+mb275+sls3+ema32+flat23 trail tr200) workers=2. Then mb260 if reject. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~06:11 Europe/Bucharest Asia TICK CONFIRM AA_runner maxbreak18 on KEEP prefer+mb275+sls3+ema32+flat23 (run 20260926T030602Z_7a80466e) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=18**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-26T02:52:09.080721+00:00 finished 2026-09-26T03:06:02.455967+00:00.
- **Result:** n264 · win42.8% · **+179806.8** · **PF 2.21** (avg +681.1 / win +2906.6 / loss -984.4). exits flatten55 / sl148 / trail58 / tp3. trail_armed 61 (23.1%). entries ema_touch120 / higher_close6 / timeout_market138. skipped 165 (no_break141 / late_short24). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T030602Z_7a80466e.json`.
- **vs CURRENT KEEP** prefer+mb275+sls3 ema32 **maxbreak16** flat23 trail tp4800 arm4000/tr200 ticks PF2.29/+179437.7 n250 (run 20260926T020406Z_0f6e1462): ΔPF **-0.08** · Δpts **+369.1** · Δn **+14** — tiny pts lift with PF drop further from ≥~2.5; not a clear promote; **REJECT**.
- **vs 5m screen** maxbreak18 PF2.325/+196988.1 n264: tick underdelivers pts (~+179806.8 vs +196988.1) and PF (~2.21 vs 2.325); Δpts direction matches but magnitude thin on ticks.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250. Pts goal still met (~179437.7); looser max_break=18 adds thin volume without PF hold.
- **Next:** overnight tick-confirm AA_runner mb260 (min_break_pts_above/below=260, else KEEP prefer+mb275+sls3+ema32+maxbreak16+flat23 trail tr200) workers=2. If reject → Batch AB 5m on KEEP. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~06:51 Europe/Bucharest Asia TICK CONFIRM AA_runner mb260 on KEEP prefer+mb275+sls3+ema32+maxbreak16+flat23 (run 20260926T032812Z_34c5bfcf) — **REJECT**
- **Setup (ticks, 2025-01→2026-09):** asia **0–6**, **ema32**, wait13, rc6, cap1200, **flat23**, **mb260**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-26T03:14:30Z finished 2026-09-26T03:28:12.661267+00:00.
- **Result:** n250 · win43.6% · **+179533.9** · **PF 2.3** (avg +718.1 / win +2918.8 / loss -983.1). exits flatten53 / sl138 / trail56 / tp3. trail_armed 59 (23.6%). entries ema_touch113 / higher_close6 / timeout_market131. skipped 179 (no_break157 / late_short22). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T032812Z_34c5bfcf.json`.
- **vs CURRENT KEEP** prefer+**mb275**+sls3 ema32 maxbreak16 flat23 trail tp4800 arm4000/tr200 ticks PF2.29/+179437.7 n250 (run 20260926T020406Z_0f6e1462): ΔPF **+0.01** · Δpts **+96.2** · Δn **+0** — micro noise, not a meaningful pts lift; **REJECT**.
- **vs 5m screen** mb260 PF2.418/+196578.9 n250: tick ~matches direction (tiny +pts) but magnitude noise (~+96.2 on ticks); AA near-KEEP runners (tr180 / maxbreak18 / mb260) exhausted.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250. Pts goal still met (~179437.7); mb260 does not beat KEEP.
- **Next:** Batch AB `VOL_TP_AB_KEEP_FLAT23` 5m on KEEP (volume expand mb200–240 / wait / pullback · TP/R trail-near-TP · ema/sls/entry · hold mild). Tick-confirm soft≥2.5 pts champs (or clear pts lift at PF≥~2.0 soft floor). Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.


### 2026-09-26 ~07:16 Europe/Bucharest Asia Batch AB VOL_TP_AB_KEEP_FLAT23 5m (47 cells) — no soft≥2.0 pts lift; KEEP unchanged
- **Grid:** `results/overnight_5m_grid_20260926T035148Z.json` · tag `VOL_TP_AB_KEEP_FLAT23` · seed KEEP ticks `20260926T020406Z_0f6e1462` (prefer+mb275+sls3 ema32 maxbreak16 flat23 N6 D1000 trail arm4000/tr200 TP4800 PF2.29/+179437.7 n250) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: volume expand mb200–240/wait/pullback/wick · TP/R trail-near-TP · hold mild · ema/sls/entry · asia range/end · news/nb/timeout_pullback.
- **Baseline 5m KEEP** (`KEEP_flat23_baseline`): n250 · PF **2.417** · **+196452.6**.
- **Soft ≥2.0 pts lifts:** none (baseline is pts champ; inert ties: wick_off / close_outside / asia_range200/400 / news_tag / nb_outside).
- **PF ≥~2.5 recoveries holding ≥~157k:** `pullback_required` PF **2.989** / **+160129.7** n165 (ΔPF **+0.572** · Δpts **−36322.9**); `mb225_req` PF **2.888** / **+164279.0** n174 (ΔPF **+0.471** · Δpts **−32173.6**). Large pts giveback — do **not** tick-confirm (goal remains maximize sum_pts; KEEP already ~179k ticks).
- **Under-floor / dilute:** under_soft=`sl1500_tp4500` PF1.885/+165216; `trail_off` PF1.997/+147276; `ema36` PF1.965/+143480; `asia_end7/5`; `wait_from_box`; `be_arm800`; `pullback_off` PF1.338/+62864. Dilute volume=`mb200/225/240` ~+183–189k; TP/R arms `tp5600/6000/4400` and `arm4500–4800` cut pts; `timeout_pullback80` PF3.051/+141931 (pts under ~157k floor for recovery).
- **Conclusion:** AB volume+TP/R screen finds **no** soft≥2.0 pts refine on KEEP flat23. PF recoveries via pullback_required cut ~32–36k pts — skip tick. KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250.
- **Next:** Batch AC `HOLD_SIDE_AC_KEEP_FLAT23` 5m (hold/flatten expand · side long/short · seasonal/week2 filter+join · trend gates · news filter · timeout_pullback mild · resume/cap · trail widen). Tick-confirm only soft≥2.0 pts lifts or clear pts lift at PF≥~2.0 holding ≥~157k. No reaktor / no push.

### 2026-09-26 ~07:43 Europe/Bucharest Asia Batch AC HOLD_SIDE_AC_KEEP_FLAT23 5m (48 cells) — no tick; KEEP unchanged
- **Grid:** `results/overnight_5m_grid_20260926T041956Z.json` · tag `HOLD_SIDE_AC_KEEP_FLAT23` · seed KEEP ticks `20260926T020406Z_0f6e1462` (prefer+mb275+sls3 ema32 maxbreak16 flat23 N6 D1000 trail arm4000/tr200 TP4800 PF2.29/+179437.7 n250) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: hold/flatten expand · side long/short · seasonal/week2 filter+join · trend gates · news filter · timeout_pullback mild · resume/cap · trail widen · maxbreak17/13 · wait10/16.
- **Baseline 5m KEEP** (`KEEP_flat23_baseline`): n250 · PF **2.417** · **+196452.6**.
- **Soft ≥2.0 pts lifts:** only `maxbreak17` PF **2.392** / **+198553.1** n256 (ΔPF **−0.025** · Δpts **+2100.5**). Skip tick — adjacent `maxbreak18` already tick-REJECT (run 20260926T030602Z_7a80466e PF2.21/+179806.8; tiny pts / PF drop).
- **PF ≥~2.5 holding ≥~157k:** `news_filter` PF **2.528** / **+179752.2** n221 (Δpts **−16700.4**); `maxbreak13` PF **2.527** / **+184274.5** n222 (Δpts **−12178.1**). Pts giveback — do **not** tick-confirm.
- **Under-floor / dilute:** timeout_pullback40/120/200 PF2.965–3.18 / +140–144k (under ~157k); side_long/+110k · side_short PF2.516/+86k (thin); seasonal/week2_filter cut pts; hold/flatten expand all ≤ baseline pts; trail widen tr230–300 / arm3900–4100 dilute; wait10/16 under PF~2.1; inert ties: seasonal_join / week2_join / teff_* / tflat_* / tsess_* / cap1100–1300 / multi_day / asia_range250–350.
- **Conclusion:** AC hold/side/seasonal screen finds **no** actionable soft≥2.0 pts refine after maxbreak18 tick reject. KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250. Pts goal still met (~179437.7).
- **Next:** Batch AD `TIMEOUT_SL_AD_KEEP_FLAT23` 5m (timeout_max_ema_dist / timeout_min_break · be_arm · denser SL + mild SL:TP · near_box N/D · ema28–34 · wait11–15 · sls2/4 · uh_c off). Tick-confirm only soft≥2.0 pts lifts or clear pts lift at PF≥~2.0 holding ≥~157k. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~08:14 Europe/Bucharest Asia Batch AD TIMEOUT_SL_AD_KEEP_FLAT23 5m (44 cells) — no soft≥2.0 pts lift; KEEP unchanged
- **Grid:** 
esults/overnight_5m_grid_20260926T044856Z.json · tag TIMEOUT_SL_AD_KEEP_FLAT23 · seed KEEP ticks 20260926T020406Z_0f6e1462 (prefer+mb275+sls3 ema32 maxbreak16 flat23 N6 D1000 trail arm4000/tr200 TP4800 PF2.29/+179437.7 n250) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: timeout_max_ema_dist / timeout_min_break · be_arm · denser SL + mild SL:TP · near_box N/D · ema28–34 · wait11–15 · sls2/4 · uhc_off.
- **Baseline 5m KEEP** (KEEP_flat23_baseline): n250 · PF **2.417** · **+196452.6**.
- **Soft ≥2.0 pts lifts:** none (baseline is pts champ; inert ties: 	minb_100/	minb_200 / all nb N/D / 
b_breakout/
b_outside).
- **PF ≥~2.5 holding ≥~157k:** 	minb_400 PF **2.552** / **+177465.1** n207 (Δpts **−18987.5**) — pts giveback; do **not** tick-confirm.
- **Under-floor PF≥2.5 (do NOT tick):** 	ema_200 PF 3.076/+148396.8; 	ema_400 / 	ema400_tminb200 PF 2.744/+156071.7.
- **Under-floor / dilute:** 	ema_600/800 ~+151–153k PF2.35–2.46; denser SL sl800/900/1100/1200 and SL:TP 1:1.5 cells cut pts hard; e_arm400–1200 disastrous (be_arm400 +4533 PF1.105); w12/14/15 / ema28/30/34 dilute; sls2/4 / uhc_off mild dilute.
- **Conclusion:** AD timeout/SL/near-box screen finds **no** soft≥2.0 pts refine on KEEP flat23. PF recoveries via timeout gates cut ~19k+ pts or land under ~157k — skip tick. KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=16** · max_hold14 · ticks PF2.29/+179437.7 n250. Pts goal still met (~179437.7).
- **Next:** Batch AE ENTRY_ASIA_AE_KEEP_FLAT23 5m (asia window/range · resume/cap denser · ema_tf · mild trail-arm/widen · sl_cap/mode · asymmetric mb · sls asia_pts · soft PF pocket tema350/tminb350). Tick-confirm only soft≥2.0 pts lifts or clear pts lift at PF≥~2.0 holding ≥~157k. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.

### 2026-09-26 ~08:46 Europe/Bucharest Asia Batch AE ENTRY_ASIA_AE_KEEP_FLAT23 5m (49 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T051523Z.json` · tag `ENTRY_ASIA_AE_KEEP_FLAT23` · seed KEEP ticks `20260926T020406Z_0f6e1462` (prefer+mb275+sls3 ema32 maxbreak16 flat23 N6 D1000 trail arm4000/tr200 TP4800 PF2.29/+179437.7 n250) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: asia window/range · resume/cap denser · ema_tf · mild trail-arm/widen · sl_cap/mode · asymmetric mb · sls asia_pts · soft PF pocket tema350/tminb350. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_flat23_baseline`): n250 · PF **2.417** · **+196452.6**.
- **Soft ≥2.0 pts lifts:** `rc3` PF **2.475** / **+198631.4** n238 — ΔPF **+0.058** · Δpts **+2178.8**; `mb_below250` PF **2.418** / **+196554.5** n250 — ΔPF **+0.001** · Δpts **+101.9**.
- **PF ≥~2.5 recoveries holding ≥~157k:** `rc3` PF 2.475/+198631.4 n238; `tema_350` PF 2.838/+157128.2 n167; `tminb_350` PF 2.45/+179248.9 n225; `tema350_tminb150` PF 2.838/+157128.2 n167.
- **Under-floor PF≥2.5 (do NOT tick):** none.
- **Reject / dilute / inert:** inert=`asia_0_6_range280`, `asia_0_6_range320`, `asia_0_6_range400`, `cap1400`, `cap1500`, `cap1600`, `ema_tf5`, `ema_tf10`, `ema_tf30`, `ema_tf60`, `sl_cap1500`, `sl_cap2500`, `sl_cap3000`, `sl_cap0`; dilute=`asia_0_5` PF1.749/+115538.8 dpts-80913.8; `asia_1_7` PF1.883/+135965.5 dpts-60487.1; `asia_0_7` PF1.895/+136965.5 dpts-59487.1; `arm4500_tr200` PF2.175/+170016.6 dpts-26436.0; `arm3500_tr200` PF2.298/+177399.8 dpts-19052.8; `arm3700_tr200` PF2.29/+178924.3 dpts-17528.3; `sl_asia_opp` PF1.844/+178963.8 dpts-17488.8; `sl_range_mult` PF1.844/+178963.8 dpts-17488.8; `mb_below300` PF2.34/+187130.4 dpts-9322.2; `sls3_2800` PF2.388/+188334.2 dpts-8118.4; `mb_above250` PF2.336/+189206.3 dpts-7246.3; `mb_above300` PF2.366/+189368.6 dpts-7084.0; `rc5` PF2.376/+191419.1 dpts-5033.5; `sls3_1800` PF2.333/+191452.6 dpts-5000.0; +15 more; under_soft=`asia_0_5` PF1.749/+115538.8 dpts-80913.8; `asia_0_7` PF1.895/+136965.5 dpts-59487.1; `asia_1_7` PF1.883/+135965.5 dpts-60487.1; `sl_asia_opp` PF1.844/+178963.8 dpts-17488.8; `sl_range_mult` PF1.844/+178963.8 dpts-17488.8.
- **Conclusion:** `rc3` is the cleanest soft≥2.0 pts+PF refine on KEEP flat23 (Δpts **+2178.8** · ΔPF **+0.058** on 5m). Runners meaningful: none. Micro-noise `mb_below250` (+101.9 pts) skipped. Do **not** promote on 5m alone.
- **Next:** overnight **tick-confirm** `AE_tick rc3` (resume_closes=3, else KEEP prefer+mb275+sls3+ema32+maxbreak16+flat23 trail tr200) workers=2. Optional runners none if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.


### 2026-09-26 ~09:11 Europe/Bucharest Asia TICK CONFIRM AE_tick rc3 on KEEP prefer+mb275+sls3+ema32+maxbreak16+flat23 (run 20260926T060024Z_cde7122c) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, wait13, **rc3**, cap1200, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=16**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-26T05:46:29Z finished 2026-09-26T06:00:24Z UTC.
- **Result:** n238 Â· win42.0% Â· **+181730.0** Â· **PF 2.35** (avg +763.6 / win +3163.8 / loss -975.7). exits flatten43 / sl133 / trail59 / tp3. trail_armed 62 (26.1%). entries ema_touch92 / higher_close62 / timeout_market59 / lower_close25. skipped 191. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T060024Z_cde7122c.json`.
- **vs PRIOR KEEP** prefer+mb275+sls3 ema32 maxbreak16 flat23 trail tp4800 arm4000/tr200 **rc6** ticks PF2.29/+179437.7 n250 (run 20260926T020406Z_0f6e1462): dPF **+0.06** Â· dpts **+2292.3** Â· dn **-12** -- meaningful pts lift with PF up (soft floor ~2.0); **PROMOTE**.
- **vs 5m screen** rc3 PF2.475/+198631.4 n238: tick **matches direction** (~+181730 PF2.35); dpts +2292.3 on ticks vs +2178.8 on 5m.
- **Conclusion:** NEW KEEP = N6 D1000 Â· near_box_trend=off Â· **mb275** Â· **TP4800** Â· **flat23** Â· SL1000 Â· **sls3** Â· wick_on Â· trail **arm4000/tr200** Â· **pullback preferred** Â· **ema32** Â· **max_break=16** Â· max_hold14 Â· **rc3** Â· ticks PF2.35/+181730 n238. Pts goal still met (~181.7k); faster resume (rc3 vs rc6) lifts PF and pts with fewer trades.
- **Next:** Batch AF `CROSS_PF_AF_KEEP_RC3` 5m on NEW KEEP rc3 (denser multi-param crosses Â· soft PF pocket near AE tema350/tminb Â· trail/TP/hold/sls mild under rc3). Tick-confirm only soft>=2.0 pts lifts or clear pts lift at PF>=~2.0 holding >=~157k. Still seek PF toward >=2.5 without giving back >=~157k pts. No reaktor / no push.



### 2026-09-26 ~09:46 Europe/Bucharest Asia Batch AF CROSS_PF_AF_KEEP_RC3 5m (50 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T061459Z.json` · tag `CROSS_PF_AF_KEEP_RC3` · seed KEEP ticks `20260926T060024Z_cde7122c` (asia0-6 ema32 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr200 flat23 sls3 maxbreak16 rc3 PF2.35/+181730 n238) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: resume/cap · soft PF tema/tminb/tpull · mb/wait/maxbreak/ema · trail/TP/hold/sls mild under rc3. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_rc3_baseline`): n238 · PF **2.475** · **+198631.4**.
- **Soft ≥2.0 pts lifts:** `rc3_mb15` PF **2.592** / **+201681.8** n228 — ΔPF **+0.117** · Δpts **+3050.4** · ov={'max_break_candles_after': 15}; `rc3_sls3_2000` PF **2.473** / **+201319.2** n242 — ΔPF **-0.002** · Δpts **+2687.8** · ov={'skip_late_short_asia_pts': 2000.0}; `rc3_cap1000` PF **2.493** / **+201035.2** n239 — ΔPF **+0.018** · Δpts **+2403.8** · ov={'resume_closes': 3, 'resume_max_break_pts': 1000.0}; `rc3_w14` PF **2.492** / **+200763.0** n237 — ΔPF **+0.017** · Δpts **+2131.6** · ov={'max_wait_candles': 14}; `rc3_hold16` PF **2.482** / **+199480.7** n238 — ΔPF **+0.007** · Δpts **+849.3** · ov={'max_hold_hours': 16.0}; `rc3_tr190` PF **2.480** / **+199251.6** n238 — ΔPF **+0.005** · Δpts **+620.2** · ov={'trail_pts': 190.0}; `rc3_hold12` PF **2.481** / **+198725.4** n238 — ΔPF **+0.006** · Δpts **+94.0** · ov={'max_hold_hours': 12.0}; `rc3_mb260` PF **2.476** / **+198655.8** n238 — ΔPF **+0.001** · Δpts **+24.4** · ov={'min_break_pts_above': 260.0, 'min_break_pts_below': 260.0}.
- **PF ≥~2.5 with pts lift:** `rc3_mb15` PF 2.592/+201681.8 n228 (Δpts +3050.4).
- **Under-floor PF<2.0:** `rc2_cap1400` PF1.931/+143191.4; `rc2` PF1.969/+148155.4.
- **Conclusion:** `rc3_mb15` is the cleanest soft≥2.0 pts+PF refine (only PF≥2.5 lift: max_break 15 → PF **2.592** / **+201681.8** · Δpts **+3050.4** · ΔPF **+0.117** on 5m). Runners: `rc3_sls3_2000`, `rc3_cap1000`, `rc3_w14`. Soft PF tema* pocket under-pts vs KEEP — skip. Do **not** promote on 5m alone. KEEP unchanged (ticks rc3 maxbreak16 PF2.35/+181730 n238).
- **Next:** overnight **tick-confirm** `AF_tick rc3_mb15` (max_break_candles_after=15, else KEEP rc3) workers=2. Optional runners later if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.



### 2026-09-26 ~10:20 Europe/Bucharest Asia TICK CONFIRM AF_tick rc3_mb15 on KEEP rc3 maxbreak16 (run 20260926T070036Z_b1ddf95b) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, wait13, **rc3**, cap1200, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2200**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-26T06:46:28.608557+00:00 finished 2026-09-26T07:00:36.575590+00:00.
- **Result:** n228 · win43.0% · **+184962.9** · **PF 2.46** (avg +811.2 / win +3179.7 / loss -974.2). exits flatten42 / sl125 / trail58 / tp3. trail_armed 61 (26.8%). entries ema_touch88 / higher_close57 / timeout_market58 / lower_close25. skipped 201. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T070036Z_b1ddf95b.json`.
- **vs PRIOR KEEP** rc3 maxbreak16 ticks PF2.35/+181730 n238 (run 20260926T060024Z_cde7122c): dPF **+0.11** · dpts **+3232.9** · dn **-10** -- meaningful pts lift with PF up (soft floor ~2.0, near prefer >=2.5); **PROMOTE**.
- **vs 5m screen** rc3_mb15 PF2.592/+201681.8 n228: tick matches direction (~+184962.9 PF2.46); dpts +3232.9 on ticks vs +3050.4 on 5m.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=15** · max_hold14 · **rc3** · ticks PF2.46/+184963 n228. Pts goal still met (~185.0k); tighter max_break=15 lifts PF and pts vs max_break=16.
- **Next:** Batch AG `VOL_SOFT_AG_KEEP_RC3_MB15` 5m on NEW KEEP (denser volume/soft-PF under rc3+mb15: pullback/mb asym/near_box/tema-tminb retainers · trail/TP/hold/sls/wait mild · AF runners sls3_2000/cap1000/w14 as cells). Tick-confirm only soft>=2.0 pts lifts or clear pts lift at PF>=~2.0 holding >=~157k. Still seek PF toward >=2.5 without giving back >=~157k pts. No reaktor / no push.



### 2026-09-26 ~10:43 Europe/Bucharest Asia Batch AG VOL_SOFT_AG_KEEP_RC3_MB15 5m (56 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T072050Z.json` · tag `VOL_SOFT_AG_KEEP_RC3_MB15` · seed KEEP ticks `20260926T070036Z_b1ddf95b` (asia0-6 ema32 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr200 flat23 sls3/2200 maxbreak15 rc3 PF2.46/+184962.9 n228) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: denser volume/soft-PF under rc3+mb15 (pullback/mb asym/near_box/tema-tminb · trail/TP/hold/sls/wait mild · AF runners sls3_2000/cap1000/w14). Error cells: none.
- **Baseline 5m KEEP** (`KEEP_rc3_mb15_baseline`): n228 · PF **2.592** · **+201681.8**.
- **Soft ≥2.0 pts lifts:** `sls3_2000` PF **2.589** / **+204369.6** n232 — ΔPF **-0.003** · Δpts **+2687.8**; `cap1000` PF **2.611** / **+204085.6** n229 — ΔPF **+0.019** · Δpts **+2403.8**; `w14` PF **2.610** / **+203813.4** n227 — ΔPF **+0.018** · Δpts **+2131.6**; `hold16` PF **2.600** / **+202531.1** n228 — ΔPF **+0.008** · Δpts **+849.3**; `sls4` PF **2.549** / **+202357.9** n235 — ΔPF **-0.043** · Δpts **+676.1**; `tr190` PF **2.597** / **+202292.0** n228 — ΔPF **+0.005** · Δpts **+610.2**; `hold12` PF **2.599** / **+201775.8** n228 — ΔPF **+0.007** · Δpts **+94.0**; `mb260` PF **2.593** / **+201706.2** n228 — ΔPF **+0.001** · Δpts **+24.4**.
- **PF ≥~2.5 with pts lift:** `sls3_2000` PF 2.589/+204369.6 n232; `cap1000` PF 2.611/+204085.6 n229; `w14` PF 2.610/+203813.4 n227; `hold16` PF 2.600/+202531.1 n228; `sls4` PF 2.549/+202357.9 n235; `tr190` PF 2.597/+202292.0 n228; `hold12` PF 2.599/+201775.8 n228; `mb260` PF 2.593/+201706.2 n228.
- **Under-floor PF<2.0:** `pullback_off` PF1.367/+65283.3.
- **Reject / dilute / inert:** inert=`cap1100`, `mb270`, `mb_below250`, `wick_off`, `close_outside`, `nb_N5`, `nb_N7`, `nb_N8`, `nb_D800`, `nb_D900`, `nb_D1200`, `nb_breakout`, `nb_outside`, `nb_off`, `tminb_150`, `tminb_200`, `tminb_250`, `tp5000`, `tp4600`, `asia_range280`, `asia_range320`; dilute=`pullback_off` PF1.367/+65283.3 dpts-136398.5; `tpull_20` PF2.337/+135288.6 dpts-66393.2; `tpull_40` PF2.337/+135288.6 dpts-66393.2; `tema_200` PF2.441/+146221.7 dpts-55460.1; `tema200_tminb100` PF2.441/+146221.7 dpts-55460.1; `pullback_required` PF2.538/+154511.9 dpts-47169.9; `tema_250` PF2.504/+155593.2 dpts-46088.6; `tema_280` PF2.504/+155593.2 dpts-46088.6; `tema250_tminb150` PF2.504/+155593.2 dpts-46088.6; `w12` PF2.278/+168024.6 dpts-33657.2; `w15` PF2.361/+176477.8 dpts-25204.0; `ema34` PF2.440/+185260.3 dpts-16421.5; `mb_below300` PF2.507/+192359.6 dpts-9322.2; `mb_above300` PF2.532/+194030.0 dpts-7651.8; `ema30` PF2.520/+194047.8 dpts-7634.0; `mb280` PF2.522/+194295.6 dpts-7386.2; `mb250` PF2.519/+196911.7 dpts-4770.1; `mb_above250` PF2.519/+196911.7 dpts-4770.1.
- **Conclusion:** `sls3_2000` is the cleanest soft≥2.0 pts refine on NEW KEEP rc3+mb15 (Δpts **+2687.8** · ΔPF **-0.003** on 5m; PF stays ≥2.5). Runners: `cap1000`, `w14`, `hold16`. Near-box / tminb / wick / tp± cells largely inert on 5m under this seed. Do **not** promote on 5m alone. KEEP unchanged (ticks rc3 maxbreak15 PF2.46/+184962.9 n228).
- **Next:** overnight **tick-confirm** `AG_tick sls3_2000` (skip_late_short_asia_pts=2000.0, else KEEP rc3+mb15) workers=2. Optional runners cap1000 / w14 / hold16 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.



### 2026-09-26 ~11:20 Europe/Bucharest Asia TICK CONFIRM AG_tick sls3_2000 on KEEP rc3 maxbreak15 (run 20260926T080023Z_f1360884) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, wait13, **rc3**, cap1200, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2000**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, max_hold14. workers=2. data_source=ticks. started 2026-09-26T07:46:33Z finished 2026-09-26T08:00:23.663785+00:00 UTC.
- **Result:** n232 · win43.1% · **+187645.7** · **PF 2.46** (avg +808.8 / win +3162.9 / loss -974.6). exits flatten43 / sl127 / trail59 / tp3. trail_armed 62 (26.7%). entries ema_touch90 / higher_close57 / timeout_market58 / lower_close27. skipped 197. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T080023Z_f1360884.json`.
- **vs PRIOR KEEP** rc3 maxbreak15 sls3/2200 ticks PF2.46/+184962.9 n228 (run 20260926T070036Z_b1ddf95b): dPF **+0.0** · dpts **+2682.8** · dn **+4** -- meaningful pts lift at same PF (soft floor ~2.0, near prefer >=2.5); **PROMOTE**.
- **vs 5m screen** sls3_2000 PF2.589/+204369.6 n232: tick matches direction (~+187645.7 PF2.46); dpts +2682.8 on ticks vs +2687.8 on 5m.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2000** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=15** · max_hold14 · **rc3** · ticks PF2.46/+187645.7 n232. Pts goal still met (~187.6k); looser late-short asia gate (2000 vs 2200) adds ~2683 pts at flat PF.
- **Next:** Batch AH `CROSS_RUN_AH_KEEP_SLS3_2000` 5m on NEW KEEP (AG runners cap1000/w14/hold16/tr190 under sls3_2000 · mild crosses · hold/flatten expand · soft PF pocket · trail/TP mild). Tick-confirm only soft>=2.0 pts lifts or clear pts lift at PF>=~2.0 holding >=~157k. Still seek PF toward >=2.5 without giving back >=~157k pts. No reaktor / no push.



### 2026-09-26 ~11:45 Europe/Bucharest Asia Batch AH CROSS_RUN_AH_KEEP_SLS3_2000 5m (51 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T082418Z.json` · tag `CROSS_RUN_AH_KEEP_SLS3_2000` · seed KEEP ticks `20260926T080023Z_f1360884` (asia0-6 ema32 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr200 flat23 sls3/2000 maxbreak15 rc3 PF2.46/+187645.7 n232) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: AG runners cap1000/w14/hold16/tr190 under sls3_2000 · mild crosses · hold/flatten expand · soft PF pocket (tema/tminb) · trail/TP/mb/ema/maxbreak/rc mild. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_sls3_2000_baseline`): n232 · PF **2.589** · **+204369.6**.
- **Soft ≥2.0 pts lifts:** `cap1000_w14_hold16` PF **2.605** / **+207846.3** n233 — ΔPF **+0.016** · Δpts **+3476.7**; `cap1000_hold16` PF **2.614** / **+207622.7** n233 — ΔPF **+0.025** · Δpts **+3253.1**; `cap1000_tr190` PF **2.612** / **+207393.6** n233 — ΔPF **+0.023** · Δpts **+3024.0**; `cap1000_w14` PF **2.598** / **+206997.0** n233 — ΔPF **+0.009** · Δpts **+2627.4**; `cap1000` PF **2.607** / **+206773.4** n233 — ΔPF **+0.018** · Δpts **+2403.8**; `sls3_2100` PF **2.629** / **+206369.6** n230 — ΔPF **+0.040** · Δpts **+2000.0**; `w14_hold16` PF **2.593** / **+206350.5** n232 — ΔPF **+0.004** · Δpts **+1980.9**; `w14_sls4` PF **2.544** / **+206177.3** n239 — ΔPF **-0.045** · Δpts **+1807.7**; `w14_tr190` PF **2.591** / **+206141.4** n232 — ΔPF **+0.002** · Δpts **+1771.8**; `sls3_1900` PF **2.602** / **+206071.0** n233 — ΔPF **+0.013** · Δpts **+1701.4**.
- **PF ≥~2.5 with pts lift:** `cap1000_w14_hold16` PF 2.605/+207846.3 n233; `cap1000_hold16` PF 2.614/+207622.7 n233; `cap1000_tr190` PF 2.612/+207393.6 n233; `cap1000_w14` PF 2.598/+206997.0 n233; `cap1000` PF 2.607/+206773.4 n233; `sls3_2100` PF 2.629/+206369.6 n230; `w14_hold16` PF 2.593/+206350.5 n232; `w14_sls4` PF 2.544/+206177.3 n239.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`cap1100`, `tminb_100`, `tminb_180`, `tp5000`, `tp5200`, `tp4600`, `mb270`; dilute=`tema_220` PF2.416/+147909.5 dpts-56460.1; `tema220_tminb100` PF2.416/+147909.5 dpts-56460.1; `tema_180` PF2.439/+148909.5 dpts-55460.1; `tema180_tminb100` PF2.439/+148909.5 dpts-55460.1; `rc2` PF2.014/+149745.8 dpts-54623.8; `tema_300` PF2.477/+157281.0 dpts-47088.6; `w12` PF2.279/+170712.4 dpts-33657.2; `w15` PF2.343/+178165.6 dpts-26204.0; `ema34` PF2.439/+187948.1 dpts-16421.5; `rc4` PF2.474/+192215.4 dpts-12154.2; `ema30` PF2.517/+196735.6 dpts-7634.0; `mb280` PF2.519/+196983.4 dpts-7386.2; `arm4200` PF2.498/+197197.4 dpts-7172.2; `cap1300` PF2.534/+198839.9 dpts-5529.7; `mb_above250` PF2.516/+199599.5 dpts-4770.1; `sls2` PF2.577/+201274.9 dpts-3094.7; `sls3_2200_ctrl` PF2.592/+201681.8 dpts-2687.8; `arm3800` PF2.580/+201716.3 dpts-2653.3.
- **Conclusion:** `cap1000_w14_hold16` is the cleanest soft≥2.0 pts refine on NEW KEEP sls3/2000 (Δpts **+3476.7** · ΔPF **+0.016** on 5m; PF stays ≥2.5). Runners: `cap1000_hold16`, `cap1000_tr190`, `cap1000_w14`. Soft-PF pocket (tema/tminb) and rc2 cut pts hard — reject. Do **not** promote on 5m alone. KEEP unchanged (ticks sls3/2000 PF2.46/+187645.7 n232).
- **Next:** overnight **tick-confirm** `AH_tick cap1000_w14_hold16` (resume_max_break_pts=1000.0, max_wait_candles=14, max_hold_hours=16.0, else KEEP sls3/2000) workers=2. Optional runners cap1000_hold16 / cap1000_tr190 / cap1000_w14 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.



### 2026-09-26 ~12:12 Europe/Bucharest Asia TICK CONFIRM AH_tick cap1000_w14_hold16 on KEEP sls3/2000 (run 20260926T090107Z_a5a23919) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2000**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail200**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T08:47:02Z finished 2026-09-26T09:01:07Z UTC.
- **Result:** n233 · win42.9% · **+192058.6** · **PF 2.48** (avg +824.3 / win +3215.8 / loss -973.9). exits flatten41 / sl128 / trail61 / tp3. trail_armed 64 (27.5%). entries ema_touch97 / higher_close58 / timeout_market53 / lower_close25. skipped 196. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T090107Z_a5a23919.json`.
- **vs PRIOR KEEP** sls3/2000 rc3 maxbreak15 wait13 cap1200 hold14 ticks PF2.46/+187645.7 n232 (run 20260926T080023Z_f1360884): dPF **+0.02** · dpts **+4412.9** · dn **+1** -- meaningful pts lift with PF up (soft floor ~2.0, near prefer >=2.5); **PROMOTE**.
- **vs 5m screen** cap1000_w14_hold16 PF2.605/+207846.3 n233: tick matches direction (~+192058.6 PF2.48); dpts +4412.9 on ticks vs +3476.7 on 5m.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2000** · wick_on · trail **arm4000/tr200** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.48/+192058.6 n233. Pts goal still met (~192.1k); tighter resume cap + wait14 + hold16 stack lifts pts and PF vs prior KEEP.
- **Next:** Batch AI `CROSS_VOL_AI_KEEP_CAP1000_W14_H16` 5m on NEW KEEP (AH runners tr190/sls3_2100/cap1000_tr190 · flatten/hold expand · TP/trail mild · soft PF pocket · mb/ema/maxbreak mild). Tick-confirm only soft>=2.0 pts lifts or clear pts lift at PF>=~2.0 holding >=~157k. Still seek PF toward >=2.5 without giving back >=~157k pts. No reaktor / no push.



### 2026-09-26 ~12:50 Europe/Bucharest Asia Batch AI CROSS_VOL_AI_KEEP_CAP1000_W14_H16 5m (52 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T091630Z.json` · tag `CROSS_VOL_AI_KEEP_CAP1000_W14_H16` · seed KEEP ticks `20260926T090107Z_a5a23919` (asia0-6 ema32 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr200 flat23 sls3/2000 maxbreak15 rc3 cap1000 wait14 hold16 PF2.48/+192058.6 n233) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: AH runners tr190/sls3_2100 · flatten/hold expand · TP/trail mild · soft PF pocket · mb/ema/maxbreak mild. Error cells: `flat24` (hour must be in 0..23).
- **Baseline 5m KEEP** (`KEEP_cap1000_w14_h16_baseline`): n233 · PF **2.605** · **+207846.3**.
- **Soft ≥2.0 pts lifts:** `tr190_sls2100` PF **2.671** / **+211486.5** n230 — ΔPF **+0.066** · Δpts **+3640.2**; `sls3_2100` PF **2.666** / **+210846.3** n230 — ΔPF **+0.061** · Δpts **+3000.0**; `sls2100_hold18` PF **2.666** / **+210846.3** n230 — ΔPF **+0.061** · Δpts **+3000.0**; `tr180` PF **2.614** / **+209126.3** n233 — ΔPF **+0.009** · Δpts **+1280.0**; `mb260` PF **2.619** / **+208560.9** n233 — ΔPF **+0.014** · Δpts **+714.6**; `tr190` PF **2.610** / **+208486.5** n233 — ΔPF **+0.005** · Δpts **+640.2**; `tr190_hold18` PF **2.610** / **+208486.5** n233 — ΔPF **+0.005** · Δpts **+640.2**.
- **PF ≥~2.5 with pts lift:** `tr190_sls2100` PF 2.671/+211486.5 n230; `sls3_2100` PF 2.666/+210846.3 n230; `sls2100_hold18` PF 2.666/+210846.3 n230; `tr180` PF 2.614/+209126.3 n233; `mb260` PF 2.619/+208560.9 n233; `tr190` PF 2.610/+208486.5 n233; `tr190_hold18` PF 2.610/+208486.5 n233.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`sls3_1900`, `hold18`, `hold20`, `tp5000`, `tp4600`, `tp5200`, `mb_below250`, `tminb_150`, `nb_breakout`, `nb_outside`; dilute=`tema_220` PF2.321/+145521.5 dpts-62324.8; `tema220_tminb100` PF2.321/+145521.5 dpts-62324.8; `pullback_required` PF2.444/+153285.7 dpts-54560.6; `w12` PF2.304/+173974.3 dpts-33872.0; `rc2` PF2.275/+180727.1 dpts-27119.2; `w15` PF2.370/+181430.1 dpts-26416.2; `w15_hold18` PF2.370/+181430.1 dpts-26416.2; `ema34` PF2.456/+191490.1 dpts-16356.2; `rc4` PF2.474/+192834.4 dpts-15011.9; `ema30` PF2.468/+193076.4 dpts-14769.9; `arm4200` PF2.481/+196218.4 dpts-11627.9; `tp5000_arm4200` PF2.481/+196218.4 dpts-11627.9; `arm4200_tr190` PF2.485/+196788.5 dpts-11057.8; `arm3800` PF2.551/+199415.4 dpts-8430.9; `mb280` PF2.560/+202093.2 dpts-5753.1; `sls2` PF2.593/+204751.6 dpts-3094.7; `mb16` PF2.489/+204795.9 dpts-3050.4; `mb14` PF2.647/+205091.4 dpts-2754.9.
- **Conclusion:** `tr190_sls2100` is the cleanest soft≥2.0 pts refine on NEW KEEP cap1000+w14+hold16 (Δpts **+3640.2** · ΔPF **+0.066** on 5m; PF stays ≥2.5). Runners: `sls3_2100`, `sls2100_hold18`, `tr180`. Soft-PF pocket (tema/tminb) and pullback_required / w12/w15 cut pts — reject. Do **not** promote on 5m alone. KEEP unchanged (ticks cap1000 wait14 hold16 PF2.48/+192058.6 n233).
- **Next:** overnight **tick-confirm** `AI_tick tr190_sls2100` (trail_pts=190.0, skip_late_short_asia_pts=2100.0, else KEEP cap1000/w14/hold16) workers=2. Optional runners sls3_2100 / sls2100_hold18 / tr180 if champ rejects. Still seek PF toward ≥2.5 without giving back ≥~157k pts. No reaktor / no push.



### 2026-09-26 ~13:12 Europe/Bucharest Asia TICK CONFIRM AI_tick tr190_sls2100 on KEEP cap1000/w14/hold16 (run 20260926T100731Z_5b3b46d4) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail190**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T09:53:49Z finished 2026-09-26T10:07:31Z UTC.
- **Result:** n230 · win43.5% · **+195668.8** · **PF 2.55** (avg +850.7 / win +3221.9 / loss -973.3). exits flatten41 / sl125 / trail61 / tp3. trail_armed 64 (27.8%). entries ema_touch95 / higher_close58 / timeout_market53 / lower_close24. skipped 199 (no_break169 / late_short30). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T100731Z_5b3b46d4.json`.
- **vs PRIOR KEEP** cap1000 wait14 hold16 trail tr200 sls3/2000 ticks PF2.48/+192058.6 n233 (run 20260926T090107Z_a5a23919): ΔPF **+0.07** · Δpts **+3610.2** · Δn **-3** -- meaningful pts lift with PF up into prefer ≥2.5; **PROMOTE**.
- **vs 5m screen** tr190_sls2100 PF2.671/+211486.5 n230: tick matches direction (~+195668.8 PF2.55); dpts +3610.2 on ticks vs +3640.2 on 5m.
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230. Pts goal still met (~195.7k); tighter trail + looser late-short asia gate lifts both PF and pts. First KEEP at PF≥2.5 since the pts-push lineage.
- **Next:** Batch AJ `CROSS_VOL_AJ_KEEP_TR190_SLS2100` 5m on NEW KEEP (AI runners hold18/tr180/mb260 · hold/flatten expand · TP/trail mild · soft PF pocket · mb/ema/maxbreak/cap/wait mild). Tick-confirm only soft≥2.0 pts lifts or clear pts lift at PF≥~2.0 holding ≥~157k. Still seek more pts while holding PF≥~2.5. No reaktor / no push.



### 2026-09-26 ~13:50 Europe/Bucharest Asia Batch AJ CROSS_VOL_AJ_KEEP_TR190_SLS2100 5m (56 cells) — soft>=2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T101549Z.json` · tag `CROSS_VOL_AJ_KEEP_TR190_SLS2100` · seed KEEP ticks `20260926T100731Z_5b3b46d4` (asia0-6 ema32 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap1000 wait14 hold16 PF2.55/+195668.8 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: denser trail/mb/hold crosses under NEW KEEP tr190+sls2100 · hold/flatten expand · TP/trail arm mild · soft PF pocket · mb/ema/maxbreak/cap/wait/rc mild. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_tr190_sls2100_baseline`): n230 · PF **2.671** · **+211486.5**.
- **Soft >=2.0 pts lifts:** `tr160` PF **2.687** / **+213406.3** n230 — dPF **+0.016** · dpts **+1919.8**; `tr180_mb260` PF **2.692** / **+212840.9** n230 — dPF **+0.021** · dpts **+1354.4**; `tr170` PF **2.682** / **+212766.6** n230 — dPF **+0.011** · dpts **+1280.1**; `hold18_mb260` PF **2.687** / **+212201.1** n230 — dPF **+0.016** · dpts **+714.6**; `mb260` PF **2.687** / **+212201.1** n230 — dPF **+0.016** · dpts **+714.6**; `tr180` PF **2.676** / **+212126.3** n230 — dPF **+0.005** · dpts **+639.8**; `hold18_tr180` PF **2.676** / **+212126.3** n230 — dPF **+0.005** · dpts **+639.8**.
- **PF >=~2.5 with pts lift:** `tr160` PF 2.687/+213406.3 n230; `tr180_mb260` PF 2.692/+212840.9 n230; `tr170` PF 2.682/+212766.6 n230; `hold18_mb260` PF 2.687/+212201.1 n230; `mb260` PF 2.687/+212201.1 n230; `tr180` PF 2.676/+212126.3 n230; `hold18_tr180` PF 2.676/+212126.3 n230.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`hold18`, `hold20`, `tp4600`, `tp5000`, `tp5200`, `mb_below250`, `tminb_150`, `nb_breakout`, `nb_outside`; dilute=`tema_220` PF2.390/+149011.6 dpts-62474.9; `tema220_tminb100` PF2.390/+149011.6 dpts-62474.9; `pullback_required` PF2.520/+156775.8 dpts-54710.7; `w12` PF2.343/+176544.5 dpts-34942.0; `rc2` PF2.329/+184337.2 dpts-27149.3; `w15` PF2.429/+185010.2 dpts-26476.3; `w15_hold18` PF2.429/+185010.2 dpts-26476.3; `ema34` PF2.518/+195090.3 dpts-16396.2; `rc4` PF2.517/+195424.5 dpts-16062.0; `ema30` PF2.530/+196686.6 dpts-14799.9; `arm4200` PF2.542/+199788.5 dpts-11698.0; `tp5000_arm4200` PF2.542/+199788.5 dpts-11698.0; `arm4200_tr180` PF2.547/+200358.4 dpts-11128.1; `arm3800` PF2.618/+203075.6 dpts-8410.9; `mb280` PF2.626/+205723.4 dpts-5763.1; `sls3_1800` PF2.546/+206398.2 dpts-5088.3; `sls3_2200` PF2.634/+206788.7 dpts-4697.8; `tr180_sls2200` PF2.639/+207418.5 dpts-4068.0.
- **Conclusion:** `tr160` is the cleanest soft>=2.0 pts refine on NEW KEEP tr190+sls2100 (dpts **+1919.8** · dPF **+0.016** on 5m; PF stays >=2.5). Runners: `tr180_mb260`, `tr170`, `hold18_mb260`. Soft-PF pocket (tema/tminb) and pullback_required / w12/w15 / rc2 cut pts — reject. Edges thin (~+1–2k on 5m). Do **not** promote on 5m alone. KEEP unchanged (ticks tr190/sls2100 PF2.55/+195668.8 n230).
- **Next:** overnight **tick-confirm** `AJ_tick tr160` (trail_pts=160.0, else KEEP tr190/sls2100) workers=2. Optional runners tr180_mb260 / tr170 / hold18_mb260 if champ rejects. Still seek more pts while holding PF>=~2.5. No reaktor / no push.



### 2026-09-26 ~14:15 Europe/Bucharest Asia TICK CONFIRM AJ_tick tr160 on KEEP tr190/sls2100 (run 20260926T110721Z_2d536d82) -- **REJECT**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail160**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T10:52:26Z finished 2026-09-26T11:07:21Z UTC.
- **Result:** n230 · win43.5% · **+194749.0** · **PF 2.54** (avg 846.7 / win 3212.7 / loss -973.3). exits {'flatten': 41, 'sl': 125, 'trail': 62, 'tp': 2}. trail_armed 64 (27.8). entries {'higher_close': 58, 'ema_touch': 95, 'timeout_market': 53, 'lower_close': 24}. skipped 199 ({'no_break': 169, 'late_short': 30}). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T110721Z_2d536d82.json`.
- **vs KEEP** tr190/sls2100 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): ΔPF **-0.01** · Δpts **-919.8** · Δn **+0** -- pts down, PF flat/slightly down; **REJECT**.
- **vs 5m screen** tr160 PF2.687/+213406.3 n230: 5m edge (~+1919.8) did not hold on ticks (tick Δpts -919.8).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230. Tighter trail160 loses ~920 pts vs tr190 on ticks.
- **Next:** overnight **tick-confirm** `AJ_runner tr180_mb260` (trail_pts=180.0, min_break_pts_above/below=260.0, else KEEP tr190/sls2100) workers=2. Optional runners tr170 / hold18_mb260 if this rejects. Still seek more pts while holding PF>=~2.5. No reaktor / no push.



### 2026-09-26 ~14:43 Europe/Bucharest Asia TICK misfire check run 20260926T113626Z_34302fb6 (intended AJ_runner tr180_mb260) -- **NO-OP / MISFIRE**
- **What landed:** overnight finished with trail_pts=190.0 mb=275.0/275.0 near_box=0/0.0 (NOT tr180/mb260). Metrics identical to KEEP: n230 · win43.5% · **+195668.8** · **PF 2.55**. started see API finished 2026-09-26T11:36:26.298666+00:00. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T113626Z_34302fb6.json`.
- **vs KEEP** tr190/sls2100 near_box N6 D1000 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): ΔPF **+0.00** · Δpts **+0.0** · Δn **+0** -- KEEP clone (near_box off inert); **not a valid AJ_runner result**.
- **Cause:** prior kick at ~14:15 claimed tr180_mb260 started 2026-09-26T11:18:28Z, but this job started ~11:22Z with KEEP trail/mb. Treat as misfire.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230.
- **Next:** re-kick overnight **tick-confirm** `AJ_runner tr180_mb260` from KEEP seed (trail_pts=180.0, min_break_pts_above/below=260.0, keep near_box N6 D1000) workers=2; verify echo params after POST. Optional runners tr170 / hold18_mb260 if this rejects. Still seek more pts while holding PF>=~2.5. No reaktor / no push.



### 2026-09-26 ~15:14 Europe/Bucharest Asia TICK CONFIRM AJ_runner tr180_mb260 on KEEP tr190/sls2100 (run 20260926T120016Z_c8002a0d) -- **REJECT**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb260**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail180**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T11:46:21Z finished 2026-09-26T12:00:16.601149+00:00.
- **Result:** n230 · win43.5% · **+195229.7** · **PF 2.55** (avg 848.8 / win 3210.4 / loss -967.8). exits {'flatten': 42, 'sl': 124, 'trail': 62, 'tp': 2}. trail_armed 64 (27.8). entries {'higher_close': 56, 'ema_touch': 95, 'timeout_market': 56, 'lower_close': 23}. skipped 199 ({'no_break': 169, 'late_short': 30}). saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T120016Z_c8002a0d.json`.
- **vs KEEP** tr190/sls2100 mb275 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): ΔPF **+0.00** · Δpts **-439.1** · Δn **+0** -- pts down, PF flat; **REJECT**.
- **vs 5m screen** tr180_mb260 PF2.692/+212840.9 n230: 5m edge (~+1354) did not hold on ticks (tick Δpts -439.1).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230. AJ trail/mb pocket thin on ticks (tr160 and tr180_mb260 both lose pts).
- **Next:** overnight **tick-confirm** `AJ_runner tr170` (trail_pts=170.0, else KEEP tr190/sls2100 mb275) workers=2. Optional runner hold18_mb260 if this rejects; then Batch AK hold/flatten + mild volume if AJ runners stall. Still seek more pts while holding PF>=~2.5. No reaktor / no push.




### 2026-09-26 ~16:13 Europe/Bucharest Asia overnight idle check — FOREIGN finished (not AJ_runner tr170) -- **IGNORE**
- **What landed:** overnight idle with run 20260926T125827Z_7fe8e2d1 finished 2026-09-26T12:58:27Z. Params are **foreign old lineage**: asia **1-6**, ema30, wait13, mb250, SL1000/TP2200, trail_arm_mode=**off**, near_box_bars=**0**, pullback **required**, max_hold14, workers=3, date_to=2026-10-01. Result n145 · win54.5% · **+89775.1** · **PF 2.38**. saved 
esults/overnight_XAUUSD_2025-01-01_2026-10-01_20260926T125827Z_7fe8e2d1.json.
- **vs KEEP** tr190/sls2100 mb275 near_box N6 D1000 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): wrong seed (not AJ_runner tr170). Prior AJ_runner tr170 kick (started ~12:17Z) was **superseded** by this foreign job (also asia-box finished ~12:59Z on candles_5m — separate UI). **Do not score as AJ candidate**.
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230.
- **Next:** re-kick overnight **tick-confirm** AJ_runner tr170 from KEEP seed (trail_pts=170.0, else KEEP) workers=2; verify PARAM_ECHO after POST. If reject → hold18_mb260; if AJ runners stall → Batch AK. Still seek more pts while holding PF>=~2.5. No reaktor / no push.



### 2026-09-26 ~16:45 Europe/Bucharest Asia TICK CONFIRM AJ_runner tr170 on KEEP tr190/sls2100 (run 20260926T133530Z_bb980382) -- **REJECT**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail170**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T13:15:51.484443+00:00 finished 2026-09-26T13:35:30.153179+00:00.
- **Result:** n230 · win43.5% · **+194267.5** · **PF 2.54** (avg 844.6 / win 3207.9 / loss -973.3). exits {'flatten': 41, 'sl': 125, 'trail': 62, 'tp': 2}. trail_armed 64 (27.8). entries {'higher_close': 58, 'ema_touch': 95, 'timeout_market': 53, 'lower_close': 24}. skipped 199 ({'no_break': 169, 'late_short': 30}). streaks max_loss=8. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T133530Z_bb980382.json`.
- **vs KEEP** tr190/sls2100 mb275 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): ΔPF **-0.01** · Δpts **-1401.3** · Δn **+0** -- pts down, PF flat/slightly down; **REJECT**.
- **vs 5m screen** tr170 PF2.682/+212766.6 n230: 5m edge (~+1280) did not hold on ticks (tick Δpts -1401.3).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230. AJ trail pocket thin on ticks (tr160/tr180_mb260/tr170 all lose pts vs KEEP).
- **Next:** overnight **tick-confirm** `AJ_runner hold18_mb260` (max_hold_hours=18.0, min_break_pts_above/below=260.0, else KEEP tr190/sls2100 trail190) workers=2. If reject → Batch AK hold/flatten + mild volume (AJ runners stalled). Still seek more pts while holding PF>=~2.5. No reaktor / no push.



### 2026-09-26 ~17:13 Europe/Bucharest Asia TICK CONFIRM AJ_runner hold18_mb260 on KEEP tr190/sls2100 (run 20260926T140011Z_43b9670b) -- **REJECT**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema32**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb260**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail190**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold18**. workers=2. data_source=ticks. started 2026-09-26T13:45:57.085954+00:00 finished 2026-09-26T14:00:11.936103+00:00.
- **Result:** n230 · win43.5% · **+196380.3** · **PF 2.56** (avg 853.8 / win 3221.9 / loss -967.8). exits {'flatten': 42, 'sl': 124, 'trail': 61, 'tp': 3}. trail_armed 64 (27.8). entries {'higher_close': 56, 'ema_touch': 95, 'timeout_market': 56, 'lower_close': 23}. skipped 199 ({'no_break': 169, 'late_short': 30}). streaks max_loss=8. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T140011Z_43b9670b.json`.
- **vs KEEP** tr190/sls2100 mb275 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): ΔPF **+0.01** · Δpts **+711.5** · Δn **+0** -- thin pts lift (~+711), max_loss=8 at hard-ish edge; **REJECT** (not meaningful promote).
- **vs 5m screen** hold18_mb260 PF2.692/+212840.9-ish lineage: 5m runner edge did not become a clear tick promote (tick Δpts +711.5).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema32** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.55/+195668.8 n230. AJ runners stalled (tr160/tr180_mb260/tr170/hold18_mb260).
- **Next:** Batch AK `HOLD_VOL_AK_KEEP_TR190_SLS2100` 5m (hold/flatten expand + mild volume; skip AJ-failed trail pocket). Tick-confirm soft>=2.5 pts champs (or clear pts lift at PF>=~2.0 holding >=~157k). Prefer max_loss streak <=7-8. No reaktor / no push.



### 2026-09-26 ~17:45 Europe/Bucharest Asia Batch AK HOLD_VOL_AK_KEEP_TR190_SLS2100 5m (51 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T141720Z.json` · tag `HOLD_VOL_AK_KEEP_TR190_SLS2100` · seed KEEP ticks `20260926T100731Z_5b3b46d4` (asia0-6 ema32 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap1000 wait14 hold16 PF2.55/+195668.8 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: hold/flatten expand · mild volume · mild trail/sls/cap · ema31/33 · soft PF pocket. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_tr190_sls2100_baseline`): n230 · PF **2.671** · **+211486.5**.
- **Soft ≥2.0 pts lifts:** `ema31` PF **2.755** / **+218578.6** n229 — ΔPF **+0.084** · Δpts **+7092.1**; `ema33` PF **2.700** / **+213430.9** n229 — ΔPF **+0.029** · Δpts **+1944.4**; `hold17_mb260` PF **2.687** / **+212201.1** n230 — ΔPF **+0.016** · Δpts **+714.6**; `hold20_mb260` PF **2.687** / **+212201.1** n230 — ΔPF **+0.016** · Δpts **+714.6**; `tr185` PF **2.674** / **+211806.3** n230 — ΔPF **+0.003** · Δpts **+319.8**.
- **PF ≥~2.5 with pts lift:** `ema31` PF 2.755/+218578.6 n229; `ema33` PF 2.700/+213430.9 n229; `hold17_mb260` PF 2.687/+212201.1 n230; `hold20_mb260` PF 2.687/+212201.1 n230; `tr185` PF 2.674/+211806.3 n230.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`hold17`, `hold22`, `hold19`, `hold24`, `hold18_flat23`, `mb265`, `mb270`, `asia_range280`, `asia_range320`, `hold18_mb265`, `sls2150`, `cap950`, `tminb_120`; dilute=`tema_200` PF2.390/+149011.6 dpts-62474.9; `pullback_required` PF2.520/+156775.8 dpts-54710.7; `w11` PF2.297/+173202.4 dpts-38284.1; `w16` PF2.441/+189276.5 dpts-22210.0; `w16_hold18` PF2.441/+189276.5 dpts-22210.0; `mb240` PF2.521/+200191.7 dpts-11294.8; `mb290` PF2.583/+200353.1 dpts-11133.4; `flat18` PF2.666/+202861.6 dpts-8624.9; `maxbreak18` PF2.386/+203029.2 dpts-8457.3; `flat19` PF2.669/+206780.1 dpts-4706.4; `flat19_hold16` PF2.669/+206780.1 dpts-4706.4; `flat19_hold18` PF2.669/+206780.1 dpts-4706.4; `sls2250` PF2.634/+206788.7 dpts-4697.8; `flat20` PF2.668/+207624.4 dpts-3862.1; `flat20_hold16` PF2.668/+207624.4 dpts-3862.1; `flat20_hold18` PF2.668/+207624.4 dpts-3862.1; `maxbreak16` PF2.549/+208446.1 dpts-3040.4; `maxbreak16_hold18` PF2.549/+208446.1 dpts-3040.4.
- **Conclusion:** `ema31` is the cleanest soft≥2.0 pts refine on KEEP tr190/sls2100 (Δpts **+7092.1** · ΔPF **+0.084** on 5m; PF stays ≥2.5). Runners: `ema33`, `hold17_mb260`, `hold20_mb260`. Soft-PF pocket (tema_200) and pullback_required / w11/w16 cut pts — reject. Hold/flatten solo mostly inert; hold*_mb260 thin (~+715) — deprioritize vs ema after AJ hold18_mb260 thin tick reject. Do **not** promote on 5m alone. KEEP unchanged (ticks tr190/sls2100 PF2.55/+195668.8 n230).
- **Next:** overnight **tick-confirm** `AK_tick ema31` (ema_period=31, else KEEP tr190/sls2100) workers=2. Optional runners ema33 / hold17_mb260 / hold20_mb260 if champ rejects. Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.



### 2026-09-26 ~18:21 Europe/Bucharest Asia TICK CONFIRM AK_tick ema31 on KEEP tr190/sls2100 (run 20260926T150205Z_cf1619ba) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema31**, **wait14**, **rc3**, **cap1000**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail190**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T14:48:00.755260+00:00 finished 2026-09-26T15:02:05.574386+00:00.
- **Result:** n230 · win43.9% · **+199872.5** · **PF 2.59** (avg 869.0 / win 3221.7 / loss -973.1). exits {'flatten': 41, 'sl': 124, 'trail': 63, 'tp': 2}. trail_armed 65 (28.3). entries {'higher_close': 58, 'ema_touch': 97, 'timeout_market': 51, 'lower_close': 24}. skipped 199 ({'no_break': 169, 'late_short': 30}). streaks max_win=6 max_loss=8. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T150205Z_cf1619ba.json`.
- **vs KEEP** tr190/sls2100 ema32 ticks PF2.55/+195668.8 n230 (run 20260926T100731Z_5b3b46d4): ΔPF **+0.04** · Δpts **+4203.7** · Δn **+0** -- meaningful pts lift (~+4204) at PF≥2.5; max_loss=8 within ≤7–8 hard-ish filter; **NEW KEEP**.
- **vs 5m screen** ema31 PF2.755/+218578.6 n229: 5m edge (~+7092) partially held on ticks (tick Δpts +4203.7; PF 2.59 vs 5m 2.755).
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema31** · **max_break=15** · **max_hold16** · **rc3** · **cap1000** · **wait14** · ticks PF2.59/+199872.5 n230.
- **Next:** Batch AL `HOLD_VOL_AL_KEEP_EMA31` 5m (denser ema×trail/hold crosses under NEW KEEP ema31; skip AJ-failed deep trail cuts). Tick-confirm soft≥2.5 pts champs (or clear pts lift at PF≥~2.0 holding ≥~157k). Prefer max_loss streak ≤7–8. No reaktor / no push.



### 2026-09-26 ~18:23 Europe/Bucharest Asia Batch AL HOLD_VOL_AL_KEEP_EMA31 5m (49 cells) — thin edges; no strong tick champ
- **Grid:** `results/overnight_5m_grid_20260926T152223Z.json` · tag `HOLD_VOL_AL_KEEP_EMA31` · seed KEEP ticks `20260926T150205Z_cf1619ba` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap1000 wait14 hold16 PF2.59/+199872.5 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: denser ema×trail/hold · mild mb/wait · soft PF pocket. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_ema31_baseline`): n229 · PF **2.755** · **+218578.6**.
- **Soft ≥2.0 pts lifts:** `ema31_mb260` PF **2.771** / **+219293.2** n229 — ΔPF **+0.016** · Δpts **+714.6**; `ema31_hold17_mb260` PF **2.771** / **+219293.2** n229 — ΔPF **+0.016** · Δpts **+714.6**; `ema31_tr185` PF **2.758** / **+218903.4** n229 — ΔPF **+0.003** · Δpts **+324.8**; `ema31_hold17_tr185` PF **2.758** / **+218903.4** n229 — ΔPF **+0.003** · Δpts **+324.8**.
- **PF ≥~2.5 with pts lift:** `ema31_mb260` PF 2.771/+219293.2 n229; `ema31_hold17_mb260` PF 2.771/+219293.2 n229; `ema31_tr185` PF 2.758/+218903.4 n229; `ema31_hold17_tr185` PF 2.758/+218903.4 n229.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`ema31_hold17`, `ema31_hold18`, `ema31_hold20`, `ema31_mb265`, `ema31_sls2150`, `tminb_100`; dilute=`tema_220` PF2.461/+155103.7 dpts-63474.9; `tema_180` PF2.484/+156103.7 dpts-62474.9; `pullback_required` PF2.594/+162867.9 dpts-55710.7; `ema31_w15` PF2.507/+192102.3 dpts-26476.3; `ema34` PF2.518/+195090.3 dpts-23488.3; `ema30_tr195` PF2.528/+196381.7 dpts-22196.9; `ema30` PF2.530/+196686.6 dpts-21892.0; `ema30_tr190` PF2.530/+196686.6 dpts-21892.0; `ema30_hold16` PF2.530/+196686.6 dpts-21892.0; `ema30_hold18` PF2.530/+196686.6 dpts-21892.0; `ema30_hold17_tr190` PF2.530/+196686.6 dpts-21892.0; `ema30_tr185` PF2.533/+196991.4 dpts-21587.2; `ema30_mb260` PF2.544/+197401.2 dpts-21177.4; `ema29_tr195` PF2.551/+199356.7 dpts-19221.9; `ema29` PF2.553/+199666.6 dpts-18912.0; `ema29_tr190` PF2.553/+199666.6 dpts-18912.0; `ema31_arm4100` PF2.619/+206486.5 dpts-12092.1; `ema32_tr195` PF2.669/+211166.6 dpts-7412.0.
- **Conclusion:** Soft lifts are **thin** — champ `ema31_mb260` Δpts **+714.6** on 5m (same ~+715 mb260 pocket as AJ hold18_mb260 tick reject). `ema31_tr185` only +324.8. Hold solo / mb265 / sls2150 inert. Soft-PF pocket and ema30/32/33/34 cut pts vs NEW KEEP ema31. **Skip tick-confirm** of thin mb260/tr185 (AJ already rejected ~+711 mb260 lineage). KEEP unchanged (ticks ema31 PF2.59/+199872.5 n230).
- **Next:** Batch AM `TP_ARM_AM_KEEP_EMA31` 5m (TP/arm mild + resume/wait/rc under NEW KEEP ema31). Tick-confirm only clear soft≥2.5 pts lifts (not ~+0.7k thin). Prefer max_loss streak ≤7–8. No reaktor / no push.



### 2026-09-26 ~18:26 Europe/Bucharest Asia Batch AM TP_ARM_AM_KEEP_EMA31 5m (43 cells) — soft≥2.0 pts champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T152420Z.json` · tag `TP_ARM_AM_KEEP_EMA31` · seed KEEP ticks `20260926T150205Z_cf1619ba` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap1000 wait14 hold16 PF2.59/+199872.5 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: TP/arm mild · resume/wait/rc · mild SL/sls/be · soft PF pocket. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_ema31_baseline`): n229 · PF **2.755** · **+218578.6**.
- **Soft ≥2.0 pts lifts:** `cap800` PF **2.863** / **+228281.9** n229 — ΔPF **+0.108** · Δpts **+9703.3**; `tp5200_tr185` PF **2.758** / **+218903.4** n229 — ΔPF **+0.003** · Δpts **+324.8**.
- **PF ≥~2.5 with pts lift:** `cap800` PF 2.863/+228281.9 n229; `tp5200_tr185` PF 2.758/+218903.4 n229.
- **Under-floor PF<2.0:** `be200` PF0.601/+-9170.7; `be400` PF1.014/+634.8.
- **Reject / dilute / inert:** inert=`tp4400`, `tp4600`, `tp5000`, `tp5200`, `tp5400`, `tp5600`, `tminb_80`; dilute=`be200` PF0.601/+-9170.7 dpts-227749.3; `be400` PF1.014/+634.8 dpts-217943.8; `tema_150` PF2.484/+156103.7 dpts-62474.9; `tminpb_100` PF2.545/+156263.7 dpts-62314.9; `rc4_w15` PF2.363/+177744.0 dpts-40834.6; `w12` PF2.416/+183335.8 dpts-35242.8; `tp5400_arm4600` PF2.435/+191627.2 dpts-26951.4; `w15` PF2.507/+192102.3 dpts-26476.3; `tp5000_w15` PF2.507/+192102.3 dpts-26476.3; `rc5` PF2.511/+194867.9 dpts-23710.7; `w16` PF2.518/+196368.6 dpts-22210.0; `rc2` PF2.455/+197498.5 dpts-21080.1; `arm3600` PF2.613/+199315.6 dpts-19263.0; `arm4200` PF2.560/+200474.2 dpts-18104.4; `tp5000_arm4200` PF2.560/+200474.2 dpts-18104.4; `tp5200_arm4200_tr185` PF2.562/+200758.9 dpts-17819.7; `rc4` PF2.596/+202399.6 dpts-16179.0; `cap1100_rc4` PF2.596/+202399.6 dpts-16179.0.
- **Conclusion:** `cap800` is a **clear** soft≥2.5 pts refine on NEW KEEP ema31 (Δpts **+9703.3** · ΔPF **+0.108** on 5m). TP-only cells inert (trail exits dominate). `tp5200_tr185` thin +324.8. be200/be400 collapse PF. Soft-PF pocket cuts pts. Do **not** promote on 5m alone. KEEP unchanged (ticks ema31 PF2.59/+199872.5 n230).
- **Next:** overnight **tick-confirm** `AM_tick cap800` (resume_max_break_pts=800.0, else KEEP ema31 tr190/sls2100) workers=2. Optional runners tp5200_tr185 if champ rejects. Prefer max_loss streak ≤7–8. No reaktor / no push.



### 2026-09-26 ~18:46 Europe/Bucharest Asia TICK CONFIRM AM_tick cap800 on KEEP ema31 (run 20260926T153950Z_d5b5cf17) -- **NEW KEEP**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema31**, **wait14**, **rc3**, **cap800**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail190**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T15:26:05.121559+00:00 finished 2026-09-26T15:39:50.214747+00:00.
- **Result:** n230 · win44.8% · **+208866.7** · **PF 2.69** (avg 908.1 / win 3227.1 / loss -972.6). exits {'flatten': 42, 'sl': 122, 'trail': 64, 'tp': 2}. trail_armed 66 (28.7). entries {'higher_close': 51, 'ema_touch': 101, 'timeout_market': 56, 'lower_close': 22}. skipped 199 ({'no_break': 169, 'late_short': 30}). streaks max_win=6 max_loss=8. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T153950Z_d5b5cf17.json`.
- **vs KEEP** ema31 cap1000 ticks PF2.59/+199872.5 n230 (run 20260926T150205Z_cf1619ba): ΔPF **+0.10** · Δpts **+8994.2** · Δn **+0** -- meaningful pts lift (~+8994) at PF≥2.5; max_loss=8 within ≤7–8 hard-ish filter; **NEW KEEP**.
- **vs 5m screen** cap800 PF2.863/+228281.9 n229: 5m edge (~+9703) mostly held on ticks (tick Δpts +8994.2; PF 2.69 vs 5m 2.863).
- **Conclusion:** NEW KEEP = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema31** · **max_break=15** · **max_hold16** · **rc3** · **cap800** · **wait14** · ticks PF2.69/+208866.7 n230.
- **Next:** Batch AN `HOLD_VOL_AN_KEEP_CAP800` 5m (cap neighborhood + trail/hold/mb/wait/arm/sls under NEW KEEP cap800). Tick-confirm soft≥2.5 pts champs (or clear pts lift at PF≥~2.0 holding ≥~157k). Prefer max_loss streak ≤7–8. No reaktor / no push.



### 2026-09-26 ~19:17 Europe/Bucharest Asia Batch AN HOLD_VOL_AN_KEEP_CAP800 5m (56 cells) — thin edges; no strong tick champ
- **Grid:** `results/overnight_5m_grid_20260926T155125Z.json` · tag `HOLD_VOL_AN_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: cap neighborhood · trail/hold · mb/wait/maxbreak · arm/sls/flat · near-box N/D · soft PF pocket. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `mb260` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `hold17_mb260` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `tr180` PF **2.868** / **+228941.7** n229 — ΔPF **+0.005** · Δpts **+659.8**; `tr185` PF **2.866** / **+228611.7** n229 — ΔPF **+0.003** · Δpts **+329.8**; `tr185_hold17` PF **2.866** / **+228611.7** n229 — ΔPF **+0.003** · Δpts **+329.8**; `tr185_hold18` PF **2.866** / **+228611.7** n229 — ΔPF **+0.003** · Δpts **+329.8**.
- **PF ≥~2.5 with pts lift:** `mb260` PF 2.880/+228996.5 n229 dpts+714.6; `hold17_mb260` PF 2.880/+228996.5 n229 dpts+714.6; `tr180` PF 2.868/+228941.7 n229 dpts+659.8; `tr185` PF 2.866/+228611.7 n229 dpts+329.8; `tr185_hold17` PF 2.866/+228611.7 n229 dpts+329.8; `tr185_hold18` PF 2.866/+228611.7 n229 dpts+329.8.
- **Thin (<+2000 pts):** `mb260` dpts+714.6, `hold17_mb260` dpts+714.6, `tr180` dpts+659.8, `tr185` dpts+329.8, `tr185_hold17` dpts+329.8, `tr185_hold18` dpts+329.8.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`hold18`, `hold17`, `hold20`, `mb265`, `sls2150`, `nb_N5`, `nb_N7`, `nb_D800`, `nb_D1200`, `nb_N5_D800`, `tminb_100`; dilute=`tema_180` PF2.620/+163896.5 dpts-64385.4; `pullback_required` PF2.722/+170779.2 dpts-57502.7; `w12` PF2.513/+192869.0 dpts-35412.9; `w15` PF2.610/+201906.9 dpts-26375.0; `arm4200` PF2.661/+210177.5 dpts-18104.4; `mb300` PF2.739/+213027.9 dpts-15254.0; `arm4100` PF2.722/+216189.8 dpts-12092.1; `cap850` PF2.745/+217342.8 dpts-10939.1; `cap900` PF2.745/+217342.8 dpts-10939.1; `cap850_hold17` PF2.745/+217342.8 dpts-10939.1; `cap850_tr185` PF2.748/+217662.6 dpts-10619.3; `arm3800` PF2.796/+218298.4 dpts-9983.5; `cap950` PF2.755/+218578.6 dpts-9703.3; `cap1000` PF2.755/+218578.6 dpts-9703.3; `arm3900` PF2.809/+221679.8 dpts-6602.1; `mb280` PF2.816/+222529.1 dpts-5752.8; `sls2200` PF2.825/+223584.1 dpts-4697.8; `cap700` PF2.812/+223842.0 dpts-4439.9.
- **Conclusion:** Soft lifts are **thin** (best `mb260` Δpts **+714.6** on 5m) — same ~+0.7k mb260/tr180 pocket AJ/AL already rejected on ticks. Clear lifts (Δpts≥2000 at PF≥2.5): none. Cap neighborhood / hold / arm / near-box N/D / soft-PF mostly inert or dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AO `GATE_SIDE_AO_KEEP_CAP800` 5m (near-box trend gates breakout/outside × N/D · side/seasonal/week2 · mild SL/wick/asia_range/teff/timeout under NEW KEEP cap800). Tick-confirm only clear soft≥2.5 pts lifts (not ~+0.7k thin). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.




### 2026-09-26 ~19:43 Europe/Bucharest Asia Batch AO GATE_SIDE_AO_KEEP_CAP800 5m (47 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T162238Z.json` · tag `GATE_SIDE_AO_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: near-box trend gates breakout/outside × N/D · side/seasonal/week2 · mild SL/wick/asia_range/teff/timeout. Error cells: none (first stub grid `overnight_5m_grid_20260926T162158Z.json` had errors only — superseded).
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 / ≥2.5 pts lifts (Δpts>0):** **none**. Clear lifts (Δpts≥2000 at PF≥2.5): **none**.
- **Inert (=baseline, 31 cells):** all near-box trend gates (breakout/outside × N/D) · wick_off · asia_range250/350 · teff_* · tflat_* · tminb_* · week2_tag · seasonal_tag · season_week2_join — confirms near-box trend still **dormant** under pullback preferred + trend=off seed (gates do not change 5m outcome vs baseline).
- **Dilute / reject:** `side_short` PF **4.129** / **+133466.6** n89 (Δpts **−94815.3**) — high PF thin book, cut total pts; `side_long` PF **2.187** / **+94815.3** n140 (Δpts **−133466.6**, under-floor); `seasonal_filter` PF2.938/+206452.8 (Δpts−21829); `week2_filter` PF2.604/+165939.5 (Δpts−62342); `season_week2_filter` PF2.734/+167251.8 (Δpts−61030); SL scale `sl900`…`sl1400` and `sl1100_tp5200`/`sl1200_tp5400` all cut pts (best still −5838); soft timeout `tema_*` / `tminpb_80` cut ~62–65k pts.
- **Under-floor PF<2.0:** none (side_long PF2.187 is soft-floor-ish but already pts-rejected).
- **Conclusion:** Batch AO finds **no** soft≥2.5 pts refine on NEW KEEP cap800. Near-box trend gates remain dormant; side/seasonal/week2 and SL/timeout probes only dilute total pts. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AP `ENTRY_HOLD_AP_KEEP_CAP800` 5m (entry/resume/wait/rc/ema/sls-wait + denser flatten×hold under KEEP cap800 — AN/AO stall on vol/gates). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k), max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-26 ~20:20 Europe/Bucharest Asia Batch AP ENTRY_HOLD_AP_KEEP_CAP800 5m (64 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T164729Z.json` · tag `ENTRY_HOLD_AP_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: entry/resume/wait/rc/ema/sls-wait + denser flatten×hold + mild maxbreak + soft PF/news. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** **none**.
- **PF ≥~2.5 with pts lift:** **none**.
- **Thin (<+2000 pts):** none.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`rco_on`, `hold19`, `hold22`, `flat23_hold17`, `flat23_hold18`, `flat23_hold20`, `tminb_100`; dilute (least-cut first)=`slsw4` PF2.803/+228188.1 dpts-93.8; `flat23_hold14` PF2.856/+227480.7 dpts-801.2; `w13` PF2.854/+227370.7 dpts-911.2; `w13_hold17` PF2.854/+227370.7 dpts-911.2; `flat22` PF2.870/+226886.1 dpts-1395.8; `flat22_hold17` PF2.870/+226886.1 dpts-1395.8; `flat22_hold18` PF2.870/+226886.1 dpts-1395.8; `flat22_hold20` PF2.870/+226886.1 dpts-1395.8; `slsw5` PF2.750/+226628.9 dpts-1653.0; `flat22_hold14` PF2.863/+226008.0 dpts-2273.9; `sls1900` PF2.795/+225281.9 dpts-3000.0; `flat21` PF2.866/+225273.2 dpts-3008.7; `flat21_hold14` PF2.866/+225273.2 dpts-3008.7; `flat21_hold17` PF2.866/+225273.2 dpts-3008.7; `flat21_hold18` PF2.866/+225273.2 dpts-3008.7; `flat21_hold20` PF2.866/+225273.2 dpts-3008.7; `mb16_hold17` PF2.725/+225174.7 dpts-3107.2; `maxbreak18` PF2.591/+225132.7 dpts-3149.2.
- **Conclusion:** Batch AP finds **no** soft≥2.5 pts refine on NEW KEEP cap800. Nearest was `slsw4` Δpts **-93.8** PF2.803 (still under baseline). Entry/resume/wait/rc/ema/sls-wait and denser flatten×hold are inert or dilute (least-cut `slsw4` Δpts −93.8). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AQ `ASIA_TRAIL_AQ_KEEP_CAP800` 5m (asia window 0–5/0–7/1–6 + asia_range + pullback/otp + denser trail×arm×TP + mild SL:TP 1:1.5 under KEEP cap800 — AN/AO/AP stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.



### 2026-09-26 ~20:47 Europe/Bucharest Asia Batch AQ ASIA_TRAIL_AQ_KEEP_CAP800 5m (54 cells) - soft trail champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T172529Z.json` — tag `ASIA_TRAIL_AQ_KEEP_CAP800` — seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) — candles_5m — workers=2 — window 2025-01→2026-09. Axes: asia window/range · pullback/otp · trail×arm×TP · mild SL:TP 1:1.5 · soft PF pocket. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 — PF **2.863** — **+228281.9**.
- **Soft >=2.0 pts lifts:** `tr160` PF **2.879** / **+230261.7** n229 (dPF **+0.016** dpts **+1979.8**); `tr170` PF **2.874** / **+229602.0** n229 (dPF **+0.011** dpts **+1320.1**); `tr175` PF **2.871** / **+229271.7** n229 (dPF **+0.008** dpts **+989.8**); `tp4600_tr180` PF **2.868** / **+228941.7** n229 (dPF **+0.005** dpts **+659.8**).
- **PF >=~2.5 with pts lift:** `tr160` PF 2.879/+230261.7 n229 dpts+1979.8; `tr170` PF 2.874/+229602.0 n229 dpts+1320.1; `tr175` PF 2.871/+229271.7 n229 dpts+989.8; `tp4600_tr180` PF 2.868/+228941.7 n229 dpts+659.8.
- **Clear dpts>=~2k:** `tr160` dpts+1979.8 (at ~2k bar).
- **Under-floor PF<2.0:** `pullback_off` PF1.369/+65728.5; `pullback_off_otp_off` PF1.369/+65728.5; `asia0_5_w13` PF1.753/+107748.3; `asia1_5` PF1.756/+107238.0; `asia0_5` PF1.857/+119012.9; `asia0_5_mb260` PF1.895/+122705.4; `sl1500_tp2250` PF1.898/+129874.6.
- **Reject / dilute / inert:** inert=`asia_range250`, `asia_range280`, `asia_range320`, `asia_range350`, `asia_range400`, `otp_off`, `tp4400`, `tp4600`, `tp5000`, `tp5200`, `tp5400`; dilute=`pullback_off` PF1.369/+65728.5 dpts-162553.4; `pullback_off_otp_off` PF1.369/+65728.5 dpts-162553.4; `sl1000_tp1500` PF2.032/+98828.4 dpts-129453.5; `asia1_5` PF1.756/+107238.0 dpts-121043.9; `asia0_5_w13` PF1.753/+107748.3 dpts-120533.6; `sl1200_tp1800` PF2.030/+118657.1 dpts-109624.8; `asia0_5` PF1.857/+119012.9 dpts-109269.0; `asia0_5_mb260` PF1.895/+122705.4 dpts-105576.5; `sl1500_tp2250` PF1.898/+129874.6 dpts-98407.3; `sl1400_tp2100` PF2.036/+137218.3 dpts-91063.6; `sl1200_tp2400` PF2.189/+149917.8 dpts-78364.1; `asia1_7` PF2.128/+158251.6 dpts-70030.3.
- **Conclusion:** `tr160` is a **soft>=2.5 pts** refine on KEEP cap800 (dpts **+1979.8** ~2k bar, dPF **+0.016** on 5m). Same trail-cut pocket as AJ tr170 tick-REJECT, but tighter trail untried on ticks under ema31/cap800. TP-only / asia_range inert; asia window cuts; SL:TP 1:1.5 collapses PF; pullback_required/tema dilute. Do **not** promote on 5m alone. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** overnight **tick-confirm** `AQ_tick tr160` (trail_pts=160.0, else KEEP ema31 cap800 tr190/sls2100) workers=2. Optional runners tr170 / tr175 / tp4600_tr180 if champ rejects. Prefer max_loss streak <=7-8. If reject -> Batch AR timeout/news/sl_cap denser under KEEP (AN-AQ stall outside thin trail). No reaktor / no push.




### 2026-09-26 ~21:20 Europe/Bucharest Asia TICK CONFIRM AQ_tick tr160 on KEEP ema31 cap800 (run 20260926T180413Z_442e6ec5) -- **REJECT**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema31**, **wait14**, **rc3**, **cap800**, **flat23**, **mb275**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail160**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T17:50:32.364393+00:00 finished 2026-09-26T18:04:13.192969+00:00.
- **Result:** n230 · win44.8% · **+208311.1** · **PF 2.69** (avg 905.7 / win 3221.7 / loss -972.6). exits {'flatten': 42, 'sl': 122, 'trail': 64, 'tp': 2}. trail_armed 66 (28.7). entries {'higher_close': 51, 'ema_touch': 101, 'timeout_market': 56, 'lower_close': 22}. skipped 199 ({'no_break': 169, 'late_short': 30}). streaks max_win=6 max_loss=8. saved `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T180413Z_442e6ec5.json`.
- **vs KEEP** ema31 cap800 tr190 ticks PF2.69/+208866.7 n230 (run 20260926T153950Z_d5b5cf17): ΔPF **+0.00** · Δpts **-555.6** · Δn **+0** -- pts down (~-556), PF flat; max_loss=8 at hard-ish edge; **REJECT** (no promote).
- **vs 5m screen** tr160 PF2.879/+230261.7 n229 (dpts+1979.8): 5m soft edge did not hold on ticks (tick Δpts -555.6).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema31** · **max_break=15** · **max_hold16** · **rc3** · **cap800** · **wait14** · ticks PF2.69/+208866.7 n230. AQ trail pocket thin on ticks (tr160 loses pts; AJ lineage already rejected nearby cuts).
- **Next:** Batch AR `TIMEOUT_NEWS_SL_AR_KEEP_CAP800` 5m (denser timeout×news×sl_cap/be under KEEP ema31 cap800 — AN-AQ stall outside thin trail). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.



### 2026-09-26 ~21:51 Europe/Bucharest Asia Batch AR TIMEOUT_NEWS_SL_AR_KEEP_CAP800 5m (48 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T182356Z.json` · tag `TIMEOUT_NEWS_SL_AR_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: denser timeout tema/tminb/tminpb × news filter/tag · sl_cap/SL scale · BE arm. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 / ≥2.5 pts lifts (Δpts>0):** **none**. Clear lifts (Δpts≥2000 at PF≥2.5): **none**.
- **Inert (=baseline):** tminb_50/150/250 · news_tag/news_tag_all · slcap_off/1200/1500/1800/2200/2500/3000 — timeout_min_break low values, news_tag, and sl_cap alone do not change 5m outcome (sl_cap dormant vs fixed SL1000).
- **Dilute / reject (least-cut first):** `sl1050` PF2.800/+227672.2 (Δpts−609.7); `slcap1800_sl1100` PF2.689/+222443.7 (Δpts−5838.2); `sl950` PF2.791/+216093.1; `sl1150` PF2.574/+216543.7; `slcap2200_sl1200` PF2.498/+213133.8; `slcap2500_tp5200` / `sl1000_tp5000` PF2.661/+210177.5; `tminb_350` PF2.734/+209056.0; `news_filter` PF2.912/+201745.6 (Δpts−26536, higher PF but cuts pts); `news_filter_all` PF2.819/+191968.6; all tema_* / tminpb_* cut ~57–65k; `be2000` PF2.636/+171566.3; `be1500` PF2.606/+152251.9; `be800` / `be800_tr185` PF~2.00/+76k (near soft floor, heavy pts cut).
- **Under-floor PF<2.0:** none (be800 PF2.005 is soft-floor edge).
- **Conclusion:** Batch AR finds **no** soft≥2.5 pts refine on KEEP cap800 after AQ_tick tr160 REJECT. Timeout denser / news filter / sl_cap / BE only inert or dilute total pts (news_filter lifts PF to 2.912 but loses ~26k pts). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AS `CROSS_THIN_AS_KEEP_CAP800` 5m (denser AN thin-edge mb260×tr/hold crosses · ema neigh · resume/rco/hc · trail_arm_cap · SL/TP mode probes under KEEP ema31 cap800 — AN–AR stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.



### 2026-09-26 ~22:21 Europe/Bucharest Asia Batch AS CROSS_THIN_AS_KEEP_CAP800 5m (62 cells) — clear mb260×tr165 champ for tick
- **Grid:** `results/overnight_5m_grid_20260926T185630Z.json` · tag `CROSS_THIN_AS_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: denser AN thin mb×tr/hold crosses · ema neigh · resume/rco · trail_arm_cap · SL/TP mode probes. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `mb260_tr165` PF **2.893** / **+230646.5** n229 — ΔPF **+0.030** · Δpts **+2364.6**; `tr155` PF **2.882** / **+230591.7** n229 — ΔPF **+0.019** · Δpts **+2309.8**; `tr165` PF **2.877** / **+229931.9** n229 — ΔPF **+0.014** · Δpts **+1650.0**; `mb260_tr180` PF **2.885** / **+229656.3** n229 — ΔPF **+0.022** · Δpts **+1374.4**; `mb260_tr180_hold17` PF **2.885** / **+229656.3** n229 — ΔPF **+0.022** · Δpts **+1374.4**; `hold18_mb260_tr180` PF **2.885** / **+229656.3** n229 — ΔPF **+0.022** · Δpts **+1374.4**; `mb260_tr185` PF **2.883** / **+229326.3** n229 — ΔPF **+0.020** · Δpts **+1044.4**; `mb260` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `mb260_hold17` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `tr180` PF **2.868** / **+228941.7** n229 — ΔPF **+0.005** · Δpts **+659.8**; `tr180_hold17` PF **2.868** / **+228941.7** n229 — ΔPF **+0.005** · Δpts **+659.8**; `armcap1800_tr180` PF **2.868** / **+228941.7** n229 — ΔPF **+0.005** · Δpts **+659.8**.
- **PF ≥~2.5 with pts lift:** `mb260_tr165` PF 2.893/+230646.5 n229 dpts+2364.6; `tr155` PF 2.882/+230591.7 n229 dpts+2309.8; `tr165` PF 2.877/+229931.9 n229 dpts+1650.0; `mb260_tr180` PF 2.885/+229656.3 n229 dpts+1374.4; `mb260_tr180_hold17` PF 2.885/+229656.3 n229 dpts+1374.4; `hold18_mb260_tr180` PF 2.885/+229656.3 n229 dpts+1374.4; `mb260_tr185` PF 2.883/+229326.3 n229 dpts+1044.4; `mb260` PF 2.880/+228996.5 n229 dpts+714.6; `mb260_hold17` PF 2.880/+228996.5 n229 dpts+714.6; `tr180` PF 2.868/+228941.7 n229 dpts+659.8.
- **Clear Δpts≥~2k at PF≥2.5:** `mb260_tr165` dpts+2364.6 PF2.893; `tr155` dpts+2309.8 PF2.882.
- **Thin (<+2000 pts):** `tr165` dpts+1650.0; `mb260_tr180` dpts+1374.4; `mb260_tr180_hold17` dpts+1374.4; `hold18_mb260_tr180` dpts+1374.4; `mb260_tr185` dpts+1044.4; `mb260` dpts+714.6; `mb260_hold17` dpts+714.6; `tr180` dpts+659.8; `tr180_hold17` dpts+659.8; `armcap1800_tr180` dpts+659.8.
- **Under-floor PF<2.0:** `sl_m12` PF1.990/+194913.6.
- **Reject / dilute / inert:** inert=`mb265`, `mb270`, `ema_tf5`, `ema_tf30`, `rco_on`, `armcap1500`, `armcap2000`, `armcap1800`, `armcap2200`, `armcap2500`; dilute=`tp_range1p5` PF2.892/+228093.8 dpts-188.1; `mb255` PF2.840/+227794.6 dpts-487.3; `flat22_mb260` PF2.872/+226979.3 dpts-1302.6; `mb16_mb260` PF2.740/+225889.3 dpts-2392.6; `cap750_mb260` PF2.834/+225253.2 dpts-3028.7; `cap750` PF2.818/+224538.6 dpts-3743.3; `ema33` PF2.807/+223234.9 dpts-5047.0; `ema32_mb260` PF2.793/+221974.3 dpts-6307.6; `ema32_tr180` PF2.782/+221909.5 dpts-6372.4; `ema32` PF2.777/+221259.7 dpts-7022.2; `arm3800_tr180_mb260` PF2.818/+219692.8 dpts-8589.1; `tp_range1` PF2.899/+219285.0 dpts-8996.9; `cap950` PF2.755/+218578.6 dpts-9703.3; `cap850` PF2.745/+217342.8 dpts-10939.1.
- **Conclusion:** `mb260_tr165` is a **clear** soft>=2.5 pts refine on KEEP cap800 (Δpts **+2364.6**, ΔPF **+0.030** on 5m). Also clear: `tr155` dpts+2309.8 PF2.882. Cross of AN thin mb260 pocket with tighter trail (AJ/AQ single-axis ticks already REJECT nearby). EMA neigh / resume / SL-mode / tp_range mostly dilute or underfloor (sl_m12 PF1.99). Do **not** promote on 5m alone. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** overnight **tick-confirm** `AS_tick mb260_tr165` (mb260 + trail_pts=165, else KEEP ema31 cap800 tr190/sls2100) workers=2. Optional runners tr155 / tr165 / mb260_tr180 if champ rejects. Prefer max_loss streak <=7-8. If reject -> Batch AT denser untried axes (tp_r / trail_arm denser / session filters not yet crossed). No reaktor / no push.

### 2026-09-26 ~22:44 Europe/Bucharest Asia TICK CONFIRM AS_tick mb260_tr165 on KEEP ema31 cap800 (run 20260926T193619Z_441c6d57) -- **REJECT**
- **Setup (ticks, 2025-01 to 2026-09):** asia **0-6**, **ema31**, **wait14**, **rc3**, **cap800**, **flat23**, **mb260**, **SL1000/TP4800**, **sls3/2100**, **near_box N=6 D=1000**, **near_box_trend=off**, **break_on_wick=true**, **max_break=15**, **trail arm4000 / trail165**, timeout market, wait_from_break, **pullback preferred**, side both, **max_hold16**. workers=2. data_source=ticks. started 2026-09-26T19:22:44.729460+00:00 finished 2026-09-26T19:36:19.350129+00:00.
- **Result:** n230 · win44.8% · **+208811.4** · **PF 2.70** (avg 907.9 / win 3219.6 / loss -967.0). exits {'flatten': 43, 'sl': 121, 'trail': 64, 'tp': 2}. trail_armed 66 (28.7). entries {'higher_close': 50, 'ema_touch': 100, 'timeout_market': 59, 'lower_close': 21}. skipped 199 ({'no_break': 169, 'late_short': 30}). streaks max_win=6 max_loss=8. saved 
esults/overnight_XAUUSD_2025-01-01_2026-09-01_20260926T193619Z_441c6d57.json.
- **vs KEEP** ema31 cap800 tr190 mb275 ticks PF2.69/+208866.7 n230 (run 20260926T153950Z_d5b5cf17): ΔPF **+0.01** · Δpts **-55.3** · Δn **+0** -- pts slightly down (~-55), PF flat; max_loss=8 at hard-ish edge; **REJECT** (no promote).
- **vs 5m screen** mb260_tr165 PF2.893/+230646.5 n229 (dpts+2364.6): 5m soft edge did not hold on ticks (tick Δpts -55.3).
- **Conclusion:** KEEP unchanged = N6 D1000 · near_box_trend=off · **mb275** · **TP4800** · **flat23** · SL1000 · **sls3/2100** · wick_on · trail **arm4000/tr190** · **pullback preferred** · **ema31** · **max_break=15** · **max_hold16** · **rc3** · **cap800** · **wait14** · ticks PF2.69/+208866.7 n230. AS mb×trail pocket fails on ticks (near-flat); skip optional tr155/tr165 runners (AQ/AS trail lineage already REJECT).
- **Next:** Batch AT HOLD_SESS_AT_KEEP_CAP800 5m (denser trail_arm · tp_r/tp_near · hold/flatten expand · session/side/week2/seasonal · late-short/maxbreak mild under KEEP ema31 cap800). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-26 ~23:15 Europe/Bucharest Asia Batch AT HOLD_SESS_AT_KEEP_CAP800 5m (65 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T194810Z.json` · tag `HOLD_SESS_AT_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: denser trail_arm · tp_r/tp_near · hold/flatten expand · session/side/week2/seasonal · late-short/maxbreak mild. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 / ≥2.5 pts lifts (Δpts>0):** **none**. Clear lifts (Δpts≥2000 at PF≥2.5): **none**.
- **Inert (=baseline, 14 cells):** hold17–21 · seasonal_tag · week2_tag · trend_eff_0p30/0p40 · trend_sess8/12 · trend_flat1200/1800 · otpd_off — hold expand and trend/session tags do not change 5m outcome vs baseline under KEEP cap800.
- **Dilute / reject (least-cut first):** `sls4_2100` PF2.803/+228188.1 (Δpts −93.8); `hold15` PF2.865/+228023.3 (Δpts −258.6); `armcap2100_tr195` / `tp4400_tr195`…`tp5400_tr195` / `hold18_tr195` PF2.860/+227952.0 (Δpts −329.9); `arm3950_tr185` PF2.856/+227432.7; `w13` PF2.854/+227370.7; `flat22` PF2.870/+226886.1; `sls5_2100` PF2.750/+226628.9; `maxbreak17` PF2.670/+226339.7; `flat21` PF2.866/+225273.2; `maxbreak18` PF2.591/+225132.7; `maxbreak14` PF2.895/+224576.3 (higher PF, cuts pts); trail_arm extremes `arm3700`…`arm4500` cut ~14–20k; `seasonal_filter` PF2.938/+206452.8 (Δpts −21829); `week2_filter` PF2.604/+165939.5; `side_short` PF4.129/+133466.6 n89 (Δpts −94815); `side_long` PF2.187/+94815.3; tp_r* collapse (best `tp_r3p0` PF2.505/+179390.5 Δpts −48891).
- **Under-floor PF<2.0:** `tp_r1p2` PF1.801/+72729.7.
- **Conclusion:** Batch AT finds **no** soft≥2.5 pts refine on KEEP cap800 after AS_tick mb260_tr165 REJECT. Trail_arm denser / tp_r / hold-flatten / session-side only inert or dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AU `NEAR_ENTRY_AU_KEEP_CAP800` 5m (near-box N/D volume · entry/break rco/wick/hc/rc · asymmetric mb · ema/cap mild · SL:TP scale · late-short asia denser under KEEP ema31 cap800 — AN–AT stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-26 ~23:42 Europe/Bucharest Asia Batch AU NEAR_ENTRY_AU_KEEP_CAP800 5m (58 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T201852Z.json` · tag `NEAR_ENTRY_AU_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: near-box N/D volume · entry/break rco/wick/hc/rc · asymmetric mb · ema/cap mild · SL:TP scale · late-short asia denser. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `mb_a260_b275` PF **2.88** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `tr185` PF **2.866** / **+228611.7** n229 — ΔPF **+0.003** · Δpts **+329.8**.
- **PF ≥~2.5 with pts lift:** same two only (thin).
- **Clear Δpts≥~2k at PF≥2.5:** **none**.
- **Under-floor PF<2.0:** `rc1` PF **1.762** / **+118527.1** n246.
- **Reject / dilute / inert:** inert (=baseline, near-box N/D + rco_on + wick_off + asia_r280/320 + mb_a275_b250/b260) — near-box size knobs still **dormant** under preferred; dilute=`mb250`/`mb_a250_b275` PF2.839/+227656.1 (Δpts−625.8); `sl1050_tp5040` PF2.800/+227672.2; `sls3_1900`/`sls3_2000` PF2.795/+225281.9; `cap700` PF2.812/+223842.0; `sl1100_tp5280` PF2.689/+222443.7; `cap900` PF2.745/+217342.8; `sl950_tp4560` PF2.791/+216093.1; `ema29` PF2.654/+209262.9; `hc_off` PF2.538/+197625.5; `rc6` PF2.542/+198151.6; `ema28` PF2.510/+195613.7; `rco_wick_off` PF2.568/+154815.6; `wfb_off` PF2.013/+143524.6; `sl1000_tp1500` PF2.032/+98828.4; `sl1200_tp1800` PF2.030/+118657.1.
- **Conclusion:** Batch AU finds **no** clear soft≥2.5 pts refine on KEEP cap800 after AT stall. Best is thin `mb_a260_b275` Δpts **+714.6** (same ~+0.7k mb260 pocket AN/AS already tick-REJECT). Near-box N/D inert; entry/break and SL:TP 1:1.5 collapse or dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AV `TRAIL_TP_AV_KEEP_CAP800` 5m (trail-off + near-TP arm/TP ladder · larger TP×trail · mild BE×toff · toff×mb260 — plan D residual after AN–AU stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-26 ~23:52 Europe/Bucharest Asia Batch AV TRAIL_TP_AV_KEEP_CAP800 5m (51 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T205055Z.json` · tag `TRAIL_TP_AV_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: trail-off + near-TP arm/TP ladder · larger TP×trail · mild BE×toff · toff×mb260. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `tp5000_tr180`…`tp7000_tr180` (6 cells) PF **2.868** / **+228941.7** n229 — ΔPF **+0.005** · Δpts **+659.8** (identical; TP inert under active trail).
- **PF ≥~2.5 with pts lift:** same thin tr180 pocket only.
- **Clear Δpts≥~2k at PF≥2.5:** **none**.
- **Under-floor PF<2.0:** `toff_sl1200_tp1800` PF1.974; `toff_sl1400_tp2800` PF1.968; `toff_be1200_tp5200` PF1.971; `toff_sl1500_tp3000` PF1.829; `near_tp5200_arm5000_be1000` PF1.913; `toff_be800_tp4800` PF1.669.
- **Reject / dilute / inert:** inert=`tp*_tr190` (TP alone inert at tr190); dilute=all trail-off TP ladder (best `toff_tp4000` PF2.684/+206392 Δpts−21890); all near-TP arm cells cut ~16–63k; arm4800–6000 cut ~28–33k; toff×mb260 dilute; BE×toff collapse.
- **Conclusion:** Batch AV finds **no** clear soft≥2.5 pts refine on KEEP cap800. Plan D trail-off / near-TP lineages dilute under this seed; only thin tr180 Δpts **+659.8** (AS pocket, already tick-REJECT lineage). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AW `VOL_WAIT_AW_KEEP_CAP800` 5m (plan C denser mb/wait/max_break/asia_range + pullback × mild crosses under KEEP ema31 cap800 — AN–AV stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-27 ~00:20 Europe/Bucharest Asia Batch AW VOL_WAIT_AW_KEEP_CAP800 5m (51 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T205424Z.json` · tag `VOL_WAIT_AW_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100).
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `mb260` PF **2.88** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**.
- **Soft detail (top):** `mb260` dpts+714.6 PF2.88.
- **Clear Δpts≥~2k at PF≥2.5:** none.
- **Under-floor PF<2.0:** `pullback_off` PF1.369.
- **Reject highlight:** `pullback_off` PF1.369/+65728.5 n260 — preferred pullback required for PF.
- **Conclusion:** Batch AW finds **no** clear soft≥2.5 pts refine on KEEP cap800 (plan C denser mb/wait/max_break). Best is thin `mb260` Δpts **+714.6** (same AN/AU/AS pocket already tick-REJECT). **Skip tick-confirm**. KEEP unchanged ticks ema31 cap800 PF2.69/+208866.7 n230.
- **Next:** Batch AX `HOLD_TIMEOUT_AX_KEEP_CAP800` 5m (plan E earlier flatten×max_hold · timeout_ema/pullback · resume denser · mild SL:TP ~1:1.5 with trail on — AN–AW stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. No reaktor push.



### 2026-09-27 ~00:48 Europe/Bucharest Asia Batch AX HOLD_TIMEOUT_AX_KEEP_CAP800 5m (57 cells) - no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T212025Z.json` - tag `HOLD_TIMEOUT_AX_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: earlier flatten x max_hold + timeout ema/pullback + resume denser + mild SL:TP ~1:1.5 with trail on + entry-path + thin mb260 crosses. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `hold13` PF **2.871** / **+228426.2** n229 - dPF **+0.008** - dpts **+144.3**.
- **PF >=~2.5 with pts lift:** only `hold13` (thin).
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** `sl1600_tp2400_tr190` PF1.888/+136025.7.
- **Reject / dilute / inert:** inert=`hold22`, `hold24`; dilute (least-cut first)=`hold12` PF2.866 dpts-449.1; `mb260_flat22_hold18` PF2.872 dpts-1302.6; `flat22` / `flat22_hold18` / `flat22_hold20` / `hold18_flat22` / `hold20_flat22` PF2.870 dpts-1395.8; `flat22_hold14` PF2.863 dpts-2273.9; `flat21*` PF2.866 dpts-3008.7; `rcap700` PF2.812 dpts-4439.9; `flat20*` PF2.855 dpts-4896.7; resume caps / timeout tema-tpull / SL:TP 1:1.5 cut further.
- **Conclusion:** Batch AX finds **no** clear soft>=2.5 pts refine on KEEP cap800 after AN-AW stall (plan E hold/timeout). Best is thin `hold13` dpts **+144.3** (far under ~2k tick bar). Flatten earlier / resume denser / timeout gates / SL:TP 1:1.5 inert or dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AY `SOFT_CROSS_AY_KEEP_CAP800` 5m (compound thin edges hold13 x mb260 x tr185/tr180 x flat22 + week2/teff + trail_arm_cap + late-short denser + mild ema x cap - AN-AX stall). Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k). Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.


### 2026-09-27 ~01:19 Europe/Bucharest Asia Batch AY SOFT_CROSS_AY_KEEP_CAP800 5m (63 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T215329Z.json` · tag `SOFT_CROSS_AY_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: compound thin edges hold13×mb260×tr185/tr180×flat22×rcap700 + week2/teff + trail_arm_cap + late-short denser + mild ema×cap. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `hold13_mb260_tr180` PF **2.894** / **+229800.6** n229 — ΔPF **+0.031** · Δpts **+1518.7**, `hold13_mb260_tr185` PF **2.891** / **+229470.6** n229 — ΔPF **+0.028** · Δpts **+1188.7**, `mb260_tr185` PF **2.883** / **+229326.3** n229 — ΔPF **+0.020** · Δpts **+1044.4**, `hold13_mb260` PF **2.888** / **+229140.8** n229 — ΔPF **+0.025** · Δpts **+858.9**, `otp_off_hold13_mb260` PF **2.888** / **+229140.8** n229 — ΔPF **+0.025** · Δpts **+858.9**, `mb260` PF **2.88** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**, `tr180` PF **2.868** / **+228941.7** n229 — ΔPF **+0.005** · Δpts **+659.8**, `hold13_tr185` PF **2.874** / **+228756.0** n229 — ΔPF **+0.011** · Δpts **+474.1**.
- **PF ≥~2.5 with pts lift:** `hold13_mb260_tr180`, `hold13_mb260_tr185`, `mb260_tr185`, `hold13_mb260`, `otp_off_hold13_mb260`, `mb260`, `tr180`, `hold13_tr185`, `mb265_tr185_hold13`, `mb270_tr185_hold13`, `tr185`, `armcap2500_tr185`, `hold13`, `armcap3000_hold13`.
- **Clear Δpts≥~2k at PF≥2.5:** none.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`week2_tag`, `teff0p2`, `week2_trend_on`, `teff0p3`, `teff0p25`, `teff0p4`, `teff0p45`, `teff0p5`, `armcap1800`, `armcap2200`, `armcap2500`, `armcap3000`, `armcap3500`, `armcap4000`, `otp_off`; dilute (least-cut): `slsw4` PF2.803/+228188.1 (Δpts -93.8); `hold13_tr180_flat22` PF2.884/+227705.8 (Δpts -576.1); `sls4_2100_hold13` PF2.804/+227461.3 (Δpts -820.6); `flat22_tr185_mb260` PF2.875/+227309.1 (Δpts -972.8); `flat22_hold13_mb260` PF2.88/+227139.2 (Δpts -1142.7); `flat22` PF2.87/+226886.1 (Δpts -1395.8); `slsw5` PF2.75/+226628.9 (Δpts -1653.0); `sls3_2000` PF2.795/+225281.9 (Δpts -3000.0); `hold13_mb260_tr185_rcap700` PF2.839/+225025.7 (Δpts -3256.2); `rcap700_mb260` PF2.828/+224556.6 (Δpts -3725.3); worst: `ema29` PF2.654/+209262.9 (Δpts -19019.0); `ema30` PF2.631/+206346.3 (Δpts -21935.6); `ema30_cap700_hold13` PF2.592/+202303.7 (Δpts -25978.2); `week2_filter_teff0p30` PF2.778/+169754.8 (Δpts -58527.1); `week2_filter` PF2.604/+165939.5 (Δpts -62342.4).
- **Conclusion:** Batch AY finds **no** clear soft≥2.5 pts refine on KEEP cap800 after AN–AX stall (compound thin edges). Best is `hold13_mb260_tr180` Δpts **+1518.7** PF2.894 (under ~2k tick bar; AS/AQ trail+mb260 lineage already tick-REJECT nearby). Week2/teff/armcap mostly inert; ema/cap/late-short dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch AZ `ASIA_ENTRY_AZ_KEEP_CAP800` 5m (asia window + min_asia_range + require_close/wick + max_wait denser + mild BE-with-trail + trail_arm denser + ema_tf/max_break + thin AY compounds — AN–AY stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-27 ~01:48 Europe/Bucharest Asia Batch AZ ASIA_ENTRY_AZ_KEEP_CAP800 5m (71 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T221943Z.json` · tag `ASIA_ENTRY_AZ_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: asia window · min_asia_range · require_close/wick · max_wait denser · mild BE-with-trail · trail_arm denser · ema_tf/max_break · thin AY compounds. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `thin_ay` PF **2.894** / **+229800.6** n229 — ΔPF **+0.031** · Δpts **+1518.7**; `thin_ay_arange250` PF **2.894** / **+229800.6** n229 — ΔPF **+0.031** · Δpts **+1518.7**; `thin_ay_rco` PF **2.894** / **+229800.6** n229 — ΔPF **+0.031** · Δpts **+1518.7**; `arange250_mb260` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `rco_on_mb260` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `arange400_hold13` PF **2.871** / **+228426.2** n229 — ΔPF **+0.008** · Δpts **+144.3**; `wick_off_hold13` PF **2.871** / **+228426.2** n229 — ΔPF **+0.008** · Δpts **+144.3**.
- **PF ≥~2.5 with pts lift:** `thin_ay` PF 2.894/+229800.6 n229 dpts+1518.7; `thin_ay_arange250` PF 2.894/+229800.6 n229 dpts+1518.7; `thin_ay_rco` PF 2.894/+229800.6 n229 dpts+1518.7; `arange250_mb260` PF 2.880/+228996.5 n229 dpts+714.6; `rco_on_mb260` PF 2.880/+228996.5 n229 dpts+714.6; `arange400_hold13` PF 2.871/+228426.2 n229 dpts+144.3; `wick_off_hold13` PF 2.871/+228426.2 n229 dpts+144.3.
- **Thin (<+2000 pts):** `thin_ay` dpts+1518.7, `thin_ay_arange250` dpts+1518.7, `thin_ay_rco` dpts+1518.7, `arange250_mb260` dpts+714.6, `rco_on_mb260` dpts+714.6, `arange400_hold13` dpts+144.3, `wick_off_hold13` dpts+144.3.
- **Clear Δpts≥~2k at PF≥2.5:** **none**.
- **Under-floor PF<2.0:** `be400` PF1.040/+1753.3; `be600` PF1.440/+28075.2; `asia1_5` PF1.756/+107238.0; `asia0_5` PF1.857/+119012.9; `asia0_5_mb260` PF1.895/+122705.4; `be800_mb260` PF1.979/+75194.4; `thin_ay_be800` PF1.984/+75515.2.
- **Reject / dilute / inert:** inert=`arange200`, `arange250`, `arange350`, `arange400`, `rco_on`, `wick_off`, `ema_tf5`, `ema_tf30`; dilute=`be400` PF1.040/+1753.3 dpts-226528.6; `be600` PF1.440/+28075.2 dpts-200206.7; `be800_mb260` PF1.979/+75194.4 dpts-153087.5; `thin_ay_be800` PF1.984/+75515.2 dpts-152766.7; `be800` PF2.005/+76194.4 dpts-152087.5; `be800_tr180` PF2.009/+76474.3 dpts-151807.6; `be1000_hold13` PF2.223/+102387.7 dpts-125894.2; `be1000` PF2.224/+102555.0 dpts-125726.9; `asia1_5` PF1.756/+107238.0 dpts-121043.9; `asia0_5` PF1.857/+119012.9 dpts-109269.0; `asia0_5_mb260` PF1.895/+122705.4 dpts-105576.5; `be1200` PF2.468/+131788.3 dpts-96493.6; `asia0_8` PF2.005/+142871.1 dpts-85410.8; `be1500` PF2.606/+152251.9 dpts-76030.0; `rco_wick_off` PF2.568/+154815.6 dpts-73466.3; `asia1_7` PF2.128/+158251.6 dpts-70030.3; `asia0_7_hold13` PF2.210/+166733.8 dpts-61548.1; `thin_ay_asia07` PF2.208/+166821.9 dpts-61460.0.
- **Conclusion:** Batch AZ finds **no** clear soft≥2.5 pts refine on KEEP cap800 after AN–AY stall (asia/entry denser). Best is `thin_ay` Δpts **+1518.7** on 5m (under ~2k tick bar; same AY thin hold13×mb260×tr180 pocket, AS/AQ lineage already tick-REJECT). Asia window / BE / denser wait mostly dilute; arange/rco/wick/maxbreak mostly inert or thin. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BA `ASYM_RESUME_BA_KEEP_CAP800` 5m (asym min_break long/short · resume denser · hc_off · trail_arm_mode asia/from_fill · timeout_min_pullback denser · late-short asia_pts denser · tp_range_mult · near_box_trend closes_dir/net_ext · thin AY residual crosses — AN–AZ stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.



### 2026-09-27 ~02:14 Europe/Bucharest Asia Batch BA ASYM_RESUME_BA_KEEP_CAP800 5m (69 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T225152Z.json` · tag `ASYM_RESUME_BA_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: asym min_break long/short · resume denser · hc_off · trail_arm_mode asia/from_fill · timeout_min_pullback denser · late-short asia_pts denser · tp_range_mult · near_box_trend residual · thin AY residual crosses. Error cells: none (1 under-floor).
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `thin_ay_mba260_mbb275` PF **2.894** / **+229800.6** n229 — ΔPF **+0.031** · Δpts **+1518.7**; `mba260_mbb275_tr180` PF **2.885** / **+229656.3** n229 — ΔPF **+0.022** · Δpts **+1374.4**; `tp_rng2p0` PF **2.889** / **+229534.2** n229 — ΔPF **+0.026** · Δpts **+1252.3**; `mba260_mbb275` PF **2.880** / **+228996.5** n229 — ΔPF **+0.017** · Δpts **+714.6**; `mba275_mbb260_hold13` PF **2.871** / **+228426.2** n229 — ΔPF **+0.008** · Δpts **+144.3**.
- **PF ≥~2.5 with pts lift:** same five (all thin; AY/AS mb260×tr180 pocket + mild tp_range_mult).
- **Clear Δpts≥~2k at PF≥2.5:** **none**.
- **Under-floor PF<2.0:** `rc1` PF **1.762** / **+118527.1** n246.
- **Reject / dilute / inert:** inert=`nb_outside`/`nb_net_ext`/`nb_closes_dir`/`nb_breakout`/`mba275_mbb260`/`mba275_mbb250` (near-box trend still dormant; short-side loosen inert); dilute worst=`arm_from_fill_tr200` PF4.480/+33295.1 (Δpts −194986.8), `arm_from_fill` PF4.973/+35229.5, `arm_asia_cap1800` PF2.238/+126032.3, `arm_asia` PF2.421/+147555.8, `tpull*` gates cut ~64–74k, `rc1` under-floor; milder dilute=`mba250_mbb275` / late-short asia denser / resume extremes.
- **Conclusion:** Batch BA finds **no** clear soft≥2.5 pts refine on KEEP cap800 after AN–AZ stall (asym/resume). Best is `thin_ay_mba260_mbb275` Δpts **+1518.7** PF2.894 (under ~2k tick bar; same AY thin hold13×mb260×tr180 pocket, AS/AQ lineage already tick-REJECT). Trail_arm asia/from_fill and timeout_min_pullback collapse pts; near-box trend inert. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BB `PULL_SL_BB_KEEP_CAP800` 5m (pullback required/off · sl_mode asia_opposite/range/m12 · timeout_max_ema_dist · timeout_min_break denser · mild SL:TP fixed scale with trail on · trail denser mid · thin AY residual × pullback/timeout — AN–BA stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.


### 2026-09-27 ~02:49 Europe/Bucharest Asia Batch BB PULL_SL_BB_KEEP_CAP800 5m (74 cells) — no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T231911Z.json` · tag `PULL_SL_BB_KEEP_CAP800` · seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) · candles_5m · workers=2 · window 2025-01→2026-09. Axes: pullback required/off · sl_mode asia_opposite/range/m12 · timeout_max_ema_dist · timeout_min_break denser · mild SL:TP fixed scale with trail on · trail denser mid · thin AY residual × pullback/timeout — AN–BA stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 · PF **2.863** · **+228281.9**.
- **Soft ≥2.0 pts lifts:** `tr175_mb260` PF **2.888** / **+229986.3** n229 — ΔPF **+0.025** · Δpts **+1704.4**, `thin_ay_mba260_mbb275` PF **2.894** / **+229800.6** n229 — ΔPF **+0.031** · Δpts **+1518.7**, `tr170` PF **2.874** / **+229602.0** n229 — ΔPF **+0.011** · Δpts **+1320.1**, `tr175_hold13` PF **2.879** / **+229416.0** n229 — ΔPF **+0.016** · Δpts **+1134.1**, `tr175` PF **2.871** / **+229271.7** n229 — ΔPF **+0.008** · Δpts **+989.8**, `tr195_mb260` PF **2.877** / **+228666.6** n229 — ΔPF **+0.014** · Δpts **+384.7**, `tr185` PF **2.866** / **+228611.7** n229 — ΔPF **+0.003** · Δpts **+329.8**.
- **PF ≥~2.5 with pts lift:** `tr175_mb260`, `thin_ay_mba260_mbb275`, `tr170`, `tr175_hold13`, `tr175`, `tr195_mb260`, `tr185`.
- **Clear Δpts≥~2k at PF≥2.5:** **none**.
- **Under-floor PF<2.0:** `pb_off` PF **1.369** / **+65728.5** n260, `pb_off_mb260` PF **1.398** / **+70553.7** n260, `sl_asia_cap2500` PF **1.929** / **+195904.3** n229, `sl_m12_0p2` PF **1.984** / **+192998.1** n229, `sl_m12_0p25` PF **1.985** / **+193836.1** n229, `sl_m12_0p333` PF **1.99** / **+194913.6** n229.
- **Reject / dilute / inert:** inert=`tminb100`, `tminb150`, `tminb200`, `tminb250`, `sl1000_tp4000`, `sl1000_tp4500`, `sl1000_tp5200`, `sl1000_tp5600`; dilute (least-cut): `tr195` PF2.86/+227952.0 (Δpts -329.9); `sl1050_tp5040` PF2.8/+227672.2 (Δpts -609.7); `tr200` PF2.858/+227621.7 (Δpts -660.2); `tr205` PF2.855/+227291.7 (Δpts -990.2); `tr210` PF2.852/+226961.7 (Δpts -1320.2); `sl1100_tp5280` PF2.689/+222443.7 (Δpts -5838.2); `sl1100_tp4400` PF2.689/+222443.7 (Δpts -5838.2); `tminb300` PF2.805/+221133.0 (Δpts -7148.9); `sl950_tp4560` PF2.791/+216093.1 (Δpts -12188.8); `tema1500` PF2.866/+213677.6 (Δpts -14604.3); worst: `tminb200_pb_req` PF2.722/+170779.2 (Δpts -57502.7); `pb_required_w15` PF2.709/+167798.1 (Δpts -60483.8); `sl800_tp4000` PF2.451/+166919.3 (Δpts -61362.6); `tema300` PF2.613/+166379.5 (Δpts -61902.4); `tema200` PF2.62/+163896.5 (Δpts -64385.4); `pb_required_w11` PF2.323/+128839.4 (Δpts -99442.5).
- **Conclusion:** Batch BB finds **no** clear soft≥2.5 pts refine on KEEP cap800 after AN–BA stall (pullback/sl_mode/timeout). Best is `tr175_mb260` Δpts **+1704.4** PF2.888 (under ~2k tick bar; trail+mb260 pocket near AS/AQ/AY already tick-REJECT lineage). Pullback_off / sl_asia / sl_m12 collapse or under-floor; SL:TP scale mostly dilute/inert under active trail. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BC `NEWS_SLCAP_BC_KEEP_CAP800` 5m (news_mode/set · sl_cap denser · seasonal/side diagnostic · otp_off · trend_flat/sessions · skip_late residual · tp_r/range mild · thin BB tr175_mb260 compounds — AN–BB stall). Tick-confirm only clear soft≥2.5 pts lifts (Δpts≥~2k). Prefer max_loss streak ≤7–8. Still seek more pts while holding PF≥~2.5. No reaktor / no push.

### 2026-09-27 ~03:20 Europe/Bucharest Asia Batch BC NEWS_SLCAP_BC_KEEP_CAP800 5m (75 cells) - no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260926T234904Z.json` - tag `NEWS_SLCAP_BC_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: news_mode/set + sl_cap denser + seasonal/side + otp_off + trend_flat/sessions + skip_late residual + tp_r/range mild + thin BB tr175_mb260 compounds - AN-BB stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `thin_bb_hold13` PF **2.896** / **+230130.6** n229 - dPF **+0.033** - dpts **+1848.7**, `otp_off_tr175_mb260` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `thin_bb` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `thin_bb_news_skip` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `thin_bb_slcap1600` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `thin_bb_slcap2500` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `thin_bb_otp_off` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `thin_bb_tflat1000` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**.
- **PF >=~2.5 with pts lift:** `thin_bb_hold13`, `otp_off_tr175_mb260`, `thin_bb`, `thin_bb_news_skip`, `thin_bb_slcap1600`, `thin_bb_slcap2500`, `thin_bb_otp_off`, `thin_bb_tflat1000`, `slcap1600_tr175`, `slsw4_tr175`, `slcap2500_mb260`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`news_skip`, `news_skip_high`, `news_skip_all`, `news_flatten`, `news_flatten_high`, `news_flatten_all`, `news_pause`, `news_pause_high`, `news_pause_all`, `news_skip_sched`, `slcap1200`, `slcap1400`, `slcap1600`, `slcap1800`, `slcap2200`, `slcap2500`, `slcap3000`, `slcap3500`, `slcap4000`, `season_winter`, `season_winter_join`, `season_summer`, `season_summer_join`, `season_q1`, `season_q1_join`; dilute (least-cut): `slsw4` PF2.803/+228188.1 (dpts -93.8); `tp_rng1p5` PF2.892/+228093.8 (dpts -188.1); `slsw5` PF2.75/+226628.9 (dpts -1653.0); `tp_rng2p5` PF2.847/+226306.0 (dpts -1975.9); `slsw1` PF2.877/+226187.5 (dpts -2094.4); `thin_bb_slsw2` PF2.854/+225876.9 (dpts -2405.0); `slsw2` PF2.83/+224187.5 (dpts -4094.4); `slsa1800` PF2.723/+223193.6 (dpts -5088.3); `slsw2_slsa1800` PF2.723/+223193.6 (dpts -5088.3); `slsa1500` PF2.666/+222757.2 (dpts -5524.7); worst: `week2_on` PF2.604/+165939.5 (dpts -62342.4); `side_short_tr175` PF4.143/+134051.4 (dpts -94230.5); `side_short` PF4.129/+133466.6 (dpts -94815.3); `tp_r1p5` PF2.032/+98828.4 (dpts -129453.5); `side_long_mb260` PF2.207/+95529.9 (dpts -132752.0); `side_long` PF2.187/+94815.3 (dpts -133466.6).
- **Conclusion:** Batch BC finds **no** clear soft>=2.5 pts refine on KEEP cap800 after AN-BB stall (news/sl_cap/seasonal). Best is `thin_bb_hold13` dpts **+1848.7** PF2.896 (under ~2k tick bar; same BB tr175_mb260 pocket, AS/AQ trail+mb lineage already tick-REJECT). News/sl_cap/seasonal/otp/trend_flat mostly inert; side long/short and week2 dilute total pts. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BD `CROSS_POCKET_BD_KEEP_CAP800` 5m (denser trail x mb x hold x arm x mild SL/wait/flatten + hc/resume/near-box around BC thin pocket - AN-BC stall). Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k). Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.

### 2026-09-27 ~03:57 Europe/Bucharest Asia Batch BD CROSS_POCKET_BD_KEEP_CAP800 5m (82 cells) - clear champs = prior tick-REJECT pocket; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T002046Z.json` - tag `CROSS_POCKET_BD_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: denser trail x mb x hold x arm x mild SL/wait/flatten + hc/resume/near-box around BC thin pocket - AN-BC stall. Error cells: none (flat24 invalid hour).
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `tr165_mb260` PF **2.893** / **+230646.5** n229 - dPF **+0.030** - dpts **+2364.6**, `hold13_tr170_mb260` PF **2.899** / **+230460.9** n229 - dPF **+0.036** - dpts **+2179.0**, `tr170_mb260` PF **2.891** / **+230316.6** n229 - dPF **+0.028** - dpts **+2034.7**, `tr160` PF **2.879** / **+230261.7** n229 - dPF **+0.016** - dpts **+1979.8**, `hold13_tr175_mb260` PF **2.896** / **+230130.6** n229 - dPF **+0.033** - dpts **+1848.7**, `tr175_mb260` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `nb_N4_D1000_tr175_mb260` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `nb_N8_D1000_tr175_mb260` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `nb_N6_D800_tr175_mb260` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**, `nb_N6_D1200_tr175_mb260` PF **2.888** / **+229986.3** n229 - dPF **+0.025** - dpts **+1704.4**.
- **PF >=~2.5 with pts lift:** `tr165_mb260` dpts+2364.6, `hold13_tr170_mb260` dpts+2179.0, `tr170_mb260` dpts+2034.7, `tr160` dpts+1979.8, `hold13_tr175_mb260` dpts+1848.7, `tr175_mb260` dpts+1704.4, `nb_N4_D1000_tr175_mb260` dpts+1704.4, `nb_N8_D1000_tr175_mb260` dpts+1704.4, `nb_N6_D800_tr175_mb260` dpts+1704.4, `nb_N6_D1200_tr175_mb260` dpts+1704.4, `tp4600_tr175_mb260` dpts+1704.4, `tp5000_tr175_mb260` dpts+1704.4, `tp5200_tr175_mb260` dpts+1704.4, `tr165` dpts+1650.0, `tr165_mb265` dpts+1650.0, `tr165_mb270` dpts+1650.0, `hold13_tr180_mb260` dpts+1518.7, `hold15_tr175_mb260` dpts+1445.8, `tr180_mb260` dpts+1374.4, `tr170` dpts+1320.1, `tr170_mb265` dpts+1320.1, `tr170_mb270` dpts+1320.1, `hold12_tr175_mb260` dpts+1255.3, `tr165_mb255` dpts+1162.7, `sl1050_tr175_mb260` dpts+1144.7, `hold13_tr175_mb265` dpts+1134.1, `tr175` dpts+989.8, `tr175_mb265` dpts+989.8, `tr175_mb270` dpts+989.8, `hold14_tr175_mb260` dpts+903.2, `tr170_mb255` dpts+832.8, `mb260` dpts+714.6, `tr180` dpts+659.8, `tr180_mb265` dpts+659.8, `tr180_mb270` dpts+659.8, `hold13_tr175_mb255` dpts+646.8, `tr175_mb255` dpts+502.5, `tr185` dpts+329.8, `tr180_mb255` dpts+172.5, `wait13_tr175_mb260` dpts+73.0.
- **Clear dpts>=~2k at PF>=2.5:** `tr165_mb260` dpts+2364.6 PF2.893, `hold13_tr170_mb260` dpts+2179.0 PF2.899, `tr170_mb260` dpts+2034.7 PF2.891 — **same AS_tick mb260_tr165 / AQ_tick tr160 REJECT pocket** (do not re-tick).
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=`mb270`, `mb265`, `nb_N4_D1000`, `nb_N8_D1000`, `nb_N6_D800`, `nb_N6_D1200`; dilute (least-cut): `flat22_hold13_tr175_mb260` PF2.888/+228129.0 (dpts -152.9); `flat22_tr175_mb260` PF2.88/+227969.1 (dpts -312.8); `mb255` PF2.84/+227794.6 (dpts -487.3); `sl1050` PF2.8/+227672.2 (dpts -609.7); `mb250` PF2.839/+227656.1 (dpts -625.8); `rcap700_tr175_mb260` PF2.836/+225531.4 (dpts -2750.5); `sl1100_tr175_mb260` PF2.698/+223526.6 (dpts -4755.3); `arm3900_tr175_mb260` PF2.834/+223399.2 (dpts -4882.7); worst: `rc4` PF2.547/+197690.6 (dpts -30591.3); `hc_off` PF2.538/+197625.5 (dpts -30656.4); `rc5` PF2.511/+194867.9 (dpts -33414.0); `wait12_tr175_mb260` PF2.522/+193814.8 (dpts -34467.1); `rc2_tr175_mb260` PF2.382/+189126.7 (dpts -39155.2); `rc2` PF2.362/+187439.0 (dpts -40842.9).
- **Conclusion:** Batch BD 5m 'clear' champs (`tr165_mb260` dpts **+2364.6** PF2.893; `hold13_tr170_mb260` +2179; `tr170_mb260` +2034.7) are the **exact AS_tick mb260_tr165 REJECT pocket** (ticks Δpts −55.3) / AQ tr160 REJECT neighborhood. Near-box N/D and TP mild cells inert (=baseline). **Skip tick-confirm** (no fresh pocket). KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BE `PTS_ORTHO_BE_KEEP_CAP800` 5m (pivot off trail×mb pocket: denser max_hold later + skip_late denser + cap residual + trend_sessions/flat + pullback-required wait + sl_range diagnostic + asym mb extremes — AN-BD stall). Tick-confirm only **fresh** clear soft>=2.5 pts lifts (dpts>=~2k) not already tick-REJECT. Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.
### 2026-09-27 ~04:14 Europe/Bucharest Asia Batch BE PTS_ORTHO_BE_KEEP_CAP800 5m (85 cells) - no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T010023Z.json` - tag `PTS_ORTHO_BE_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: denser max_hold later + skip_late denser + cap residual + trend_sessions/flat + pullback-required wait + sl_range diagnostic + asym mb extremes - AN-BD stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** **none**.
- **PF >=~2.5 with pts lift:** **none**.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** `rc1` PF1.762/+118527.1.
- **Reject / dilute / inert:** inert=`hold17`..`hold22`, `ema_tf10`, `ema_tf60`, `otp_off`, `otp_off_hold18`, `tflat*`, `tsess*`, `mba275_mbb250`; dilute (least-cut): `slsw4`/`hold18_slsw4` PF2.803/+228188.1 (dpts -93.8); `mba250_mbb275` PF2.839 dpts-625.8; `mba275_mbb225` PF2.798 dpts-749.0; `slsw5` PF2.75 dpts-1653.0; `cap750` PF2.818 dpts-3743.3; `cap700` PF2.812 dpts-4439.9; worst: `slrng*` ~PF2.0-2.1 dpts~-28k..-37k; `rc2` PF2.362 dpts-40842.9; `pb_req*` PF2.58-2.72 dpts~-57k..-64k.
- **Conclusion:** Batch BE finds **no** soft>=2.5 pts refine on KEEP cap800 after AN-BD stall (orthogonal axes). Max-hold later / trend_sessions/flat / ema_tf / otp inert (=baseline). Skip_late / asym mb / cap residual / sl_range / pullback-required dilute or under-floor. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230). Overnight idle leftover `20260926T193619Z_441c6d57` = prior AS_tick mb260_tr165 REJECT (already logged) — not re-scored.
- **Next:** Batch BF `TP_TRAIL_BF_KEEP_CAP800` 5m (plan D TP/arm denser with trail ON + trail-off TP scale residual + near_box_trend breakout/outside/closes_dir/net_ext x N/D + timeout_min_pullback + mild wait/maxbreak/ema — AN-BE stall). Tick-confirm only **fresh** clear soft>=2.5 pts lifts (dpts>=~2k) not already tick-REJECT (avoid AS/AQ mb260_tr165 pocket). Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.
### 2026-09-27 ~04:27 Europe/Bucharest Asia Batch BF TP_TRAIL_BF_KEEP_CAP800 5m (94 cells) - no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T012635Z.json` - tag `TP_TRAIL_BF_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: plan D TP/arm denser with trail ON + trail-off TP scale + near_box_trend breakout/outside/closes_dir/net_ext x N/D + timeout_min_pullback + mild wait/maxbreak/ema - AN-BE stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** **none**.
- **PF >=~2.5 with pts lift:** **none**.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert= all `tp4000`..`tp6000`, `arm4000_tp4400`, all `nb_*` trend gates (dormant under preferred); dilute (least-cut): `wait13` PF2.854 dpts-911.2; `tr210_arm4000` PF2.852 dpts-1320.2; `maxbreak17` PF2.67 dpts-1942.2; `tr220_arm4000` PF2.847 dpts-1979.9; `maxbreak14` PF2.895 dpts-3705.6 (PF up, pts down); `arm3900` PF2.809 dpts-6602.1; worst: `toff_tp*` PF2.21-2.68 dpts~-22k..-62k; `tpull*` PF~2.7 dpts~-63k..-76k.
- **Conclusion:** Batch BF finds **no** soft>=2.5 pts refine on KEEP cap800 after AN-BE stall (plan D / near-box trend). TP-only inert under active trail (trail exits before TP). Near-box trend gates inert (=baseline; dormant under preferred). Arm shifts / trail-off / tpull / wait/maxbreak/ema dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BG `SLTP_RATIO_BG_KEEP_CAP800` 5m (prefer SL:TP ~1:1.5+ with trail ON denser + mild SL/TP/trail/hold/flatten compounds; avoid AS/AQ mb260_tr165 pocket — AN-BF stall). Tick-confirm only **fresh** clear soft>=2.5 pts lifts (dpts>=~2k). Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.
### 2026-09-27 ~04:42 Europe/Bucharest Asia Batch BG SLTP_RATIO_BG_KEEP_CAP800 5m (81 cells) - clear champs = prior tick-REJECT pocket; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T013027Z.json` - tag `SLTP_RATIO_BG_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: prefer SL:TP ~1:1.5+ denser with trail ON + mild trail/hold/flatten/arm compounds; trail denser alone; avoid AS/AQ mb260_tr165 pocket - AN-BF stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `tr140` PF **2.890** / **+231581.9** n229 - dPF **+0.027** - dpts **+3300.0**, `tr150` PF **2.885** / **+230921.7** n229 - dPF **+0.022** - dpts **+2639.8**, `tr160` PF **2.879** / **+230261.7** n229 - dPF **+0.016** - dpts **+1979.8**, `tr170` PF **2.874** / **+229602.0** n229 - dPF **+0.011** - dpts **+1320.1**.
- **PF >=~2.5 with pts lift:** `tr140`, `tr150`, `tr160`, `tr170`.
- **Clear dpts>=~2k at PF>=2.5:** `tr140` dpts+3300.0 PF2.890, `tr150` dpts+2639.8 PF2.885 - **same AQ_tick tr160 / AS_tick mb260_tr165 / AJ trail-tighten REJECT pocket** (do not re-tick tr140-170).
- **Under-floor PF<2.0:** `sl800_tp1200` PF1.658/+57000.2; `sl2000_tp3000` PF1.803/+150625.0; `sl900_tp1350` PF1.810/+75277.7; `sl1800_tp2700` PF1.873/+147285.6; `sl1600_tp2400` PF1.888/+136025.7; `sl1500_tp2250` PF1.898/+129874.6; `sl800_tp2000` PF1.909/+93364.8; `sl1000_tp1500_arm1200` PF1.991/+89026.7.
- **Reject / dilute / inert:** inert=`tp4000_keep_sl` (=baseline); dilute (least-cut): `tr195` PF2.86/+227952.0 (dpts -329.9); `sl1050_keep_tp` PF2.8/+227672.2 (dpts -609.7); `tr205` PF2.855/+227291.7 (dpts -990.2); `tr215` PF2.85/+226631.9 (dpts -1650.0); `tr230` PF2.841/+225641.7 (dpts -2640.2); `tr250` PF2.831/+224321.7 (dpts -3960.2); `sl1100_keep_tp` PF2.689/+222443.7 (dpts -5838.2); worst: `sl800_tp1200` dpts -171281.7 and other tight 1:1.5 SL:TP cells (~ -129k to -153k).
- **Conclusion:** Batch BG finds **no fresh** soft>=2.5 pts refine on KEEP cap800 after AN-BF stall (SL:TP ratio). Clear 5m champs `tr140`/`tr150` are deeper into the **already tick-REJECT trail-tighten pocket** (AQ tr160 / AS mb260_tr165 / AJ). Prefer SL:TP ~1:1.5 with trail ON collapses pts vs KEEP 1000/4800 trail structure. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BH `HOLD_FLAT_BH_KEEP_CAP800` 5m (plan E denser flatten/max_hold on KEEP + otp_off volume + mild ema/wait/maxbreak/asia_range/mb crosses; trail widen-only tr200+; avoid tr140-170 / AS/AQ pocket - AN-BG stall). Tick-confirm only **fresh** clear soft>=2.5 pts lifts (dpts>=~2k) not already tick-REJECT. Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.

### 2026-09-27 ~04:51 Europe/Bucharest Asia Batch BH HOLD_FLAT_BH_KEEP_CAP800 5m (93 cells) - no pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T015113Z.json` - tag `HOLD_FLAT_BH_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: plan E denser flatten/max_hold on KEEP + otp_off volume + mild ema/wait/maxbreak/asia_range/mb; trail widen-only tr200+; avoid tr140-170 / AS/AQ pocket - AN-BG stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `otp_off_mb260` PF **2.88** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**; `mb260` PF **2.88** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**; `mb260_hold18` PF **2.88** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**; `hold13` PF **2.871** / **+228426.2** n229 - dPF **+0.008** - dpts **+144.3**.
- **PF >=~2.5 with pts lift:** `otp_off_mb260`, `mb260`, `mb260_hold18`, `hold13`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=['flat23', 'hold17', 'hold18', 'hold20', 'hold19', 'hold21', 'hold22', 'hold18_flat23', 'hold20_flat23', 'otp_off', 'otp_off_hold18', 'arange200', 'arange250', 'arange350', 'arange400', 'arange250_otp_off', 'mb265', 'mb270', 'te0p2', 'te0p25']; dilute (least-cut): `hold15` PF2.865 (dpts -258.6); `hold12` PF2.866 (dpts -449.1); `otp_off_mb250` PF2.839 (dpts -625.8); `mb250` PF2.839 (dpts -625.8); `tr200` PF2.858 (dpts -660.2); `tr200_hold18` PF2.858 (dpts -660.2); `hold14` PF2.856 (dpts -801.2); `otp_off_hold14` PF2.856 (dpts -801.2); worst: `wait11` PF2.469 (dpts -38001.1); `otp_off_wait12` PF2.513 (dpts -35412.9); `wait12` PF2.513 (dpts -35412.9); `ema28` PF2.51 (dpts -32668.2); `wait15_hold14` PF2.603 (dpts -27176.2); `otp_off_wait15` PF2.61 (dpts -26375.0); `wait15` PF2.61 (dpts -26375.0); `wait15_flat22` PF2.625 (dpts -26222.2).
- **Conclusion:** Batch BH finds **no** clear soft>=2.5 pts refine on KEEP cap800 after AN-BG stall (plan E / volume). Best is `otp_off_mb260` dpts **+714.6** PF2.88 (under ~2k tick bar; prior mb260 thin pocket). Flatten/hold/ema/wait/maxbreak/te mostly inert (=baseline); otp_off does not lift trade count on this seed (n still 229). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BI `ARM_RESUME_BI_KEEP_CAP800` 5m (trail_arm denser mid + resume/hc/wick/rco residual + skip_late denser + mild flatten/hold/TP crosses; avoid tr140-170 / AS/AQ pocket - AN-BH stall). Tick-confirm only **fresh** clear soft>=2.5 pts lifts (dpts>=~2k). Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.

### 2026-09-27 ~05:17 Europe/Bucharest Asia Batch BI ARM_RESUME_BI_KEEP_CAP800 5m (88 cells) - no pts lift; skip tick
- **Grid:** esults/overnight_5m_grid_20260927T015414Z.json\ - tag \ARM_RESUME_BI_KEEP_CAP800\ - seed KEEP ticks 60926T153950Z_d5b5cf17\ (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: trail_arm denser mid + resume/hc/wick/rco + skip_late denser + mild flatten/hold/TP; avoid tr140-170 / AS/AQ pocket - AN-BH stall. Error cells: none.
- **Baseline 5m KEEP** (\KEEP_cap800_baseline\): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** \	hin_bh_mb260\ PF **2.88** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**; \	hin_bh_hold13\ PF **2.871** / **+228426.2** n229 - dPF **+0.008** - dpts **+144.3**.
- **PF >=~2.5 with pts lift:** \	hin_bh_mb260\, \	hin_bh_hold13\.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** c1\ PF **1.762** / **+118527.1** n246.
- **Reject / dilute / inert:** inert=\rm4000_tp5200\/\rm4000_tp5600\/\wick_off\/co_on\/\rmcap*\ (=baseline); dilute (least-cut): \slsw4\ PF2.803/+228188.1 (dpts -93.8); \rm3950\ PF2.853/+227097.9 (dpts -1184.0); \wick_off_flat22\/co_on_flat22\ PF2.87 (dpts -1395.8); \slsw5\ PF2.75 (dpts -1653.0); worst: co_wick_off\ PF2.568/+154815.6 (dpts -73466.3); \hc_off_arm3800\ PF2.409 (dpts -47236.2); c2*\ / low arm3000-3400 / c4\/c5\ cut ~30-43k.
- **Conclusion:** Batch BI finds **no** clear soft>=2.5 pts refine on KEEP cap800 after AN-BH stall (arm/resume). Best is \	hin_bh_mb260\ dpts **+714.6** PF2.88 (under ~2k tick bar; prior mb260 thin pocket). Arm denser mid / resume / hc_off / skip_late dilute or under-floor; wick/rco/armcap inert. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BJ \BE_VOLUME_BJ_KEEP_CAP800\ 5m (be_arm denser + one_trade_per_day off volume + asia start/end denser + min_asia_range denser + max_break denser + ema/wait denser + trail widen-only tr200+; avoid tr140-170 / AS/AQ pocket - AN-BI stall). Tick-confirm only **fresh** clear soft>=2.5 pts lifts (dpts>=~2k). Prefer max_loss streak <=7-8. Still seek more pts while holding PF>=~2.5. No reaktor / no push.


### 2026-09-27 ~05:43 Europe/Bucharest Asia Batch BJ BE_VOLUME_BJ_KEEP_CAP800 5m (87 cells) - clear maxbreak19 champ for tick
- **Grid:** `results/overnight_5m_grid_20260927T022144Z.json` - tag `BE_VOLUME_BJ_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: be_arm denser + one_trade_per_day off volume + asia start/end denser + min_asia_range denser + max_break denser + ema/wait denser + trail widen-only tr200+; avoid tr140-170 / AS/AQ pocket - AN-BI stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `maxbreak19` PF **2.583** / **+230413.3** n261 - dPF **-0.280** - dpts **+2131.4**; `otp_off_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**; `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**; `thin_bh_hold13` PF **2.871** / **+228426.2** n229 - dPF **+0.008** - dpts **+144.3**.
- **PF >=~2.5 with pts lift:** `maxbreak19`, `otp_off_mb260`, `thin_bh_mb260`, `thin_bh_hold13`.
- **Clear dpts>=~2k at PF>=2.5:** `maxbreak19` dpts+2131.4 PF2.583.
- **Under-floor PF<2.0:** `asia0_5` PF1.857/+119012.9; `asia1_5` PF1.756/+107238.0; `be800_tr220` PF1.994/+75354.4; `be800_flat22` PF1.993/+75282.5; `thin_bh_mb260_be800` PF1.979/+75194.4; `ema32_be800` PF1.974/+72879.8; `asia0_7_be800` PF1.548/+48036.6; `be600` PF1.440/+28075.2; `be500` PF1.204/+11172.1; `otp_off_be500` PF1.204/+11172.1.
- **Reject / dilute / inert:** inert=['otp_off', 'otp_off_hold18', 'arange200', 'arange250', 'arange280', 'arange320', 'arange350', 'arange400', 'arange250_otp_off']; dilute (least-cut): `otp_off_mb250` PF2.839 (dpts -625.8); `otp_off_tr200` PF2.858 (dpts -660.2); `tr200` PF2.858 (dpts -660.2); `otp_off_wait13` PF2.854 (dpts -911.2); `wait13` PF2.854 (dpts -911.2); `tr210` PF2.852 (dpts -1320.2); `maxbreak17` PF2.670 (dpts -1942.2); `tr220` PF2.847 (dpts -1979.9); worst: `be200` PF0.629 (dpts -236452.6); `be300` PF1.017 (dpts -227724.3); `be400` PF1.040 (dpts -226528.6); `be500_hold14` PF1.194 (dpts -217668.1); `be500_flat22` PF1.199 (dpts -217399.6); `be500_tr200` PF1.202 (dpts -217209.9); `be500` PF1.204 (dpts -217109.8); `otp_off_be500` PF1.204 (dpts -217109.8).
- **Conclusion:** `maxbreak19` is a **clear** soft>=2.5 pts refine on KEEP cap800 (dpts **+2131.4**, dPF **-0.280** on 5m; n261). Lonely maxbreak peak (mb18/20 do not lift; denser be_arm / asia / arange / ema/wait / otp_off mostly dilute or underfloor). Thin residual otp_off_mb260/thin_bh_mb260 dpts+714.6 under ~2k bar. Do **not** promote on 5m alone. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** overnight **tick-confirm** `BJ_tick maxbreak19` (max_break_candles_after=19, else KEEP ema31 cap800 tr190/sls2100) workers=2. Optional note runners maxbreak18 / maxbreak17 / otp_off_mb260 if champ rejects (not auto-queue thin mb260). Prefer max_loss streak <=7-8. If reject -> Batch BK plan-F denser (seasonal/week2/side + untried timeout/news residual). No reaktor / no push.

### 2026-09-27 ~06:12 Europe/Bucharest Asia BJ_tick maxbreak19 ticks - REJECT
- **Run:** `results/overnight_XAUUSD_2025-01-01_2026-09-01_20260927T030123Z_ba655e3e.json` - run_id `20260927T030123Z_ba655e3e` - data_source=ticks - workers=2 - window 2025-01 to 2026-09 - finished `2026-09-27T03:01:23.256195+00:00`.
- **Overrides vs KEEP:** `max_break_candles_after=19` (else KEEP asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16).
- **Result:** n262 - PF **2.43** - **+209682.8** - win42.7% - max_loss_streak **9** (max_win 6) - exits {"flatten":46,"sl":145,"trail":69,"tp":2}.
- **vs KEEP** ticks `20260926T153950Z_d5b5cf17` PF2.69/+208866.7 n230: dPF **-0.26** - dpts **+816.1**.
- **Decision:** **REJECT** - dpts +816.1 under ~2k promote bar; PF 2.43 under soft >=2.5; max_loss streak 9 > 8 hard-ish filter. 5m overpromised (+230.4k PF2.58 -> ticks +209.7k PF2.43; n261->262). KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BK `PLAN_F_BK_KEEP_CAP800` 5m (plan F denser: real seasonal/week2/news tag|filter + untried timeout_max_ema_dist / timeout_min_break / timeout_min_pullback denser + pullback-required / rco residual; avoid side-only and trail-tighten pocket; prefer combined for total pts). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.

### 2026-09-27 ~06:44 Europe/Bucharest Asia Batch BK PLAN_F_BK_KEEP_CAP800 5m (75 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T031651Z.json` - tag `PLAN_F_BK_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: plan F denser real seasonal/week2/news tag|filter + timeout_max_ema_dist / timeout_min_break / timeout_min_pullback denser + pullback-required / rco residual; avoid side-only and tr140-170 / AS/AQ pocket; after BJ_tick maxbreak19 REJECT. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**, `thin_bh_hold13` PF **2.871** / **+228426.2** n229 - dPF **+0.008** - dpts **+144.3**.
- **PF >=~2.5 with pts lift:** `thin_bh_mb260`, `thin_bh_hold13`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** `pb_off` PF1.369/+65728.5.
- **Reject / dilute / inert:** inert=[`season_tag`, `season_tag_join`, `week2_tag`, `season_tag_week2_tag`, `news_tag_sched`, `news_tag_high`, `news_tag_all`, `tminbreak50`, `tminbreak100`, `tminbreak150`, `tminbreak200`, `tminbreak250`, `tminbreak250_otp_off`, `rco_on`, `otp_off`]; dilute (least-cut): `news_tag_sched_hold14` PF2.856 (dpts -801.2); `temd2500` PF2.898 (dpts -1426.0); `tminbreak300_mb260` PF2.899 (dpts -3148.9); `temd3000` PF2.850 (dpts -3426.0); `temd2000` PF2.886 (dpts -4671.4); `temd2000_tmb250` PF2.886 (dpts -4671.4); worst: `tminpb150` PF2.694 (dpts -65369.7); `temd200` PF2.620 (dpts -64385.4); `tminpb200` PF2.722 (dpts -64369.7); `tminpb300` PF2.722 (dpts -64369.7); `tminpb400` PF2.722 (dpts -64369.7); `tminpb500` PF2.722 (dpts -64369.7); `tminpb750` PF2.722 (dpts -64369.7); `tminpb1000` PF2.722 (dpts -64369.7).
- **Conclusion:** Batch BK finds **no** clear soft>=2.5 pts refine on KEEP cap800 after AN-BJ stall (plan F). Best is `thin_bh_mb260` dpts **+714.6** PF2.880 (under ~2k tick bar; prior mb260 thin pocket). Seasonal/week2/news tag mostly inert; filters + timeout knobs + pb_required/rco dilute; `pb_off` under-floor. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BL `SL_EMA_TF_BL_KEEP_CAP800` 5m (untried residual after A-F stall: ema_tf_min denser + SL fixed/cap denser holding SL:TP~1:1.5+ with trail ON + asymmetric mb above/below + trail_arm_cap denser + mild compounds; avoid tr140-170 / AS/AQ / maxbreak19 / side-only). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.

### 2026-09-27 ~06:53 Europe/Bucharest Asia Batch BL SL_EMA_TF_BL_KEEP_CAP800 5m (71 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T035139Z.json` - tag `SL_EMA_TF_BL_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: after A-F stall — ema_tf_min denser + SL fixed/cap denser (SL:TP~1:1.5+ trail ON) + asymmetric mb above/below + trail_arm_cap denser + mild compounds; avoid tr140-170 / AS/AQ / maxbreak19 / side-only. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `etf30_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**, `mba260_mbb275` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**, `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**.
- **PF >=~2.5 with pts lift:** `etf30_mb260`, `mba260_mbb275`, `thin_bh_mb260`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=[`etf5`, `etf20`, `etf10`, `etf30`, `etf45`, `etf60`, `slcap1200`, `slcap1500`, `slcap1800`, `slcap2200`, `slcap2500`, `slcap3000`, `slcap3500`, `slcap4000`, `armcap3000`, `armcap2000`, `armcap3500`, `armcap4000`, `armcap4500`, `armcap5000`, `armcap6000`, `mba275_mbb250`, `mba275_mbb260`]; dilute (least-cut): `mba250_mbb275` PF2.839 (dpts -625.8); `etf10_tr200` PF2.858 (dpts -660.2); `etf30_tr200` PF2.858 (dpts -660.2); `armcap4000_tr200` PF2.858 (dpts -660.2); `etf10_hold14` PF2.856 (dpts -801.2); `mba200_mbb275` PF2.758 (dpts -4127.8); worst: `sl800_tp4000` PF2.451 (dpts -61362.6); `sl800_tp4800` PF2.451 (dpts -61362.6); `sl1600_tp6400` PF2.115 (dpts -31702.6); `sl1500_tr220` PF2.183 (dpts -29789.2); `sl1500_tp6000` PF2.196 (dpts -27749.3); `sl1500_tp4800` PF2.196 (dpts -27749.3); `sl2000_tp8000` PF2.046 (dpts -25456.0); `sl1800_tp7200` PF2.108 (dpts -24973.7).
- **Conclusion:** Batch BL finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BK stall (SL/ema_tf/asymm). Best is `etf30_mb260` dpts **+714.6** PF2.880 (under ~2k tick bar; prior mb260 thin pocket). ema_tf / sl_cap / armcap mostly inert (=baseline); SL retunes dilute PF/pts; asymmetric mba260_mbb275 equals thin mb260 pocket. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BM `TREND_EFF_BM_KEEP_CAP800` 5m (plan-F residual denser: trend_efficiency_min / trend_flat_pts / trend_sessions + week2_mode tag|filter compounds + mild near_box D/N denser; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only chase). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.

### 2026-09-27 ~06:55 Europe/Bucharest Asia Batch BM TREND_EFF_BM_KEEP_CAP800 5m (75 cells) - no clear pts lift; skip tick
- **Grid:** 
esults/overnight_5m_grid_20260927T035345Z.json - tag TREND_EFF_BM_KEEP_CAP800 - seed KEEP ticks 20260926T153950Z_d5b5cf17 (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: plan-F residual denser trend_efficiency_min / trend_flat_pts / trend_sessions + week2_mode tag|filter compounds + mild near_box D/N denser; after BL stall. Error cells: none.
- **Baseline 5m KEEP** (KEEP_cap800_baseline): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** thin_bh_mb260 PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**.
- **PF >=~2.5 with pts lift:** thin_bh_mb260.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=[te0p1_w2tag, te0p15_w2tag, te0p2_w2tag, te0p25_w2tag, te0p3_w2tag, te0p35_w2tag, te0p4_w2tag, te0p45_w2tag, te0p5_w2tag, te0p55_w2tag, te0p6_w2tag, tflat500_w2tag, tflat800_w2tag, tflat1000_w2tag, tflat1200_w2tag, tflat1500_w2tag, tflat1800_w2tag, tflat2000_w2tag, tflat2500_w2tag, tflat3000_w2tag, nbars3, nbars4, nbars5, nbars7, nbars8]; dilute (least-cut): te0p6_w2filter PF2.894 (dpts -11414.1); te0p55_w2filter PF2.856 (dpts -15763.0); te0p5_w2filter PF2.779 (dpts -29884.7); tsess20_w2filter PF2.716 (dpts -38659.5); te0p45_w2filter PF2.808 (dpts -39414.3); te0p45_tf2000_w2f PF2.808 (dpts -39414.3); worst: te0p1_w2filter PF2.724 (dpts -96402.0); te0p15_w2filter PF2.689 (dpts -86666.0); tsess4_w2filter PF2.667 (dpts -85651.3); te0p25_tf1000_tsess8_w2f PF2.733 (dpts -79096.6); te0p2_w2filter PF2.739 (dpts -76242.0); te0p2_tf800_w2f PF2.739 (dpts -76242.0); te0p3_tsess8_w2f PF2.763 (dpts -67689.2); te0p25_w2filter PF2.785 (dpts -66832.2).
- **Conclusion:** Batch BM finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BL stall (trend/week2). Best is thin_bh_mb260 dpts **+714.6** PF2.880 (under ~2k tick bar; prior mb260 thin pocket). week2 tag / near_box D/N mostly inert; week2 filter + te/tflat/tsess dilute. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BN SL_MODE_BN_KEEP_CAP800 5m (untried sl_mode asia_opposite/range/m12_frac denser + sl_range_mult / sl_m12_frac / sl_cap compounds with trail ON; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only chase). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.

### 2026-09-27 ~07:16 Europe/Bucharest Asia Batch BN SL_MODE_BN_KEEP_CAP800 5m (50 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T035618Z.json` - tag `SL_MODE_BN_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: sl_mode asia_opposite/range/m12_frac denser + sl_range_mult / sl_m12_frac / sl_cap compounds with trail ON; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only chase; after BM stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft PF>=2.5 by pts:** `thin_bh_mb260` PF2.880 / +228996.5 n229 (dpts **+714.6**, dpf +0.017) â€” under ~2k tick bar; prior mb260 thin pocket. Only soft>=2.5 cell besides baseline.
- **Top by pts (any PF):** thin_bh_mb260 +228996.5 PF2.880; KEEP baseline +228281.9 PF2.863; `sl_range_m2p0_cap4000` +226572.1 PF1.949 (under-floor); `sl_asia_opp_cap4000` +223718.1 PF2.011; `sl_asia_opp_cap1200` +210594.8 PF2.479.
- **Under-floor PF<2:** 19/50 (mostly sl_range/m12 retunes with large caps).
- **Conclusion:** Batch BN finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BM stall (sl_mode). Best is thin_bh_mb260 dpts **+714.6** PF2.880 (under ~2k tick bar). asia_opposite/range/m12_frac + mult/cap compounds dilute PF/pts vs fixed SL1000 KEEP; no fresh champ. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BO `TP_MODE_BO_KEEP_CAP800` 5m (untried residual after A-F+BN stall: tp_mode range_mult/r_mult/m12 denser + tp_range_mult/tp_r_mult + mild fixed TP ladder SL:TP~1:1.5+ trail ON + trail_arm_mode asia/from_fill/off residual + mild armxTP; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only / sl_mode retunes). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.


### 2026-09-27 ~07:41 Europe/Bucharest Asia Batch BO TP_MODE_BO_KEEP_CAP800 5m (58 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T042124Z.json` - tag `TP_MODE_BO_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: tp_mode range_mult/r_mult/m12 denser + mild fixed TP ladder + trail_arm_mode asia/from_fill/off residual; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only / sl_mode retunes; after BN stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `tp_range_m2p0` PF **2.889** / **+229534.2** n229 - dPF **+0.026** - dpts **+1252.3**, `tp_m12` PF **2.871** / **+229231.2** n229 - dPF **+0.008** - dpts **+949.3**, `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**, `tp_range_m2_tr200` PF **2.883** / **+228904.0** n229 - dPF **+0.020** - dpts **+622.1**, `tp_m12_tr200` PF **2.865** / **+228571.0** n229 - dPF **+0.002** - dpts **+289.1**, `tp_m12_hold14` PF **2.865** / **+228557.1** n229 - dPF **+0.002** - dpts **+275.2**.
- **PF >=~2.5 with pts lift:** `tp_range_m2p0`, `tp_m12`, `thin_bh_mb260`, `tp_range_m2_tr200`, `tp_m12_tr200`, `tp_m12_hold14`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** `tp_r1p0` PF1.683/+57935.5, `tp_r1p25` PF1.841/+77229.7.
- **Reject / dilute / inert:** inert=[`tp_r4p0`, `tp_fixed_4200`, `tp_fixed_5400`, `tp_fixed_6000`]; dilute (least-cut): `tp_range_m1p5` PF2.892 (dpts -188.1); `tp_range_m1p5_tr200` PF2.887 (dpts -778.3); `tp_range_m4p0` PF2.854 (dpts -1080.1); `tp_range_m3p0` PF2.852 (dpts -1327.2); `tp_range_m1p5_hold14` PF2.881 (dpts -1542.5); `tp_range_m2p5` PF2.847 (dpts -1975.9); worst: `arm_from_fill` PF4.973 (dpts -193052.4); `arm_from_fill_tp_r2` PF4.973 (dpts -193052.4); `tp_r1p5` PF2.032 (dpts -129453.5); `tp_r1p5_tr200` PF2.032 (dpts -129453.5); `tp_fixed_1500` PF2.032 (dpts -129453.5); `arm_asia_tp_r1p5` PF2.045 (dpts -129229.6); `tp_r1p5_hold14_flat22` PF2.047 (dpts -128998.4); `tp_r1p5_arm3500` PF2.054 (dpts -127329.1).
- **Conclusion:** Batch BO finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BN stall (tp_mode). Best is `tp_range_m2p0` dpts **+1252.3** PF2.889 (under ~2k tick bar; tp_mode thin, not tick-chase). Fixed TP ladder / r_mult tight ratios / arm_from_fill / arm_asia / arm_off dilute or collapse pts (arm_from_fill high PF tiny pts). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BP `ENTRY_ASIA_BP_KEEP_CAP800` 5m (untried residual after A-F+BO stall: min_asia_range denser + ema_period denser + require_close_outside / break_on_wick entry quality + mild otp_off×arange×ema compounds + thin tp_range_m2 sentinel compound with arange/ema only — not mb260/tr140-170). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.


### 2026-09-27 ~08:18 Europe/Bucharest Asia Batch BP ENTRY_ASIA_BP_KEEP_CAP800 5m (56 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T044606Z.json` - tag `ENTRY_ASIA_BP_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: min_asia_range denser + ema_period denser + require_close_outside / break_on_wick entry quality + mild otp_off x arange x ema compounds + thin tp_range_m2 sentinel with arange/ema only; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only; after BO stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `tpm2` PF **2.889** / **+229534.2** n229 - dPF **+0.026** - dpts **+1252.3**, `tpm2_arange350` PF **2.889** / **+229534.2** n229 - dPF **+0.026** - dpts **+1252.3**, `tpm2_rco` PF **2.889** / **+229534.2** n229 - dPF **+0.026** - dpts **+1252.3**, `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**.
- **PF >=~2.5 with pts lift:** `tpm2`, `tpm2_arange350`, `tpm2_rco`, `thin_bh_mb260`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=[`arange150`, `arange200`, `arange225`, `arange275`, `arange250`, `arange300`, `arange325`, `arange400`, `arange350`, `ema31`, `rco_on`, `wick_off`, `rco_arange350`, `wick_off_arange350`, `otp_off`, `otp_off_arange250`, `otp_off_arange400`, `otp_off_rco`, `arange400_ema31`]; dilute (least-cut): `arange350_hold14` PF2.856 (dpts -801.2); `arange350_wait13` PF2.854 (dpts -911.2); `arange450` PF2.840 (dpts -2845.5); `arange500` PF2.840 (dpts -2845.5); `tpm2_ema33` PF2.832 (dpts -3821.1); `tpm2_arange350_ema33` PF2.832 (dpts -3821.1); worst: `rco_wick_off` PF2.568 (dpts -73466.3); `ema40` PF2.139 (dpts -71698.4); `ema45` PF2.157 (dpts -69196.1); `ema37` PF2.226 (dpts -63328.3); `ema23` PF2.459 (dpts -37892.3); `ema35` PF2.510 (dpts -34197.2); `ema28` PF2.510 (dpts -32668.2); `ema27` PF2.514 (dpts -32194.2).
- **Conclusion:** Batch BP finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BO stall (entry/asia). Best is `tpm2` dpts **+1252.3** PF2.889 (under ~2k tick bar; BO tpm2 thin pocket, not tick-chase). arange denser / ema denser dilute; rco/wick/otp mostly inert (=baseline); tpm2 compounds with arange/rco equal BO thin pocket. **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BQ `WAIT_RESUME_BQ_KEEP_CAP800` 5m (untried residual after A-F+BP stall: max_wait denser + resume_closes denser + resume_max_break denser/cap pocket + skip_late denser + use_higher_close off + mild wait x resume compounds + thin tpm2 x wait/resume sentinel; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only / arange-only). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.


### 2026-09-27 ~08:42 Europe/Bucharest Asia Batch BQ WAIT_RESUME_BQ_KEEP_CAP800 5m (79 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T052236Z.json` - tag `WAIT_RESUME_BQ_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: max_wait denser + resume_closes denser + resume_max_break denser/cap pocket + skip_late denser + use_higher_close off + mild wait x resume compounds + thin tpm2 x wait/resume sentinel; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only / arange-only; after BP stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `tpm2` PF **2.889** / **+229534.2** n229 - dPF **+0.026** - dpts **+1252.3**, `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**.
- **PF >=~2.5 with pts lift:** `tpm2`, `thin_bh_mb260`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** `rc1` PF1.762/+118527.1, `wait8` PF1.833/+120991.4.
- **Reject / dilute / inert:** inert=[`wait14`, `rc3`, `rcap800`, `slw3`, `sls2100`]; dilute (least-cut): `slw4` PF2.803 (dpts -93.8); `wait13` PF2.854 (dpts -911.2); `slw5` PF2.750 (dpts -1653.0); `slw1` PF2.877 (dpts -2094.4); `slw2` PF2.830 (dpts -4094.4); `rcap700` PF2.812 (dpts -4439.9); worst: `wait9` PF2.024 (dpts -84469.8); `hc_off_wait16` PF2.218 (dpts -62883.0); `wait16_rc2` PF2.172 (dpts -62276.4); `wait24` PF2.266 (dpts -60572.3); `wait10` PF2.306 (dpts -53951.1); `tpm2_wait12_rc4` PF2.369 (dpts -51420.5); `hc_off_wait12` PF2.351 (dpts -50651.6); `wait12_rc4` PF2.391 (dpts -48489.7).
- **Conclusion:** Batch BQ finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BP stall (wait/resume). Best is `tpm2` dpts **+1252.3** PF2.889 (under ~2k tick bar; BO tpm2 thin pocket, not tick-chase). wait/resume/skip_late denser mostly dilute; hc_off dilute; KEEP wait14/rc3/rcap800/slw3/sls2100 inert (=baseline). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BR `NEARBOX_REQ_BR_KEEP_CAP800` 5m (untried residual after A-F+BQ stall: pullback-required activates dormant near_box recovery + near_box D/N denser + near_box_trend breakout/outside/net_ext/closes_dir + mild wait/otp/hold/flatten compounds + thin tpm2 sentinel; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only / wait-resume retunes). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.


### 2026-09-27 ~09:11 Europe/Bucharest Asia Batch BR NEARBOX_REQ_BR_KEEP_CAP800 5m (64 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T054651Z.json` - tag `NEARBOX_REQ_BR_KEEP_CAP800` - seed KEEP ticks `20260926T153950Z_d5b5cf17` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP4800 wick_on trail arm4000/tr190 flat23 sls3/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.69/+208866.7 n230) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: pullback-required activates dormant near_box recovery + near_box D/N denser + near_box_trend breakout/outside/net_ext/closes_dir + mild wait/otp/hold/flatten compounds + thin tpm2 sentinel; avoid tr140-170 / AS/AQ / maxbreak19 / side-only / mb260-only / wait-resume retunes; after BQ stall. Error cells: none.
- **Baseline 5m KEEP** (`KEEP_cap800_baseline`): n229 - PF **2.863** - **+228281.9**.
- **Soft >=2.0 pts lifts:** `tpm2` PF **2.889** / **+229534.2** n229 - dPF **+0.026** - dpts **+1252.3**, `thin_bh_mb260` PF **2.880** / **+228996.5** n229 - dPF **+0.017** - dpts **+714.6**.
- **PF >=~2.5 with pts lift:** `tpm2`, `thin_bh_mb260`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=[`pref_breakout`, `pref_outside`, `pref_N5_D800`, `pref_N10_D1200`]; dilute (least-cut still huge): `pb_req_D1800` PF2.747 (dpts -47595); `pb_req_D2000` PF2.679 (dpts -49387.1); `pb_req_D1500` PF2.782 (dpts -51058); worst: `pb_req_breakout_wait12` PF2.587 (dpts -83132.8); `pb_req_outside_wait12` PF2.601 (dpts -80279.2); `pb_req_wait12` PF2.546 (dpts -76079.6); `pb_req_closes_dir*` / `pb_req_nb_off` ~dpts -63370.
- **Conclusion:** Batch BR finds **no** clear soft>=2.5 pts refine on KEEP cap800 after BQ stall (nearbox/required). Best is `tpm2` dpts **+1252.3** PF2.889 (under ~2k tick bar; BO thin pocket, not tick-chase). `pullback_mode=required` destroys ~47k–83k pts vs preferred baseline; near_box D/N/trend under required cannot recover. Preferred-mode near_box trend/N/D cells inert (=baseline; near_box still dormant). **Skip tick-confirm**. KEEP unchanged (ticks ema31 cap800 PF2.69/+208866.7 n230).
- **Next:** Batch BS `TPM2_COMPOUND_BS_KEEP_CAP800` 5m (push recurring tpm2 thin +1252 with orthogonal hold/flat/wait/otp/trail-widen/arm/arange/ema/maxbreak compounds to seek dpts>=~2k; avoid mb260 / tr140-170 / pb_req / maxbreak19 / side-only). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. No reaktor / no push.


### 2026-09-27 ~09:53 Europe/Bucharest Asia BS clear → tick kick tpm2_sls4
- **5m clear champs** (Batch BS `TPM2_COMPOUND_BS_KEEP_CAP800`, grid `overnight_5m_grid_20260927T061635Z.json`): `tpm2_sls4` PF2.842 / +231169.0 n235 (dpts **+2887.1**); `tpm2_hold12` PF2.904 / +230539.0 n229 (dpts **+2257.1**) vs 5m KEEP baseline PF2.863/+228281.9.
- **Kicked ticks:** `tpm2_sls4` = KEEP + `tp_mode=range_mult` `tp_range_mult=2.0` `skip_late_short_wait=4` (workers=2, data_source=ticks, window 2025-01→2026-09). Echo OK. Runner `tpm2_hold12` queued after.
- **KEEP unchanged** pending tick: `20260926T153950Z_d5b5cf17` PF2.69/+208866.7 n230.
- **Next:** score BS tick tpm2_sls4 when finished (max_loss streak ≤7–8); then tpm2_hold12 if needed. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~10:20 Europe/Bucharest Asia BS tick tpm2_sls4 → NEW KEEP
- **Tick:** `tpm2_sls4` = prior KEEP + `tp_mode=range_mult` `tp_range_mult=2.0` `skip_late_short_wait=4` — run `20260927T070719Z_f35e5620` — data_source=ticks — window 2025-01→2026-09 — workers=2.
- **Result:** n235 — PF **2.70** — **+212960.2** — win%45.1 — max_loss_streak **8** (max_win 6) — exits {"sl": 124, "tp": 14, "flatten": 34, "trail": 63}.
- **vs KEEP** `20260926T153950Z_d5b5cf17` PF2.69/+208866.7 n230: ΔPF **+0.01** — Δpts **+4093.5** — Δn **+5**.
- **Streak filter:** max_loss=8 (prefer ≤7–8) — PASS at edge.
- **Decision:** **PROMOTE NEW KEEP**.
- **NEW KEEP** (if promoted): asia0-6 · ema31 · wait14 · rc3 · cap800 · flat23 · mb275 · SL1000 / TP range_mult×2 · sls4/2100 · trail arm4000/tr190 · timeout market · wait_from_break · pullback preferred · near_box N6 D1000 trend=off · side both · ticks → PF2.70/+212960.2 n235 (`20260927T070719Z_f35e5620`).
- **Next:** tick-confirm runner `tpm2_hold12` (exact 5m cell: tpm2 + max_hold_hours=12 on prior KEEP base sls3) vs NEW KEEP. Then residual 5m on NEW KEEP. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~10:51 Europe/Bucharest Asia BS runner tick tpm2_hold12 — REJECT vs NEW KEEP
- **Tick:** `tpm2_hold12` = prior KEEP base + `tp_mode=range_mult` `tp_range_mult=2.0` `max_hold_hours=12` (sls3, not compounded with sls4) — run `20260927T073419Z_3be95680` — data_source=ticks — window 2025-01→2026-09 — workers=2.
- **Result:** n230 — PF **2.74** — **+212070.6** — win%45.7 — max_loss_streak **8** (max_win 6) — exits {"tp": 13, "flatten": 33, "sl": 121, "trail": 63}.
- **vs NEW KEEP** `20260927T070719Z_f35e5620` PF2.70/+212960.2 n235: ΔPF **+0.04** — Δpts **-889.6** — Δn **-5**.
- **vs old KEEP** `20260926T153950Z_d5b5cf17` PF2.69/+208866.7 n230: ΔPF **+0.05** — Δpts **+3203.9**.
- **Streak filter:** max_loss=8 (prefer ≤7–8) — PASS at edge.
- **Decision:** **REJECT** — pts down vs NEW KEEP (Δpts -889.6 < ~2k); KEEP stays `tpm2_sls4` PF2.70/+212960.2 n235.
- **KEEP unchanged:** asia0-6 · ema31 · wait14 · rc3 · cap800 · flat23 · mb275 · SL1000 / TP range_mult×2 · sls4/2100 · trail arm4000/tr190 · hold16 · timeout market · wait_from_break · pullback preferred · near_box N6 D1000 trend=off · side both · ticks → PF2.70/+212960.2 n235 (`20260927T070719Z_f35e5620`).
- **Next:** Batch BT `RESIDUAL_BT_NEW_KEEP_TPM2_SLS4` 5m on NEW KEEP seed (tpm2+sls4 baked in): denser hold/flat/wait/trail-widen/arm/otp/arange/ema/maxbreak/sls/rc compounds; avoid tr140-170 / pb_req / maxbreak19 / mb260-only / AS/AQ / hold12-alone retread. Tick-confirm only fresh soft≥2.5 pts lifts (Δpts≥~2k), max_loss streak ≤7–8. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~11:16 Europe/Bucharest Asia Batch BT RESIDUAL_BT_NEW_KEEP_TPM2_SLS4 5m (73 cells) - no clear pts lift; skip tick
- **Grid:** `results/overnight_5m_grid_20260927T075145Z.json` - tag `RESIDUAL_BT_NEW_KEEP_TPM2_SLS4` - seed KEEP ticks `20260927T070719Z_f35e5620` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP range_mult×2 wick_on trail arm4000/tr190 flat23 sls4/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.70/+212960.2 n235) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: denser hold/flat/wait/trail-widen/arm/otp/arange/ema/maxbreak/sls/rc/tpr compounds on NEW KEEP; avoid tr140-170 / pb_req / maxbreak19 / mb260-only / AS/AQ / hold12-alone. Error cells: none.
- **Baseline 5m KEEP** (`NEW_KEEP_tpm2_sls4_baseline`): n235 - PF **2.842** - **+231169.0**.
- **Soft >=2.0 pts lifts:** `tpr2_1` PF **2.854** / **+232701.3** n235 - dPF **+0.012** - dpts **+1532.3**, `tpr2_25` PF **2.853** / **+232608.0** n235 - dPF **+0.011** - dpts **+1439.0**, `sls5` PF **2.822** / **+232369.1** n239 - dPF **-0.020** - dpts **+1200.1**, `otp_off_sls5` PF **2.822** / **+232369.1** n239 - dPF **-0.020** - dpts **+1200.1**, `tpr2_1_tr200` PF **2.849** / **+232061.1** n235 - dPF **+0.007** - dpts **+892.1**, `flat22` PF **2.860** / **+231236.8** n235 - dPF **+0.018** - dpts **+67.8**, `otp_off_flat22` PF **2.860** / **+231236.8** n235 - dPF **+0.018** - dpts **+67.8**, `hold18_flat22` PF **2.860** / **+231236.8** n235 - dPF **+0.018** - dpts **+67.8**.
- **PF >=~2.5 with pts lift:** `tpr2_1`, `tpr2_25`, `sls5`, `otp_off_sls5`, `tpr2_1_tr200`, `flat22`, `otp_off_flat22`, `hold18_flat22`.
- **Clear dpts>=~2k at PF>=2.5:** **none**.
- **Under-floor PF<2.0:** `be_arm500` PF1.171/+9892.9.
- **Reject / dilute / inert:** inert=[`hold17`, `hold18`, `hold20`, `otp_off`, `arange250`, `arange280`, `arange350`, `arange400`]; dilute (least-cut): `hold15` PF2.843 (dpts -251.1), `sls5_hold14` PF2.809 (dpts -405.5), `otp_off_tr200` PF2.836 (dpts -630.2), `tr200` PF2.836 (dpts -630.2), `hold13` PF2.843 (dpts -647.3); worst: `be_arm500` PF1.171 (dpts -221276.1), `be_arm1000` PF2.137 (dpts -131338.0), `rc2` PF2.292 (dpts -46925.4), `arm3200` PF2.500 (dpts -42895.6), `rc5` PF2.503 (dpts -35858.2), `wait12` PF2.499 (dpts -35632.5), `rc4` PF2.530 (dpts -34163.8), `arm5000` PF2.450 (dpts -33155.3).
- **Conclusion:** Batch BT finds **no** clear soft>=2.5 pts refine on NEW KEEP tpm2+sls4. Best is `tpr2_1` dpts **+1532.3** PF2.854 (under ~2k tick bar). be_arm destroys; arm/rc/wait/ema mostly dilute; hold/arange/otp mostly inert. **Skip tick-confirm**. KEEP unchanged (ticks tpm2+sls4 PF2.70/+212960.2 n235).
- **Next:** Batch BU `TPR_COMPOUND_BU_NEW_KEEP_TPM2_SLS4` 5m (push recurring tpr2_1/tpr2_25/sls5 thin with orthogonal hold/flat/trail/sls/otp/wait/mb/ema compounds to seek dpts>=~2k; thin plan-F seasonal/week2/news/side/timeout sentinels on NEW KEEP; avoid tr140-170 / pb_req / maxbreak19 / mb260-only / be_arm / hold12-alone / full BK timeout retread). Tick-confirm only fresh soft>=2.5 pts lifts (dpts>=~2k) with max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~11:43 Europe/Bucharest Asia Batch BU TPR_COMPOUND_BU_NEW_KEEP_TPM2_SLS4 5m (65 cells) - clear dpts>=~2k; tick-confirm champ
- **Grid:** `results/overnight_5m_grid_20260927T081726Z.json` - tag `TPR_COMPOUND_BU_NEW_KEEP_TPM2_SLS4` - seed KEEP ticks `20260927T070719Z_f35e5620` (asia0-6 ema31 mb275 prefer near_box N6 D1000 trend=off SL1000/TP range_mult×2 wick_on trail arm4000/tr190 flat23 sls4/2100 maxbreak15 rc3 cap800 wait14 hold16 PF2.70/+212960.2 n235) - candles_5m - workers=2 - window 2025-01 to 2026-09. Axes: denser tp_range around 2.1 + tpr2_1/tpr2_25/sls5 orthogonal hold/flat/trail/otp/wait/mb/ema compounds; thin plan-F seasonal/week2/news/side/timeout sentinels. Error cells: none.
- **Baseline 5m KEEP** (`NEW_KEEP_tpm2_sls4_baseline`): n235 - PF **2.842** - **+231169.0**.
- **Soft >=2.0 pts lifts (top):** `tpr2_25_sls5` PF **2.835** / **+234028.0** n239 - dPF **-0.007** - dpts **+2859.0**, `tpr2_1_sls5` PF **2.835** / **+233989.4** n239 - dPF **-0.007** - dpts **+2820.4**, `tpr2_1_otp_off_sls5` PF **2.835** / **+233989.4** n239 - dPF **-0.007** - dpts **+2820.4**, `tpr2_1_sls5_flat22` PF **2.852** / **+233938.1** n239 - dPF **+0.010** - dpts **+2769.1**, `tpr2_4` PF **2.855** / **+232845.1** n235 - dPF **+0.013** - dpts **+1676.1**, `tpr2_25_flat22` PF **2.873** / **+232798.9** n235 - dPF **+0.031** - dpts **+1629.9**, `tpr2_1_flat22` PF **2.873** / **+232769.1** n235 - dPF **+0.031** - dpts **+1600.1**, `tpr2_1` PF **2.854** / **+232701.3** n235 - dPF **+0.012** - dpts **+1532.3**.
- **Clear dpts>=~2k at PF>=2.5:** `tpr2_25_sls5` PF **2.835** / **+234028.0** n239 - dPF **-0.007** - dpts **+2859.0**, `tpr2_1_sls5` PF **2.835** / **+233989.4** n239 - dPF **-0.007** - dpts **+2820.4**, `tpr2_1_otp_off_sls5` PF **2.835** / **+233989.4** n239 - dPF **-0.007** - dpts **+2820.4**, `tpr2_1_sls5_flat22` PF **2.852** / **+233938.1** n239 - dPF **+0.010** - dpts **+2769.1**.
- **Under-floor PF<2.0:** none.
- **Reject / dilute / inert:** inert=[`season_tag`, `week2_tag`, `news_tag_sched`, `tminbreak250`, `ematf5`, `ematf10`, `ematf30`, `wick_off`, `rco_on`]; dilute (worst): `side_long` PF2.220 (dpts -134962.7), `tpr2_1_side_long` PF2.235 (dpts -133751.1), `side_short` PF3.893 (dpts -96206.3), `tpr2_1_side_short` PF3.900 (dpts -95885.6), `week2_filter` PF2.650 (dpts -60423.0), `temd1000` PF2.676 (dpts -35862.8), `tpr2_1_temd1000` PF2.689 (dpts -34330.5), `tpr2_1_wait15` PF2.608 (dpts -24669.8).
- **Side diagnostic:** `tpr2_1_side_short` PF3.900/+135283.4 n95; `side_short` PF3.893/+134962.7 n95; `tpr2_1_side_long` PF2.235/+97417.9 n140; `side_long` PF2.220/+96206.3 n140; (prefer combined for total pts).
- **Conclusion:** Batch BU unlocks clear soft>=2.5 pts compounds on NEW KEEP via **tpr×sls5**. Champ `tpr2_25_sls5` (tp_range_mult=2.25, skip_late_short_wait=5) dpts **+2859.0** PF2.835. Runner `tpr2_1_sls5_flat22` slightly better PF. Plan-F filters mostly cut pts; side-split shorts strong / longs weak — keep combined.
- **KEEP unchanged pending tick:** ticks tpm2+sls4 PF2.70/+212960.2 n235 (`20260927T070719Z_f35e5620`).
- **Next:** overnight **tick-confirm** `BU_tick tpr2_25_sls5` (KEEP + tp_range_mult=2.25 + skip_late_short_wait=5) workers=2. If reject → tick runner `tpr2_1_sls5` or `tpr2_1_sls5_flat22`; else promote if pts lift + PF>=~2.5 + max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.



### 2026-09-27 ~12:12 Europe/Bucharest Asia BU_tick tpr2_25_sls5 -> NEW KEEP
- **Tick:** `tpr2_25_sls5` = prior KEEP + `tp_mode=range_mult` `tp_range_mult=2.25` `skip_late_short_wait=5` - run `20260927T090050Z_65ffdcc2` - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n239 - PF **2.69** - **+215812.6** - win%45.2 - max_loss_streak **8** (max_win 6) - exits {"flatten":36,"sl":126,"tp":13,"trail":64}.
- **vs KEEP** `20260927T070719Z_f35e5620` PF2.70/+212960.2 n235: dPF **-0.01** - dpts **+2852.4** - dn **+4**.
- **Streak filter:** max_loss=8 (prefer <=7-8) - PASS at edge.
- **Decision:** **PROMOTE NEW KEEP**.
- **NEW KEEP** (promoted): asia0-6 · ema31 · wait14 · rc3 · cap800 · flat23 · mb275 · SL1000 / TP range_mult×2.25 · sls5/2100 · trail arm4000/tr190 · hold16 · timeout market · wait_from_break · pullback preferred · near_box N6 D1000 trend=off · side both · ticks -> PF2.69/+215812.6 n239 (`20260927T090050Z_65ffdcc2`).
- **Next:** tick-confirm runner `tpr2_1_sls5` (tp_range_mult=2.1 + skip_late_short_wait=5 on prior KEEP base; vs NEW KEEP). Then `tpr2_1_sls5_flat22` if needed; else residual 5m on NEW KEEP. stop_auto_tick=FALSE. No reaktor / no push.



### 2026-09-27 ~12:43 Europe/Bucharest Asia BU_runner tick tpr2_1_sls5 - REJECT vs NEW KEEP
- **Tick:** 	pr2_1_sls5 = NEW KEEP base + 	p_range_mult=2.1 skip_late_short_wait=5 (flat23) - run 20260927T092843Z_953a2d35 - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n239 - PF **2.69** - **+215842.7** - win%45.2 - max_loss_streak **8** (max_win 6) - exits {"flatten":35,"sl":126,"tp":15,"trail":63}.
- **vs NEW KEEP** 20260927T090050Z_65ffdcc2 PF2.69/+215812.6 n239: dPF **+0.00** - dpts **+30.1** - dn **+0**.
- **Streak filter:** max_loss=8 (prefer <=7-8) - PASS at edge.
- **Decision:** **REJECT** - dpts +30.1 is noise under ~2k pts bar (5m overpromised tpr2.1 vs tpr2.25).
- **KEEP unchanged:** asia0-6 / ema31 / wait14 / rc3 / cap800 / flat23 / mb275 / SL1000 / TP range_multx2.25 / sls5/2100 / trail arm4000/tr190 / hold16 / timeout market / wait_from_break / pullback preferred / near_box N6 D1000 trend=off / side both / ticks -> PF2.69/+215812.6 n239 (20260927T090050Z_65ffdcc2).
- **Next:** tick-confirm runner 	pr2_1_sls5_flat22 (tp_range_mult=2.1 + sls5 + flatten_hour=22; 5m PF2.852/+233938 dpts+2769). If reject/no lift -> Batch BV residual 5m on NEW KEEP. stop_auto_tick=FALSE. No reaktor / no push.



### 2026-09-27 ~13:22 Europe/Bucharest Asia BU_runner tick tpr2_1_sls5_flat22 - REJECT vs NEW KEEP
- **Tick:** tpr2_1_sls5_flat22 = NEW KEEP base + tp_range_mult=2.1 + skip_late_short_wait=5 + flatten_hour=22 - run `20260927T095958Z_b7f4aec0` - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n239 - PF **2.71** - **+215944.3** - win%45.6 - max_loss_streak **8** (max_win 6) - exits {'flatten': 36, 'sl': 125, 'tp': 15, 'trail': 63}.
- **vs NEW KEEP** `20260927T090050Z_65ffdcc2` PF2.69/+215812.6 n239: dPF **+0.02** - dpts **+131.7** - dn **+0**.
- **Streak filter:** max_loss=8 (prefer <=7-8) - PASS at edge.
- **Decision:** **REJECT** - dpts +131.7 is noise under ~2k pts bar (5m overpromised flat22 compound vs KEEP tpr2.25).
- **KEEP unchanged:** asia0-6 / ema31 / wait14 / rc3 / cap800 / flat23 / mb275 / SL1000 / TP range_multx2.25 / sls5/2100 / trail arm4000/tr190 / hold16 / timeout market / wait_from_break / pullback preferred / near_box N6 D1000 trend=off / PF2.69/+215812.6 n239 (`20260927T090050Z_65ffdcc2`).
- **Next:** Batch BV `RESIDUAL_BV_NEW_KEEP_TPR225_SLS5` 5m on NEW KEEP seed (tpr2.25+sls5 baked in): denser hold/flat/wait/trail-widen/arm/otp/arange/ema/maxbreak/sls/rc/tpr-around-2.25/mb; avoid tr140-170 / pb_req / maxbreak19 / mb260 / be_arm / tpr2_1_sls5_flat22 retread. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~13:46 Europe/Bucharest Asia Batch BV RESIDUAL_BV_NEW_KEEP_TPR225_SLS5 5m — no clear pts lift (skip tick)
- **Grid:** `results/overnight_5m_grid_20260927T102253Z.json` — tag `RESIDUAL_BV_NEW_KEEP_TPR225_SLS5` — seed KEEP ticks `20260927T090050Z_65ffdcc2` (asia0-6 ema31 wait14 rc3 cap800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) — candles_5m — workers=2 — window 2025-01 to 2026-09 — 97 cells (1 error: flat24 hour must be in 0..23).
- **Baseline 5m KEEP** (`NEW_KEEP_tpr225_sls5_baseline`): n239 — PF **2.835** — **+234028.0**.
- **Top by pts vs baseline:**
  - `hold12`: PF **2.845** / **+234539.8** n239 — dPF **+0.010** — dpts **+511.8**
  - `tpr2_4`: PF **2.838** / **+234397.1** n239 — dPF **+0.003** — dpts **+369.1**
  - `tpr2_4_flat22`: PF **2.856** / **+234359.2** n239 — dPF **+0.021** — dpts **+331.2**
  - `flat22`: PF **2.854** / **+234099.8** n239 — dPF **+0.019** — dpts **+71.8**
  - `otp_off_flat22`: PF **2.854** / **+234099.8** n239 — dPF **+0.019** — dpts **+71.8**
- **Soft >=2.5 with pts lift:** hold12 / tpr2_4 / tpr2_4_flat22 / flat22 family — all dpts **under ~2k** tick bar (best hold12 **+511.8**).
- **Dilute / reject notes:** wait11/12 and arm3200-3500 / arm5000 / rc2 / hc_off / side_long cut PF or pts hard; side_short PF3.771/+134.8k thin n99 (prefer combined); season/week2/news tag inert (=baseline).
- **Conclusion:** Batch BV finds **no** clear soft>=2.5 pts refine on NEW KEEP tpr2.25+sls5 after BU_runner reject. Best 5m lift hold12 dpts **+511.8** PF2.845 — skip tick-confirm. KEEP unchanged (ticks PF2.69/+215812.6 n239 `20260927T090050Z_65ffdcc2`).
- **Next:** Batch BW `RESIDUAL_BW_NEARBOX_TP_ASIA_NEW_KEEP` 5m — near_box N/D/trend gates, asia start/end denser, pullback/rco/wick, TP-fixed + trail-near-TP arms, SL:TP ~1:1.5 fixed pairs, sl_cap/range_mult, timeout denser, season/week2/news **filter** (not tag), be_arm mild; avoid BV retreads. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.
### 2026-09-27 ~18:21 Europe/Bucharest Asia Batch BW RESIDUAL_BW_NEARBOX_TP_ASIA_NEW_KEEP 5m - no soft pts lift (skip tick)
- **Grid:** 
esults/overnight_5m_grid_20260927T104744Z.json - tag RESIDUAL_BW_NEARBOX_TP_ASIA_NEW_KEEP - seed KEEP ticks 20260927T090050Z_65ffdcc2 (asia0-6 ema31 wait14 rc3 cap800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) - candles_5m - workers=2 - window 2025-01 to 2026-09 - 91 cells (0 errors). Scored after Lenovo reconnect (offline streak cleared).
- **Baseline 5m KEEP** (NEW_KEEP_baseline): n239 - PF **2.835** - **+234028.0**.
- **CLEAR dpts>=~2k at PF>=2.5:** none.
- **Soft >=2.5 with pts lift:** none (0 cells with dpts>0).
- **Inert (=baseline, 31 cells):** near_box N/D/trend family (incl. nb_off) - confirms near-box dormant under preferred; rco_on; wick_off; slcap1200-2500; tminbreak150/200.
- **Best PF-up / pts-down (reject for pts goal):** season_filter PF **2.951** / **+211778.9** n206 - dPF **+0.116** - dpts **-22249.1**; 
ews_filter_sched PF **2.890** / **+208952.0** n212 - dpts **-25076.0**; 	emd2000 PF **2.857** / **+229356.6** n233 - dpts **-4671.4**.
- **Hard rejects:** fixed SL:TP ~1:1.5 pairs and fixed-TP / trail-near-TP arms cut pts hard (best fixed TP still dpts <=-7.4k); asia0_4/0_5/0_7/1_5/2_6 and pb_off/wfb_off/be_arm dilute; week2_filter dpts **-59771.8**.
- **Conclusion:** Batch BW finds **no** soft>=2.5 pts refine on NEW KEEP after BV stall. Near-box / asia denser / TP-fixed / SL:TP-fixed / filter-skip axes do not lift total points. KEEP unchanged (ticks PF2.69/+215812.6 n239 20260927T090050Z_65ffdcc2).
- **Next:** Batch BX PLANF_RESIDUAL_BX_NEW_KEEP_TPR225_SLS5 5m - denser plan-F seasonal/week2/news tag|filter|join + timeout compounds + trend_eff/sessions/flat + ema_tf + resume + hold19-22/flatten expand + tp_r_mult + mild mb volume; avoid BW near-box/TP-fixed/SL-pair retreads and BV hold12-20/tr/arm pocket. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~18:46 Europe/Bucharest Asia Batch BX PLANF_RESIDUAL_BX_NEW_KEEP_TPR225_SLS5 5m — no clear soft pts lift (skip tick)
- **Grid:** `results/overnight_5m_grid_20260927T152846Z.json` — tag `PLANF_RESIDUAL_BX_NEW_KEEP_TPR225_SLS5` — seed KEEP ticks `20260927T090050Z_65ffdcc2` (asia0-6 ema31 wait14 rc3 cap800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) — candles_5m — workers=2 — window 2025-01 to 2026-09 — 140 cells (0 errors). Finished ~15:30Z; scored after Lenovo reconnect (offline streak cleared).
- **Baseline 5m KEEP** (`NEW_KEEP_baseline`): n239 — PF **2.835** — **+234028.0**.
- **CLEAR dpts>=~2k at PF>=2.5:** none.
- **Soft >=2.5 with pts lift (3 cells, all under ~2k tick bar):**
  - `temd2000_wait13`: PF **2.933** / **+235088.9** n233 — dPF **+0.098** — dpts **+1060.9**
  - `tr180`: PF **2.840** / **+234667.8** n239 — dPF **+0.005** — dpts **+639.8**
  - `hold22_flat22`: PF **2.854** / **+234099.8** n239 — dPF **+0.019** — dpts **+71.8**
- **Inert (=baseline, 44 cells):** season/week2/news **tag** family; tminbreak50/100/250; teff/tsess/tflat family; ematf5/10/30/60; hold19/21/22/24; otp_off_hold19/21; armcap1800/2500.
- **Best PF-up / pts-down (reject for pts goal):**
  - `armmode_from_fill`: PF **4.736** / **+34947.7** n239 — dPF **+1.901** — dpts **-199080.3**
  - `armmode_from_fill_tr200`: PF **4.303** / **+33283.6** n239 — dPF **+1.468** — dpts **-200744.4**
  - `side_short`: PF **3.771** / **+134792.8** n99 — dPF **+0.936** — dpts **-99235.2**
  - `season_filter`: PF **2.951** / **+211778.9** n206 — dPF **+0.116** — dpts **-22249.1**
  - `season_filter_week2_tag`: PF **2.951** / **+211778.9** n206 — dPF **+0.116** — dpts **-22249.1**
- **Hard rejects:** trail_arm_mode from_fill / asia cut pts hard (~-67k to -200k) despite high PF; tpr1.5–2.5 and rc1/side_long dilute; side_short thin PF3.771/+134.8k n99 (prefer combined); season/news **filter** trade PF for pts (−22k/−25k).
- **Conclusion:** Batch BX finds **no** clear soft>=2.5 pts refine on NEW KEEP after BW stall. Plan-F denser + timeout/trend/ema_tf/resume/hold-flat/tp_r/mb axes do not clear the ~2k pts bar (best `temd2000_wait13` dpts **+1060.9** PF2.933). KEEP unchanged (ticks PF2.69/+215812.6 n239 `20260927T090050Z_65ffdcc2`).
- **Next:** Batch BY `COMPOUND_BY_THIN_SOFT_NEW_KEEP` 5m — compound thin soft pocket (`temd2000`×wait13×tr180×hold22_flat22) + untried residual on this seed: asymmetric min_break, max_break denser, skip_late_short denser, otp_off compounds with soft pocket, mild mb 250/300 around KEEP, resume denser; avoid BX arm_mode/tpr-under-2.25/side-only and BW near-box/TP-fixed/SL-pair retreads. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~21:54 Europe/Bucharest Asia Batch BY COMPOUND_BY_THIN_SOFT_NEW_KEEP 5m — CLEAR pts lifts → tick kick
- **Grid:** `results/overnight_5m_grid_20260927T154742Z.json` — tag `COMPOUND_BY_THIN_SOFT_NEW_KEEP` — seed KEEP ticks `20260927T090050Z_65ffdcc2` (asia0-6 ema31 wait14 rc3 rmb800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) — candles_5m — workers=2 — window 2025-01 to 2026-09 — 80 cells (0 errors).
- **Baseline 5m KEEP** (`NEW_KEEP_baseline`): n239 — PF **2.835** — **+234028.0**.
- **Top by pts vs baseline:**
  - `temd1800_wait13_tr180`: PF **2.962** / **+236698.7** n232 — dPF **+0.127** — dpts **+2670.7**
  - `temd2000_wait13_tr170`: PF **2.943** / **+236309.0** n233 — dPF **+0.108** — dpts **+2281.0**
  - `tr175_temd2000_wait13`: PF **2.940** / **+236003.7** n233 — dPF **+0.105** — dpts **+1975.7**
  - `temd2000_wait13_tr180`: PF **2.938** / **+235698.7** n233 — dPF **+0.103** — dpts **+1670.7**
  - `temd2000_wait13_tr180_otp_off`: PF **2.938** / **+235698.7** n233 — dPF **+0.103** — dpts **+1670.7**
  - `tr182_temd2000_wait13`: PF **2.937** / **+235576.9** n233 — dPF **+0.102** — dpts **+1548.9**
  - `temd2000_wait13_tr185`: PF **2.935** / **+235393.7** n233 — dPF **+0.100** — dpts **+1365.7**
  - `tr188_temd2000_wait13`: PF **2.934** / **+235210.7** n233 — dPF **+0.099** — dpts **+1182.7**
- **CLEAR dpts>=~2k at PF>=2.5:**
  - `temd1800_wait13_tr180`: PF **2.962** / **+236698.7** n232 — dPF **+0.127** — dpts **+2670.7**
  - `temd2000_wait13_tr170`: PF **2.943** / **+236309.0** n233 — dPF **+0.108** — dpts **+2281.0**
- **Soft >=2.5 with pts lift (under/at tick bar):** `temd1800_wait13_tr180`, `temd2000_wait13_tr170`, `tr175_temd2000_wait13`, `temd2000_wait13_tr180`, `temd2000_wait13_tr180_otp_off`, `tr182_temd2000_wait13`, `temd2000_wait13_tr185`, `tr188_temd2000_wait13`, `temd2000_wait13`, `rc3_rmb800_temd2000_wait13` (soft count 24).
- **Under-floor PF<2.0:** 0.
- **Inert (=baseline) count:** 3.
- **Conclusion:** Batch BY compounds BX thin soft pocket (temd x wait13 x tr~180) and clears the ~2k pts bar on 5m. Champ `temd1800_wait13_tr180` dpts **+2670.7** PF2.962; runner `temd2000_wait13_tr170` dpts **+2281.0** PF2.943. KEEP unchanged pending tick (`20260927T090050Z_65ffdcc2` PF2.69/+215812.6 n239).
- **Note:** overnight API also had loaded stray 5m `20260927T155922Z_bffa99d4` (fixed TP4000 / trail_arm off / sls3 / not KEEP seed) PF2.68/+206392 n229 — **ignore** (not a KEEP candidate).
- **Next:** tick-confirm champ `temd1800_wait13_tr180` (timeout_max_ema_dist_pts=1800, max_wait_candles=13, trail_pts=180) on KEEP seed; then runner `temd2000_wait13_tr170` if needed. max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.


### 2026-09-27 ~22:16 Europe/Bucharest Asia BY_tick temd1800_wait13_tr180 - REJECT vs NEW KEEP
- **Tick:** `temd1800_wait13_tr180` = KEEP + `timeout_max_ema_dist_pts=1800` `max_wait_candles=13` `trail_pts=180` - run `20260927T190817Z_6cb9b76d` - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n232 - PF **2.78** - **+214810.0** - win%46.6 - max_loss_streak **6** (max_win 7) - exits {"flatten":39,"sl":119,"tp":13,"trail":61}.
- **vs NEW KEEP** `20260927T090050Z_65ffdcc2` PF2.69/+215812.6 n239: dPF **+0.09** - dpts **-1002.6** - dn **-7**.
- **Streak filter:** max_loss=6 (prefer <=7-8) - PASS.
- **Decision:** **REJECT** - dpts -1002.6 under ~2k pts bar (5m overpromised dpts+2670); PF lift alone does not promote when total points fall.
- **KEEP unchanged:** asia0-6 / ema31 / wait14 / rc3 / cap800 / flat23 / mb275 / SL1000 / TP range_multx2.25 / sls5/2100 / trail arm4000/tr190 / hold16 / timeout market / wait_from_break / pullback preferred / near_box N6 D1000 trend=off / side both / ticks -> PF2.69/+215812.6 n239 (`20260927T090050Z_65ffdcc2`).
- **Next:** tick-confirm runner `temd2000_wait13_tr170` (timeout_max_ema_dist_pts=2000, max_wait_candles=13, trail_pts=170) on KEEP seed. If reject -> Batch BZ residual/compound on untried soft pocket (tr175/tr182/temd2000_wait13_tr180 family under ~2k + asymmetric mb / max_break denser). max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.

### 2026-09-27 ~22:44 Europe/Bucharest Asia BY_runner tick temd2000_wait13_tr170 - REJECT vs NEW KEEP
- **Tick:** `temd2000_wait13_tr170` = KEEP + `timeout_max_ema_dist_pts=2000` `max_wait_candles=13` `trail_pts=170` - run `20260927T193059Z_5f697dbd` - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n233 - PF **2.76** - **+213519.6** - win%46.4 - max_loss_streak **6** (max_win 7) - exits {"flatten":39,"sl":120,"tp":13,"trail":61}.
- **vs NEW KEEP** `20260927T090050Z_65ffdcc2` PF2.69/+215812.6 n239: dPF **+0.07** - dpts **-2293.0** - dn **-6**.
- **Streak filter:** max_loss=6 (prefer <=7-8) - PASS.
- **Decision:** **REJECT** - dpts -2293 under ~2k pts bar (5m overpromised dpts+2281); both BY clear 5m champs (temd1800_wait13_tr180 and this runner) lost points on ticks despite PF lift.
- **KEEP unchanged:** asia0-6 / ema31 / wait14 / rc3 / cap800 / flat23 / mb275 / SL1000 / TP range_multx2.25 / sls5/2100 / trail arm4000/tr190 / hold16 / timeout market / wait_from_break / pullback preferred / near_box N6 D1000 trend=off / side both / ticks -> PF2.69/+215812.6 n239 (`20260927T090050Z_65ffdcc2`).
- **Next:** Batch BZ `COMPOUND_BZ_SOFT_NEAR2K_NEW_KEEP` 5m — denser compounds around soft under-~2k pocket (`tr175`/`tr182`/`temd2000_wait13_tr180`/`tr185`/`tr188` × mild temd 1900–2100 × wait13–14 × hold/flat/arm/ema/rc) + untried trail_arm mild + ema denser; avoid retread of rejected ticks temd1800_tr180 / temd2000_tr170 and BY mb/maxbreak/sls singles already screened. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.

### 2026-09-27 ~23:20 Europe/Bucharest Asia Batch BZ COMPOUND_BZ_SOFT_NEAR2K_NEW_KEEP 5m - CLEAR pts lifts -> tick kick
- **Grid:** 
esults/overnight_5m_grid_20260927T194757Z.json - tag COMPOUND_BZ_SOFT_NEAR2K_NEW_KEEP - seed KEEP ticks 20260927T090050Z_65ffdcc2 (asia0-6 ema31 wait14 rc3 rmb800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) - candles_5m - workers=2 - window 2025-01 to 2026-09 - 84 cells (0 errors).
- **Baseline 5m KEEP** (NEW_KEEP_baseline): n239 - PF **2.835** - **+234028.0**.
- **Top by pts vs baseline:**
  - tr172_temd1900_wait13: PF **2.966** / **+237186.8** n232 - dPF **+0.131** - dpts **+3158.8**
  - tr174_temd1900_wait13: PF **2.965** / **+237065.0** n232 - dPF **+0.130** - dpts **+3037.0**
  - tr175_temd1900_wait13: PF **2.965** / **+237003.7** n232 - dPF **+0.130** - dpts **+2975.7**
  - tr176_temd1900_wait13: PF **2.964** / **+236942.7** n232 - dPF **+0.129** - dpts **+2914.7**
  - tr178_temd1900_wait13: PF **2.963** / **+236820.9** n232 - dPF **+0.128** - dpts **+2792.9**
  - tr180_temd1900_wait13: PF **2.962** / **+236698.7** n232 - dPF **+0.127** - dpts **+2670.7**
  - tr182_temd1900_wait13: PF **2.961** / **+236576.9** n232 - dPF **+0.126** - dpts **+2548.9**
  - tr183_temd1900_wait13: PF **2.961** / **+236515.8** n232 - dPF **+0.126** - dpts **+2487.8**
- **CLEAR dpts>=~2k at PF>=2.5:**
  - tr172_temd1900_wait13: PF **2.966** / **+237186.8** n232 - dPF **+0.131** - dpts **+3158.8**
  - tr174_temd1900_wait13: PF **2.965** / **+237065.0** n232 - dPF **+0.130** - dpts **+3037.0**
  - tr175_temd1900_wait13: PF **2.965** / **+237003.7** n232 - dPF **+0.130** - dpts **+2975.7**
  - tr176_temd1900_wait13: PF **2.964** / **+236942.7** n232 - dPF **+0.129** - dpts **+2914.7**
  - tr178_temd1900_wait13: PF **2.963** / **+236820.9** n232 - dPF **+0.128** - dpts **+2792.9**
  - tr180_temd1900_wait13: PF **2.962** / **+236698.7** n232 - dPF **+0.127** - dpts **+2670.7**
  - tr182_temd1900_wait13: PF **2.961** / **+236576.9** n232 - dPF **+0.126** - dpts **+2548.9**
  - tr183_temd1900_wait13: PF **2.961** / **+236515.8** n232 - dPF **+0.126** - dpts **+2487.8**
  - tr185_temd1900_wait13: PF **2.960** / **+236393.7** n232 - dPF **+0.125** - dpts **+2365.7**
  - tpr2_4_tr175_temd2000_wait13: PF **2.944** / **+236387.8** n233 - dPF **+0.109** - dpts **+2359.8**
  - tr186_temd1900_wait13: PF **2.959** / **+236332.9** n232 - dPF **+0.124** - dpts **+2304.9**
  - tr172_temd2000_wait13: PF **2.942** / **+236186.8** n233 - dPF **+0.107** - dpts **+2158.8**
  - tr172_temd2100_wait13: PF **2.942** / **+236186.8** n233 - dPF **+0.107** - dpts **+2158.8**
  - tpr2_4_tr180_temd2000_wait13: PF **2.941** / **+236077.8** n233 - dPF **+0.106** - dpts **+2049.8**
  - tr174_temd2000_wait13: PF **2.941** / **+236065.0** n233 - dPF **+0.106** - dpts **+2037.0**
  - tr174_temd2100_wait13: PF **2.941** / **+236065.0** n233 - dPF **+0.106** - dpts **+2037.0**
- **Soft >=2.5 with pts lift (under/at tick bar sample):** tr172_temd1900_wait13, tr174_temd1900_wait13, tr175_temd1900_wait13, tr176_temd1900_wait13, tr178_temd1900_wait13, tr180_temd1900_wait13, tr182_temd1900_wait13, tr183_temd1900_wait13, tr185_temd1900_wait13, tpr2_4_tr175_temd2000_wait13, tr186_temd1900_wait13, tr172_temd2000_wait13 (soft count 56).
- **Under-floor PF<2.0:** 0.
- **Inert (=baseline) count:** 0.
- **Best PF-up / pts-down (reject for pts goal sample):**
  - hc_off_tr175_temd2000_wait13: PF **2.603** / **+201373.5** n233 - dpts **-32654.5**
  - arm4500_tr180_temd2000_wait13: PF **2.600** / **+205849.7** n233 - dpts **-28178.3**
  - arm4500_tr175_temd2000_wait13: PF **2.602** / **+206079.7** n233 - dpts **-27948.3**
  - arm3500_tr180_temd2000_wait13: PF **2.759** / **+212154.6** n233 - dpts **-21873.4**
  - arm3500_tr175_temd2000_wait13: PF **2.762** / **+212509.6** n233 - dpts **-21518.4**
  - ema29_tr180_temd2000_wait13: PF **2.720** / **+216047.1** n233 - dpts **-17980.9**
- **Conclusion:** Batch BZ densifies BY soft under-~2k pocket (tr~172-188 x temd1900/2000/2100 x wait13) after both BY clear ticks REJECT. Champ 	r172_temd1900_wait13 dpts **+3158.8** PF2.966; temd1900 ladder dominates clears. KEEP unchanged pending tick (20260927T090050Z_65ffdcc2 PF2.69/+215812.6 n239).
- **Next:** tick-confirm champ 	r172_temd1900_wait13 (trail_pts=172, timeout_max_ema_dist_pts=1900, max_wait_candles=13) on KEEP seed; then runner 	r174_temd1900_wait13 if needed. Avoid retread of rejected BY ticks temd1800_tr180 / temd2000_tr170. max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.



### 2026-09-27 ~23:50 Europe/Bucharest Asia BZ_tick tr172_temd1900_wait13 - REJECT vs NEW KEEP
- **Tick:** `tr172_temd1900_wait13` = KEEP + `trail_pts=172` `timeout_max_ema_dist_pts=1900` `max_wait_candles=13` - run `20260927T203646Z_ff446762` - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n232 - PF **2.78** - **+214397.2** - win%46.6 - max_loss_streak **6** (max_win 7) - exits {"flatten":39,"sl":119,"tp":13,"trail":61}.
- **vs NEW KEEP** `20260927T090050Z_65ffdcc2` PF2.69/+215812.6 n239: dPF **+0.09** - dpts **-1415.4** - dn **-7**.
- **Streak filter:** max_loss=6 (prefer <=7-8) - PASS.
- **Decision:** **REJECT** - dpts -1415.4 under ~2k pts bar (5m overpromised dpts+3158.8); PF lift alone does not promote when total points fall. Same tick-vs-5m pattern as BY champ/runner rejects.
- **KEEP unchanged:** asia0-6 / ema31 / wait14 / rc3 / cap800 / flat23 / mb275 / SL1000 / TP range_multx2.25 / sls5/2100 / trail arm4000/tr190 / hold16 / timeout market / wait_from_break / pullback preferred / near_box N6 D1000 trend=off / side both / ticks -> PF2.69/+215812.6 n239 (`20260927T090050Z_65ffdcc2`).
- **Next:** tick-confirm runner `tr174_temd1900_wait13` (trail_pts=174, timeout_max_ema_dist_pts=1900, max_wait_candles=13) on KEEP seed. If reject -> Batch CA residual/compound on untried BZ soft clears (tr175-188 x temd1900 ladder already screened on 5m but not ticks; prefer axes outside rejected BY/BZ tick trio: asymmetric mb, max_break denser, mild arm/hold not retread). max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.

### 2026-09-28 ~00:13 Europe/Bucharest Asia BZ_runner tick tr174_temd1900_wait13 - REJECT vs NEW KEEP
- **Tick:** `tr174_temd1900_wait13` = KEEP + `trail_pts=174` `timeout_max_ema_dist_pts=1900` `max_wait_candles=13` - run `20260927T210451Z_ad92f714` - data_source=ticks - window 2025-01 to 2026-09 - workers=2.
- **Result:** n232 - PF **2.78** - **+214908.1** - win%46.6 - max_loss_streak **6** (max_win 7) - exits {"flatten":39,"sl":119,"tp":13,"trail":61}.
- **vs NEW KEEP** `20260927T090050Z_65ffdcc2` PF2.69/+215812.6 n239: dPF **+0.09** - dpts **-904.5** - dn **-7**.
- **Streak filter:** max_loss=6 (prefer <=7-8) - PASS.
- **Decision:** **REJECT** - dpts -904.5 under ~2k pts bar (5m overpromised dpts+3037); PF lift alone does not promote when total points fall. Fourth consecutive temd/tr/wait13 tick reject (BY champ/runner + BZ champ/runner).
- **KEEP unchanged:** asia0-6 / ema31 / wait14 / rc3 / cap800 / flat23 / mb275 / SL1000 / TP range_multx2.25 / sls5/2100 / trail arm4000/tr190 / hold16 / timeout market / wait_from_break / pullback preferred / near_box N6 D1000 trend=off / side both / ticks -> PF2.69/+215812.6 n239 (`20260927T090050Z_65ffdcc2`).
- **Next:** Batch CA `RESIDUAL_CA_OUTSIDE_TEMD_POCKET_NEW_KEEP` 5m - axes outside failed temd×tr×wait13 tick pocket: asymmetric mb, max_break denser, skip_late denser, mild mb volume, otp_off, resume denser, pullback/rco, mild arm/hold/trail alone, be_arm, wait alone; avoid BY/BZ temd×tr×wait13 retreads and BW near-box/TP-fixed/SL-pair. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.



### 2026-09-28 ~00:41 Europe/Bucharest Asia Batch CA RESIDUAL_CA_OUTSIDE_TEMD_POCKET_NEW_KEEP 5m — no clear pts lifts
- **Grid:** `results/overnight_5m_grid_20260927T211723Z.json` — tag `RESIDUAL_CA_OUTSIDE_TEMD_POCKET_NEW_KEEP` — seed KEEP ticks `20260927T090050Z_65ffdcc2` (asia0-6 ema31 wait14 rc3 rmb800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) — candles_5m — workers=2 — window 2025-01 to 2026-09 — 129 cells (0 errors).
- **Baseline 5m KEEP** (`NEW_KEEP_baseline`): n239 — PF **2.835** — **+234028.0**.
- **Top by pts vs baseline:**
  - `tr175`: PF **2.843** / **+234987.8** n239 — dPF **+0.008** — dpts **+959.8**
  - `tr180`: PF **2.840** / **+234667.8** n239 — dPF **+0.005** — dpts **+639.8**
  - `tr185`: PF **2.838** / **+234347.8** n239 — dPF **+0.003** — dpts **+319.8**
  - `maxbreak19`: PF **2.535** / **+234159.4** n273 — dPF **-0.300** — dpts **+131.4**
  - `tr188`: PF **2.836** / **+234155.8** n239 — dPF **+0.001** — dpts **+127.8**
  - `hold15_flat22` / `hold16_flat22` / `hold17_flat22` / `hold18_flat22` / `hold19_flat22` / `hold20_flat22`: PF **2.854** / **+234099.8** n239 — dPF **+0.019** — dpts **+71.8**
- **CLEAR dpts≥~2k at PF≥2.5:** none.
- **Soft ≥2.5 with pts lift (under ~2k tick bar):** 11 cells — best `tr175` dpts **+959.8**; hold*_flat22 cluster +71.8.
- **Under-floor PF<2.0:** `be_arm400` PF0.955; `pb_off` PF1.369; `be_arm600` PF1.370; `be_arm800` PF1.911.
- **Inert (=baseline):** 13 (otp_off family, rco_on, wick_off, several hold*_flat23).
- **Best PF-up / pts-down (reject for pts goal):** `maxbreak10` dpts **-59701.6**; asymmetric mb×maxbreak12 ~-27k; `maxbreak12/13/14` cut pts; `sls3_2100` PF2.915 dpts -1326.
- **Conclusion:** Batch CA screens axes outside failed BY/BZ temd×tr×wait13 tick pocket after fourth consecutive temd tick reject. **No** clear soft≥2.5 pts refine (best `tr175` dpts **+959.8** under ~2k bar). KEEP unchanged (ticks PF2.69/+215812.6 n239 `20260927T090050Z_65ffdcc2`).
- **Next:** Batch CB `RESIDUAL_CB_TPR_SL_EMA_SOFT_NEW_KEEP` 5m — denser tp_range_mult around KEEP 2.25; SL fixed/sl_cap denser preserving ~1:1.5+; ema_period denser; CA soft pocket compounds **without** temd (`tr175`/`tr180` × hold_flat22 / wait); trail-near-TP arm×tpm compounds; mild min_asia_range + asia window micro. Avoid BY/BZ temd×tr×wait13 retreads, CA singles already screened, BW near-box/TP-fixed, BX armmode from_fill / season filter. Tick-confirm only clear soft≥2.5 pts lifts (dpts≥~2k), max_loss streak ≤7–8. stop_auto_tick=FALSE. No reaktor / no push.



### 2026-09-28 ~01:14 Europe/Bucharest Asia Batch CB RESIDUAL_CB_TPR_SL_EMA_SOFT_NEW_KEEP 5m - no clear pts lifts
- **Grid:** `results/overnight_5m_grid_20260927T214441Z.json` - tag `RESIDUAL_CB_TPR_SL_EMA_SOFT_NEW_KEEP` - seed KEEP ticks `20260927T090050Z_65ffdcc2` (asia0-6 ema31 wait14 rc3 cap800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) - candles_5m - workers=2 - window 2025-01 to 2026-09 - 113 cells (0 errors).
- **Baseline 5m KEEP** (`NEW_KEEP_baseline`): n239 - PF **2.835** - **+234028.0**.
- **Top by pts vs baseline:**
  - `tr175_tpm2_4` / `arm4000_tr175_tpm2_4`: PF **2.846** / **+235371.9** n239 - dPF **+0.011** - dpts **+1343.9**
  - `tr172_hold16/17/18_flat22`: PF **2.863** / **+235251.7** n239 - dPF **+0.028** - dpts **+1223.7**
  - `tr172_hold16_flat23`: PF **2.844** / **+235179.9** n239 - dPF **+0.009** - dpts **+1151.9**
  - `tr175_hold16/17/18_flat22`: PF **2.861** / **+235059.6** n239 - dPF **+0.026** - dpts **+1031.6**
  - `tr180_tpm2_4_hold16_flat22`: PF **2.861** / **+235009.0** n239 - dPF **+0.026** - dpts **+981.0**
- **CLEAR dpts>=~2k at PF>=2.5:** none.
- **Soft >=2.5 with pts lift (under ~2k tick bar):** 24 cells - best `tr175_tpm2_4` dpts **+1343.9**; also `tpm2_4` / `sl1000_tpm2_4` / `mar250_tpm2_4` / `mar350_tpm2_4` / `tr175_wait13` thin.
- **Under-floor PF<2.0:** `asia1_5` PF1.803; `asia0_5_tpm2_4` PF1.890; `asia0_5` PF1.899; `asia0_8` PF1.998.
- **Inert (=baseline):** 10 (slcap* family, mar200/250/350/400).
- **Best PF-near / pts-down (reject for pts goal):** asia window micro cuts ~57k-113k; `ema36` dpts **-55611**; `sl850` **-41313**; large arm x tpm cut pts; `tr175/180_wait12` ~-35k.
- **Conclusion:** Batch CB densifies tpr/SL/ema + CA soft pocket compounds without temd after CA stall. **No** clear soft>=2.5 pts refine (best dpts **+1343.9** under ~2k bar). Asia micro / tight SL / oversized arm x tpm rejected. KEEP unchanged (ticks PF2.69/+215812.6 n239 `20260927T090050Z_65ffdcc2`).
- **Next:** Batch CC `RESIDUAL_CC_SOFT_COMPOUND_PLAN_EF_NEW_KEEP` 5m - compound CB soft pocket to seek dpts>=~2k (`tr172/175/178` x `tpm2.4/2.5` x hold_flat22 x mild wait/mar/sl); plan-E hold/flatten denser; mild rc/rmb/otp x soft; thin plan-F only if compounds stall. Avoid BY/BZ temd x tr x wait13, CA/CB singles already screened, BW near-box/TP-fixed, asia micro underfloor, wait12, arm>=4800, sl850. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.

### 2026-09-28 ~01:49 Europe/Bucharest Asia Batch CC RESIDUAL_CC_SOFT_COMPOUND_PLAN_EF_NEW_KEEP 5m - no clear pts lifts
- **Grid:** 
esults/overnight_5m_grid_20260927T221820Z.json - tag RESIDUAL_CC_SOFT_COMPOUND_PLAN_EF_NEW_KEEP - seed KEEP ticks 20260927T090050Z_65ffdcc2 (asia0-6 ema31 wait14 rc3 cap800 flat23 mb275 SL1000 TP range_multx2.25 sls5/2100 trail arm4000/tr190 hold16 near_box N6 D1000 trend=off) - candles_5m - workers=2 - window 2025-01 to 2026-09 - 127 cells (8 errors: hold*_flat24 hour must be in 0..23).
- **Baseline 5m KEEP** (NEW_KEEP_baseline): n239 - PF **2.835** - **+234028.0**.
- **Top by pts vs baseline:**
  - 	r170_tpm2_4: PF **2.848** / **+235697.2** n239 - dPF **+0.013** - dpts **+1669.2**
  - 	r172_tpm2_4 / 	r172_tpm2_4_wait14 / mar250_tr172_tpm2_4 / mar350_tr172_tpm2_4: PF **2.847** / **+235567.0** n239 - dPF **+0.012** - dpts **+1539.0**
  - 	r172_tpm2_4_hold16/17/18_flat22: PF **2.865** / **+235529.1** n239 - dPF **+0.030** - dpts **+1501.1**
  - 	r175_tpm2_4 family: PF **2.846** / **+235371.9** n239 - dPF **+0.011** - dpts **+1343.9**
- **CLEAR dpts>=~2k at PF>=2.5:** none.
- **Soft >=2.5 with pts lift (under ~2k tick bar):** 50 cells - best 	r170_tpm2_4 dpts **+1669.2**; tpm2.5 compounds mostly pts-down vs tpm2.4.
- **Under-floor PF<2.0:** 0.
- **Inert (=baseline):** 7 (news_skip + several hold*_flat23).
- **Best PF-up / pts-down (reject for pts goal):** side_short PF3.771 dpts **-99235**; season_filter PF2.951 dpts **-22249**; hold*_flat21 cluster dpts **-1856**; rc2/4/5 x soft cut 35k-47k.
- **Conclusion:** Batch CC compounds CB soft pocket (tr x tpm2.4/2.5 x hold_flat22 x wait/mar/sl) after CA/CB stall. **No** clear soft>=2.5 pts refine (best dpts **+1669.2** under ~2k bar). Plan-F side/season/week2 and rc denser reject for total pts. KEEP unchanged (ticks PF2.69/+215812.6 n239 20260927T090050Z_65ffdcc2).
- **Next:** Batch CD RESIDUAL_CD_TR170_TPM_DENSE_NEW_KEEP 5m - densify CC soft champ pocket (	r166-171 x 	pm2.30-2.45 x hold_flat22 / mild ema29-33 / mild sls / mild arm3900-4100 / mild maxbreak16-18) to seek dpts>=~2k; avoid CC cells already screened, BY/BZ temd x tr x wait13, CA singles, BW near-box/TP-fixed, asia micro, wait12, flat24, arm>=4500, sl850, rc/side/season plan-F retreads. Tick-confirm only clear soft>=2.5 pts lifts (dpts>=~2k), max_loss streak <=7-8. stop_auto_tick=FALSE. No reaktor / no push.

