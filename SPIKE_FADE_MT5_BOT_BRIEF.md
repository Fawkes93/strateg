# Brief for another Grok: live Spike Fade MT5 bot (Windows)

You are implementing a **new, small Python bot** on a Windows PC that already runs **several MetaTrader 5 terminals**. Clone the pattern of **`Fawkes93/patient-scalper`** (private) for MT5 connect / order send / which-terminal, then implement **Spike Fade** logic from **`Fawkes93/strateg`** (`backtest/spike_fade.py`). Do **not** copy patient-scalper’s hedge / martingale / recovery.

Owner will paste this whole file into you. Repo to imitate: `https://github.com/Fawkes93/patient-scalper` (private). Research backtest: `https://github.com/Fawkes93/strateg` (private).

---

## Goal

Live XAUUSD bot:

1. Watch ticks in a **3 second** window.
2. If mid moves **≥ 1100 points** in that window, **fade** (trade the other way).
3. Fixed **TP 3000 / SL 1000 / trail 500** (points). No % of spike.
4. Flatten after **200 seconds** if still open.
5. One position at a time. 30s cooldown after close.
6. Skip first **10 minutes after Sunday 22:00 UTC** (weekend reopen).
7. Optional **fill lag** 0 / 1 / 2 seconds after detect (config; start at **1**, easy to set to 0).
8. User picks **which MT5 terminal** via `MT5_PATH` exactly like patient-scalper.

**Demo first. Small lot. Supervised.**

---

## What to copy from patient-scalper

Read `config.py` + `bot.py` there. Reuse these ideas **verbatim in spirit**:

| Piece | How they do it | What you do |
|---|---|---|
| Which MT5 | `MT5_PATH = r"C:\Program Files\RoboForex MT5 Terminal\terminal64.exe"` then `mt5.initialize(path=MT5_PATH)` | Same. Each installed client has its **own** `terminal64.exe`. That path **is** the account picker. |
| Connect | `connect_mt5()`, log account/server/balance, warn if `trade_allowed` is false | Copy |
| Symbol | `ensure_symbol()`, `symbol_select` | Copy |
| Filling | `filling_mode()` tries IOC / FOK / RETURN from `symbol_info.filling_mode` | Copy |
| Volume | snap to `volume_min` / `volume_step` | Copy |
| Orders | `TRADE_ACTION_DEAL`, magic, comment, deviation | Copy |
| Modify SL | `TRADE_ACTION_SLTP` | Use for **trail** |
| Close | opposite deal with `position=ticket` | Use for **timeout** and trail if you close at market |
| Filter our trades | `positions_get` where `magic == MAGIC` | **New MAGIC**, not `20260730` (that is patient-scalper). Use `20260814`. |
| Loop | `LOOP_SLEEP_SEC` | Use **0.02s or faster** (this is a 3s spike, not a 0.25s hedge bot) |
| Logs | console + `*.log` file | `spike_fade.log` |

Their README setup path on this user’s Windows box was:

```powershell
cd C:\Users\M4800\source\repos\patient-scalper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py
```

Put the new bot next to it, e.g. `C:\Users\M4800\source\repos\spike-fade-bot\`.

`requirements.txt` = `MetaTrader5>=5.0.45` only.

**Do not** use `copy_ticks_*` as the primary feed. Patient-scalper found broker tick history frozen / wrong timestamps. Poll `symbol_info_tick` every loop and keep a deque of live mids (they already do this for settle).

---

## Units — do not mix with patient-scalper pips

Strateg / this fade backtest:

- **1 point = 0.01 price** on XAU (`point_size = 0.01`).
- **100 pts = $1** on **0.01 lot**.
- **1100 pts = $11.00** of gold.
- **3000 pts = $30.00**.
- **1000 pts = $10.00**.
- **500 pts = $5.00**.

Patient-scalper uses `PIP_SIZE = 0.1` (a “pip” = $0.10). **Do not use that.** Live bot distances are **MT5 points** (`symbol_info.point`, almost always `0.01` on XAUUSD).

On start:

```text
assert abs(symbol_info.point - 0.01) < 1e-9 or log a hard warning
price_offset = pts * symbol_info.point
```

If you wrongly treat 1100 as 0.1-pips you will look for an **$110** spike. That is wrong.

---

## Live defaults (screenshot combo that tested best)

No date range. No TP%/SL%. Fixed numbers only.

```python
SYMBOL = "XAUUSD"
MAGIC = 20260814
LOT = 0.01
DRY_RUN = True          # default ON until they say go live

