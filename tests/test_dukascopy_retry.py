"""Download progress keeps the hour line moving through a retry."""

from datetime import datetime, timezone


def test_cache_hours_retry_returns_to_hour_line(tmp_path, monkeypatch):
    from backtest import dukascopy as duka

    hours = [
        datetime(2026, 8, 1, h, tzinfo=timezone.utc) for h in range(20)
    ]
    fails = {hours[0], hours[1]}

    def fake_cache_hour(symbol, when, *, cache_dir, note=None, **kwargs):
        when = when.replace(minute=0, second=0, microsecond=0)
        if when in fails:
            fails.remove(when)
            if note:
                note("HTTP 503 · try 1/8 · 8s")
            raise RuntimeError("503")
        return "empty"

    monkeypatch.setattr(duka, "cache_hour", fake_cache_hour)
    monkeypatch.setattr(duka.time, "sleep", lambda *_a, **_k: None)
    messages = []
    duka.cache_hours(
        "XAUUSD",
        hours,
        cache_dir=tmp_path,
        max_workers=16,
        progress=lambda **kw: messages.append(kw["message"]),
    )
    retry_i = next(i for i, m in enumerate(messages) if "retry 1:" in m)
    assert "2 hours failed" in messages[retry_i]
    assert "next pass 8 workers" in messages[retry_i]
    assert messages[retry_i].startswith("Hour ")
    assert "reducing workers" not in messages[retry_i]
    assert any(
        m.startswith("Hour ") and "retry 2" in m for m in messages[retry_i + 1 :]
    )
    assert any("HTTP 503" in m and m.startswith("Hour ") for m in messages)
