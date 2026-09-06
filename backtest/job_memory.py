"""Release heavy in-process payloads after backtest jobs finish.

Long-lived webapp.py keeps module-level job state. Full tick packs and
trade-row lists must not stay in RAM after success/cancel/error — the full
JSON is already on disk under results/.
"""

from __future__ import annotations

import gc
from typing import Any, Dict, Mapping, Optional, Sequence

# Match typical status endpoint defaults (spike-fade 300, cooloff 400).
DEFAULT_UI_ROW_LIMIT = 400

# List keys commonly attached to strategy summaries.
DEFAULT_LIST_KEYS: Sequence[str] = ("rows", "skips")


def slim_retained_result(
    result: Optional[Mapping[str, Any]],
    *,
    row_limit: int = DEFAULT_UI_ROW_LIMIT,
    list_keys: Sequence[str] = DEFAULT_LIST_KEYS,
) -> Optional[Dict[str, Any]]:
    """Keep metrics + truncated row lists for status endpoints.

    Full payloads are written to disk before this runs. Truncation is
    recorded via row_count / *_truncated so get_*_state stays accurate.
    """
    if result is None:
        return None
    out: Dict[str, Any] = dict(result)
    limit = max(0, int(row_limit))

    # Research detail paths are enormous — drop after disk save.
    detail = out.get("detail_by_threshold")
    if isinstance(detail, dict) and detail:
        n = sum(len(v) for v in detail.values() if isinstance(v, list))
        out["detail_by_threshold"] = {}
        out["detail_row_count"] = n
        out["detail_truncated"] = True

    for key in list_keys:
        val = out.get(key)
        if not isinstance(val, list):
            continue
        n = len(val)
        count_key = "row_count" if key == "rows" else f"{key}_count"
        # Preserve an earlier authoritative count if present.
        if count_key not in out or out[count_key] is None:
            out[count_key] = n
        trunc_key = "rows_truncated" if key == "rows" else f"{key}_truncated"
        if n > limit:
            out[key] = val[:limit]
            out[trunc_key] = True
        else:
            out.setdefault(trunc_key, False)
    return out


def retain_result(
    result: Optional[Mapping[str, Any]],
    *,
    row_limit: int = DEFAULT_UI_ROW_LIMIT,
    list_keys: Sequence[str] = DEFAULT_LIST_KEYS,
) -> Optional[Dict[str, Any]]:
    """Alias used at the point _state.result / report is assigned post-save."""
    return slim_retained_result(result, row_limit=row_limit, list_keys=list_keys)


def slim_state_result_inplace(
    state: Any,
    attr: str = "result",
    *,
    row_limit: int = DEFAULT_UI_ROW_LIMIT,
    list_keys: Sequence[str] = DEFAULT_LIST_KEYS,
) -> None:
    """Slim a job-state attribute if it currently holds a mapping."""
    cur = getattr(state, attr, None)
    if isinstance(cur, Mapping):
        setattr(
            state,
            attr,
            slim_retained_result(cur, row_limit=row_limit, list_keys=list_keys),
        )


def release_job_memory() -> None:
    """Drop in-process tick packs and run a GC pass."""
    from backtest.dukascopy import clear_mem_packs

    clear_mem_packs()
    gc.collect()