WINDOW_SEC = 3.0
MIN_SPIKE_PTS = 1100    # $11 mid move in the window
TP_PTS = 3000           # $30
SL_PTS = 1000           # $10
TRAIL_PTS = 500         # arm at +$5, then trail $5 behind best
MAX_HOLD_SEC = 200
COOLDOWN_SEC = 30
WEEKEND_BLACKOUT_MIN = 10
LAG_SEC = 1.0           # 0.0 = fire immediately; 1 or 2 = wait then fill
MAX_SPREAD_PTS = 80     # skip new entries if (ask-bid)/point > this
DEVIATION_PTS = 30      # order slippage allowance in points

# Which MT5 — user edits this per client (same idea as patient-scalper)
MT5_PATH = r"C:\Program Files\RoboForex MT5 Terminal\terminal64.exe"
```

`LAG_SEC` must be a single obvious config line. They are unsure live; they will flip 0 ↔ 1 ↔ 2.

`DRY_RUN=True`: detect + log `WOULD OPEN BUY/SELL …` but **do not** `order_send`. Manage a fake local position from ticks so they can see detects without risk.

---

## Exact detect logic (port this)

Maintain `deque` of `(epoch_sec, mid)` for the last `WINDOW_SEC`. Mid = `(bid+ask)/2`. Also track `win_hi` / `win_lo` of prices still in the deque.

Do **not** fire if the window span `< min(0.4, WINDOW_SEC * 0.25)` seconds (stops a one-tick print).

```
ref = oldest mid in deque
up   = (win_hi - ref) / point
down = (ref - win_lo) / point

if up >= down and up >= MIN_SPIKE_PTS → spike_dir = UP
elif down > up and down >= MIN_SPIKE_PTS → spike_dir = DOWN
else no signal
```

Fade:

- spike UP (rip) → **SELL**
- spike DOWN (dump) → **BUY**

One trade at a time. If a position (real or dry) is open, **do not detect**. After close, ignore signals until `now >= close_time + COOLDOWN_SEC`.

Weekend blackout (UTC, not broker server time):

```
Sunday 22:00:00 UTC  inclusive
to Sunday 22:00 + WEEKEND_BLACKOUT_MIN  exclusive
```

No new entries in that window.

### Fill lag

If `LAG_SEC <= 0`: market order on the detect tick.

If `LAG_SEC` is 1 or 2: remember `{side, spike_pts, detect_mid, fill_at=now+LAG_SEC}`. On the first tick with `now >= fill_at`, send the market order at **that later** bid/ask (not the detect price). Cancel pending if blackout / spread too wide / already in a position.

---

## Position management (match the backtest)

On fill (live: actual `result.price`; dry: ask for buy / bid for sell):

```
BUY:  tp = fill + TP_PTS * point
      sl = fill - SL_PTS * point
SELL: tp = fill - TP_PTS * point
      sl = fill + SL_PTS * point
