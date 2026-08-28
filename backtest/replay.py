"""
Replay Dukascopy ticks through standalone range-live + spike + spike_neo engines.

Uses simulated tick timestamps for hold / cooldown (not wall clock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Sequence, Set

from backtest import config
from backtest.candles import (
    CandleBuilder,
    is_candle_ignored,
    is_market_open,
    is_session_open_skip,
)
from backtest.dukascopy import Tick
from backtest.range_live import RangeBaselineCache, calculate_candle_metrics, conditions_met
from backtest.spike import SpikeDetector
from backtest.spike_neo import (
    conditions_met as spike_neo_conditions_met,
    evaluate_spike_neo,
)
from backtest.impulse_retrace import (
    conditions_met as impulse_retrace_conditions_met,
    evaluate_impulse_retrace,
)
from backtest.range_wick import (
    calculate_wick_metrics,
    conditions_met as wick_conditions_met,
)
from backtest.trades import AlertSignal


@dataclass
class ReplayResult:
    alerts: List[AlertSignal] = field(default_factory=list)
    alert_tick_index: List[int] = field(default_factory=list)
    ticks_processed: int = 0
    candles_completed: int = 0


class AlertReplay:
    """
    Stateful tick consumer mirroring Reaktor monitor path for:
      - range live (hold + cooldown + one-per-bar-side)
      - spike (detector internal cooldown)
      - spike_neo (compression → expansion → structure hold)
      - impulse_retrace (blast then 50%/75% pullback)
      - candle_wick / range wick (legacy wick-latched range)
    """

    def __init__(
        self,
        symbol: str = "XAU/USD",
        *,
        engines: Optional[Set[str]] = None,
        price_field: str = "mid",
    ):
        self.symbol = symbol
        self.engines = engines or {"candle", "spike"}
        self.price_field = price_field

        self.builder = CandleBuilder(
            timeframe_minutes=config.CANDLE_TIMEFRAME_MIN,
            max_completed=max(config.CANDLE_LOOKBACK + 40, 100),
        )
        spike_cfg = {symbol: dict(config.SPIKE_CONFIG.get(symbol) or {})}
        self.spike = SpikeDetector(spike_cfg)
        self._range_cache = RangeBaselineCache()

        self._range_condition_since: Optional[float] = None
        self._last_range_alert_ts: float = 0.0
        self._range_alerted_bar = None

        # Spike Neo hold / cooldown / one-per-bar (market time)
        self._neo_condition_since: Optional[float] = None
        self._last_neo_alert_ts: float = 0.0
        self._neo_alerted_bar = None

        # Impulse retrace: hold per fraction + fractions fired per impulse leg
        # + extreme age clock (max_retrace_age_sec from reaktor)
        self._ir_condition_since = None  # (ts, frac) | None
        self._last_ir_alert_ts: float = 0.0
        self._ir_leg_key = None
        self._ir_alerted_fractions: set = set()
        self._ir_extreme_clock = None  # {"key": impulse_key, "at": epoch} | None

        # Range wick (legacy)
        self._wick_condition_since: Optional[float] = None
        self._last_wick_alert_ts: float = 0.0
        self._wick_alerted_bar = None

        # Cache ignore decision for the current 15m bucket
        self._ignore_bucket_ot = None
        self._ignore_bucket_val = False

        self.alerts: List[AlertSignal] = []
        self.alert_tick_index: List[int] = []
        self.candles_completed = 0

    def _px(self, tick: Tick) -> float:
        if self.price_field == "bid":
            return tick.bid
        if self.price_field == "ask":
            return tick.ask
        return tick.mid

    def _range_cooldown_ok(self, now_ts: float) -> bool:
        cfg = config.THRESHOLDS.get(self.symbol) or {}
        cd = float(cfg.get("cooldown_min", 60)) * 60.0
        return (now_ts - self._last_range_alert_ts) >= cd

    def _range_hold_ready(self, metrics: dict, now_ts: float) -> bool:
        cfg = config.THRESHOLDS.get(self.symbol) or {}
        hold_sec = float(cfg.get("hold_sec") or 0)
        if not conditions_met(self.symbol, metrics):
            self._range_condition_since = None
            return False
        if self._range_condition_since is None:
            self._range_condition_since = now_ts
            return hold_sec <= 0
        held = now_ts - self._range_condition_since
        return held >= hold_sec if hold_sec > 0 else True

    def on_tick(self, tick: Tick, tick_index: int) -> List[AlertSignal]:
        price = self._px(tick)
        ts = tick.ts
        now_ts = ts.timestamp()
        fired: List[AlertSignal] = []

        # Reaktor: no processing when market closed
        if not is_market_open(ts):
            self._range_condition_since = None
            self._neo_condition_since = None
            self._ir_condition_since = None
            self._wick_condition_since = None
            return fired

        open_time, _ = self.builder._get_candle_bounds(ts)
        if open_time != self._ignore_bucket_ot:
            self._ignore_bucket_ot = open_time
            self._ignore_bucket_val = is_candle_ignored(open_time)
        ignore = self._ignore_bucket_val

        closed = self.builder.add_price(price, ts)
        if closed is not None:
            self.candles_completed += 1

        if ignore:
            self._range_condition_since = None
            self._neo_condition_since = None
            self._ir_condition_since = None
            self._wick_condition_since = None
            return fired

        # Week-open skip: still build candles, do not fire alerts
        if is_session_open_skip(ts):
            self._range_condition_since = None
            self._neo_condition_since = None
            self._ir_condition_since = None
            self._wick_condition_since = None
            return fired

        # Use full completed list (spike lookback is small; range cache slices)
        completed = self.builder.completed_candles

        if "spike" in self.engines:
            hit = self.spike.update(
                self.symbol,
                price,
                timestamp=ts,
                completed_candles=completed,
            )
            if hit is not None:
                alert = AlertSignal(
                    kind="spike",
                    symbol=self.symbol,
                    side=hit.direction,  # type: ignore[arg-type]
                    ts=ts,
                    price=price,
                    meta={
                        "points": hit.points,
                        "min_points": hit.min_points,
                        "window_sec": hit.window_sec,
                        "ref": hit.ref_price,
                        "extreme": hit.extreme_price,
                    },
                )
                self.alerts.append(alert)
                self.alert_tick_index.append(tick_index)
                fired.append(alert)

        if "spike_neo" in self.engines:
            neo_alert = self._maybe_fire_spike_neo(price, ts, now_ts, tick_index)
            if neo_alert is not None:
                fired.append(neo_alert)

        if "impulse_retrace" in self.engines:
            ir_alert = self._maybe_fire_impulse_retrace(price, ts, now_ts, tick_index)
            if ir_alert is not None:
                fired.append(ir_alert)

        if "candle_wick" in self.engines or "range_wick" in self.engines:
            wick_alert = self._maybe_fire_range_wick(price, ts, now_ts, tick_index)
            if wick_alert is not None:
                fired.append(wick_alert)

        if "candle" in self.engines:
            forming = self.builder.get_current_candle()
            # Cheap pre-filter: can't meet min body/dir floors → skip full metrics
            # (except while a hold timer is already running)
            skip_full = False
            if forming is not None and self._range_condition_since is None:
                cfg = config.THRESHOLDS.get(self.symbol) or {}
                ps = float(config.point_size(self.symbol))
                min_need = max(
                    float(cfg.get("min_directed_points") or 0),
                    float(cfg.get("min_body_points") or 0),
                )
                # 0.95 slack so we still compute near the floor
                if abs(price - forming.open) < min_need * ps * 0.95:
                    skip_full = True
                    # still reset hold when far from open after having been near
                    # (hold already None here)

            if skip_full or forming is None:
                if forming is None:
                    self._range_condition_since = None
            else:
                metrics = calculate_candle_metrics(
                    self.builder,
                    price,
                    symbol=self.symbol,
                    cache=self._range_cache,
                )
                if metrics is None:
                    self._range_condition_since = None
                else:
                    ready = self._range_hold_ready(metrics, now_ts)
                    if ready and self._range_cooldown_ok(now_ts):
                        side = metrics.get("live_side") or metrics.get(
                            "directed_side"
                        )
                        bar_key = (metrics.get("forming_open_time"), side)
                        if not (
                            bar_key[0] is not None
                            and self._range_alerted_bar == bar_key
                        ):
                            alert = AlertSignal(
                                kind="candle",
                                symbol=self.symbol,
                                side=side,  # type: ignore[arg-type]
                                ts=ts,
                                price=price,
                                meta={
                                    "directed_points": metrics.get("directed_points"),
                                    "directed_ratio": metrics.get("directed_ratio"),
                                    "body_points": metrics.get("body_points"),
                                    "structure_break_ok": metrics.get(
                                        "structure_break_ok"
                                    ),
                                    "forming_open_time": metrics.get(
                                        "forming_open_time"
                                    ),
                                },
                            )
                            self.alerts.append(alert)
                            self.alert_tick_index.append(tick_index)
                            fired.append(alert)
                            self._last_range_alert_ts = now_ts
                            self._range_condition_since = None
                            if bar_key[0] is not None:
                                self._range_alerted_bar = bar_key

        return fired

    def _neo_cooldown_ok(self, now_ts: float) -> bool:
        cfg = config.SPIKE_NEO_CONFIG.get(self.symbol) or {}
        cd = float(cfg.get("cooldown_min") or 45) * 60.0
        return (now_ts - self._last_neo_alert_ts) >= cd

    def _neo_hold_ready(self, snap: Optional[dict], now_ts: float) -> bool:
        cfg = config.SPIKE_NEO_CONFIG.get(self.symbol) or {}
        hold_sec = float(cfg.get("hold_sec") or 0)
        if not spike_neo_conditions_met(snap):
            self._neo_condition_since = None
            return False
        if self._neo_condition_since is None:
            self._neo_condition_since = now_ts
            return hold_sec <= 0
        held = now_ts - self._neo_condition_since
        return held >= hold_sec if hold_sec > 0 else True

    def _maybe_fire_spike_neo(
        self, price: float, ts: datetime, now_ts: float, tick_index: int
    ) -> Optional[AlertSignal]:
        snap = evaluate_spike_neo(self.builder, price, symbol=self.symbol)
        if not snap or not snap.get("enabled", True) or snap.get("waiting"):
            self._neo_condition_since = None
            return None
        if not self._neo_hold_ready(snap, now_ts):
            return None
        if not self._neo_cooldown_ok(now_ts):
            return None
        side = snap.get("side")
        if side not in ("UP", "DOWN"):
            return None
        bar_key = (snap.get("forming_open_time"), side)
        if bar_key[0] is not None and self._neo_alerted_bar == bar_key:
            return None
        exp = snap.get("expansion") or {}
        alert = AlertSignal(
            kind="spike_neo",
            symbol=self.symbol,
            side=side,  # type: ignore[arg-type]
            ts=ts,
            price=price,
            meta={
                "beyond_points": snap.get("beyond_points"),
                "forming_range_points": snap.get("forming_range_points"),
                "expansion_ratio": exp.get("ratio"),
                "expansion_mult": exp.get("expansion_mult"),
                "compression_swing_points": (snap.get("compression") or {}).get(
                    "swing_points"
                ),
                "forming_open_time": snap.get("forming_open_time"),
                "variant": "spike_neo",
            },
        )
        self.alerts.append(alert)
        self.alert_tick_index.append(tick_index)
        self._last_neo_alert_ts = now_ts
        self._neo_condition_since = None
        if bar_key[0] is not None:
            self._neo_alerted_bar = bar_key
        return alert

    def _ir_cooldown_ok(self, now_ts: float) -> bool:
        cfg = config.IMPULSE_RETRACE_CONFIG.get(self.symbol) or {}
        cd = float(cfg.get("cooldown_min") or 30) * 60.0
        return (now_ts - self._last_ir_alert_ts) >= cd

    def _ir_hold_ready(self, snap: Optional[dict], now_ts: float) -> bool:
        cfg = config.IMPULSE_RETRACE_CONFIG.get(self.symbol) or {}
        hold_sec = float(cfg.get("hold_sec") or 0)
        if not impulse_retrace_conditions_met(snap):
            self._ir_condition_since = None
            return False
        frac = snap.get("active_fraction")
        since = None
        since_frac = None
        blob = self._ir_condition_since
        if isinstance(blob, tuple) and len(blob) == 2:
            since, since_frac = blob
        if since is None or since_frac != frac:
            self._ir_condition_since = (now_ts, frac)
            return hold_sec <= 0
        held = now_ts - since
        return held >= hold_sec if hold_sec > 0 else True

    def _touch_ir_extreme_clock(
        self, snap: Optional[dict], now_ts: float
    ) -> Optional[float]:
        """
        Stamp / read when the current impulse extreme was seen (mirrors reaktor).
        Clock starts on first observation of impulse_key; resets when key changes
        (new blast or extreme extension).
        """
        if not snap or not snap.get("impulse_ok") or snap.get("impulse_key") is None:
            self._ir_extreme_clock = None
            return None
        key = snap.get("impulse_key")
        prev = self._ir_extreme_clock
        if (
            isinstance(prev, dict)
            and prev.get("key") == key
            and prev.get("at") is not None
        ):
            return float(prev["at"])
        self._ir_extreme_clock = {"key": key, "at": now_ts}
        return now_ts

    def _maybe_fire_impulse_retrace(
        self, price: float, ts: datetime, now_ts: float, tick_index: int
    ) -> Optional[AlertSignal]:
        # Probe without age clock (same two-pass as reaktor live monitor)
        snap = evaluate_impulse_retrace(
            self.builder,
            price,
            symbol=self.symbol,
            alerted_fractions=self._ir_alerted_fractions,
            now=now_ts,
        )
        if not snap or not snap.get("enabled", True):
            self._ir_condition_since = None
            self._ir_extreme_clock = None
            return None
        if snap.get("waiting") or snap.get("idle"):
            self._ir_condition_since = None
            # New idle impulse → clear leg + age clock when no impulse
            if snap.get("message") == "no_impulse":
                self._ir_leg_key = None
                self._ir_alerted_fractions = set()
                self._ir_extreme_clock = None
            else:
                self._touch_ir_extreme_clock(snap, now_ts)
            return None

        impulse_key = snap.get("impulse_key")
        if impulse_key != self._ir_leg_key:
            self._ir_leg_key = impulse_key
            self._ir_alerted_fractions = set()
            self._ir_condition_since = None

        extreme_at = self._touch_ir_extreme_clock(snap, now_ts)
        # Re-evaluate with alerted set + age clock after leg/clock sync
        snap = evaluate_impulse_retrace(
            self.builder,
            price,
            symbol=self.symbol,
            alerted_fractions=self._ir_alerted_fractions,
            extreme_seen_at=extreme_at,
            now=now_ts,
        )
        if not snap or not snap.get("enabled", True):
            self._ir_condition_since = None
            return None
        if snap.get("waiting") or snap.get("idle"):
            self._ir_condition_since = None
            return None

        if not self._ir_hold_ready(snap, now_ts):
            return None
        if not self._ir_cooldown_ok(now_ts):
            return None
        side = snap.get("side")
        frac = snap.get("active_fraction")
        if side not in ("UP", "DOWN") or frac is None:
            return None
        if float(frac) in self._ir_alerted_fractions:
            return None

        alert = AlertSignal(
            kind="impulse_retrace",
            symbol=self.symbol,
            side=side,  # type: ignore[arg-type]
            ts=ts,
            price=price,
            meta={
                "retrace_fraction": frac,
                "retrace_pct": snap.get("retrace_pct"),
                "active_level": snap.get("active_level"),
                "base": snap.get("base"),
                "extreme": snap.get("extreme"),
                "range_points": snap.get("range_points"),
                "extreme_age_sec": snap.get("extreme_age_sec"),
                "forming_open_time": snap.get("forming_open_time"),
                "variant": "impulse_retrace",
            },
        )
        self.alerts.append(alert)
        self.alert_tick_index.append(tick_index)
        self._last_ir_alert_ts = now_ts
        self._ir_condition_since = None
        self._ir_alerted_fractions.add(float(frac))
        return alert

    def _wick_cooldown_ok(self, now_ts: float) -> bool:
        cfg = config.RANGE_WICK_THRESHOLDS.get(self.symbol) or {}
        cd = float(cfg.get("cooldown_min") or 60) * 60.0
        return (now_ts - self._last_wick_alert_ts) >= cd

    def _wick_hold_ready(self, metrics: Optional[dict], now_ts: float) -> bool:
        cfg = config.RANGE_WICK_THRESHOLDS.get(self.symbol) or {}
        hold_sec = float(cfg.get("hold_sec") or 0)
        if metrics is None or not wick_conditions_met(self.symbol, metrics):
            self._wick_condition_since = None
            return False
        if self._wick_condition_since is None:
            self._wick_condition_since = now_ts
            return hold_sec <= 0
        held = now_ts - self._wick_condition_since
        return held >= hold_sec if hold_sec > 0 else True

    def _maybe_fire_range_wick(
        self, price: float, ts: datetime, now_ts: float, tick_index: int
    ) -> Optional[AlertSignal]:
        metrics = calculate_wick_metrics(self.builder, price, symbol=self.symbol)
        if not self._wick_hold_ready(metrics, now_ts):
            return None
        if not self._wick_cooldown_ok(now_ts):
            return None
        side = (metrics or {}).get("directed_side") or (metrics or {}).get("side")
        if side not in ("UP", "DOWN"):
            return None
        bar_key = ((metrics or {}).get("forming_open_time"), side)
        if bar_key[0] is not None and self._wick_alerted_bar == bar_key:
            return None
        alert = AlertSignal(
            kind="candle_wick",
            symbol=self.symbol,
            side=side,  # type: ignore[arg-type]
            ts=ts,
            price=price,
            meta={
                "directed_points": (metrics or {}).get("directed_points"),
                "directed_ratio": (metrics or {}).get("directed_ratio"),
                "body_points": (metrics or {}).get("body_points"),
                "structure_break_ok": (metrics or {}).get("structure_break_ok"),
                "forming_open_time": (metrics or {}).get("forming_open_time"),
                "variant": "wick",
            },
        )
        self.alerts.append(alert)
        self.alert_tick_index.append(tick_index)
        self._last_wick_alert_ts = now_ts
        self._wick_condition_since = None
        if bar_key[0] is not None:
            self._wick_alerted_bar = bar_key
        return alert


def run_replay(
    ticks: Sequence[Tick],
    symbol: str = "XAU/USD",
    *,
    engines: Optional[Set[str]] = None,
    price_field: str = "mid",
    progress_every: int = 250_000,
    progress_cb=None,
) -> ReplayResult:
    eng = AlertReplay(symbol, engines=engines, price_field=price_field)
    n = len(ticks)
    for i, t in enumerate(ticks):
        eng.on_tick(t, i)
        if progress_every and i > 0 and i % progress_every == 0:
            msg = (
                f"  replay {i:,}/{n:,} ticks  alerts={len(eng.alerts)}  "
                f"candles={eng.candles_completed}"
            )
            print(msg, flush=True)
            if progress_cb:
                progress_cb(i, n, len(eng.alerts), eng.candles_completed)
    return ReplayResult(
        alerts=eng.alerts,
        alert_tick_index=eng.alert_tick_index,
        ticks_processed=n,
        candles_completed=eng.candles_completed,
    )
