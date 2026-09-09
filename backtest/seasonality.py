"""Conservative XAU month regimes plus a 2-week trend overlay.

Not a day-of-year scan. Only months that repeatedly show up in multi-year gold
work: January effect, summer doldrums, late-summer bid. September is not marked
soft — that story is sample-dependent.

2-week trend: last close vs EMA of daily closes, plus path efficiency
(|net| / sum |daily changes|). Small net stays flat. Low efficiency stays
flat even if net is large (two-way tape).

Season and 2-week each have off | tag | filter. Filter on either (or both).
If both filter and they disagree, tag both and do not skip.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from backtest.config import point_size
from backtest.dukascopy import Tick

# Bucharest calendar month → regime. Missing months stay neutral.
XAU_MONTH_REGIMES = {
    1: "strong",  # January
    8: "strong",  # August
    5: "soft",  # May
    6: "soft",  # June
}

REGIME_LABELS = {
    "strong": "strong (long bias)",
    "soft": "soft (short bias)",
    "neutral": "neutral",
}

BIAS_KINDS = frozenset({"spike_neo", "impulse_retrace"})
TREND_LOOKBACK_DAYS = 16
DEFAULT_TREND_SESSIONS = 10
DEFAULT_TREND_FLAT_PTS = 1500.0
DEFAULT_TREND_EFFICIENCY_MIN = 0.35
MIN_TREND_SESSIONS = 5


def month_regime(local_day: date) -> str:
    return XAU_MONTH_REGIMES.get(int(local_day.month), "neutral")


def bias_side(regime: str) -> Optional[str]:
    if regime == "strong":
        return "UP"
    if regime == "soft":
        return "DOWN"
    return None


def against_bias(regime: str, side: Optional[str]) -> bool:
    want = bias_side(regime)
    return want is not None and side is not None and side != want


def seasonal_label(regime: str, local_day: Optional[date] = None) -> str:
    body = REGIME_LABELS.get(regime, regime or "neutral")
    if local_day is None:
        return body
    return f"{local_day.strftime('%b')} {body}"


def normalize_seasonal_mode(mode: Optional[str]) -> str:
    m = (mode or "off").strip().lower()
    if m in ("off", "tag", "filter"):
        return m
    return "off"


def normalize_week2_mode(
    mode: Optional[str] = None,
    *,
    week2_trend: bool = False,
    seasonal_mode: str = "off",
) -> str:
    """off | tag | filter.

    Legacy checkbox: week2_trend True with no mode → tag, or filter when
    the month filter is already on (old combined behaviour).
    """
    m = (mode or "").strip().lower()
    if m in ("tag", "filter"):
        return m
    if m in ("1", "true", "on", "yes"):
        return "tag"
    # Default field is "off"; a legacy checkbox still arrives as week2_trend=True.
    if bool(week2_trend) and m in ("", "off"):
        if normalize_seasonal_mode(seasonal_mode) == "filter":
            return "filter"
        return "tag"
    return "off"


def combine_sides(
    season_side: Optional[str],
    trend_side: Optional[str],
) -> tuple[Optional[str], bool]:
    """Return (filter_side, conflict).

    Conflict (month vs 2-week opposite) → no filter, caller tags both.
    Otherwise the non-null side is the filter (they agree, or only one speaks).
    """
    if season_side and trend_side and season_side != trend_side:
        return None, True
    return (season_side or trend_side), False


@dataclass
class DailyClose:
    local_date: date
    close: float


def build_daily_closes(
    ticks: Sequence[Tick],
    tz_name: str = "Europe/Bucharest",
) -> List[DailyClose]:
    if not ticks:
        return []
    tz = ZoneInfo(tz_name)
    out: List[DailyClose] = []
    cur_day: Optional[date] = None
    cur_close = 0.0
    for t in ticks:
        d = t.ts.astimezone(tz).date()
        px = t.mid
        if cur_day is None:
            cur_day = d
            cur_close = px
            continue
        if d != cur_day:
            out.append(DailyClose(local_date=cur_day, close=cur_close))
            cur_day = d
        cur_close = px
    if cur_day is not None:
        out.append(DailyClose(local_date=cur_day, close=cur_close))
    return out


def _ema(values: Sequence[float], period: int) -> Optional[float]:
    if period < 1 or len(values) < period:
        return None
    k = 2.0 / (period + 1)
    e = float(values[0])
    for v in values[1:]:
        e = float(v) * k + e * (1.0 - k)
    return e


def week2_trend(
    dailies: Sequence[DailyClose],
    asof: date,
    *,
    sessions: int = DEFAULT_TREND_SESSIONS,
    flat_pts: float = DEFAULT_TREND_FLAT_PTS,
    efficiency_min: float = DEFAULT_TREND_EFFICIENCY_MIN,
    ps: float = 0.01,
) -> Dict[str, Any]:
    """Last close vs EMA of prior daily closes, plus path efficiency.

    Flat when net displacement is below `flat_pts`, or the path is two-way
    (efficiency below `efficiency_min`; 0 = skip that gate). Side is the
    sign of last close vs EMA, not first-to-last.
    """
    n = max(MIN_TREND_SESSIONS, int(sessions or DEFAULT_TREND_SESSIONS))
    flat = float(flat_pts if flat_pts is not None else DEFAULT_TREND_FLAT_PTS)
    try:
        eff_min = max(0.0, float(efficiency_min or 0.0))
    except (TypeError, ValueError):
        eff_min = DEFAULT_TREND_EFFICIENCY_MIN
    prior = [d for d in dailies if d.local_date < asof]
    used = prior[-n:] if len(prior) >= n else prior
    empty = {
        "state": "flat",
        "side": None,
        "move_pts": None,
        "net_pts": None,
        "efficiency": None,
        "sessions": len(used),
        "label": "flat (short history)",
    }
    if len(used) < MIN_TREND_SESSIONS or ps <= 0:
        return empty
    period = min(n, len(prior))
    ema = _ema([d.close for d in prior], period)
    if ema is None:
        return empty
    last = float(used[-1].close)
    slope_pts = (last - ema) / ps
    net = last - float(used[0].close)
    path = sum(
        abs(used[i].close - used[i - 1].close) for i in range(1, len(used))
    )
    eff = (abs(net) / path) if path > 1e-12 else 1.0
    net_pts = net / ps
    two_way = eff_min > 0 and eff + 1e-12 < eff_min
    if abs(net_pts) < flat:
        state, side = "flat", None
        why = "small net"
    elif two_way:
        state, side = "flat", None
        why = "chop"
    elif slope_pts > 1e-9:
        state, side = "up", "UP"
        why = None
    elif slope_pts < -1e-9:
        state, side = "down", "DOWN"
        why = None
    else:
        state, side = "flat", None
        why = "at EMA"
    tag = why or state
    return {
        "state": state,
        "side": side,
        "move_pts": round(slope_pts, 1),
        "net_pts": round(net_pts, 1),
        "efficiency": round(eff, 3),
        "sessions": len(used),
        "label": f"2w {tag} ({slope_pts:+.0f} vs EMA, eff {eff:.2f})",
    }


@dataclass
class BiasSnapshot:
    season_regime: str
    season_side: Optional[str]
    season_label: str
    trend_state: str
    trend_side: Optional[str]
    trend_move_pts: Optional[float]
    trend_efficiency: Optional[float]
    trend_sessions: int
    trend_label: str
    filter_side: Optional[str]
    conflict: bool

    def as_meta(self) -> Dict[str, Any]:
        return {
            "seasonal_regime": self.season_regime,
            "seasonal_label": self.season_label,
            "trend_state": self.trend_state,
            "trend_side": self.trend_side,
            "trend_move_pts": self.trend_move_pts,
            "trend_efficiency": self.trend_efficiency,
            "bias_conflict": self.conflict,
            "bias_side": self.filter_side,
        }

    def decision_note(self) -> str:
        bits = []
        if self.season_regime and self.season_regime != "neutral":
            bits.append(self.season_label)
        if self.trend_state and self.trend_state != "flat":
            bits.append(self.trend_label)
        elif self.trend_label and self.trend_sessions:
            bits.append(self.trend_label)
        if self.conflict:
            bits.append("bias conflict (no filter)")
        elif self.filter_side:
            bits.append("bias " + self.filter_side)
        return " · ".join(bits)


def snapshot_bias(
    local_day: date,
    *,
    dailies: Optional[Sequence[DailyClose]] = None,
    use_season: bool = True,
    use_week2: bool = False,
    season_filter: Optional[bool] = None,
    week2_filter: Optional[bool] = None,
    flat_pts: float = DEFAULT_TREND_FLAT_PTS,
    sessions: int = DEFAULT_TREND_SESSIONS,
    efficiency_min: float = DEFAULT_TREND_EFFICIENCY_MIN,
    ps: float = 0.01,
) -> BiasSnapshot:
    regime = month_regime(local_day) if use_season else "neutral"
    season_side = bias_side(regime) if use_season else None
    s_lbl = seasonal_label(regime, local_day) if use_season else "season off"
    if use_week2 and dailies:
        tr = week2_trend(
            dailies,
            local_day,
            sessions=sessions,
            flat_pts=flat_pts,
            efficiency_min=efficiency_min,
            ps=ps,
        )
    else:
        tr = {
            "state": "flat",
            "side": None,
            "move_pts": None,
            "efficiency": None,
            "sessions": 0,
            "label": "2w off",
        }
    sf = bool(use_season) if season_filter is None else bool(season_filter)
    wf = bool(use_week2) if week2_filter is None else bool(week2_filter)
    filt, conflict = combine_sides(
        season_side if sf else None,
        tr.get("side") if wf else None,
    )
    return BiasSnapshot(
        season_regime=regime if use_season else "neutral",
        season_side=season_side,
        season_label=s_lbl,
        trend_state=str(tr.get("state") or "flat"),
        trend_side=tr.get("side"),
        trend_move_pts=tr.get("move_pts"),
        trend_efficiency=tr.get("efficiency"),
        trend_sessions=int(tr.get("sessions") or 0),
        trend_label=str(tr.get("label") or ""),
        filter_side=filt,
        conflict=conflict,
    )


class BiasFilter:
    """Replay gate for Spike Neo + impulse retrace."""

    kinds = BIAS_KINDS

    def __init__(
        self,
        *,
        mode: str,
        use_season: bool,
        use_week2: bool,
        dailies: Sequence[DailyClose],
        tz_name: str = "Europe/Bucharest",
        flat_pts: float = DEFAULT_TREND_FLAT_PTS,
        sessions: int = DEFAULT_TREND_SESSIONS,
        ps: float = 0.01,
    ):
        self.mode = normalize_seasonal_mode(mode)
        self.week2_mode = "tag" if use_week2 else "off"
        self.use_season = bool(use_season)
        self.use_week2 = bool(use_week2)
        self.dailies = list(dailies or [])
        self.tz = ZoneInfo(tz_name)
        self.flat_pts = float(flat_pts)
        self.sessions = int(sessions or DEFAULT_TREND_SESSIONS)
        self.efficiency_min = DEFAULT_TREND_EFFICIENCY_MIN
        self.ps = float(ps)

    def snapshot(self, ts: datetime) -> BiasSnapshot:
        local_day = ts.astimezone(self.tz).date()
        return snapshot_bias(
            local_day,
            dailies=self.dailies,
            use_season=self.use_season,
            use_week2=self.use_week2,
            season_filter=self.mode == "filter",
            week2_filter=self.week2_mode == "filter",
            flat_pts=self.flat_pts,
            sessions=self.sessions,
            efficiency_min=self.efficiency_min,
            ps=self.ps,
        )

    def allows(self, kind: str, side: str, ts: datetime, meta: Dict[str, Any]) -> bool:
        """Stamp meta. Return False to drop this fire (still consume cooldown)."""
        if kind not in self.kinds:
            return True
        snap = self.snapshot(ts)
        meta.update(snap.as_meta())
        if self.mode != "filter" and self.week2_mode != "filter":
            return True
        if snap.conflict or snap.filter_side is None:
            return True
        return side == snap.filter_side

    @classmethod
    def from_filters(
        cls,
        filters: Optional[Dict[str, Any]],
        ticks: Sequence[Tick],
        *,
        symbol: str,
    ) -> Optional["BiasFilter"]:
        f = dict(filters or {})
        mode = normalize_seasonal_mode(f.get("seasonal_mode"))
        week2_mode = normalize_week2_mode(
            f.get("week2_mode"),
            week2_trend=bool(f.get("week2_trend")),
            seasonal_mode=mode,
        )
        week2 = week2_mode != "off"
        if mode == "off" and not week2:
            return None
        tz_name = str(f.get("timezone") or "Europe/Bucharest")
        dailies = build_daily_closes(ticks, tz_name) if week2 else []
        ps = point_size(symbol if "/" in symbol else symbol)
        inst = cls(
            mode=mode,
            use_season=mode != "off",
            use_week2=week2,
            dailies=dailies,
            tz_name=tz_name,
            flat_pts=float(f.get("trend_flat_pts") or DEFAULT_TREND_FLAT_PTS),
            sessions=int(f.get("trend_sessions") or DEFAULT_TREND_SESSIONS),
            ps=ps,
        )
        inst.week2_mode = week2_mode
        try:
            inst.efficiency_min = max(
                0.0, float(f.get("trend_efficiency_min") or DEFAULT_TREND_EFFICIENCY_MIN)
            )
        except (TypeError, ValueError):
            inst.efficiency_min = DEFAULT_TREND_EFFICIENCY_MIN
        return inst


def lookback_from(date_from: str, days: int = TREND_LOOKBACK_DAYS) -> str:
    d = date.fromisoformat(str(date_from)[:10])
    return (d - timedelta(days=int(days))).isoformat()
