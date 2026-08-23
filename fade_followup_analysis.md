# Follow-up analysis (auto)

Written 2026-08-14T23:22:35.214618+00:00

## Jan–Feb hunt (busy)
Best: **min=800** n=1156 avg=95.1 PF=1.25 sum=109905.8
params: `{"window_sec": 3.0, "min_spike_pts": 800.0, "tp_pts": 3000.0, "sl_pts": 1000.0, "tp_pct": 0.0, "sl_pct": 0.0, "trail_pts": 500.0, "trail_arm_pts": 700.0, "confirm_pts": 0.0, "confirm_timeout_sec": 5.0, "max_hold_sec": 320.0, "cooldown_sec": 0.0, "weekend_blackout_min": 10.0, "lag_sec": 1.0}`

## Quiet months
Best: **min=300** n=2418 avg=41.0 PF=1.25 sum=99186.1
Judgement: refine around this seed.

## Spike rate (activity meter)
- **2026-01**: 283 detects, active hours 32, median/p90/max per active hour 2/19/121, hours≥3/5/10 = 13/8/4
- **2026-02**: 213 detects, active hours 57, median/p90/max per active hour 2/7/38, hours≥3/5/10 = 22/12/5
- **2026-03**: 102 detects, active hours 29, median/p90/max per active hour 1/6/23, hours≥3/5/10 = 9/5/2
- **2026-05**: 1 detects, active hours 1, median/p90/max per active hour 1/1/1, hours≥3/5/10 = 0/0/0

## Plan for the next 3 sets

1. **Busy** — neighbors around Jan–Feb winner (or 94k seed).
2. **Quiet** — neighbors around quiet winner.
3. **One-way** — March+June only, 94k detect + confirm/cd (do not loosen min).