```

Attach **initial SL and TP on the MT5 order** as a safety net. Also manage locally every tick:

Favorite points (`fav`):

- BUY: `(bid - entry) / point`   (use **bid** for long mark-to-market)
- SELL: `(entry - ask) / point`

`best_fav = max(best_fav, fav)`

Trail **arms** when `best_fav >= TRAIL_PTS` (500). Then:

```
BUY  trail_px = (entry + best_fav * point) - TRAIL_PTS * point
SELL trail_px = (entry - best_fav * point) + TRAIL_PTS * point
```

At the arm moment trail is **breakeven**. After that it ratchets with the extreme. Push the broker SL to `trail_px` via `TRADE_ACTION_SLTP` (never loosen SL). Keep the original TP.

Exit priority on each tick (same as backtest):

1. **TP** — bid/ask through TP (or broker TP)
2. **hard SL** — through initial SL (or broker SL)
3. **trail** — through `trail_px` after armed (or broker SL after you moved it)
4. **timeout** — `now - entry_time >= MAX_HOLD_SEC` → **market close**

Comments on orders, 31 chars max: `SF` / `SFtrail` / `SFtime`.

If the terminal already has one of our MAGIC positions on start (crash recovery), **adopt it** — do not open a second. Reconstruct `entry`, `sl`, `tp`, `entry_time` from the position.

---

## Spread gate (live only; backtest was mid)

Before sending an entry:

```
spread_pts = (ask - bid) / point
if spread_pts > MAX_SPREAD_PTS: skip (log once)
```

Default 80. During a 1100-pt spike the book can be 50–200 pts wide; they know this. Keep the cap configurable.

---

## Suggested layout

```
spike-fade-bot/
  bot.py              # loop + detect + manage
  config.py           # all tunables including MT5_PATH, LAG_SEC, DRY_RUN
  requirements.txt    # MetaTrader5>=5.0.45
  README.md           # how to pick a terminal + run
  spike_fade.log      # gitignore
```

Keep it as small as patient-scalper. No web UI. No Dukascopy. No date range.

---

## Loop sketch

```
connect_mt5(path)
ensure_symbol
assert point
if existing MAGIC position: adopt
loop:
    tick = symbol_info_tick
    mid = (bid+ask)/2
    push deque, drop older than WINDOW_SEC
    if position open:
        update best_fav; maybe modify trail SL; maybe timeout close
    elif pending lag:
        if now >= fill_at and spread ok: open
    elif cooldown done and not weekend_blackout:
        detect; if hit: open or arm lag
    sleep 0.02
```

Log STATUS every 30–60s: mid, spread, deque span, in_pos, best_fav, hold_sec.

---

## Multi-terminal (required)

Windows will have **multiple MT5 clients** logged into different accounts.

- `mt5.initialize(path=...)` attaches to **that** `terminal64.exe`.
- That client must already be **open and logged in**.
- **Algo Trading** enabled on that terminal.
- Symbol in Market Watch.
- Do **not** run two bots against the same terminal/magic.

In `config.py` put a short comment block listing example paths, e.g.:

```python
# Pick ONE. Terminal must be running and logged in.
# MT5_PATH = r"C:\Program Files\RoboForex MT5 Terminal\terminal64.exe"
# MT5_PATH = r"C:\Program Files\MetaTrader 5 IC Markets\terminal64.exe"
# MT5_PATH = r"C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe"
MT5_PATH = r"C:\Program Files\RoboForex MT5 Terminal\terminal64.exe"
```

On startup log `terminal_info().path`, `account_info().login`, `account_info().server` so they can see they hit the right client.

Optional later: `python bot.py --mt5 "C:\...\terminal64.exe"` override. Config constant is enough for v1.

---

## README you should write

- Windows only, same PC as MT5
- venv + `pip install -r requirements.txt`
- Edit `MT5_PATH`, `DRY_RUN`, `LAG_SEC`, `LOT`
- `python bot.py` / Ctrl+C (positions stay in MT5)
- Units table (1100 pts = $11)
- Risk: spike entries pay real spread; backtest was mid

---

## Do not

- Do not port Session clock or impulse retrace.
- Do not implement TP%/SL% of spike.
- Do not reuse patient-scalper MAGIC or recovery.
- Do not size lots from martingale.
- Do not require Strateg or tick packs on this PC.
- Do not start with `DRY_RUN = False`.

---

## Acceptance

1. With `DRY_RUN=True`, log fade signals on a live XAU tick stream; no orders.
2. Switching `MT5_PATH` changes which account appears in the connect log.
3. `LAG_SEC=0` vs `1` is one config flip.
4. A real fill (when they turn dry run off) has SL 1000 pts and TP 3000 pts from fill; after +500 pts SL ratchets; at 200s the bot market-closes if still open.
5. Two bots / two terminals can run at once if MAGICs or terminals differ.

Build that. Ask the user only for the exact `terminal64.exe` path of the test client if it is not the RoboForex default above.
