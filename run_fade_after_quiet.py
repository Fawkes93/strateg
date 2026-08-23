#!/usr/bin/env python3
"""When run_fade_quiet.py exits: spike-rate (Jan–Mar) then Jan–Feb param hunt."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_fade_oat import log

PY = sys.executable


def quiet_running() -> bool:
    me = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-fl", "run_fade_quiet"], text=True)
    except subprocess.CalledProcessError:
        return False
    for line in out.splitlines():
        if "run_fade_after_quiet" in line:
            continue
        try:
            pid = int(line.split()[0])
        except (ValueError, IndexError):
            continue
        if pid != me:
            return True
    return False


def run(script: str) -> None:
    path = ROOT / script
    log(f"starting {script}")
    r = subprocess.run([PY, "-u", str(path)], cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(f"{script} failed with {r.returncode}")


def main() -> int:
    while quiet_running():
        log("quiet sweep still running — waiting 45s")
        time.sleep(45)
    log("quiet sweep finished")
    run("run_fade_spike_rate.py")
    run("run_fade_janfeb.py")
    log("pipeline done (spike-rate + janfeb)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
