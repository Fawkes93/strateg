# Data (not in git)

Tick / Dukascopy downloads live here and are gitignored (large binary packs).

Expected layout after download:

- `dukascopy/<SYMBOL>/YYYY/MM/DD/*_ticks.bi5`
- `tick_packs/<SYMBOL>_....tickpack`
- `candles/5m/<SYMBOL>/YYYY-MM.candlepack` (built from ticks on first 5m overnight run; reused until new tick hours appear)

Generate packs with the project download / pack tools before running sweeps.
5m candle months are created automatically when Overnight break runs with Data = 5m candles.
