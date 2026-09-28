"""List and load saved result JSON from results/ without re-running a scan."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backtest.runner import DEFAULT_RESULTS

KNOWN_KINDS = frozenset(
    {
        "research",
        "batch_sweep",
        "session_clock",
        "spike_fade",
        "micro_fade",
        "micro_momentum",
        "overnight_break",
        "asia_liquidity",
        "impulse_fork",
        "cooloff",
        "fvg",
    }
)

_PEEK_BYTES = 8192
_STR_KEYS = ("kind", "symbol", "date_from", "date_to", "finished_at", "from", "to", "data_source")
_NUM_KEYS = ("trades", "alerts", "sum_pts", "run_count", "ticks")


def classify_filename(name: str) -> Optional[str]:
    """Best-effort kind from the results/ basename. 'micro' needs a JSON peek."""
    n = (name or "").lower()
    if not n.endswith(".json"):
        return None
    if n.startswith("batch_"):
        return "batch_sweep"
    if n.startswith("summary_") and (n.endswith("_forward.json") or "_forward_" in n):
        return "research"
    if n.startswith("session_"):
        return "session_clock"
    if n.startswith("spikefade_"):
        return "spike_fade"
    if n.startswith("overnight_"):
        return "overnight_break"
    if n.startswith("asialiq_"):
        return "asia_liquidity"
    if n.startswith("fork_"):
        return "impulse_fork"
    if n.startswith("cooloff_"):
        return "cooloff"
    if n.startswith("ifvg_"):
        return "fvg"
    if n.startswith("micro_"):
        return "micro"
    return None


def classify_result(
    name: str,
    peek: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Filename prefix wins when it is a concrete kind (research/batch/session/…).
    Micro UI/CLI files share the micro_ prefix — use JSON `kind`.
    Unknown names can still match if the JSON kind is one we know.
    """
    fn = classify_filename(name)
    if fn and fn != "micro":
        return fn
    peeked = None
    if data and isinstance(data.get("kind"), str):
        peeked = data["kind"]
    else:
        peeked = _extract_fields(peek).get("kind")
    if peeked in KNOWN_KINDS:
        return peeked
    return None


def resolve_saved_path(name: str) -> Path:
    """Resolve a basename under results/. Rejects path traversal."""
    if (
        not name
        or "/" in name
        or "\\" in name
        or ".." in name
        or name.startswith(".")
        or name != Path(name).name
    ):
        raise ValueError("Invalid result name")
    if not name.endswith(".json"):
        raise ValueError("Not a JSON result")
    root = Path(DEFAULT_RESULTS).resolve()
    path = (root / name).resolve()
    if path.parent != root:
        raise ValueError("Invalid result name")
    return path


def read_saved_result(name: str) -> Tuple[Dict[str, Any], Path]:
    path = resolve_saved_path(name)
    if not path.is_file():
        raise FileNotFoundError(name)
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Result JSON must be an object")
    return data, path


def list_saved_results(kind: str) -> List[Dict[str, Any]]:
    if kind not in KNOWN_KINDS:
        raise ValueError(f"Unknown kind: {kind}")
    root = Path(DEFAULT_RESULTS)
    if not root.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
    for path in root.glob("*.json"):
        if not path.is_file():
            continue
        try:
            peek = path.read_bytes()[:_PEEK_BYTES].decode("utf-8", errors="replace")
        except OSError:
            continue
        classified = classify_result(path.name, peek)
        if classified != kind:
            continue
        fields = _extract_fields(peek)
        st = path.stat()
        rows.append(
            {
                "name": path.name,
                "kind": classified,
                "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "size": st.st_size,
                "symbol": fields.get("symbol"),
                "date_from": fields.get("date_from") or _ymd(fields.get("from")),
                "date_to": fields.get("date_to") or _ymd(fields.get("to")),
                "trades": fields.get("trades"),
                "alerts": fields.get("alerts"),
                "run_count": fields.get("run_count"),
                "sum_pts": fields.get("sum_pts"),
                "finished_at": fields.get("finished_at"),
                "label": _label(path.name, fields, classified),
            }
        )
    rows.sort(key=lambda r: r.get("mtime") or "", reverse=True)
    return rows


def load_into_job(kind: str, name: str) -> Dict[str, Any]:
    """Inject a saved JSON into the matching tab's in-memory job state."""
    if kind not in KNOWN_KINDS:
        raise ValueError(f"Unknown kind: {kind}")
    data, path = read_saved_result(name)
    actual = classify_result(path.name, data=data)
    if actual != kind:
        raise ValueError(f"File is {actual or 'unknown'}, not {kind}")

    if kind == "batch_sweep":
        from backtest.batch import load_report

        out = load_report(data)
    elif kind == "research":
        from backtest.jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "session_clock":
        from backtest.session_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "spike_fade":
        from backtest.spike_fade_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind in ("micro_fade", "micro_momentum"):
        from backtest.micro_momentum_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "overnight_break":
        from backtest.overnight_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "asia_liquidity":
        from backtest.asia_liquidity_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "impulse_fork":
        from backtest.impulse_fork_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "cooloff":
        from backtest.cooloff_jobs import load_saved

        out = load_saved(data, name=name)
    elif kind == "fvg":
        from backtest.fvg_jobs import load_saved

        out = load_saved(data, name=name)
    else:
        raise ValueError(f"Unknown kind: {kind}")

    if out.get("ok"):
        out["path"] = str(path)
        out["name"] = name
        out["kind"] = kind
    return out


def _ymd(value: Any) -> Optional[str]:
    if not value:
        return None
    s = str(value)
    return s[:10] if len(s) >= 10 else s


def _extract_fields(blob: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not blob:
        return out
    for key in _STR_KEYS:
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', blob)
        if m:
            out[key] = m.group(1)
    for key in _NUM_KEYS:
        m = re.search(rf'"{re.escape(key)}"\s*:\s*(-?\d+(?:\.\d+)?)', blob)
        if m:
            raw = m.group(1)
            out[key] = float(raw) if "." in raw else int(raw)
    return out


def _label(name: str, fields: Dict[str, Any], kind: str) -> str:
    parts: List[str] = []
    sym = fields.get("symbol")
    if isinstance(sym, str) and sym:
        parts.append(sym.replace("/", ""))
    df = fields.get("date_from") or _ymd(fields.get("from")) or ""
    dt = fields.get("date_to") or _ymd(fields.get("to")) or ""
    if df or dt:
        parts.append(f"{df} → {dt}")
    if kind == "batch_sweep" and fields.get("run_count") is not None:
        parts.append(f"{fields['run_count']} runs")
    elif kind == "research" and fields.get("alerts") is not None:
        parts.append(f"{fields['alerts']} alerts")
    elif fields.get("trades") is not None:
        parts.append(f"{fields['trades']} trades")
    if kind == "overnight_break":
        source = fields.get("data_source")
        if source == "ticks":
            parts.append("ticks")
        elif source == "candles_5m":
            parts.append("5m candles")
    if fields.get("sum_pts") is not None:
        parts.append(f"sum {fields['sum_pts']}")
    head = " · ".join(parts)
    return f"{head} — {name}" if head else name
