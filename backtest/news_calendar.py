"""Gold-moving news days for backtest filters.

Calendar file: `backtest/xau_news_days.json` (2023-01 → 2026-12).
Dates are US/Eastern calendar days. CPI/NFP 08:30 ET, FOMC 14:00 ET,
Jackson Hole ~10:00 ET — same YYYY-MM-DD in Europe/Bucharest.

Sets:
  scheduled  FOMC decision, CPI, NFP, Jackson Hole (known in advance)
  all        scheduled plus unscheduled shocks that actually moved gold
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet, Iterable, List, Optional, Sequence, Union

CALENDAR_PATH = Path(__file__).with_name("xau_news_days.json")

KIND_SCHEDULED = frozenset({"fomc", "cpi", "nfp", "jackson_hole"})
KIND_SHOCK = frozenset({"shock"})
KIND_ALL = KIND_SCHEDULED | KIND_SHOCK

NEWS_SETS = {
    "scheduled": KIND_SCHEDULED,
    "all": KIND_ALL,
}

DateLike = Union[date, datetime, str]


@dataclass(frozen=True)
class NewsEvent:
    date: date
    kind: str
    title: str
    time_et: Optional[str] = None
    note: Optional[str] = None

    def as_dict(self) -> dict:
        out = {
            "date": self.date.isoformat(),
            "kind": self.kind,
            "title": self.title,
        }
        if self.time_et:
            out["time_et"] = self.time_et
        if self.note:
            out["note"] = self.note
        return out


def normalize_news_mode(mode: Optional[str]) -> str:
    m = (mode or "off").strip().lower()
    if m in ("off", "tag", "filter"):
        return m
    return "off"


def normalize_news_set(name: Optional[str]) -> str:
    s = (name or "scheduled").strip().lower()
    if s in NEWS_SETS:
        return s
    return "scheduled"


def kinds_for_set(name: Optional[str]) -> FrozenSet[str]:
    return NEWS_SETS[normalize_news_set(name)]


def _as_date(value: DateLike) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _parse_event(raw: dict) -> NewsEvent:
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in KIND_ALL:
        raise ValueError(f"unknown news kind {kind!r} on {raw.get('date')}")
    return NewsEvent(
        date=_as_date(raw["date"]),
        kind=kind,
        title=str(raw.get("title") or kind),
        time_et=(str(raw["time_et"]).strip() if raw.get("time_et") else None),
        note=(str(raw["note"]).strip() if raw.get("note") else None),
    )


@lru_cache(maxsize=1)
def load_events(path: Optional[str] = None) -> tuple[NewsEvent, ...]:
    p = Path(path) if path else CALENDAR_PATH
    blob = json.loads(p.read_text(encoding="utf-8"))
    rows = blob.get("events") if isinstance(blob, dict) else blob
    events = tuple(_parse_event(r) for r in rows or [])
    return tuple(sorted(events, key=lambda e: (e.date, e.kind, e.title)))


def events_on(
    day: DateLike,
    *,
    kinds: Optional[Iterable[str]] = None,
    path: Optional[str] = None,
) -> List[NewsEvent]:
    want = frozenset(k.strip().lower() for k in kinds) if kinds is not None else KIND_ALL
    d = _as_date(day)
    return [e for e in load_events(path) if e.date == d and e.kind in want]


def is_news_day(
    day: DateLike,
    *,
    kinds: Optional[Iterable[str]] = None,
    path: Optional[str] = None,
) -> bool:
    return bool(events_on(day, kinds=kinds, path=path))


def news_dates(
    *,
    kinds: Optional[Iterable[str]] = None,
    path: Optional[str] = None,
) -> FrozenSet[date]:
    want = frozenset(k.strip().lower() for k in kinds) if kinds is not None else KIND_ALL
    return frozenset(e.date for e in load_events(path) if e.kind in want)


def format_news(events: Sequence[NewsEvent]) -> tuple[Optional[str], Optional[str]]:
    if not events:
        return None, None
    kinds = ",".join(dict.fromkeys(e.kind for e in events))
    title = " · ".join(e.title for e in events)
    return kinds, title
